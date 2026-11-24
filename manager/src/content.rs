//! Content checkout follows install.sh. The binary does not exec that script or `python -m omh update`.

use crate::error::Fail;
use crate::forward::{self, Child};
use crate::record::Record;
use crate::util;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

pub fn update(
    home: &Path,
    record: &mut Record,
    python: &Path,
    explicit_source: Option<&Path>,
    tag_flag: Option<&str>,
) -> Result<i32, Fail> {
    if let Some(source) = explicit_source {
        if !same_path(source, &home.join("repo")) {
            return Err(Fail::new(
                "OMH_SOURCE_NOT_MANAGED",
                format!(
                    "omh update delegates to the managed checkout at {} (current source: {}); from a developer checkout use omh refresh, or bootstrap with install.sh on POSIX or install.ps1 on Windows",
                    home.join("repo").display(),
                    source.display()
                ),
            ));
        }
    }
    require_tool("git")?;
    require_tool("curl")?;
    let clone = home.join("repo");
    if clone.join(".git").is_dir() {
        require_clean(&clone)?;
    }
    let repo = std::env::var("OMH_REPO").unwrap_or_else(|_| "https://github.com/zzzhty/oh-my-harness".to_string());
    let tag = resolve_tag(&repo, tag_flag)?;
    let pinned = pinned_sha(&repo, &tag)?;
    let resolved = resolve_remote_tag(&repo, &tag)?;
    if resolved != pinned {
        return Err(Fail::new(
            "OMH_INVALID",
            format!("tag {tag} resolves to {resolved} but the release pins {pinned}"),
        ));
    }
    let mode = acquire(&clone, &repo, &tag, &pinned)?;
    require_clean(&clone)?;
    project(home, record, python, &clone, &mode)
}

fn project(home: &Path, record: &mut Record, python: &Path, clone: &Path, mode: &str) -> Result<i32, Fail> {
    let (verb, targets) = selected(home, mode)?;
    let scratch = forward::scratch_dir(home);
    for (harness, skills) in &targets {
        eprintln!("{verb} target: {harness} at {}", skills.display());
        let code = forward::run(home, record, &child(&verb, home, python, clone, harness, skills, Some(scratch.clone())))?;
        if code != 0 {
            return Ok(code);
        }
    }
    eprintln!("Target writes completed; verifying selected targets.");
    let mut failed = false;
    for (harness, skills) in &targets {
        let code = forward::run(home, record, &child("status", home, python, clone, harness, skills, None))?;
        if code != 0 {
            eprintln!("verification failed for {harness} at {}", skills.display());
            failed = true;
        }
    }
    if failed {
        return Err(Fail::new(
            "OMH_INVALID",
            "Target writes are not rolled back; inspect the reported target status.",
        ));
    }
    Ok(0)
}

fn child(
    verb: &str,
    home: &Path,
    python: &Path,
    clone: &Path,
    harness: &str,
    skills: &Path,
    scratch: Option<PathBuf>,
) -> Child {
    let mut args = vec![
        "--home".into(),
        home.display().to_string(),
        "--harness".into(),
        harness.to_string(),
        "--skills-root".into(),
        skills.display().to_string(),
        "--python".into(),
        python.display().to_string(),
    ];
    if let Some(scratch) = &scratch {
        args.push("--bin-dir".into());
        args.push(scratch.display().to_string());
    }
    Child {
        command: verb.to_string(),
        args,
        source: clone.to_path_buf(),
        python: python.to_path_buf(),
        store_source: true,
        scratch,
    }
}

fn selected(home: &Path, mode: &str) -> Result<(String, Vec<(String, PathBuf)>), Fail> {
    let verb = if mode == "bootstrap" { "install" } else { "refresh" };
    let index = home.join("targets.json");
    let mut targets = Vec::new();
    if mode == "upgrade" && index.exists() {
        let bytes = fs::read(&index).map_err(|err| {
            Fail::new("OMH_INVALID", format!("cannot read target index {}: {err}", index.display()))
        })?;
        let value: Value = serde_json::from_slice(&bytes).map_err(|err| {
            Fail::new("OMH_INVALID", format!("cannot read target index {}: {err}", index.display()))
        })?;
        let obj = value.as_object().ok_or_else(|| {
            Fail::new("OMH_INVALID", format!("cannot read target index {}: expected an object", index.display()))
        })?;
        for entry in obj.values() {
            let harness = entry.get("harness").and_then(Value::as_str).filter(|value| !value.is_empty());
            let root = entry.get("skillsRoot").and_then(Value::as_str).filter(|value| Path::new(value).is_absolute());
            match (harness, root) {
                (Some(harness), Some(root)) => targets.push((harness.to_string(), PathBuf::from(root))),
                _ => {
                    return Err(Fail::new(
                        "OMH_INVALID",
                        format!("cannot read target index {}: expected harness and absolute skillsRoot for every target", index.display()),
                    ));
                }
            }
        }
    }
    if targets.is_empty() {
        let list = std::env::var("OMH_HARNESS").unwrap_or_else(|_| "codex".to_string());
        let user = util::user_home()?;
        for harness in list.split(',').filter(|item| !item.is_empty()) {
            let folder = harness_dir(harness)?;
            targets.push((harness.to_string(), user.join(folder).join("skills")));
        }
    }
    if targets.is_empty() {
        return Err(Fail::new("OMH_INVALID", "no OMH targets selected"));
    }
    for (harness, _) in &targets {
        harness_dir(harness)?;
    }
    Ok((verb.to_string(), targets))
}

