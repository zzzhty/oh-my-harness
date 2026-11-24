//! Pin one already-installed base interpreter. Never download or search PATH for Python.

use crate::error::Fail;
use crate::util::{absolute, path_string, sha256};
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};

static PIN_SEQ: AtomicU64 = AtomicU64::new(0);

pub struct Pin {
    pub path: PathBuf,
    pub digest: String,
}

const PROBE: &str = "import json,sys; print(json.dumps({'version':[sys.version_info[0], sys.version_info[1]], 'prefix': sys.prefix, 'base_prefix': sys.base_prefix}))";

pub fn select(explicit: Option<&str>) -> Result<Pin, Fail> {
    let raw = if let Some(value) = explicit {
        value.to_string()
    } else if let Ok(value) = std::env::var("OMH_PYTHON") {
        if value.is_empty() {
            find_managed()?
        } else {
            value
        }
    } else {
        find_managed()?
    };
    // A relative override is a spec error, not a PATH lookup.
    let requested = absolute(&raw)?;
    // Probe the given path. A venv `bin/python` is a symlink to the base
    // interpreter; canonicalizing first would execute that base file and
    // report prefix == base_prefix.
    if !requested.is_file() {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Explicit Python is missing",
        ));
    }
    if !executable(&requested) {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Cannot execute explicit Python",
        ));
    }
    probe(&requested)?;
    let resolved = fs::canonicalize(&requested)
        .map_err(|_| Fail::new("HARNESS_PYTHON_REQUIRED", "Explicit Python is missing"))?;
    let bytes = fs::read(&resolved)
        .map_err(|_| Fail::new("HARNESS_PYTHON_REQUIRED", "Explicit Python is missing"))?;
    Ok(Pin {
        path: resolved,
        digest: sha256(&bytes),
    })
}

pub fn require_executable(path: &Path) -> Result<PathBuf, Fail> {
    let resolved = fs::canonicalize(path)
        .map_err(|_| Fail::new("HARNESS_PYTHON_REQUIRED", "Explicit Python is missing"))?;
    if !resolved.is_file() {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Explicit Python is missing",
        ));
    }
    if !executable(&resolved) {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Cannot execute explicit Python",
        ));
    }
    Ok(resolved)
}

fn find_managed() -> Result<String, Fail> {
    let scratch = std::env::temp_dir().join(format!(
        "omh-pin-{}-{}",
        std::process::id(),
        PIN_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&scratch).map_err(|err| Fail::io("cannot create pin directory", err))?;
    let mut command = Command::new(if cfg!(windows) { "uv.exe" } else { "uv" });
    command
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
        .env("UV_PYTHON_PREFERENCE", "only-managed");
    let ran = command.output();
    let _ = fs::remove_dir_all(&scratch);
    let output = match ran {
        Ok(output) => output,
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => {
            return Err(Fail::new(
                "HARNESS_PYTHON_REQUIRED",
                "uv is required to pin a managed interpreter",
            ));
        }
        Err(_) => {
            return Err(Fail::new(
                "HARNESS_PYTHON_REQUIRED",
                "Explicit Python is missing",
            ))
        }
    };
    if !output.status.success() {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Explicit Python is missing",
        ));
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let found = text
        .lines()
        .rev()
        .find(|line| !line.trim().is_empty())
        .map(str::trim)
        .unwrap_or("");
    if found.is_empty() {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Explicit Python is missing",
        ));
    }
    // Reject a non-absolute uv result before any record is written.
    absolute(found)?;
    Ok(found.to_string())
}

fn probe(python: &Path) -> Result<(), Fail> {
    let output = Command::new(python)
        .args(["-I", "-B", "-c", PROBE])
        .env_remove("PYTHONPATH")
        .env_remove("PYTHONHOME")
        .output()
        .map_err(|_| Fail::new("HARNESS_PYTHON_REQUIRED", "Cannot execute explicit Python"))?;
    if !output.status.success() {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Cannot execute explicit Python",
        ));
    }
    let text = String::from_utf8_lossy(&output.stdout);
    let line = text
        .lines()
        .find(|line| line.trim_start().starts_with('{'))
        .unwrap_or("");
    let value: Value = serde_json::from_str(line)
        .map_err(|_| Fail::new("HARNESS_PYTHON_REQUIRED", "Cannot execute explicit Python"))?;
    let version = value.get("version").and_then(Value::as_array);
    let major = version
        .and_then(|items| items.first())
        .and_then(Value::as_u64);
    let minor = version
        .and_then(|items| items.get(1))
        .and_then(Value::as_u64);
    if major != Some(3) || minor.unwrap_or(0) < 11 {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Python 3.11 or newer is required",
        ));
    }
    let prefix = value.get("prefix").and_then(Value::as_str).unwrap_or("");
    let base = value
        .get("base_prefix")
        .and_then(Value::as_str)
        .unwrap_or("");
    if prefix.is_empty() || prefix != base {
        return Err(Fail::new(
            "HARNESS_PYTHON_REQUIRED",
            "Explicit Python is not a base interpreter",
        ));
    }
    let _ = path_string(python)?;
    Ok(())
}

fn executable(path: &Path) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        return fs::metadata(path)
            .map(|meta| meta.permissions().mode() & 0o111 != 0)
            .unwrap_or(false);
    }
    #[cfg(not(unix))]
    {
        path.is_file()
    }
}
