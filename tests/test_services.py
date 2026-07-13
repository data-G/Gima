import json
import base64
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import io
from pathlib import Path
from unittest.mock import patch

from human_ai.config import Config
from human_ai.memory import MemoryStore
from human_ai.services import (
    AdvancedVideoSongRenderer,
    ExternalMusicApiGenerator,
    FrontierVideoPlanner,
    HuggingFaceFeatureExtractor,
    HuggingFaceImageGenerator,
    HuggingFaceVideoGenerator,
    LipSyncPlanner,
    LocalImageMusicVideoRenderer,
    LocalMusicVideoDirector,
    LocalMusicVideoRenderer,
    NeuralLipSyncRenderer,
    OpenSourceVideoApiRenderer,
    OpenRouterCatalog,
    OpenRouterSpeechGenerator,
    OpenRouterVideoGenerator,
    OpenAIImageGenerator,
    SandboxedCodeRunner,
    SafeToolRunner,
    TeacherModelClient,
    TransformersTextGenerator,
    VideoQualityEvaluator,
    WebImporter,
    WhatsAppMessenger,
)
from human_ai.model_council import ModelCouncil
from human_ai.openrouter_router import OpenRouterTaskRouter, RoutingRequest
from human_ai.vibe_code import VibeCodingAgent


