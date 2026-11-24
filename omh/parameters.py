"""Public harness names and the omh command's own lifecycle.

Persisted ids stay codex, claude-code, and grok. The only input alias is
claude, and it resolves to claude-code before argparse checks choices.
`omh self uninstall` removes the owned omh command. `omh uninstall` does not.
"""
import argparse
import json
from pathlib import Path

REQUIRED_TARGET = 'uninstall requires a target: codex, claude-code, grok, or claude'


def harness_name(value):
    """Map claude to claude-code before choices rejects unknown spellings."""
    return 'claude-code' if value == 'claude' else value


def _uninstall(parser):
    return str(getattr(parser, 'prog', '')).rsplit(maxsplit=1)[-1] == 'uninstall'


def positional_help(parser):
    """Keep the claude alias. Uninstall help states that a target is required."""
    text = 'positional harness; claude means claude-code'
    if _uninstall(parser):
        return f'{text}; {REQUIRED_TARGET}'
    return text


class _RequiredTargetHelp(argparse.HelpFormatter):
    """Show uninstall's positional as HARNESS, not the optional [HARNESS] form."""

    def _format_args(self, action, default_metavar):
        if action.nargs == '?' and not action.option_strings and action.dest == 'target':
            return '%s' % self._metavar_formatter(action, default_metavar)(1)
        return super()._format_args(action, default_metavar)


def formatter(name):
    """Uninstall usage lists HARNESS as required. Other commands stay default."""
    if name == 'uninstall':
        return _RequiredTargetHelp
    return argparse.HelpFormatter


def bind_parser(parser, args):
    """Apply one positional name and --harness. Uninstall must name a target."""
    positional = getattr(args, 'target', None)
    flagged = getattr(args, 'harness', None)
    if positional and flagged and positional != flagged:
        parser.error(f'{positional} does not match --harness {flagged}')
    chosen = positional or flagged
    if args.command == 'uninstall' and chosen is None and getattr(args, 'skills_root', None) is None:
        parser.error(REQUIRED_TARGET)
    return chosen


def add_self(commands, shared_flags, json_flag):
    """Register `omh self`, the namespace for the omh command itself."""
    parent = commands.add_parser('self', help='manage the omh command',
        description='Manage the omh command itself.')
    nested = parent.add_subparsers(dest='self_command', required=True)
    leaf = nested.add_parser('uninstall', help='remove the omh command',
        description='Remove the owned omh command. Harness targets and runtimes stay.')
    shared_flags(leaf)
    json_flag(leaf)


def run_self(args, home, read, owned, remove, fail):
    """Remove the owned launcher recorded for this home. Leave every harness in place."""
    raw = read(home / 'shim.json')
    removed = False
    if raw is not None:
        path = Path(json.loads(raw)['path'])
        content = read(path)
        if content is not None and not owned(content):
            fail(f'Unowned omh command exists: {path}', 'HARNESS_CONFLICT')
        removed = owned(content)
        remove(home)
    text = 'removed the omh command' if removed else 'no omh command to remove'
    print(json.dumps({'removed': removed}) if args.json else text)
    return 0
