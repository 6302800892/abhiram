#!/usr/bin/env bash
# Shared helpers for MediCard project hooks. Source this file; do not execute it.
# Claude Code passes the hook payload as a single JSON object on stdin.

HOOK_PAYLOAD="$(cat)"

# Extract a top-level string field from tool_input (good enough for file_path/command).
hook_field() {
  printf '%s' "$HOOK_PAYLOAD" \
    | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" \
    | head -n 1
}

# Normalised forward-slash file path of the tool call (empty when not a file tool).
hook_file_path() {
  hook_field file_path | sed 's#\\\\#/#g; s#\\#/#g'
}

hook_tool_name() {
  hook_field tool_name
}

# Block with a message Claude can act on (exit 2 => stderr is fed back to the model).
hook_block() {
  printf 'BLOCKED by %s: %s\n' "$HOOK_NAME" "$1" >&2
  exit 2
}
