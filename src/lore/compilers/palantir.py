"""
Palantir Foundry Ontology Compiler.

Generates a JSON document compatible with Palantir Foundry's OntologyFullMetadata
schema. This can be imported into Foundry via the Ontology Manager's
Advanced > Import workflow.

Mapping from Lore to Palantir:
  - Entity          -> Object Type
  - Attribute       -> Property
  - Relationship    -> Link Type
  - Rule            -> Action Type (advisory)
  - Taxonomy        -> (embedded as property enum annotations)
  - View            -> (not directly mapped — Palantir uses Workshop apps)

Note: Palantir warns that the export/import JSON schema may change over time.
This compiler targets the documented fullMetadata structure from their V2 API.
"""
from __future__ import annotations
import json
import uuid
from ..models import Ontology, Entity, Attribute, Relationship


# ── Palantir type mapping ──────────────────────────────────────────────

_TYPE_MAP = {
    "string": "string",
    "text": "string",
    "email": "string",
    "url": "string",
    "enum": "string",
    "int": "integer",
    "integer": "integer",
    "float": "double",
    "double": "double",
    "decimal": "double",
    "number": "double",
    "boolean": "boolean",
    "bool": "boolean",
    "date": "date",
    "datetime": "timestamp",
    "timestamp": "timestamp",
    "currency": "double",
    "percentage": "double",
    "reference": "string",          # references become string IDs
    "list<reference>": "string",    # simplified for Palantir
    "list<string>": "string",       # Palantir arrays are limited
}


def _palantir_type(lore_type: str) -> dict:
    """Map a Lore attribute type to a Palantir dataType object."""
    base = _TYPE_MAP.get(lore_type.lower(), "string")
    return {"type": base}


def _make_rid(kind: str) -> str:
    """Generate a placeholder Palantir Resource Identifier."""
    uid = str(uuid.uuid4())
    return f"ri.ontology.main.{kind}.{uid}"


def _api_name(name: str) -> str:
    """Convert entity/attribute name to camelCase API name."""
    if not name:
        return name
    # Handle PascalCase -> camelCase
    if name[0].isupper() and not name.isupper():
        return name[0].lower() + name[1:]
    # Handle snake_case -> camelCase
    parts = name.split("_")
    if len(parts) > 1:
        return parts[0].lower() + "".join(p.title() for p in parts[1:])
    return name.lower()


def _plural(name: str) -> str:
    """Naive pluralization for display names."""
    if name.endswith("s") or name.endswith("x") or name.endswith("z"):
        return name + "es"
    if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


# ── Property serializer ───────────────────────────────────────────────

def _serialize_property(attr: Attribute) -> dict:
    """Convert a Lore Attribute to a Palantir property definition."""
    prop = {
        "apiName": _api_name(attr.name),
        "displayName": attr.name.replace("_", " ").title(),
        "dataType": _palantir_type(attr.type),
        "rid": _make_rid("property"),
        "status": "ACTIVE",
        "visibility": "NORMAL",
    }
    if attr.description:
        prop["description"] = attr.description
    return prop


# ── Object type serializer ────────────────────────────────────────────

