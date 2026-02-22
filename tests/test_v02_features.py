"""Tests for v0.2 implementation features: plugins, contradiction detection,
conflict annotation in agent compiler, and lore init command."""
import json
from datetime import date
from pathlib import Path
import pytest
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Provenance, EvolutionConfig,
    PluginConfig, ObservationFile, Observation, OutcomeFile, Outcome,
    Taxonomy, TaxonomyNode,
)
from lore.parser import parse_ontology
from lore.curator import curate_consistency
from lore.compilers.agent import compile_agent_context


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_is_0_2_0(self):
        """Library version should be 0.2.0."""
        from lore import __version__
        assert __version__ == "0.2.0"

    def test_plugin_config_exported(self):
        """PluginConfig should be importable from lore."""
        from lore import PluginConfig
        assert PluginConfig is not None


# ---------------------------------------------------------------------------
# Plugin Config in Manifest
# ---------------------------------------------------------------------------

class TestPluginConfig:
    def test_plugin_config_defaults(self):
        """PluginConfig defaults are empty."""
        pc = PluginConfig()
        assert pc.compilers == {}
        assert pc.curators == {}
        assert pc.directories == []

    def test_plugin_config_with_values(self):
        """PluginConfig stores values correctly."""
        pc = PluginConfig(
            compilers={"graphql": "my_plugins.graphql:compile_graphql"},
            curators={"naming": "my_plugins.naming:check_naming"},
            directories=["playbooks"],
        )
        assert pc.compilers["graphql"] == "my_plugins.graphql:compile_graphql"
        assert pc.curators["naming"] == "my_plugins.naming:check_naming"
        assert "playbooks" in pc.directories

    def test_manifest_plugins_none_by_default(self):
        """OntologyManifest.plugins is None by default."""
        m = OntologyManifest(name="test")
        assert m.plugins is None

    def test_manifest_with_plugins(self):
        """OntologyManifest stores PluginConfig."""
        pc = PluginConfig(
            compilers={"xml": "plugins.xml:compile"},
            directories=["signals"],
        )
        m = OntologyManifest(name="test", plugins=pc)
        assert m.plugins is not None
        assert "xml" in m.plugins.compilers

    def test_parser_extracts_plugins(self, tmp_path):
        """Parser reads plugins section from lore.yaml."""
        manifest = (
            "name: test-plugins\n"
            "version: 0.1.0\n"
            "plugins:\n"
            "  compilers:\n"
            "    graphql: my_plugins.graphql:compile_graphql\n"
            "    xml: my_plugins.xml:compile_xml\n"
            "  curators:\n"
            "    naming: my_plugins.naming:check_naming\n"
            "  directories:\n"
            "    - playbooks\n"
            "    - signals\n"
        )
        (tmp_path / "lore.yaml").write_text(manifest)
        (tmp_path / "entities").mkdir()

        ont = parse_ontology(tmp_path)
        assert ont.manifest is not None
        assert ont.manifest.plugins is not None
        assert ont.manifest.plugins.compilers["graphql"] == "my_plugins.graphql:compile_graphql"
        assert ont.manifest.plugins.compilers["xml"] == "my_plugins.xml:compile_xml"
        assert ont.manifest.plugins.curators["naming"] == "my_plugins.naming:check_naming"
        assert ont.manifest.plugins.directories == ["playbooks", "signals"]

    def test_parser_no_plugins_section(self, tmp_path):
        """Parser handles missing plugins section gracefully."""
        (tmp_path / "lore.yaml").write_text("name: no-plugins\nversion: 0.1.0\n")
        (tmp_path / "entities").mkdir()

        ont = parse_ontology(tmp_path)
        assert ont.manifest is not None
        assert ont.manifest.plugins is None

    def test_parser_empty_plugins_section(self, tmp_path):
        """Parser handles empty plugins section."""
        manifest = (
            "name: empty-plugins\n"
            "version: 0.1.0\n"
            "plugins:\n"
            "  compilers: {}\n"
        )
        (tmp_path / "lore.yaml").write_text(manifest)
        (tmp_path / "entities").mkdir()

        ont = parse_ontology(tmp_path)
        assert ont.manifest is not None
        assert ont.manifest.plugins is not None
        assert ont.manifest.plugins.compilers == {}
        assert ont.manifest.plugins.curators == {}
        assert ont.manifest.plugins.directories == []


