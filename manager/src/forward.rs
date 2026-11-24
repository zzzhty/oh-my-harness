//! Run the pinned interpreter. The child owns projection; this process holds no lock.

use crate::error::Fail;
use crate::pin;
use crate::record::Record;
use crate::util::{self, exe_name, sha256};
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

pub struct Child {
    pub command: String,
    pub args: Vec<String>,
    pub source: PathBuf,
    pub python: PathBuf,
    pub store_source: bool,
    pub scratch: Option<PathBuf>,
}

pub fn run(home: &Path, record: &mut Record, child: &Child) -> Result<i32, Fail> {
    if !child.source.is_dir() {
        return Err(Fail::new(
            "OMH_INVALID",
            format!("content source is missing: {}", child.source.display()),
        ));
    }
    let mut command = Command::new(&child.python);
    command.arg("-B").arg("-m").arg("omh").arg(&child.command).args(&child.args);
    command.env("PYTHONPATH", &child.source);
    command.current_dir(&child.source);
    command.stdin(Stdio::inherit()).stdout(Stdio::inherit()).stderr(Stdio::inherit());
    let status = command.status().map_err(|_| {
        Fail::new("HARNESS_PYTHON_REQUIRED", "Cannot execute explicit Python")
    })?;
    if let Some(scratch) = &child.scratch {
        cleanup_scratch(home, scratch);
    }
    let code = status.code().unwrap_or(1);
    if code == 0 {
        remember(home, record, child)?;
    }
    Ok(code)
}

fn remember(home: &Path, record: &mut Record, child: &Child) -> Result<(), Fail> {
    let mut changed = false;
    if record.python != child.python {
        record.python = child.python.clone();
        record.python_digest = sha256(&std::fs::read(&child.python).map_err(|_| {
            Fail::new("HARNESS_PYTHON_REQUIRED", "Explicit Python is missing")
        })?);
        changed = true;
    }
    if child.store_source && record.source != child.source {
        record.source = child.source.clone();
        changed = true;
    }
    if changed {
        record.write(home)?;
    }
    Ok(())
}

pub fn confirm_binary(record: &Record) -> Result<(), Fail> {
    match record.file_digest()? {
        Some(digest) if digest == record.digest => Ok(()),
        Some(_) | None => Err(Fail::new(
            "HARNESS_CONFLICT",
            format!("Recorded omh command does not match manager.json: {}", record.path.display()),
        )),
    }
}

pub fn interpreter(record: &Record, explicit: Option<&str>) -> Result<PathBuf, Fail> {
    let selected = if let Some(value) = explicit {
        crate::util::absolute(value)?
    } else if let Ok(value) = std::env::var("OMH_PYTHON") {
        if value.is_empty() {
            record.python.clone()
        } else {
            crate::util::absolute(&value)?
        }
    } else {
        record.python.clone()
    };
    pin::require_executable(&selected)
}

fn cleanup_scratch(home: &Path, scratch: &Path) {
    // Python's shim name is omh on POSIX. Windows write_shim writes nothing.
    let shim = scratch.join(if cfg!(windows) { exe_name() } else { "omh" });
    if let Ok(Some(bytes)) = util::read_file(&shim) {
        if util::is_v1_marker(&bytes) {
            let _ = std::fs::remove_file(&shim);
        }
    }
    let record = home.join("shim.json");
    let Ok(Some(bytes)) = util::read_file(&record) else {
        return;
    };
    let Ok(value) = serde_json::from_slice::<Value>(&bytes) else {
        return;
    };
    if value.get("path").and_then(Value::as_str).map(Path::new) == Some(shim.as_path()) {
        let _ = std::fs::remove_file(record);
    }
}

pub fn scratch_dir(home: &Path) -> PathBuf {
    home.join(".manager-bin")
}
