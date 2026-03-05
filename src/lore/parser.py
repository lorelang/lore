"""
Lore Parser.

Parses .lore files and lore.yaml manifests into the Ontology data model.
The parser handles YAML frontmatter, section-based content, and the
various sub-formats (attributes, relationships, taxonomies, etc.)
"""
from __future__ import annotations
import importlib
import re
import yaml
from pathlib import Path
from .models import (
    Ontology, OntologyManifest, EvolutionConfig, PluginConfig,
    Entity, Attribute,
    Relationship, RelationshipProperty, RelationshipFile, Traversal,
    Rule, RuleFile, Taxonomy, TaxonomyNode, Glossary, GlossaryEntry,
    View, Provenance, Observation, ObservationFile, Outcome, OutcomeFile,
    KnowledgeClaim, Decision, DecisionFile,
)


def _lore_files(directory: Path) -> list[Path]:
    """List .lore files in a directory, excluding INDEX.lore."""
    return sorted(f for f in directory.glob("*.lore") if f.name != "INDEX.lore")


def parse_ontology(root_dir: str | Path) -> Ontology:
    """Parse an entire ontology directory into an Ontology object."""
    root = Path(root_dir)
    ontology = Ontology()

    # Parse manifest
    manifest_path = root / "lore.yaml"
    if manifest_path.exists():
        ontology.manifest = _parse_manifest(manifest_path)

    # Parse entities
    entities_dir = root / "entities"
    if entities_dir.exists():
        for f in _lore_files(entities_dir):
            ontology.entities.append(_parse_entity(f))

    # Parse relationships
    rels_dir = root / "relationships"
    if rels_dir.exists():
        for f in _lore_files(rels_dir):
            ontology.relationship_files.append(_parse_relationship_file(f))

    # Parse rules
    rules_dir = root / "rules"
    if rules_dir.exists():
        for f in _lore_files(rules_dir):
            ontology.rule_files.append(_parse_rule_file(f))

    # Parse taxonomies
    tax_dir = root / "taxonomies"
    if tax_dir.exists():
        for f in _lore_files(tax_dir):
            ontology.taxonomies.append(_parse_taxonomy(f))

    # Parse glossary
    glossary_dir = root / "glossary"
    if glossary_dir.exists():
        for f in _lore_files(glossary_dir):
            parsed = _parse_glossary(f)
            if ontology.glossary is None:
                ontology.glossary = parsed
            else:
                _merge_glossary(ontology.glossary, parsed)

    # Parse views
    views_dir = root / "views"
    if views_dir.exists():
        for f in _lore_files(views_dir):
            ontology.views.append(_parse_view(f))

    # Parse observations
    obs_dir = root / "observations"
    if obs_dir.exists():
        for f in _lore_files(obs_dir):
            ontology.observation_files.append(_parse_observation_file(f))

    # Parse outcomes
    outcomes_dir = root / "outcomes"
    if outcomes_dir.exists():
        for f in _lore_files(outcomes_dir):
            ontology.outcome_files.append(_parse_outcome_file(f))

    # Parse decisions
    decisions_dir = root / "decisions"
    if decisions_dir.exists():
        for f in _lore_files(decisions_dir):
            ontology.decision_files.append(_parse_decision_file(f))

    # Parse plugin directories (generic files or plugin parser outputs)
    if ontology.manifest and ontology.manifest.plugins:
        _parse_extension_directories(ontology, root)

    return ontology


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body content."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return fm, body
    return {}, text.strip()


def _load_plugin_callable(entrypoint: str):
    """
    Load a plugin callable from a module:function entrypoint string.

    Returns None if the entrypoint cannot be loaded.
    """
    if not entrypoint or ":" not in entrypoint:
        return None
    module_name, fn_name = entrypoint.split(":", 1)
    module_name = module_name.strip()
    fn_name = fn_name.strip()
    if not module_name or not fn_name:
        return None
    try:
        module = importlib.import_module(module_name)
        fn = getattr(module, fn_name)
    except Exception:
        return None
    return fn if callable(fn) else None


