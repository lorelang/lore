# Lore File Format Reference

All `.lore` files use YAML frontmatter followed by Markdown-structured content.

## Manifest (lore.yaml)

```yaml
name: my-ontology
version: 0.2.0
description: >
  Human-readable description of the domain.
domain: Customer Success Operations
maintainers:
  - name: Domain Team
    role: Domain Owner
evolution:
  proposals: review-required    # open | review-required | closed
  staleness: 45d                # freshness window (e.g. 30d, 12h, 3m)
plugins:
  compilers:
    custom-target: my_module:compile_fn
  curators:
    custom-check: my_module:curate_fn
```

## Entity (entities/*.lore)

```
---
entity: EntityName
description: One-line description of the entity.
inherits: ParentEntity          # optional inheritance
provenance:
  author: author-name
  source: domain-expert         # domain-expert | ai-generated | imported | derived
  confidence: 0.9               # 0.0 to 1.0
  created: 2025-01-15
status: stable                  # draft | proposed | stable | deprecated
---

## Attributes

name: string [required, unique]
  | Description of this attribute.

score: float [0.0 .. 100.0]
  | Numeric range constraint.

category: enum [low, medium, high]
  | Enum values in brackets.

tags: list
  | List type for multi-valued attributes.

created_at: date
  | Date type.

owner: -> Contact
  | Reference to another entity (foreign key).

computed_field: float
  | @computed: rules/scoring.lore#rule-name

## Identity

Free-form prose: how is this entity uniquely identified?

## Lifecycle

Free-form prose: what stages does this entity go through?

## Notes

Free-form prose: edge cases, reasoning guidance, agent instructions.
```

### Attribute Types

- `string` -- Text value
- `int` -- Integer
- `float` -- Decimal number
- `bool` -- True/false
- `date` -- Date value
- `enum [val1, val2, ...]` -- Enumerated values
- `list` -- Multi-valued
- `-> EntityName` -- Reference to another entity

### Attribute Constraints

- `[required]` -- Must be present
- `[unique]` -- Must be unique across instances
- `[0.0 .. 100.0]` -- Numeric range
- `[required, unique]` -- Multiple constraints

### Attribute Annotations

- `@computed: rules/file.lore#rule-name` -- Computed by a rule

## Relationship (relationships/*.lore)

```
---
domain: Relationship Group Name
description: Description of this relationship set.
provenance:
  author: ...
  source: domain-expert
  confidence: 0.9
  created: 2025-01-15
status: stable
---

## RELATIONSHIP_NAME
  from: EntityA -> to: EntityB
  cardinality: one-to-many       # one-to-one | one-to-many | many-to-one | many-to-many
  | Description of this relationship.

  properties:
    property_name: type
      | Description.

## Traversal: traversal-name
  path: EntityA -[REL_NAME]-> EntityB -[REL_NAME]-> EntityC
  | What question does this traversal answer?
```

## Rule (rules/*.lore)

```
---
domain: Rule Group Name
description: Description of this rule set.
status: stable
---

## rule-name
  applies_to: EntityName
  severity: critical             # critical | warning | info
  trigger: When this happens

  condition:
    Entity.attribute > threshold
    AND Entity.status = "active"

  action:
    Do something specific
    Notify someone

  outputs:
    computed_field: float
      | What the rule computes

  Free-form prose explaining the rule's reasoning and context.
```

## Taxonomy (taxonomies/*.lore)

```
---
taxonomy: TaxonomyName
applied_to: EntityName.attribute
description: What this taxonomy classifies.
status: stable
---

Root Category
+-- Child Category             @tag: tag-name
|   +-- Grandchild             @tag: another-tag
|   +-- Another Grandchild     @tag: third-tag
+-- Second Child               @tag: second-tag

## Inheritance Rules

Free-form prose about how tags propagate.
```

Tree notation uses `+--` and `|` for hierarchy. Tags are `@tag: value`.

## Glossary (glossary/*.lore)

```
---
description: Description of this glossary.
status: stable
---

## Term Name

Definition of the term. Can be multi-line prose.

## Another Term

Another definition.
```

## View (views/*.lore)

```
---
view: View Name
audience: Who this view is for
description: What this view scopes.
status: stable
---

## Entities
- EntityA (all)
- EntityB (name, status)

## Relationships
- REL_NAME
- traversal-name

## Rules
- rule-name

## Key Questions
- What should this audience focus on?
- What decisions do they make?

## Not In Scope

What this view explicitly excludes.

## Notes

Additional context for this audience.
```

## Observation (observations/*.lore)

```
---
observations: Collection Name
about: EntityName
observed_by: observer-id
date: 2025-01-15
confidence: 0.75
status: proposed
provenance:
  author: observer-id
  source: ai-generated
  confidence: 0.75
  created: 2025-01-15
---

## Section heading

Free-form prose describing what was observed.

Fact: A verifiable statement.
Belief: An interpretation or hypothesis.
Value: A stated priority or preference.
Precedent: A historical pattern that should inform future decisions.
```

Claim markers (`Fact:`, `Belief:`, `Value:`, `Precedent:`) are optional but enable structured claim extraction.

## Outcome (outcomes/*.lore)

```
---
outcomes: Outcome Name
reviewed_by: reviewer-id
date: 2025-01-15
status: proposed
provenance:
  author: reviewer-id
  source: ai-generated
  confidence: 0.8
  created: 2025-01-15
---

## Section heading

Retrospective prose about what happened.

Takeaway: a lesson learned that should feed back into the ontology
Takeaway: another lesson

Ref: observations/file.lore#section-heading
```

`Takeaway:` markers are consumed by `lore evolve` to generate proposals.

## Decision (decisions/*.lore)

```
---
decisions: Decision Name
decided_by: decider-id
decided_date: 2025-01-15
status: stable
provenance:
  author: decider-id
  source: domain-expert
  confidence: 0.95
  created: 2025-01-15
---

## Decision Heading

Context: What situation prompted this decision.
Resolution: What was decided.
Rationale: Why this was chosen.

Fact: Supporting evidence.
Belief: Reasoning behind the choice.

Affects: EntityName
Affects: RuleName

Evidence: observations/file.lore#section
```

## Provenance Block

All file types support optional provenance:

```yaml
provenance:
  author: who-created-this
  source: domain-expert       # domain-expert | ai-generated | imported | derived
  confidence: 0.9             # 0.0 to 1.0
  created: 2025-01-15
  deprecated: 2025-06-01      # optional deprecation date
```

## Status Values

All file types support: `draft`, `proposed`, `stable`, `deprecated`
