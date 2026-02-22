"""Tests for provenance and status (Phase 1)."""
import json
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Provenance,
    Relationship, RelationshipFile,
)
from lore.validator import validate, Severity
from lore.compilers.agent import compile_agent_context
from lore.compilers.json_export import compile_json
from lore.compilers.embeddings import compile_embeddings


class TestProvenanceModel:
    def test_defaults(self):
        p = Provenance()
        assert p.author == ""
        assert p.source == ""
        assert p.confidence is None
        assert p.created == ""
        assert p.deprecated == ""

    def test_full_provenance(self):
        p = Provenance(
            author="revops-team",
            source="domain-expert",
            confidence=0.95,
            created="2025-01-15",
            deprecated="",
        )
        assert p.confidence == 0.95
        assert p.created == "2025-01-15"


class TestProvenanceParser:
    def test_entity_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"thing.lore": """---
entity: Thing
description: A thing
provenance:
  author: ai-agent-v1
  source: ai-generated
  confidence: 0.72
  created: 2025-06-01
status: proposed
---
## Attributes
id: string [required]
"""},
        )
        entity = ont.entities[0]
        assert entity.provenance is not None
        assert entity.provenance.author == "ai-agent-v1"
        assert entity.provenance.source == "ai-generated"
        assert entity.provenance.confidence == 0.72
        assert entity.provenance.created == "2025-06-01"
        assert entity.status == "proposed"

    def test_entity_without_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"thing.lore": "---\nentity: Thing\n---\n## Attributes\nid: string"},
        )
        entity = ont.entities[0]
        assert entity.provenance is None
        assert entity.status == ""

    def test_relationship_file_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={
                "a.lore": "---\nentity: A\n---\n## Attributes\nid: string",
                "b.lore": "---\nentity: B\n---\n## Attributes\nid: string",
            },
            relationships={"rels.lore": """---
domain: Core
provenance:
  author: domain-team
  source: domain-expert
  confidence: 0.9
status: stable
---
## HAS_B
  from: A -> to: B
  cardinality: one-to-many
"""},
        )
        rf = ont.relationship_files[0]
        assert rf.provenance is not None
        assert rf.provenance.source == "domain-expert"
        assert rf.status == "stable"

    def test_rule_file_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            rules={"alerts.lore": """---
domain: Alerts
provenance:
  author: ml-team
  source: derived
  confidence: 0.65
status: draft
---
## test-rule
  applies_to: Widget
  severity: info
"""},
        )
        rf = ont.rule_files[0]
        assert rf.provenance is not None
        assert rf.provenance.confidence == 0.65
        assert rf.status == "draft"

    def test_taxonomy_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            taxonomies={"types.lore": """---
taxonomy: Types
provenance:
  author: analyst
  source: imported
status: stable
---
Root
├── Child A
└── Child B
"""},
        )
        tax = ont.taxonomies[0]
        assert tax.provenance is not None
        assert tax.provenance.source == "imported"

    def test_glossary_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            glossary={"terms.lore": """---
type: glossary
provenance:
  author: editorial
  source: domain-expert
  confidence: 1.0
status: stable
---
## Widget
A thing that does stuff.
"""},
        )
        assert ont.glossary.provenance is not None
        assert ont.glossary.provenance.confidence == 1.0

    def test_view_with_provenance(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            views={"admin.lore": """---
view: Admin
provenance:
  author: platform-team
  source: domain-expert
status: stable
---
## Entities
- Widget
## Key Questions
- How many widgets?
"""},
        )
        view = ont.views[0]
        assert view.provenance is not None

    def test_deprecated_entity(self, tmp_ontology):
        ont = tmp_ontology(
            manifest="name: test\nversion: 0.1.0",
            entities={"old.lore": """---
entity: OldThing
provenance:
  author: cleanup-agent
  source: derived
  created: 2024-01-01
  deprecated: 2025-06-01
status: deprecated
---
## Attributes
id: string
"""},
        )
        entity = ont.entities[0]
        assert entity.status == "deprecated"
        assert entity.provenance.deprecated == "2025-06-01"
        assert entity.provenance.created == "2024-01-01"