def _serialize_object_type(entity: Entity, relationships: list[Relationship]) -> dict:
    """Convert a Lore Entity to a Palantir Object Type with link types."""
    api_name = _api_name(entity.name)

    # Properties
    properties = {}
    primary_key = None
    for attr in entity.attributes:
        prop = _serialize_property(attr)
        properties[prop["apiName"]] = prop
        if "required" in attr.constraints or attr.name in ("id", "domain_id"):
            if primary_key is None:
                primary_key = prop["apiName"]

    # If no explicit primary key, synthesize one
    if primary_key is None:
        pk_name = f"{api_name}Id"
        properties[pk_name] = {
            "apiName": pk_name,
            "displayName": f"{entity.name} ID",
            "description": f"Auto-generated primary key for {entity.name}",
            "dataType": {"type": "string"},
            "rid": _make_rid("property"),
            "status": "ACTIVE",
            "visibility": "NORMAL",
        }
        primary_key = pk_name

    # Link types (outgoing relationships from this entity)
    link_types = {}
    for rel in relationships:
        if rel.from_entity == entity.name:
            link_api = _api_name(rel.name)
            link_types[link_api] = {
                "apiName": link_api,
                "displayName": rel.name.replace("_", " ").title(),
                "status": "ACTIVE",
                "objectTypeApiName": _api_name(rel.to_entity),
            }
            if rel.description:
                link_types[link_api]["description"] = rel.description

    # Object type
    object_type = {
        "objectType": {
            "apiName": api_name,
            "displayName": entity.name,
            "pluralDisplayName": _plural(entity.name),
            "status": _palantir_status(entity.status),
            "visibility": "NORMAL",
            "primaryKey": primary_key,
            "rid": _make_rid("object-type"),
            "properties": properties,
        },
        "linkTypes": link_types,
    }

    if entity.description:
        object_type["objectType"]["description"] = entity.description

    return object_type


def _palantir_status(lore_status: str) -> str:
    """Map Lore status to Palantir status."""
    return {
        "draft": "EXPERIMENTAL",
        "proposed": "EXPERIMENTAL",
        "stable": "ACTIVE",
        "deprecated": "DEPRECATED",
    }.get(lore_status, "ACTIVE")


# ── Action type serializer ────────────────────────────────────────────

def _serialize_action_types(ontology: Ontology) -> dict:
    """Convert Lore rules to advisory Palantir Action Types."""
    action_types = {}
    for rule in ontology.all_rules:
        api_name = _api_name(rule.name.replace("-", "_").replace(" ", "_"))
        action = {
            "apiName": api_name,
            "displayName": rule.name.replace("-", " ").replace("_", " ").title(),
            "rid": _make_rid("action-type"),
            "parameters": {},
        }
        desc_parts = []
        if rule.trigger:
            desc_parts.append(f"Trigger: {rule.trigger}")
        if rule.condition:
            desc_parts.append(f"Condition: {rule.condition}")
        if rule.action:
            desc_parts.append(f"Action: {rule.action}")
        if rule.prose:
            desc_parts.append(rule.prose)
        if desc_parts:
            action["description"] = " | ".join(desc_parts)

        if rule.applies_to:
            action["parameters"]["targetEntity"] = {
                "displayName": f"Target {rule.applies_to}",
                "dataType": {"type": "string"},
            }
        action_types[api_name] = action
    return action_types


# ── Main compiler ─────────────────────────────────────────────────────

def compile_palantir(ontology: Ontology) -> str:
    """
    Compile ontology to Palantir Foundry OntologyFullMetadata JSON.

    This produces a JSON document that mirrors the structure returned by
    Palantir's GET /api/v2/ontologies/{ontology}/fullMetadata endpoint.
    It can be imported into Foundry via Ontology Manager > Advanced > Import.
    """
    name = ontology.manifest.name if ontology.manifest else "lore-ontology"
    desc = ontology.manifest.description if ontology.manifest else ""

    all_rels = ontology.all_relationships

    # Object types
    object_types = {}
    for entity in ontology.entities:
        api = _api_name(entity.name)
        object_types[api] = _serialize_object_type(entity, all_rels)

    # Action types from rules
    action_types = _serialize_action_types(ontology)

    metadata = {
        "ontology": {
            "apiName": _api_name(name.replace("-", "_").replace(" ", "_")),
            "displayName": name,
            "description": desc,
            "rid": _make_rid("ontology"),
        },
        "objectTypes": object_types,
        "actionTypes": action_types,
        "interfaceTypes": {},
        "sharedPropertyTypes": {},
        "queryTypes": {},
    }

    return json.dumps(metadata, indent=2, default=str)
