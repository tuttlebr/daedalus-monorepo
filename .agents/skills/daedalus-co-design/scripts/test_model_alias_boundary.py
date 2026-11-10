"""Cross-check the agent's model aliases against every discovered provider file.

Run with Python 3.12 and PyYAML. No service, binary or credential access. This
checks that configured and documented aliases resolve on whichever provider is
selected; it does not exercise routing, provider capability or task quality.
"""

import re
import tomllib
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
AGENT = ROOT / "submodules/daedalus-agent"
GATEWAY = ROOT / "submodules/daedalus-switchyard"
# A gateway alias, not a path, image or Secret reference such as daedalus/values.yaml.
ALIAS = re.compile(r"(?<![\w./-])daedalus(?:/[a-z_]+)?(?![\w/-]|\.\w)")


def providers():
    paths = sorted(GATEWAY.glob("routes_*.toml"))
    if not paths:
        raise AssertionError("No provider route configurations discovered")
    return {
        path.name: {route["id"] for route in tomllib.loads(path.read_text())["routes"].values()}
        for path in paths
    }


class ModelAliasBoundaryTest(unittest.TestCase):
    def assert_served(self, alias, where):
        for name, served in providers().items():
            with self.subTest(alias=alias, where=where, provider=name):
                self.assertIn(alias, served)

    def test_shipped_workflow_profiles_resolve_on_every_provider(self):
        workflow = yaml.safe_load((AGENT / "backend/tool-calling-config.yaml").read_text())
        routes = workflow["workflow"]["model_routes"]
        self.assertTrue(routes)
        for profile, value in routes.items():
            # ${NAME:-default}: the default is what an unset deployment sends.
            default = re.fullmatch(r"\$\{[A-Z0-9_]+:-([^}]+)\}", value)
            self.assertIsNotNone(default, f"{profile} has no default alias")
            self.assert_served(default[1], f"workflow.model_routes.{profile}")

    def test_template_aliases_and_examples_resolve_on_every_provider(self):
        """Comments count: a documented example is what an operator pastes."""
        for name in (".env.template", ".env.example"):
            lines = (AGENT / name).read_text().splitlines()
            # Only the gateway section names aliases; the bare word elsewhere
            # is the product, a namespace or a path component.
            aliases = {
                (alias, number)
                for number, line in enumerate(lines, 1)
                for alias in ALIAS.findall(line)
                if "/" in alias or re.match(r"#?\s*[A-Z0-9_]*MODEL[A-Z0-9_]*=daedalus$", line)
            }
            self.assertTrue(aliases, f"{name} names no gateway alias")
            for alias, number in sorted(aliases):
                self.assert_served(alias, f"{name}:{number}")


if __name__ == "__main__":
    unittest.main()
