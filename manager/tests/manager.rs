//! Manager behavior the Python suites cannot see.
//! Every process gets a temp HOME and an explicit --home. Nothing writes the real omh command.

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::OnceLock;

static SEQ: AtomicU64 = AtomicU64::new(0);

const MARKER: &str = "# oh-my-harness standalone launcher v1";

const FAKE_MAIN: &str = r##"import json, os, sys
from pathlib import Path

cmdline = []
try:
    raw = Path("/proc/self/cmdline").read_bytes().split(b"\0")
    cmdline = [part.decode("utf-8", "replace") for part in raw if part]
except OSError:
    cmdline = []

row = {
    "argv": sys.argv,
    "exe": sys.executable,
    "pythonpath": os.environ.get("PYTHONPATH", ""),
    "path": os.environ.get("PATH", ""),
    "cwd": os.getcwd(),
    "cmdline": cmdline,
}
trace = os.environ.get("OMH_TRACE")
if trace:
    path = Path(trace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")

argv = sys.argv[1:]
verb = argv[0] if argv else ""

def flag(name):
    if name in argv:
        return argv[argv.index(name) + 1]
    return None

if os.environ.get("OMH_WRITE_SHIM") == "1" and flag("--bin-dir"):
    dest = Path(flag("--bin-dir")) / "omh"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"#!/bin/sh\n# oh-my-harness standalone launcher v1\n")
    home = flag("--home")
    if home:
        Path(home, "shim.json").write_bytes((json.dumps({"path": str(dest)}) + "\n").encode())

mark = os.environ.get("OMH_MARK")
if mark and verb in ("install", "refresh"):
    Path(mark).write_text(verb + "\n", encoding="utf-8")

if verb == "status":
    code = int(os.environ.get("OMH_STATUS_CODE", os.environ.get("OMH_CHILD_CODE", "0")))
else:
    code = int(os.environ.get("OMH_CHILD_CODE", "0"))
if code:
    sys.stderr.write("child-exit %s\n" % code)
raise SystemExit(code)
"##;

struct Sandbox {
    root: PathBuf,
    user: PathBuf,
    home: PathBuf,
    bin: PathBuf,
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

struct Repo {
    bare: PathBuf,
    sha1: String,
    sha2: String,
    ref1: PathBuf,
    ref2: PathBuf,
}

fn sandbox() -> Sandbox {
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let root = std::env::temp_dir().join(format!("omh-mgr-{}-{}", std::process::id(), n));
    assert!(root.starts_with(std::env::temp_dir()), "{}", root.display());
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(root.join("user")).unwrap();
    fs::create_dir_all(root.join("home")).unwrap();
    fs::create_dir_all(root.join("bin")).unwrap();
    Sandbox {
        user: root.join("user"),
        home: root.join("home"),
        bin: root.join("bin"),
        root,
    }
}

fn p(path: &Path) -> String {
    path.display().to_string()
}

fn bin() -> &'static Path {
    static CELL: OnceLock<PathBuf> = OnceLock::new();
    CELL.get_or_init(|| PathBuf::from(env!("CARGO_BIN_EXE_omh")))
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::new().chain_update(bytes).finalize())
}

fn empty_gitconfig() -> &'static Path {
    static CELL: OnceLock<PathBuf> = OnceLock::new();
    CELL.get_or_init(|| {
        let path = std::env::temp_dir().join(format!("omh-gitconfig-{}", std::process::id()));
        fs::write(&path, b"").unwrap();
        path
    })
}

fn mode_set(path: &Path, mode: u32) {
    fs::set_permissions(path, fs::Permissions::from_mode(mode)).unwrap();
}

fn unix_mode(path: &Path) -> u32 {
    fs::metadata(path).unwrap().permissions().mode() & 0o777
}

fn inode(path: &Path) -> u64 {
    fs::metadata(path).unwrap().ino()
}

fn uv_python_dir() -> String {
    // FORCE_COLOR wraps the directory in ANSI; that is not a path uv can search.
    let output = Command::new(uv_binary())
        .args(["python", "dir", "--color", "never"])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).unwrap().trim().to_string()
}

fn uv_binary() -> PathBuf {
    let path = std::env::var("PATH").unwrap_or_default();
    for dir in path
        .split(':')
        .chain(std::iter::once("/home/zzzhty/.local/bin"))
    {
        let candidate = PathBuf::from(dir).join("uv");
        if candidate.is_file() {
            return candidate;
        }
    }
    panic!("uv is not on PATH and not at ~/.local/bin/uv");
}

fn base_python() -> &'static Path {
    static CELL: OnceLock<PathBuf> = OnceLock::new();
    CELL.get_or_init(|| {
        let scratch = std::env::temp_dir().join(format!("omh-base-{}", std::process::id()));
        fs::create_dir_all(&scratch).unwrap();
        let output = Command::new(uv_binary())
            .args([
                "python",
                "find",
                "--no-project",
                "--python-preference",
                "only-managed",
                "--no-python-downloads",
            ])
            .current_dir(&scratch)
            .env_remove("VIRTUAL_ENV")
            .env_remove("UV_PROJECT_ENVIRONMENT")
            .env("UV_NO_PROJECT", "1")
            .env("UV_PYTHON_DOWNLOADS", "never")
            .env("UV_PYTHON_PREFERENCE", "only-managed")
            .output()
            .expect("uv");
        let _ = fs::remove_dir_all(&scratch);
        assert!(
            output.status.success(),
            "uv python find failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let text = String::from_utf8_lossy(&output.stdout);
        let found = text.lines().rev().find(|line| !line.trim().is_empty()).expect("uv printed no path");
        let path = fs::canonicalize(found.trim()).expect("python path");
        let check = Command::new(&path)
            .args([
                "-I",
                "-B",
                "-c",
                "import sys; assert sys.prefix==sys.base_prefix; assert sys.version_info[:2] >= (3, 11)",
            ])
            .env_remove("PYTHONPATH")
            .env_remove("PYTHONHOME")
            .output()
            .unwrap();
        assert!(check.status.success(), "base probe: {}", String::from_utf8_lossy(&check.stderr));
        path
    })
}

fn invoke(sb: &Sandbox, args: &[&str], extra: &[(&str, &str)], path: Option<&str>) -> Output {
    let mut cmd = Command::new(bin());
    for (key, _) in std::env::vars() {
        if key.starts_with("OMH_")
            || matches!(
                key.as_str(),
                "VIRTUAL_ENV" | "UV_PROJECT_ENVIRONMENT" | "UV_PYTHON"
            )
        {
            cmd.env_remove(key);
        }
    }
    let leaked = sb.root.join("leaked-pythonpath");
    cmd.env("HOME", &sb.user);
    cmd.env("PYTHONPATH", &leaked);
    cmd.env("GIT_CONFIG_GLOBAL", empty_gitconfig());
    cmd.env("GIT_CONFIG_SYSTEM", empty_gitconfig());
    cmd.env("GIT_CONFIG_NOSYSTEM", "1");
    cmd.env("GIT_TERMINAL_PROMPT", "0");
    cmd.current_dir(&sb.root);
    if let Some(path) = path {
        cmd.env("PATH", path);
    }
    for (key, value) in extra {
        cmd.env(key, value);
    }
    cmd.args(args);
    cmd.output()
        .unwrap_or_else(|err| panic!("spawn omh: {err}"))
}

fn show(output: &Output) -> String {
    format!(
        "status {:?}\nstdout {}\nstderr {}",
        output.status.code(),
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    )
}

fn fail_value(output: &Output) -> Value {
    let err = String::from_utf8_lossy(&output.stderr);
    let line = err
        .lines()
        .rev()
        .find(|line| line.starts_with('{'))
        .unwrap_or("");
    serde_json::from_str(line).unwrap_or_else(|error| panic!("stderr JSON {error}: {err}"))
}

fn assert_ok(output: &Output) {
    assert_eq!(output.status.code(), Some(0), "{}", show(output));
}

fn assert_err(output: &Output, code: &str, message: &str) {
    assert_eq!(output.status.code(), Some(1), "{}", show(output));
    let value = fail_value(output);
    assert_eq!(value["error"]["code"], code, "{}", show(output));
    assert_eq!(value["error"]["message"], message, "{}", show(output));
}

fn assert_usage(output: &Output, text: &str) {
    assert_eq!(output.status.code(), Some(2), "{}", show(output));
    assert!(output.stdout.is_empty(), "{}", show(output));
    let err = String::from_utf8_lossy(&output.stderr);
    assert!(err.starts_with("usage: omh <command>\n"), "{err}");
    assert!(err.contains(text), "{err}");
}

fn assert_no_locks(sb: &Sandbox) {
    for root in [&sb.home, &sb.bin, &sb.user] {
        let mut stack = vec![root.clone()];
        while let Some(dir) = stack.pop() {
            let Ok(entries) = fs::read_dir(&dir) else {
                continue;
            };
            for entry in entries.flatten() {
                let path = entry.path();
                let name = entry.file_name();
                let name = name.to_string_lossy();
                assert!(
                    name != ".omh-owner.lock"
                        && name != ".prepare.lock"
                        && name != ".omh-home.lock",
                    "lock created at {}",
                    path.display()
                );
                if path.is_dir() {
                    stack.push(path);
                }
            }
        }
    }
}

fn record(sb: &Sandbox) -> Value {
    let bytes = fs::read(sb.home.join("manager.json")).unwrap_or_else(|err| panic!("{err}"));
    serde_json::from_slice(&bytes)
        .unwrap_or_else(|err| panic!("{err}: {}", String::from_utf8_lossy(&bytes)))
}

fn assert_record_shape(sb: &Sandbox) {
    let text = fs::read_to_string(sb.home.join("manager.json")).unwrap();
    let mut at = 0;
    for key in [
        "schemaVersion",
        "kind",
        "binDir",
        "path",
        "source",
        "python",
        "pythonDigest",
        "digest",
        "binaryVersion",
    ] {
        let needle = format!("\"{key}\"");
        let found = text[at..]
            .find(&needle)
            .unwrap_or_else(|| panic!("missing {key} in {text}"));
        at += found + needle.len();
    }
    assert!(!text.contains(' '), "{text}");
    assert_eq!(unix_mode(&sb.home.join("manager.json")), 0o644);
}

