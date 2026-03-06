# Publishing the Lorelang Skill

This document covers how to publish the Lore ontology skill to the various AI agent skill marketplaces.

## Package Layout

```
.claude-plugin/
  plugin.json               # Claude Code plugin manifest (repo-level)
  marketplace.json           # Claude Code marketplace index

skills/
  lorelang/
    SKILL.md                 # Main skill file (Agent Skills + OpenClaw metadata)
    plugin.json              # ClawHub package manifest (skill-level)
    references/
      CLI.md                 # CLI reference
      FORMAT.md              # File format reference
      WORKFLOWS.md           # Workflow guides

.claude/skills/lorelang/     # Project-level Claude Code skill (copy)
  SKILL.md
  references/
```

## Pre-Publishing Checklist

- [ ] All tests pass: `make launch-check`
- [ ] SKILL.md frontmatter has correct version matching `pyproject.toml`
- [ ] `.claude-plugin/plugin.json` version matches
- [ ] `skills/lorelang/plugin.json` version matches
- [ ] `lore-ontology` package is published on PyPI
- [ ] All CLI commands referenced in the skill work correctly
- [ ] Reference files are up to date with current CLI
- [ ] `.claude/skills/lorelang/` is in sync with `skills/lorelang/`

## Publishing to ClawHub (OpenClaw)

### Prerequisites

- GitHub account (at least 1 week old)
- `clawhub` CLI installed: `npm install -g clawhub`

### Steps

```bash
# 1. Authenticate
clawhub login

# 2. Verify
clawhub whoami

# 3. Publish
clawhub publish skills/lorelang \
  --slug lorelang \
  --name "Lorelang" \
  --version 0.2.1 \
  --changelog "Initial release: full CLI support for AI agent autonomous ontology management"

# 4. Verify on clawhub.ai
```

### Updating

```bash
clawhub publish skills/lorelang \
  --slug lorelang \
  --version 0.2.2 \
  --changelog "Description of changes"
```

## Publishing to Vercel Skills.sh

Skills.sh uses a GitHub-first model. No explicit publish command.

### Steps

1. Push the skill to a public GitHub repository
2. Users install via: `npx skills add lorelang/lore`
3. The skill appears on the skills.sh leaderboard automatically as installs grow

### Validation

```bash
npx skills check skills/lorelang
```

## Publishing as Claude Code Plugin

### For Users

Users can add the skill directly from GitHub:

```bash
# Add the marketplace
/plugin marketplace add lorelang/lore

# Install the skill
/plugin install lorelang:lorelang
```

### For Organizations

Copy the skill into your project:

```bash
# Project-level (committed to repo)
cp -r skills/lorelang .claude/skills/lorelang

# Personal (local only)
cp -r skills/lorelang ~/.claude/skills/lorelang
```

## Publishing to SkillHub

SkillHub (skillhub.club) automatically evaluates published skills. Steps:

1. Ensure the skill is published on ClawHub or available on GitHub
2. SkillHub crawls and evaluates new skills automatically
3. Skills are rated on: Practicality, Clarity, Automation, Quality, Impact

## Publishing to PyPI (the CLI itself)

The skill depends on the `lore-ontology` Python package. To publish:

```bash
# Build
make build

# Check dist
make dist-check

# Upload to PyPI
python3 -m twine upload dist/*
```

## Skill Format Notes

The SKILL.md uses the Agent Skills open standard (agentskills.io/specification):

- **name**: Lowercase, hyphens only, max 64 chars
- **description**: What the skill does AND when to use it (critical for discovery). Include NOT clause for exclusions.
- **metadata**: Includes both standard fields and OpenClaw-specific requirements
- **OpenClaw metadata**: Single-line JSON under `metadata.openclaw` with binary requirements, OS support, and install instructions
- **allowed-tools**: Pre-approved tools for the skill

The skill body follows progressive disclosure:
- SKILL.md: Overview and quick reference (under 500 lines)
- references/CLI.md: Complete CLI documentation
- references/FORMAT.md: Complete file format reference
- references/WORKFLOWS.md: Step-by-step workflows

## Manifest Locations

There are two `plugin.json` files and two `SKILL.md` copies. This is intentional -- each marketplace has its own manifest convention, and the repo must satisfy all of them.

| File | Location | Marketplace | Purpose |
|------|----------|-------------|---------|
| `plugin.json` | `.claude-plugin/` | Claude Code | Repo-level plugin manifest. Claude Code reads this when a user runs `/plugin marketplace add` or `claude --plugin-dir`. Points to `skills/` so Claude Code can discover the skill. |
| `marketplace.json` | `.claude-plugin/` | Claude Code | Marketplace index. Lists all plugins in this repo for the `/plugin install` discovery flow. |
| `plugin.json` | `skills/lorelang/` | ClawHub (OpenClaw) | Skill-level package manifest. `clawhub publish skills/lorelang` reads this file to get the name, version, keywords, and `skillsPath` for the OpenClaw registry. |
| `SKILL.md` | `skills/lorelang/` | All | The skill itself, following the Agent Skills open standard. Read by ClawHub, skills.sh, and Claude Code. The `metadata.openclaw` field in the frontmatter carries OpenClaw-specific install requirements. |
| `SKILL.md` | `.claude/skills/lorelang/` | Claude Code (project) | Copy of the skill for project-level use when working inside this repo. Must be kept in sync with `skills/lorelang/SKILL.md`. |

### Why two plugin.json?

- **Claude Code** looks for `.claude-plugin/plugin.json` at the repo root. It uses this to register the repo as a plugin and find the `skills/` directory.
- **ClawHub/OpenClaw** looks for `plugin.json` inside the skill directory being published (`skills/lorelang/`). It uses this for registry metadata like version, namespace, and keywords.

Different ecosystems, different conventions. Both are required if you want to publish to both marketplaces. If you only target one marketplace, you only need that marketplace's manifest.
