# Lore CLI Reference

Every command returns exit code 0 on success, 1 on error.

## Directory Auto-Detection

Most commands auto-detect the ontology directory by walking up from the current working directory looking for `lore.yaml`. You can always override by passing the directory explicitly as the last positional argument.

```bash
# These are equivalent when running from inside an ontology:
lore validate
lore validate /path/to/ontology

# Auto-detection also works from subdirectories:
cd my-ontology/entities/
lore list  # finds my-ontology/ via lore.yaml
```

Commands that REQUIRE a directory argument: `init`, `setup` (create new), `diff` (compare two).

## lore version

```bash
lore version
```

## lore init

Scaffold a minimal ontology directory.

```bash
lore init <dir> [--name NAME] [--domain DESCRIPTION]
```

Creates: `lore.yaml`, all standard directories, one example entity.

## lore setup

AI-first domain bootstrap with governance defaults. Preferred over `init`.

```bash
lore setup <dir> [--name NAME] [--domain DESCRIPTION] [--maintainer NAME]
    [--role ROLE] [--proposals MODE] [--staleness WINDOW]
```

- `--proposals` -- `open`, `review-required` (default), `closed`
- `--staleness` -- Freshness window, e.g. `45d`, `12h`, `3m` (default: 45d)

Aliases: `/setup`, `lore:setup`, `/lore:setup`

## lore add

Scaffold a new `.lore` file with correct frontmatter in the right directory.

```bash
lore add <type> <name> [dir] [--description DESC] [--status STATUS]
```

Types: `entity`, `relationship`, `rule`, `taxonomy`, `glossary`, `view`, `observation`, `outcome`, `decision`

Type-specific options:

```bash
# Entity with inheritance
lore add entity "Premium Account" --inherits Account

# Relationship (--from-entity and --to-entity are required)
lore add relationship "Account Contacts" \
  --from-entity Account --to-entity Contact --cardinality one-to-many

# Rule (--applies-to recommended)
lore add rule "Churn Alert" --applies-to Account --severity critical

# Observation (--about is required)
lore add observation "Q1 Discovery" --about Account
```

Exit code 1 if file already exists (prints path to edit instead).

## lore validate

```bash
lore validate [dir] [--json]
```

JSON output:

```json
{
  "valid": true,
  "errors": [],
  "warnings": ["..."],
  "info": ["..."]
}
```

Exit code 1 if any errors.

## lore compile

```bash
lore compile [dir] -t TARGET [-o FILE] [--view NAME] [--budget TOKENS]
```

- `-t/--target` -- Required. Built-in: `neo4j`, `json`, `jsonld`, `agent`, `embeddings`, `mermaid`, `palantir`, `tools`, `agents.md`, `metrics`
- `-o/--output` -- Write to file instead of stdout
- `--view` -- Scope to a named view (`agent` and `agents.md` targets)
- `--budget` -- Token budget (`agent` target, enables projection)

```bash
lore compile -t agent --view "Account Executive" --budget 4000
lore compile -t json -o ontology.json
lore compile -t neo4j -o schema.cypher
lore compile -t embeddings -o chunks.jsonl
```

## lore list

```bash
lore list [dir] [--type TYPE] [--status STATUS] [--json]
```

- `--type` -- `entities`, `relationships`, `rules`, `taxonomies`, `glossary`, `views`, `observations`, `outcomes`, `decisions`
- `--status` -- `draft`, `proposed`, `stable`, `deprecated`

```bash
lore list --type entities --json
lore list --status draft
```

## lore show

Show details of a named entity, relationship, rule, view, traversal, or glossary term. Looks up by name (case-insensitive) across all types.

```bash
lore show <name> [dir] [--json]
```

```bash
lore show Account --json
lore show "Account Executive"
lore show HAS_SUBSCRIPTION
```

## lore search

Full-text search across all prose in the ontology.

```bash
lore search <query> [dir] [--limit N] [--json]
```

```bash
lore search "churn risk" --json
lore search "workflow automation" --limit 5
```

## lore stats

```bash
lore stats [dir] [--json]
```

JSON output includes full entity detail breakdown.

## lore viz

```bash
lore viz [dir]
```

## lore curate

```bash
lore curate [dir] [--job JOB] [--dry-run] [--json]
```

- `--job` -- `staleness`, `coverage`, `consistency`, `index`, `summarize`, `all` (default), or plugin name
- `--dry-run` -- Report only

## lore evolve

```bash
lore evolve [dir] [-o OUTPUT_DIR]
```

Reads outcomes/ for `Takeaway:` markers and generates proposals/ files.

## lore ingest transcript

```bash
lore ingest transcript [dir] --input FILE --about ENTITY
    [--name NAME] [--observed-by ID] [--confidence FLOAT]
    [--source LABEL] [--date YYYY-MM-DD] [--output FILE]
    [--max-sections N]
```

## lore ingest memory

```bash
lore ingest memory [dir] --adapter ADAPTER --input FILE --about ENTITY
    [--name NAME] [--observed-by ID] [--confidence FLOAT]
    [--source LABEL] [--date YYYY-MM-DD] [--output FILE]
    [--max-sections N]
```

Adapters: `arscontexta`, `mem0`, `graphiti`

## lore review

```bash
lore review <path> --decision DECISION --reviewer ID [--note TEXT] [--all]
```

- `--decision` -- `accept` or `reject` (required)
- `--reviewer` -- Reviewer identity (required)

## lore diff

```bash
lore diff <dir1> <dir2> [--json]
```

## lore index

```bash
lore index [dir]
```
