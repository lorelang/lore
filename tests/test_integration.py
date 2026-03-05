"""Integration tests for the full Lore pipeline."""
import json
import pytest
from pathlib import Path
from lore.parser import parse_ontology
from lore.validator import validate, Severity
from lore.compilers.agent import compile_agent_context
from lore.compilers.json_export import compile_json
from lore.compilers.jsonld import compile_jsonld
from lore.compilers.neo4j import compile_neo4j
from lore.compilers.mermaid import compile_mermaid
from lore.compilers.embeddings import compile_embeddings
from lore.compilers.tools import compile_tools
from lore.compilers.agents_md import compile_agents_md
from lore.compilers.metrics import compile_metrics
from lore.projection import estimate_tokens
from lore.models import (
    Ontology, OntologyManifest, Entity, Attribute, Relationship,
    RelationshipFile, Rule, RuleFile, Taxonomy, TaxonomyNode,
    Glossary, GlossaryEntry, View, Provenance,
    ObservationFile, Observation, KnowledgeClaim,
    OutcomeFile, Outcome,
)


EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "b2b-saas-gtm"

ALL_COMPILERS = {
    "agent": lambda ont: compile_agent_context(ont),
    "json": compile_json,
    "jsonld": compile_jsonld,
    "neo4j": compile_neo4j,
    "mermaid": compile_mermaid,
    "embeddings": compile_embeddings,
    "tools": lambda ont: compile_tools(ont),
    "agents.md": lambda ont: compile_agents_md(ont),
    "metrics": lambda ont: compile_metrics(ont),
}


class TestFullPipelineParseValidateCompile:
    """Create ontology on disk, parse, validate, compile all targets."""

    def test_all_targets_on_disk_ontology(self, tmp_path):
        # Create a minimal but complete ontology on disk
        (tmp_path / "lore.yaml").write_text(
            "name: pipeline-test\n"
            "version: 1.0\n"
            "description: Full pipeline test ontology.\n"
        )
        (tmp_path / "entities").mkdir()
        (tmp_path / "entities" / "widget.lore").write_text(
            "---\n"
            "entity: Widget\n"
            "description: A test widget.\n"
            "status: stable\n"
            "provenance:\n"
            "  author: tester\n"
            "  source: domain-expert\n"
            "  confidence: 0.9\n"
            "  created: 2025-01-01\n"
            "---\n"
            "\n"
            "## Attributes\n\n"
            "id: string [required, unique]\n"
            "  | The widget identifier.\n"
            "\n"
            "status: enum [active, inactive] [required]\n"
            "  | Current state.\n"
            "\n"
            "## Identity\n\n"
            "A Widget is identified by its id.\n"
            "\n"
            "## Notes\n\n"
            "Widgets are the core unit of the system.\n"
        )
        (tmp_path / "relationships").mkdir()
        (tmp_path / "relationships" / "core.lore").write_text(
            "---\n"
            "domain: Core Relationships\n"
            "---\n"
            "\n"
            "## CONTAINS\n"
            "  from: Widget -> to: Widget\n"
            "  cardinality: one-to-many\n"
            "  | A widget can contain sub-widgets.\n"
        )
        (tmp_path / "rules").mkdir()
        (tmp_path / "rules" / "alerts.lore").write_text(
            "---\n"
            "domain: Alert Rules\n"
            "---\n"
            "\n"
            "## inactive-alert\n"
            "  applies_to: Widget\n"
            "  severity: warning\n"
            "  condition:\n"
            "    Widget.status = 'inactive'\n"
            "  action:\n"
            "    Flag for review\n"
        )
        (tmp_path / "glossary").mkdir()
        (tmp_path / "glossary" / "terms.lore").write_text(
            "---\n"
            "description: Core terms.\n"
            "---\n"
            "\n"
            "## Widget\n\n"
            "The fundamental unit.\n"
        )
        (tmp_path / "views").mkdir()
        (tmp_path / "views" / "admin.lore").write_text(
            "---\n"
            "view: Admin\n"
            "audience: Administrators\n"
            "---\n"
            "\n"
            "## Entities\n"
            "- Widget\n"
            "\n"
            "## Key Questions\n"
            "- How many widgets are inactive?\n"
        )

        # Parse
        ontology = parse_ontology(tmp_path)
        assert len(ontology.entities) == 1
        assert ontology.entities[0].name == "Widget"

        # Validate
        diags = validate(ontology)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        assert len(errors) == 0, f"Validation errors: {errors}"

        # Compile all targets
        for target_name, compile_fn in ALL_COMPILERS.items():
            result = compile_fn(ontology)
            assert isinstance(result, str), f"{target_name} did not return string"
            assert len(result) > 0 or target_name == "embeddings", \
                f"{target_name} returned empty output"


