# Meeting to Ontology Workflow

Convert raw meeting learning into durable Lorelang knowledge.

## 1. Start a Domain

```bash
lore setup my-domain --domain "B2B SaaS GTM"
```

## 2. Ingest Transcript

```bash
lore ingest transcript my-domain \
  --input ./meeting.txt \
  --about DomainObject
```

## 3. Ingest Memory Export (Optional)

```bash
lore ingest memory my-domain \
  --adapter mem0 \
  --input ./memory.json \
  --about DomainObject
```

Supported adapters: `arscontexta`, `mem0`, `graphiti`.

## 4. Validate and Curate

```bash
lore validate my-domain
lore curate my-domain --dry-run
```

## 5. Compile for Agent Context

```bash
lore compile my-domain -t agent --view "Domain Curator"
```

## 6. Close the Loop

Record outcomes in `outcomes/`, then generate and review proposals:

```bash
lore evolve my-domain
lore review my-domain/proposals --decision accept --reviewer ontology-curator
```

This is the core Lorelang loop:

- ingest raw learning
- distill into semi-structured ontology artifacts
- review and promote durable domain knowledge