fn install_args<'a>(home: &'a str, bin_dir: &'a str, python: &'a str) -> Vec<&'a str> {
    vec![
        "self",
        "install",
        "--home",
        home,
        "--bin-dir",
        bin_dir,
        "--python",
        python,
    ]
}

fn install_managed(sb: &Sandbox, source: Option<&Path>) -> Value {
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let python = p(base_python());
    let source_text = source.map(p);
    let mut args = install_args(&home, &bin_dir, &python);
    if let Some(source) = source_text.as_deref() {
        args.extend(["--source", source]);
    }
    let output = invoke(sb, &args, &[("OMH_BINARY_VERSION", "1.2.3")], None);
    assert_ok(&output);
    record(sb)
}

fn write_package(dir: &Path) {
    let pkg = dir.join("omh");
    fs::create_dir_all(&pkg).unwrap();
    fs::write(pkg.join("__init__.py"), b"").unwrap();
    fs::write(pkg.join("__main__.py"), FAKE_MAIN).unwrap();
}

fn read_trace(path: &Path) -> Vec<Value> {
    if !path.exists() {
        return Vec::new();
    }
    fs::read_to_string(path)
        .unwrap()
        .lines()
        .filter(|line| !line.is_empty())
        .map(|line| serde_json::from_str(line).unwrap_or_else(|err| panic!("{err}: {line}")))
        .collect()
}

fn argv_flag<'a>(row: &'a Value, name: &str) -> &'a str {
    let argv = row["argv"].as_array().unwrap();
    let pos = argv
        .iter()
        .position(|item| item == name)
        .unwrap_or_else(|| panic!("no {name} in {argv:?}"));
    argv[pos + 1].as_str().unwrap()
}

fn assert_child_launch(row: &Value, verb: &str, source: &Path) {
    let argv0 = row["argv"][0].as_str().unwrap();
    assert!(argv0.ends_with("omh/__main__.py"), "{argv0}");
    assert_eq!(row["argv"][1], verb);
    let exe = fs::canonicalize(row["exe"].as_str().unwrap()).unwrap();
    assert_eq!(exe, base_python());
    assert_eq!(row["pythonpath"], p(source));
    assert!(!row["pythonpath"]
        .as_str()
        .unwrap()
        .contains("leaked-pythonpath"));
    assert!(!row["path"].as_str().unwrap().contains(".manager-bin"));
    assert_eq!(
        fs::canonicalize(row["cwd"].as_str().unwrap()).unwrap(),
        fs::canonicalize(source).unwrap()
    );
    let cmdline: Vec<&str> = row["cmdline"]
        .as_array()
        .unwrap()
        .iter()
        .map(|item| item.as_str().unwrap())
        .collect();
    assert!(
        cmdline.windows(3).any(|item| item == ["-B", "-m", "omh"]),
        "{cmdline:?}"
    );
    assert!(!cmdline.iter().any(|item| *item == "-I"), "{cmdline:?}");
}

fn git(args: &[&str]) -> Output {
    let output = Command::new("/usr/bin/git")
        .args(args)
        .env("GIT_CONFIG_GLOBAL", empty_gitconfig())
        .env("GIT_CONFIG_SYSTEM", empty_gitconfig())
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_TERMINAL_PROMPT", "0")
        .env_remove("GIT_DIR")
        .env_remove("GIT_WORK_TREE")
        .output()
        .expect("git");
    assert!(
        output.status.success(),
        "git {args:?}\n{}",
        String::from_utf8_lossy(&output.stderr)
    );
    output
}

fn git_text(args: &[&str]) -> String {
    String::from_utf8(git(args).stdout)
        .unwrap()
        .trim()
        .to_string()
}

fn repo_fixture(sb: &Sandbox) -> Repo {
    let work = sb.root.join("work");
    write_package(&work);
    fs::write(work.join("README"), b"one\n").unwrap();
    fs::write(work.join(".gitignore"), b".local-note\n").unwrap();
    let work_s = p(&work);
    git(&["init", "-q", "-b", "main", &work_s]);
    git(&["-C", &work_s, "add", "-A"]);
    git(&[
        "-C",
        &work_s,
        "-c",
        "user.email=omh@test.invalid",
        "-c",
        "user.name=omh test",
        "commit",
        "-q",
        "-m",
        "one",
    ]);
    git(&["-C", &work_s, "tag", "v0.1.0"]);
    fs::write(work.join("README"), b"two\n").unwrap();
    git(&["-C", &work_s, "add", "README"]);
    git(&[
        "-C",
        &work_s,
        "-c",
        "user.email=omh@test.invalid",
        "-c",
        "user.name=omh test",
        "commit",
        "-q",
        "-m",
        "two",
    ]);
    git(&["-C", &work_s, "tag", "v0.2.0"]);
    let bare = sb.root.join("repo.git");
    let bare_s = p(&bare);
    git(&["clone", "--quiet", "--bare", &work_s, &bare_s]);
    let sha1 = git_text(&["-C", &bare_s, "rev-parse", "v0.1.0^{}"]);
    let sha2 = git_text(&["-C", &bare_s, "rev-parse", "v0.2.0^{}"]);
    let ref1 = sb.root.join("v0.1.0.ref");
    let ref2 = sb.root.join("v0.2.0.ref");
    fs::write(&ref1, format!("  {sha1}\n\n")).unwrap();
    fs::write(&ref2, format!("\n{sha2} \n")).unwrap();
    Repo {
        bare,
        sha1,
        sha2,
        ref1,
        ref2,
    }
}

fn seed_clone(sb: &Sandbox, repo: &Repo, tag: &str) {
    let dest = p(&sb.home.join("repo"));
    let bare = p(&repo.bare);
    git(&["clone", "--quiet", "--branch", tag, &bare, &dest]);
}

fn write_git_wrapper(dir: &Path) {
    fs::create_dir_all(dir).unwrap();
    let path = dir.join("git");
    fs::write(
        &path,
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$OMH_GIT_TRACE\"\nif [ \"$OMH_GIT_FAIL_CLONE\" = 1 ]; then\n  for arg in \"$@\"; do\n    if [ \"$arg\" = clone ]; then exit 1; fi\n  done\nfi\nexec /usr/bin/git \"$@\"\n",
    )
    .unwrap();
    mode_set(&path, 0o755);
}

fn content_path(sb: &Sandbox) -> String {
    let wrap = sb.root.join("wrap");
    write_git_wrapper(&wrap);
    format!("{}:/usr/bin:/bin", wrap.display())
}

fn write_uv(dir: &Path) {
    fs::create_dir_all(dir).unwrap();
    let path = dir.join("uv");
    fs::write(
        &path,
        r#"#!/bin/sh
{
  printf 'cwd=%s\n' "$(pwd)"
  printf 'argv=%s\n' "$*"
  printf 'UV_NO_PROJECT=%s\n' "$UV_NO_PROJECT"
  printf 'UV_PYTHON_DOWNLOADS=%s\n' "$UV_PYTHON_DOWNLOADS"
  printf 'UV_PYTHON_PREFERENCE=%s\n' "$UV_PYTHON_PREFERENCE"
  if [ -n "${VIRTUAL_ENV+x}" ]; then printf 'VIRTUAL_ENV=%s\n' "$VIRTUAL_ENV"; else printf 'VIRTUAL_ENV=unset\n'; fi
  if [ -n "${UV_PROJECT_ENVIRONMENT+x}" ]; then printf 'UV_PROJECT_ENVIRONMENT=%s\n' "$UV_PROJECT_ENVIRONMENT"; else printf 'UV_PROJECT_ENVIRONMENT=unset\n'; fi
} >> "$OMH_UV_LOG"
if [ -n "$OMH_UV_CODE" ]; then
  exit "$OMH_UV_CODE"
fi
printf '%s\n' "$OMH_UV_PRINT"
"#,
    )
    .unwrap();
    mode_set(&path, 0o755);
}

fn write_stamps(dir: &Path) {
    fs::create_dir_all(dir).unwrap();
    let script = "#!/bin/sh\necho \"$0 $*\" >> \"$OMH_STAMP\"\nexit 1\n";
    for name in ["python", "python3", "py", "uv"] {
        let path = dir.join(name);
        fs::write(&path, script).unwrap();
        mode_set(&path, 0o755);
    }
}

fn marker_bytes() -> Vec<u8> {
    format!("#!/bin/sh\n{MARKER}\nexec true\n").into_bytes()
}

fn write_shim_json(home: &Path, dest: &Path) {
    fs::write(
        home.join("shim.json"),
        serde_json::to_vec(&json!({"path": p(dest)})).unwrap(),
    )
    .unwrap();
}

fn harness_files(sb: &Sandbox) {
    fs::create_dir_all(sb.home.join("repo")).unwrap();
    fs::write(sb.home.join("repo/README"), b"keep-repo\n").unwrap();
    fs::create_dir_all(sb.home.join("runtimes/workflow")).unwrap();
    fs::write(sb.home.join("runtimes/workflow/python"), b"venv\n").unwrap();
    fs::create_dir_all(sb.home.join("transactions")).unwrap();
    fs::write(sb.home.join("transactions/journal.json"), b"{}\n").unwrap();
    fs::write(sb.home.join(".omh-owner.json"), b"{}\n").unwrap();
    fs::write(sb.home.join("targets.json"), b"{}\n").unwrap();
    fs::create_dir_all(sb.user.join(".codex/skills")).unwrap();
    fs::write(sb.user.join(".codex/skills/keep.txt"), b"keep\n").unwrap();
}

fn assert_harness_files(sb: &Sandbox) {
    assert_eq!(
        fs::read(sb.home.join("repo/README")).unwrap(),
        b"keep-repo\n"
    );
    assert_eq!(
        fs::read(sb.home.join("runtimes/workflow/python")).unwrap(),
        b"venv\n"
    );
    assert_eq!(
        fs::read(sb.home.join("transactions/journal.json")).unwrap(),
        b"{}\n"
    );
    assert_eq!(fs::read(sb.home.join(".omh-owner.json")).unwrap(), b"{}\n");
    assert_eq!(fs::read(sb.home.join("targets.json")).unwrap(), b"{}\n");
    assert_eq!(
        fs::read(sb.user.join(".codex/skills/keep.txt")).unwrap(),
        b"keep\n"
    );
}