fn harness_dir(harness: &str) -> Result<&'static str, Fail> {
    match harness {
        "codex" => Ok(".codex"),
        "claude-code" => Ok(".claude"),
        "grok" => Ok(".grok"),
        _ => Err(Fail::new("OMH_INVALID", format!("unknown OMH harness: {harness}"))),
    }
}

fn acquire(clone: &Path, repo: &str, tag: &str, pinned: &str) -> Result<String, Fail> {
    if clone.exists() && !clone.join(".git").is_dir() {
        return Err(Fail::new("OMH_INVALID", format!("{} exists and is not a git clone", clone.display())));
    }
    if clone.join(".git").is_dir() {
        let clone_text = clone.display().to_string();
        git_ok(&["-C", &clone_text, "fetch", "--tags", "--force", "origin"], "git fetch failed")?;
        checkout(clone, tag)?;
        let got = rev_parse(clone)?;
        if got != pinned {
            return Err(Fail::new("OMH_INVALID", format!("checkout HEAD {got} does not match the pinned {pinned}")));
        }
        return Ok("upgrade".to_string());
    }
    let staging = clone
        .parent()
        .ok_or_else(|| Fail::new("OMH_INVALID", "manager home has no parent"))?
        .join(format!(".repo.clone.{}", std::process::id()));
    let _ = fs::remove_dir_all(&staging);
    if let Some(parent) = clone.parent() {
        fs::create_dir_all(parent).map_err(|err| Fail::io("cannot create the manager home", err))?;
    }
    let staging_text = staging.display().to_string();
    let mut clone_args = vec!["-c".to_string(), "advice.detachedHead=false".into()];
    if cfg!(windows) {
        clone_args.extend(["-c".into(), "core.autocrlf=false".into()]);
    }
    clone_args.extend([
        "clone".into(),
        "--quiet".into(),
        "--branch".into(),
        tag.to_string(),
        repo.to_string(),
        staging_text,
    ]);
    let borrowed: Vec<&str> = clone_args.iter().map(String::as_str).collect();
    if let Err(err) = git_status(&borrowed, "git clone failed") {
        let _ = fs::remove_dir_all(&staging);
        return Err(err);
    }
    match rev_parse(&staging) {
        Ok(got) if got == pinned => {}
        Ok(got) => {
            let _ = fs::remove_dir_all(&staging);
            return Err(Fail::new("OMH_INVALID", format!("clone HEAD {got} does not match the pinned {pinned}")));
        }
        Err(err) => {
            let _ = fs::remove_dir_all(&staging);
            return Err(err);
        }
    }
    if let Err(err) = fs::rename(&staging, clone) {
        let _ = fs::remove_dir_all(&staging);
        return Err(Fail::io("cannot move the clone into place", err));
    }
    checkout(clone, tag)?;
    let got = rev_parse(clone)?;
    if got != pinned {
        return Err(Fail::new("OMH_INVALID", format!("checkout HEAD {got} does not match the pinned {pinned}")));
    }
    Ok("bootstrap".to_string())
}

fn checkout(clone: &Path, tag: &str) -> Result<(), Fail> {
    let clone_text = clone.display().to_string();
    let reference = format!("refs/tags/{tag}");
    let mut args = vec!["-C".to_string(), clone_text, "-c".into(), "advice.detachedHead=false".into()];
    if cfg!(windows) {
        args.extend(["-c".into(), "core.autocrlf=false".into()]);
    }
    args.extend(["checkout".into(), "--quiet".into(), reference]);
    let borrowed: Vec<&str> = args.iter().map(String::as_str).collect();
    git_ok(&borrowed, &format!("checkout {tag} failed (a dirty clone fails closed)"))
}

fn require_clean(clone: &Path) -> Result<(), Fail> {
    let output = git_command(&["-C", &clone.display().to_string(), "status", "--porcelain", "--untracked-files=all", "--ignored"])?;
    if !output.status.success() {
        return Err(Fail::new(
            "OMH_INVALID",
            format!("cannot inspect {}; leaving the checkout unchanged", clone.display()),
        ));
    }
    if !String::from_utf8_lossy(&output.stdout).trim().is_empty() {
        return Err(Fail::new(
            "OMH_INVALID",
            format!(
                "{} has local changes or untracked files (including ignored files); preserve or move them outside the clone before retrying",
                clone.display()
            ),
        ));
    }
    Ok(())
}

