# Lore Workflows

Step-by-step workflows for common ontology operations. All workflows assume `lore` CLI is installed.

## 1. Bootstrap a New Domain Ontology

```bash
# Create ontology with AI-first defaults
lore setup customer-success --domain "Customer Success Operations"

# Validate the generated structure
lore validate customer-success/

# See what was created
lore list customer-success/

# Compile to agent context to verify
lore compile customer-success/ -t agent
```

## 2. Add an Entity

Create a file in `entities/`:

```bash
# Write entity file
cat > ontology/entities/account.lore << 'EOF'
---
entity: Account
description: A company that is a customer or prospect.
status: draft
---

## Attributes

name: string [required, unique]
  | Legal entity name.

stage: enum [prospect, onboarding, active, at-risk, churned]
  | Current lifecycle stage.

## Identity

An account is identified by its primary web domain.

## Notes

Accounts are the primary unit for all revenue tracking.
EOF

# Validate
lore validate ontology/
```

## 3. Add Relationships Between Entities

```bash
cat > ontology/relationships/account_links.lore << 'EOF'
---
domain: Account Links
description: How accounts connect to other entities.
---

## HAS_CONTACT
  from: Account -> to: Contact
  cardinality: one-to-many
  | An account has multiple contacts.

## Traversal: account-contacts
  path: Account -[HAS_CONTACT]-> Contact
  | Who are the contacts at this account?
EOF

lore validate ontology/
```

## 4. Compile for Different Targets

```bash
# AI agent system prompt (most common)
lore compile ontology/ -t agent -o context.txt

# Scoped to a team's view
lore compile ontology/ -t agent --view "Account Executive" --budget 4000

# JSON for API consumption
lore compile ontology/ -t json -o ontology.json

# Neo4j graph schema
lore compile ontology/ -t neo4j -o schema.cypher

# Embedding chunks for vector store
lore compile ontology/ -t embeddings -o chunks.jsonl

# Visual diagram
lore compile ontology/ -t mermaid -o diagram.mmd

# Tool/function schemas for agent function calling
lore compile ontology/ -t tools -o tools.json
```

## 5. Ingest Meeting Notes

```bash
# From a transcript file
lore ingest transcript ontology/ \
  --input ./meeting-notes.txt \
  --about Account \
  --observed-by "product-team" \
  --confidence 0.7

# Validate the generated observation
lore validate ontology/
```

## 6. Learn and Evolve

After observations accumulate and outcomes are written:

```bash
# Write an outcome with takeaways
cat > ontology/outcomes/q1_retro.lore << 'EOF'
---
outcomes: Q1 Retrospective
reviewed_by: domain-team
date: 2025-04-01
status: proposed
---

## Churn prediction accuracy

Our churn rules caught 70% of actual churn events.

Takeaway: add usage-decline threshold as a churn trigger
Takeaway: weight champion-departure higher in risk scoring

Ref: observations/q1_signals.lore#usage-patterns
EOF

# Generate proposals from takeaways
lore evolve ontology/

# Review and accept proposals
lore review ontology/proposals --decision accept --reviewer domain-lead
```

## 7. Monitor Ontology Health

```bash
# Run all health checks
lore curate ontology/ --json

# Check specific aspects
lore curate ontology/ --job staleness
lore curate ontology/ --job coverage
lore curate ontology/ --job consistency

# Dry run (no proposal generation)
lore curate ontology/ --dry-run
```

## 8. Compare Ontology Versions

```bash
lore diff ontology-v1/ ontology-v2/ --json
```

## 9. Full AI Agent Autonomous Loop

An AI agent can run this complete loop without human intervention:

```bash
# 1. Bootstrap
lore setup my-domain --domain "Target Domain"

# 2. Author: write .lore files to entities/, relationships/, rules/, etc.
#    (agent writes files directly to the filesystem)

# 3. Validate after each change
lore validate my-domain/ --json
# Parse JSON output, fix any errors, re-validate

# 4. Compile for use
lore compile my-domain/ -t agent

# 5. Monitor health
lore curate my-domain/ --json
# Parse findings, address warnings

# 6. Search and query
lore search my-domain/ "relevant topic" --json
lore show my-domain/ EntityName --json
lore list my-domain/ --type entities --json

# 7. Evolve from outcomes
lore evolve my-domain/
lore review my-domain/proposals --decision accept --reviewer ai-agent

# 8. Track stats
lore stats my-domain/ --json
```

All commands return exit code 0 on success, 1 on error. JSON output is always valid JSON on stdout. Error messages go to stdout with non-zero exit.

## 10. Plugin Compilers and Curators

Add custom compilation targets or curation jobs via `lore.yaml`:

```yaml
plugins:
  compilers:
    my-target: my_package.module:compile_function
  curators:
    my-check: my_package.module:curate_function
```

Compiler function signature: `def compile_fn(ontology: Ontology) -> str`
Curator function signature: `def curate_fn(ontology: Ontology) -> CurationReport`
