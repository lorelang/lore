"""Shared fixtures for Lore tests."""
import sys
import os
import pytest
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lore.parser import parse_ontology
from lore.models import Ontology


EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "b2b-saas-gtm"


@pytest.fixture
def example_ontology() -> Ontology:
    """Parse the full B2B SaaS GTM example."""
    return parse_ontology(EXAMPLE_DIR)


@pytest.fixture
def tmp_ontology(tmp_path):
    """Create a minimal ontology directory for testing."""
    def _make(manifest=None, entities=None, relationships=None,
              rules=None, taxonomies=None, glossary=None, views=None,
              observations=None, outcomes=None, decisions=None):
        if manifest:
            (tmp_path / "lore.yaml").write_text(manifest)
        if entities:
            (tmp_path / "entities").mkdir(exist_ok=True)
            for name, content in entities.items():
                (tmp_path / "entities" / name).write_text(content)
        if relationships:
            (tmp_path / "relationships").mkdir(exist_ok=True)
            for name, content in relationships.items():
                (tmp_path / "relationships" / name).write_text(content)
        if rules:
            (tmp_path / "rules").mkdir(exist_ok=True)
            for name, content in rules.items():
                (tmp_path / "rules" / name).write_text(content)
        if taxonomies:
            (tmp_path / "taxonomies").mkdir(exist_ok=True)
            for name, content in taxonomies.items():
                (tmp_path / "taxonomies" / name).write_text(content)
        if glossary:
            (tmp_path / "glossary").mkdir(exist_ok=True)
            for name, content in glossary.items():
                (tmp_path / "glossary" / name).write_text(content)
        if views:
            (tmp_path / "views").mkdir(exist_ok=True)
            for name, content in views.items():
                (tmp_path / "views" / name).write_text(content)
        if observations:
            (tmp_path / "observations").mkdir(exist_ok=True)
            for name, content in observations.items():
                (tmp_path / "observations" / name).write_text(content)
        if outcomes:
            (tmp_path / "outcomes").mkdir(exist_ok=True)
            for name, content in outcomes.items():
                (tmp_path / "outcomes" / name).write_text(content)
        if decisions:
            (tmp_path / "decisions").mkdir(exist_ok=True)
            for name, content in decisions.items():
                (tmp_path / "decisions" / name).write_text(content)
        return parse_ontology(tmp_path)
    return _make
