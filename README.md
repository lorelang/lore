# 🏛️ Lore

**Human-readable ontology format for the AI age.**

Define your domain knowledge in prose. Compile to knowledge graphs, AI agent prompts, embedding indexes, or JSON schemas.

Lore is designed for teams that need to encode institutional knowledge — the kind of expertise that lives in people's heads, scattered documents, and tribal knowledge — into a format that both humans and AI can reason over.

```
ontology/
├── lore.yaml              # manifest
├── entities/              # what things exist
├── relationships/         # how they connect
├── rules/                 # what logic governs them
├── taxonomies/            # how they're classified
├── glossary/              # what terms mean
└── views/                 # who sees what
```

## Why Lore?

**The problem:** AI agents need domain understanding, not just data access. An agent querying a database can retrieve rows, but it can't reason about what those rows *mean* — how entities relate, what rules apply, or what constitutes a valid chain of inference.

**The existing solutions are wrong:**
- **OWL/RDF:** Powerful but unreadable. Nobody outside ontology specialists can author or review them.
- **JSON/YAML schemas:** Too flat. Can't express inheritance, inference rules, or reasoning paths.
- **Markdown docs:** Great for humans but no tooling can parse them consistently.

**Lore's approach:** A markdown-like format with just enough structure that tooling can parse it deterministically, but readable enough that domain experts can author and review it directly.

## Quick Start

```bash
# Install
pip install -e .

# Validate an ontology
lore validate examples/b2b-saas-gtm/

# Compile to AI agent context
lore compile examples/b2b-saas-gtm/ -t agent

# Compile scoped to a specific team's view
lore compile examples/b2b-saas-gtm/ -t agent --view "Account Executive"

# Compile to Neo4j Cypher
lore compile examples/b2b-saas-gtm/ -t neo4j -o schema.cypher

# Export as JSON
lore compile examples/b2b-saas-gtm/ -t json -o ontology.json

# Generate embedding chunks (JSONL)
lore compile examples/b2b-saas-gtm/ -t embeddings -o chunks.jsonl

# Generate Mermaid ER diagram
lore compile examples/b2b-saas-gtm/ -t mermaid -o diagram.mmd

# Show statistics
lore stats examples/b2b-saas-gtm/

# Visualize entity graph
lore viz examples/b2b-saas-gtm/
```

## File Format

### Entity (`.lore` files in `entities/`)

```markdown
---
entity: Account
description: A company that is a customer or prospect.
---

## Attributes

name: string [required, unique]
  | Legal entity name.

health_score: float [0.0 .. 100.0]
  | Composite health metric.
  | @computed: rules/scoring.lore#account-health-score

## Identity

An account is uniquely identified by its primary web domain.

## Lifecycle

Accounts progress through stages: prospect → onboarding →
active → at-risk → churned → former.
```

### Relationships (`.lore` files in `relationships/`)

```markdown
## HAS_SUBSCRIPTION
  from: Account -> to: Subscription
  cardinality: one-to-many
  | An account can have multiple subscriptions.

## Traversal: revenue-by-product
  path: Account -[HAS_SUBSCRIPTION]-> Subscription -[SUBSCRIBES_TO]-> Product
  | Answers: "What products does this account use?"
```

### Rules (`.lore` files in `rules/`)

```markdown
## champion-departure-alert
  applies_to: Account
  severity: critical
  trigger: Champion contact becomes inactive

  condition:
    Contact WHERE account = this
      AND role = "champion"
      AND last_engaged < now() - 60d

  action:
    Create Signal with type = "Champion Departure"
    Set account.stage = "at-risk"
    Notify csm_owner immediately

  Champion departure is historically our #1 churn predictor.
  The CSM should identify a replacement within 14 days.
```

### Taxonomies (`.lore` files in `taxonomies/`)

```markdown
Signal
├── Expansion Signal              @tag: expansion
│   ├── Usage Spike               @tag: product-led
│   ├── New Department Adoption   @tag: product-led
│   └── Executive Engagement      @tag: relationship
└── Contraction Signal            @tag: contraction
    ├── Usage Decline             @tag: product-led
    └── Champion Departure        @tag: relationship
```

## Compilation Targets

| Target       | Output                  | Use Case                           |
|-------------|-------------------------|------------------------------------|
| `neo4j`     | Cypher DDL + constraints| Graph database schema              |
| `json`      | JSON representation     | API consumption, interop           |
| `agent`     | Structured prompt text  | AI agent system prompts            |
| `embeddings`| JSONL chunks + metadata | Vector store ingestion             |
| `mermaid`   | Mermaid ER diagram      | Visual documentation               |

## Design Principles

1. **Reads like documentation.** Domain experts author and review it without training.
2. **Parses like code.** Deterministic grammar for reliable tooling.
3. **Lives in git.** Version-controlled, diffable, reviewable in PRs.
4. **Compiles to anything.** Source format that targets any runtime.
5. **Prose where meaning is rich, structure where precision matters.** Lore supports both.

## Example: B2B SaaS GTM

The included example (`examples/b2b-saas-gtm/`) models a B2B SaaS company's go-to-market operations for an AI revenue expansion agent. It includes:

- **7 entities:** Account, Contact, Subscription, Product, Opportunity, Interaction, Signal, Usage
- **12 relationships** with named traversals
- **11 rules** covering expansion detection, churn risk, and scoring
- **1 taxonomy** with 20+ signal types
- **15 glossary terms**
- **3 views** for Account Executives, CSMs, and RevOps

## License

Apache 2.0
