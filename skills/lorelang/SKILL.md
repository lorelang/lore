---
name: lorelang
description: Create, manage, validate, and compile Lore ontologies -- human-readable domain knowledge files for the AI age. Use when working with .lore files, ontology directories, domain modeling, knowledge graphs, knowledge engineering, or when the user mentions Lore, lorelang, ontology, or domain knowledge.
license: Apache-2.0
compatibility: Requires Python 3.10+ and lore-ontology package (pip install lore-ontology). Works on macOS and Linux.
metadata: {"author": "lorelang", "version": "0.2.1", "tags": ["ontology", "domain-modeling", "knowledge-graph", "ai-first", "lore", "knowledge-engineering"], "repository": "https://github.com/lorelang/lore", "openclaw": {"requires": {"bins": ["python3", "lore"]}, "homepage": "https://github.com/lorelang/lore", "os": ["darwin", "linux"], "install": [{"kind": "uv", "package": "lore-ontology"}], "emoji": "\ud83c\udfdb\ufe0f"}}
allowed-tools: Read Write Edit Bash Glob Grep
---

# Lore: Human-Readable Ontology Format

Lore encodes domain knowledge in prose-first `.lore` files that both humans and AI agents can author, review, and reason over. A single ontology compiles to knowledge graphs, agent prompts, embeddings, JSON schemas, and more.

## Install

```bash
pip install lore-ontology
```

## Quick Start

```bash
# Bootstrap a new domain ontology
lore setup my-domain --domain "Customer Success Operations"

# Validate
lore validate my-domain/

# Compile to AI agent context
lore compile my-domain/ -t agent

# List everything in the ontology
lore list my-domain/

# Search across ontology
lore search my-domain/ "churn risk"
```

## Ontology Structure

```
ontology/
  lore.yaml              # manifest (name, version, domain, evolution config)
  entities/              # domain concepts (.lore files)
  relationships/         # how entities connect
  rules/                 # business logic and constraints
  taxonomies/            # classification hierarchies
  glossary/              # canonical term definitions
  views/                 # team-scoped perspectives
  observations/          # field notes and claims
  outcomes/              # retrospectives with takeaways
  decisions/             # operational decisions
```

## Core Workflow for AI Agents

1. **Setup**: `lore setup <dir> --domain "<description>"` -- creates full starter ontology
2. **Author**: Write `.lore` files directly in entities/, relationships/, rules/, etc.
3. **Validate**: `lore validate <dir>` -- check for errors (use `--json` for machine output)
4. **Compile**: `lore compile <dir> -t <target>` -- compile to any target format
5. **Curate**: `lore curate <dir>` -- run health checks (staleness, coverage, consistency)
6. **Evolve**: `lore evolve <dir>` -- generate improvement proposals from outcomes
7. **Review**: `lore review <path> --decision accept --reviewer <id>` -- accept/reject proposals

## File Format Quick Reference

### Entity (entities/*.lore)

```
---
entity: Account
description: A company that is a customer or prospect.
status: stable
---

## Attributes

name: string [required, unique]
  | Legal entity name.

health_score: float [0.0 .. 100.0]
  | Composite health metric.

## Identity

An account is uniquely identified by its primary web domain.

## Notes

Free-form prose about edge cases, reasoning guidance, etc.
```

### Relationship (relationships/*.lore)

```
---
domain: Account Relationships
description: How accounts connect to other entities.
---

## HAS_SUBSCRIPTION
  from: Account -> to: Subscription
  cardinality: one-to-many
  | An account can have multiple subscriptions.

## Traversal: revenue-path
  path: Account -[HAS_SUBSCRIPTION]-> Subscription -[SUBSCRIBES_TO]-> Product
  | What products does this account use?
```

### Rule (rules/*.lore)

```
---
domain: Risk Rules
description: Rules for detecting risk signals.
---

## churn-risk-alert
  applies_to: Account
  severity: critical
  trigger: Usage decline detected

  condition:
    Account.health_score < 40
    AND Account.stage = "active"

  action:
    Set Account.stage = "at-risk"
    Notify csm_owner
```

For complete format reference: see [FORMAT.md](references/FORMAT.md)

## CLI Commands

Most commands auto-detect the ontology directory by walking up from CWD looking for `lore.yaml`. You only need to pass a directory when creating (`init`, `setup`) or comparing (`diff`).

| Command | Purpose |
|---------|---------|
| `lore version` | Show version |
| `lore init <dir>` | Scaffold minimal ontology |
| `lore setup <dir>` | AI-first domain bootstrap |
| `lore add <type> <name>` | Scaffold a new .lore file |
| `lore validate [--json]` | Validate syntax and semantics |
| `lore compile -t <target> [-o file]` | Compile to target format |
| `lore list [--type T] [--json]` | List ontology contents |
| `lore show <name> [--json]` | Show item details |
| `lore search <query> [--json]` | Full-text search |
| `lore stats [--json]` | Show statistics |
| `lore viz` | ASCII entity graph |
| `lore curate [--json]` | Run health checks |
| `lore evolve` | Generate proposals from outcomes |
| `lore ingest transcript` | Ingest meeting transcripts |
| `lore ingest memory` | Ingest memory exports |
| `lore review <path>` | Review proposals |
| `lore diff <dir1> <dir2>` | Compare ontologies |
| `lore index` | Generate routing indexes |

Compilation targets: `agent`, `json`, `jsonld`, `neo4j`, `embeddings`, `mermaid`, `palantir`, `tools`, `agents.md`, `metrics`

For complete CLI reference: see [CLI.md](references/CLI.md)

## AI Agent Autonomous Workflow

An AI agent can fully manage a Lore ontology using only the filesystem and CLI:

1. **Bootstrap**: `lore setup my-domain --domain "Target Domain"`
2. **Scaffold files**: `lore add entity "Account"` (from inside the ontology dir)
3. **Author**: Edit the scaffolded files or write `.lore` files directly
4. **Define relationships**: `lore add relationship "Links" --from-entity A --to-entity B`
5. **Validate continuously**: `lore validate --json` after each change
6. **Compile for use**: `lore compile -t agent` to get agent-ready context
7. **Monitor health**: `lore curate --json` to detect staleness and gaps
8. **Learn from outcomes**: Write outcomes with `Takeaway:` markers, then `lore evolve`
9. **Review proposals**: `lore review proposals/ --decision accept --reviewer agent`

All commands return exit codes (0 = success, 1 = error) and support `--json` for machine-readable output where applicable.

For detailed workflows: see [WORKFLOWS.md](references/WORKFLOWS.md)
