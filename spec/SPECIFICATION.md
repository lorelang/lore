# Lore Specification v0.2.0

**Lore** is a human-readable, machine-parseable format for defining domain ontologies. It is designed to be authored by domain experts and AI agents, version-controlled in git, and compiled to multiple execution targets (knowledge graphs, AI agent contexts, embedding indexes, JSON schemas).

Lore files use the `.lore` extension.

**Tagline:** Lore — the self-updating ontology.

## What Lore Is

Lore is a **language and a compiler** for domain knowledge. It defines how you describe a domain (entities, relationships, rules, prose) and provides tooling to validate, compile, curate, and evolve that description over time.

Lore is a **source format**, not a runtime. It produces artifacts (agent prompts, graph schemas, embeddings, JSON) that other systems consume. It is a **sedimentation layer** — the place where distilled, validated domain knowledge lives after being extracted from conversations, databases, expert interviews, or AI agent observations.

## What Lore Is Not

Lore is **not a conversation memory store**. Agent interaction memory (what did the agent learn from talking to Sarah on Tuesday) belongs in runtime memory systems like Agno Learning Stores, Mem0, or Zep. Lore holds the distilled insight that emerges from 1000 conversations — not the conversations themselves.

Lore is **not an agent framework**. It does not route tasks, manage agent lifecycles, or coordinate multi-agent workflows. Agent orchestration belongs in LangGraph, CrewAI, Agno, or similar. Lore provides the domain knowledge those agents reason over.

Lore is **not a runtime query engine**. If you need real-time graph queries, compile to Neo4j and query there. If you need vector search, compile to embeddings and index them. Lore is the source, not the database.

## Scope Boundaries

| Concern | In Scope | Out of Scope |
|---------|----------|-------------|
| Domain knowledge | Entities, relationships, rules, taxonomies, glossary, prose | Raw conversation logs, interaction traces |
| Knowledge lifecycle | Author → validate → compile → observe → outcomes → evolve | Real-time streaming, pub/sub, event sourcing |
| Agent context | Compiled system prompts, embedding chunks, structured JSON | Agent memory, session state, user profiles |
| Quality assurance | Validation (correctness) + curation (quality) | Runtime monitoring, APM, alerting |
| Contradiction handling | Detection and annotation in compiled output | Runtime resolution, automatic merging |
| Versioning | Git (file-level diffs, branches, PRs) | Per-entity version numbers, temporal queries |
| Extensibility | Custom compilers, custom curators, custom file types via plugins | Custom runtimes, agent SDKs, hosted services |

## Design Principles

1. **Reads like documentation.** A non-technical domain expert should be able to read and edit `.lore` files without training.
2. **Parses like code.** The format has a deterministic grammar that tooling can parse without ambiguity.
3. **Lives in git.** File structure, diffs, and merge conflicts should be manageable using standard git workflows.
4. **Compiles to anything.** `.lore` is a source format, not a runtime format. It compiles to Neo4j Cypher, JSON-LD, AI agent prompts, embedding chunks, or any other target.
5. **Prose where meaning is rich, structure where precision matters.** Lore supports both formal attribute definitions and freeform prose descriptions. The format doesn't force you to formalize what's better said in natural language.
6. **AI agents are first-class authors.** The format is as easy for an LLM to write as for a human. An LLM that has seen one example `.lore` file should be able to write another without documentation.
7. **Every feature is opt-in.** No provenance block? Fine. No observations directory? Fine. The ontology still works.
8. **Extensible by default.** Custom compilers, custom curators, and custom directories are first-class. The core is small; the ecosystem grows through plugins.

## File Types

Lore recognizes eight file types, determined by their location in the directory structure:

| Directory          | Purpose                          | Defines                          |
|-------------------|----------------------------------|----------------------------------|
| `entities/`       | Domain concepts                  | Entities, attributes, identity   |
| `relationships/`  | How entities connect             | Edges, cardinality, properties   |
| `rules/`          | Business logic and constraints   | Conditions, actions, triggers    |
| `taxonomies/`     | Classification hierarchies       | Trees of types/categories        |
| `glossary/`       | Canonical term definitions       | Authoritative meanings           |
| `views/`          | Team-scoped perspectives         | Filtered slices of the ontology  |
| `observations/`   | AI agent and expert field notes  | What was observed in the domain  |
| `outcomes/`       | Retrospectives                   | What actually happened           |

