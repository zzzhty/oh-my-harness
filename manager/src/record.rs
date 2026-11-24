//! `<home>/manager.json` is the manager install record. It is not a target owner.

use crate::error::Fail;
use crate::util::{self, absolute, path_string, sha256};
use serde_json::{Map, Value};
use std::fs;
use std::path::{Path, PathBuf};

pub struct Record {
    pub bin_dir: PathBuf,
    pub path: PathBuf,
    pub source: PathBuf,
    pub python: PathBuf,
    pub python_digest: String,
    pub digest: String,
    pub binary_version: String,
}

impl Record {
    pub fn load(home: &Path) -> Result<Option<Self>, Fail> {
        let file = home.join("manager.json");
        let Some(bytes) = util::read_file(&file)? else {
            return Ok(None);
        };
        let value: Value = serde_json::from_slice(&bytes).map_err(|err| {
            Fail::new("OMH_INVALID", format!("manager.json is not a record: {err}"))
        })?;
        let obj = value.as_object().ok_or_else(|| Fail::new("OMH_INVALID", "manager.json is not a record"))?;
        if obj.get("schemaVersion").and_then(Value::as_u64) != Some(1) || obj.get("kind").and_then(Value::as_str) != Some("binary") {
            return Err(Fail::new("OMH_INVALID", "manager.json is not a binary manager record"));
        }
        Ok(Some(Self {
            bin_dir: required_path(obj, "binDir")?,
            path: required_path(obj, "path")?,
            source: required_path(obj, "source")?,
            python: required_path(obj, "python")?,
            python_digest: required_digest(obj, "pythonDigest")?,
            digest: required_digest(obj, "digest")?,
            binary_version: required_string(obj, "binaryVersion")?,
        }))
    }

    pub fn write(&self, home: &Path) -> Result<(), Fail> {
        let mut map = Map::new();
        map.insert("schemaVersion".into(), Value::from(1));
        map.insert("kind".into(), Value::from("binary"));
        map.insert("binDir".into(), Value::from(path_string(&self.bin_dir)?));
        map.insert("path".into(), Value::from(path_string(&self.path)?));
        map.insert("source".into(), Value::from(path_string(&self.source)?));
        map.insert("python".into(), Value::from(path_string(&self.python)?));
        map.insert("pythonDigest".into(), Value::from(self.python_digest.clone()));
        map.insert("digest".into(), Value::from(self.digest.clone()));
        map.insert("binaryVersion".into(), Value::from(self.binary_version.clone()));
        let bytes = serde_json::to_vec(&Value::Object(map))
            .map_err(|err| Fail::new("OMH_INVALID", format!("cannot encode manager.json: {err}")))?;
        util::atomic_write(&home.join("manager.json"), &bytes, 0o644)
    }

    pub fn file_digest(&self) -> Result<Option<String>, Fail> {
        Ok(util::read_file(&self.path)?.map(|bytes| sha256(&bytes)))
    }
}

fn required_string(obj: &Map<String, Value>, key: &str) -> Result<String, Fail> {
    obj.get(key)
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
        .ok_or_else(|| Fail::new("OMH_INVALID", format!("manager.json is missing {key}")))
}

fn required_path(obj: &Map<String, Value>, key: &str) -> Result<PathBuf, Fail> {
    let text = required_string(obj, key)?;
    absolute(&text).map_err(|_| Fail::new("OMH_INVALID", format!("manager.json {key} is not an absolute path")))
}

fn required_digest(obj: &Map<String, Value>, key: &str) -> Result<String, Fail> {
    let text = required_string(obj, key)?;
    if text.len() == 64 && text.chars().all(|ch| ch.is_ascii_hexdigit()) {
        Ok(text.to_ascii_lowercase())
    } else {
        Err(Fail::new("OMH_INVALID", format!("manager.json {key} is not a SHA-256 digest")))
    }
}

pub fn remove(home: &Path) -> Result<(), Fail> {
    match fs::remove_file(home.join("manager.json")) {
        Ok(()) => Ok(()),
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(err) => Err(Fail::io("cannot remove manager.json", err)),
    }
}