fn dest_of(sb: &Sandbox) -> PathBuf {
    sb.bin.join("omh")
}

#[test]
fn binary_image_excludes_retired_exporter_and_strategy() {
    let bytes = fs::read(bin()).unwrap();
    for needle in [
        b"omh.omh".as_slice(),
        b"omh.lock.json",
        b"--copies",
        b"--symlinks",
        b"uv python install",
    ] {
        assert!(
            bytes.windows(needle.len()).all(|window| window != needle),
            "binary contains {}",
            String::from_utf8_lossy(needle)
        );
    }
}

#[test]
fn usage_errors_exit_2() {
    let sb = sandbox();
    assert_usage(&invoke(&sb, &[], &[], None), "a command is required");
    assert_usage(
        &invoke(&sb, &["self"], &[], None),
        "omh self requires install, update, or uninstall",
    );
    assert_usage(
        &invoke(&sb, &["self", "uninstall", "claude"], &[], None),
        "unrecognized arguments",
    );
    assert_usage(
        &invoke(&sb, &["self", "--json", "uninstall"], &[], None),
        "unrecognized arguments",
    );
    assert_usage(
        &invoke(&sb, &["nosuch"], &[], None),
        "unrecognized command: nosuch",
    );
    assert_usage(
        &invoke(&sb, &["self", "install", "extra"], &[], None),
        "unrecognized arguments: extra",
    );
    assert!(!sb.home.join("manager.json").exists());
}

#[test]
fn self_install_records_the_pin_and_a_second_run_changes_nothing() {
    let sb = sandbox();
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let python = p(base_python());
    let output = invoke(
        &sb,
        &install_args(&home, &bin_dir, &python),
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    );
    assert_ok(&output);
    assert!(output.stdout.is_empty(), "{}", show(&output));
    let dest = dest_of(&sb);
    let installed = fs::read(&dest).unwrap();
    assert_eq!(installed, fs::read(bin()).unwrap());
    assert_eq!(unix_mode(&dest), 0o755);
    assert_record_shape(&sb);
    let value = record(&sb);
    assert_eq!(value["schemaVersion"], 1);
    assert_eq!(value["kind"], "binary");
    assert_eq!(value["binDir"], bin_dir);
    assert_eq!(value["path"], p(&dest));
    assert_eq!(value["source"], p(&sb.home.join("repo")));
    assert_eq!(value["python"], python);
    assert_eq!(
        value["pythonDigest"],
        sha256(&fs::read(base_python()).unwrap())
    );
    assert_eq!(value["digest"], sha256(&installed));
    assert_eq!(value["binaryVersion"], "1.2.3");
    assert!(!sb.user.join(".local/bin/omh").exists());
    assert!(!sb.home.join("repo").exists());
    assert_no_locks(&sb);
    let file_ino = inode(&dest);
    let record_ino = inode(&sb.home.join("manager.json"));
    let record_bytes = fs::read(sb.home.join("manager.json")).unwrap();
    let again = invoke(
        &sb,
        &install_args(&home, &bin_dir, &python),
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    );
    assert_ok(&again);
    assert_eq!(inode(&dest), file_ino);
    assert_eq!(inode(&sb.home.join("manager.json")), record_ino);
    assert_eq!(
        fs::read(sb.home.join("manager.json")).unwrap(),
        record_bytes
    );

    let other = sb.root.join("other-source");
    let other_s = p(&other);
    let mut args = install_args(&home, &bin_dir, &python);
    args.extend(["--source", &other_s]);
    assert_ok(&invoke(
        &sb,
        &args,
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    ));
    assert_eq!(inode(&dest), file_ino);
    assert_eq!(record(&sb)["source"], other_s);
    assert_ne!(inode(&sb.home.join("manager.json")), record_ino);
}

#[test]
fn self_install_uv_query_is_constrained_and_rejects_a_venv() {
    let sb = sandbox();
    let tools = sb.root.join("tools");
    write_uv(&tools);
    fs::create_dir_all(sb.root.join("decoy")).unwrap();
    let log = sb.root.join("uv.log");
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let path = format!("{}:/usr/bin:/bin", tools.display());
    let venv = sb.root.join("venv");
    let created = Command::new(base_python())
        .args(["-m", "venv", &p(&venv)])
        .output()
        .unwrap();
    assert!(
        created.status.success(),
        "{}",
        String::from_utf8_lossy(&created.stderr)
    );
    let venv_python = venv.join("bin/python");

    let output = invoke(
        &sb,
        &["self", "install", "--home", &home, "--bin-dir", &bin_dir],
        &[
            ("OMH_UV_LOG", &p(&log)),
            ("OMH_UV_PRINT", &p(base_python())),
            ("OMH_PYTHON", ""),
            ("VIRTUAL_ENV", &p(&venv)),
            ("UV_PROJECT_ENVIRONMENT", &p(&venv)),
            ("OMH_BINARY_VERSION", "9.9.9"),
        ],
        Some(&path),
    );
    assert_ok(&output);
    let text = fs::read_to_string(&log).unwrap();
    assert!(
        text.contains("argv=python find --no-project --python-preference only-managed --no-python-downloads\n"),
        "{text}"
    );
    assert!(text.contains("UV_NO_PROJECT=1\n"), "{text}");
    assert!(text.contains("UV_PYTHON_DOWNLOADS=never\n"), "{text}");
    assert!(
        text.contains("UV_PYTHON_PREFERENCE=only-managed\n"),
        "{text}"
    );
    assert!(text.contains("VIRTUAL_ENV=unset\n"), "{text}");
    assert!(text.contains("UV_PROJECT_ENVIRONMENT=unset\n"), "{text}");
    let cwd = text.lines().find(|line| line.starts_with("cwd=")).unwrap();
    assert!(cwd.contains("omh-pin-"), "{text}");
    assert!(!cwd.contains("decoy"), "{text}");
    assert!(!text.contains("python install"), "{text}");
    assert_eq!(record(&sb)["python"], p(base_python()));
    assert_eq!(record(&sb)["binaryVersion"], "9.9.9");

    let live = sandbox();
    let uv_dir = uv_binary().parent().unwrap().to_path_buf();
    let live_path = format!(
        "{}:{}",
        uv_dir.display(),
        std::env::var("PATH").unwrap_or_else(|_| "/usr/bin:/bin".into())
    );
    let live_home = p(&live.home);
    let live_bin = p(&live.bin);
    let live_out = invoke(
        &live,
        &[
            "self",
            "install",
            "--home",
            &live_home,
            "--bin-dir",
            &live_bin,
        ],
        &[
            ("VIRTUAL_ENV", &p(&venv)),
            ("UV_PROJECT_ENVIRONMENT", &p(&venv)),
            ("UV_PYTHON_INSTALL_DIR", &uv_python_dir()),
        ],
        Some(&live_path),
    );
    assert_ok(&live_out);
    assert_eq!(record(&live)["python"], p(base_python()));
    assert_ne!(record(&live)["python"], p(&venv_python));

    let printed = sandbox();
    let log2 = printed.root.join("uv.log");
    let home2 = p(&printed.home);
    let bin2 = p(&printed.bin);
    let rejected = invoke(
        &printed,
        &["self", "install", "--home", &home2, "--bin-dir", &bin2],
        &[
            ("OMH_UV_LOG", &p(&log2)),
            ("OMH_UV_PRINT", &p(&venv_python)),
        ],
        Some(&path),
    );
    assert_err(
        &rejected,
        "HARNESS_PYTHON_REQUIRED",
        "Explicit Python is not a base interpreter",
    );
    assert!(!printed.home.join("manager.json").exists());
    assert!(!printed.bin.join("omh").exists());

    let direct = sandbox();
    let home3 = p(&direct.home);
    let bin3 = p(&direct.bin);
    let py = p(&venv_python);
    let output = invoke(&direct, &install_args(&home3, &bin3, &py), &[], None);
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Explicit Python is not a base interpreter",
    );
    assert!(!direct.home.join("manager.json").exists());
    assert!(!direct.bin.join("omh").exists());
}