A root `lore.yaml` manifest describes the ontology metadata.

## Manifest (`lore.yaml`)

```yaml
name: my-ontology
version: 0.2.0
description: A brief description of this domain ontology
domain: The business domain this covers
maintainers:
  - name: Jane Smith
    role: Domain Owner
    email: jane@example.com

# Optional: enable the self-updating loop
evolution:
  proposals: open          # open | review-required | closed
  staleness: 90d           # flag observations older than this
```

### Evolution Config

| Field        | Values                              | Purpose                                     |
|-------------|-------------------------------------|---------------------------------------------|
| `proposals` | `open`, `review-required`, `closed` | Controls whether `lore evolve` generates proposals |
| `staleness` | Duration string (e.g., `90d`)       | Flag observations older than this as stale   |

## Provenance and Status

All `.lore` file types support optional `provenance` and `status` fields in their YAML frontmatter. These transform Lore from static documentation into knowledge with a traceable source.

### Provenance Block

```yaml
provenance:
  author: revops-team           # Who or what created this
  source: domain-expert         # How it was created
  confidence: 0.95              # How much to trust it (0.0-1.0)
  created: 2025-01-15           # When this knowledge was created
  deprecated: 2025-06-01        # When it became stale (only if status: deprecated)
```

| Field        | Type    | Description                                              |
|-------------|---------|----------------------------------------------------------|
| `author`    | string  | Person, team, or agent that created this knowledge       |
| `source`    | string  | `domain-expert`, `ai-generated`, `imported`, `derived`   |
| `confidence`| float   | Trust level from 0.0 to 1.0                              |
| `created`   | date    | ISO date (YYYY-MM-DD) when knowledge was created         |
| `deprecated`| date    | ISO date when knowledge became stale                     |

### Status

```yaml
status: stable    # draft | proposed | stable | deprecated
```

| Status       | Meaning                                                    |
|-------------|-----------------------------------------------------------|
| `draft`     | Work in progress, not yet reviewed                         |
| `proposed`  | Suggested (often by AI), awaiting human review             |
| `stable`    | Reviewed and accepted as reliable                          |
| `deprecated`| No longer current, kept for historical reference           |

All fields are optional. Files without provenance or status work exactly as in v0.1.

## Format Grammar

### Frontmatter

Every `.lore` file begins with YAML frontmatter between `---` delimiters:

```
---
key: value
another_key: value
provenance:
  author: someone
  source: domain-expert
status: stable
---
```

Required frontmatter keys vary by file type (see below).

### Sections

Sections are denoted by `##` headers. Section names are significant and parsed by the toolchain.

```
## Section Name

Content goes here.
```

### Attributes

Attributes use the format:

```
attribute_name: type [constraints]
  | Description line 1
  | Description line 2
```

**Supported types:** `string`, `int`, `float`, `boolean`, `date`, `datetime`, `enum [val1, val2, ...]`, `list<Type>`, `-> EntityName` (reference), `text` (long-form).

**Constraints:** `[min .. max]` for numeric ranges, `[required]`, `[unique]`, `[optional]`.

**Annotations:** `@computed: path/to/rule#name`, `@deprecated: reason`, `@sensitive`, `@pii`.

### Relationships

Relationship blocks in `relationships/*.lore` files:

```
## RELATIONSHIP_NAME
  from: EntityA -> to: EntityB
  cardinality: one-to-many | many-to-many | one-to-one
  | Description of what this relationship means.

  properties:
    prop_name: type
      | Description
```

### Traversals

Named traversals define valid multi-hop reasoning paths:

```
## Traversal: traversal-name
  path: Entity1 -[REL1]-> Entity2 -[REL2]-> Entity3
  | Description of what question this traversal answers.
```

### Taxonomies

Taxonomies use ASCII tree notation:

```
RootConcept
├── ChildA
│   ├── GrandchildA1
│   └── GrandchildA2    @tag: some-tag
├── ChildB
└── ChildC
```

Tags can be applied to any node with `@tag: tag-name`.

### Rules

Rules have a semi-structured format:

```
## rule-name
  applies_to: EntityName
  severity: critical | warning | info
  trigger: description of when this fires

  condition:
    structured condition expression

  action:
    what happens when the condition is met

  Prose description providing additional context that an LLM
  can reason over but that doesn't need formal encoding.
```