class ServiceSafetyTests(unittest.TestCase):
    def test_web_import_blocks_local_addresses(self):
        with self.assertRaises(PermissionError):
            WebImporter([]).fetch("http://127.0.0.1/private")

    def test_tool_runner_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            memory = MemoryStore(config.resolved_data_dir)
            with self.assertRaises(PermissionError):
                SafeToolRunner(config, memory).run(["git", "status"])

    def test_tool_runner_rejects_non_allowlisted_command(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.tools.enabled = True
            config.permissions.require_scoped_grants = False
            memory = MemoryStore(config.resolved_data_dir)
            with self.assertRaises(PermissionError):
                SafeToolRunner(config, memory).run(["rm", "-rf", "something"])

    def test_sandboxed_code_runner_captures_output_and_blocks_workspace_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = root / "secret.txt"
            secret.write_text("private", encoding="utf-8")
            runner = SandboxedCodeRunner(root / "runs", protected_roots=[root])

            hello = runner.run("python", "print(17 * 19)")
            blocked = runner.run("python", f"print(open({str(secret)!r}).read())")

            self.assertEqual(hello.exit_code, 0)
            self.assertEqual(hello.stdout.strip(), "323")
            self.assertTrue(hello.source_path.exists())
            self.assertTrue(hello.output_path.exists())
            self.assertNotEqual(blocked.exit_code, 0)
            self.assertNotIn("private", blocked.stdout)

    def test_web_search_falls_back_to_wikipedia(self):
        importer = WebImporter([])
        with patch.object(importer, "_duckduckgo_search", return_value=[]), patch.object(
            importer, "_wikipedia_search", return_value=["https://en.wikipedia.org/wiki/Large_language_model"]
        ):
            self.assertEqual(
                importer.search("large language model", limit=1),
                ["https://en.wikipedia.org/wiki/Large_language_model"],
            )

    def test_web_search_parses_duckduckgo_lite_result_links(self):
        importer = WebImporter([])

        class Response:
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, *_args):
                return (
                    b'<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fopenai.com%2Findex%2Fcomputer-using-agent%2F">'
                    b"Computer-Using Agent</a>"
                )

        with patch("urllib.request.urlopen", return_value=Response()):
            self.assertEqual(
                importer.search("OpenAI browser agents", limit=1),
                ["https://openai.com/index/computer-using-agent/"],
            )

    def test_open_source_video_targets_include_wan555_safety_gate(self):
        targets = {target.provider_id: target for target in OpenSourceVideoApiRenderer.known_targets()}

        self.assertIn("wan555_huggingface_space", targets)
        wan555 = targets["wan555_huggingface_space"]
        self.assertEqual(wan555.backend, "Gradio queue API")
        self.assertEqual(wan555.auth_env, "HF_TOKEN")
        self.assertTrue(wan555.requires_cloud_allowed)
        self.assertTrue(wan555.requires_explicit_consent)
        self.assertIn("kulkas2pintu/wan555/agents.md", wan555.source_url)
        self.assertTrue(any("Do not upload private" in note for note in wan555.safety_notes))

    def test_teacher_model_requires_known_provider(self):
        with self.assertRaises(ValueError):
            TeacherModelClient(Config()).ask("unknown", "hello")

    def test_openai_response_text_is_parsed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test", "CLOUD_ALLOWED": "true"}), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"output_text":"teacher answer"}'
            )
            self.assertEqual(client.ask("chatgpt", "hello"), "teacher answer")

    def test_teacher_model_requires_cloud_allowed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}, clear=True), patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(PermissionError):
                client.ask("chatgpt", "hello")
            urlopen.assert_not_called()

    def test_openai_falls_back_when_top_model_is_unavailable(self):
        config = Config()
        config.teacher_models.openai_model = "gpt-5.5"
        client = TeacherModelClient(config)

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"output_text":"fallback answer"}'

        def fake_urlopen(request, timeout=0):
            body = json.loads(request.data.decode("utf-8"))
            if body["model"] == "gpt-5.5":
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, io.BytesIO(b'{"error":"not found"}'))
            self.assertEqual(body["model"], "gpt-5.1")
            return Response()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test", "CLOUD_ALLOWED": "true"}), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertIn("fallback answer", client.ask("chatgpt", "hello"))

    def test_openrouter_uses_chat_completions_headers_and_fallback_model(self):
        config = Config()
        config.teacher_models.openrouter_model = "openai/gpt-5.5"
        client = TeacherModelClient(config)
        calls = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"router fallback answer"}}]}'

        def fake_urlopen(request, timeout=0):
            calls.append(request)
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(request.full_url, "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer test-router")
            self.assertEqual(request.headers["Http-referer"], "http://127.0.0.1:8787")
            self.assertEqual(request.headers["X-title"], "Gima local assistant")
            self.assertEqual(body["messages"], [{"role": "user", "content": "hello"}])
            self.assertEqual(body["provider"]["sort"], "latency")
            self.assertEqual(body["provider"]["data_collection"], "deny")
            if body["model"] == "openai/gpt-5.5":
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, io.BytesIO(b'{"error":"not found"}'))
            self.assertEqual(body["model"], "openrouter/auto")
            return Response()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-router", "CLOUD_ALLOWED": "true"}), patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            answer = client.ask("openrouter", "hello")

        self.assertIn("router fallback answer", answer)
        self.assertIn("[OpenRouter model used: openrouter/auto]", answer)
        self.assertEqual(len(calls), 2)

    def test_openai_compatible_headers_are_ascii_safe(self):
        client = TeacherModelClient(Config())

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"ok"}}]}'

        def fake_urlopen(request, timeout=0):
            self.assertEqual(request.headers["X-title"], "Gima ")
            return Response()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            answer = client._ask_openai_compatible(
                "https://example.test/chat/completions",
                "test-key",
                "test-model",
                "hello",
                extra_headers={"X-Title": "Gima නව"},
            )
        self.assertEqual(answer, "ok")

    def test_openrouter_catalog_fetches_normalizes_and_caches_models(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return json.dumps(
                        {
                            "data": [
                                {
                                    "id": "openai/gpt-4o",
                                    "name": "GPT-4o",
                                    "context_length": 128000,
                                    "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
                                    "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                                    "supported_parameters": ["temperature"],
                                },
                                {
                                    "id": "meta-llama/llama-3.3-70b-instruct:free",
                                    "name": "Llama Free",
                                    "context_length": 8192,
                                    "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                                    "pricing": {"prompt": "0", "completion": "0"},
                                },
                            ]
                        }
                    ).encode("utf-8")

            def fake_urlopen(request, timeout=0):
                self.assertIn("https://openrouter.ai/api/v1/models?", request.full_url)
                self.assertIn("output_modalities=all", request.full_url)
                return Response()

            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                data = OpenRouterCatalog(config).models(refresh=True, query="llama")

            self.assertEqual(data["source"], "openrouter")
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["models"][0]["id"], "meta-llama/llama-3.3-70b-instruct:free")
            self.assertTrue(data["models"][0]["free"])
            self.assertTrue((config.resolved_data_dir / "openrouter" / "models_catalog.json").exists())

    def test_openrouter_routing_config_is_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            catalog = OpenRouterCatalog(config)
            saved = catalog.save_routing_config(
                {
                    "routing_sort": "throughput",
                    "data_collection": "deny",
                    "fallback_models": "openrouter/auto, openrouter/free",
                    "auxiliary_models": {"vision": "google/gemini-flash-1.5"},
                    "pareto_min_coding_score": 0.7,
                }
            )
            loaded = OpenRouterCatalog(config).routing_config()

        self.assertEqual(saved["routing_sort"], "throughput")
        self.assertEqual(loaded["fallback_models"], ["openrouter/auto", "openrouter/free"])
        self.assertEqual(loaded["auxiliary_models"]["vision"], "google/gemini-flash-1.5")
        self.assertEqual(loaded["pareto_min_coding_score"], 0.7)

    def test_openrouter_task_router_keeps_high_privacy_local(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.model.active_level = "fast"
            decision = OpenRouterTaskRouter(config).decide(
                RoutingRequest("summarize this private document with API key", privacy="high")
            )

        self.assertEqual(decision.provider, "local")
        self.assertEqual(decision.model, "fast")
        self.assertEqual(decision.task_category, "PRIVATE_LOCAL_TASK")
        self.assertFalse(decision.fallbacks)

    def test_openrouter_task_router_routes_coding_to_cloud_when_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}):
            config = Config(workspace=Path(temp))
            catalog = OpenRouterCatalog(config)
            catalog.save_routing_config(
                {
                    "auxiliary_models": {"coding": "anthropic/claude-sonnet-4.5"},
                    "fallback_models": ["openrouter/auto"],
                }
            )
            decision = OpenRouterTaskRouter(config).decide(RoutingRequest("debug this Python class", mode="AUTO"))

        self.assertEqual(decision.provider, "openrouter")
        self.assertEqual(decision.task_category, "DEBUGGING")
        self.assertEqual(decision.model, "anthropic/claude-sonnet-4.5")
        self.assertIn("openrouter/auto", decision.fallbacks)

    def test_openrouter_task_router_writes_usage_log_without_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            path = OpenRouterTaskRouter(config).log_usage(
                provider="openrouter",
                model="openrouter/auto",
                prompt_tokens=10,
                completion_tokens=5,
                estimated_cost_usd=0.001,
                latency_seconds=1.25,
                success=True,
                fallback_used="",
                request_id="route_test",
            )
            text = path.read_text(encoding="utf-8")

        self.assertIn("route_test", text)
        self.assertIn("openrouter/auto", text)
        self.assertNotIn("sk-", text)

    def test_model_council_prefers_mai_voice_for_speech_output(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            plan = ModelCouncil(config).plan("Use Microsoft MAI speech API to speak this answer")
        self.assertEqual(plan["winner"]["model"], "microsoft/mai-voice-2")
        self.assertTrue(any(row["name"] == "QVAC Llama 3.2 1B local" for row in plan["recommendations"]))
        self.assertIn("safety", plan)

    def test_openrouter_speech_generator_posts_mai_voice_payload(self):
        class Headers:
            def get(self, key, default=None):
                return {"Content-Type": "audio/mpeg", "X-Generation-Id": "gen-speech-1"}.get(key, default)

        class Response:
            headers = Headers()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"fake mp3"

        def fake_urlopen(request, timeout=0):
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(request.full_url, "https://openrouter.ai/api/v1/audio/speech")
            self.assertEqual(request.headers["Authorization"], "Bearer test-router-speech")
            self.assertEqual(body["model"], "microsoft/mai-voice-2")
            self.assertEqual(body["voice"], "en-US-Harper:MAI-Voice-2")
            self.assertEqual(body["response_format"], "mp3")
            self.assertEqual(body["provider"]["options"]["azure"]["style"], "cheerful")
            return Response()

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ", {"OPENROUTER_SPEECH_API_KEY": "test-router-speech", "OPENROUTER_API_KEY": "fallback-router", "CLOUD_ALLOWED": "true"}
        ), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = OpenRouterSpeechGenerator(Path(temp)).generate("Hello from Gima", consent=True)
            self.assertTrue(Path(result["output_path"]).exists())
            self.assertEqual(Path(result["output_path"]).read_bytes(), b"fake mp3")

        self.assertEqual(result["status"], "generated")

    def test_openrouter_speech_generator_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-router"}, clear=True):
            with self.assertRaises(PermissionError):
                OpenRouterSpeechGenerator(Path(temp)).generate("Hello", consent=True)

    def test_gemini_response_text_is_parsed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test", "CLOUD_ALLOWED": "true"}), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"candidates":[{"content":{"parts":[{"text":"gemini answer"}]}}]}'
            )
            self.assertEqual(client.ask("gemini", "hello"), "gemini answer")

    def test_openai_image_generator_writes_png_and_manifest(self):
        png = b"\x89PNG\r\n\x1a\nfake"

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(
                    {
                        "data": [
                            {
                                "b64_json": base64.b64encode(png).decode("ascii"),
                                "revised_prompt": "A polished Gima logo",
                            }
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout=0):
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(request.full_url, "https://api.openai.com/v1/images/generations")
            self.assertEqual(request.headers["Authorization"], "Bearer test-openai")
            self.assertEqual(body["model"], "gpt-image-2")
            self.assertEqual(body["prompt"], "Gima logo")
            return Response()

        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai", "CLOUD_ALLOWED": "true"}), patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            result = OpenAIImageGenerator(Path(temp)).generate("Gima logo", consent=True)
            self.assertEqual(Path(result["output_path"]).read_bytes(), png)
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["provider"], "openai")
            self.assertEqual(manifest["revised_prompt"], "A polished Gima logo")

    def test_openai_image_generator_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai"}, clear=True), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            with self.assertRaises(PermissionError):
                OpenAIImageGenerator(Path(temp)).generate("Gima logo", consent=True)
            urlopen.assert_not_called()

    def test_huggingface_image_generator_uses_inference_client(self):
        class FakeImage:
            def save(self, path):
                Path(path).write_bytes(b"png bytes")

        class FakeClient:
            def __init__(self, provider, api_key):
                self.provider = provider
                self.api_key = api_key

            def text_to_image(self, prompt, model):
                self.prompt = prompt
                self.model = model
                return FakeImage()

        class FakeHub:
            InferenceClient = FakeClient

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ", {"HF_TOKEN": "test-hf", "CLOUD_ALLOWED": "true"}, clear=True
        ), patch("human_ai.services.importlib.import_module", return_value=FakeHub):
            result = HuggingFaceImageGenerator(Path(temp)).generate(
                "Astronaut riding a horse",
                model="black-forest-labs/FLUX.1-dev",
                provider="wavespeed",
                consent=True,
            )
            output = Path(str(result["output_path"]))
            manifest = json.loads(Path(str(result["manifest_path"])).read_text(encoding="utf-8"))
            self.assertEqual(output.read_bytes(), b"png bytes")
            self.assertEqual(manifest["provider"], "huggingface")
            self.assertEqual(manifest["inference_provider"], "wavespeed")
            self.assertEqual(manifest["model"], "black-forest-labs/FLUX.1-dev")

    def test_huggingface_image_generator_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"HF_TOKEN": "test-hf"}, clear=True):
            with self.assertRaises(PermissionError):
                HuggingFaceImageGenerator(Path(temp)).generate("image prompt", consent=True)

    def test_huggingface_feature_extractor_uses_inference_client(self):
        class FakeClient:
            def __init__(self, provider, api_key):
                self.provider = provider
                self.api_key = api_key

            def feature_extraction(self, text, model):
                self.text = text
                self.model = model
                return [[0.1, 0.2], [0.3, 0.4]]

        class FakeHub:
            InferenceClient = FakeClient

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ", {"HF_TOKEN": "test-hf", "CLOUD_ALLOWED": "true"}, clear=True
        ), patch("human_ai.services.importlib.import_module", return_value=FakeHub):
            result = HuggingFaceFeatureExtractor(Path(temp)).extract(
                "Today is a sunny day and I will get some ice cream.",
                model="microsoft/harrier-oss-v1-0.6b",
                provider="hf-inference",
                consent=True,
            )
            features = json.loads(Path(str(result["features_path"])).read_text(encoding="utf-8"))
            csv_text = Path(str(result["csv_path"])).read_text(encoding="utf-8")
            manifest = json.loads(Path(str(result["manifest_path"])).read_text(encoding="utf-8"))
            self.assertEqual(features, [[0.1, 0.2], [0.3, 0.4]])
            self.assertIn("0.1", csv_text)
            self.assertEqual(manifest["provider"], "huggingface")
            self.assertEqual(manifest["inference_provider"], "hf-inference")
            self.assertEqual(result["stats"]["count"], 4)

    def test_huggingface_feature_extractor_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"HF_TOKEN": "test-hf"}, clear=True):
            with self.assertRaises(PermissionError):
                HuggingFaceFeatureExtractor(Path(temp)).extract("private text", consent=True)

    def test_transformers_text_generator_uses_pipeline_messages(self):
        calls = {}

        class FakeMps:
            @staticmethod
            def is_available():
                return True

        class FakeCuda:
            @staticmethod
            def is_available():
                return False

        class FakeBackends:
            mps = FakeMps()

        class FakeTorch:
            bfloat16 = "bf16"
            cuda = FakeCuda()
            backends = FakeBackends()

        class FakeTransformers:
            @staticmethod
            def pipeline(task, model, model_kwargs, device):
                calls["task"] = task
                calls["model"] = model
                calls["model_kwargs"] = model_kwargs
                calls["device"] = device

                def run(messages, max_new_tokens):
                    calls["messages"] = messages
                    calls["max_new_tokens"] = max_new_tokens
                    return [
                        {
                            "generated_text": [
                                {"role": "user", "content": messages[0]["content"]},
                                {"role": "assistant", "content": "Ahoy from local Gemma."},
                            ]
                        }
                    ]

                return run

        def fake_import(name):
            if name == "torch":
                return FakeTorch
            if name == "transformers":
                return FakeTransformers
            raise ImportError(name)

        with tempfile.TemporaryDirectory() as temp, patch("human_ai.services.importlib.import_module", side_effect=fake_import):
            result = TransformersTextGenerator(Path(temp)).generate(
                "Who are you? Please, answer in pirate-speak.",
                model="google/gemma-2-2b-it",
                device="auto",
                max_new_tokens=256,
                local_files_only=True,
                consent=True,
            )
            manifest = json.loads(Path(str(result["manifest_path"])).read_text(encoding="utf-8"))

        self.assertEqual(calls["task"], "text-generation")
        self.assertEqual(calls["model"], "google/gemma-2-2b-it")
        self.assertEqual(calls["device"], "mps")
        self.assertEqual(calls["model_kwargs"]["torch_dtype"], "bf16")
        self.assertTrue(calls["model_kwargs"]["local_files_only"])
        self.assertEqual(calls["messages"][0]["role"], "user")
        self.assertEqual(result["answer"], "Ahoy from local Gemma.")
        self.assertEqual(manifest["kind"], "local_transformers_text_generation")

    def test_transformers_text_generator_requires_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PermissionError):
                TransformersTextGenerator(Path(temp)).generate("hello", consent=False)

    def test_whatsapp_messenger_creates_draft_link(self):
        with tempfile.TemporaryDirectory() as temp:
            result = WhatsAppMessenger(Path(temp)).draft_link("+94 77 123 4567", "Hello from Gima")
            manifest = json.loads(Path(str(result["manifest_path"])).read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "drafted")
        self.assertEqual(result["recipient"], "94771234567")
        self.assertIn("https://wa.me/94771234567?text=Hello%20from%20Gima", result["wa_me_link"])
        self.assertEqual(manifest["kind"], "whatsapp_message_draft")

    def test_whatsapp_messenger_sends_official_cloud_api_payload(self):
        calls = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"messages":[{"id":"wamid.test"}]}'

        def fake_urlopen(request, timeout=0):
            calls.append(request)
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(request.full_url, "https://graph.facebook.com/v20.0/phone-id/messages")
            self.assertEqual(request.headers["Authorization"], "Bearer test-token")
            self.assertEqual(body["messaging_product"], "whatsapp")
            self.assertEqual(body["to"], "94771234567")
            self.assertEqual(body["text"]["body"], "Hello from Gima")
            return Response()

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ",
            {
                "WHATSAPP_CLOUD_TOKEN": "test-token",
                "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
                "CLOUD_ALLOWED": "true",
            },
            clear=True,
        ), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = WhatsAppMessenger(Path(temp)).send_text("+94 77 123 4567", "Hello from Gima", consent=True)
            manifest = json.loads(Path(str(result["manifest_path"])).read_text(encoding="utf-8"))

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["api_response"]["messages"][0]["id"], "wamid.test")
        self.assertEqual(manifest["kind"], "whatsapp_cloud_text_message")

    def test_whatsapp_messenger_requires_cloud_allowed_for_send(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ",
            {"WHATSAPP_CLOUD_TOKEN": "test-token", "WHATSAPP_PHONE_NUMBER_ID": "phone-id"},
            clear=True,
        ):
            with self.assertRaises(PermissionError):
                WhatsAppMessenger(Path(temp)).send_text("+94771234567", "Hello", consent=True)

    def test_whatsapp_messenger_records_webhook_and_searches_messages(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "94771234567",
                                        "id": "wamid.inbound",
                                        "timestamp": "123456",
                                        "type": "text",
                                        "text": {"body": "Need the invoice please"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp:
            messenger = WhatsAppMessenger(Path(temp))
            result = messenger.record_webhook(payload)
            search = messenger.search_messages("invoice")

        self.assertEqual(result["received_count"], 1)
        self.assertEqual(search["count"], 1)
        self.assertEqual(search["messages"][0]["direction"], "inbound")
        self.assertIn("invoice", search["messages"][0]["text"])

    def test_openrouter_video_generator_submits_polls_and_downloads(self):
        video_bytes = b"fake mp4"
        calls = []

        class Response:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        def fake_urlopen(request, timeout=0):
            url = request.full_url if hasattr(request, "full_url") else str(request)
            calls.append(url)
            if url == "https://openrouter.ai/api/v1/videos":
                body = json.loads(request.data.decode("utf-8"))
                self.assertEqual(body["model"], "google/veo-3.1")
                self.assertEqual(body["prompt"], "cinematic Gima video")
                self.assertEqual(request.headers["Authorization"], "Bearer test-router-video")
                return Response(b'{"id":"job-1","polling_url":"/api/v1/videos/job-1","status":"pending"}')
            if url == "https://openrouter.ai/api/v1/videos/job-1":
                return Response(b'{"id":"job-1","generation_id":"gen-1","status":"completed","unsigned_urls":["https://cdn.example/video.mp4"],"usage":{"cost":0.5}}')
            if url == "https://cdn.example/video.mp4":
                return Response(video_bytes)
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"OPENROUTER_VIDEO_API_KEY": "test-router-video", "OPENROUTER_API_KEY": "fallback-router", "CLOUD_ALLOWED": "true"}), patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            result = OpenRouterVideoGenerator(Path(temp)).generate("cinematic Gima video", consent=True)
            self.assertEqual(Path(result["output_path"]).read_bytes(), video_bytes)
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["model"], "google/veo-3.1")
            self.assertEqual(manifest["final_status"]["usage"]["cost"], 0.5)

        self.assertEqual(calls, ["https://openrouter.ai/api/v1/videos", "https://openrouter.ai/api/v1/videos/job-1", "https://cdn.example/video.mp4"])

    def test_openrouter_video_generator_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-router"}, clear=True), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            with self.assertRaises(PermissionError):
                OpenRouterVideoGenerator(Path(temp)).generate("cinematic Gima video", consent=True)
            urlopen.assert_not_called()

    def test_huggingface_video_generator_uses_inference_client(self):
        class FakeClient:
            def __init__(self, provider, api_key):
                self.provider = provider
                self.api_key = api_key

            def text_to_video(self, prompt, model):
                self.prompt = prompt
                self.model = model
                return b"mp4 bytes"

        class FakeHub:
            InferenceClient = FakeClient

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ", {"HF_TOKEN": "test-hf", "CLOUD_ALLOWED": "true"}, clear=True
        ), patch("human_ai.services.importlib.import_module", return_value=FakeHub):
            result = HuggingFaceVideoGenerator(Path(temp)).generate(
                "A young man walking on the street",
                model="Wan-AI/Wan2.2-TI2V-5B",
                provider="replicate",
                consent=True,
            )
            output = Path(str(result["output_path"]))
            manifest = json.loads(Path(str(result["manifest_path"])).read_text(encoding="utf-8"))
            self.assertEqual(output.read_bytes(), b"mp4 bytes")
            self.assertEqual(manifest["provider"], "huggingface")
            self.assertEqual(manifest["inference_provider"], "replicate")
            self.assertEqual(manifest["model"], "Wan-AI/Wan2.2-TI2V-5B")

    def test_huggingface_video_generator_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"HF_TOKEN": "test-hf"}, clear=True):
            with self.assertRaises(PermissionError):
                HuggingFaceVideoGenerator(Path(temp)).generate("video prompt", consent=True)

    def test_external_music_api_requires_cloud_allowed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ",
            {"HUGGINGFACE_API_KEY": "test-hf", "GIMA_MUSICGEN_ENDPOINT_URL": "https://hf.example/musicgen"},
            clear=True,
        ), patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(PermissionError):
                ExternalMusicApiGenerator(Path(temp)).generate("cinematic song", consent=True)
            urlopen.assert_not_called()

    def test_external_music_api_writes_huggingface_binary_audio(self):
        class Headers:
            def get_content_type(self):
                return "audio/wav"

        class Response:
            headers = Headers()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"RIFFfake-wave"

        def fake_urlopen(request, timeout=0):
            self.assertEqual(request.full_url, "https://hf.example/musicgen")
            self.assertEqual(request.headers["Authorization"], "Bearer test-hf")
            payload = json.loads(request.data.decode("utf-8"))
            self.assertIn("cinematic song", payload["inputs"])
            self.assertEqual(payload["parameters"]["duration"], 12)
            return Response()

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ",
            {
                "HUGGINGFACE_API_KEY": "test-hf",
                "GIMA_MUSICGEN_ENDPOINT_URL": "https://hf.example/musicgen",
                "CLOUD_ALLOWED": "true",
            },
            clear=True,
        ), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            project = ExternalMusicApiGenerator(Path(temp)).generate(
                "cinematic song",
                lyrics="owned lyrics",
                duration_seconds=12,
                consent=True,
            )
            self.assertEqual(project.output_path.read_bytes(), b"RIFFfake-wave")
            manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["provider"], "huggingface_musicgen")
            self.assertEqual(manifest["response_summary"]["body_bytes"], len(b"RIFFfake-wave"))
            self.assertIn("owned lyrics", project.prompt_path.read_text(encoding="utf-8"))

    def test_external_music_api_accepts_json_base64_audio(self):
        class Headers:
            def get_content_type(self):
                return "application/json"

        class Response:
            headers = Headers()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({"audio_base64": base64.b64encode(b"audio").decode("ascii"), "api_key": "secret"}).encode("utf-8")

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ",
            {
                "GIMA_SUNO_API_BASE_URL": "https://music.example",
                "SUNO_API_KEY": "test-suno",
                "CLOUD_ALLOWED": "true",
            },
            clear=True,
        ), patch("urllib.request.urlopen", return_value=Response()):
            project = ExternalMusicApiGenerator(Path(temp)).generate(
                "pop song",
                provider="suno_compatible",
                consent=True,
            )
            self.assertEqual(project.output_path.read_bytes(), b"audio")
            manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["provider"], "suno_compatible")
            self.assertEqual(manifest["response_summary"]["json"]["api_key"], "[redacted]")

    def test_external_music_api_uses_waivepulse_local_without_cloud_allowed(self):
        calls = []

        class Headers:
            def __init__(self, content_type):
                self.content_type = content_type

            def get_content_type(self):
                return self.content_type

        class Response:
            def __init__(self, body, content_type="application/json"):
                self.body = body
                self.headers = Headers(content_type)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                if isinstance(self.body, bytes):
                    return self.body
                return json.dumps(self.body).encode("utf-8")

        def fake_urlopen(request, timeout=0):
            url = request.full_url if hasattr(request, "full_url") else str(request)
            calls.append(url)
            if url == "http://127.0.0.1:7861/model-status":
                return Response({"ready": True, "components": {"HeartMuLaGen": True}, "gpu": {"available": True}})
            if url == "http://127.0.0.1:7861/generate":
                payload = json.loads(request.data.decode("utf-8"))
                self.assertEqual(payload["tags"], "pop,piano,upbeat")
                self.assertIn("[Verse]", payload["lyrics"])
                return Response({"job_id": "abc12345"})
            if url == "http://127.0.0.1:7861/status/abc12345":
                return Response({"status": "done", "file": "/outputs/song_abc12345.mp3", "title": "Song"})
            if url == "http://127.0.0.1:7861/outputs/song_abc12345.mp3":
                return Response(b"mp3-bytes", "audio/mpeg")
            raise AssertionError(url)

        lyrics = "[Verse]\nHello world\n[Chorus]\nSing with Gima"
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {}, clear=True), patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            project = ExternalMusicApiGenerator(Path(temp)).generate(
                "pop,piano,upbeat",
                provider="waivepulse_local",
                lyrics=lyrics,
                duration_seconds=10,
                consent=True,
            )
            self.assertEqual(project.output_path.read_bytes(), b"mp3-bytes")
            manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["provider"], "waivepulse_local")
            self.assertEqual(manifest["response_summary"]["waivepulse_job"]["status"], "done")
        self.assertIn("http://127.0.0.1:7861/generate", calls)

    def test_lip_sync_planner_requires_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            face = root / "face.jpg"
            audio.write_bytes(b"fake mp3")
            face.write_bytes(b"fake jpg")
            with self.assertRaises(PermissionError):
                LipSyncPlanner(root / "out").create_project(audio, face, "sing", consent=False)

    def test_lip_sync_planner_creates_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            face = root / "face.jpg"
            audio.write_bytes(b"fake mp3")
            face.write_bytes(b"fake jpg")
            project = LipSyncPlanner(root / "out").create_project(
                audio,
                face,
                "make a respectful lip sync performance",
                consent=True,
            )
            self.assertTrue(project.manifest_path.exists())
            self.assertTrue(project.timing_path.exists())
            self.assertTrue(project.backend_path.exists())
            self.assertTrue(project.eval_path.exists())
            text = project.manifest_path.read_text(encoding="utf-8")
            self.assertIn("make a respectful lip sync performance", text)
            self.assertIn(str(audio.resolve()), text)
            self.assertIn(str(face.resolve()), text)
            self.assertIn("100% lip-sync accuracy cannot be guaranteed", text)
            self.assertIn("mouth open/close", project.timing_path.read_text(encoding="utf-8"))
            self.assertIn("Wav2Lip", project.backend_path.read_text(encoding="utf-8"))
            self.assertIn("mouth_timing", project.eval_path.read_text(encoding="utf-8"))

    def test_lip_sync_planner_keeps_long_song_segments_under_eight_seconds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            face = root / "face.jpg"
            audio.write_bytes(b"fake mp3")
            face.write_bytes(b"fake jpg")
            planner = LipSyncPlanner(root / "out")
            with patch.object(
                planner,
                "_media_metadata",
                side_effect=[{"format": {"duration": "353.88"}}, {"streams": []}],
            ):
                project = planner.create_project(audio, face, "long song", consent=True)

            timing = project.timing_path.read_text(encoding="utf-8")
            self.assertIn("### Segment 45:", timing)
            self.assertNotIn("### Segment 46:", timing)

    def test_local_music_video_renderer_requires_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake mp3")
            with self.assertRaises(PermissionError):
                LocalMusicVideoRenderer(root / "out").render(audio, "make video", consent=False)

    def test_local_music_video_renderer_creates_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake mp3")

            def fake_run(command, **kwargs):
                output = Path(command[-1])
                output.write_bytes(b"fake mp4")
                return None

            with patch("human_ai.services.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
                "human_ai.services.subprocess.run", side_effect=fake_run
            ):
                project = LocalMusicVideoRenderer(root / "out").render(
                    audio,
                    "make a waveform music video",
                    style="waveform",
                    consent=True,
                )

            self.assertTrue(project.output_path.exists())
            text = project.manifest_path.read_text(encoding="utf-8")
            self.assertIn("local_music_video", text)
            self.assertIn("make a waveform music video", text)
            self.assertIn(str(audio.resolve()), text)

    def test_frontier_video_planner_creates_prompt_ladder_and_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake mp3")

            project = FrontierVideoPlanner(root / "out").plan(
                "romantic cinematic Sinhala music video",
                audio=audio,
                target="seedance",
                duration_seconds=12,
            )

            self.assertTrue(project.manifest_path.exists())
            self.assertTrue(project.prompt_ladder_path.exists())
            self.assertTrue(project.backend_report_path.exists())
            self.assertTrue(project.eval_rubric_path.exists())
            self.assertIn("temporal consistency", project.prompt_ladder_path.read_text(encoding="utf-8").casefold())
            self.assertIn("Veo/Seedance", project.eval_rubric_path.read_text(encoding="utf-8"))
            self.assertIn(str(audio.resolve()), project.manifest_path.read_text(encoding="utf-8"))

    def test_local_image_music_video_renderer_creates_slideshow_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            image = root / "image.jpg"
            audio.write_bytes(b"fake mp3")
            image.write_bytes(b"fake jpg")

            def fake_run(command, **kwargs):
                output = Path(command[-1])
                output.write_bytes(b"fake mp4")
                return None

            with patch("human_ai.services.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
                "human_ai.services.subprocess.run", side_effect=fake_run
            ), patch("human_ai.services.LipSyncPlanner._media_metadata", return_value={"format": {"duration": "4.0"}}):
                project = LocalImageMusicVideoRenderer(root / "out").render(
                    audio,
                    [image],
                    "make an image music video",
                    aspect="9:16",
                    max_duration_seconds=4,
                    consent=True,
                )

            self.assertTrue(project.output_path.exists())
            text = project.manifest_path.read_text(encoding="utf-8")
            self.assertIn("local_image_music_video", text)
            self.assertIn("make an image music video", text)
            self.assertIn("720x1280", text)
            self.assertIn("render_duration_seconds", text)

    def test_local_music_video_director_creates_freebeat_style_storyboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake mp3")
            fake_metadata = {"format": {"duration": "24.0"}}
            with patch("human_ai.services.LipSyncPlanner._media_metadata", return_value=fake_metadata):
                project = LocalMusicVideoDirector(root / "out").plan(
                    audio,
                    "neon city dance story",
                    mode="lyrics",
                    style="anime",
                    aspect="9:16",
                    lyrics="line one\nline two",
                )

            self.assertTrue(project.storyboard_path.exists())
            self.assertTrue(project.manifest_path.exists())
            text = project.manifest_path.read_text(encoding="utf-8")
            self.assertIn("freebeat_style_local_music_video_director", text)
            self.assertIn("neon city dance story", text)
            self.assertIn("9:16", text)

    def test_advanced_video_song_creates_emotion_camera_and_pitch_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            image = root / "singer.jpg"
            audio.write_bytes(b"audio")
            image.write_bytes(b"image")
            renderer = AdvancedVideoSongRenderer(root / "out")
            with patch("human_ai.services.shutil.which", return_value="/usr/bin/ffmpeg"), patch.object(
                renderer, "_duration", return_value=12.0
            ), patch.object(
                renderer,
                "_audio_analysis",
                return_value=[
                    {"index": 1, "start": 0.0, "end": 4.0, "rms_db": -20.0, "peak_db": -4.0, "zero_crossing_rate": 0.04, "energy": 0.61, "pitch_activity": 0.33},
                    {"index": 2, "start": 4.0, "end": 8.0, "rms_db": -12.0, "peak_db": -1.0, "zero_crossing_rate": 0.09, "energy": 0.83, "pitch_activity": 0.75},
                    {"index": 3, "start": 8.0, "end": 12.0, "rms_db": -30.0, "peak_db": -9.0, "zero_crossing_rate": 0.02, "energy": 0.22, "pitch_activity": 0.17},
                ],
            ), patch.object(renderer, "_render") as render, patch(
                "human_ai.services.LipSyncPlanner._media_metadata", return_value={"format": {"duration": "12"}}
            ):
                render.side_effect = lambda audio_path, images, scenes, output, aspect: output.write_bytes(b"mp4")
                project = renderer.render(
                    audio,
                    [image],
                    "romantic movie performance",
                    lyrics="first line\nsecond line",
                    max_duration_seconds=12,
                    consent=True,
                )
            manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["kind"], "advanced_local_video_song")
            self.assertEqual(manifest["scene_count"], 3)
            self.assertIn("camera", manifest["scenes"][0])
            self.assertIn("effects", manifest["scenes"][0])
            self.assertIn("film_grain", manifest["scenes"][0]["effects"])
            self.assertIn("pitch_activity", manifest["scenes"][0])
            self.assertIn("human emotion", project.prompt_pack_path.read_text(encoding="utf-8"))
            self.assertTrue(project.output_path.exists())

    def test_neural_lip_sync_status_reports_missing_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            renderer = NeuralLipSyncRenderer(root / "out", root / "SadTalker")
            status = renderer.status()
            self.assertFalse(status["ready"])
            self.assertIn("inference.py", status["missing"])

    def test_neural_lip_sync_status_rejects_incomplete_face_weights(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backend = root / "SadTalker"
            (backend / "checkpoints").mkdir(parents=True)
            (backend / "checkpoints" / "SadTalker_V0.0.2_256.safetensors").write_bytes(b"checkpoint")
            (backend / "inference.py").write_text("print('ok')\n", encoding="utf-8")
            (backend / "gfpgan" / "weights").mkdir(parents=True)
            (backend / "gfpgan" / "weights" / "detection_Resnet50_Final.pth").write_bytes(b"partial")
            (backend / "gfpgan" / "weights" / "alignment_WFLW_4HG.pth").write_bytes(b"partial")
            renderer = NeuralLipSyncRenderer(root / "out", backend, python_path=Path(sys.executable))
            status = renderer.status()
            self.assertFalse(status["ready"])
            self.assertIn("complete face detection/alignment weights", status["missing"])

    def test_open_source_video_api_renderer_patches_workflow_and_downloads_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflow = root / "workflow.json"
            workflow.write_text(
                json.dumps(
                    {
                        "1": {"inputs": {"text": "{{PROMPT}}"}},
                        "2": {"inputs": {"image": "{{IMAGE}}", "width": "{{WIDTH}}", "length": "{{FRAMES}}"}},
                    }
                ),
                encoding="utf-8",
            )
            image = root / "input.jpg"
            image.write_bytes(b"jpg")
            calls = []

            class Response:
                def __init__(self, payload):
                    self.payload = payload

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    if isinstance(self.payload, bytes):
                        return self.payload
                    return json.dumps(self.payload).encode("utf-8")

            def fake_urlopen(request, timeout=0):
                url = getattr(request, "full_url", request)
                calls.append(str(url))
                if str(url).endswith("/upload/image"):
                    return Response({"name": "uploaded.jpg"})
                if str(url).endswith("/prompt"):
                    body = json.loads(request.data.decode("utf-8"))
                    self.assertEqual(body["prompt"]["1"]["inputs"]["text"], "cinematic video")
                    self.assertEqual(body["prompt"]["2"]["inputs"]["image"], "uploaded.jpg")
                    self.assertEqual(body["prompt"]["2"]["inputs"]["length"], "9")
                    return Response({"prompt_id": "abc"})
                if "/history/abc" in str(url):
                    return Response({"abc": {"outputs": {"7": {"videos": [{"filename": "result.mp4", "subfolder": "", "type": "output"}]}}}})
                if "/view?" in str(url):
                    return Response(b"mp4")
                raise AssertionError(url)

            renderer = OpenSourceVideoApiRenderer(root / "out")
            with patch("human_ai.services.urllib.request.urlopen", side_effect=fake_urlopen):
                project = renderer.render(workflow, "cinematic video", image=image, frames=9, consent=True)

            self.assertTrue(project.output_path.exists())
            self.assertEqual(project.output_path.read_bytes(), b"mp4")
            manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["backend"], "ComfyUI")
            self.assertEqual(manifest["prompt_id"], "abc")
            self.assertTrue(any("/prompt" in call for call in calls))

    def test_video_quality_evaluator_scores_manifest_and_streams(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "video.mp4"
            manifest = root / "manifest.json"
            video.write_bytes(b"fake mp4")
            manifest.write_text(
                '{"prompt":"make a video","renderer":"ffmpeg"}',
                encoding="utf-8",
            )
            ffprobe_json = (
                b'{"streams":[{"codec_type":"video","width":1280,"height":720},'
                b'{"codec_type":"audio","codec_name":"aac"}],"format":{"duration":"3.0","size":"1000"}}'
            )

            with patch("human_ai.services.shutil.which", return_value="/usr/bin/ffprobe"), patch(
                "human_ai.services.subprocess.run"
            ) as run:
                run.return_value.stdout = ffprobe_json.decode("utf-8")
                result = VideoQualityEvaluator(root / "eval").evaluate(video, manifest)

            self.assertEqual(result.score, 1.0)
            text = result.report_path.read_text(encoding="utf-8")
            self.assertIn("veo_style_local_video_eval", text)
            self.assertIn("audio_stream_present", text)

    def test_vibe_coding_agent_creates_offline_plan_in_working_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "human_ai").mkdir()
            (root / "human_ai" / "gima.py").write_text("def cli():\n    pass\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_gima.py").write_text("def test_cli():\n    pass\n", encoding="utf-8")
            memory = MemoryStore(root / ".human-ai")

            plan = VibeCodingAgent(root, root / ".human-ai", memory).plan(
                "add vibe coding cli tests",
                max_files=5,
            )

            self.assertTrue(plan.plan_path.exists())
            self.assertTrue(plan.patch_skeleton_path.exists())
            self.assertTrue(plan.snapshot_path.exists())
            self.assertTrue((plan.update_request.working_copy / "human_ai" / "gima.py").exists())
            text = plan.plan_path.read_text(encoding="utf-8")
            self.assertIn("Offline Vibe Coding Plan", text)
            self.assertIn("human_ai/gima.py", text)
            self.assertIn("tests/test_gima.py", text)
            rows = [row for row in memory.list_by_status("review") if row["category"] == "code"]
            self.assertEqual(rows[0]["subcategory"], "vibe_agent")

    def test_vibe_coding_agent_implements_only_in_copy_and_runs_tests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "human_ai").mkdir()
            live_file = root / "human_ai" / "gima.py"
            live_file.write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_gima.py").write_text("import unittest\n", encoding="utf-8")
            memory = MemoryStore(root / ".human-ai")

            def run_command(command, **kwargs):
                if command[0] == "/usr/bin/codex":
                    (Path(kwargs["cwd"]) / "human_ai" / "gima.py").write_text("VALUE = 2\n", encoding="utf-8")
                    return subprocess.CompletedProcess(command, 0, "implemented", "")
                return subprocess.CompletedProcess(command, 0, "tests passed", "")

            with patch("human_ai.vibe_code.shutil.which", return_value="/usr/bin/codex"), patch(
                "human_ai.vibe_code.subprocess.run", side_effect=run_command
            ):
                execution = VibeCodingAgent(root, root / ".human-ai", memory).implement("change value")

            self.assertEqual(live_file.read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(execution.status, "implemented_pending_review")
            self.assertTrue(execution.tests_passed)
            self.assertEqual(execution.changed_files, ["human_ai/gima.py"])
            self.assertIn("+VALUE = 2", execution.patch_path.read_text(encoding="utf-8"))
            manifest = execution.plan.update_request.manifest_path.read_text(encoding="utf-8")
            self.assertIn('"status": "implemented_pending_review"', manifest)


if __name__ == "__main__":
    unittest.main()
