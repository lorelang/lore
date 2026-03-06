# Publishing the Lorelang Skill

This document covers how to publish the Lore ontology skill to the various AI agent skill marketplaces.

## Skill Package Location

```
skills/
  lorelang/
    SKILL.md                # Main skill file (Agent Skills + OpenClaw metadata)
    plugin.json             # Plugin manifest
    references/
      CLI.md                # CLI reference
      FORMAT.md             # File format reference
      WORKFLOWS.md          # Workflow guides
  marketplace.json          # Marketplace distribution manifest
```

The same skill is also available at `.claude/skills/lorelang/` for project-level use.

## Pre-Publishing Checklist

- [ ] All tests pass: `make launch-check`
- [ ] SKILL.md frontmatter has correct version matching `pyproject.toml`
- [ ] `plugin.json` version matches
- [ ] `lore-ontology` package is published on PyPI
- [ ] All CLI commands referenced in the skill work correctly
- [ ] Reference files are up to date with current CLI

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
- **description**: What the skill does AND when to use it (critical for discovery)
- **metadata**: Includes both standard fields and OpenClaw-specific requirements
- **OpenClaw metadata**: Single-line JSON under `metadata.openclaw` with binary requirements, OS support, and install instructions
- **allowed-tools**: Pre-approved tools for the skill

The skill body follows progressive disclosure:
- SKILL.md: Overview and quick reference (under 500 lines)
- references/CLI.md: Complete CLI documentation
- references/FORMAT.md: Complete file format reference
- references/WORKFLOWS.md: Step-by-step workflows