#[test]
fn self_install_rejects_bad_interpreters_without_writing() {
    let sb = sandbox();
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let stamps = sb.root.join("stamps");
    write_stamps(&stamps);
    let stamp = sb.root.join("stamp");
    let path = format!("{}:/usr/bin:/bin", stamps.display());
    let stamp_s = p(&stamp);

    let missing = sb.root.join("missing-python");
    let missing_s = p(&missing);
    let output = invoke(
        &sb,
        &install_args(&home, &bin_dir, &missing_s),
        &[("OMH_STAMP", &stamp_s)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Explicit Python is missing",
    );
    assert!(!stamp.exists());
    assert!(!sb.home.join("manager.json").exists());

    let locked = sb.root.join("locked-python");
    fs::write(&locked, b"#!/bin/sh\nexit 0\n").unwrap();
    mode_set(&locked, 0o644);
    let locked_s = p(&locked);
    let output = invoke(
        &sb,
        &install_args(&home, &bin_dir, &locked_s),
        &[("OMH_STAMP", &stamp_s)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Cannot execute explicit Python",
    );
    assert!(!sb.home.join("manager.json").exists());

    let old = sb.root.join("old-python");
    fs::write(&old, "#!/bin/sh\nprintf '%s\\n' '{\"version\":[3,10],\"prefix\":\"/opt/old\",\"base_prefix\":\"/opt/old\"}'\n").unwrap();
    mode_set(&old, 0o755);
    let old_s = p(&old);
    let output = invoke(&sb, &install_args(&home, &bin_dir, &old_s), &[], None);
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Python 3.11 or newer is required",
    );

    let dead = sb.root.join("dead-python");
    fs::write(&dead, "#!/bin/sh\nexit 1\n").unwrap();
    mode_set(&dead, 0o755);
    let dead_s = p(&dead);
    let output = invoke(&sb, &install_args(&home, &bin_dir, &dead_s), &[], None);
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Cannot execute explicit Python",
    );

    let output = invoke(
        &sb,
        &install_args(&home, &bin_dir, "python3"),
        &[("OMH_STAMP", &stamp_s)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_RUNTIME_SPEC",
        "An absolute, control-free path is required",
    );
    assert!(!stamp.exists());

    let weird = format!("/tmp/omh-bad\npath-{}", std::process::id());
    let output = invoke(
        &sb,
        &[
            "self",
            "install",
            "--home",
            &home,
            "--bin-dir",
            &bin_dir,
            "--python",
            &weird,
        ],
        &[],
        None,
    );
    assert_err(
        &output,
        "HARNESS_RUNTIME_SPEC",
        "An absolute, control-free path is required",
    );

    let tools = sb.root.join("tools");
    write_uv(&tools);
    let log = sb.root.join("uv.log");
    let uv_path = format!("{}:/usr/bin:/bin", tools.display());
    let skipped = invoke(
        &sb,
        &["self", "install", "--home", &home, "--bin-dir", &bin_dir],
        &[
            ("OMH_UV_LOG", &p(&log)),
            ("OMH_UV_CODE", "1"),
            ("OMH_PYTHON", "relative/python"),
        ],
        Some(&uv_path),
    );
    assert_err(
        &skipped,
        "HARNESS_RUNTIME_SPEC",
        "An absolute, control-free path is required",
    );
    assert!(!log.exists());

    let no_uv = invoke(
        &sb,
        &["self", "install", "--home", &home, "--bin-dir", &bin_dir],
        &[("OMH_STAMP", &stamp_s)],
        Some("/usr/bin:/bin"),
    );
    assert_err(
        &no_uv,
        "HARNESS_PYTHON_REQUIRED",
        "uv is required to pin a managed interpreter",
    );
    assert!(!stamp.exists());
    assert!(!sb.home.join("manager.json").exists());

    let empty = invoke(
        &sb,
        &["self", "install", "--home", &home, "--bin-dir", &bin_dir],
        &[("OMH_UV_LOG", &p(&log)), ("OMH_UV_PRINT", "")],
        Some(&uv_path),
    );
    assert_err(
        &empty,
        "HARNESS_PYTHON_REQUIRED",
        "Explicit Python is missing",
    );

    let relative_bin = invoke(
        &sb,
        &[
            "self",
            "install",
            "--home",
            &home,
            "--bin-dir",
            "relative-bin",
            "--python",
            &p(base_python()),
        ],
        &[
            ("OMH_UV_LOG", &p(&sb.root.join("unused-uv.log"))),
            ("OMH_UV_CODE", "1"),
        ],
        Some(&uv_path),
    );
    assert_err(
        &relative_bin,
        "HARNESS_RUNTIME_SPEC",
        "An absolute, control-free path is required",
    );
    assert!(!sb.home.join("manager.json").exists());
}

#[test]
fn self_install_migrates_a_recorded_v1_shim_and_rejects_unowned() {
    let sb = sandbox();
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let python = p(base_python());
    let dest = dest_of(&sb);
    let unowned = b"not-the-binary\n";
    fs::write(&dest, unowned).unwrap();
    let output = invoke(&sb, &install_args(&home, &bin_dir, &python), &[], None);
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest.display()),
    );
    assert_eq!(fs::read(&dest).unwrap(), unowned);
    assert!(!sb.home.join("manager.json").exists());

    fs::write(&dest, marker_bytes()).unwrap();
    let output = invoke(&sb, &install_args(&home, &bin_dir, &python), &[], None);
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest.display()),
    );
    assert_eq!(fs::read(&dest).unwrap(), marker_bytes());
    assert!(!sb.home.join("manager.json").exists());

    write_shim_json(&sb.home, &dest);
    fs::write(&dest, b"nope\n").unwrap();
    let output = invoke(&sb, &install_args(&home, &bin_dir, &python), &[], None);
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest.display()),
    );
    assert!(sb.home.join("shim.json").is_file());
    assert!(!sb.home.join("manager.json").exists());

    fs::remove_file(&dest).unwrap();
    let output = invoke(&sb, &install_args(&home, &bin_dir, &python), &[], None);
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest.display()),
    );
    assert!(!dest.exists());
    assert!(!sb.home.join("manager.json").exists());

    let crlf = format!("#!/bin/sh\n{MARKER}\r\n");
    fs::write(&dest, crlf.as_bytes()).unwrap();
    let output = invoke(&sb, &install_args(&home, &bin_dir, &python), &[], None);
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest.display()),
    );
    assert_eq!(fs::read(&dest).unwrap(), crlf.as_bytes());

    harness_files(&sb);
    fs::write(&dest, marker_bytes()).unwrap();
    write_shim_json(&sb.home, &dest);
    let output = invoke(
        &sb,
        &install_args(&home, &bin_dir, &python),
        &[("OMH_BINARY_VERSION", "3.0.0")],
        None,
    );
    assert_ok(&output);
    assert!(!sb.home.join("shim.json").exists());
    assert_eq!(fs::read(&dest).unwrap(), fs::read(bin()).unwrap());
    assert_eq!(record(&sb)["digest"], sha256(&fs::read(&dest).unwrap()));
    assert_eq!(record(&sb)["binaryVersion"], "3.0.0");
    assert_harness_files(&sb);
    let file_ino = inode(&dest);
    let record_ino = inode(&sb.home.join("manager.json"));
    assert_ok(&invoke(
        &sb,
        &install_args(&home, &bin_dir, &python),
        &[("OMH_BINARY_VERSION", "3.0.0")],
        None,
    ));
    assert_eq!(inode(&dest), file_ino);
    assert_eq!(inode(&sb.home.join("manager.json")), record_ino);
    assert_no_locks(&sb);
}

#[test]
fn self_install_refuses_a_second_bin_directory_while_the_binary_remains() {
    let sb = sandbox();
    let home = p(&sb.home);
    let python = p(base_python());
    let first = p(&sb.bin);
    assert_ok(&invoke(
        &sb,
        &install_args(&home, &first, &python),
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    ));
    let dest = dest_of(&sb);
    let original = fs::read(&dest).unwrap();
    let other = sb.root.join("other-bin");
    let other_s = p(&other);
    let output = invoke(
        &sb,
        &install_args(&home, &other_s, &python),
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    );
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!(
            "Owned omh command is already installed at {}; run omh self uninstall before choosing another bin directory",
            dest.display()
        ),
    );
    assert_eq!(fs::read(&dest).unwrap(), original);
    assert!(!other.join("omh").exists());
    assert_eq!(record(&sb)["path"], p(&dest));

    fs::write(&dest, b"changed-bytes").unwrap();
    let output = invoke(
        &sb,
        &install_args(&home, &other_s, &python),
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    );
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest.display()),
    );
    assert_eq!(fs::read(&dest).unwrap(), b"changed-bytes");
    assert!(!other.join("omh").exists());

    fs::remove_file(&dest).unwrap();
    assert_ok(&invoke(
        &sb,
        &install_args(&home, &other_s, &python),
        &[("OMH_BINARY_VERSION", "1.2.3")],
        None,
    ));
    assert!(!dest.exists());
    assert_eq!(
        fs::read(other.join("omh")).unwrap(),
        fs::read(bin()).unwrap()
    );
    assert_eq!(record(&sb)["path"], p(&other.join("omh")));
}

