"""
Lore data models.

These dataclasses represent the parsed ontology structure.
They are the intermediate representation between .lore files
and compilation targets.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path


class FileType(Enum):
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    RULE = "rule"
    TAXONOMY = "taxonomy"
    GLOSSARY = "glossary"
    VIEW = "view"
    OBSERVATION = "observation"
    OUTCOME = "outcome"
    DECISION = "decision"


@dataclass
class Provenance:
    """Tracks who/what created this knowledge and how much to trust it."""
    author: str = ""
    source: str = ""        # domain-expert | ai-generated | imported | derived
    confidence: Optional[float] = None  # 0.0 - 1.0
    created: str = ""       # YYYY-MM-DD
    deprecated: str = ""    # YYYY-MM-DD (only if status is deprecated)


@dataclass
class Attribute:
    name: str
    type: str
    constraints: list[str] = field(default_factory=list)
    enum_values: list[str] = field(default_factory=list)
    description: str = ""
    annotations: dict[str, str] = field(default_factory=dict)
    reference_to: Optional[str] = None  # For -> EntityName types


@dataclass
class Entity:
    name: str
    description: str = ""
    inherits: Optional[str] = None
    attributes: list[Attribute] = field(default_factory=list)
    identity: str = ""       # Prose block
    lifecycle: str = ""      # Prose block
    notes: str = ""          # Prose block
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""         # draft | proposed | stable | deprecated


@dataclass
class RelationshipProperty:
    name: str
    type: str
    description: str = ""


@dataclass
class Relationship:
    name: str
    from_entity: str
    to_entity: str
    cardinality: str = ""
    description: str = ""
    properties: list[RelationshipProperty] = field(default_factory=list)


@dataclass
class Traversal:
    name: str
    path: str
    description: str = ""


@dataclass
class RelationshipFile:
    domain: str
    description: str = ""
    relationships: list[Relationship] = field(default_factory=list)
    traversals: list[Traversal] = field(default_factory=list)
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""


@dataclass
class TaxonomyNode:
    name: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    children: list[TaxonomyNode] = field(default_factory=list)
    depth: int = 0


@dataclass
class Taxonomy:
    name: str
    description: str = ""
    applied_to: str = ""
    root: Optional[TaxonomyNode] = None
    inheritance_rules: str = ""  # Prose block
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""


@dataclass
class Rule:
    name: str
    applies_to: str = ""
    severity: str = "info"
    trigger: str = ""
    condition: str = ""
    action: str = ""
    prose: str = ""           # Free-form context
    outputs: str = ""         # For computed rules


@dataclass
class RuleFile:
    domain: str
    description: str = ""
    rules: list[Rule] = field(default_factory=list)
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""


@dataclass
class GlossaryEntry:
    term: str
    definition: str


@dataclass
class Glossary:
    description: str = ""
    entries: list[GlossaryEntry] = field(default_factory=list)
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""


@dataclass
class View:
    name: str
    description: str = ""
    audience: str = ""
    entities: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    key_questions: list[str] = field(default_factory=list)
    not_in_scope: str = ""
    notes: str = ""
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""


@dataclass
class KnowledgeClaim:
    """A semi-structured claim extracted from prose."""
    kind: str   # fact | belief | value | precedent
    text: str


@dataclass
class Observation:
    """A single observation (one ## section in an observation file)."""
    heading: str
    prose: str = ""
    claims: list[KnowledgeClaim] = field(default_factory=list)


@dataclass
class ObservationFile:
    """A file of AI-generated or human field notes."""
    name: str
    about: str = ""           # Entity name this observation relates to
    observed_by: str = ""     # Agent or person
    date: str = ""            # YYYY-MM-DD
    confidence: Optional[float] = None
    status: str = ""
    observations: list[Observation] = field(default_factory=list)
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None


@dataclass
class Outcome:
    """A single outcome (one ## section in an outcome file)."""
    heading: str
    prose: str = ""
    refs: list[str] = field(default_factory=list)         # Ref: lines
    takeaways: list[str] = field(default_factory=list)    # Takeaway: lines


@dataclass
class OutcomeFile:
    """A retrospective file recording what actually happened."""
    name: str
    reviewed_by: str = ""
    date: str = ""
    outcomes: list[Outcome] = field(default_factory=list)
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None
    status: str = ""


@dataclass
class Decision:
    """A single decision (one ## section in a decision file)."""
    heading: str
    context: str = ""               # What situation prompted the decision
    resolution: str = ""            # What was decided
    rationale: str = ""             # Why — prose, may contain claims
    rationale_claims: list[KnowledgeClaim] = field(default_factory=list)
    affects: list[str] = field(default_factory=list)   # Cross-refs to rules/entities
    evidence: list[str] = field(default_factory=list)  # Cross-refs to observations/outcomes


@dataclass
class DecisionFile:
    """A file recording operational decisions and their rationale."""
    name: str
    decided_by: str = ""            # Person or agent who decided
    date: str = ""                  # YYYY-MM-DD
    status: str = ""
    decisions: list[Decision] = field(default_factory=list)
    source_file: Optional[Path] = None
    provenance: Optional[Provenance] = None


@dataclass
class EvolutionConfig:
    """Configuration for the self-updating loop."""
    proposals: str = "open"      # open | review-required | closed
    staleness: str = ""          # e.g., "90d" — flag observations older than this


@dataclass
class PluginConfig:
    """Extension point registration in lore.yaml."""
    compilers: dict[str, str] = field(default_factory=dict)    # name -> module:function
    curators: dict[str, str] = field(default_factory=dict)     # name -> module:function
    directories: list[str] = field(default_factory=list)       # extra file type dirs
    directory_parsers: dict[str, str] = field(default_factory=dict)  # dir -> module:function


@dataclass
class OntologyManifest:
    name: str
    version: str = ""
    description: str = ""
    domain: str = ""
    maintainers: list[dict] = field(default_factory=list)
    evolution: Optional[EvolutionConfig] = None
    plugins: Optional[PluginConfig] = None


@dataclass
class Ontology:
    """The complete parsed ontology."""
    manifest: Optional[OntologyManifest] = None
    entities: list[Entity] = field(default_factory=list)
    relationship_files: list[RelationshipFile] = field(default_factory=list)
    rule_files: list[RuleFile] = field(default_factory=list)
    taxonomies: list[Taxonomy] = field(default_factory=list)
    glossary: Optional[Glossary] = None
    views: list[View] = field(default_factory=list)
    observation_files: list[ObservationFile] = field(default_factory=list)
    outcome_files: list[OutcomeFile] = field(default_factory=list)
    decision_files: list[DecisionFile] = field(default_factory=list)
    extensions: dict[str, list] = field(default_factory=dict)

    @property
    def all_relationships(self) -> list[Relationship]:
        return [r for rf in self.relationship_files for r in rf.relationships]

    @property
    def all_traversals(self) -> list[Traversal]:
        return [t for rf in self.relationship_files for t in rf.traversals]

    @property
    def all_rules(self) -> list[Rule]:
        return [r for rf in self.rule_files for r in rf.rules]

    @property
    def entity_names(self) -> set[str]:
        return {e.name for e in self.entities}

    @property
    def all_glossary_entries(self) -> list[GlossaryEntry]:
        return self.glossary.entries if self.glossary else []

    @property
    def all_observations(self) -> list[Observation]:
        return [o for of in self.observation_files for o in of.observations]

    @property
    def all_outcomes(self) -> list[Outcome]:
        return [o for of in self.outcome_files for o in of.outcomes]

    @property
    def all_takeaways(self) -> list[str]:
        return [t for o in self.all_outcomes for t in o.takeaways]

    @property
    def all_claims(self) -> list[KnowledgeClaim]:
        claims = [c for o in self.all_observations for c in o.claims]
        claims.extend(c for d in self.all_decisions for c in d.rationale_claims)
        return claims

    @property
    def all_decisions(self) -> list[Decision]:
        return [d for df in self.decision_files for d in df.decisions]
