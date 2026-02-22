# Lore FAQ

Frequently asked questions for developers building with or contributing to Lore.

---

### What is Lore?

Lore is a human-readable, machine-parseable format (`.lore` files) for defining domain ontologies. Think of it as "Markdown for domain knowledge" — you describe your business domain (entities, relationships, rules, glossary) in structured prose, and Lore compiles it to whatever your systems need: Neo4j schemas, AI agent prompts, embedding chunks, JSON, Mermaid diagrams, or Palantir Foundry definitions.

### How is Lore different from JSON Schema / YAML configs / Protobuf?

Those formats optimize for machines. Lore optimizes for **shared understanding between humans and AI agents**. A `.lore` file reads like documentation but parses like code. It supports freeform prose (`## Notes`, `## Identity`, `## Lifecycle`) alongside structured attributes — because domain knowledge is richer than what fits in a type system.

### Do I need an LLM to use Lore?

No. Lore is a language and compiler — it works entirely offline. The `lore validate`, `lore compile`, `lore curate`, and `lore index` commands run without any API calls. The only optional LLM integration is `lore curate --job summarize`, which can use an LLM function for polished health summaries (it falls back to a template if no LLM is provided).

### What's the minimum viable ontology?

Two files:

```
my-domain/
├── lore.yaml
└── entities/
    └── customer.lore
```

Run `lore init my-domain` to scaffold this automatically.

### Can AI agents write .lore files?

Yes — that's a core design goal. An LLM that has seen one example `.lore` file can write another without documentation. The observations/outcomes/evolution loop is specifically designed for agents to record field notes, which then get distilled into ontology improvements.

### How do I add Lore to my AI agent?

Compile to an agent context prompt and include it in your system prompt:

```bash
lore compile my-ontology/ -t agent > system-context.md
```

Or for a team-specific view:

```bash
lore compile my-ontology/ -t agent --view account-executive
```

The agent can also use the filesystem directly — `grep`, `cat`, and `ls` on the `.lore` files work as a zero-dependency knowledge retrieval API.

### What compilation targets exist?

| Target | Command | Output |
|--------|---------|--------|
| AI Agent Context | `lore compile . -t agent` | Structured XML prompt |
| JSON | `lore compile . -t json` | Full ontology as JSON |
| Neo4j | `lore compile . -t neo4j` | Cypher DDL + constraints |
| Embeddings | `lore compile . -t embeddings` | JSONL chunks for vector stores |
| Mermaid | `lore compile . -t mermaid` | Entity relationship diagram |
| Palantir Foundry | `lore compile . -t palantir` | OntologyFullMetadata JSON |

Custom compilers can be registered via the `plugins:` section in `lore.yaml`.

### What are INDEX.lore files?

INDEX.lore files are auto-generated routing guides that help AI agents navigate the ontology. They exist at the root and in each directory, listing contents, stats, and search hints. Generate them with:

```bash
lore index my-ontology/
```

The `lore curate --job index` curator job checks if they're missing or stale.

### What's the self-updating loop?

The core innovation: **Compile -> Observe -> Act -> Record -> Evolve -> Review**.

1. **Compile** your ontology to agent context
2. Agent **observes** patterns in the domain (writes `.lore` observation files)
3. Agent **acts** on the domain knowledge
4. Human or agent **records** outcomes (what actually happened)
5. `lore evolve` reads outcomes and **generates proposals** for ontology changes
6. Human **reviews** and merges proposals

This turns your ontology from static documentation into a living, self-improving knowledge base.

### How does contradiction handling work?

Three levels:

1. **Detection**: The `lore curate --job consistency` curator detects when two observations about the same entity contain opposing signals (e.g., one says "expansion readiness", another says "churn risk").
2. **Annotation**: The agent compiler (`-t agent`) annotates conflicting observations with `conflict="true"` so the agent knows to reason carefully.
3. **Resolution**: Humans or the evolution loop resolve contradictions — Lore detects and flags, it doesn't auto-merge.

### Can I extend Lore with custom compilers/curators?

Yes. Register extensions in `lore.yaml`:

```yaml
plugins:
  compilers:
    graphql: my_plugins.graphql:compile_graphql
  curators:
    naming: my_plugins.naming:check_naming
  directories:
    - playbooks
```

Your custom compiler receives an `Ontology` object and returns a string. Your custom curator receives an `Ontology` and returns a `CurationReport`.

### What does Lore NOT do?

- **Not a conversation memory store** — Use Mem0, Zep, or Agno Learning Stores for agent session memory. Lore holds distilled domain knowledge, not raw conversations.
- **Not an agent framework** — Use LangGraph, CrewAI, or Agno for agent orchestration. Lore provides the knowledge they reason over.
- **Not a runtime query engine** — Compile to Neo4j for graph queries, or to embeddings for vector search. Lore is the source, not the database.
- **Not a capability router** — Agent routing belongs in orchestration frameworks. Lore describes WHAT the domain looks like, not WHICH agent handles it.

### How does Lore compare to Palantir's Ontology?

Palantir's ontology is a runtime operational layer tied to Foundry datasets. Lore is a source format — you define knowledge in `.lore` files and compile to Palantir (or Neo4j, or JSON, or anything else). Lore can generate Palantir-compatible JSON via `lore compile . -t palantir`.

### How does Lore compare to "Context Repositories" / "Skill Graphs"?

Context Repositories (Letta) focus on agent memory retrieval. Skill Graphs focus on agent capability routing. Lore is neither — it's a **sedimentation layer** for domain knowledge that sits upstream of both. Lore provides the structured, validated, version-controlled knowledge that memory systems and routing systems consume.

### What Python version is required?

Python 3.9+. The only dependency is PyYAML.

### How do I contribute?

1. Fork the repo
2. Create a feature branch
3. Run tests: `PYTHONPATH=src python3 -m pytest tests/`
4. Submit a PR

Key areas for contribution:
- New compilation targets (custom compilers)
- New curation jobs (custom curators)
- Example ontologies for different domains
- Documentation and tutorials
