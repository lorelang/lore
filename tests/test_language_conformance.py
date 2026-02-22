"""Language-level conformance checks for Lorelang fixtures."""
from pathlib import Path

from lore.compilers.agent import compile_agent_context
from lore.compilers.embeddings import compile_embeddings
from lore.compilers.json_export import compile_json
from lore.compilers.jsonld import compile_jsonld
from lore.compilers.mermaid import compile_mermaid
from lore.compilers.neo4j import compile_neo4j
from lore.compilers.palantir import compile_palantir
from lore.parser import parse_ontology
from lore.validator import Severity, validate


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "conformance" / "v0.2" / "core"


def test_conformance_fixture_parses():
    ontology = parse_ontology(_fixture_dir())
    assert ontology.manifest is not None
    assert ontology.manifest.name == "lorelang-v0-2-core"
    assert len(ontology.entities) >= 2
    assert len(ontology.views) >= 1
    assert len(ontology.observation_files) >= 1
    assert len(ontology.outcome_files) >= 1


def test_conformance_fixture_has_no_validation_errors():
    ontology = parse_ontology(_fixture_dir())
    diagnostics = validate(ontology)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    assert errors == []


def test_conformance_compiles_across_builtin_targets():
    ontology = parse_ontology(_fixture_dir())

    outputs = {
        "neo4j": compile_neo4j(ontology),
        "json": compile_json(ontology),
        "jsonld": compile_jsonld(ontology),
        "agent": compile_agent_context(ontology, view_name="Language Curator"),
        "embeddings": compile_embeddings(ontology),
        "mermaid": compile_mermaid(ontology),
        "palantir": compile_palantir(ontology),
    }

    for target, out in outputs.items():
        assert out.strip(), f"{target} compiler emitted empty output"

    assert "<domain_ontology>" in outputs["agent"]
    assert "Language Curator" in outputs["agent"]