class TestProvenanceValidation:
    def test_confidence_out_of_range_high(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Bad",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(confidence=1.5),
            )],
        )
        diags = validate(ont)
        assert any("outside valid range" in d.message for d in diags if d.severity == Severity.WARNING)

    def test_confidence_out_of_range_low(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Bad",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(confidence=-0.1),
            )],
        )
        diags = validate(ont)
        assert any("outside valid range" in d.message for d in diags if d.severity == Severity.WARNING)

    def test_valid_confidence(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Good",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(confidence=0.85),
            )],
        )
        diags = validate(ont)
        confidence_warnings = [d for d in diags if "outside valid range" in d.message]
        assert len(confidence_warnings) == 0

    def test_unknown_status(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Bad",
                attributes=[Attribute(name="id", type="string")],
                status="unknown-status",
            )],
        )
        diags = validate(ont)
        assert any("unknown status" in d.message for d in diags if d.severity == Severity.WARNING)

    def test_deprecated_entity_referenced(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Active", attributes=[Attribute(name="id", type="string")]),
                Entity(name="Old", attributes=[Attribute(name="id", type="string")], status="deprecated"),
            ],
            relationship_files=[RelationshipFile(
                domain="test",
                relationships=[Relationship(
                    name="USES_OLD",
                    from_entity="Active",
                    to_entity="Old",
                    cardinality="one-to-many",
                )],
            )],
        )
        diags = validate(ont)
        assert any("deprecated entity 'Old'" in d.message for d in diags if d.severity == Severity.WARNING)

    def test_non_standard_source(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Foo",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(source="custom-pipeline"),
            )],
        )
        diags = validate(ont)
        assert any("non-standard provenance source" in d.message for d in diags if d.severity == Severity.INFO)


class TestProvenanceInAgentCompiler:
    def test_provenance_in_agent_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Widget",
                description="A widget",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(author="ai-v1", source="ai-generated", confidence=0.72, created="2025-06-01"),
                status="proposed",
            )],
        )
        result = compile_agent_context(ont)
        assert "Status: proposed" in result
        assert "Provenance:" in result
        assert "source=ai-generated" in result
        assert "confidence=0.72" in result
        assert "author=ai-v1" in result
        assert "created=2025-06-01" in result

    def test_no_provenance_no_extra_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Widget",
                description="A widget",
                attributes=[Attribute(name="id", type="string")],
            )],
        )
        result = compile_agent_context(ont)
        assert "Provenance:" not in result
        assert "Status:" not in result


class TestProvenanceInJsonCompiler:
    def test_provenance_in_json_output(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Widget",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(author="team", source="domain-expert", confidence=0.9),
                status="stable",
            )],
        )
        data = json.loads(compile_json(ont))
        entity = data["entities"][0]
        assert entity["provenance"]["author"] == "team"
        assert entity["provenance"]["confidence"] == 0.9
        assert entity["status"] == "stable"

    def test_no_provenance_no_fields(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Widget",
                attributes=[Attribute(name="id", type="string")],
            )],
        )
        data = json.loads(compile_json(ont))
        entity = data["entities"][0]
        assert "provenance" not in entity
        assert "status" not in entity


class TestProvenanceInEmbeddingsCompiler:
    def test_provenance_metadata_in_chunks(self):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(
                name="Widget",
                description="A widget",
                attributes=[Attribute(name="id", type="string")],
                provenance=Provenance(source="ai-generated", confidence=0.72, created="2025-06-01"),
                status="proposed",
            )],
        )
        result = compile_embeddings(ont)
        chunks = [json.loads(line) for line in result.strip().split("\n")]
        entity_chunk = next(c for c in chunks if c["type"] == "entity")
        assert entity_chunk["metadata"]["provenance_source"] == "ai-generated"
        assert entity_chunk["metadata"]["provenance_confidence"] == 0.72
        assert entity_chunk["metadata"]["status"] == "proposed"


class TestBackwardCompatibility:
    def test_v01_example_still_works(self, example_ontology):
        """The existing B2B SaaS example should still parse and validate."""
        diags = validate(example_ontology)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_v01_example_entities_provenance_optional(self, example_ontology):
        """Original v0.1 entities have no provenance; new v0.2 entities may have it."""
        # Original entities (Account, Contact, etc.) still have no provenance
        original_entities = ["Account", "Contact", "Interaction", "Opportunity",
                             "Signal", "Subscription", "Usage"]
        for entity in example_ontology.entities:
            if entity.name in original_entities:
                assert entity.provenance is None, f"{entity.name} should not have provenance"
                assert entity.status == "", f"{entity.name} should have empty status"
        # New v0.2 entities (Competitor, Feature, Play, Product) may have provenance
        entities_with_provenance = [e for e in example_ontology.entities if e.provenance is not None]
        assert len(entities_with_provenance) >= 1, "At least some new entities should have provenance"

    def test_v01_compilers_still_work(self, example_ontology):
        """All compilers should still produce valid output."""
        from lore.compilers.neo4j import compile_neo4j
        from lore.compilers.mermaid import compile_mermaid

        assert compile_agent_context(example_ontology)
        assert json.loads(compile_json(example_ontology))
        assert compile_neo4j(example_ontology)
        assert compile_mermaid(example_ontology)
        assert compile_embeddings(example_ontology)