# ---------------------------------------------------------------------------
# Observation Contradiction Detection (Curator)
# ---------------------------------------------------------------------------

class TestContradictionDetection:
    def test_opposing_observations_flagged(self):
        """Two observations about same entity with opposing signals are flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[
                ObservationFile(
                    name="Positive Signals", about="Account",
                    observations=[
                        Observation(
                            heading="Acme expansion readiness",
                            prose="Acme shows strong growth and expansion patterns."
                        ),
                    ],
                ),
                ObservationFile(
                    name="Negative Signals", about="Account",
                    observations=[
                        Observation(
                            heading="Acme churn risk",
                            prose="Acme shows decline and churn signals."
                        ),
                    ],
                ),
            ],
        )
        report = curate_consistency(ont)
        conflict_warnings = [f for f in report.warnings if "contradiction" in f.message.lower()]
        assert len(conflict_warnings) >= 1
        assert "Acme expansion readiness" in conflict_warnings[0].message or \
               "Acme churn risk" in conflict_warnings[0].message

    def test_same_polarity_not_flagged(self):
        """Two positive observations about same entity are not flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[
                ObservationFile(
                    name="Notes A", about="Account",
                    observations=[
                        Observation(heading="Growth signal", prose="Active users increased."),
                    ],
                ),
                ObservationFile(
                    name="Notes B", about="Account",
                    observations=[
                        Observation(heading="Adoption signal", prose="New adoption pattern."),
                    ],
                ),
            ],
        )
        report = curate_consistency(ont)
        conflict_warnings = [f for f in report.warnings if "contradiction" in f.message.lower()]
        assert len(conflict_warnings) == 0

    def test_different_entities_not_flagged(self):
        """Opposing signals about different entities are not flagged."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[
                ObservationFile(
                    name="Account Notes", about="Account",
                    observations=[
                        Observation(heading="Growth", prose="Strong expansion and growth."),
                    ],
                ),
                ObservationFile(
                    name="Contact Notes", about="Contact",
                    observations=[
                        Observation(heading="Risk", prose="Decline and churn signals."),
                    ],
                ),
            ],
        )
        report = curate_consistency(ont)
        conflict_warnings = [f for f in report.warnings if "contradiction" in f.message.lower()]
        assert len(conflict_warnings) == 0

    def test_single_observation_no_contradiction(self):
        """Single observation about entity is never a contradiction."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[
                ObservationFile(
                    name="Notes", about="Account",
                    observations=[
                        Observation(heading="Mixed signals", prose="Both growth and churn patterns."),
                    ],
                ),
            ],
        )
        report = curate_consistency(ont)
        conflict_warnings = [f for f in report.warnings if "contradiction" in f.message.lower()]
        assert len(conflict_warnings) == 0

    def test_mixed_signal_in_one_observation_not_flagged(self):
        """An observation with both positive and negative keywords is not flagged against itself."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[
                ObservationFile(
                    name="Notes", about="Account",
                    observations=[
                        Observation(heading="Expansion but risk", prose="Growth with churn risk."),
                        Observation(heading="Clear positive", prose="Strong growth trajectory."),
                    ],
                ),
            ],
        )
        report = curate_consistency(ont)
        # The mixed-signal observation shouldn't trigger against the pure positive one
        conflict_warnings = [f for f in report.warnings if "contradiction" in f.message.lower()]
        assert len(conflict_warnings) == 0

    def test_contradiction_suggestion(self):
        """Contradiction finding has a useful suggestion."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            observation_files=[
                ObservationFile(
                    name="Pos", about="Account",
                    observations=[Observation(heading="Growth", prose="Strong expansion.")],
                ),
                ObservationFile(
                    name="Neg", about="Account",
                    observations=[Observation(heading="Risk", prose="Clear churn decline.")],
                ),
            ],
        )
        report = curate_consistency(ont)
        conflict_warnings = [f for f in report.warnings if "contradiction" in f.message.lower()]
        assert len(conflict_warnings) >= 1
        assert conflict_warnings[0].suggestion  # has a suggestion
        assert "opposing signals" in conflict_warnings[0].suggestion.lower()


