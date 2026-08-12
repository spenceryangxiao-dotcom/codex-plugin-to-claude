# Codex Plugin to Claude

[![Tests](https://github.com/spenceryangxiao-dotcom/codex-plugin-to-claude/actions/workflows/test.yml/badge.svg)](https://github.com/spenceryangxiao-dotcom/codex-plugin-to-claude/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Keep Codex as the primary developer. Bring in Claude as a bounded second opinion only when the work is important enough to justify it.

## What it does

```text
Codex investigates → Codex plans and implements → Codex tests
          │                                      │
          ├─ high risk: ask before review        ├─ sanitized review brief
          └─ explicit request: review directly   └─ Claude: PASS / FAIL / ASK
```

- Explicit request such as “让 Claude 互审” authorizes an immediate review.
- Production, payments, auth, security, privacy, destructive data changes, migrations, core architecture, incidents, and recurring important bugs trigger an approval prompt.
- Ordinary reversible work stays with Codex and incurs no Claude call.
- Claude receives a prepared brief, not repository access.
- `PASS`, `FAIL`, and `ASK` have deterministic handling with a two-round default limit.

## Requirements

- Codex with Skills/Plugins support.
- Python 3.9 or newer.
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated.
- A Claude subscription or API account. Claude usage may incur charges; this repository itself is free.

## Install as a Codex Plugin

```bash
codex plugin marketplace add spenceryangxiao-dotcom/codex-plugin-to-claude
codex plugin add codex-plugin-to-claude@codex-plugin-to-claude
```

Start a new Codex task after installation so the Skill is discovered.

## Install only the personal Skill

```bash
git clone https://github.com/spenceryangxiao-dotcom/codex-plugin-to-claude.git
mkdir -p ~/.agents/skills
cp -R codex-plugin-to-claude/plugins/codex-plugin-to-claude/skills/codex-plugin-to-claude ~/.agents/skills/
```

The `~/.agents/skills` location makes it available across projects and Codex tasks.

## Use it

Explicit invocation:

```text
$codex-plugin-to-claude Review this migration plan before implementation.
```

Natural-language invocation also works:

```text
This is an important payment bug. Have Claude cross-review the tested fix.
```

For high-risk work where you did not explicitly request Claude, Codex explains the risk and asks before sending a review brief.

## Safety model

Claude runs with no tools, no repository access, no session persistence, structured output, and a default USD 1 per-invocation budget cap. The runner rejects common credential, private-key, payment-card, phone-number, and raw-payload patterns before invocation.

The scanner is a guardrail, not a complete data-loss-prevention system. Codex must also inspect every brief manually. Never include secrets, personal identifiers, customer content, payment data, phone numbers, raw payloads, or unrelated proprietary material.

Claude's verdict never replaces tests or Codex's independent verification. If Claude is unavailable or returns invalid output, the Skill reports that review did not complete; it never converts failure into `PASS`.

## Development

Run the standard-library test suite:

```bash
cd plugins/codex-plugin-to-claude
python3 -m unittest discover -s tests -v
```

Validate the plugin with Codex's plugin validator when developing inside a Codex installation:

```bash
python3 /path/to/plugin-creator/scripts/validate_plugin.py plugins/codex-plugin-to-claude
```

## License

[MIT](LICENSE)
