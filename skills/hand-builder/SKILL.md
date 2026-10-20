---
name: hand-builder
description: "Guide for creating custom LibreFang hands — single-agent vs multi-agent, HAND.toml format, installation, and troubleshooting"
---

# LibreFang Hand Builder Guide

## Overview

A LibreFang Hand is a packaged capability bundle that composes an agent with tools, skills, and configuration into a working application. This guide covers how to create custom hands for local installation.

## Directory Structure

```
hands/<hand-name>/
├── HAND.toml          # required: hand definition
└── SKILL.md           # optional: reference knowledge

skills/<skill-name>/
├── SKILL.md           # required: skill definition
└── references/        # optional: supplementary docs
```

### Important: Registry vs Custom

> **Registry** (`librefang/.librefang/registry/`) is synced from online — do NOT put custom hands there. They will be overwritten.
>
> **Custom hands** go in `hands/<name>/` at the librefang project root.
> **Custom skills** go in `skills/<name>/` at the librefang project root.

## Installation

```bash
# Install a custom hand from a local path
librefang hand install ./hands/my-hand/

# Alternative: install from an absolute path
librefang hand install /path/to/my-hand/

# List installed hands
librefang hand list

# Activate a hand
librefang hand activate <hand-id>

# Remove a hand
librefang hand remove <hand-id>
```

## HAND.toml Format

### Required: `[hand]` section wrapper

> **Critical**: Custom hands MUST have a `[hand]` section wrapper at the top. The registry hands (apitester, devops) use top-level fields, but custom hands parsed from local paths require the `[hand]` wrapper.

```toml
[hand]
id = "my-hand"              # required: unique identifier, matches directory name
version = "1.0.0"           # recommended: semver
name = "My Hand"            # required: display name
description = "..."         # required: one-line description
category = "devops"         # required: one of productivity|development|data|content|communication
icon = "lucide:gauge"       # recommended: lucide icon name

tools = [                   # required: tools available to the agent
  "shell_exec",
  "file_read",
  "file_write",
  "file_list",
  "memory_store",
  "memory_recall",
]

skills = [                  # recommended: skills to load
  "shell-scripting",
  "python-expert",
]
```

### Section: `[hand.routing]` — Activation Phrases

```toml
[hand.routing]
aliases = [                 # exact activation phrases (user says these → hand activates)
  "load test",
  "stress test",
  "benchmark",
]
weak_aliases = [            # keyword hints (lower priority matching)
  "latency",
  "throughput",
  "RPS",
]
```

### Section: `[[hand.settings]]` — Configurable Settings

> **Note**: `setting_type` only supports `"select"`, `"text"`, `"toggle"`. `"number"` is NOT supported — use `"text"` instead; validation happens at the daemon level.

```toml
[[hand.settings]]
key = "my_setting"              # unique key
label = "My Setting"            # display label
description = "What this does"  # tooltip description
setting_type = "text"           # only: select | text | toggle
default = "default_value"

# For select type, add options:
[[hand.settings]]
key = "my_choice"
label = "My Choice"
description = "Pick one"
setting_type = "select"
default = "option1"

[[hand.settings.options]]
value = "option1"
label = "Option One"

[[hand.settings.options]]
value = "option2"
label = "Option Two"
```

### Section: `[hand.agent]` (Single-Agent) — Agent Definition

```toml
[hand.agent]
name = "my-agent-name"          # required: agent identifier
description = "..."             # recommended: agent description
module = "builtin:chat"         # required: runtime module (always "builtin:chat")
provider = "default"            # recommended: provider to use
model = "default"               # recommended: model to use
max_tokens = 16384              # optional: max response tokens
temperature = 0.3               # optional: sampling temperature (0.0-1.0)
max_iterations = 50             # optional: max tool-use iterations
system_prompt = """..."""       # required: the agent's behavioral prompt
```

### Section: `[hand.metadata]` — Operational Metadata

```toml
[hand.metadata]
frequency = "on-demand"         # how often: continuous | on-demand | scheduled
token_consumption = "medium"    # expected usage: low | medium | high
default_active = true           # start active on install
```

## Single-Agent vs Multi-Agent Hands

### Single-Agent Hand

```toml
[hand]
id = "my-single-agent"
# ... top-level fields ...

[hand.agent]
name = "my-agent"
# ... agent config ...
```

- One agent, one system_prompt
- Simple, self-contained
- Best for focused tasks (load testing, API testing, etc.)

### Multi-Agent Hand

```toml
[hand]
id = "my-multi-agent"
# ... top-level fields ...

[hand.agents.main]
coordinator = true
name = "coordinator"
module = "builtin:chat"
# ...
# coordinator delegates to sub-agents

[hand.agents.worker]
name = "worker"
module = "builtin:chat"
# ...
```

- Multiple agents with different roles
- `coordinator = true` marks the orchestrator agent
- Sub-agents handle specialized tasks
- Each agent has its own system_prompt and model config
- Best for complex workflows (dev team, CI/CD pipeline, etc.)

## What NOT to Include in Custom Hands

Based on extensive testing, avoid these in custom hand TOML files:

| Feature | Why to Avoid | Alternative |
|---------|-------------|-------------|
| `[[requires]]` | Daemon rejects custom hands with requires | Document dependencies in README.md or SKILL.md |
| `[requires.install]` | Same as above | User installs deps manually |
| `[i18n.*]` | Not needed for custom hands | Keep prompts in the hand's primary language |
| `setting_type = "number"` | NOT supported — only `select`, `text`, `toggle` | Use `"text"` and validate at the daemon level |
| `[dashboard]` | Not needed for custom hands | Skip entirely |
| Nested subdirectories (`.identity/`, `scenarios/`) | Those are runtime artifacts | Keep only `HAND.toml` + optional `SKILL.md` |

## Troubleshooting

### "no [hand] section" error
**Fix**: Add `[hand]` at the top of HAND.toml. Custom hands require the wrapper.

### "unknown variant `number`, expected one of `select`, `text`, `toggle`"
**Fix**: Change `setting_type = "number"` to `setting_type = "text"`.

### "Failed to parse hand during reload"
**Fix**: Check for:
1. Missing `[hand]` section wrapper
2. Invalid `setting_type` value
3. TOML syntax errors (unclosed strings, etc.)
4. Use `python -c "import tomllib; tomllib.load(open('HAND.toml','rb'))"` to validate TOML syntax

### 400 Bad Request on install
**Fix**: Check daemon logs with `librefang logs --follow`. Common causes:
- TOML parse error in HAND.toml
- Invalid field values
- Missing required fields

### Hand installed but with "?" as name
**Fix**: The daemon rejected the hand. Check daemon logs for the actual error.

## Quick Reference: Minimal Working Hand

```toml
[hand]
id = "my-hand"
version = "1.0.0"
name = "My Hand"
description = "What my hand does"
category = "development"
icon = "lucide:box"

tools = ["shell_exec", "file_read", "file_write"]

[hand.routing]
aliases = ["trigger phrase"]

[hand.agent]
name = "my-agent"
module = "builtin:chat"
provider = "default"
model = "default"
system_prompt = """You are a helpful assistant."""

[hand.metadata]
frequency = "on-demand"
token_consumption = "low"
default_active = true
```

## Installation Steps

1. Create `hands/<name>/HAND.toml` with the `[hand]` wrapper
2. Add optional `SKILL.md` for reference knowledge
3. Create `skills/<name>/SKILL.md` for any custom skills (if needed)
4. Run `librefang hand install ./hands/<name>/`
5. Activate with `librefang hand activate <hand-id>`
6. Test with a trigger phrase