def _parse_extension_directories(ontology: Ontology, root: Path):
    """Parse custom directories configured in manifest plugins."""
    plugins = ontology.manifest.plugins if ontology.manifest else None
    if not plugins:
        return
    if not plugins.directories:
        return

    for dirname in plugins.directories:
        dir_path = root / dirname
        if not dir_path.exists():
            continue

        parser_fn = None
        if plugins.directory_parsers:
            parser_fn = _load_plugin_callable(plugins.directory_parsers.get(dirname, ""))

        parsed_items = []
        for file_path in _lore_files(dir_path):
            if parser_fn:
                parsed = parser_fn(file_path)
            else:
                parsed = _parse_generic_lore(file_path)
            if parsed is not None:
                parsed_items.append(parsed)
        if parsed_items:
            ontology.extensions[dirname] = parsed_items


def _parse_generic_lore(path: Path) -> dict:
    """Parse custom .lore file into frontmatter + sections."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    return {
        "source_file": path,
        "frontmatter": fm,
        "sections": _split_sections(body),
        "body": body,
    }


def _split_sections(body: str) -> dict[str, str]:
    """Split body into {section_name: content} dict by ## headers."""
    sections: dict[str, str] = {}
    current_section = "__preamble__"
    lines: list[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if lines:
                sections[current_section] = "\n".join(lines).strip()
            current_section = line[3:].strip()
            lines = []
        else:
            lines.append(line)

    if lines:
        sections[current_section] = "\n".join(lines).strip()

    return sections


def _parse_provenance(fm: dict) -> tuple[Provenance | None, str]:
    """Extract provenance and status from frontmatter dict."""
    prov_data = fm.get("provenance")
    status = fm.get("status", "")
    if not prov_data:
        return None, status
    if not isinstance(prov_data, dict):
        return None, status
    confidence = prov_data.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = None
    return Provenance(
        author=str(prov_data.get("author", "")),
        source=str(prov_data.get("source", "")),
        confidence=confidence,
        created=str(prov_data.get("created", "")),
        deprecated=str(prov_data.get("deprecated", "")),
    ), status


def _parse_manifest(path: Path) -> OntologyManifest:
    data = yaml.safe_load(path.read_text())
    evolution = None
    evo_data = data.get("evolution")
    if isinstance(evo_data, dict):
        evolution = EvolutionConfig(
            proposals=str(evo_data.get("proposals", "open")),
            staleness=str(evo_data.get("staleness", "")),
        )
    plugins = None
    plugins_data = data.get("plugins")
    if isinstance(plugins_data, dict):
        compilers = {}
        curators = {}
        directories = []
        directory_parsers = {}
        comp_data = plugins_data.get("compilers")
        if isinstance(comp_data, dict):
            compilers = {str(k): str(v) for k, v in comp_data.items()}
        cur_data = plugins_data.get("curators")
        if isinstance(cur_data, dict):
            curators = {str(k): str(v) for k, v in cur_data.items()}
        dir_data = plugins_data.get("directories")
        if isinstance(dir_data, list):
            directories = [str(d) for d in dir_data]
        elif isinstance(dir_data, dict):
            directory_parsers = {str(k): str(v) for k, v in dir_data.items()}
            directories = list(directory_parsers.keys())
        plugins = PluginConfig(
            compilers=compilers,
            curators=curators,
            directories=directories,
            directory_parsers=directory_parsers,
        )
    return OntologyManifest(
        name=data.get("name", ""),
        version=data.get("version", ""),
        description=data.get("description", ""),
        domain=data.get("domain", ""),
        maintainers=data.get("maintainers", []),
        evolution=evolution,
        plugins=plugins,
    )


def _parse_attributes(text: str) -> list[Attribute]:
    """Parse attribute definitions from an Attributes section."""
    attrs: list[Attribute] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("|"):
            i += 1
            continue

        header = re.match(r"^(\w+):\s*(.+?)\s*$", line)
        if not header:
            i += 1
            continue

        attr_name = header.group(1)
        tail = header.group(2).strip()
        attr_type = tail
        constraints: list[str] = []
        enum_values: list[str] = []

        enum_match = re.match(r"^enum\s*\[(.+?)\](?:\s*\[(.+?)\])?$", tail)
        if enum_match:
            attr_type = "enum"
            enum_values = [
                v.strip() for v in enum_match.group(1).split(",") if v.strip()
            ]
            constraints_str = enum_match.group(2) or ""
            constraints = [
                c.strip() for c in constraints_str.split(",") if c.strip()
            ]
        else:
            typed = re.match(r"^(.+?)(?:\s*\[(.+?)\])?$", tail)
            if typed:
                attr_type = typed.group(1).strip()
                constraints_str = typed.group(2) or ""
                constraints = [
                    c.strip() for c in constraints_str.split(",") if c.strip()
                ]

        # Check for reference type
        reference_to = None
        if attr_type.startswith("->"):
            reference_to = attr_type[2:].strip()
            attr_type = "reference"
        elif attr_type.startswith("list<->"):
            inner = attr_type[7:].rstrip(">").strip()
            reference_to = inner
            attr_type = "list<reference>"

        # Collect description lines (starting with |)
        desc_lines: list[str] = []
        annotations: dict[str, str] = {}
        i += 1
        while i < len(lines):
            dline = lines[i].strip()
            if dline.startswith("| ") or dline == "|":
                content = dline[2:] if dline.startswith("| ") else ""
                ann_match = re.match(r'^@(\w+):\s*(.+)$', content)
                if ann_match:
                    annotations[ann_match.group(1)] = ann_match.group(2)
                else:
                    desc_lines.append(content)
                i += 1
            else:
                break

        attrs.append(Attribute(
            name=attr_name,
            type=attr_type,
            constraints=constraints,
            enum_values=enum_values,
            description=" ".join(desc_lines).strip(),
            annotations=annotations,
            reference_to=reference_to,
        ))

    return attrs


def _parse_entity(path: Path) -> Entity:
    """Parse an entity .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    entity = Entity(
        name=fm.get("entity", path.stem.title()),
        description=fm.get("description", ""),
        inherits=fm.get("inherits"),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    if "Attributes" in sections:
        entity.attributes = _parse_attributes(sections["Attributes"])
    if "Identity" in sections:
        entity.identity = sections["Identity"]
    if "Lifecycle" in sections:
        entity.lifecycle = sections["Lifecycle"]
    if "Notes" in sections:
        entity.notes = sections["Notes"]

    return entity


def _parse_relationship_block(lines: list[str], name: str) -> Relationship | None:
    """Parse a single relationship block."""
    from_entity = ""
    to_entity = ""
    cardinality = ""
    desc_lines: list[str] = []
    properties: list[RelationshipProperty] = []
    in_properties = False
    current_property: RelationshipProperty | None = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("from:") and "->" in stripped:
            match = re.match(r'from:\s*(\w+)\s*->\s*to:\s*(\w+)', stripped)
            if match:
                from_entity = match.group(1)
                to_entity = match.group(2)
        elif stripped.startswith("cardinality:"):
            cardinality = stripped.split(":", 1)[1].strip()
        elif stripped == "properties:":
            in_properties = True
        elif in_properties and stripped.startswith("| ") and current_property:
            extra = stripped[2:].strip()
            if extra:
                current_property.description = (
                    f"{current_property.description} {extra}".strip()
                )
        elif in_properties and ":" in stripped:
            prop_match = re.match(r'(\w+):\s*(.+)', stripped)
            if prop_match:
                current_property = RelationshipProperty(
                    name=prop_match.group(1),
                    type=prop_match.group(2).strip(),
                )
                properties.append(current_property)
        elif stripped.startswith("| "):
            desc_lines.append(stripped[2:])

    if from_entity and to_entity:
        return Relationship(
            name=name,
            from_entity=from_entity,
            to_entity=to_entity,
            cardinality=cardinality,
            description=" ".join(desc_lines).strip(),
            properties=properties,
        )
    return None


def _parse_traversal_block(lines: list[str], name: str) -> Traversal | None:
    """Parse a traversal block."""
    path = ""
    desc_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("path:"):
            path = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("| "):
            desc_lines.append(stripped[2:])

    if path:
        return Traversal(
            name=name,
            path=path,
            description=" ".join(desc_lines).strip(),
        )
    return None


def _parse_relationship_file(path: Path) -> RelationshipFile:
    """Parse a relationships .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    rf = RelationshipFile(
        domain=fm.get("domain", ""),
        description=fm.get("description", ""),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    for section_name, content in sections.items():
        if section_name == "__preamble__":
            continue
        lines = content.split("\n")

        if section_name.startswith("Traversal: "):
            trav_name = section_name[len("Traversal: "):]
            trav = _parse_traversal_block(lines, trav_name)
            if trav:
                rf.traversals.append(trav)
        elif section_name.isupper() or "_" in section_name.upper():
            rel = _parse_relationship_block(lines, section_name)
            if rel:
                rf.relationships.append(rel)

    return rf


def _parse_rule_block(lines: list[str], name: str) -> Rule:
    """Parse a single rule block."""
    rule = Rule(name=name)
    prose_lines: list[str] = []
    condition_lines: list[str] = []
    action_lines: list[str] = []
    current_block = "meta"

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("applies_to:"):
            rule.applies_to = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("severity:"):
            rule.severity = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("trigger:"):
            rule.trigger = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("outputs:"):
            rule.outputs = stripped.split(":", 1)[1].strip()
        elif stripped == "condition:":
            current_block = "condition"
        elif stripped == "action:":
            current_block = "action"
        elif current_block == "condition" and stripped:
            condition_lines.append(stripped)
        elif current_block == "action" and stripped:
            action_lines.append(stripped)
        elif current_block == "meta" and stripped and not stripped.startswith("applies_to") \
                and not stripped.startswith("severity") and not stripped.startswith("trigger") \
                and not stripped.startswith("outputs"):
            # Check if we've moved to prose
            if not any(stripped.startswith(k) for k in ["applies_to", "severity", "trigger", "outputs"]):
                current_block = "prose"
                prose_lines.append(stripped)
        elif current_block == "prose":
            prose_lines.append(line.rstrip())
        elif current_block == "action" and not stripped:
            # Empty line after action block -> switch to prose
            current_block = "prose"

    rule.condition = "\n".join(condition_lines).strip()
    rule.action = "\n".join(action_lines).strip()
    rule.prose = "\n".join(prose_lines).strip()

    return rule


def _parse_rule_file(path: Path) -> RuleFile:
    """Parse a rules .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    rf = RuleFile(
        domain=fm.get("domain", ""),
        description=fm.get("description", ""),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    for section_name, content in sections.items():
        if section_name == "__preamble__":
            continue
        lines = content.split("\n")
        rule = _parse_rule_block(lines, section_name)
        rf.rules.append(rule)

    return rf


def _parse_taxonomy_tree(lines: list[str]) -> TaxonomyNode | None:
    """Parse ASCII tree notation into TaxonomyNode hierarchy."""
    if not lines:
        return None

    # Find root (first non-empty, non-comment line)
    root_line = ""
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("|") and not stripped.startswith("#"):
            root_line = stripped
            start_idx = i
            break

    if not root_line:
        return None

    root_name, root_tags = _extract_tags(root_line)
    root = TaxonomyNode(name=root_name, tags=root_tags, depth=0)

    # Parse tree lines
    stack: list[tuple[int, TaxonomyNode]] = [(0, root)]

    for line in lines[start_idx + 1:]:
        if not line.strip():
            continue
        if line.strip().startswith("##"):
            break

        # Calculate indent level from tree characters
        indent = 0
        content = line
        for ch in ["│", "├", "└", "─", " ", "─"]:
            content = content.replace(ch, " ", 1) if ch in content[:20] else content

        # More robust: count leading tree/space chars
        stripped = line.lstrip("│├└─ \t")
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip("│├└─ \t"))
        # Normalize indent to depth (roughly 4 chars per level)
        depth = max(1, (indent + 2) // 4)

        node_text = stripped.strip()
        if node_text.startswith("| "):
            # Description line for previous node
            if stack:
                stack[-1][1].description += " " + node_text[2:]
            continue

        name, tags = _extract_tags(node_text)

        # Split off inline description
        desc = ""
        if "|" in name:
            parts = name.split("|", 1)
            name = parts[0].strip()
            desc = parts[1].strip()

        node = TaxonomyNode(name=name, tags=tags, description=desc, depth=depth)

        # Find parent: pop stack until we find a node at lower depth
        while stack and stack[-1][0] >= depth:
            stack.pop()

        if stack:
            stack[-1][1].children.append(node)

        stack.append((depth, node))

    return root


def _extract_tags(text: str) -> tuple[str, list[str]]:
    """Extract @tag: annotations from a line."""
    tags: list[str] = []
    clean = text
    for match in re.finditer(r'@tag:\s*(\S+)', text):
        tags.append(match.group(1))
    clean = re.sub(r'\s*@tag:\s*\S+', '', clean).strip()
    return clean, tags


def _parse_taxonomy(path: Path) -> Taxonomy:
    """Parse a taxonomy .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    taxonomy = Taxonomy(
        name=fm.get("taxonomy", path.stem.title()),
        description=fm.get("description", ""),
        applied_to=fm.get("applied_to", ""),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    # The main body (preamble or first section) contains the tree
    tree_text = sections.get("__preamble__", "")
    if tree_text:
        tree_lines = tree_text.split("\n")
        taxonomy.root = _parse_taxonomy_tree(tree_lines)

    if "Inheritance Rules" in sections:
        taxonomy.inheritance_rules = sections["Inheritance Rules"]

    return taxonomy


def _parse_glossary(path: Path) -> Glossary:
    """Parse a glossary .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    glossary = Glossary(
        description=fm.get("description", ""),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    for section_name, content in sections.items():
        if section_name == "__preamble__":
            continue
        glossary.entries.append(GlossaryEntry(
            term=section_name,
            definition=content.strip(),
        ))

    return glossary


def _merge_glossary(base: Glossary, other: Glossary) -> None:
    """Merge glossary entries/descriptions from another glossary file."""
    if other.description:
        if base.description:
            base.description = f"{base.description.strip()}\n\n{other.description.strip()}"
        else:
            base.description = other.description
    base.entries.extend(other.entries)


def _parse_view(path: Path) -> View:
    """Parse a view .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    view = View(
        name=fm.get("view", path.stem.title()),
        description=fm.get("description", ""),
        audience=fm.get("audience", ""),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    if "Entities" in sections:
        view.entities = _parse_list_items(sections["Entities"])
    if "Relationships" in sections:
        view.relationships = _parse_list_items(sections["Relationships"])
    if "Rules" in sections:
        view.rules = _parse_list_items(sections["Rules"])
    if "Key Questions" in sections:
        view.key_questions = _parse_list_items(sections["Key Questions"])
    if "Not In Scope" in sections:
        view.not_in_scope = sections["Not In Scope"]
    if "Notes" in sections:
        view.notes = sections["Notes"]

    return view


def _parse_list_items(text: str) -> list[str]:
    """Parse markdown list items."""
    items: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


_CLAIM_KINDS = {"fact", "belief", "value", "precedent"}


def _extract_claims(content: str) -> tuple[str, list[KnowledgeClaim]]:
    """Extract semi-structured claim lines from observation prose."""
    prose_lines: list[str] = []
    claims: list[KnowledgeClaim] = []
    for line in content.split("\n"):
        stripped = line.strip()
        claim_match = re.match(r"^(Fact|Belief|Value|Precedent):\s*(.+)$", stripped, re.IGNORECASE)
        if claim_match:
            kind = claim_match.group(1).lower()
            if kind in _CLAIM_KINDS:
                claims.append(KnowledgeClaim(kind=kind, text=claim_match.group(2).strip()))
                continue
        prose_lines.append(line)
    prose = "\n".join(prose_lines).strip()
    return prose, claims


def _parse_observation_file(path: Path) -> ObservationFile:
    """Parse an observations .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)
    confidence = fm.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = None

    of = ObservationFile(
        name=fm.get("observations", path.stem.title()),
        about=fm.get("about", ""),
        observed_by=fm.get("observed_by", ""),
        date=str(fm.get("date", "")),
        confidence=confidence,
        status=status or fm.get("status", ""),
        source_file=path,
        provenance=provenance,
    )

    for section_name, content in sections.items():
        if section_name == "__preamble__":
            continue
        prose, claims = _extract_claims(content)
        of.observations.append(Observation(
            heading=section_name,
            prose=prose,
            claims=claims,
        ))

    return of


def _parse_outcome_file(path: Path) -> OutcomeFile:
    """Parse an outcomes .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    sections = _split_sections(body)

    provenance, status = _parse_provenance(fm)

    of = OutcomeFile(
        name=fm.get("outcomes", path.stem.title()),
        reviewed_by=fm.get("reviewed_by", ""),
        date=str(fm.get("date", "")),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    for section_name, content in sections.items():
        if section_name == "__preamble__":
            continue

        # Extract Ref: and Takeaway: markers from prose
        refs = []
        takeaways = []
        prose_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("Ref:"):
                refs.append(stripped[4:].strip())
            elif stripped.startswith("Takeaway:"):
                takeaways.append(stripped[9:].strip())
            else:
                prose_lines.append(line)

        of.outcomes.append(Outcome(
            heading=section_name,
            prose="\n".join(prose_lines).strip(),
            refs=refs,
            takeaways=takeaways,
        ))

    return of


def _split_sections_seq(body: str) -> list[tuple[str, str]]:
    """Split body into [(section_name, content), ...] preserving order and duplicates."""
    sections: list[tuple[str, str]] = []
    current_section = "__preamble__"
    lines: list[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            sections.append((current_section, "\n".join(lines).strip()))
            current_section = line[3:].strip()
            lines = []
        else:
            lines.append(line)

    sections.append((current_section, "\n".join(lines).strip()))
    return sections


def _parse_decision_file(path: Path) -> DecisionFile:
    """Parse a decisions .lore file."""
    text = path.read_text()
    fm, body = _split_frontmatter(text)
    # Use sequential section splitter to preserve duplicate section names
    # (e.g. multiple ## Context sections in a multi-decision file)
    sections = _split_sections_seq(body)

    provenance, status = _parse_provenance(fm)

    df = DecisionFile(
        name=fm.get("decision", path.stem.replace("-", " ").replace("_", " ").title()),
        decided_by=fm.get("decided_by", ""),
        date=str(fm.get("date", "")),
        source_file=path,
        provenance=provenance,
        status=status,
    )

    # Each ## heading is a separate decision.
    # Known sub-sections within a decision: Context, Resolution, Rationale, Affects, Evidence.
    # Strategy: walk sections sequentially and group by decision.
    # A section is a "decision heading" if it's NOT one of the known sub-section names.
    _SUB_SECTIONS = {"Context", "Resolution", "Rationale", "Affects", "Evidence"}

    # Build ordered decision groups: list of (heading, {subsection -> content})
    decision_groups: list[tuple[str, dict[str, str]]] = []
    current_parts: dict[str, str] | None = None
    current_heading: str | None = None

    def _ensure_current():
        nonlocal current_heading, current_parts
        if current_heading is None:
            current_heading = fm.get("decision",
                path.stem.replace("-", " ").replace("_", " ").title())
            current_parts = {}
            decision_groups.append((current_heading, current_parts))

    for section_name, content in sections:
        if section_name == "__preamble__":
            if content.strip():
                _ensure_current()
                current_parts["_preamble"] = content
            continue

        if section_name in _SUB_SECTIONS:
            _ensure_current()
            current_parts[section_name] = content
        else:
            # New decision heading
            current_heading = section_name
            current_parts = {}
            decision_groups.append((current_heading, current_parts))
            if content.strip():
                current_parts["_prose"] = content

    # If no decisions found but there's body content, create one from the whole body
    if not decision_groups and body.strip():
        fallback_name = fm.get("decision", path.stem.replace("-", " ").replace("_", " ").title())
        decision_groups.append((fallback_name, {"_prose": body}))

    # Convert grouped parts into Decision objects
    for heading, parts in decision_groups:
        context = parts.get("Context", "")
        resolution = parts.get("Resolution", "")
        rationale_raw = parts.get("Rationale", "")
        affects_raw = parts.get("Affects", "")
        evidence_raw = parts.get("Evidence", "")

        # If there's raw prose without sub-sections, try to use it as context
        prose = parts.get("_prose", "")
        preamble = parts.get("_preamble", "")
        if prose and not context:
            context = prose
        if preamble and not context:
            context = preamble

        # Extract claims from rationale
        rationale_prose, rationale_claims = _extract_claims(rationale_raw) if rationale_raw else ("", [])

        # Parse affects as list items (- prefixed lines)
        affects = _parse_ref_lines(affects_raw) if affects_raw else []

        # Parse evidence as list items
        evidence = _parse_ref_lines(evidence_raw) if evidence_raw else []

        df.decisions.append(Decision(
            heading=heading,
            context=context.strip(),
            resolution=resolution.strip(),
            rationale=rationale_prose.strip(),
            rationale_claims=rationale_claims,
            affects=affects,
            evidence=evidence,
        ))

    return df


def _parse_ref_lines(text: str) -> list[str]:
    """Parse list items or bare lines as references."""
    refs: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            refs.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("#"):
            refs.append(stripped)
    return refs
