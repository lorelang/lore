"""
Lore — Human-readable ontology format for the AI age.

Define domain knowledge in prose. Compile to anything.
"""
__version__ = "0.2.1"

from .parser import parse_ontology
from .validator import validate
from .models import Ontology, Provenance, PluginConfig, KnowledgeClaim
from .sdk import LoreOntology