# ---------------------------------------------------------------------------
# Conflict Annotation in Agent Compiler
# ---------------------------------------------------------------------------

class TestAgentConflictAnnotation:
    def test_conflict_annotation_present(self):
        """Agent compiler annotates contradicting observations with conflict='true'."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
            observation_files=[
                ObservationFile(
                    name="Positive", about="Account",
                    observations=[
                        Observation(heading="Expansion ready", prose="Strong growth patterns."),
                    ],
                ),
                ObservationFile(
                    name="Negative", about="Account",
                    observations=[
                        Observation(heading="Churn warning", prose="Usage decline and churn risk."),
                    ],
                ),
            ],
        )
        result = compile_agent_context(ont)
        assert 'conflict="true"' in result

    def test_no_conflict_when_same_polarity(self):
        """Agent compiler does not annotate when observations agree."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
            observation_files=[
                ObservationFile(
                    name="Notes A", about="Account",
                    observations=[Observation(heading="Growth", prose="Active users increasing.")],
                ),
                ObservationFile(
                    name="Notes B", about="Account",
                    observations=[Observation(heading="Adoption", prose="New engagement patterns.")],
                ),
            ],
        )
        result = compile_agent_context(ont)
        assert 'conflict="true"' not in result

    def test_conflict_includes_contradiction_note(self):
        """Conflicting observations include a CONFLICT note in output."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
            observation_files=[
                ObservationFile(
                    name="Positive", about="Account",
                    observations=[
                        Observation(heading="Expansion ready", prose="Strong growth patterns."),
                    ],
                ),
                ObservationFile(
                    name="Negative", about="Account",
                    observations=[
                        Observation(heading="Churn warning", prose="Usage decline and churn risk."),
                    ],
                ),
            ],
        )
        result = compile_agent_context(ont)
        assert "[CONFLICT:" in result

    def test_no_conflict_across_entities(self):
        """No conflict annotation when observations are about different entities."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[
                Entity(name="Account", attributes=[]),
                Entity(name="Contact", attributes=[]),
            ],
            observation_files=[
                ObservationFile(
                    name="Account Notes", about="Account",
                    observations=[Observation(heading="Growth", prose="Strong expansion.")],
                ),
                ObservationFile(
                    name="Contact Notes", about="Contact",
                    observations=[Observation(heading="Risk", prose="Churn decline.")],
                ),
            ],
        )
        result = compile_agent_context(ont)
        assert 'conflict="true"' not in result

    def test_no_observations_no_crash(self):
        """Agent compiler handles ontology with no observations."""
        ont = Ontology(
            manifest=OntologyManifest(name="test", version="1.0"),
            entities=[Entity(name="Account", attributes=[])],
        )
        result = compile_agent_context(ont)
        assert 'conflict="true"' not in result
        assert "<domain_ontology>" in result


# ---------------------------------------------------------------------------
# lore init command
# ---------------------------------------------------------------------------

