# Plugin Guide

Lorelang supports plugin compilers and curators via `lore.yaml`.

## Compiler Plugin

Create a Python function that takes `Ontology` and returns `str`.

```python
from lore.models import Ontology

def compile_graphql(ontology: Ontology) -> str:
    lines = []
    for entity in ontology.entities:
        lines.append(f"type {entity.name} {{")
        for attr in entity.attributes:
            lines.append(f"  {attr.name}: String")
        lines.append("}")
    return "\n".join(lines)
```

Register in `lore.yaml`:

```yaml
plugins:
  compilers:
    graphql: mypackage.compilers:compile_graphql
```

Run:

```bash
lore compile my-ontology -t graphql
```

## Curator Plugin

Create a function that takes `Ontology` and returns `CurationReport`.

```python
from lore.models import Ontology
from lore.curator import CurationReport, CurationFinding

def curate_naming(ontology: Ontology) -> CurationReport:
    report = CurationReport(job="naming")
    for entity in ontology.entities:
        if entity.name != entity.name.strip():
            report.findings.append(
                CurationFinding(
                    job="naming",
                    severity="warning",
                    message=f"Entity has invalid spacing: {entity.name!r}",
                )
            )
    return report
```

Register:

```yaml
plugins:
  curators:
    naming: mypackage.curators:curate_naming
```

Run:

```bash
lore curate my-ontology --job naming
```

## Testing Plugins

Use fixture ontologies and assert plugin output in normal pytest tests.

```bash
PYTHONPATH=src python3 -m pytest -q
```
