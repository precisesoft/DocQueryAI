import os
import sys
import unittest

from flask import Flask, request


# Ensure we can import providers from the backend package
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from providers.base import select_provider_name, get_provider  # noqa: E402


class TestProviderSelection(unittest.TestCase):
    def setUp(self):
        # Clear env overrides for a clean slate
        os.environ.pop("LLM_PROVIDER", None)
        os.environ.pop("LLM_API_URL", None)
        os.environ.pop("OLLAMA_BASE_URL", None)
        self.app = Flask(__name__)

    def test_default_provider_is_ollama_when_unset(self):
        with self.app.test_request_context("/api/test"):
            self.assertEqual(select_provider_name(request), "ollama")

    def test_env_default_provider(self):
        os.environ["LLM_PROVIDER"] = "bedrock"
        with self.app.test_request_context("/api/test"):
            self.assertEqual(select_provider_name(request), "bedrock")

    def test_query_override(self):
        os.environ["LLM_PROVIDER"] = "bedrock"
        with self.app.test_request_context("/api/test?provider=ollama"):
            self.assertEqual(select_provider_name(request), "ollama")

    def test_json_override(self):
        os.environ["LLM_PROVIDER"] = "ollama"
        with self.app.test_request_context("/api/test", json={"provider": "bedrock"}):
            self.assertEqual(select_provider_name(request), "bedrock")

    def test_ollama_base_url_fallback(self):
        # When only OLLAMA_BASE_URL is set, provider should use it with /v1 suffix
        os.environ.pop("LLM_API_URL", None)
        os.environ["OLLAMA_BASE_URL"] = "http://myhost:1234"
        with self.app.test_request_context("/api/test"):
            provider = get_provider(request)
            # Access provider.base_url attribute from OllamaProvider
            self.assertTrue(hasattr(provider, "base_url"))
            self.assertEqual(provider.base_url, "http://myhost:1234/v1")

    def test_ollama_default_local_url_when_unset(self):
        # No LLM_API_URL and no OLLAMA_BASE_URL -> default to localhost:11434/v1
        os.environ.pop("LLM_API_URL", None)
        os.environ.pop("OLLAMA_BASE_URL", None)
        with self.app.test_request_context("/api/test"):
            provider = get_provider(request)
            self.assertEqual(provider.base_url, "http://localhost:11434/v1")


if __name__ == "__main__":
    unittest.main()

