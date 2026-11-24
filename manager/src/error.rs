//! Failures use the distributor's stderr object. Usage stays plain text.

use serde_json::json;

#[derive(Debug)]
pub struct Fail {
    pub code: &'static str,
    pub message: String,
}

impl Fail {
    pub fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self { code, message: message.into() }
    }

    pub fn io(context: &str, err: std::io::Error) -> Self {
        Self::new("OMH_INVALID", format!("{context}: {err}"))
    }

    pub fn json(&self) -> String {
        json!({"error": {"code": self.code, "message": self.message}}).to_string()
    }
}

pub enum Stop {
    Usage(String),
    Fail(Fail),
}

impl From<Fail> for Stop {
    fn from(fail: Fail) -> Self {
        Self::Fail(fail)
    }
}
