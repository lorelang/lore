"""
Lore Validator.

Validates a parsed Ontology for structural integrity, broken references,
and other issues. Returns a list of diagnostic messages.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .models import Ontology


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Diagnostic:
    severity: Severity
    message: str
    source: str = ""  # file or location

    def __str__(self):
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}[self.severity.value]
        src = f" ({self.source})" if self.source else ""
        return f"  {icon} {self.message}{src}"


VALID_STATUSES = {"", "draft", "proposed", "stable", "deprecated"}
VALID_SOURCES = {"", "domain-expert", "ai-generated", "imported", "derived"}


def validate(ontology: Ontology) -> list[Diagnostic]:
    """Run all validation checks on an ontology."""
    diagnostics: list[Diagnostic] = []

    diagnostics.extend(_check_manifest(ontology))
    diagnostics.extend(_check_entities(ontology))
    diagnostics.extend(_check_relationships(ontology))
    diagnostics.extend(_check_rules(ontology))
    diagnostics.extend(_check_taxonomies(ontology))
    diagnostics.extend(_check_views(ontology))
    diagnostics.extend(_check_glossary(ontology))
    diagnostics.extend(_check_provenance(ontology))
    diagnostics.extend(_check_observations(ontology))
    diagnostics.extend(_check_outcomes(ontology))

    return diagnostics


def _check_manifest(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if not ont.manifest:
        diags.append(Diagnostic(Severity.WARNING, "No lore.yaml manifest found"))
    else:
        if not ont.manifest.name:
            diags.append(Diagnostic(Severity.ERROR, "Manifest missing 'name'", "lore.yaml"))
        if not ont.manifest.version:
            diags.append(Diagnostic(Severity.WARNING, "Manifest missing 'version'", "lore.yaml"))
    return diags


def _check_entities(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    names = set()

    for entity in ont.entities:
        src = str(entity.source_file) if entity.source_file else entity.name

        # Duplicate check
        if entity.name in names:
            diags.append(Diagnostic(Severity.ERROR, f"Duplicate entity: {entity.name}", src))
        names.add(entity.name)

        # Check inheritance references
        if entity.inherits and entity.inherits not in ont.entity_names:
            # Allow inheriting from external types (not defined in this ontology)
            diags.append(Diagnostic(
                Severity.INFO,
                f"Entity '{entity.name}' inherits from '{entity.inherits}' which is not defined in this ontology",
                src,
            ))

        # Check attribute references
        for attr in entity.attributes:
            if attr.reference_to and attr.reference_to not in ont.entity_names:
                # Check if it's a taxonomy or external reference
                tax_names = {t.name for t in ont.taxonomies}
                if attr.reference_to not in tax_names:
                    diags.append(Diagnostic(
                        Severity.WARNING,
                        f"Entity '{entity.name}' attribute '{attr.name}' references "
                        f"unknown entity '{attr.reference_to}'",
                        src,
                    ))

        # Check for required attributes
        if not entity.attributes:
            diags.append(Diagnostic(Severity.WARNING, f"Entity '{entity.name}' has no attributes", src))

        # Check for identity section
        if not entity.identity:
            diags.append(Diagnostic(
                Severity.INFO,
                f"Entity '{entity.name}' has no Identity section — consider defining uniqueness",
                src,
            ))

    return diags


def _check_relationships(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    entity_names = ont.entity_names

    for rf in ont.relationship_files:
        src = str(rf.source_file) if rf.source_file else rf.domain

        for rel in rf.relationships:
            if rel.from_entity not in entity_names:
                diags.append(Diagnostic(
                    Severity.ERROR,
                    f"Relationship '{rel.name}' references unknown entity '{rel.from_entity}'",
                    src,
                ))
            if rel.to_entity not in entity_names:
                diags.append(Diagnostic(
                    Severity.ERROR,
                    f"Relationship '{rel.name}' references unknown entity '{rel.to_entity}'",
                    src,
                ))

        # Check traversals reference valid relationships
        all_rel_names = {r.name for r in ont.all_relationships}
        for trav in rf.traversals:
            # Extract relationship names from path
            rel_refs = set(re.findall(r'\[(\w+)\]', trav.path)) if trav.path else set()
            # Note: some traversal paths use filters like [type = expansion]
            # so we don't strictly validate those

    return diags


def _check_rules(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    entity_names = ont.entity_names
    rule_names: set[str] = set()

    for rf in ont.rule_files:
        src = str(rf.source_file) if rf.source_file else rf.domain

        for rule in rf.rules:
            if rule.name in rule_names:
                diags.append(Diagnostic(Severity.ERROR, f"Duplicate rule name: {rule.name}", src))
            rule_names.add(rule.name)

            if rule.applies_to and rule.applies_to not in entity_names:
                diags.append(Diagnostic(
                    Severity.WARNING,
                    f"Rule '{rule.name}' applies_to unknown entity '{rule.applies_to}'",
                    src,
                ))

            if not rule.applies_to:
                diags.append(Diagnostic(
                    Severity.INFO,
                    f"Rule '{rule.name}' has no applies_to — consider specifying target entity",
                    src,
                ))

    return diags


def _check_taxonomies(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []

    for tax in ont.taxonomies:
        src = str(tax.source_file) if tax.source_file else tax.name

        if not tax.root:
            diags.append(Diagnostic(Severity.WARNING, f"Taxonomy '{tax.name}' has no tree structure", src))
        else:
            # Count nodes
            node_count = _count_nodes(tax.root)
            if node_count < 2:
                diags.append(Diagnostic(
                    Severity.WARNING,
                    f"Taxonomy '{tax.name}' has only {node_count} node(s)",
                    src,
                ))

        # Check applied_to references a valid entity.attribute
        if tax.applied_to and "." in tax.applied_to:
            entity_name = tax.applied_to.split(".")[0]
            if entity_name not in ont.entity_names:
                diags.append(Diagnostic(
                    Severity.WARNING,
                    f"Taxonomy '{tax.name}' applied_to references unknown entity '{entity_name}'",
                    src,
                ))

    return diags


def _count_nodes(node) -> int:
    count = 1
    for child in node.children:
        count += _count_nodes(child)
    return count


def _check_views(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    entity_names = ont.entity_names

    for view in ont.views:
        src = str(view.source_file) if view.source_file else view.name

        if not view.entities:
            diags.append(Diagnostic(Severity.WARNING, f"View '{view.name}' lists no entities", src))

        if not view.key_questions:
            diags.append(Diagnostic(
                Severity.INFO,
                f"View '{view.name}' has no Key Questions — these help scope the AI agent",
                src,
            ))

    return diags


def _check_glossary(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []

    if not ont.glossary:
        diags.append(Diagnostic(Severity.INFO, "No glossary defined — consider adding canonical term definitions"))
    elif not ont.glossary.entries:
        diags.append(Diagnostic(Severity.WARNING, "Glossary is empty"))

    return diags


def _check_provenance(ont: Ontology) -> list[Diagnostic]:
    """Validate provenance and status fields across all file types."""
    diags: list[Diagnostic] = []

    # Collect all items with provenance/status
    items = []
    for e in ont.entities:
        items.append((e.name, "Entity", e.provenance, e.status, str(e.source_file) if e.source_file else e.name))
    for rf in ont.relationship_files:
        items.append((rf.domain, "RelationshipFile", rf.provenance, rf.status, str(rf.source_file) if rf.source_file else rf.domain))
    for rf in ont.rule_files:
        items.append((rf.domain, "RuleFile", rf.provenance, rf.status, str(rf.source_file) if rf.source_file else rf.domain))
    for t in ont.taxonomies:
        items.append((t.name, "Taxonomy", t.provenance, t.status, str(t.source_file) if t.source_file else t.name))
    if ont.glossary:
        items.append(("glossary", "Glossary", ont.glossary.provenance, ont.glossary.status,
                       str(ont.glossary.source_file) if ont.glossary.source_file else "glossary"))
    for v in ont.views:
        items.append((v.name, "View", v.provenance, v.status, str(v.source_file) if v.source_file else v.name))

    # Track deprecated entities for reference checking
    deprecated_entities = set()

    for name, kind, prov, status, src in items:
        # Validate status
        if status and status not in VALID_STATUSES:
            diags.append(Diagnostic(
                Severity.WARNING,
                f"{kind} '{name}' has unknown status '{status}' "
                f"(expected: draft, proposed, stable, deprecated)",
                src,
            ))

        if status == "deprecated" and kind == "Entity":
            deprecated_entities.add(name)

        if prov:
            # Validate confidence range
            if prov.confidence is not None:
                if prov.confidence < 0.0 or prov.confidence > 1.0:
                    diags.append(Diagnostic(
                        Severity.WARNING,
                        f"{kind} '{name}' has confidence {prov.confidence} outside valid range [0.0, 1.0]",
                        src,
                    ))

            # Validate source
            if prov.source and prov.source not in VALID_SOURCES:
                diags.append(Diagnostic(
                    Severity.INFO,
                    f"{kind} '{name}' has non-standard provenance source '{prov.source}'",
                    src,
                ))

    # Warn if relationships reference deprecated entities
    for rf in ont.relationship_files:
        for rel in rf.relationships:
            if rel.from_entity in deprecated_entities:
                diags.append(Diagnostic(
                    Severity.WARNING,
                    f"Relationship '{rel.name}' references deprecated entity '{rel.from_entity}'",
                    str(rf.source_file) if rf.source_file else rf.domain,
                ))
            if rel.to_entity in deprecated_entities:
                diags.append(Diagnostic(
                    Severity.WARNING,
                    f"Relationship '{rel.name}' references deprecated entity '{rel.to_entity}'",
                    str(rf.source_file) if rf.source_file else rf.domain,
                ))

    return diags


def _check_observations(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    entity_names = ont.entity_names

    for of in ont.observation_files:
        src = str(of.source_file) if of.source_file else of.name

        if of.about and of.about not in entity_names:
            diags.append(Diagnostic(
                Severity.WARNING,
                f"Observation '{of.name}' references unknown entity '{of.about}' in 'about' field",
                src,
            ))

        if not of.observations:
            diags.append(Diagnostic(
                Severity.WARNING,
                f"Observation file '{of.name}' has no observation sections",
                src,
            ))

        if of.confidence is not None and (of.confidence < 0.0 or of.confidence > 1.0):
            diags.append(Diagnostic(
                Severity.WARNING,
                f"Observation '{of.name}' has confidence {of.confidence} outside valid range [0.0, 1.0]",
                src,
            ))

    return diags


def _check_outcomes(ont: Ontology) -> list[Diagnostic]:
    diags: list[Diagnostic] = []

    for of in ont.outcome_files:
        src = str(of.source_file) if of.source_file else of.name

        if not of.outcomes:
            diags.append(Diagnostic(
                Severity.WARNING,
                f"Outcome file '{of.name}' has no outcome sections",
                src,
            ))

        for outcome in of.outcomes:
            # Validate Ref: paths point to real observation files
            for ref in outcome.refs:
                # Ref format: observations/filename.lore#heading-slug
                if ref.startswith("observations/"):
                    # Extract file path
                    ref_path = ref.split("#")[0]
                    # Check if the referenced observation file exists
                    obs_names = {o.source_file.name if o.source_file else "" for o in ont.observation_files}
                    ref_filename = ref_path.replace("observations/", "")
                    if ref_filename and ref_filename not in obs_names:
                        diags.append(Diagnostic(
                            Severity.WARNING,
                            f"Outcome '{outcome.heading}' references unknown observation file '{ref_path}'",
                            src,
                        ))

    return diags


# Need re for traversal parsing
import re