#[test]
fn self_update_checks_the_checksum_before_replacing_bytes() {
    let sb = sandbox();
    harness_files(&sb);
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let python = p(base_python());
    assert_ok(&invoke(
        &sb,
        &install_args(&home, &bin_dir, &python),
        &[("OMH_BINARY_VERSION", "1.0.0")],
        None,
    ));
    let dest = dest_of(&sb);
    let before = fs::read(&dest).unwrap();
    let before_record = record(&sb);
    let file_ino = inode(&dest);
    let bad = sb.root.join("bad.bin");
    fs::write(&bad, b"replacement-bytes").unwrap();
    let output = invoke(
        &sb,
        &["self", "update", "--home", &home],
        &[
            ("OMH_BINARY_FILE", &p(&bad)),
            ("OMH_BINARY_SHA256", "abcd"),
            ("OMH_VERSION", "9.9.9"),
        ],
        None,
    );
    assert_err(&output, "OMH_INVALID", "binary checksum does not match");
    assert_eq!(inode(&dest), file_ino);
    assert_eq!(fs::read(&dest).unwrap(), before);
    assert_eq!(record(&sb)["digest"], before_record["digest"]);
    assert_eq!(record(&sb)["pythonDigest"], before_record["pythonDigest"]);
    assert_harness_files(&sb);

    let sum = sha256(b"replacement-bytes");
    assert_ok(&invoke(
        &sb,
        &["self", "update", "--home", &home, "--to", "4.0.0"],
        &[
            ("OMH_BINARY_FILE", &p(&bad)),
            ("OMH_BINARY_SHA256", &sum.to_ascii_uppercase()),
            ("OMH_BINARY_VERSION", "should-not-win"),
            ("OMH_VERSION", "9.9.9"),
            ("OMH_BINARY_URL", "http://127.0.0.1:1/nope"),
        ],
        None,
    ));
    assert_ne!(inode(&dest), file_ino);
    assert_eq!(fs::read(&dest).unwrap(), b"replacement-bytes");
    let updated = record(&sb);
    assert_eq!(updated["digest"], sum);
    assert_eq!(updated["binaryVersion"], "4.0.0");
    assert_eq!(updated["python"], before_record["python"]);
    assert_eq!(updated["pythonDigest"], before_record["pythonDigest"]);
    assert_eq!(updated["source"], before_record["source"]);
    assert_harness_files(&sb);

    let same = sb.root.join("same.bin");
    fs::write(&same, b"replacement-bytes").unwrap();
    let same_ino = inode(&dest);
    assert_ok(&invoke(
        &sb,
        &["self", "update", "--home", &home],
        &[
            ("OMH_BINARY_FILE", &p(&same)),
            ("OMH_BINARY_SHA256", &sum),
            ("OMH_VERSION", "8.8.8"),
        ],
        None,
    ));
    assert_eq!(inode(&dest), same_ino);
    assert_eq!(record(&sb)["digest"], sum);
    assert_eq!(record(&sb)["binaryVersion"], "4.0.0");

    fs::remove_file(&dest).unwrap();
    let placed = sb.root.join("placed.bin");
    fs::write(&placed, b"placed-bytes").unwrap();
    let placed_sum = sha256(b"placed-bytes");
    assert_ok(&invoke(
        &sb,
        &["self", "update", "--home", &home, "--to", "5.0.0"],
        &[
            ("OMH_BINARY_FILE", &p(&placed)),
            ("OMH_BINARY_SHA256", &placed_sum),
        ],
        None,
    ));
    assert_eq!(fs::read(&dest).unwrap(), b"placed-bytes");
    assert_eq!(record(&sb)["digest"], placed_sum);
    assert_eq!(record(&sb)["binaryVersion"], "5.0.0");
    assert_eq!(record(&sb)["pythonDigest"], before_record["pythonDigest"]);

    let conflict = sandbox();
    let home_c = p(&conflict.home);
    let bin_c = p(&conflict.bin);
    assert_ok(&invoke(
        &conflict,
        &install_args(&home_c, &bin_c, &python),
        &[("OMH_BINARY_VERSION", "1.0.0")],
        None,
    ));
    let dest_c = dest_of(&conflict);
    let owned = fs::read(&dest_c).unwrap();
    fs::write(&dest_c, b"neither").unwrap();
    let third = conflict.root.join("third.bin");
    fs::write(&third, b"third-payload").unwrap();
    let third_sum = sha256(b"third-payload");
    let output = invoke(
        &conflict,
        &["self", "update", "--home", &home_c],
        &[
            ("OMH_BINARY_FILE", &p(&third)),
            ("OMH_BINARY_SHA256", &third_sum),
        ],
        None,
    );
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest_c.display()),
    );
    assert_eq!(fs::read(&dest_c).unwrap(), b"neither");
    assert_eq!(record(&conflict)["digest"], sha256(&owned));
    let trace = conflict.root.join("trace");
    let forwarded = invoke(
        &conflict,
        &["install", "--home", &home_c],
        &[
            ("OMH_TRACE", &p(&trace)),
            ("OMH_STAMP", &p(&conflict.root.join("stamp"))),
        ],
        Some(&format!("{}:/usr/bin:/bin", {
            write_stamps(&conflict.root.join("stamps"));
            conflict.root.join("stamps").display()
        })),
    );
    assert_err(
        &forwarded,
        "HARNESS_CONFLICT",
        &format!(
            "Recorded omh command does not match manager.json: {}",
            dest_c.display()
        ),
    );
    assert!(!trace.exists());
    assert!(!conflict.root.join("stamp").exists());
    assert_eq!(fs::read(&dest_c).unwrap(), b"neither");
    let output = invoke(
        &conflict,
        &["self", "uninstall", "--home", &home_c],
        &[],
        None,
    );
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!("Unowned omh command exists: {}", dest_c.display()),
    );
    assert_eq!(fs::read(&dest_c).unwrap(), b"neither");
    assert!(conflict.home.join("manager.json").is_file());

    let missing = sandbox();
    let payload = missing.root.join("payload.bin");
    fs::write(&payload, b"payload").unwrap();
    let output = invoke(
        &missing,
        &["self", "update", "--home", &p(&missing.home)],
        &[
            ("OMH_BINARY_FILE", &p(&payload)),
            ("OMH_BINARY_SHA256", &sha256(b"payload")),
        ],
        None,
    );
    assert_err(
        &output,
        "OMH_ENVIRONMENT_INVALID",
        "manager.json is missing",
    );
    assert!(!missing.home.join("manager.json").exists());

    let bare = sandbox();
    assert_ok(&invoke(
        &bare,
        &install_args(&p(&bare.home), &p(&bare.bin), &python),
        &[("OMH_BINARY_VERSION", "1.0.0")],
        None,
    ));
    let output = invoke(
        &bare,
        &["self", "update", "--home", &p(&bare.home)],
        &[],
        None,
    );
    assert_err(
        &output,
        "OMH_INVALID",
        "no binary payload: set OMH_BINARY_FILE or OMH_BINARY_URL",
    );
    let output = invoke(
        &bare,
        &["self", "update", "--home", &p(&bare.home)],
        &[("OMH_BINARY_FILE", &p(&payload))],
        None,
    );
    assert_err(&output, "OMH_INVALID", "OMH_BINARY_SHA256 is required");
    assert_eq!(fs::read(dest_of(&bare)).unwrap(), fs::read(bin()).unwrap());
}

#[test]
fn self_uninstall_matches_run_self_and_leaves_harness_files() {
    let sb = sandbox();
    harness_files(&sb);
    let home = p(&sb.home);
    let bin_dir = p(&sb.bin);
    let python = p(base_python());
    assert_ok(&invoke(
        &sb,
        &install_args(&home, &bin_dir, &python),
        &[("OMH_BINARY_VERSION", "1.0.0")],
        None,
    ));
    let removed = invoke(&sb, &["self", "uninstall", "--home", &home], &[], None);
    assert_ok(&removed);
    assert_eq!(
        String::from_utf8(removed.stdout).unwrap(),
        "removed the omh command\n"
    );
    assert!(!dest_of(&sb).exists());
    assert!(!sb.home.join("manager.json").exists());
    assert_harness_files(&sb);
    let again = invoke(
        &sb,
        &["self", "uninstall", "--home", &home, "--json"],
        &[],
        None,
    );
    assert_ok(&again);
    assert_eq!(
        String::from_utf8(again.stdout).unwrap(),
        "{\"removed\": false}\n"
    );
    assert_harness_files(&sb);

    let json_sb = sandbox();
    let home_j = p(&json_sb.home);
    assert_ok(&invoke(
        &json_sb,
        &install_args(&home_j, &p(&json_sb.bin), &python),
        &[("OMH_BINARY_VERSION", "1.0.0")],
        None,
    ));
    let removed = invoke(
        &json_sb,
        &["self", "uninstall", "--json", "--home", &home_j],
        &[],
        None,
    );
    assert_ok(&removed);
    assert_eq!(
        String::from_utf8(removed.stdout).unwrap(),
        "{\"removed\": true}\n"
    );
    assert!(!dest_of(&json_sb).exists());

    let gone = sandbox();
    let home_g = p(&gone.home);
    assert_ok(&invoke(
        &gone,
        &install_args(&home_g, &p(&gone.bin), &python),
        &[("OMH_BINARY_VERSION", "1.0.0")],
        None,
    ));
    fs::remove_file(dest_of(&gone)).unwrap();
    let removed = invoke(&gone, &["self", "uninstall", "--home", &home_g], &[], None);
    assert_ok(&removed);
    assert_eq!(
        String::from_utf8(removed.stdout).unwrap(),
        "no omh command to remove\n"
    );
    assert!(!gone.home.join("manager.json").exists());

    let stray = sandbox();
    fs::write(stray.bin.join("omh"), b"stray").unwrap();
    let removed = invoke(
        &stray,
        &["self", "uninstall", "--home", &p(&stray.home)],
        &[],
        None,
    );
    assert_ok(&removed);
    assert_eq!(
        String::from_utf8(removed.stdout).unwrap(),
        "no omh command to remove\n"
    );
    assert_eq!(fs::read(stray.bin.join("omh")).unwrap(), b"stray");

    fs::write(gone.home.join("manager.json"), b"{}\n").unwrap();
    let output = invoke(
        &gone,
        &["self", "uninstall", "--home", &p(&gone.home)],
        &[],
        None,
    );
    assert_err(
        &output,
        "OMH_INVALID",
        "manager.json is not a binary manager record",
    );
    assert!(gone.home.join("manager.json").is_file());
}

#[test]
fn forward_respects_the_real_python_cli_grammar() {
    let sb = sandbox();
    let source = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    install_managed(&sb, Some(source));
    let home = p(&sb.home);
    let skills = p(&sb.user.join(".codex/skills"));
    let python = p(base_python());
    for command in ["prepare", "plan", "install", "status", "recover", "refresh", "uninstall"] {
        let mut args = vec![command, "--home", &home, "--python", &python, "--json"];
        if command != "prepare" {
            args.extend(["--skills-root", &skills]);
        }
        if matches!(command, "prepare" | "install" | "refresh") {
            args.push("--offline");
        }
        let result = invoke(&sb, &args, &[], None);
        assert!(result.status.success(), "{command}: {}", show(&result));
        assert!(serde_json::from_slice::<Value>(&result.stdout).is_ok(), "{command}: {}", show(&result));
    }
    assert!(!sb.user.join(".codex/.omh-owner.json").exists());
}