The `condition` block supports a simple expression language:
- Comparisons: `entity.attribute > value`, `entity.attribute = value`
- Logical: `AND`, `OR`, `NOT`
- Aggregations: `count(...)`, `sum(...)`, `avg(...)`
- Path expressions: `Entity -[REL]-> OtherEntity`
- Set operations: `includes`, `excludes`

### Glossary

Glossary entries are simple:

```
## Term Name

Definition in prose. This is the canonical, authoritative
definition of this term within this domain.
```

### Views

Views define scoped perspectives:

```
---
view: ViewName
audience: Who this view is for
---

## Entities
- EntityA (attribute subset or "all")
- EntityB (specific attributes: attr1, attr2)

## Relationships
- RELATIONSHIP_NAME
- traversal-name

## Rules
- rule-name-1
- rule-name-2

## Key Questions
- What question can this view answer?
- Another question?
```

### Observations (v0.2)

Observations are prose-heavy field notes written by AI agents or humans. They record what was seen in the domain.

```
---
observations: Q2 Account Signals
about: Account
observed_by: expansion-agent-v2
date: 2025-06-15
confidence: 0.75
status: proposed
provenance:
  author: expansion-agent-v2
  source: ai-generated
  confidence: 0.75
  created: 2025-06-15
---

## Acme Corp shows expansion readiness

Acme Corp is showing classic multi-signal expansion
patterns over the past 30 days:

- Active users increased 45%
- Three new departments started using the product
- VP Engineering attended the enterprise webinar
```

| Frontmatter Field | Type   | Description                                |
|-------------------|--------|--------------------------------------------|
| `observations`    | string | Name of this observation collection        |
| `about`           | string | Entity name this observation relates to    |
| `observed_by`     | string | Agent or person who made the observation   |
| `date`            | date   | When the observation was made              |
| `confidence`      | float  | Confidence level (0.0-1.0)                 |

Each `##` section is one observation. The body is pure prose.

### Outcomes (v0.2)

Outcomes record what actually happened — retrospectives comparing predictions to reality.

```
---
outcomes: Q2 2025 Retrospective
reviewed_by: outcome-tracker-agent
date: 2025-07-01
---

## Acme Corp expansion — correct

We predicted Acme was expansion-ready (confidence: 0.82).
They expanded. Upsell closed for +$45K ARR.

Takeaway: increase weight of executive engagement signals

Ref: observations/q2-signals.lore#acme-corp-shows-expansion-readiness
```

| Frontmatter Field | Type   | Description                                |
|-------------------|--------|--------------------------------------------|
| `outcomes`        | string | Name of this retrospective                 |
| `reviewed_by`     | string | Agent or person who reviewed outcomes      |
| `date`            | date   | When the review was conducted              |

#### Inline Markers

Outcomes support two inline markers that are extracted by the parser:

- **`Takeaway:`** — A learning signal. The `lore evolve` command scans for these to generate improvement proposals.
- **`Ref:`** — A cross-reference to an observation file and heading. Format: `observations/filename.lore#heading-slug`.

### Prose Blocks

Any section can contain freeform prose paragraphs. These are preserved as-is for LLM reasoning but are not formally parsed for structure. This is by design — some knowledge is best expressed in natural language.

```
## Lifecycle

An account progresses through stages based on engagement
and commercial activity. New accounts start as "prospect"
and move to "onboarding" upon first contract signature.
```

## The Self-Updating Loop

Lore v0.2 introduces a feedback loop where AI agents can contribute back to the ontology:

```
  .lore files ──compile──> AI agent ──observe──> observations/
       ^                                              │
       │                                              v
  proposals/ <──evolve── outcomes/ <──record── AI agent acts
```

1. **Compile**: `.lore` files are compiled to an AI agent context.
2. **Observe**: The agent records field notes in `observations/`.
3. **Act**: The agent takes actions based on the ontology.
4. **Record**: The agent compares predictions to reality in `outcomes/`.
5. **Evolve**: `lore evolve` reads takeaways from outcomes and generates proposals.
6. **Review**: Humans review proposals and accept/reject them.

## Compilation Targets

The Lore toolchain compiles `.lore` files to:

