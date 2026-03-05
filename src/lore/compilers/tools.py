"""
Tool Schema Compiler.

Generates function-calling schemas from ontology entities and
relationships. Each entity becomes get_<entity> and list_<entities>
tools. Each relationship becomes a query tool.

Output formats: openai, anthropic (same shape), json_schema (plain).
"""
from __future__ import annotations

import json
from ..models import Ontology, Attribute


# Lore type -> JSON Schema type mapping
_TYPE_MAP = {
    "string": "string",
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "number": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string",
    "url": "string",
    "email": "string",
}


def _json_schema_type(attr: Attribute) -> dict:
    """Convert a Lore attribute to JSON Schema property definition."""
    if attr.type == "enum" and attr.enum_values:
        return {"type": "string", "enum": attr.enum_values}
    if attr.reference_to:
        return {
            "type": "string",
            "description": f"Reference to {attr.reference_to} entity",
        }
    if attr.type.startswith("list<"):
        inner = attr.type[5:-1] if attr.type.endswith(">") else "string"
        inner_type = _TYPE_MAP.get(inner.lstrip("-> ").strip(), "string")
        return {"type": "array", "items": {"type": inner_type}}

    base_type = _TYPE_MAP.get(attr.type, "string")
    return {"type": base_type}


def generate_tool_schemas(ontology: Ontology, fmt: str = "openai") -> list[dict]:
    """
    Generate function-calling tool schemas from the ontology.

    Args:
        ontology: Parsed ontology
        fmt: Output format — "openai", "anthropic", or "json_schema"

    Returns:
        List of tool schema dicts
    """
    tools: list[dict] = []

    # Entity tools
    for entity in ontology.entities:
        safe_name = entity.name.lower().replace(" ", "_").replace("-", "_")

        # get_<entity> tool
        get_schema = _build_get_tool(entity, safe_name, fmt)
        tools.append(get_schema)

        # list_<entities> tool
        list_schema = _build_list_tool(entity, safe_name, fmt)
        tools.append(list_schema)

    # Relationship query tools
    for rel in ontology.all_relationships:
        safe_name = rel.name.lower().replace(" ", "_").replace("-", "_")
        rel_schema = _build_relationship_tool(rel, safe_name, fmt)
        tools.append(rel_schema)

    return tools


def _build_get_tool(entity, safe_name: str, fmt: str) -> dict:
    """Build a get_<entity> tool schema."""
    properties = {}
    required = []

    # Identity parameter — first required+unique attribute, or "name"
    id_attr = None
    for attr in entity.attributes:
        if "required" in attr.constraints and "unique" in attr.constraints:
            id_attr = attr
            break
    if not id_attr:
        for attr in entity.attributes:
            if "required" in attr.constraints:
                id_attr = attr
                break
    if not id_attr and entity.attributes:
        id_attr = entity.attributes[0]

    if id_attr:
        properties[id_attr.name] = {
            **_json_schema_type(id_attr),
            "description": id_attr.description or f"The {id_attr.name} to look up",
        }
        required.append(id_attr.name)

    parameters = {
        "type": "object",
        "properties": properties,
        "required": required,
    }

    desc = entity.description or f"Get details of a {entity.name}"
    first_sentence = desc.split(".")[0] + "." if "." in desc else desc

    return _wrap_tool(
        name=f"get_{safe_name}",
        description=f"Get a {entity.name} by identifier. {first_sentence}",
        parameters=parameters,
        fmt=fmt,
    )


def _build_list_tool(entity, safe_name: str, fmt: str) -> dict:
    """Build a list_<entities> tool schema."""
    properties: dict = {}
    # Add filterable enum/status attributes as optional params
    for attr in entity.attributes:
        if attr.type == "enum" and attr.enum_values:
            properties[attr.name] = {
                "type": "string",
                "enum": attr.enum_values,
                "description": attr.description or f"Filter by {attr.name}",
            }
        elif attr.type == "string" and "required" not in attr.constraints:
            properties[attr.name] = {
                "type": "string",
                "description": attr.description or f"Filter by {attr.name}",
            }

    # Always add limit
    properties["limit"] = {
        "type": "integer",
        "description": "Maximum number of results to return",
        "default": 10,
    }

    parameters = {
        "type": "object",
        "properties": properties,
        "required": [],
    }

    return _wrap_tool(
        name=f"list_{safe_name}s",
        description=f"List {entity.name} entities with optional filters.",
        parameters=parameters,
        fmt=fmt,
    )


def _build_relationship_tool(rel, safe_name: str, fmt: str) -> dict:
    """Build a relationship query tool."""
    properties = {
        "from_entity": {
            "type": "string",
            "description": f"The {rel.from_entity} to query from",
        },
    }
    required = ["from_entity"]

    # Add relationship properties as optional filters
    for prop in rel.properties:
        prop_type = _TYPE_MAP.get(prop.type, "string")
        properties[prop.name] = {
            "type": prop_type,
            "description": prop.description or f"Filter by {prop.name}",
        }

    parameters = {
        "type": "object",
        "properties": properties,
        "required": required,
    }

    desc = rel.description or f"Query {rel.name} relationships"
    first_sentence = desc.split(".")[0] + "." if "." in desc else desc

    return _wrap_tool(
        name=f"query_{safe_name}",
        description=(
            f"Find {rel.to_entity} entities related to a {rel.from_entity} "
            f"via {rel.name}. {first_sentence}"
        ),
        parameters=parameters,
        fmt=fmt,
    )


def _wrap_tool(name: str, description: str, parameters: dict, fmt: str) -> dict:
    """Wrap tool definition in the specified format."""
    if fmt in ("openai", "anthropic"):
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
    else:  # json_schema
        return {
            "name": name,
            "description": description,
            "parameters": parameters,
        }


def compile_tools(ontology: Ontology, fmt: str = "openai") -> str:
    """Compile ontology to tool schema JSON string."""
    schemas = generate_tool_schemas(ontology, fmt=fmt)
    return json.dumps(schemas, indent=2)
