"""Tests for the Lore indexer — INDEX.lore routing file generation."""
from datetime import date
from pathlib import Path
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, ObservationFile, Observation,
    View, Taxonomy, TaxonomyNode, Glossary, GlossaryEntry, KnowledgeClaim,
)
from lore.indexer import (
    generate_root_index, generate_directory_index,
    generate_all_indexes, write_indexes,
)
from lore.parser import parse_ontology
from lore.curator import curate_index


# ---------------------------------------------------------------------------
# Root index generation
# ---------------------------------------------------------------------------

class TestRootIndex:
    def test_contains_ontology_name(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="my-project", version="1.0",
                                      description="Test ontology"),
            entities=[Entity(name="Account", attributes=[])],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "my-project" in result
        assert "v1.0" in result

    def test_contains_stats(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="A", attributes=[Attribute(name="id", type="string")]),
                Entity(name="B", attributes=[]),
            ],
            relationship_files=[RelationshipFile(
                domain="Core",
                relationships=[Relationship(name="R", from_entity="A", to_entity="B")],
            )],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "2 entities" in result
        assert "1 relationships" in result

    def test_contains_entity_listing(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Account", description="A customer", attributes=[
                    Attribute(name="id", type="string"),
                    Attribute(name="name", type="string"),
                ]),
            ],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "**Account** (2 attrs)" in result

    def test_contains_search_guide(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "Search Guide" in result
        assert "entities/" in result

    def test_contains_frontmatter(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "index: true" in result
        assert "generated: 2025-06-01" in result

    def test_directory_map_counts_files(self, tmp_path):
        """Directory map shows file counts for existing directories."""
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "account.lore").write_text("test")
        (tmp_path / "entities" / "contact.lore").write_text("test")
        (tmp_path / "rules").mkdir()
        (tmp_path / "rules" / "churn.lore").write_text("test")

        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "entities/" in result
        assert "2 files" in result
        assert "rules/" in result

    def test_view_names_in_search_guide(self, tmp_path):
        """Search guide mentions available views."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            views=[
                View(name="AE", audience="Account Executives"),
                View(name="CSM", audience="Customer Success"),
            ],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "AE" in result
        assert "CSM" in result

    def test_agent_first_sections_present(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[], notes="Long enough context for agent use.")],
            observation_files=[ObservationFile(
                name="Discovery",
                about="Account",
                date="2025-05-15",
                observations=[Observation(
                    heading="Signal",
                    prose="Detailed signal text.",
                    claims=[KnowledgeClaim(kind="fact", text="Client requires SSO")],
                )],
            )],
        )
        result = generate_root_index(ont, tmp_path, today=date(2025, 6, 1))
        assert "Agent-First Reading Order" in result
        assert "Recent Learning Signals" in result
        assert "claims" in result


# ---------------------------------------------------------------------------
# Directory index generation
# ---------------------------------------------------------------------------

class TestDirectoryIndex:
    def test_entities_index(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Account", attributes=[
                    Attribute(name="id", type="string"),
                ], notes="Has notes.", source_file=tmp_path / "entities" / "account.lore"),
            ],
        )
        result = generate_directory_index(ont, tmp_path / "entities", "entities",
                                          today=date(2025, 6, 1))
        assert "**Account**" in result
        assert "1 attrs" in result
        assert "notes" in result

    def test_relationships_index(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            relationship_files=[RelationshipFile(
                domain="Core",
                relationships=[
                    Relationship(name="HAS_CONTACT", from_entity="Account", to_entity="Contact"),
                ],
                source_file=tmp_path / "relationships" / "core.lore",
            )],
        )
        result = generate_directory_index(ont, tmp_path / "relationships", "relationships",
                                          today=date(2025, 6, 1))
        assert "HAS_CONTACT" in result
        assert "Account" in result
        assert "Contact" in result

    def test_rules_index(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            rule_files=[RuleFile(
                domain="Churn",
                rules=[Rule(name="churn-alert", applies_to="Account", severity="critical")],
                source_file=tmp_path / "rules" / "churn.lore",
            )],
        )
        result = generate_directory_index(ont, tmp_path / "rules", "rules",
                                          today=date(2025, 6, 1))
        assert "churn-alert" in result
        assert "Account" in result
        assert "critical" in result

    def test_observations_index(self, tmp_path):
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[ObservationFile(
                name="Q2 Notes", about="Account", date="2025-05-01",
                observations=[
                    Observation(heading="Signal A", prose="text"),
                    Observation(heading="Signal B", prose="text"),
                ],
                source_file=tmp_path / "observations" / "q2.lore",
            )],
        )
        result = generate_directory_index(ont, tmp_path / "observations", "observations",
                                          today=date(2025, 6, 1))
        assert "Q2 Notes" in result
        assert "Account" in result
        assert "2 observations" in result


# ---------------------------------------------------------------------------
# Full index generation
# ---------------------------------------------------------------------------

class TestGenerateAllIndexes:
    def test_generates_root_and_directories(self, tmp_path):
        """Generates indexes for root and all populated directories."""
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "account.lore").write_text("test")
        (tmp_path / "rules").mkdir()
        (tmp_path / "rules" / "churn.lore").write_text("test")
        (tmp_path / "relationships").mkdir()  # empty — no index

        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[],
                             source_file=tmp_path / "entities" / "account.lore")],
            rule_files=[RuleFile(domain="Churn",
                                 rules=[Rule(name="test", applies_to="Account")],
                                 source_file=tmp_path / "rules" / "churn.lore")],
        )
        indexes = generate_all_indexes(ont, tmp_path, today=date(2025, 6, 1))
        assert "INDEX.lore" in indexes
        assert "entities/INDEX.lore" in indexes
        assert "rules/INDEX.lore" in indexes
        # Empty directory should not get an index
        assert "relationships/INDEX.lore" not in indexes

    def test_write_indexes_creates_files(self, tmp_path):
        """write_indexes creates actual files on disk."""
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "account.lore").write_text("test")

        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[],
                             source_file=tmp_path / "entities" / "account.lore")],
        )
        written = write_indexes(ont, tmp_path, today=date(2025, 6, 1))
        assert len(written) >= 2  # root + entities
        assert (tmp_path / "INDEX.lore").exists()
        assert (tmp_path / "entities" / "INDEX.lore").exists()


# ---------------------------------------------------------------------------
# INDEX.lore excluded from parsing
# ---------------------------------------------------------------------------

class TestIndexExcludedFromParsing:
    def test_parser_skips_index_files(self, tmp_path):
        """Parser should not treat INDEX.lore as an entity/relationship/etc."""
        (tmp_path / "lore.yaml").write_text("name: test\nversion: 1.0\n")
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "account.lore").write_text(
            "---\nentity: Account\n---\n## Attributes\nname: string\n"
        )
        (tmp_path / "entities" / "INDEX.lore").write_text(
            "---\nindex: true\ngenerated: 2025-06-01\n---\n## Overview\ntest\n"
        )
        ont = parse_ontology(tmp_path)
        assert len(ont.entities) == 1
        assert ont.entities[0].name == "Account"


# ---------------------------------------------------------------------------
# Index curator job
# ---------------------------------------------------------------------------

class TestIndexCurator:
    def test_missing_root_index(self, tmp_path):
        """Missing root INDEX.lore is a warning."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        report = curate_index(ont, root_dir=tmp_path)
        warnings = [f for f in report.warnings if "Root INDEX.lore" in f.message]
        assert len(warnings) == 1

    def test_stale_root_index(self, tmp_path):
        """Root INDEX.lore with wrong entity count is stale."""
        (tmp_path / "INDEX.lore").write_text(
            "---\nindex: true\n---\n## Stats\n- 5 entities, 10 relationships\n"
        )
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="A", attributes=[]), Entity(name="B", attributes=[])],
        )
        report = curate_index(ont, root_dir=tmp_path)
        stale = [f for f in report.warnings if "stale" in f.message.lower()]
        assert len(stale) == 1

    def test_up_to_date_root_index(self, tmp_path):
        """Root INDEX.lore with correct entity count is fine."""
        (tmp_path / "INDEX.lore").write_text(
            "---\nindex: true\n---\n## Stats\n- 2 entities, 0 relationships\n"
        )
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="A", attributes=[]), Entity(name="B", attributes=[])],
        )
        report = curate_index(ont, root_dir=tmp_path)
        root_warnings = [f for f in report.warnings if "Root" in f.message]
        assert len(root_warnings) == 0

    def test_missing_directory_index(self, tmp_path):
        """Directory without INDEX.lore is flagged as info."""
        (tmp_path / "INDEX.lore").write_text(
            "---\nindex: true\n---\n## Stats\n- 1 entities\n"
        )
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "account.lore").write_text("test")

        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        report = curate_index(ont, root_dir=tmp_path)
        dir_infos = [f for f in report.infos if "entities/INDEX.lore" in f.message]
        assert len(dir_infos) == 1

    def test_stale_directory_index(self, tmp_path):
        """Directory INDEX.lore missing a file is flagged."""
        (tmp_path / "INDEX.lore").write_text(
            "---\nindex: true\n---\n## Stats\n- 1 entities\n"
        )
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "account.lore").write_text("test")
        (tmp_path / "entities" / "contact.lore").write_text("test")
        (tmp_path / "entities" / "INDEX.lore").write_text(
            "---\nindex: true\n---\n## Contents\n- account.lore\n"
        )

        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        report = curate_index(ont, root_dir=tmp_path)
        stale = [f for f in report.warnings if "stale" in f.message.lower() and "entities" in f.message]
        assert len(stale) == 1
        assert "contact.lore" in stale[0].message

    def test_no_root_dir_skips(self):
        """No root_dir provided skips the check."""
        ont = Ontology(manifest=OntologyManifest(name="test", version="1.0"))
        report = curate_index(ont, root_dir=None)
        assert len(report.findings) == 0
        assert "skipping" in report.summary.lower()


# ---------------------------------------------------------------------------
# Integration with example ontology
# ---------------------------------------------------------------------------

class TestIndexOnExample:
    def test_example_generates_indexes(self, example_ontology):
        """Indexer runs on full example without errors."""
        from pathlib import Path
        root = Path("examples/b2b-saas-gtm")
        indexes = generate_all_indexes(example_ontology, root, today=date(2025, 6, 1))
        assert "INDEX.lore" in indexes
        assert "entities/INDEX.lore" in indexes
        # Root should mention all 11 entities
        assert "11 entities" in indexes["INDEX.lore"]
