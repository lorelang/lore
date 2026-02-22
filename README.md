# 🏛️ Lore

**Human-readable ontology format for the AI age.**

Define your domain knowledge in prose. Compile to knowledge graphs, AI agent prompts, embedding indexes, or JSON schemas.

Lore is designed for teams that need to encode institutional knowledge — the kind of expertise that lives in people's heads, scattered documents, and tribal knowledge — into a format that both humans and AI can reason over.

Lore is **AI-first**: unstructured and semi-structured narrative is the primary source
of meaning. Structured compilers are best-effort projections of that source.

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

**Lore's approach:** A markdown-like format with just enough structure that tooling can parse it deterministically, but readable enough that domain experts can author and review it directly. Domain understanding also has to evolve, but humans and AI Agents, Lore comes with opinionated curation workflows for evolution of domain understnading.

## Quick Start

```bash
# Install
pip install -e .

# AI-first domain bootstrap (Lore equivalent of /...:setup)
lore setup my-domain --domain "B2B Customer Discovery"

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

# Export interoperable ontology JSON-LD
lore compile examples/b2b-saas-gtm/ -t jsonld -o ontology.jsonld

# Generate Mermaid ER diagram
lore compile examples/b2b-saas-gtm/ -t mermaid -o diagram.mmd

# Generate routing indexes and run quality curation
lore index examples/b2b-saas-gtm/
lore curate examples/b2b-saas-gtm/

# Run self-improving proposal generation from outcomes
lore evolve examples/b2b-saas-gtm/

# Distill a meeting transcript into observations (semi-structured claims)
lore ingest transcript examples/b2b-saas-gtm/ \
  --input ./meeting.txt \
  --about Account

# Distill memory exports into observations (adapters: arscontexta|mem0|graphiti)
lore ingest memory examples/b2b-saas-gtm/ \
  --adapter mem0 \
  --input ./memory.json \
  --about Account

# Review generated proposals (accept/reject)
lore review examples/b2b-saas-gtm/proposals \
  --decision accept \
  --reviewer ontology-curator

# Show statistics
lore stats examples/b2b-saas-gtm/

# Visualize entity graph
lore viz examples/b2b-saas-gtm/
```

## Build Shortcuts

```bash
make help
make launch-check
make dist-check
```

This gives a single command path for test + conformance + example validation +
compile matrix + end-to-end smoke checks.

`setup` also accepts alias forms:
`/setup`, `lore:setup`, `/lore:setup`.

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

### Observations (`.lore` files in `observations/`)

Use optional claim markers to capture semi-structured insight from meetings:

```markdown
## Discovery Call: Acme

Fact: Acme has 4 regional sales teams and 2 RevOps analysts.
Belief: Salesforce integration will be phase-1 critical path.
Value: Security review must complete before pilot rollout.
Precedent: Last migration failed due to SSO scope gaps.
```

## Compilation Targets

| Target       | Output                  | Use Case                           |
|-------------|-------------------------|------------------------------------|
| `neo4j`     | Cypher DDL + constraints| Graph database schema              |
| `json`      | JSON representation     | API consumption, interop           |
| `jsonld`    | JSON-LD graph           | Semantic-web / ontology interop    |
| `agent`     | Structured prompt text  | AI agent system prompts            |
| `embeddings`| JSONL chunks + metadata | Vector store ingestion             |
| `mermaid`   | Mermaid ER diagram      | Visual documentation               |
| `palantir`  | Foundry ontology JSON   | Palantir import                    |

## Design Principles

1. **Reads like documentation.** Domain experts author and review it without training.
2. **Parses like code.** Deterministic grammar for reliable tooling.
3. **Lives in git.** Version-controlled, diffable, reviewable in PRs.
4. **Compiles to anything.** Source format that targets any runtime.
5. **Prose where meaning is rich, structure where precision matters.** Lore supports both.

## Lorelang as a Language

Lore is launched as a language ecosystem, not just a CLI utility:

- Language charter: `LANGUAGE.md`
- Conformance fixtures: `conformance/`
- Conformance tests: `tests/test_language_conformance.py`

PRs are welcome. Current contribution mode is PR-first. Language-level changes should update
spec + conformance fixtures + conformance tests together.

## Example: B2B SaaS GTM

The included example (`examples/b2b-saas-gtm/`) models a B2B SaaS company's go-to-market operations for an AI revenue expansion agent. It includes:

- **11 entities** including Account, Contact, Subscription, Product, Feature, Competitor, and Play
- **18 relationships** with named traversals
- **16 rules** covering expansion detection, churn risk, and scoring
- **2 taxonomies** with 20+ signal and product categories
- **15 glossary terms**
- **3 views** for Account Executives, CSMs, and RevOps

## Example: AI-First Client Learning

The additional example (`examples/ai-first-client-learning/`) shows how to turn
meeting-derived learning into ontology updates:

- Observations contain rich prose plus optional `Fact:`, `Belief:`, `Value:`, `Precedent:` claims
- Outcomes close the loop with `Takeaway:` and `Ref:` markers
- `lore evolve` runs in `review-required` mode for human-in-the-loop governance

## Example: Implementation Kickoff Intelligence

The example (`examples/implementation-kickoff-intelligence/`) models how delivery
teams can convert onboarding and kickoff meeting notes into a reusable ontology:

- Captures implementation entities such as Client, Stakeholder, Integration, and Workstream
- Includes traversals like `onboarding-risk-path` and `sponsor-gap-path` for agent routing
- Encodes recurring delivery risk rules with narrative-first conditions and actions
- Uses observation claims plus retrospective outcomes to evolve onboarding playbooks

## Example: Support Intelligence Loop

The example (`examples/support-intelligence-loop/`) shows a voice-of-customer
loop for support and retention workflows:

- Links Account, SupportCase, Conversation, and IssueTheme into a support graph
- Uses recurring signal rules to escalate churn-risk patterns from unstructured support narrative
- Demonstrates taxonomy-driven theme normalization without losing conversational context
- Closes the loop with outcomes and takeaways that can feed `lore evolve`

## Contributing

PRs are welcome. If something is missing, build it and open a PR with tests.

See:

- `CONTRIBUTING.md`
- `docs/DEVELOPER_GUIDE.md`
- `docs/PLUGIN_GUIDE.md`
- `docs/MEETING_TO_ONTOLOGY.md`
- `docs/LAUNCH_TOOLING.md`
- `docs/VERSIONING_RELEASE.md`

## License

Apache 2.0
