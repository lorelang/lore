---
name: lorelang
description: Create, manage, validate, and compile Lore ontologies -- human-readable domain knowledge files for the AI age. Activate on .lore files, ontology directories, domain modeling, knowledge graphs, knowledge engineering, lore.yaml, or when the user mentions Lore, lorelang, ontology, or domain knowledge. NOT for general file editing, non-ontology YAML, or database schema design.
license: Apache-2.0
compatibility: Requires Python 3.10+ and lore-ontology package (pip install lore-ontology). Works on macOS and Linux.
metadata: {"author": "lorelang", "version": "0.2.1", "tags": ["ontology", "domain-modeling", "knowledge-graph", "ai-first", "lore", "knowledge-engineering"], "repository": "https://github.com/lorelang/lore", "openclaw": {"requires": {"bins": ["python3", "lore"]}, "homepage": "https://github.com/lorelang/lore", "os": ["darwin", "linux"], "install": [{"kind": "uv", "package": "lore-ontology"}], "emoji": "\ud83c\udfdb\ufe0f"}}
allowed-tools: Read Write Edit Bash Glob Grep
---

# Lore: Human-Readable Ontology Format

Work with Lore ontologies -- prose-first `.lore` files that encode domain knowledge for humans and machines. A single ontology compiles to knowledge graphs, agent prompts, embeddings, JSON schemas, and more.

## When to Use

**Use for:**
- Bootstrapping new domain ontologies (`lore setup`)
- Authoring and editing `.lore` files (entities, relationships, rules, taxonomies, glossary, views, observations, outcomes, decisions)
- Validating ontology syntax and semantics
- Compiling ontologies to target formats (agent context, JSON, Neo4j, embeddings, Mermaid, tools)
- Running health checks, evolving ontologies from outcomes, reviewing proposals
- Any task involving `lore.yaml`, `.lore` files, or ontology directories

**NOT for:**
- General YAML/Markdown editing unrelated to Lore
- Database schema design (use Lore only for domain knowledge modeling)
- Writing application code that consumes compiled output

## Install

```bash
pip install lore-ontology
```

Verify: `lore version`

## Core Workflow

Follow this sequence when working with Lore ontologies. All commands auto-detect the ontology directory from CWD by walking up to find `lore.yaml`.

### 1. Bootstrap

```bash
lore setup my-domain --domain "Customer Success Operations"
cd my-domain
```

### 2. Scaffold and Author

```bash
# Scaffold files with correct frontmatter
lore add entity "Account" --description "A company that is a customer or prospect."
lore add relationship "Account Contacts" --from-entity Account --to-entity Contact --cardinality one-to-many
lore add rule "Churn Alert" --applies-to Account --severity critical

# Then edit the scaffolded .lore files to add attributes, conditions, and prose
```

### 3. Validate After Every Change

```bash
lore validate          # human-readable output
lore validate --json   # machine-readable, parse for errors/warnings
```

Always validate after editing `.lore` files. Parse `--json` output to detect and fix errors programmatically.

### 4. Compile

```bash
lore compile -t agent                          # AI agent system prompt
lore compile -t agent --view "Account Exec" --budget 4000  # scoped + projected
lore compile -t json -o ontology.json          # JSON for APIs
lore compile -t neo4j -o schema.cypher         # graph database
lore compile -t embeddings -o chunks.jsonl     # vector store chunks
lore compile -t mermaid -o diagram.mmd         # visual diagram
lore compile -t tools -o tools.json            # function-calling schemas
```

Targets: `agent`, `json`, `jsonld`, `neo4j`, `embeddings`, `mermaid`, `palantir`, `tools`, `agents.md`, `metrics`

### 5. Query and Explore

```bash
lore list                          # everything in the ontology
lore list --type entities --json   # filtered, machine-readable
lore show Account --json           # entity details
lore search "churn risk" --json    # full-text search
lore stats --json                  # ontology statistics
lore viz                           # ASCII entity graph
```

### 6. Curate and Evolve

```bash
lore curate --json                 # run all health checks
lore curate --job staleness        # specific check
lore evolve                        # generate proposals from outcome takeaways
lore review proposals/ --decision accept --reviewer agent
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

For complete format reference, read `references/FORMAT.md`.

## CLI Quick Reference

Most commands auto-detect the ontology from CWD. Only `setup`, `init`, and `diff` require explicit directory arguments.

| Command | Purpose |
|---------|---------|
| `lore version` | Show version |
| `lore setup <dir>` | Bootstrap new ontology |
| `lore add <type> <name>` | Scaffold a .lore file |
| `lore validate [--json]` | Check syntax and semantics |
| `lore compile -t <target>` | Compile to target format |
| `lore list [--type T] [--json]` | List ontology contents |
| `lore show <name> [--json]` | Show item details |
| `lore search <query> [--json]` | Full-text search |
| `lore stats [--json]` | Ontology statistics |
| `lore viz` | ASCII entity graph |
| `lore curate [--json]` | Run health checks |
| `lore evolve` | Generate proposals from outcomes |
| `lore review <path>` | Accept or reject proposals |
| `lore diff <dir1> <dir2>` | Compare two ontologies |
| `lore index` | Generate routing indexes |
| `lore ingest transcript` | Ingest meeting transcripts |
| `lore ingest memory` | Ingest memory exports |

All commands return exit code 0 on success, 1 on error. Commands with `--json` output valid JSON to stdout.

For complete CLI reference, read `references/CLI.md`.

## Key Conventions

- **Directory auto-detection**: Run commands from inside the ontology directory (or any subdirectory). The CLI walks up looking for `lore.yaml`.
- **File types**: `entity`, `relationship`, `rule`, `taxonomy`, `glossary`, `view`, `observation`, `outcome`, `decision`
- **Status lifecycle**: `draft` -> `proposed` -> `stable` -> `deprecated`
- **Validation-first**: Always run `lore validate` after modifying `.lore` files.
- **Machine output**: Use `--json` on `validate`, `list`, `show`, `search`, `stats`, `curate` for structured output.

## References

Consult these for detailed documentation -- they are not loaded automatically:

| File | Consult When |
|------|-------------|
| `references/CLI.md` | Looking up exact command syntax, flags, or options |
| `references/FORMAT.md` | Writing or editing `.lore` files and need the full format specification |
| `references/WORKFLOWS.md` | Following step-by-step guides for common operations (bootstrap, ingest, evolve, curate) |