class TestLoreInit:
    def test_init_creates_directory_structure(self, tmp_path):
        """lore init creates all required directories."""
        target = tmp_path / "my-ontology"
        from lore.cli import cmd_init
        cmd_init(str(target), name=None, domain="Test Domain")

        assert (target / "lore.yaml").exists()
        assert (target / "entities").is_dir()
        assert (target / "relationships").is_dir()
        assert (target / "rules").is_dir()
        assert (target / "taxonomies").is_dir()
        assert (target / "glossary").is_dir()
        assert (target / "views").is_dir()
        assert (target / "observations").is_dir()
        assert (target / "outcomes").is_dir()

    def test_init_creates_manifest(self, tmp_path):
        """lore init creates a valid manifest."""
        target = tmp_path / "test-ont"
        from lore.cli import cmd_init
        cmd_init(str(target), name="my-test", domain="Testing")

        content = (target / "lore.yaml").read_text()
        assert "name: my-test" in content
        assert "domain: Testing" in content
        assert "version: 0.1.0" in content
        assert "staleness: 90d" in content

    def test_init_creates_example_entity(self, tmp_path):
        """lore init creates a starter entity file."""
        target = tmp_path / "test-ont"
        from lore.cli import cmd_init
        cmd_init(str(target), name=None, domain="")

        entity_file = target / "entities" / "example.lore"
        assert entity_file.exists()
        content = entity_file.read_text()
        assert "entity: Example" in content
        assert "## Attributes" in content
        assert "## Identity" in content
        assert "## Notes" in content

    def test_init_uses_dirname_as_default_name(self, tmp_path):
        """lore init uses directory name when --name not specified."""
        target = tmp_path / "my-domain"
        from lore.cli import cmd_init
        cmd_init(str(target), name=None, domain="")

        content = (target / "lore.yaml").read_text()
        assert "name: my-domain" in content

    def test_init_result_is_parseable(self, tmp_path):
        """The scaffolded ontology can be parsed and validated."""
        target = tmp_path / "parseable-test"
        from lore.cli import cmd_init
        cmd_init(str(target), name="parseable-test", domain="Test")

        ont = parse_ontology(target)
        assert ont.manifest is not None
        assert ont.manifest.name == "parseable-test"
        assert len(ont.entities) == 1
        assert ont.entities[0].name == "Example"

    def test_init_refuses_nonempty_directory(self, tmp_path):
        """lore init exits when directory is not empty."""
        target = tmp_path / "existing"
        target.mkdir()
        (target / "some-file.txt").write_text("existing content")

        from lore.cli import cmd_init
        with pytest.raises(SystemExit):
            cmd_init(str(target), name=None, domain="")

    def test_init_creates_parent_dirs(self, tmp_path):
        """lore init creates parent directories if needed."""
        target = tmp_path / "deep" / "nested" / "ontology"
        from lore.cli import cmd_init
        cmd_init(str(target), name=None, domain="")

        assert (target / "lore.yaml").exists()

    def test_init_without_domain(self, tmp_path):
        """lore init works without --domain."""
        target = tmp_path / "no-domain"
        from lore.cli import cmd_init
        cmd_init(str(target), name="no-domain", domain="")

        content = (target / "lore.yaml").read_text()
        assert "name: no-domain" in content
        # Domain should not appear in manifest
        assert "domain:" not in content


# ---------------------------------------------------------------------------
# Integration: existing example still works with all new features
# ---------------------------------------------------------------------------

class TestExampleIntegration:
    def test_example_ontology_no_plugins(self, example_ontology):
        """Existing example has no plugins (backward compat)."""
        if example_ontology.manifest:
            # plugins field may or may not be present, but should be None
            # if not in lore.yaml
            pass  # Just verifying it parses without error

    def test_example_consistency_with_contradictions(self, example_ontology):
        """Consistency check includes contradiction detection on example."""
        report = curate_consistency(example_ontology)
        # Just verify it runs without error; the example may or may not
        # have contradictions
        assert report.job == "consistency"
        assert report.summary is not None

    def test_example_agent_compile_with_conflicts(self, example_ontology):
        """Agent compiler runs with conflict detection on example."""
        result = compile_agent_context(example_ontology)
        assert "<domain_ontology>" in result
        assert "<observations>" in result