fn resolve_tag(repo: &str, flag: Option<&str>) -> Result<String, Fail> {
    if let Some(tag) = flag {
        return Ok(tag.to_string());
    }
    if let Ok(tag) = std::env::var("OMH_VERSION") {
        if !tag.is_empty() {
            return Ok(tag);
        }
    }
    let Some(api) = repo.strip_prefix("https://github.com/").filter(|rest| !rest.is_empty()) else {
        return Err(Fail::new("OMH_INVALID", "OMH_VERSION is required when OMH_REPO is not a GitHub URL"));
    };
    let url = format!("https://api.github.com/repos/{api}/releases/latest");
    let body = curl(&url, "could not resolve the latest release tag")?;
    let value: Value = serde_json::from_str(&body).map_err(|_| {
        Fail::new("OMH_INVALID", "could not resolve the latest release tag")
    })?;
    value
        .get("tag_name")
        .and_then(Value::as_str)
        .filter(|tag| !tag.is_empty())
        .map(str::to_string)
        .ok_or_else(|| Fail::new("OMH_INVALID", "could not resolve the latest release tag"))
}

fn pinned_sha(repo: &str, tag: &str) -> Result<String, Fail> {
    let url = if let Ok(value) = std::env::var("OMH_REF_URL") {
        if value.is_empty() {
            default_ref(repo, tag)?
        } else {
            value
        }
    } else {
        default_ref(repo, tag)?
    };
    let body = if url.contains("://") {
        curl(&url, &format!("ref asset not found: {url}"))?
    } else {
        fs::read_to_string(&url).map_err(|_| Fail::new("OMH_INVALID", format!("ref asset not found: {url}")))?
    };
    let pinned: String = body.chars().filter(|ch| !ch.is_whitespace()).collect();
    if pinned.len() < 40 {
        return Err(Fail::new("OMH_INVALID", format!("the ref asset does not hold a commit SHA: {url}")));
    }
    Ok(pinned)
}

fn default_ref(repo: &str, tag: &str) -> Result<String, Fail> {
    let Some(api) = repo.strip_prefix("https://github.com/").filter(|rest| !rest.is_empty()) else {
        return Err(Fail::new("OMH_INVALID", "OMH_REF_URL is required when OMH_REPO is not a GitHub URL"));
    };
    Ok(format!("https://github.com/{api}/releases/download/{tag}/omh-{tag}.ref"))
}

fn resolve_remote_tag(repo: &str, tag: &str) -> Result<String, Fail> {
    let peeled = ls_remote(repo, &format!("refs/tags/{tag}^{{}}"))?;
    if !peeled.is_empty() {
        return Ok(peeled);
    }
    let plain = ls_remote(repo, &format!("refs/tags/{tag}"))?;
    if plain.is_empty() {
        return Err(Fail::new("OMH_INVALID", format!("tag {tag} was not found in {repo}")));
    }
    Ok(plain)
}

fn ls_remote(repo: &str, reference: &str) -> Result<String, Fail> {
    let output = git_command(&["ls-remote", repo, reference])?;
    if !output.status.success() {
        return Err(Fail::new("OMH_INVALID", format!("tag was not found in {repo}")));
    }
    let text = String::from_utf8_lossy(&output.stdout);
    Ok(text.lines().next().and_then(|line| line.split_whitespace().next()).unwrap_or("").to_string())
}

fn rev_parse(clone: &Path) -> Result<String, Fail> {
    let output = git_command(&["-C", &clone.display().to_string(), "rev-parse", "HEAD"])?;
    if !output.status.success() {
        return Err(Fail::new("OMH_INVALID", format!("cannot read HEAD of {}", clone.display())));
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

fn require_tool(name: &str) -> Result<(), Fail> {
    let program = if cfg!(windows) { format!("{name}.exe") } else { name.to_string() };
    match Command::new(&program).arg("--version").output() {
        Ok(output) if output.status.success() => Ok(()),
        _ => Err(Fail::new("OMH_INVALID", format!("{name} is required"))),
    }
}

fn git_ok(args: &[&str], message: &str) -> Result<(), Fail> {
    git_status(args, message).map(|_| ())
}

fn git_status(args: &[&str], message: &str) -> Result<std::process::Output, Fail> {
    let output = git_command(args)?;
    if output.status.success() {
        Ok(output)
    } else {
        Err(Fail::new("OMH_INVALID", message))
    }
}

fn git_command(args: &[&str]) -> Result<std::process::Output, Fail> {
    let mut command = Command::new("git");
    if cfg!(windows) {
        command.env("GIT_TERMINAL_PROMPT", "0");
        command.env("GCM_INTERACTIVE", "Never");
    }
    command.args(args);
    command.output().map_err(|_| Fail::new("OMH_INVALID", "git is required"))
}

fn curl(url: &str, message: &str) -> Result<String, Fail> {
    let program = if cfg!(windows) { "curl.exe" } else { "curl" };
    let output = Command::new(program)
        .args(["-fsSL", url])
        .output()
        .map_err(|_| Fail::new("OMH_INVALID", message))?;
    if !output.status.success() {
        return Err(Fail::new("OMH_INVALID", message));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

fn same_path(left: &Path, right: &Path) -> bool {
    normalize(left) == normalize(right)
}

fn normalize(path: &Path) -> PathBuf {
    if let Ok(resolved) = path.canonicalize() {
        return resolved;
    }
    let mut out = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}


