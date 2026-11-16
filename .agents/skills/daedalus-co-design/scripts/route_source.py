"""Use Switchyard's composition contract without resolving private header values."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
_SPEC = importlib.util.spec_from_file_location(
    "codesign_route_renderer",
    ROOT / "submodules/daedalus-switchyard/scripts/render_routes.py",
)
_RENDERER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_RENDERER)


def compose_routes(path):
    """Snapshot the explicitly selected profile and its includes as standalone TOML."""
    return _RENDERER.compose_source(Path(path))
