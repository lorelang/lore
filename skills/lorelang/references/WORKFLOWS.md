# Lore Workflows

Step-by-step workflows for common ontology operations. All workflows assume `lore` CLI is installed.

## 1. Bootstrap a New Domain Ontology

```bash
# Create ontology with AI-first defaults
lore setup customer-success --domain "Customer Success Operations"

# cd into the ontology — all subsequent commands auto-detect
cd customer-success

# Validate the generated structure
lore validate

# See what was created
lore list

# Compile to agent context to verify
lore compile -t agent
```

## 2. Add an Entity

```bash
# Scaffold a correctly-formatted entity file
lore add entity "Account" --description "A company that is a customer or prospect."

# Edit the scaffolded file to add attributes, identity, notes
# (agent edits entities/account.lore directly)

# Validate after editing
lore validate
```

Or write the file directly:

```bash
cat > entities/account.lore << 'EOF'
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
EOF

lore validate
```

## 3. Add Relationships Between Entities

```bash
# Scaffold with required flags
lore add relationship "Account Contacts" \
  --from-entity Account --to-entity Contact --cardinality one-to-many

# Or write directly
cat > relationships/account_links.lore << 'EOF'
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

lore validate
```

## 4. Compile for Different Targets

```bash
# AI agent system prompt (most common)
lore compile -t agent -o context.txt

# Scoped to a team's view
lore compile -t agent --view "Account Executive" --budget 4000

# JSON for API consumption
lore compile -t json -o ontology.json

# Neo4j graph schema
lore compile -t neo4j -o schema.cypher

# Embedding chunks for vector store
lore compile -t embeddings -o chunks.jsonl

# Visual diagram
lore compile -t mermaid -o diagram.mmd

# Tool/function schemas for agent function calling
lore compile -t tools -o tools.json
```

## 5. Ingest Meeting Notes

```bash
# From a transcript file (run from inside ontology dir)
lore ingest transcript --input ./meeting-notes.txt \
  --about Account --observed-by "product-team" --confidence 0.7

# Validate the generated observation
lore validate
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
lore evolve

# Review and accept proposals
lore review proposals/ --decision accept --reviewer domain-lead
```

## 7. Monitor Ontology Health

```bash
# Run all health checks
lore curate --json

# Check specific aspects
lore curate --job staleness
lore curate --job coverage
lore curate --job consistency

# Dry run (no proposal generation)
lore curate --dry-run
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
cd my-domain

# 2. Scaffold files
lore add entity "Account" --description "A customer or prospect"
lore add entity "Contact" --description "A person at an account"
lore add relationship "Account Contacts" --from-entity Account --to-entity Contact

# 3. Author: edit the scaffolded .lore files directly on the filesystem

# 4. Validate after each change (parse JSON, fix errors, re-validate)
lore validate --json

# 5. Compile for use
lore compile -t agent

# 6. Search and query
lore search "relevant topic" --json
lore show Account --json
lore list --type entities --json

# 7. Monitor health (parse findings, address warnings)
lore curate --json

# 8. Evolve from outcomes
lore evolve
lore review proposals/ --decision accept --reviewer ai-agent

# 9. Track stats
lore stats --json
```

All commands return exit code 0 on success, 1 on error. JSON output is always valid JSON on stdout.

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