| Target       | Output                  | Use Case                           |
|-------------|-------------------------|------------------------------------|
| `neo4j`     | Cypher DDL + constraints| Graph database schema              |
| `json`      | JSON representation     | API consumption, interop           |
| `agent`     | Structured prompt text  | AI agent system prompts            |
| `embeddings`| Chunked text + metadata | Vector store ingestion             |
| `mermaid`   | Mermaid diagram code    | Visual documentation               |
| `palantir`  | OntologyFullMetadata JSON| Palantir Foundry import           |

### Palantir Foundry Target

The `palantir` compiler generates JSON compatible with Palantir Foundry's OntologyFullMetadata schema. Lore concepts map to Palantir as follows:

| Lore | Palantir |
|------|----------|
| Entity | Object Type |
| Attribute | Property |
| Relationship | Link Type |
| Rule | Action Type (advisory) |
| Taxonomy | Property enum annotations |

The output can be imported into Foundry via Ontology Manager > Advanced > Import. Note: Palantir object types require backing datasources (Foundry datasets); the compiler generates placeholder RIDs that must be mapped to real datasets during import.

## Curation

`lore curate` runs opinionated health checks that go beyond validation. Validation asks "is this correct?" — curation asks "is this *good*?"

```
lore curate <dir>                     Run all curation jobs
lore curate <dir> --job staleness     Flag stale knowledge past its freshness window
lore curate <dir> --job coverage      Find gaps — missing Notes, orphaned entities
lore curate <dir> --job consistency   Find contradictions — attribute drift, taxonomy/enum mismatch
lore curate <dir> --job index         Check INDEX.lore files are present and up-to-date
lore curate <dir> --job summarize     Generate a natural-language health digest
lore curate <dir> --dry-run           Report only, suppress suggestions
```

### Curation Jobs

| Job           | LLM Required | What It Checks                                              |
|---------------|-------------|-------------------------------------------------------------|
| `staleness`   | No          | Files older than `evolution.staleness` window               |
| `coverage`    | No          | Missing Notes/Identity, orphaned entities, observation gaps |
| `consistency` | No          | Rules referencing missing attributes, taxonomy drift, observation contradictions |
| `index`       | No          | Missing or stale INDEX.lore routing files                   |
| `summarize`   | Optional    | Aggregates all findings into an executive digest            |

Jobs 1-4 are pure Python — zero API calls, works offline, suitable for CI. The `summarize` job optionally accepts an LLM function for a polished natural-language digest; without one, it falls back to a template.

### Curation vs. Validation

Validation (`lore validate`) checks structural correctness: broken references, duplicate names, missing required fields. These are errors and warnings about *syntax and semantics*.

Curation (`lore curate`) checks quality: is the ontology well-documented? Is knowledge fresh? Are rules referencing attributes that actually exist? These are opinions about *how good the ontology is for AI agent reasoning*.

An ontology can pass validation with zero errors but still have a poor curation score — for example, every entity has attributes but none have Notes sections, leaving AI agents without context.

## Contradiction Handling

As ontologies grow and multiple agents write observations, contradictions are inevitable. Agent A observes "Acme is expansion-ready" while Agent B observes "Acme shows churn signals." Both are in `observations/` and both get compiled into the agent context.

Lore handles contradictions at three levels:

### 1. Detection (Curator)

The `consistency` curation job detects contradictions:

- **Observation conflicts**: Two observations about the same entity with opposing signals (expansion vs. contraction keywords in headings/prose).
- **Observation vs. outcome drift**: High-confidence observations that outcomes later proved wrong.
- **Structural contradictions**: Rules referencing attributes that don't exist, taxonomy nodes that don't match enum values, glossary definitions that disagree with entity descriptions.

### 2. Annotation (Agent Compiler)

When the agent compiler detects conflicting observations about the same entity, it annotates the conflict in the compiled output rather than silently including both:

```
<observation conflict="true">
  Conflicting observations about Account:
  - "Acme shows expansion readiness" (confidence: 0.82, 15 days ago, by expansion-agent)
  - "Acme usage declining sharply" (confidence: 0.71, 45 days ago, by churn-detector)
  Consider recency and confidence when reasoning.
</observation>
```

The agent receives both observations plus the metadata to resolve the conflict itself. This is intentional — LLMs are good at weighing conflicting evidence when given the right context (confidence scores, recency, source).

### 3. Resolution (Human or Evolution)

