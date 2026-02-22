"""
JSON Compiler.

Exports the ontology as a structured JSON document suitable
for API consumption, interop with other tools, or programmatic access.
"""
from __future__ import annotations
import json
from ..models import Ontology, TaxonomyNode


def _serialize_provenance(prov, status=""):
    """Serialize provenance and status to a dict, omitting empty fields."""
    result = {}
    if prov:
        p = {}
        if prov.author:
            p["author"] = prov.author
        if prov.source:
            p["source"] = prov.source
        if prov.confidence is not None:
            p["confidence"] = prov.confidence
        if prov.created:
            p["created"] = prov.created
        if prov.deprecated:
            p["deprecated"] = prov.deprecated
        if p:
            result["provenance"] = p
    if status:
        result["status"] = status
    return result


def compile_json(ontology: Ontology) -> str:
    """Compile ontology to JSON."""
    data = {
        "metadata": _serialize_manifest(ontology),
        "entities": [_serialize_entity(e) for e in ontology.entities],
        "relationships": [_serialize_rel(r) for r in ontology.all_relationships],
        "traversals": [_serialize_traversal(t) for t in ontology.all_traversals],
        "rules": [_serialize_rule(r) for r in ontology.all_rules],
        "taxonomies": [_serialize_taxonomy(t) for t in ontology.taxonomies],
        "glossary": [_serialize_glossary_entry(g) for g in ontology.all_glossary_entries],
        "views": [_serialize_view(v) for v in ontology.views],
        "observations": [_serialize_observation_file(of) for of in ontology.observation_files],
        "outcomes": [_serialize_outcome_file(of) for of in ontology.outcome_files],
        "extensions": ontology.extensions,
    }
    return json.dumps(data, indent=2, default=str)


def _serialize_manifest(ont: Ontology) -> dict:
    if not ont.manifest:
        return {}
    m = ont.manifest
    data = {
        "name": m.name,
        "version": m.version,
        "description": m.description,
        "domain": m.domain,
        "maintainers": m.maintainers,
    }
    if m.plugins:
        data["plugins"] = {
            "compilers": m.plugins.compilers,
            "curators": m.plugins.curators,
            "directories": m.plugins.directories,
            "directory_parsers": m.plugins.directory_parsers,
        }
    return data


def _serialize_entity(entity) -> dict:
    result = {
        "name": entity.name,
        "description": entity.description,
        "inherits": entity.inherits,
        "attributes": [
            {
                "name": a.name,
                "type": a.type,
                "constraints": a.constraints,
                "enum_values": a.enum_values,
                "description": a.description,
                "annotations": a.annotations,
                "reference_to": a.reference_to,
            }
            for a in entity.attributes
        ],
        "identity": entity.identity,
        "lifecycle": entity.lifecycle,
        "notes": entity.notes,
    }
    result.update(_serialize_provenance(entity.provenance, entity.status))
    return result


def _serialize_rel(rel) -> dict:
    return {
        "name": rel.name,
        "from": rel.from_entity,
        "to": rel.to_entity,
        "cardinality": rel.cardinality,
        "description": rel.description,
        "properties": [
            {"name": p.name, "type": p.type, "description": p.description}
            for p in rel.properties
        ],
    }


def _serialize_traversal(trav) -> dict:
    return {
        "name": trav.name,
        "path": trav.path,
        "description": trav.description,
    }


def _serialize_rule(rule) -> dict:
    return {
        "name": rule.name,
        "applies_to": rule.applies_to,
        "severity": rule.severity,
        "trigger": rule.trigger,
        "condition": rule.condition,
        "action": rule.action,
        "prose": rule.prose,
        "outputs": rule.outputs,
    }


def _serialize_taxonomy(tax) -> dict:
    result = {
        "name": tax.name,
        "description": tax.description,
        "applied_to": tax.applied_to,
        "tree": _serialize_tax_node(tax.root) if tax.root else None,
        "inheritance_rules": tax.inheritance_rules,
    }
    result.update(_serialize_provenance(tax.provenance, tax.status))
    return result


def _serialize_tax_node(node: TaxonomyNode) -> dict:
    return {
        "name": node.name,
        "tags": node.tags,
        "description": node.description,
        "children": [_serialize_tax_node(c) for c in node.children],
    }


def _serialize_glossary_entry(entry) -> dict:
    return {
        "term": entry.term,
        "definition": entry.definition,
    }


def _serialize_view(view) -> dict:
    result = {
        "name": view.name,
        "description": view.description,
        "audience": view.audience,
        "entities": view.entities,
        "relationships": view.relationships,
        "rules": view.rules,
        "key_questions": view.key_questions,
        "not_in_scope": view.not_in_scope,
    }
    result.update(_serialize_provenance(view.provenance, view.status))
    return result


def _serialize_observation_file(of) -> dict:
    result = {
        "name": of.name,
        "about": of.about,
        "observed_by": of.observed_by,
        "date": of.date,
        "observations": [
            {
                "heading": obs.heading,
                "prose": obs.prose,
                "claims": [{"kind": c.kind, "text": c.text} for c in obs.claims],
            }
            for obs in of.observations
        ],
    }
    if of.confidence is not None:
        result["confidence"] = of.confidence
    if of.status:
        result["status"] = of.status
    result.update(_serialize_provenance(of.provenance))
    return result


def _serialize_outcome_file(of) -> dict:
    result = {
        "name": of.name,
        "reviewed_by": of.reviewed_by,
        "date": of.date,
        "outcomes": [
            {
                "heading": outcome.heading,
                "prose": outcome.prose,
                "refs": outcome.refs,
                "takeaways": outcome.takeaways,
            }
            for outcome in of.outcomes
        ],
    }
    result.update(_serialize_provenance(of.provenance, of.status))
    return result
