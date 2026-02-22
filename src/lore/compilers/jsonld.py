"""
JSON-LD Compiler.

Exports Lore as interoperable JSON-LD so ontology data can flow into
semantic-web compatible tools and graph pipelines.
"""
from __future__ import annotations
import json
from ..models import Ontology, Attribute


_CONTEXT = {
    "lore": "https://lorelang.org/schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "label": "rdfs:label",
    "comment": "rdfs:comment",
    "domain": {"@id": "rdfs:domain", "@type": "@id"},
    "range": {"@id": "rdfs:range", "@type": "@id"},
    "subClassOf": {"@id": "rdfs:subClassOf", "@type": "@id"},
    "appliesTo": {"@id": "lore:appliesTo", "@type": "@id"},
    "status": "lore:status",
    "constraints": "lore:constraints",
    "enumValues": "lore:enumValues",
    "identity": "lore:identity",
    "lifecycle": "lore:lifecycle",
    "notes": "lore:notes",
    "cardinality": "lore:cardinality",
    "path": "lore:path",
    "severity": "lore:severity",
    "trigger": "lore:trigger",
    "condition": "lore:condition",
    "action": "lore:action",
    "sourceFile": "lore:sourceFile",
}


def compile_jsonld(ontology: Ontology) -> str:
    """Compile ontology to JSON-LD."""
    graph: list[dict] = []
    name = ontology.manifest.name if ontology.manifest else "ontology"
    desc = ontology.manifest.description if ontology.manifest else ""

    graph.append({
        "@id": f"lore:Ontology/{name}",
        "@type": "owl:Ontology",
        "label": name,
        "comment": desc,
    })

    for entity in ontology.entities:
        entity_id = _entity_id(entity.name)
        node = {
            "@id": entity_id,
            "@type": "owl:Class",
            "label": entity.name,
            "comment": entity.description,
        }
        if entity.inherits:
            node["subClassOf"] = _entity_id(entity.inherits)
        if entity.identity:
            node["identity"] = entity.identity
        if entity.lifecycle:
            node["lifecycle"] = entity.lifecycle
        if entity.notes:
            node["notes"] = entity.notes
        if entity.status:
            node["status"] = entity.status
        if entity.source_file:
            node["sourceFile"] = str(entity.source_file)
        graph.append(node)

        for attr in entity.attributes:
            attr_node = {
                "@id": _attribute_id(entity.name, attr.name),
                "@type": "rdf:Property",
                "label": f"{entity.name}.{attr.name}",
                "comment": attr.description,
                "domain": entity_id,
                "range": _range_for_attribute(attr),
                "constraints": attr.constraints,
            }
            if attr.enum_values:
                attr_node["enumValues"] = attr.enum_values
            if attr.annotations:
                attr_node["lore:annotations"] = attr.annotations
            graph.append(attr_node)

    for rel in ontology.all_relationships:
        graph.append({
            "@id": f"lore:Relationship/{rel.name}",
            "@type": "owl:ObjectProperty",
            "label": rel.name,
            "comment": rel.description,
            "domain": _entity_id(rel.from_entity),
            "range": _entity_id(rel.to_entity),
            "cardinality": rel.cardinality,
        })

    for trav in ontology.all_traversals:
        graph.append({
            "@id": f"lore:Traversal/{trav.name}",
            "@type": "lore:Traversal",
            "label": trav.name,
            "path": trav.path,
            "comment": trav.description,
        })

    for rule in ontology.all_rules:
        rule_node = {
            "@id": f"lore:Rule/{rule.name}",
            "@type": "lore:Rule",
            "label": rule.name,
            "severity": rule.severity,
            "trigger": rule.trigger,
            "condition": rule.condition,
            "action": rule.action,
            "comment": rule.prose,
        }
        if rule.applies_to:
            rule_node["appliesTo"] = _entity_id(rule.applies_to)
        graph.append(rule_node)

    payload = {
        "@context": _CONTEXT,
        "@graph": graph,
    }
    return json.dumps(payload, indent=2, default=str)


def _entity_id(name: str) -> str:
    return f"lore:Entity/{name}"


def _attribute_id(entity_name: str, attr_name: str) -> str:
    return f"lore:Property/{entity_name}.{attr_name}"


def _range_for_attribute(attr: Attribute) -> str:
    if attr.reference_to:
        return _entity_id(attr.reference_to)

    type_map = {
        "string": "xsd:string",
        "text": "xsd:string",
        "int": "xsd:integer",
        "integer": "xsd:integer",
        "float": "xsd:double",
        "double": "xsd:double",
        "boolean": "xsd:boolean",
        "bool": "xsd:boolean",
        "date": "xsd:date",
        "datetime": "xsd:dateTime",
        "enum": "xsd:string",
        "reference": "xsd:string",
        "list<reference>": "xsd:string",
    }
    return type_map.get(attr.type, "xsd:string")