Contradictions are not auto-resolved. They surface as:
- **Curator warnings**: `lore curate --job consistency` flags the conflict.
- **Outcome takeaways**: When the truth becomes known, outcomes record which observation was right, generating takeaways that `lore evolve` uses to adjust confidence or propose rule changes.
- **Status changes**: A human (or a review process) marks the wrong observation as `status: deprecated`.

This is a deliberate design choice. Automatic contradiction resolution (like Graphiti's temporal edge invalidation) requires a runtime database. Lore is a source format — contradictions are surfaced, annotated, and resolved through the normal review cycle, not through runtime graph operations.

## Observation Patterns

Observations are the most flexible file type in Lore. Beyond field notes, they support several common patterns:

### Decision Logs

Record agent reasoning for auditability:

```
---
observations: Expansion Agent Decisions — March
about: Account
observed_by: expansion-agent-v3
date: 2025-03-15
---

## Acme Corp — recommended tier upgrade

Recommended Enterprise upgrade based on: seat utilization 92%,
3 SSO requests in last 60 days, VP Engineering attended
enterprise webinar. Confidence: 0.84.

Chose tier-upgrade play over seat-expansion because the
feature ceiling signals (SSO, audit logs) outweigh the
seat growth signal.
```

### Domain Drift Notes

Record when real-world changes affect the ontology:

```
---
observations: Q1 Market Changes
about: Product
observed_by: product-team
date: 2025-03-01
confidence: 0.95
status: stable
---

## Pricing restructure effective April 1

Starter tier increasing from $29 to $39/seat. Professional
unchanged. Enterprise adding a new "Platform" sub-tier at
$149/seat with API-only access.

The Product entity and product-catalog taxonomy need updates.
```

### Cross-Entity Observations

Use `about:` with an empty value for observations that span multiple entities:

```
---
observations: Onboarding Funnel Analysis
about:
observed_by: analytics-agent
date: 2025-02-15
---

## Accounts that skip training have 40% lower adoption at 90 days

The correlation between Professional Services (Training) and
long-term adoption is stronger than expected...
```

These patterns don't require new file types — they're conventions on top of the existing observation format.

## Extension Architecture

Lore is designed to be extended at four levels: compilers, curators, file types, and CLI commands. Extensions follow a simple contract: they receive the parsed `Ontology` object and produce output.

### Extension Points

```
  ┌─────────────┐
  │  .lore files │
  └──────┬───────┘
         │ parse
         v
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Ontology    │────>│  Compilers   │────>│  Outputs     │
  │  (models.py) │     │  (built-in   │     │  (files,     │
  │              │     │   + plugins)  │     │   stdout)    │
  │              │     └──────────────┘     └──────────────┘
  │              │
  │              │────>│  Validators  │────>│  Diagnostics │
  │              │     │  (built-in   │     │  (errors,    │
  │              │     │   + plugins)  │     │   warnings)  │
  │              │     └──────────────┘     └──────────────┘
  │              │
  │              │────>│  Curators    │────>│  Reports     │
  │              │     │  (built-in   │     │  (findings,  │
  │              │     │   + plugins)  │     │   scores)    │
  └─────────────┘     └──────────────┘     └──────────────┘
```

### Custom Compilers

A compiler is a function that takes an `Ontology` and returns a string:

```python
from lore.models import Ontology

def compile_graphql(ontology: Ontology) -> str:
    """Compile Lore ontology to GraphQL schema."""
    lines = []
    for entity in ontology.entities:
        lines.append(f"type {entity.name} {{")
        for attr in entity.attributes:
            gql_type = _map_type(attr.type)
            lines.append(f"  {attr.name}: {gql_type}")
        lines.append("}")
    return "\n".join(lines)
```

Register via `lore.yaml`:

```yaml
plugins:
  compilers:
    graphql: mypackage.compilers:compile_graphql
```

Then use: `lore compile <dir> -t graphql`

### Custom Curators

A curator job is a function that takes an `Ontology` and returns a `CurationReport`:

```python
from lore.models import Ontology
from lore.curator import CurationReport, CurationFinding

def curate_pii(ontology: Ontology) -> CurationReport:
    """Check for attributes that might contain PII without @pii annotation."""
    report = CurationReport(job="pii-check")
    pii_keywords = {"email", "phone", "ssn", "address", "name"}
    for entity in ontology.entities:
        for attr in entity.attributes:
            if attr.name in pii_keywords and "pii" not in attr.annotations:
                report.findings.append(CurationFinding(
                    job="pii-check", severity="warning",
                    message=f"'{entity.name}.{attr.name}' may contain PII but lacks @pii annotation",
                ))
    return report
```

Register via `lore.yaml`:

```yaml
plugins:
  curators:
    pii-check: mypackage.curators:curate_pii
```

Then use: `lore curate <dir> --job pii-check`

### Custom File Types (Directories)

Lore recognizes file types by directory name. Custom directories are parsed as generic `.lore` files (frontmatter + sections) and made available on the `Ontology` object:

```yaml
plugins:
  directories:
    playbooks: mypackage.parsers:parse_playbook
```

A custom directory parser receives a file path and returns a dataclass that gets attached to `ontology.extensions["playbooks"]`. The core parser handles frontmatter splitting; the plugin handles semantic parsing of the body.

### The `Ontology` Object as Plugin Contract

All extensions receive the same `Ontology` dataclass. This is the stable API surface:

```python
ontology.manifest          # OntologyManifest
ontology.entities          # list[Entity]
ontology.relationship_files # list[RelationshipFile]
ontology.rule_files        # list[RuleFile]
ontology.taxonomies        # list[Taxonomy]
ontology.glossary          # Glossary
ontology.views             # list[View]
ontology.observation_files # list[ObservationFile]
ontology.outcome_files     # list[OutcomeFile]

# Convenience properties
ontology.entity_names      # set[str]
ontology.all_relationships # list[Relationship]
ontology.all_traversals    # list[Traversal]
ontology.all_rules         # list[Rule]
ontology.all_glossary_entries # list[GlossaryEntry]
ontology.all_observations  # list[Observation]
ontology.all_outcomes      # list[Outcome]
ontology.all_takeaways     # list[str]
```

Plugin authors code against this interface. As long as the `Ontology` object is stable, plugins don't break.

### Plugin Registration in `lore.yaml`

```yaml
name: my-ontology
version: 0.2.0

plugins:
  compilers:
    graphql: lore_graphql:compile_graphql
    dbt: lore_dbt:compile_dbt_models
  curators:
    pii-check: lore_pii:curate_pii
    naming: lore_style:curate_naming_conventions
  directories:
    playbooks: lore_playbooks:parse_playbook
```

Plugins are Python packages installed via pip. The string format is `package.module:function_name`. The CLI discovers them at parse time by reading `lore.yaml` and importing the specified entry points.

### Agent-as-Tool Pattern

The ontology directory is a filesystem. Any agent with shell access can use Lore without a special SDK:

| Agent needs to... | Tool |
|---|---|
| Understand the ontology | `cat INDEX.lore` |
| Search knowledge | `grep -r "expansion" entities/ rules/` |
| Read an entity | `cat entities/account.lore` |
| List all entities | `ls entities/` or `cat entities/INDEX.lore` |
| Get compiled context | `lore compile . -t agent` |
| Check a proposed change | `lore validate .` |
| Assess knowledge quality | `lore curate . --job coverage --dry-run` |
| See what's stale | `lore curate . --job staleness` |
| Find contradictions | `lore curate . --job consistency` |
| Refresh routing indexes | `lore index .` |
| View the entity graph | `lore viz .` |
| Get stats | `lore stats .` |
| Propose improvements | `lore evolve .` |

No special memory retrieval API, no vector search layer, no custom tool-use protocol. The filesystem is the API. `grep` is the search tool. The Lore CLI commands are the domain-aware tools on top.

## INDEX.lore Files

INDEX.lore files are auto-generated routing guides that help AI agents navigate the ontology efficiently. Instead of grepping blindly, an agent reads the INDEX.lore to understand what's where.

```
lore index <dir>                      Generate all INDEX.lore files
```

INDEX.lore files are generated at two levels:

### Root INDEX.lore

The root `INDEX.lore` contains:
- **Overview**: Ontology name, version, description
- **Stats**: Entity/relationship/rule/observation counts
- **Directory Map**: What each directory contains and how many files
- **Entity Listing**: Every entity with attribute count and description
- **Search Guide**: Natural language routing hints (e.g., "What is X? -> Look in entities/")

### Directory INDEX.lore

Each directory (`entities/`, `rules/`, `observations/`, etc.) gets its own `INDEX.lore` with:
- **Contents**: File listing with key metadata (entity names, rule severities, observation dates)
- **Search Guide**: Directory-specific search tips (e.g., `grep -l 'applies_to: Account' rules/*.lore`)

### Index Freshness

The `lore curate --job index` curator checks:
- Missing INDEX.lore files
- Stale indexes (entity count mismatch, files not listed)

INDEX.lore files have `index: true` in their frontmatter and are excluded from ontology parsing — they are metadata about the ontology, not part of it.

## CLI Reference

```
lore init <dir>                        Scaffold a new ontology
lore validate <dir>                    Validate ontology for errors
lore compile <dir> -t <target>         Compile to target format
lore compile <dir> -t agent --view V   Compile scoped to a view
lore compile <dir> -t palantir         Compile to Palantir Foundry JSON
lore stats <dir>                       Show ontology statistics
lore viz <dir>                         ASCII entity relationship graph
lore index <dir>                       Generate INDEX.lore routing files
lore evolve <dir>                      Generate proposals from outcome takeaways
lore curate <dir>                      Run all curation health checks
lore curate <dir> --job <name>         Run a specific curation job
lore curate <dir> --dry-run            Report only, suppress suggestions
```

Compilation targets: `neo4j`, `json`, `agent`, `embeddings`, `mermaid`, `palantir`

Curation jobs: `staleness`, `coverage`, `consistency`, `index`, `summarize`, `all`

## Temporal Relevance

Knowledge freshness is tracked at three levels:

1. **File-level freshness**: `provenance.created` date combined with `evolution.staleness` window. The validator can flag stale knowledge.
2. **Deprecation tracking**: `status: deprecated` + `provenance.deprecated` date. Old knowledge is marked, not deleted.
3. **Prose-level context**: `## Lifecycle` and `## Notes` sections support narrative temporal evolution.

Versioning is intentionally simple:
- **Ontology-level**: `version` in `lore.yaml` (semantic versioning).
- **File-level**: Git handles diffs better than per-file version numbers.
- **Observation/outcome-level**: `date` field in frontmatter.

## Directory Structure

A complete v0.2 ontology:

```
my-ontology/
├── lore.yaml                    # Manifest + plugin config
├── INDEX.lore                   # Root routing guide (generated)
├── entities/                    # Domain concepts
│   ├── INDEX.lore               # Entity directory index (generated)
│   ├── account.lore
│   ├── product.lore
│   └── contact.lore
├── relationships/               # How entities connect
│   ├── INDEX.lore
│   ├── commercial.lore
│   └── product-intelligence.lore
├── rules/                       # Business logic
│   ├── INDEX.lore
│   ├── churn-risk.lore
│   └── expansion.lore
├── taxonomies/                  # Classification hierarchies
│   ├── signal-types.lore
│   └── product-catalog.lore
├── glossary/                    # Canonical definitions
│   ├── terms.lore
│   └── products.lore
├── views/                       # Team-scoped perspectives
│   ├── account-executive.lore
│   └── cs-manager.lore
├── observations/                # Field notes (AI + human)
│   ├── INDEX.lore
│   ├── q2-account-signals.lore
│   ├── feature-adoption.lore
│   └── market-changes.lore
├── outcomes/                    # Retrospectives
│   └── q2-retrospective.lore
├── proposals/                   # Generated by lore evolve
│   └── adjust-usage-rule.lore
└── _compiled/                   # Generated outputs (gitignored)
    ├── agent-context.md
    ├── ontology.json
    ├── palantir-ontology.json
    ├── embeddings.jsonl
    ├── neo4j-schema.cypher
    └── entity-graph.mmd
```

The simplest valid ontology is still 2 files:

```
my-domain/
├── lore.yaml
└── entities/
    └── customer.lore
```

### Convention: Organize by Concern, Not by Size

As ontologies grow, organize files within directories by domain concern rather than splitting by entity count:

```
observations/
├── q2-account-signals.lore      # Time-scoped agent observations
├── feature-adoption.lore        # Entity-scoped patterns
├── market-changes.lore          # External domain drift
└── agent-decisions-march.lore   # Decision log pattern
```

```
rules/
├── churn-risk.lore              # One domain = one file
├── expansion-signals.lore
└── scoring.lore
```

Each file should have a clear domain focus described in its frontmatter. Avoid monolithic files with 50+ rules or entities — split by business concern when a file exceeds ~200 lines.
