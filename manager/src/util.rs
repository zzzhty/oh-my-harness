//! Path and file helpers shared by the manager. No projection and no locks.

use crate::error::Fail;
use sha2::{Digest, Sha256};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Component, Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

static TEMP_SEQ: AtomicU64 = AtomicU64::new(0);

pub fn exe_name() -> &'static str {
    if cfg!(windows) { "omh.exe" } else { "omh" }
}

pub fn absolute(raw: &str) -> Result<PathBuf, Fail> {
    let path = Path::new(raw);
    if !path.is_absolute()
        || path.components().any(|component| matches!(component, Component::ParentDir))
        || raw.chars().any(|ch| (ch as u32) < 32)
    {
        return Err(Fail::new(
            "HARNESS_RUNTIME_SPEC",
            "An absolute, control-free path is required",
        ));
    }
    Ok(path.to_path_buf())
}

pub fn path_string(path: &Path) -> Result<String, Fail> {
    path.to_str()
        .map(str::to_string)
        .ok_or_else(|| Fail::new("OMH_INVALID", "path is not valid UTF-8"))
}

pub fn user_home() -> Result<PathBuf, Fail> {
    let raw = std::env::var_os("HOME")
        .filter(|value| !value.is_empty())
        .or_else(|| {
            if cfg!(windows) {
                std::env::var_os("USERPROFILE")
            } else {
                None
            }
        });
    let Some(raw) = raw else {
        return Err(Fail::new("OMH_ENVIRONMENT_INVALID", "HOME is not set to an absolute path"));
    };
    let text = raw.to_str().ok_or_else(|| Fail::new("OMH_ENVIRONMENT_INVALID", "HOME is not valid UTF-8"))?;
    absolute(text).map_err(|_| Fail::new("OMH_ENVIRONMENT_INVALID", "HOME is not set to an absolute path"))
}

pub fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::new().chain_update(bytes).finalize())
}

pub fn is_v1_marker(bytes: &[u8]) -> bool {
    let text = String::from_utf8_lossy(bytes);
    let mut lines = text.split('\n');
    lines.next();
    lines.next() == Some("# oh-my-harness standalone launcher v1")
}

fn temp_name(parent: &Path) -> PathBuf {
    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    let seq = TEMP_SEQ.fetch_add(1, Ordering::Relaxed);
    parent.join(format!(".omh-{}-{}-{}", std::process::id(), nanos, seq))
}

pub fn atomic_write(dest: &Path, bytes: &[u8], mode: u32) -> Result<(), Fail> {
    let parent = dest
        .parent()
        .filter(|path| !path.as_os_str().is_empty())
        .ok_or_else(|| Fail::new("OMH_INVALID", "path has no parent"))?;
    fs::create_dir_all(parent).map_err(|err| Fail::io("cannot create parent directory", err))?;
    let tmp = temp_name(parent);
    let write_result = (|| -> std::io::Result<()> {
        let mut file = OpenOptions::new().write(true).create_new(true).open(&tmp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        Ok(())
    })();
    if let Err(err) = write_result {
        let _ = fs::remove_file(&tmp);
        return Err(Fail::io("cannot write temporary file", err));
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Err(err) = fs::set_permissions(&tmp, fs::Permissions::from_mode(mode)) {
            let _ = fs::remove_file(&tmp);
            return Err(Fail::io("cannot set permissions", err));
        }
    }
    let _ = mode;
    if let Err(err) = fs::rename(&tmp, dest) {
        let _ = fs::remove_file(&tmp);
        return Err(Fail::io("cannot replace file", err));
    }
    #[cfg(unix)]
    if let Ok(dir) = OpenOptions::new().read(true).open(parent) {
        let _ = dir.sync_all();
    }
    Ok(())
}

pub fn read_file(path: &Path) -> Result<Option<Vec<u8>>, Fail> {
    match fs::read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(err) => Err(Fail::io(&format!("cannot read {}", path.display()), err)),
    }
}
