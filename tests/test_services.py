import json
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
    FrontierVideoPlanner,
    LipSyncPlanner,
    LocalImageMusicVideoRenderer,
    LocalMusicVideoDirector,
    LocalMusicVideoRenderer,
    NeuralLipSyncRenderer,
    OpenSourceVideoApiRenderer,
    SandboxedCodeRunner,
    SafeToolRunner,
    TeacherModelClient,
    VideoQualityEvaluator,
    WebImporter,
)
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

    def test_teacher_model_requires_known_provider(self):
        with self.assertRaises(ValueError):
            TeacherModelClient(Config()).ask("unknown", "hello")

    def test_openai_response_text_is_parsed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"output_text":"teacher answer"}'
            )
            self.assertEqual(client.ask("chatgpt", "hello"), "teacher answer")

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

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}), patch("urllib.request.urlopen", side_effect=fake_urlopen):
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
            if body["model"] == "openai/gpt-5.5":
                raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, io.BytesIO(b'{"error":"not found"}'))
            self.assertEqual(body["model"], "openai/gpt-4o")
            return Response()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-router"}), patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            answer = client.ask("openrouter", "hello")

        self.assertIn("router fallback answer", answer)
        self.assertIn("[OpenRouter model used: openai/gpt-4o]", answer)
        self.assertEqual(len(calls), 2)

    def test_gemini_response_text_is_parsed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"candidates":[{"content":{"parts":[{"text":"gemini answer"}]}}]}'
            )
            self.assertEqual(client.ask("gemini", "hello"), "gemini answer")

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
            audio = root / "song.wav"
            audio.write_bytes(b"fake wav")
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
            with patch.object(renderer, "_duration", return_value=12.0), patch.object(
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
