//! `omh self` owns the manager binary and manager.json. Harness files stay.

use crate::error::Fail;
use crate::pin;
use crate::record::Record;
use crate::util::{self, absolute, exe_name, sha256};
use serde_json::Value;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

pub fn install(
    home: &Path,
    bin_dir: &Path,
    explicit_python: Option<&str>,
    explicit_source: Option<&str>,
) -> Result<(), Fail> {
    let pin = pin::select(explicit_python)?;
    let payload = fs::read(
        env::current_exe().map_err(|err| Fail::io("cannot read the running omh binary", err))?,
    )
    .map_err(|err| Fail::io("cannot read the running omh binary", err))?;
    let payload_hash = sha256(&payload);
    let dest = bin_dir.join(exe_name());
    let existing = Record::load(home)?;
    if let Some(record) = &existing {
        if record.path != dest {
            match util::read_file(&record.path)? {
                Some(bytes) if sha256(&bytes) == record.digest => {
                    return Err(Fail::new(
                        "HARNESS_CONFLICT",
                        format!(
                            "Owned omh command is already installed at {}; run omh self uninstall before choosing another bin directory",
                            record.path.display()
                        ),
                    ));
                }
                Some(_) => {
                    return Err(Fail::new(
                        "HARNESS_CONFLICT",
                        format!("Unowned omh command exists: {}", record.path.display()),
                    ));
                }
                None => {}
            }
        }
    }
    let current = util::read_file(&dest)?;
    let shim_here = shim_points_at(home, &dest)?;
    let migrating = match &current {
        Some(bytes) => classify_destination(&existing, &dest, bytes, &payload_hash, shim_here)?,
        None => {
            if shim_here {
                return Err(Fail::new(
                    "HARNESS_CONFLICT",
                    format!("Unowned omh command exists: {}", dest.display()),
                ));
            }
            false
        }
    };
    let source = install_source(home, explicit_source, existing.as_ref())?;
    let version = install_version(existing.as_ref());
    let same_file = current
        .as_ref()
        .map(|bytes| sha256(bytes) == payload_hash)
        .unwrap_or(false);
    let record = Record {
        bin_dir: bin_dir.to_path_buf(),
        path: dest.clone(),
        source,
        python: pin.path.clone(),
        python_digest: pin.digest.clone(),
        digest: payload_hash.clone(),
        binary_version: version,
    };
    if same_file
        && existing
            .as_ref()
            .is_some_and(|old| same_record(old, &record))
    {
        return Ok(());
    }
    if !same_file {
        place_payload(&dest, &payload, &payload_hash)?;
    }
    if migrating {
        match fs::remove_file(home.join("shim.json")) {
            Ok(()) => {}
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => {}
            Err(err) => return Err(Fail::io("cannot remove shim.json", err)),
        }
    }
    record.write(home)
}

pub fn update(home: &Path, version_flag: Option<&str>) -> Result<(), Fail> {
    let Some(mut record) = Record::load(home)? else {
        return Err(Fail::new(
            "OMH_ENVIRONMENT_INVALID",
            "manager.json is missing",
        ));
    };
    let payload = binary_payload()?;
    let payload_hash = sha256(&payload);
    let dest_bytes = util::read_file(&record.path)?;
    match dest_bytes {
        Some(bytes) if sha256(&bytes) == payload_hash => {}
        Some(bytes) if sha256(&bytes) == record.digest => {
            place_payload(&record.path, &payload, &payload_hash)?
        }
        Some(_) => {
            return Err(Fail::new(
                "HARNESS_CONFLICT",
                format!("Unowned omh command exists: {}", record.path.display()),
            ));
        }
        None => place_payload(&record.path, &payload, &payload_hash)?,
    }
    record.digest = payload_hash;
    record.binary_version = next_version(version_flag, &record.binary_version);
    record.write(home)
}

pub fn uninstall(home: &Path, json: bool) -> Result<(), Fail> {
    let Some(record) = Record::load(home)? else {
        report(false, json);
        return Ok(());
    };
    let removed = match util::read_file(&record.path)? {
        Some(bytes) if sha256(&bytes) == record.digest => {
            fs::remove_file(&record.path)
                .map_err(|err| Fail::io("cannot remove the omh command", err))?;
            true
        }
        Some(_) => {
            return Err(Fail::new(
                "HARNESS_CONFLICT",
                format!("Unowned omh command exists: {}", record.path.display()),
            ));
        }
        None => false,
    };
    crate::record::remove(home)?;
    report(removed, json);
    Ok(())
}

fn place_payload(dest: &Path, payload: &[u8], payload_hash: &str) -> Result<(), Fail> {
    util::atomic_write(dest, payload, 0o755)?;
    let placed =
        fs::read(dest).map_err(|err| Fail::io("cannot read the installed omh binary", err))?;
    if sha256(&placed) != payload_hash {
        return Err(Fail::new(
            "OMH_INVALID",
            "installed omh binary does not match the payload",
        ));
    }
    Ok(())
}