#[test]
fn forward_execs_the_pin_and_clears_only_the_scratch_shim() {
    let sb = sandbox();
    let package = sb.root.join("package");
    write_package(&package);
    install_managed(&sb, Some(&package));
    let home = p(&sb.home);
    let public = sb.root.join("public-bin");
    let public_s = p(&public);
    let scratch = sb.home.join(".manager-bin");
    let record_bytes = fs::read(sb.home.join("manager.json")).unwrap();
    let binary_bytes = fs::read(dest_of(&sb)).unwrap();
    let skills = p(&sb.user.join(".codex/skills"));
    fs::create_dir_all(sb.user.join(".codex/skills")).unwrap();
    fs::write(sb.user.join(".codex/skills/keep.txt"), b"keep\n").unwrap();

    for command in [
        "install",
        "refresh",
        "uninstall",
        "prepare",
        "plan",
        "status",
        "recover",
    ] {
        for code in [0, 1, 2] {
            let trace = sb.root.join(format!("trace-{command}-{code}"));
            let _ = fs::remove_file(&trace);
            let code_s = code.to_string();
            let mut args = vec![
                command,
                "--home",
                home.as_str(),
                "--skills-root",
                skills.as_str(),
            ];
            if command == "install" || command == "refresh" {
                args.extend(["--bin-dir", public_s.as_str()]);
            }
            let output = invoke(
                &sb,
                &args,
                &[
                    ("OMH_TRACE", &p(&trace)),
                    ("OMH_CHILD_CODE", &code_s),
                    ("OMH_PYTHON", ""),
                ],
                None,
            );
            assert_eq!(
                output.status.code(),
                Some(code),
                "{command} {code}: {}",
                show(&output)
            );
            let err = String::from_utf8_lossy(&output.stderr);
            assert!(!err.contains("\"error\""), "{command} {code}: {err}");
            let rows = read_trace(&trace);
            assert_eq!(rows.len(), 1, "{command} {code}");
            assert_child_launch(&rows[0], command, &package);
            if matches!(command, "prepare" | "install" | "refresh") {
                assert_eq!(argv_flag(&rows[0], "--python"), p(base_python()));
            } else {
                assert!(!rows[0]["argv"].as_array().unwrap().iter().any(|item| item == "--python"));
            }
            let bin_flags = rows[0]["argv"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|item| *item == "--bin-dir")
                .count();
            if command == "install" || command == "refresh" {
                assert_eq!(bin_flags, 1);
                assert_eq!(argv_flag(&rows[0], "--bin-dir"), p(&scratch));
                assert!(!rows[0]["argv"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|item| item == public_s.as_str()));
            } else {
                assert_eq!(bin_flags, 0, "{command}");
            }
            assert_eq!(
                fs::read(sb.home.join("manager.json")).unwrap(),
                record_bytes
            );
            assert_eq!(fs::read(dest_of(&sb)).unwrap(), binary_bytes);
            assert!(!public.join("omh").exists());
            assert!(!sb.user.join(".local/bin/omh").exists());
            assert_eq!(
                fs::read(sb.user.join(".codex/skills/keep.txt")).unwrap(),
                b"keep\n"
            );
        }
    }
    assert_no_locks(&sb);

    let trace = sb.root.join("shim-trace");
    let output = invoke(
        &sb,
        &["install", "--home", &home, "--bin-dir", &public_s],
        &[
            ("OMH_TRACE", &p(&trace)),
            ("OMH_WRITE_SHIM", "1"),
            ("OMH_CHILD_CODE", "1"),
        ],
        None,
    );
    assert_eq!(output.status.code(), Some(1), "{}", show(&output));
    assert!(!scratch.join("omh").exists());
    assert!(!sb.home.join("shim.json").exists());
    assert!(!public.join("omh").exists());
    assert_eq!(
        fs::read(sb.home.join("manager.json")).unwrap(),
        record_bytes
    );

    let elsewhere = sb.root.join("elsewhere/omh");
    fs::create_dir_all(scratch.clone()).unwrap();
    fs::write(scratch.join("omh"), marker_bytes()).unwrap();
    fs::write(scratch.join("omh-note"), b"not a shim\n").unwrap();
    write_shim_json(&sb.home, &elsewhere);
    let kept = fs::read(sb.home.join("shim.json")).unwrap();
    assert_ok(&invoke(
        &sb,
        &["refresh", "--home", &home],
        &[("OMH_TRACE", &p(&sb.root.join("refresh-trace")))],
        None,
    ));
    assert!(!scratch.join("omh").exists());
    assert_eq!(fs::read(scratch.join("omh-note")).unwrap(), b"not a shim\n");
    assert_eq!(fs::read(sb.home.join("shim.json")).unwrap(), kept);

    let other = sb.root.join("other-package");
    write_package(&other);
    let other_s = p(&other);
    assert_ok(&invoke(
        &sb,
        &["status", "--home", &home, "--source", &other_s],
        &[("OMH_TRACE", &p(&sb.root.join("source-trace")))],
        None,
    ));
    assert_eq!(record(&sb)["source"], other_s);
    let broken = record_bytes;
    fs::write(sb.home.join("manager.json"), &broken).unwrap();
    let trace = sb.root.join("fail-source");
    let output = invoke(
        &sb,
        &["status", "--home", &home, "--source", &other_s],
        &[("OMH_TRACE", &p(&trace)), ("OMH_CHILD_CODE", "1")],
        None,
    );
    assert_eq!(output.status.code(), Some(1), "{}", show(&output));
    assert_eq!(fs::read(sb.home.join("manager.json")).unwrap(), broken);
}

#[test]
fn forward_fails_closed_without_a_record_digest_or_pin() {
    let sb = sandbox();
    let package = sb.root.join("package");
    write_package(&package);
    let home = p(&sb.home);
    let stamps = sb.root.join("stamps");
    write_stamps(&stamps);
    let stamp = p(&sb.root.join("stamp"));
    let path = format!("{}:/usr/bin:/bin", stamps.display());
    let trace = p(&sb.root.join("trace"));
    let output = invoke(
        &sb,
        &["install", "--home", &home],
        &[("OMH_TRACE", &trace), ("OMH_STAMP", &stamp)],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_ENVIRONMENT_INVALID",
        "manager.json is missing",
    );
    assert!(!sb.root.join("trace").exists());
    assert!(!sb.root.join("stamp").exists());

    install_managed(&sb, Some(&package));
    let dest = dest_of(&sb);
    fs::write(&dest, b"tampered").unwrap();
    let output = invoke(
        &sb,
        &["status", "--home", &home],
        &[("OMH_TRACE", &trace), ("OMH_STAMP", &stamp)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_CONFLICT",
        &format!(
            "Recorded omh command does not match manager.json: {}",
            dest.display()
        ),
    );
    assert_eq!(fs::read(&dest).unwrap(), b"tampered");
    assert!(!sb.root.join("trace").exists());
    fs::write(&dest, fs::read(bin()).unwrap()).unwrap();
    install_managed(&sb, Some(&package));

    let mut edited = record(&sb);
    edited["python"] = json!(p(&sb.root.join("gone-python")));
    fs::write(
        sb.home.join("manager.json"),
        serde_json::to_vec(&edited).unwrap(),
    )
    .unwrap();
    let output = invoke(
        &sb,
        &["prepare", "--home", &home],
        &[("OMH_TRACE", &trace), ("OMH_STAMP", &stamp)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Explicit Python is missing",
    );
    assert!(!sb.root.join("stamp").exists());
    assert!(!sb.root.join("trace").exists());

    let locked = sb.root.join("locked-python");
    fs::write(&locked, b"#!/bin/sh\nexit 0\n").unwrap();
    mode_set(&locked, 0o644);
    edited["python"] = json!(p(&locked));
    fs::write(
        sb.home.join("manager.json"),
        serde_json::to_vec(&edited).unwrap(),
    )
    .unwrap();
    let output = invoke(
        &sb,
        &["plan", "--home", &home],
        &[("OMH_STAMP", &stamp)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_PYTHON_REQUIRED",
        "Cannot execute explicit Python",
    );
    assert!(!sb.root.join("stamp").exists());

    install_managed(&sb, Some(&package));
    let output = invoke(
        &sb,
        &["recover", "--home", &home, "--python", "python3"],
        &[("OMH_STAMP", &stamp)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_RUNTIME_SPEC",
        "An absolute, control-free path is required",
    );
    assert!(!sb.root.join("stamp").exists());
    let output = invoke(
        &sb,
        &["recover", "--home", &home],
        &[("OMH_PYTHON", "python3"), ("OMH_STAMP", &stamp)],
        Some(&path),
    );
    assert_err(
        &output,
        "HARNESS_RUNTIME_SPEC",
        "An absolute, control-free path is required",
    );

    let missing_source = sb.root.join("missing-source");
    let mut current = record(&sb);
    current["source"] = json!(p(&missing_source));
    fs::write(
        sb.home.join("manager.json"),
        serde_json::to_vec(&current).unwrap(),
    )
    .unwrap();
    let output = invoke(
        &sb,
        &["status", "--home", &home],
        &[("OMH_TRACE", &trace)],
        None,
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!("content source is missing: {}", missing_source.display()),
    );
    assert!(!sb.root.join("trace").exists());

    fs::write(sb.home.join("manager.json"), b"{}").unwrap();
    let output = invoke(&sb, &["status", "--home", &home], &[], None);
    assert_err(
        &output,
        "OMH_INVALID",
        "manager.json is not a binary manager record",
    );
}

#[test]
fn forward_updates_python_only_after_success() {
    let sb = sandbox();
    let package = sb.root.join("package");
    write_package(&package);
    install_managed(&sb, Some(&package));
    let home = p(&sb.home);
    let wrapper = sb.root.join("wrap-python");
    let mark = sb.root.join("exe-mark");
    fs::write(
        &wrapper,
        format!(
            "#!/bin/sh\necho \"$0\" > \"{}\"\nexec {} \"$@\"\n",
            mark.display(),
            base_python().display()
        ),
    )
    .unwrap();
    mode_set(&wrapper, 0o755);
    let wrapper_s = p(&fs::canonicalize(&wrapper).unwrap());
    let before = record(&sb);
    let output = invoke(
        &sb,
        &["plan", "--home", &home],
        &[
            ("OMH_PYTHON", &wrapper_s),
            ("OMH_TRACE", &p(&sb.root.join("trace"))),
            ("OMH_EXE_MARK", &p(&mark)),
            ("OMH_CHILD_CODE", "1"),
        ],
        None,
    );
    assert_eq!(output.status.code(), Some(1), "{}", show(&output));
    assert!(mark.is_file(), "wrapper did not run");
    assert_eq!(record(&sb)["python"], before["python"]);
    assert_eq!(record(&sb)["pythonDigest"], before["pythonDigest"]);

    let _ = fs::remove_file(&mark);
    assert_ok(&invoke(
        &sb,
        &["plan", "--home", &home],
        &[
            ("OMH_PYTHON", &wrapper_s),
            ("OMH_TRACE", &p(&sb.root.join("trace-ok"))),
            ("OMH_EXE_MARK", &p(&mark)),
        ],
        None,
    ));
    assert_eq!(record(&sb)["python"], wrapper_s);
    assert_eq!(
        record(&sb)["pythonDigest"],
        sha256(&fs::read(&wrapper).unwrap())
    );
    assert_eq!(record(&sb)["source"], before["source"]);
}

#[test]
fn content_update_stops_before_fetch_or_a_foreign_source() {
    let sb = sandbox();
    let package = sb.root.join("package");
    write_package(&package);
    install_managed(&sb, Some(&package));
    let repo = repo_fixture(&sb);
    let home = p(&sb.home);
    let dev = sb.root.join("dev");
    fs::create_dir_all(&dev).unwrap();
    let dev_s = p(&dev);
    let trace = sb.root.join("git.trace");
    let path = content_path(&sb);
    let output = invoke(
        &sb,
        &["update", "--home", &home, "--source", &dev_s],
        &[("OMH_GIT_TRACE", &p(&trace)), ("OMH_REPO", &p(&repo.bare))],
        Some("/usr/bin:/bin"),
    );
    assert_err(
        &output,
        "OMH_SOURCE_NOT_MANAGED",
        &format!(
            "omh update delegates to the managed checkout at {} (current source: {}); from a developer checkout use omh refresh, or bootstrap with install.sh on POSIX or install.ps1 on Windows",
            sb.home.join("repo").display(),
            dev.display()
        ),
    );
    assert!(!trace.exists());
    assert!(!output
        .stderr
        .windows(b"install target".len())
        .any(|w| w == b"install target"));

    seed_clone(&sb, &repo, "v0.1.0");
    fs::write(sb.home.join("repo/.local-note"), b"dirty\n").unwrap();
    let output = invoke(
        &sb,
        &["update", "--home", &home, "--to", "v0.2.0"],
        &[
            ("OMH_GIT_TRACE", &p(&trace)),
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref2)),
            ("OMH_TRACE", &p(&sb.root.join("py.trace"))),
        ],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!(
            "{} has local changes or untracked files (including ignored files); preserve or move them outside the clone before retrying",
            sb.home.join("repo").display()
        ),
    );
    let git_log = fs::read_to_string(&trace).unwrap();
    assert!(!git_log.contains("fetch"), "{git_log}");
    assert!(!git_log.contains("ls-remote"), "{git_log}");
    assert!(!git_log.contains("checkout"), "{git_log}");
    assert!(!sb.root.join("py.trace").exists());
    assert_eq!(
        git_text(&["-C", &p(&sb.home.join("repo")), "rev-parse", "HEAD"]),
        repo.sha1
    );
    assert!(!String::from_utf8_lossy(&output.stderr).contains("refresh target"));

    let _ = fs::remove_file(&trace);
    let no_curl = invoke(
        &sb,
        &["update", "--home", &home],
        &[
            ("OMH_GIT_TRACE", &p(&trace)),
            ("OMH_VERSION", "v0.1.0"),
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
        ],
        Some(&p(&sb.root.join("wrap"))),
    );
    assert_err(&no_curl, "OMH_INVALID", "curl is required");

    let isolated = sb.root.join("empty-path");
    fs::create_dir_all(&isolated).unwrap();
    let no_git = invoke(
        &sb,
        &["update", "--home", &home],
        &[
            ("OMH_VERSION", "v0.1.0"),
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
        ],
        Some(&p(&isolated)),
    );
    assert_err(&no_git, "OMH_INVALID", "git is required");
    fs::remove_file(sb.home.join("repo/.local-note")).unwrap();

    let no_version = invoke(
        &sb,
        &["update", "--home", &home],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
            ("OMH_GIT_TRACE", &p(&sb.root.join("version.trace"))),
        ],
        Some(&path),
    );
    assert_err(
        &no_version,
        "OMH_INVALID",
        "OMH_VERSION is required when OMH_REPO is not a GitHub URL",
    );
    let version_log = fs::read_to_string(sb.root.join("version.trace")).unwrap_or_default();
    assert!(!version_log.contains("ls-remote"), "{version_log}");

    let no_ref = invoke(
        &sb,
        &["update", "--home", &home],
        &[("OMH_REPO", &p(&repo.bare)), ("OMH_VERSION", "v0.1.0")],
        Some(&path),
    );
    assert_err(
        &no_ref,
        "OMH_INVALID",
        "OMH_REF_URL is required when OMH_REPO is not a GitHub URL",
    );

    let short = sb.root.join("short.ref");
    fs::write(&short, b"abc\n").unwrap();
    let output = invoke(
        &sb,
        &["update", "--home", &home],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_VERSION", "v0.1.0"),
            ("OMH_REF_URL", &p(&short)),
        ],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!(
            "the ref asset does not hold a commit SHA: {}",
            short.display()
        ),
    );

    let wrong = sb.root.join("wrong.ref");
    fs::write(&wrong, b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n").unwrap();
    let output = invoke(
        &sb,
        &["update", "--home", &home, "--to", "v0.1.0"],
        &[("OMH_REPO", &p(&repo.bare)), ("OMH_REF_URL", &p(&wrong))],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!(
            "tag v0.1.0 resolves to {} but the release pins aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            repo.sha1
        ),
    );

    let output = invoke(
        &sb,
        &["update", "--home", &home, "--to", "v9.9.9"],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
        ],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!("tag v9.9.9 was not found in {}", repo.bare.display()),
    );
}

