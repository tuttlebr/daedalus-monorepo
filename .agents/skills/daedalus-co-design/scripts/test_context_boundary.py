"""Cross-check generated context settings against the checked-out agent consumer.

Run with Python 3.12, PyYAML and jsonschema. No service or credential access.
This checks configuration compatibility, not ingestion/retrieval correctness.
"""

import importlib.util
from pathlib import Path
import re
import shlex
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[4]
CONTEXT = ROOT / "submodules/daedalus-context"
AGENT = ROOT / "submodules/daedalus-agent"
SPEC = importlib.util.spec_from_file_location("contextctl", CONTEXT / "scripts/contextctl.py")
contextctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contextctl)


class ContextBoundaryTest(unittest.TestCase):
    def test_generated_endpoints_resolve_actual_agent_workflow(self):
        workflow = yaml.safe_load((AGENT / "backend/tool-calling-config.yaml").read_text())
        functions = workflow["functions"]
        original_load = contextctl.load_yaml

        def topology_fixture(path):
            value = original_load(path)
            if path.name == "topology.yaml":
                for release in value["releases"].values():
                    release["namespace"] = "synthetic-context"
                value["releases"]["nv-ingest"]["services"]["api"].update(
                    name="synthetic-ingestion", port=8765
                )
            return value

        for environment in ("development", "production"):
            with self.subTest(environment=environment), patch.object(
                contextctl, "load_yaml", side_effect=topology_fixture
            ):
                generated = dict(
                    token.split("=", 1)
                    for token in shlex.split(contextctl.agent_env(environment), comments=True)
                )

                def resolve(value):
                    return re.sub(r"\$\{([^}]+)\}", lambda match: generated[match[1]], value)

                # Use the consumer's actual key references, not a second list of
                # expected environment names. Missing generator keys fail here.
                ingest = functions["user_document_tool"]
                host = resolve(ingest["nv_ingest_host"])
                port = int(resolve(ingest["nv_ingest_port"]))
                self.assertEqual(host, "synthetic-ingestion.synthetic-context.svc.cluster.local")
                self.assertEqual(port, 8765)
                self.assertEqual(f"http://{host}:{port}", generated["NV_INGEST_ENDPOINT"])

                domain = functions["domain_retriever_tool"]
                embedder = workflow["embedders"][domain["embedding_model"]]
                for value in (domain["uri"], domain["reranker_endpoint"], embedder["base_url"]):
                    self.assertIn(".synthetic-context.svc.cluster.local:", resolve(value))
                rag = original_load(CONTEXT / "stack/rag-schema.yaml")
                self.assertEqual(resolve(embedder["model_name"]), rag["embedding"]["model"])
                self.assertEqual(resolve(domain["reranker_model"]), rag["reranker"]["model"])
                self.assertEqual(resolve(domain["database_name"]), rag.get("database", "default"))

    def test_agent_env_template_names_served_models(self):
        """A template built without render-agent-env must still name served models.

        The embedder serves no legacy aliases; a stale template ID fails every
        query embedding while readiness still reports ready.
        """
        template = dict(
            line.split("=", 1)
            for line in (AGENT / ".env.template").read_text().splitlines()
            if "=" in line and not line.startswith("#")
        )
        rag = contextctl.load_yaml(CONTEXT / "stack/rag-schema.yaml")
        generated = dict(
            token.split("=", 1)
            for token in shlex.split(contextctl.agent_env("production"), comments=True)
        )
        self.assertEqual(template["EMBEDDING_MODEL"], rag["embedding"]["model"])
        self.assertEqual(template["RERANKER_MODEL"], rag["reranker"]["model"])
        # Upload metadata records this ID; it must name the same embedding space.
        self.assertEqual(template["EMBEDDING_NIM_MODEL_NAME"], rag["embedding"]["model"])
        self.assertEqual(generated["EMBEDDING_NIM_MODEL_NAME"], rag["embedding"]["model"])


if __name__ == "__main__":
    unittest.main()
