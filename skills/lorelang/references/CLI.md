# Lore CLI Reference

Complete reference for all `lore` commands. Every command returns exit code 0 on success, 1 on error. Commands with `--json` produce machine-readable JSON on stdout.

## lore version

Show installed version.

```bash
lore version
# Output: lore 0.2.1
```

## lore init

Scaffold a minimal ontology directory.

```bash
lore init <dir> [--name NAME] [--domain DESCRIPTION]
```

- `dir` -- Target directory (must be empty or not exist)
- `--name` -- Ontology name (default: directory name)
- `--domain` -- Domain description

Creates: `lore.yaml`, all standard directories, one example entity.

## lore setup

AI-first domain bootstrap with governance defaults. Preferred over `init` for production use.

```bash
lore setup <dir> [--name NAME] [--domain DESCRIPTION] [--maintainer NAME]
    [--role ROLE] [--proposals MODE] [--staleness WINDOW]
```

- `--maintainer` -- Primary maintainer (default: "Domain Team")
- `--role` -- Maintainer role (default: "Domain Owner")
- `--proposals` -- Evolution mode: `open`, `review-required`, `closed` (default: review-required)
- `--staleness` -- Freshness window, e.g. `45d`, `12h`, `3m` (default: 45d)

Creates: Full starter ontology with entity, relationship, rules, taxonomy, glossary, view, observations, outcomes.

Aliases: `/setup`, `lore:setup`, `/lore:setup`

## lore add

Scaffold a new `.lore` file with correct frontmatter in the right directory.

```bash
lore add <type> <dir> <name> [--description DESC] [--status STATUS]
```

Types: `entity`, `relationship`, `rule`, `taxonomy`, `glossary`, `view`, `observation`, `outcome`, `decision`

Type-specific options:

```bash
# Entity with inheritance
lore add entity my-domain/ "Premium Account" --inherits Account

# Relationship
lore add relationship my-domain/ "Account Contacts" \
  --from-entity Account --to-entity Contact --cardinality one-to-many

# Rule
lore add rule my-domain/ "Churn Alert" \
  --applies-to Account --severity critical

# Observation
lore add observation my-domain/ "Q1 Discovery" --about Account
```

Creates a file with correct frontmatter, provenance, and placeholder sections. Exit code 1 if file already exists (prints path to edit instead).

## lore validate

Check syntax and semantics.

```bash
lore validate <dir> [--json]
```

Human output shows errors, warnings, info. JSON output:

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

Compile ontology to a target format.

```bash
lore compile <dir> -t TARGET [-o FILE] [--view NAME] [--budget TOKENS]
```

- `-t/--target` -- Required. One of: `neo4j`, `json`, `jsonld`, `agent`, `embeddings`, `mermaid`, `palantir`, `tools`, `agents.md`, `metrics`, or a plugin compiler name
- `-o/--output` -- Write to file instead of stdout
- `--view` -- Scope to a named view (agent target)
- `--budget` -- Token budget for agent target (enables projection)

Examples:

```bash
lore compile my-domain/ -t agent --view "Account Executive" --budget 4000
lore compile my-domain/ -t json -o ontology.json
lore compile my-domain/ -t neo4j -o schema.cypher
lore compile my-domain/ -t embeddings -o chunks.jsonl
lore compile my-domain/ -t mermaid -o diagram.mmd
```

## lore list

List all items in the ontology.

```bash
lore list <dir> [--type TYPE] [--status STATUS] [--json]
```

- `--type` -- Filter: `entities`, `relationships`, `rules`, `taxonomies`, `glossary`, `views`, `observations`, `outcomes`, `decisions`
- `--status` -- Filter: `draft`, `proposed`, `stable`, `deprecated`
- `--json` -- JSON array output

```bash
lore list my-domain/ --type entities --json
lore list my-domain/ --status draft
```

## lore show

Show details of a named entity, relationship, rule, view, traversal, or glossary term.

```bash
lore show <dir> <name> [--json]
```

Looks up by name (case-insensitive) across all types. Shows attributes, relationships, rules, and metadata.

```bash
lore show my-domain/ Account --json
lore show my-domain/ "Account Executive"
lore show my-domain/ HAS_SUBSCRIPTION
```

## lore search

Full-text search across all prose in the ontology.

```bash
lore search <dir> <query> [--limit N] [--json]
```

- `--limit` -- Max results (default: 20)
- `--json` -- JSON array with type, name, text, score

```bash
lore search my-domain/ "churn risk" --json
lore search my-domain/ "workflow automation" --limit 5
```

## lore stats

Show ontology statistics.

```bash
lore stats <dir> [--json]
```

JSON output includes full entity detail breakdown.

## lore viz

ASCII visualization of entity relationship graph.

```bash
lore viz <dir>
```

## lore curate

Run curation health checks.

```bash
lore curate <dir> [--job JOB] [--dry-run] [--json]
```

- `--job` -- One of: `staleness`, `coverage`, `consistency`, `index`, `summarize`, `all` (default: all), or a plugin curator name
- `--dry-run` -- Report only, don't generate proposals
- `--json` -- JSON array of report objects

## lore evolve

Generate improvement proposals from outcome takeaways.

```bash
lore evolve <dir> [-o OUTPUT_DIR]
```

Reads outcomes/ for `Takeaway:` markers and generates proposals/ files.

## lore ingest transcript

Ingest a meeting transcript into observations.

```bash
lore ingest transcript <dir> --input FILE --about ENTITY
    [--name NAME] [--observed-by ID] [--confidence FLOAT]
    [--source LABEL] [--date YYYY-MM-DD] [--output FILE]
    [--max-sections N]
```

## lore ingest memory

Ingest a memory export (JSON/JSONL) into observations.

```bash
lore ingest memory <dir> --adapter ADAPTER --input FILE --about ENTITY
    [--name NAME] [--observed-by ID] [--confidence FLOAT]
    [--source LABEL] [--date YYYY-MM-DD] [--output FILE]
    [--max-sections N]
```

Adapters: `arscontexta`, `mem0`, `graphiti`

## lore review

Apply review decisions to proposal files.

```bash
lore review <path> --decision DECISION --reviewer ID [--note TEXT] [--all]
```

- `path` -- Single proposal file or proposals/ directory
- `--decision` -- `accept` or `reject`
- `--reviewer` -- Reviewer identity string
- `--all` -- Include already-reviewed files

## lore diff

Compare two ontology directories.

```bash
lore diff <dir1> <dir2> [--json]
```

## lore index

Generate INDEX.lore routing files for each directory.

```bash
lore index <dir>
```