#[test]
fn content_update_bootstraps_and_refreshes_without_reading_a_bad_index() {
    let sb = sandbox();
    install_managed(&sb, None);
    let repo = repo_fixture(&sb);
    let home = p(&sb.home);
    let index = sb.home.join("targets.json");
    fs::write(&index, b"not-json").unwrap();
    mode_set(&index, 0o000);
    let trace = sb.root.join("trace");
    let path = content_path(&sb);
    let git_trace = sb.root.join("git.trace");
    let output = invoke(
        &sb,
        &["update", "--home", &home, "--to", "v0.2.0"],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref2)),
            ("OMH_HARNESS", "codex,grok"),
            ("OMH_TRACE", &p(&trace)),
            ("OMH_GIT_TRACE", &p(&git_trace)),
            ("OMH_WRITE_SHIM", "1"),
        ],
        Some(&path),
    );
    assert_ok(&output);
    assert_eq!(
        git_text(&["-C", &p(&sb.home.join("repo")), "rev-parse", "HEAD"]),
        repo.sha2
    );
    assert_eq!(unix_mode(&index), 0);
    mode_set(&index, 0o644);
    assert_eq!(fs::read(&index).unwrap(), b"not-json");
    let rows = read_trace(&trace);
    assert_eq!(rows.len(), 4, "{rows:?}");
    for (row, (verb, harness, root)) in rows.iter().zip([
        ("install", "codex", ".codex"),
        ("install", "grok", ".grok"),
        ("status", "codex", ".codex"),
        ("status", "grok", ".grok"),
    ]) {
        assert_child_launch(row, verb, &sb.home.join("repo"));
        assert_eq!(argv_flag(row, "--harness"), harness);
        assert_eq!(
            argv_flag(row, "--skills-root"),
            p(&sb.user.join(root).join("skills"))
        );
        if verb == "status" {
            assert!(!row["argv"].as_array().unwrap().iter().any(|item| item == "--python"));
        } else {
            assert_eq!(argv_flag(row, "--python"), p(base_python()));
        }
        let bins = row["argv"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|item| *item == "--bin-dir")
            .count();
        if verb == "status" {
            assert_eq!(bins, 0);
        } else {
            assert_eq!(
                argv_flag(row, "--bin-dir"),
                p(&sb.home.join(".manager-bin"))
            );
        }
        assert!(!row["argv"]
            .as_array()
            .unwrap()
            .iter()
            .any(|item| item == "update"));
    }
    assert!(!sb.home.join(".manager-bin/omh").exists());
    assert!(!sb.home.join("shim.json").exists());
    assert!(!sb.user.join(".local/bin/omh").exists());
    assert_eq!(record(&sb)["source"], p(&sb.home.join("repo")));
    assert_eq!(
        record(&sb)["digest"],
        sha256(&fs::read(dest_of(&sb)).unwrap())
    );
    let git_log = fs::read_to_string(&git_trace).unwrap();
    assert!(
        git_log.contains("clone --quiet --branch v0.2.0"),
        "{git_log}"
    );
    assert!(git_log.contains("refs/tags/v0.2.0"), "{git_log}");
    assert!(
        !git_log.contains("fetch --tags --force origin"),
        "{git_log}"
    );
    assert_no_locks(&sb);
    mode_set(&index, 0o644);

    let upgrade = sandbox();
    install_managed(&upgrade, None);
    let repo = repo_fixture(&upgrade);
    seed_clone(&upgrade, &repo, "v0.1.0");
    let trace = upgrade.root.join("trace");
    let git_trace = upgrade.root.join("git.trace");
    let output = invoke(
        &upgrade,
        &["update", "--home", &p(&upgrade.home)],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
            ("OMH_VERSION", "v0.1.0"),
            ("OMH_TRACE", &p(&trace)),
            ("OMH_GIT_TRACE", &p(&git_trace)),
        ],
        Some(&content_path(&upgrade)),
    );
    assert_ok(&output);
    let rows = read_trace(&trace);
    assert_eq!(rows.len(), 2, "{rows:?}");
    assert_eq!(rows[0]["argv"][1], "refresh");
    assert_eq!(argv_flag(&rows[0], "--harness"), "codex");
    assert_eq!(
        argv_flag(&rows[0], "--skills-root"),
        p(&upgrade.user.join(".codex/skills"))
    );
    assert_eq!(rows[1]["argv"][1], "status");
    let git_log = fs::read_to_string(&git_trace).unwrap();
    assert!(git_log.contains("fetch --tags --force origin"), "{git_log}");
    assert!(!git_log.contains(" clone "), "{git_log}");

    fs::write(upgrade.home.join("targets.json"), b"{}").unwrap();
    let _ = fs::remove_file(&trace);
    assert_ok(&invoke(
        &upgrade,
        &["update", "--home", &p(&upgrade.home), "--to", "v0.2.0"],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref2)),
            ("OMH_TRACE", &p(&trace)),
        ],
        Some(&content_path(&upgrade)),
    ));
    assert_eq!(
        git_text(&["-C", &p(&upgrade.home.join("repo")), "rev-parse", "HEAD"]),
        repo.sha2
    );
    let rows = read_trace(&trace);
    assert_eq!(rows[0]["argv"][1], "refresh");
    assert_eq!(argv_flag(&rows[0], "--harness"), "codex");

    let grok_root = upgrade.root.join("grok-skills");
    let codex_root = upgrade.root.join("codex-skills");
    let index = format!(
        "{{\"b\":{{\"harness\":\"grok\",\"skillsRoot\":\"{}\"}},\"a\":{{\"harness\":\"codex\",\"skillsRoot\":\"{}\"}}}}",
        grok_root.display(),
        codex_root.display()
    );
    fs::write(upgrade.home.join("targets.json"), index.as_bytes()).unwrap();
    let _ = fs::remove_file(&trace);
    assert_ok(&invoke(
        &upgrade,
        &["update", "--home", &p(&upgrade.home)],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref2)),
            ("OMH_VERSION", "v0.2.0"),
            ("OMH_HARNESS", "claude-code"),
            ("OMH_TRACE", &p(&trace)),
        ],
        Some(&content_path(&upgrade)),
    ));
    let rows = read_trace(&trace);
    let verbs: Vec<&str> = rows
        .iter()
        .map(|row| row["argv"][1].as_str().unwrap())
        .collect();
    assert_eq!(verbs, ["refresh", "refresh", "status", "status"]);
    assert_eq!(argv_flag(&rows[0], "--harness"), "grok");
    assert_eq!(argv_flag(&rows[0], "--skills-root"), p(&grok_root));
    assert_eq!(argv_flag(&rows[1], "--harness"), "codex");
    assert_eq!(argv_flag(&rows[1], "--skills-root"), p(&codex_root));
    assert!(rows.iter().all(|row| !row["argv"]
        .as_array()
        .unwrap()
        .iter()
        .any(|item| item == "claude-code")));
}