fn report(removed: bool, json: bool) {
    if json {
        println!(
            "{{\"removed\": {}}}",
            if removed { "true" } else { "false" }
        );
    } else if removed {
        println!("removed the omh command");
    } else {
        println!("no omh command to remove");
    }
}

fn classify_destination(
    existing: &Option<Record>,
    dest: &Path,
    bytes: &[u8],
    payload_hash: &str,
    shim_here: bool,
) -> Result<bool, Fail> {
    let dest_hash = sha256(bytes);
    let marker = util::is_v1_marker(bytes);
    if marker && !shim_here {
        return Err(Fail::new(
            "HARNESS_CONFLICT",
            format!("Unowned omh command exists: {}", dest.display()),
        ));
    }
    if shim_here && !marker {
        return Err(Fail::new(
            "HARNESS_CONFLICT",
            format!("Unowned omh command exists: {}", dest.display()),
        ));
    }
    let owned = existing.as_ref().is_some_and(|record| {
        record.path == dest && (dest_hash == record.digest || dest_hash == payload_hash)
    });
    let migrating = marker && shim_here;
    if !owned && dest_hash != payload_hash && !migrating {
        return Err(Fail::new(
            "HARNESS_CONFLICT",
            format!("Unowned omh command exists: {}", dest.display()),
        ));
    }
    Ok(migrating)
}

fn same_record(old: &Record, new: &Record) -> bool {
    old.bin_dir == new.bin_dir
        && old.path == new.path
        && old.source == new.source
        && old.python == new.python
        && old.python_digest == new.python_digest
        && old.digest == new.digest
        && old.binary_version == new.binary_version
}

fn install_source(
    home: &Path,
    explicit: Option<&str>,
    existing: Option<&Record>,
) -> Result<PathBuf, Fail> {
    if let Some(value) = explicit {
        return absolute(value);
    }
    if let Some(record) = existing {
        return Ok(record.source.clone());
    }
    Ok(home.join("repo"))
}

fn install_version(existing: Option<&Record>) -> String {
    if let Ok(value) = env::var("OMH_BINARY_VERSION") {
        if !value.is_empty() {
            return value;
        }
    }
    existing
        .map(|record| record.binary_version.clone())
        .unwrap_or_else(|| env!("CARGO_PKG_VERSION").to_string())
}

fn next_version(flag: Option<&str>, previous: &str) -> String {
    if let Some(value) = flag {
        return value.to_string();
    }
    if let Ok(value) = env::var("OMH_BINARY_VERSION") {
        if !value.is_empty() {
            return value;
        }
    }
    previous.to_string()
}

fn binary_payload() -> Result<Vec<u8>, Fail> {
    let file = env::var("OMH_BINARY_FILE")
        .ok()
        .filter(|value| !value.is_empty());
    let url = env::var("OMH_BINARY_URL")
        .ok()
        .filter(|value| !value.is_empty());
    let bytes = match (file, url) {
        (Some(path), _) => {
            let path = absolute(&path)?;
            fs::read(&path).map_err(|_| {
                Fail::new(
                    "OMH_INVALID",
                    format!("binary payload is missing: {}", path.display()),
                )
            })?
        }
        (None, Some(url)) => download(&url)?,
        (None, None) => {
            return Err(Fail::new(
                "OMH_INVALID",
                "no binary payload: set OMH_BINARY_FILE or OMH_BINARY_URL",
            ));
        }
    };
    let expected = env::var("OMH_BINARY_SHA256")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| Fail::new("OMH_INVALID", "OMH_BINARY_SHA256 is required"))?;
    if !expected.trim().eq_ignore_ascii_case(&sha256(&bytes)) {
        return Err(Fail::new("OMH_INVALID", "binary checksum does not match"));
    }
    Ok(bytes)
}

fn download(url: &str) -> Result<Vec<u8>, Fail> {
    let output = Command::new(if cfg!(windows) { "curl.exe" } else { "curl" })
        .args(["-fsSL", url])
        .output()
        .map_err(|_| Fail::new("OMH_INVALID", format!("binary download failed: {url}")))?;
    if !output.status.success() {
        return Err(Fail::new(
            "OMH_INVALID",
            format!("binary download failed: {url}"),
        ));
    }
    Ok(output.stdout)
}

fn shim_points_at(home: &Path, dest: &Path) -> Result<bool, Fail> {
    let Some(bytes) = util::read_file(&home.join("shim.json"))? else {
        return Ok(false);
    };
    let Ok(value) = serde_json::from_slice::<Value>(&bytes) else {
        return Ok(false);
    };
    let Some(recorded) = value.get("path").and_then(Value::as_str) else {
        return Ok(false);
    };
    Ok(Path::new(recorded) == dest)
}

pub fn command_dir(explicit: Option<&str>) -> Result<PathBuf, Fail> {
    if let Some(value) = explicit {
        return absolute(value);
    }
    Ok(util::user_home()?.join(".local").join("bin"))
}
