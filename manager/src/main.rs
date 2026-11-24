//! Static omh manager. `self` owns the binary. Content commands exec the pinned interpreter.

mod content;
mod error;
mod forward;
mod pin;
mod record;
mod self_cmd;
mod util;

use error::Stop;
use forward::Child;
use record::Record;
use std::env;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use util::absolute;

fn main() -> ExitCode {
    match run(env::args().skip(1).collect()) {
        Ok(code) => ExitCode::from(code),
        Err(Stop::Usage(text)) => {
            eprintln!("usage: omh <command>\n{text}");
            ExitCode::from(2)
        }
        Err(Stop::Fail(fail)) => {
            eprintln!("{}", fail.json());
            ExitCode::from(1)
        }
    }
}

fn run(args: Vec<String>) -> Result<u8, Stop> {
    let index = find_command(&args)?;
    let command = args[index].clone();
    let without = without_index(&args, index);
    match command.as_str() {
        "self" => self_command(&args, &without),
        "install" | "refresh" | "uninstall" | "prepare" | "plan" | "status" | "recover" => {
            forward_command(&args, &command, &without)
        }
        "update" => content_command(&args, &without),
        _ => usage(format!("unrecognized command: {command}")),
    }
}

fn self_command(args: &[String], rest: &[String]) -> Result<u8, Stop> {
    let Some(leaf) = rest.first() else {
        return usage("omh self requires install, update, or uninstall");
    };
    if !matches!(leaf.as_str(), "install" | "update" | "uninstall") {
        return usage("unrecognized arguments");
    }
    let tail = &rest[1..];
    let home = home_of(args)?;
    match leaf.as_str() {
        "install" => {
            scan(tail, &["--home", "--python", "--bin-dir", "--source"], &["--json"])?;
            let bin_dir = self_cmd::command_dir(flag(args, "--bin-dir").as_deref())?;
            let source = flag(args, "--source");
            self_cmd::install(&home, &bin_dir, flag(args, "--python").as_deref(), source.as_deref())?;
            Ok(0)
        }
        "update" => {
            scan(tail, &["--home", "--to"], &["--json"])?;
            self_cmd::update(&home, flag(args, "--to").as_deref())?;
            Ok(0)
        }
        "uninstall" => {
            scan(tail, &["--home"], &["--json"])?;
            self_cmd::uninstall(&home, args.iter().any(|arg| arg == "--json"))?;
            Ok(0)
        }
        _ => usage("unrecognized arguments"),
    }
}

fn forward_command(args: &[String], command: &str, without: &[String]) -> Result<u8, Stop> {
    let home = home_of(args)?;
    let mut record = load_record(&home)?;
    forward::confirm_binary(&record)?;
    let explicit = flag(args, "--python");
    let python = forward::interpreter(&record, explicit.as_deref())?;
    let source_flag = flag(args, "--source");
    let source = match &source_flag {
        Some(value) => absolute(value)?,
        None => record.source.clone(),
    };
    let scratch = matches!(command, "install" | "refresh").then(|| forward::scratch_dir(&home));
    let mut child_args = strip_flag(without, "--python");
    if scratch.is_some() {
        child_args = strip_flag(&child_args, "--bin-dir");
    }
    child_args.push("--python".into());
    child_args.push(python.display().to_string());
    if let Some(dir) = &scratch {
        child_args.push("--bin-dir".into());
        child_args.push(dir.display().to_string());
    }
    let code = forward::run(
        &home,
        &mut record,
        &Child {
            command: command.to_string(),
            args: child_args,
            source,
            python,
            store_source: source_flag.is_some(),
            scratch,
        },
    )?;
    Ok(narrow(code))
}

fn content_command(args: &[String], without: &[String]) -> Result<u8, Stop> {
    scan(without, &["--home", "--source", "--to", "--python"], &["--json"])?;
    let home = home_of(args)?;
    let mut record = load_record(&home)?;
    forward::confirm_binary(&record)?;
    let explicit = flag(args, "--python");
    let python = forward::interpreter(&record, explicit.as_deref())?;
    let source = match flag(args, "--source") {
        Some(value) => Some(absolute(&value)?),
        None => None,
    };
    let code = content::update(&home, &mut record, &python, source.as_deref(), flag(args, "--to").as_deref())?;
    Ok(narrow(code))
}

fn narrow(code: i32) -> u8 {
    if (0..=255).contains(&code) { code as u8 } else { 1 }
}

fn load_record(home: &Path) -> Result<Record, Stop> {
    match Record::load(home)? {
        Some(record) => Ok(record),
        None => Err(error::Fail::new("OMH_ENVIRONMENT_INVALID", "manager.json is missing").into()),
    }
}

fn home_of(args: &[String]) -> Result<PathBuf, Stop> {
    if let Some(value) = flag(args, "--home") {
        Ok(absolute(&value)?)
    } else {
        Ok(util::user_home()?.join(".oh-my-harness"))
    }
}

fn find_command(args: &[String]) -> Result<usize, Stop> {
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        if arg == "--json" || arg == "--offline" || arg == "--help" || arg == "-h" {
            index += 1;
            continue;
        }
        if arg.starts_with("--") {
            if arg.contains('=') {
                index += 1;
                continue;
            }
            if index + 1 >= args.len() {
                return usage(format!("missing value for {arg}"));
            }
            index += 2;
            continue;
        }
        if arg.starts_with('-') {
            return usage(format!("unrecognized arguments: {arg}"));
        }
        return Ok(index);
    }
    usage("a command is required")
}

fn scan(args: &[String], values: &[&str], bools: &[&str]) -> Result<(), Stop> {
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        if bools.contains(&arg.as_str()) {
            index += 1;
            continue;
        }
        let name = arg.split('=').next().unwrap_or(arg);
        if !arg.starts_with("--") || !values.contains(&name) {
            return usage(format!("unrecognized arguments: {arg}"));
        }
        if arg.contains('=') {
            index += 1;
            continue;
        }
        if index + 1 >= args.len() {
            return usage(format!("missing value for {name}"));
        }
        index += 2;
    }
    Ok(())
}

fn flag(args: &[String], name: &str) -> Option<String> {
    let mut found = None;
    let mut index = 0;
    let with_equals = format!("{name}=");
    while index < args.len() {
        let arg = &args[index];
        if arg == name {
            found = args.get(index + 1).cloned();
            index += 2;
            continue;
        }
        if let Some(value) = arg.strip_prefix(&with_equals) {
            found = Some(value.to_string());
        }
        index += 1;
    }
    found
}

fn without_index(args: &[String], skip: usize) -> Vec<String> {
    args.iter().enumerate().filter(|(index, _)| *index != skip).map(|(_, arg)| arg.clone()).collect()
}

fn strip_flag(args: &[String], name: &str) -> Vec<String> {
    let mut kept = Vec::new();
    let mut index = 0;
    let with_equals = format!("{name}=");
    while index < args.len() {
        let arg = &args[index];
        if arg == name {
            index += 2;
            continue;
        }
        if arg.starts_with(&with_equals) {
            index += 1;
            continue;
        }
        kept.push(arg.clone());
        index += 1;
    }
    kept
}

fn usage<T>(text: impl Into<String>) -> Result<T, Stop> {
    Err(Stop::Usage(text.into()))
}
