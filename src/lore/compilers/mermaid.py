"""
Mermaid Diagram Compiler.

Generates Mermaid.js diagram code for visualizing the ontology
as an entity-relationship diagram.
"""
from __future__ import annotations
from ..models import Ontology


def compile_mermaid(ontology: Ontology) -> str:
    """Compile ontology to Mermaid ER diagram."""
    lines: list[str] = []
    name = ontology.manifest.name if ontology.manifest else "Ontology"

    lines.append(f"---")
    lines.append(f"title: {name}")
    lines.append(f"---")
    lines.append("erDiagram")

    # Entities with key attributes
    for entity in ontology.entities:
        lines.append(f"    {entity.name} {{")
        for attr in entity.attributes[:8]:  # Limit to keep diagram readable
            mtype = _mermaid_type(attr.type)
            pk = " PK" if "unique" in attr.constraints else ""
            fk = " FK" if attr.reference_to else ""
            lines.append(f"        {mtype} {attr.name}{pk}{fk}")
        lines.append(f"    }}")

    lines.append("")

    # Relationships
    for rel in ontology.all_relationships:
        card = _mermaid_cardinality(rel.cardinality)
        label = rel.name.replace("_", " ").lower()
        lines.append(
            f"    {rel.from_entity} {card} {rel.to_entity} : \"{label}\""
        )

    return "\n".join(lines)


def _mermaid_type(type_str: str) -> str:
    """Map Lore types to Mermaid-friendly types."""
    mapping = {
        "string": "string",
        "int": "int",
        "float": "float",
        "boolean": "bool",
        "date": "date",
        "datetime": "datetime",
        "text": "text",
        "reference": "ref",
    }
    # Handle enum types
    if type_str.startswith("enum"):
        return "enum"
    if type_str.startswith("list"):
        return "list"
    return mapping.get(type_str, "string")


def _mermaid_cardinality(card: str) -> str:
    """Map cardinality strings to Mermaid notation."""
    mapping = {
        "one-to-one": "||--||",
        "one-to-many": "||--o{",
        "many-to-one": "}o--||",
        "many-to-many": "}o--o{",
    }
    # Handle optional markers
    clean = card.split("[")[0].strip()
    return mapping.get(clean, "||--o{")