#[test]
fn content_update_preserves_failures_and_passes_the_child_code() {
    let sb = sandbox();
    install_managed(&sb, None);
    let repo = repo_fixture(&sb);
    seed_clone(&sb, &repo, "v0.1.0");
    let home = p(&sb.home);
    let path = content_path(&sb);
    let index = sb.home.join("targets.json");
    let original = b"[]";
    fs::write(&index, original).unwrap();
    let trace = sb.root.join("trace");
    let output = invoke(
        &sb,
        &["update", "--home", &home, "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
            ("OMH_TRACE", &p(&trace)),
        ],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!(
            "cannot read target index {}: expected an object",
            index.display()
        ),
    );
    assert_eq!(fs::read(&index).unwrap(), original);
    assert!(!trace.exists());
    assert!(!String::from_utf8_lossy(&output.stderr).contains("refresh target"));

    fs::write(
        &index,
        br#"{"one":{"harness":"","skillsRoot":"/tmp/skills"}}"#,
    )
    .unwrap();
    let output = invoke(
        &sb,
        &["update", "--home", &home],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_REF_URL", &p(&repo.ref1)),
            ("OMH_VERSION", "v0.1.0"),
            ("OMH_TRACE", &p(&trace)),
        ],
        Some(&path),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!("cannot read target index {}: expected harness and absolute skillsRoot for every target", index.display()),
    );
    assert!(!trace.exists());

    mode_set(&index, 0o000);
    let output = invoke(
        &sb,
        &["update", "--home", &home],
        &[
            ("OMH_REPO", &p(&repo.bare)),
            ("OMH_VERSION", "v0.1.0"),
            ("OMH_REF_URL", &p(&repo.ref1)),
        ],
        Some(&path),
    );
    assert_eq!(output.status.code(), Some(1), "{}", show(&output));
    assert_eq!(fail_value(&output)["error"]["code"], "OMH_INVALID");
    assert!(fail_value(&output)["error"]["message"]
        .as_str()
        .unwrap()
        .starts_with(&format!("cannot read target index {}:", index.display())));
    mode_set(&index, 0o644);

    let unknown = sandbox();
    install_managed(&unknown, None);
    let repo_u = repo_fixture(&unknown);
    let output = invoke(
        &unknown,
        &["update", "--home", &p(&unknown.home), "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo_u.bare)),
            ("OMH_REF_URL", &p(&repo_u.ref1)),
            ("OMH_HARNESS", "nope"),
            ("OMH_TRACE", &p(&unknown.root.join("trace"))),
        ],
        Some(&content_path(&unknown)),
    );
    assert_err(&output, "OMH_INVALID", "unknown OMH harness: nope");
    assert!(unknown.home.join("repo/.git").is_dir());
    assert!(!unknown.root.join("trace").exists());

    let empty = sandbox();
    install_managed(&empty, None);
    let repo_e = repo_fixture(&empty);
    let output = invoke(
        &empty,
        &["update", "--home", &p(&empty.home), "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo_e.bare)),
            ("OMH_REF_URL", &p(&repo_e.ref1)),
            ("OMH_HARNESS", ""),
            ("OMH_TRACE", &p(&empty.root.join("trace"))),
        ],
        Some(&content_path(&empty)),
    );
    assert_err(&output, "OMH_INVALID", "no OMH targets selected");

    let hooked = sandbox();
    install_managed(&hooked, None);
    let repo_h = repo_fixture(&hooked);
    seed_clone(&hooked, &repo_h, "v0.1.0");
    let hook = hooked.home.join("repo/.git/hooks/post-checkout");
    fs::write(&hook, "#!/bin/sh\necho hooked > .hooked\n").unwrap();
    mode_set(&hook, 0o755);
    let output = invoke(
        &hooked,
        &["update", "--home", &p(&hooked.home), "--to", "v0.2.0"],
        &[
            ("OMH_REPO", &p(&repo_h.bare)),
            ("OMH_REF_URL", &p(&repo_h.ref2)),
            ("OMH_TRACE", &p(&hooked.root.join("trace"))),
        ],
        Some(&content_path(&hooked)),
    );
    assert_eq!(output.status.code(), Some(1), "{}", show(&output));
    assert!(fail_value(&output)["error"]["message"]
        .as_str()
        .unwrap()
        .contains("including ignored files"));
    assert!(hooked.home.join("repo/.hooked").is_file());
    assert!(!hooked.root.join("trace").exists());
    assert_eq!(
        git_text(&["-C", &p(&hooked.home.join("repo")), "rev-parse", "HEAD"]),
        repo_h.sha2
    );

    let alien = sandbox();
    install_managed(&alien, None);
    let repo_a = repo_fixture(&alien);
    fs::write(alien.home.join("repo"), b"not-a-clone").unwrap();
    let output = invoke(
        &alien,
        &["update", "--home", &p(&alien.home), "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo_a.bare)),
            ("OMH_REF_URL", &p(&repo_a.ref1)),
        ],
        Some(&content_path(&alien)),
    );
    assert_err(
        &output,
        "OMH_INVALID",
        &format!(
            "{} exists and is not a git clone",
            alien.home.join("repo").display()
        ),
    );
    assert_eq!(fs::read(alien.home.join("repo")).unwrap(), b"not-a-clone");

    let failed = sandbox();
    install_managed(&failed, None);
    let repo_f = repo_fixture(&failed);
    let output = invoke(
        &failed,
        &["update", "--home", &p(&failed.home), "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo_f.bare)),
            ("OMH_REF_URL", &p(&repo_f.ref1)),
            ("OMH_GIT_FAIL_CLONE", "1"),
            ("OMH_GIT_TRACE", &p(&failed.root.join("git.trace"))),
        ],
        Some(&content_path(&failed)),
    );
    assert_err(&output, "OMH_INVALID", "git clone failed");
    assert!(!failed.home.join("repo").exists());
    assert!(!failed
        .home
        .join(format!(".repo.clone.{}", std::process::id()))
        .exists());

    let child = sandbox();
    let placeholder = child.root.join("placeholder");
    install_managed(&child, Some(&placeholder));
    let repo_c = repo_fixture(&child);
    let mark = child.root.join("mark");
    let output = invoke(
        &child,
        &["update", "--home", &p(&child.home), "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo_c.bare)),
            ("OMH_REF_URL", &p(&repo_c.ref1)),
            ("OMH_HARNESS", "codex,grok"),
            ("OMH_CHILD_CODE", "2"),
            ("OMH_TRACE", &p(&child.root.join("trace"))),
            ("OMH_MARK", &p(&mark)),
        ],
        Some(&content_path(&child)),
    );
    assert_eq!(output.status.code(), Some(2), "{}", show(&output));
    assert!(!String::from_utf8_lossy(&output.stderr).contains("\"error\""));
    assert!(String::from_utf8_lossy(&output.stderr).contains("child-exit 2"));
    let rows = read_trace(&child.root.join("trace"));
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0]["argv"][1], "install");
    assert_eq!(argv_flag(&rows[0], "--harness"), "codex");
    assert_eq!(fs::read_to_string(&mark).unwrap(), "install\n");
    assert_eq!(record(&child)["source"], p(&placeholder));

    let status = sandbox();
    let placeholder = status.root.join("placeholder");
    install_managed(&status, Some(&placeholder));
    let repo_s = repo_fixture(&status);
    let mark = status.root.join("mark");
    let output = invoke(
        &status,
        &["update", "--home", &p(&status.home), "--to", "v0.1.0"],
        &[
            ("OMH_REPO", &p(&repo_s.bare)),
            ("OMH_REF_URL", &p(&repo_s.ref1)),
            ("OMH_HARNESS", "codex"),
            ("OMH_STATUS_CODE", "1"),
            ("OMH_MARK", &p(&mark)),
            ("OMH_TRACE", &p(&status.root.join("trace"))),
            ("OMH_WRITE_SHIM", "1"),
        ],
        Some(&content_path(&status)),
    );
    assert_eq!(output.status.code(), Some(1), "{}", show(&output));
    let err = String::from_utf8_lossy(&output.stderr);
    assert!(err.contains("verification failed for codex"), "{err}");
    assert!(
        err.contains("Target writes are not rolled back; inspect the reported target status."),
        "{err}"
    );
    assert_err(
        &output,
        "OMH_INVALID",
        "Target writes are not rolled back; inspect the reported target status.",
    );
    assert_eq!(fs::read_to_string(&mark).unwrap(), "install\n");
    assert_eq!(record(&status)["source"], p(&status.home.join("repo")));
    assert!(status.home.join("repo").is_dir());
    assert!(!status.home.join(".manager-bin/omh").exists());
    assert!(!status.home.join("shim.json").exists());
    assert_no_locks(&status);
}