class TestInitThenValidate:
    """cmd_init scaffold -> parse -> validate. Zero errors."""

    def test_init_scaffold_validates(self, tmp_path):
        from lore.cli import cmd_init
        target = tmp_path / "test-ontology"
        cmd_init(str(target), "test-ontology", "Test domain")

        ontology = parse_ontology(target)
        diags = validate(ontology)
        errors = [d for d in diags if d.severity == Severity.ERROR]
        assert len(errors) == 0


class TestViewScopingEffectiveness:
    """Full vs each view — each view strictly smaller or similar size.

    A view that scopes to "all entities" may be slightly larger than
    unscoped output because it adds view metadata (description, audience,
    key questions). We check that scoped views don't explode in size.
    """

    def test_view_produces_comparable_output(self):
        ontology = parse_ontology(EXAMPLE_DIR)
        full = compile_agent_context(ontology)
        full_tokens = estimate_tokens(full)

        for view in ontology.views:
            scoped = compile_agent_context(ontology, view_name=view.name)
            scoped_tokens = estimate_tokens(scoped)
            # Scoped should be at most 10% larger than full (metadata overhead)
            assert scoped_tokens <= full_tokens * 1.1, \
                f"View '{view.name}' ({scoped_tokens} tokens) >> full ({full_tokens} tokens)"


class TestEvolveGeneratesProposals:
    """Ontology with outcomes -> evolve(). Proposals generated."""

    def test_evolve_produces_proposals(self, tmp_path):
        from lore.evolution import evolve

        ontology = parse_ontology(EXAMPLE_DIR)
        if not ontology.all_takeaways:
            pytest.skip("No takeaways in example ontology")

        proposals = evolve(ontology, tmp_path / "proposals")
        assert len(proposals) > 0
        for p in proposals:
            assert "name" in p
            assert "path" in p


class TestCompileOutputSizeScalesLinearly:
    """10, 50, 100 entities — assert linear (not exponential) growth."""

    def test_linear_scaling(self):
        def _make_ont(n: int) -> Ontology:
            return Ontology(
                manifest=OntologyManifest(name="scale-test", version="1.0"),
                entities=[
                    Entity(
                        name=f"Entity_{i}",
                        description=f"Description for entity {i}.",
                        attributes=[
                            Attribute(name="id", type="string",
                                      constraints=["required"]),
                            Attribute(name="value", type="float"),
                        ],
                        notes=f"Notes for entity {i}.",
                    )
                    for i in range(n)
                ],
            )

        size_10 = len(compile_agent_context(_make_ont(10)))
        size_50 = len(compile_agent_context(_make_ont(50)))
        size_100 = len(compile_agent_context(_make_ont(100)))

        # Output should grow roughly linearly
        # size_100 / size_10 should be ~10x, not exponential
        ratio = size_100 / size_10
        assert ratio < 15, f"Growth ratio {ratio:.1f}x is not linear"

        # 50 should be roughly between 10 and 100
        assert size_10 < size_50 < size_100


class TestNewCompilerTargets:
    """New compiler targets produce valid output on the example ontology."""

    def test_tools_compiler(self):
        ontology = parse_ontology(EXAMPLE_DIR)
        result = compile_tools(ontology)
        schemas = json.loads(result)
        assert isinstance(schemas, list)
        assert len(schemas) > 0
        # Check structure
        for schema in schemas:
            assert "type" in schema or "name" in schema

    def test_agents_md_compiler(self):
        ontology = parse_ontology(EXAMPLE_DIR)
        result = compile_agents_md(ontology)
        assert "# Domain Knowledge" in result
        assert "Account" in result

    def test_agents_md_with_view(self):
        ontology = parse_ontology(EXAMPLE_DIR)
        if ontology.views:
            view_name = ontology.views[0].name
            result = compile_agents_md(ontology, view_name=view_name)
            assert "---" in result  # YAML frontmatter

    def test_metrics_compiler(self):
        ontology = parse_ontology(EXAMPLE_DIR)
        result = compile_metrics(ontology)
        data = json.loads(result)
        assert "counts" in data
        assert "coverage" in data
        assert "status_distribution" in data
        assert data["counts"]["entities"] > 0
