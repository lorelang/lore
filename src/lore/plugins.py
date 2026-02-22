"""
Lore plugin loading helpers.

Plugins are configured in lore.yaml using module:function entrypoints.
"""
from __future__ import annotations
import importlib
from typing import Callable
from .models import Ontology


def load_entrypoint(entrypoint: str) -> Callable:
    """Load a callable from a `module:function` entrypoint string."""
    if ":" not in entrypoint:
        raise ValueError(
            f"Invalid entrypoint '{entrypoint}'. Expected format: module:function"
        )
    module_name, fn_name = entrypoint.split(":", 1)
    module_name = module_name.strip()
    fn_name = fn_name.strip()
    if not module_name or not fn_name:
        raise ValueError(
            f"Invalid entrypoint '{entrypoint}'. Expected format: module:function"
        )

    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name)
    if not callable(fn):
        raise TypeError(f"Entrypoint '{entrypoint}' is not callable")
    return fn


def available_compilers(ontology: Ontology) -> dict[str, str]:
    """Return configured compiler plugins as {name: entrypoint}."""
    if not ontology.manifest or not ontology.manifest.plugins:
        return {}
    return dict(ontology.manifest.plugins.compilers)


def available_curators(ontology: Ontology) -> dict[str, str]:
    """Return configured curator plugins as {name: entrypoint}."""
    if not ontology.manifest or not ontology.manifest.plugins:
        return {}
    return dict(ontology.manifest.plugins.curators)


def resolve_compiler(ontology: Ontology, name: str) -> Callable:
    """Resolve a compiler plugin by name."""
    compilers = available_compilers(ontology)
    if name not in compilers:
        raise KeyError(name)
    return load_entrypoint(compilers[name])


def resolve_curator(ontology: Ontology, name: str) -> Callable:
    """Resolve a curator plugin by name."""
    curators = available_curators(ontology)
    if name not in curators:
        raise KeyError(name)
    return load_entrypoint(curators[name])
