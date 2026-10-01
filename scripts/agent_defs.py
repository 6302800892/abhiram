"""Load .claude/agents/*.md definitions into Claude Agent SDK AgentDefinition objects."""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_agent_file(path: pathlib.Path) -> dict[str, object]:
    """Parse the YAML-ish frontmatter (name, description, tools list, model) and body."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"{path} has no frontmatter")
    meta: dict[str, object] = {"tools": []}
    current_list: list[str] | None = None
    for line in match.group(1).splitlines():
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value:
            meta[key.strip()] = value
            current_list = None
        else:
            current_list = []
            meta[key.strip()] = current_list
    meta["prompt"] = match.group(2).strip()
    return meta


def load_agent_definitions(names: list[str]) -> dict[str, object]:
    """Return {name: AgentDefinition} for the requested agents (imports the SDK lazily)."""
    from claude_agent_sdk import AgentDefinition

    definitions: dict[str, object] = {}
    for name in names:
        meta = parse_agent_file(AGENTS_DIR / f"{name}.md")
        definitions[name] = AgentDefinition(
            description=str(meta["description"]),
            prompt=str(meta["prompt"]),
            tools=[t for t in meta["tools"] if isinstance(t, str)],  # type: ignore[union-attr]
            model=str(meta.get("model", "sonnet")),
        )
    return definitions
