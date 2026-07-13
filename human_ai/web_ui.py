from __future__ import annotations

import csv
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .agent import Agent
from .agent_registry import AgentRegistry
from .ai_task_map import AITaskMapStore
from .artifacts import ChatArtifactEngine, _extract_weather_location
from .brain import BrainServer
from .brain_index import rebuild_brain_csv
from .capabilities import CapabilityStore
from .config import Config
from .free_llm_planner import free_llm_plan
from .huggingface_learning import HuggingFaceLearner, extract_huggingface_url
from .local_ai_stack import local_ai_stack_payload
from .memory import Record
from .model_council import ModelCouncil
from .model_levels import ModelLevelManager
from .openrouter_paid_planner import paid_openrouter_plan
from .openrouter_router import OpenRouterTaskRouter, RoutingRequest
from .public_apis import PublicApiCatalogStore
from .quota import FreeQuotaTracker
from .readers import read_file
from .secrets import save_teacher_secret, teacher_secret_status
from .self_update import SelfUpdateManager
from .services import AdvancedVideoSongRenderer, ExternalMusicApiGenerator, HuggingFaceFeatureExtractor, HuggingFaceImageGenerator, HuggingFaceVideoGenerator, LipSyncPlanner, LocalImageMusicVideoRenderer, LocalMusicVideoDirector, LocalMusicVideoRenderer, LocalSongSketcher, NeuralLipSyncRenderer, OpenAIImageGenerator, OpenRouterCatalog, OpenRouterSpeechGenerator, OpenRouterVideoGenerator, OpenSourceVideoApiRenderer, SandboxedCodeRunner, TransformersTextGenerator, Voice, WhatsAppMessenger, cloud_allowed
from .system_doctor import build_doctor_report, latest_ai_era_requirements_agent, latest_area_agent_supervisor, latest_daily_improvement_agent
from .vibe_code import VibeCodingAgent


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#050608">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Gima">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/api/app-icon.png" type="image/png">
  <link rel="apple-touch-icon" href="/api/app-icon.png">
  <title>Gima Chat</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #090a0c;
      --bg-soft: #0d0f13;
      --panel: #151820;
      --panel-2: #1b202a;
      --panel-3: #20242d;
      --line: #303642;
      --line-soft: rgba(255, 255, 255, 0.07);
      --text: #f1f3f7;
      --muted: #a7afba;
      --muted-2: #c0c6cf;
      --accent: #7f88ff;
      --accent-2: #6fc7f7;
      --user: #252b35;
      --assistant: #171c26;
      --danger: #ff6b6b;
      --ok: #46f2a8;
      --ease: cubic-bezier(.2, .8, .2, 1);
      --glow: 0 18px 52px rgba(111, 199, 247, 0.09), 0 14px 34px rgba(127, 136, 255, 0.11);
      --font-xs: 11px;
      --font-sm: 12px;
      --font-md: 14px;
      --font-lg: 16px;
      --font-xl: 22px;
      --font-hero: 30px;
    }
    * { box-sizing: border-box; }
    *::-webkit-scrollbar { width: 10px; height: 10px; }
    *::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.025); }
    *::-webkit-scrollbar-thumb {
      background: rgba(167, 175, 186, 0.26);
      border-radius: 999px;
      border: 2px solid rgba(9, 10, 12, 0.66);
    }
    *::-webkit-scrollbar-thumb:hover { background: rgba(167, 175, 186, 0.42); }
    :focus-visible {
      outline: 2px solid rgba(111, 199, 247, 0.70);
      outline-offset: 3px;
    }
    body {
      margin: 0;
      min-height: 100vh;
      overflow: hidden;
      background:
        linear-gradient(135deg, rgba(127, 136, 255, 0.055), transparent 28rem),
        radial-gradient(circle at top left, rgba(127, 136, 255, 0.12), transparent 34rem),
        radial-gradient(circle at bottom right, rgba(111, 199, 247, 0.09), transparent 30rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .app {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 320px;
      min-height: 100vh;
      height: 100vh;
    }
    aside, .workspace {
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.040), transparent 18rem),
        rgba(18, 21, 28, 0.90);
      padding: 18px;
      backdrop-filter: blur(18px);
      overflow: auto;
      height: 100vh;
    }
    aside { border-right: 1px solid var(--line); }
    .workspace {
      border-left: 1px solid var(--line);
      overflow: auto;
      max-height: 100vh;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 22px;
    }
    .logo {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      background-image: url("/api/app-icon.png");
      background-size: cover;
      background-position: center;
      color: white;
      font-weight: 800;
      box-shadow: var(--glow);
      overflow: hidden;
      text-indent: -999px;
    }
    h1, h2, p { margin: 0; }
    h1 { font-size: 20px; letter-spacing: 0.2px; }
    .subtitle { color: var(--muted); font-size: 13px; margin-top: 3px; }
    .section-label {
      color: var(--muted-2);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin: 18px 0 8px;
    }
    .card {
      border: 1px solid var(--line-soft);
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.020)),
        rgba(24, 28, 37, 0.76);
      border-radius: 20px;
      padding: 14px;
      margin: 12px 0;
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.18);
      transition: border-color 180ms var(--ease), background 180ms var(--ease), transform 180ms var(--ease);
    }
    .card:hover {
      border-color: rgba(127, 136, 255, 0.24);
      transform: translateY(-1px);
    }
    .status-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      font-size: 13px;
      color: var(--muted);
      margin: 8px 0;
    }
    .pill {
      border: 1px solid rgba(0, 212, 255, 0.35);
      color: #b9f3ff;
      background: rgba(0, 212, 255, 0.08);
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      white-space: nowrap;
    }
    .quick button, .search button {
      width: 100%;
      margin-top: 8px;
      border: 1px solid var(--line);
      background: rgba(18, 22, 30, 0.84);
      color: var(--text);
      border-radius: 14px;
      padding: 10px 12px;
      text-align: left;
      cursor: pointer;
    }
    .quick button:hover, .search button:hover {
      border-color: var(--accent);
      background: rgba(127, 136, 255, 0.12);
      transform: translateY(-1px);
    }
    .search input, .tool-input, .tool-select {
      width: 100%;
      background: rgba(10, 12, 16, 0.74);
      border: 1px solid var(--line-soft);
      border-radius: 14px;
      color: var(--text);
      padding: 10px 12px;
      outline: none;
      transition: border-color 160ms var(--ease), background 160ms var(--ease), box-shadow 160ms var(--ease);
    }
    .search input:focus, .tool-input:focus, .tool-select:focus, .tool-textarea:focus {
      border-color: rgba(111, 199, 247, 0.54);
      box-shadow: 0 0 0 4px rgba(111, 199, 247, 0.08);
      background: rgba(13, 16, 21, 0.86);
    }
    .tool-input, .tool-select { margin-top: 8px; }
    .tool-textarea {
      width: 100%;
      min-height: 78px;
      margin-top: 8px;
      background: rgba(10, 12, 16, 0.74);
      border: 1px solid var(--line-soft);
      border-radius: 14px;
      color: var(--text);
      padding: 10px 12px;
      outline: none;
      resize: vertical;
      font: inherit;
      transition: border-color 160ms var(--ease), background 160ms var(--ease), box-shadow 160ms var(--ease);
    }
    .tool-button {
      width: 100%;
      margin-top: 8px;
      border: 1px solid rgba(124, 92, 255, 0.45);
      background: linear-gradient(135deg, rgba(127, 136, 255, 0.82), rgba(111, 199, 247, 0.70));
      color: var(--text);
      border-radius: 14px;
      padding: 11px 12px;
      text-align: center;
      cursor: pointer;
      font-weight: 700;
    }
    .tool-button:disabled { opacity: 0.55; cursor: wait; }
    button { transition: transform 160ms var(--ease), border-color 160ms var(--ease), background 160ms var(--ease), opacity 160ms var(--ease); }
    .results {
      margin-top: 10px;
      max-height: 220px;
      overflow: auto;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .tool-output {
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .code-report {
      display: grid;
      gap: 12px;
      white-space: normal;
    }
    .code-report-head,
    .code-metrics,
    .code-step {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .code-report-head {
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
    }
    .code-report-title { color: var(--text); font-size: 15px; font-weight: 820; }
    .code-status {
      border: 1px solid rgba(111, 199, 247, 0.30);
      border-radius: 999px;
      padding: 4px 8px;
      color: #dff8ff;
      background: rgba(111, 199, 247, 0.10);
      font-size: 11px;
      font-weight: 800;
    }
    .code-status.failed { border-color: rgba(255, 120, 120, 0.35); color: #ffc7c7; background: rgba(255, 80, 80, 0.10); }
    .code-metrics { justify-content: flex-start; flex-wrap: wrap; }
    .code-metric {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 7px 9px;
      background: rgba(255, 255, 255, 0.035);
      color: var(--muted-2);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .code-steps { display: grid; gap: 6px; }
    .code-step { justify-content: flex-start; color: var(--muted-2); }
    .code-step-mark { color: #91e6b8; font-weight: 900; }
    .code-step-mark.failed { color: #ff9f9f; }
    .code-section-title { margin: 2px 0 6px; color: var(--text); font-weight: 800; }
    .changed-file-list { display: flex; flex-wrap: wrap; gap: 6px; }
    .changed-file {
      border: 1px solid rgba(124, 92, 255, 0.25);
      border-radius: 9px;
      padding: 5px 7px;
      color: #e7e2ff;
      background: rgba(124, 92, 255, 0.08);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 11px;
    }
    .code-label {
      position: absolute;
      top: 10px;
      left: 12px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .terminal-output {
      margin: 0;
      min-height: 72px;
      max-height: 360px;
      overflow: auto;
      border: 1px solid rgba(145, 230, 184, 0.20);
      border-radius: 12px;
      padding: 12px;
      background: #050706;
      color: #bff7d4;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .file-list {
      margin-top: 10px;
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .file-chip {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px;
      background: rgba(12, 14, 18, 0.58);
      overflow-wrap: anywhere;
    }
    main {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-width: 0;
      height: 100vh;
      background:
        radial-gradient(circle at top, rgba(111, 199, 247, 0.060), transparent 28rem),
        linear-gradient(180deg, rgba(127, 136, 255, 0.045), transparent 18rem),
        rgba(9, 10, 12, 0.86);
    }
    header {
      border-bottom: 1px solid var(--line);
      padding: 18px max(18px, calc((100vw - 760px) / 2));
      background: rgba(9, 10, 12, 0.82);
      backdrop-filter: blur(16px);
    }
    .chat {
      overflow: auto;
      padding: 28px 18px 34px;
      scroll-behavior: smooth;
    }
    .message {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      gap: 14px;
      width: min(100%, 780px);
      margin: 0 auto 18px;
      animation: messageIn 180ms var(--ease);
    }
    @keyframes messageIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .avatar {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: var(--panel-2);
      color: var(--muted);
      font-weight: 800;
      border: 1px solid var(--line);
    }
    .bubble {
      position: relative;
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 16px 18px;
      line-height: 1.55;
      white-space: pre-wrap;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.015)),
        var(--assistant);
      box-shadow: 0 18px 38px rgba(0, 0, 0, 0.20);
    }
    .user .bubble { background: var(--user); }
    .assistant .avatar {
      background: linear-gradient(135deg, rgba(124, 92, 255, 0.26), rgba(0, 212, 255, 0.14));
      color: white;
    }
    .composer {
      padding: 14px 18px 18px;
      border-top: 1px solid var(--line);
      background: rgba(10, 11, 14, 0.94);
      backdrop-filter: blur(16px);
    }
    form {
      display: flex;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.045), transparent),
        rgba(15, 17, 22, 0.95);
      padding: 10px;
      width: min(100%, 780px);
      margin: 0 auto;
      box-shadow: var(--glow);
    }
    textarea {
      flex: 1;
      min-height: 48px;
      max-height: 180px;
      resize: none;
      overflow: hidden;
      border: 0;
      outline: 0;
      color: var(--text);
      background: transparent;
      font: inherit;
      padding: 10px;
    }
    .attach-inline {
      align-self: end;
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border: 1px solid var(--line);
      border-radius: 14px;
      color: var(--text);
      background: rgba(27, 32, 42, 0.88);
      cursor: pointer;
      font-weight: 900;
    }
    .attach-inline:hover { border-color: var(--accent-2); transform: translateY(-1px); }
    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
    .send {
      align-self: end;
      border: 0;
      border-radius: 14px;
      color: white;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      padding: 12px 18px;
      min-width: 78px;
      font-weight: 700;
      cursor: pointer;
    }
    .send:disabled { opacity: 0.55; cursor: wait; }
    .send:hover, .tool-button:hover, .mini-button:hover { transform: translateY(-1px); }
    .response-meta {
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 10px;
    }
    .bubble a {
      color: #7ee7ff;
      font-weight: 750;
      text-decoration: none;
    }
    .bubble a:hover { text-decoration: underline; }
    .bubble table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      overflow: hidden;
      border-radius: 14px;
      display: block;
      max-width: 100%;
      overflow-x: auto;
    }
    .bubble th, .bubble td {
      border: 1px solid rgba(255, 255, 255, 0.10);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
      white-space: normal;
    }
    .bubble th {
      background: rgba(124, 92, 255, 0.16);
      color: #ffffff;
    }
    .artifact-list {
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }
    .artifact-link {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      border: 1px solid rgba(0, 212, 255, 0.20);
      background: rgba(0, 212, 255, 0.07);
      border-radius: 14px;
      padding: 9px 11px;
    }
    .file-card-list {
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }
    .file-card {
      display: grid;
      gap: 7px;
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 14px;
      padding: 10px;
      background: rgba(255, 255, 255, 0.045);
      color: var(--muted-2);
      font-size: var(--font-sm);
      overflow-wrap: anywhere;
    }
    .file-card-main {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .file-name {
      color: var(--text);
      font-weight: 780;
    }
    .file-path {
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: var(--font-xs);
    }
    .file-kind {
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(111, 199, 247, 0.24);
      border-radius: 999px;
      padding: 2px 7px;
      color: #bfefff;
      background: rgba(111, 199, 247, 0.075);
      font-size: var(--font-xs);
      font-weight: 760;
      white-space: nowrap;
    }
    .download-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      border: 1px solid rgba(111, 199, 247, 0.26);
      border-radius: 999px;
      padding: 6px 9px;
      background: rgba(111, 199, 247, 0.08);
      color: #dff8ff;
      font-size: var(--font-xs);
      font-weight: 780;
      text-decoration: none;
      white-space: nowrap;
    }
    .download-button:hover {
      border-color: rgba(111, 199, 247, 0.48);
      background: rgba(111, 199, 247, 0.13);
      text-decoration: none;
    }
    .copy-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    .copy-button {
      border: 1px solid rgba(124, 92, 255, 0.30);
      background: rgba(124, 92, 255, 0.12);
      color: #f5f7fb;
      border-radius: 999px;
      padding: 7px 10px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 750;
    }
    .copy-button:hover {
      background: rgba(0, 212, 255, 0.12);
      border-color: rgba(0, 212, 255, 0.38);
    }
    .code-wrap {
      position: relative;
      margin: 12px 0;
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 14px;
      background: rgba(5, 6, 8, 0.72);
      overflow: hidden;
    }
    .code-wrap pre {
      margin: 0;
      padding: 40px 12px 12px;
      overflow: auto;
      color: #e7edf6;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre;
    }
    .code-copy {
      position: absolute;
      top: 8px;
      right: 8px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      background: rgba(31, 36, 46, 0.92);
      color: var(--text);
      border-radius: 999px;
      padding: 6px 10px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 800;
    }
    .progress-shell {
      width: 100%;
      height: 8px;
      margin-top: 8px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      overflow: hidden;
    }
    .progress-bar {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      transition: width 300ms ease;
    }
    .composer-tools {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      width: min(100%, 780px);
      margin: 0 auto 10px;
    }
    .composer-tools input[type="file"] {
      max-width: 220px;
      color: var(--muted);
    }
    .drawer-backdrop {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: none;
      background: rgba(0, 0, 0, 0.48);
      backdrop-filter: blur(4px);
    }
    body.show-left .drawer-backdrop,
    body.show-right .drawer-backdrop { display: block; }
    .nav-rail {
      position: fixed;
      inset: 0 auto 0 0;
      z-index: 35;
      width: 64px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
      padding: 24px 10px;
      background: rgba(9, 9, 10, 0.94);
      border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    .rail-spacer { flex: 1; }
    .rail-button {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border: 1px solid transparent;
      border-radius: 50%;
      color: #f4f4f5;
      background: transparent;
      cursor: pointer;
      font-size: 19px;
      font-weight: 850;
    }
    .rail-button:hover,
    .rail-button.active {
      border-color: rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.105);
    }
    .drawer-menu {
      display: grid;
      gap: 8px;
      margin: 18px 0;
    }
    .drawer-menu button {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      border: 0;
      border-radius: 14px;
      padding: 12px;
      color: var(--text);
      background: transparent;
      cursor: pointer;
      text-align: left;
      font-size: 16px;
      font-weight: 760;
    }
    .drawer-menu button:hover,
    .drawer-menu button.active {
      background: rgba(255, 255, 255, 0.105);
    }
    .menu-icon {
      display: grid;
      place-items: center;
      width: 26px;
      color: var(--muted-2);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .topbar {
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr) auto;
      align-items: center;
      gap: 14px;
    }
    .icon-button {
      display: grid;
      place-items: center;
      min-width: 44px;
      height: 44px;
      border: 1px solid transparent;
      border-radius: 15px;
      color: var(--text);
      background: transparent;
      cursor: pointer;
      font-weight: 850;
    }
    .icon-button:hover {
      border-color: var(--line);
      background: rgba(255, 255, 255, 0.055);
    }
    .empty-state {
      width: min(100%, 900px);
      margin: auto;
      padding: 18vh 18px 7vh;
      text-align: center;
    }
    .empty-state h2 {
      font-size: clamp(32px, 5vw, 52px);
      line-height: 1.05;
      letter-spacing: -0.04em;
    }
    .empty-state p {
      margin-top: 18px;
      color: var(--muted);
      font-size: clamp(18px, 2.4vw, 25px);
      font-weight: 650;
    }
    .chat.has-messages .empty-state { display: none; }
    .composer-bottom {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
    }
    .model-chip {
      display: inline-flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 7px;
      min-height: 34px;
      margin-left: auto;
      border-radius: 999px;
      padding: 7px 12px;
      color: #f4f4f5;
      background: rgba(64, 64, 67, 0.82);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.055);
      font-size: 13px;
      font-weight: 850;
    }
    .model-chip[hidden] { display: none; }
    .model-chip span {
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 999px;
      padding: 2px 7px;
      color: #f2f2f3;
      background: rgba(255, 255, 255, 0.065);
      font-weight: 760;
    }
    .route-preview {
      display: inline-flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 7px;
      min-height: 34px;
      border-radius: 999px;
      padding: 7px 12px;
      color: var(--muted-2);
      background: rgba(8, 12, 18, 0.74);
      border: 1px solid rgba(177, 222, 255, 0.18);
      font-size: 12px;
      font-weight: 820;
    }
    .route-preview[hidden] { display: none; }
    .route-preview strong { color: var(--text); }
    .route-preview span {
      border: 1px solid rgba(177, 222, 255, 0.22);
      border-radius: 999px;
      padding: 2px 7px;
      color: #f8fbff;
      background: rgba(155, 216, 255, 0.08);
    }
    .route-preview.local span:first-of-type {
      border-color: rgba(130, 255, 202, 0.38);
      background: rgba(130, 255, 202, 0.10);
    }
    .route-preview.cloud span:first-of-type {
      border-color: rgba(155, 216, 255, 0.46);
      background: rgba(155, 216, 255, 0.14);
    }
    .route-preview.blocked span:first-of-type {
      border-color: rgba(255, 198, 120, 0.44);
      background: rgba(255, 198, 120, 0.12);
    }
    .screen-record-button {
      min-width: 58px;
      height: 44px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--text);
      background: rgba(255, 255, 255, 0.055);
      cursor: pointer;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0.02em;
    }
    .screen-record-button.recording {
      color: #07111b;
      border-color: rgba(255, 255, 255, 0.66);
      background: linear-gradient(135deg, #ffffff, #bfe7ff 58%, #78c8ff);
      box-shadow: 0 0 30px rgba(155, 216, 255, 0.34);
    }
    .action-tray {
      width: min(100%, 980px);
      margin: 12px auto 0;
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding: 3px 2px 8px;
      scrollbar-width: thin;
    }
    .action-tray button {
      flex: 0 0 auto;
      border: 1px solid rgba(255, 255, 255, 0.075);
      border-radius: 999px;
      color: var(--muted-2);
      background: rgba(31, 34, 39, 0.72);
      padding: 9px 13px;
      cursor: pointer;
      font-weight: 780;
      white-space: nowrap;
    }
    .action-tray button:hover {
      color: var(--text);
      border-color: rgba(111, 199, 247, 0.30);
      background: rgba(111, 199, 247, 0.10);
      transform: translateY(-1px);
    }
    .add-sheet-backdrop {
      position: fixed;
      inset: 0;
      z-index: 50;
      display: none;
      background: rgba(0, 0, 0, 0.58);
      backdrop-filter: blur(3px);
    }
    .add-sheet {
      position: fixed;
      left: max(74px, calc((100vw - 1080px) / 2));
      right: max(18px, calc((100vw - 1080px) / 2));
      bottom: 18px;
      z-index: 55;
      display: none;
      max-height: min(72vh, 720px);
      overflow: auto;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 28px;
      padding: 24px;
      background: rgba(13, 13, 14, 0.98);
      box-shadow: 0 28px 90px rgba(0, 0, 0, 0.58);
    }
    body.show-add-sheet .add-sheet,
    body.show-add-sheet .add-sheet-backdrop { display: block; }
    .sheet-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 20px;
    }
    .sheet-title {
      font-size: 25px;
      font-weight: 850;
      letter-spacing: -0.02em;
    }
    .sheet-close {
      border: 0;
      background: transparent;
      color: var(--muted-2);
      cursor: pointer;
      font-size: 30px;
      line-height: 1;
    }
    .sheet-list {
      display: grid;
      gap: 4px;
    }
    .sheet-action {
      display: grid;
      grid-template-columns: 34px minmax(0, 1fr) auto;
      align-items: center;
      gap: 14px;
      width: 100%;
      min-height: 58px;
      border: 0;
      border-radius: 16px;
      padding: 11px 10px;
      color: var(--text);
      background: transparent;
      cursor: pointer;
      text-align: left;
      font: inherit;
    }
    .sheet-action:hover {
      background: rgba(255, 255, 255, 0.08);
    }
    .sheet-action[disabled] {
      opacity: 0.45;
      cursor: not-allowed;
    }
    .sheet-action b {
      display: block;
      font-size: 18px;
    }
    .sheet-action span {
      color: var(--muted);
      font-size: 13px;
    }
    .sheet-icon {
      display: grid;
      place-items: center;
      color: #f5f5f5;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 18px;
      font-weight: 850;
    }
    .mini-button {
      border: 1px solid var(--line);
      background: rgba(27, 32, 42, 0.92);
      color: var(--text);
      border-radius: 12px;
      padding: 9px 12px;
      cursor: pointer;
      font-weight: 650;
    }
    .attachment-pill {
      border: 1px solid rgba(0, 212, 255, 0.26);
      background: rgba(0, 212, 255, 0.08);
      color: #c8f6ff;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .folder-grid {
      display: grid;
      gap: 8px;
    }
    .folder-row {
      border: 1px solid var(--line-soft);
      border-radius: 14px;
      padding: 10px;
      background: rgba(10, 12, 16, 0.50);
    }
    .binding-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin-top: 10px;
    }
    details.card > summary {
      cursor: pointer;
      color: var(--text);
      font-weight: 800;
      list-style: none;
    }
    details.card > summary::-webkit-details-marker { display: none; }
    details.card > summary::after {
      content: "open";
      float: right;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    details.card[open] > summary::after { content: "close"; }
    .hint {
      color: var(--muted);
      font-size: 12px;
      margin-top: 10px;
    }
    #chatStatus {
      border: 1px solid rgba(111, 199, 247, 0.20);
      background: rgba(111, 199, 247, 0.055);
      border-radius: 999px;
      padding: 5px 9px;
      margin-top: 0;
    }
    .app {
      display: block;
      min-height: 100vh;
      height: 100vh;
      overflow: hidden;
    }
    aside, .workspace {
      position: fixed;
      top: 0;
      bottom: 0;
      z-index: 30;
      width: min(390px, calc(100vw - 28px));
      max-height: none;
      height: 100vh;
      transform: translateX(-112%);
      opacity: 0;
      pointer-events: none;
      transition: transform 220ms var(--ease), opacity 220ms var(--ease);
    }
    aside { left: 64px; border-right: 1px solid var(--line); }
    .workspace {
      right: 0;
      border-left: 1px solid var(--line);
      transform: translateX(112%);
    }
    body.show-left aside,
    body.show-right .workspace {
      transform: translateX(0);
      opacity: 1;
      pointer-events: auto;
    }
    main {
      height: 100vh;
      min-height: 100vh;
      grid-template-rows: auto 1fr auto;
      background:
        radial-gradient(circle at bottom center, rgba(127, 136, 255, 0.040), transparent 24rem),
        #0d0d0e;
      margin-left: 64px;
    }
    header {
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding: 18px max(18px, calc((100vw - 1120px) / 2));
      background: rgba(13, 13, 14, 0.92);
    }
    .chat {
      display: flex;
      flex-direction: column;
      min-height: 0;
      padding: 30px 18px;
    }
    .chat.has-messages {
      display: block;
      padding-top: 28px;
    }
    .message { width: min(100%, 980px); }
    .composer {
      padding: 0 18px 22px;
      border-top: 0;
      background: linear-gradient(180deg, rgba(13, 13, 14, 0), rgba(13, 13, 14, 0.94) 18%, #0d0d0e);
    }
    form {
      display: grid;
      grid-template-rows: minmax(62px, auto) auto;
      gap: 14px;
      width: min(100%, 980px);
      min-height: 150px;
      border-radius: 34px;
      border-color: rgba(255, 255, 255, 0.25);
      padding: 18px 22px;
      background: rgba(34, 34, 35, 0.88);
      box-shadow: 0 28px 80px rgba(0, 0, 0, 0.32);
    }
    textarea {
      width: 100%;
      min-height: 58px;
      max-height: 220px;
      padding: 6px 2px 0;
      font-size: 24px;
      font-weight: 650;
      color: #f6f6f6;
    }
    textarea::placeholder { color: #aaa; }
    .attach-inline,
    .send {
      width: 52px;
      height: 52px;
      min-width: 52px;
      padding: 0;
      border-radius: 50%;
      font-size: 28px;
      line-height: 1;
    }
    .attach-inline {
      background: rgba(255, 255, 255, 0.105);
      border-color: rgba(255, 255, 255, 0.06);
    }
    .send {
      background: #a3a3a3;
      color: #111;
      font-size: 22px;
    }
    .composer-tools {
      width: min(100%, 980px);
      margin-bottom: 8px;
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 1ms !important;
        transition-duration: 1ms !important;
        scroll-behavior: auto !important;
      }
    }
    @media (max-width: 1180px) {
      .app { display: block; }
      .workspace { display: block; }
    }
    @media (max-width: 840px) {
      body { overflow: hidden; }
      .app { height: 100vh; min-height: 100vh; }
      aside, .workspace { display: block; }
      .nav-rail { width: 54px; padding-left: 6px; padding-right: 6px; }
      .rail-button { width: 38px; height: 38px; }
      aside { left: 54px; width: min(360px, calc(100vw - 54px)); }
      main { min-height: 100vh; height: 100vh; }
      main { margin-left: 54px; }
      header { padding: 18px 16px; }
      .chat, .composer { padding-left: 16px; padding-right: 16px; }
      .message { grid-template-columns: 36px minmax(0, 1fr); gap: 10px; }
      .avatar { width: 36px; height: 36px; border-radius: 12px; font-size: 12px; }
      form { min-height: 136px; padding: 16px; border-radius: 28px; }
      textarea { font-size: 20px; }
      .model-chip { max-width: 58vw; overflow: hidden; text-overflow: ellipsis; }
      .add-sheet { left: 58px; right: 8px; bottom: 8px; border-radius: 22px; padding: 18px; }
    }
    .app.standard-shell {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      height: 100vh;
      min-height: 100vh;
      overflow: hidden;
      background: #0d0d0e;
    }
    .standard-shell .nav-rail { display: none; }
    .standard-shell aside {
      position: relative;
      inset: auto;
      left: auto;
      z-index: 1;
      width: auto;
      max-height: none;
      height: 100vh;
      transform: none;
      opacity: 1;
      pointer-events: auto;
      border-right: 1px solid rgba(255, 255, 255, 0.10);
      background: rgba(19, 19, 20, 0.96);
    }
    .standard-shell .workspace {
      width: min(420px, calc(100vw - 28px));
      z-index: 35;
    }
    .standard-shell main {
      margin-left: 0;
      min-width: 0;
      background:
        radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.025), transparent 24rem),
        #0b0b0c;
    }
    .standard-shell .topbar {
      grid-template-columns: minmax(0, 1fr) auto;
      padding: 16px max(18px, calc((100vw - 1220px) / 2));
    }
    .standard-shell h1 { font-size: 18px; }
    .standard-shell .subtitle { font-size: var(--font-sm); }
    .standard-shell #leftDrawerBtn { display: none; }
    .standard-shell #rightDrawerBtn {
      min-width: auto;
      width: auto;
      padding: 0 14px;
      border-color: rgba(255, 255, 255, 0.10);
      background: rgba(255, 255, 255, 0.055);
    }
    .standard-shell .drawer-backdrop {
      left: 320px;
      background: rgba(0, 0, 0, 0.38);
    }
    .standard-shell .chat {
      padding: 32px 20px;
    }
    .standard-shell .empty-state {
      padding-top: 16vh;
    }
    .standard-shell .empty-state h2 {
      font-size: clamp(24px, 2.8vw, var(--font-hero));
      letter-spacing: -0.035em;
    }
    .standard-shell .empty-state p {
      margin-top: 12px;
      font-size: clamp(13px, 1.35vw, 16px);
      font-weight: 560;
    }
    .standard-shell .bubble {
      font-size: var(--font-md);
      line-height: 1.5;
      padding: 14px 16px;
    }
    .standard-shell form,
    .standard-shell .composer-tools,
    .standard-shell .action-tray {
      width: min(100%, 920px);
    }
    .standard-shell form {
      min-height: 118px;
      border-radius: 24px;
      border-color: rgba(255, 255, 255, 0.16);
      background: rgba(31, 31, 32, 0.96);
      box-shadow: 0 22px 70px rgba(0, 0, 0, 0.30);
    }
    .standard-shell textarea {
      min-height: 42px;
      font-size: 15px;
      font-weight: 500;
    }
    .standard-shell .action-tray {
      flex-wrap: wrap;
      overflow: visible;
      justify-content: center;
    }
    .standard-shell .action-tray button {
      background: rgba(255, 255, 255, 0.055);
      border-color: rgba(255, 255, 255, 0.10);
      color: #d5d5d8;
      font-size: var(--font-sm);
      padding: 8px 11px;
    }
    .standard-shell .card {
      box-shadow: none;
      background: rgba(255, 255, 255, 0.045);
    }
    .standard-shell .quick button,
    .standard-shell .search button,
    .standard-shell .drawer-menu button {
      background: rgba(255, 255, 255, 0.045);
      border-color: rgba(255, 255, 255, 0.075);
      font-size: 13px;
    }
    .standard-shell .tool-button,
    .standard-shell .mini-button,
    .standard-shell .tool-input,
    .standard-shell .tool-select,
    .standard-shell .tool-textarea {
      font-size: 13px;
    }
    .standard-shell .model-chip {
      min-height: 30px;
      padding: 5px 10px;
      font-size: var(--font-sm);
      gap: 5px;
    }
    .standard-shell .model-chip span {
      padding: 1px 6px;
    }
    .standard-shell .composer-bottom {
      justify-content: space-between;
    }
    .standard-shell .attach-inline,
    .standard-shell .send {
      width: 44px;
      height: 44px;
      min-width: 44px;
      font-size: 20px;
    }
    .standard-shell .send {
      font-size: 17px;
    }
    .standard-shell .sheet-title {
      font-size: 20px;
    }
    .standard-shell .sheet-close {
      font-size: 24px;
    }
    .standard-shell .sheet-action b {
      font-size: 15px;
    }
    .standard-shell .sheet-action span {
      font-size: var(--font-sm);
    }
    .standard-shell .sheet-icon {
      font-size: 15px;
    }
    .standard-shell .file-chip,
    .standard-shell .folder-row,
    .standard-shell .results,
    .standard-shell .tool-output,
    .standard-shell .file-list {
      font-size: var(--font-sm);
    }
    .standard-shell .add-sheet {
      left: calc(320px + max(20px, (100vw - 1220px) / 2));
      right: max(20px, calc((100vw - 1220px) / 2));
      bottom: 18px;
      border-radius: 26px;
    }
    .standard-shell .add-sheet-backdrop {
      left: 320px;
    }
    @media (max-width: 980px) {
      .app.standard-shell {
        display: block;
      }
      .standard-shell .nav-rail {
        display: flex;
      }
      .standard-shell aside {
        position: fixed;
        left: 54px;
        width: min(360px, calc(100vw - 54px));
        transform: translateX(-112%);
        opacity: 0;
        pointer-events: none;
        z-index: 35;
      }
      body.show-left .standard-shell aside {
        transform: translateX(0);
        opacity: 1;
        pointer-events: auto;
      }
      .standard-shell main {
        margin-left: 54px;
      }
      .standard-shell .topbar {
        grid-template-columns: 48px minmax(0, 1fr) auto;
      }
      .standard-shell #leftDrawerBtn { display: grid; }
      .standard-shell .drawer-backdrop,
      .standard-shell .add-sheet-backdrop {
        left: 54px;
      }
      .standard-shell .add-sheet {
        left: 62px;
        right: 8px;
      }
    }

    /* Gima glass black/white cloud-blue interface layer. Pure visual upgrade; app behavior stays unchanged. */
    :root {
      --bg: #030406;
      --bg-soft: #080a0f;
      --panel: rgba(8, 10, 15, 0.78);
      --panel-2: rgba(12, 15, 22, 0.84);
      --panel-3: rgba(18, 22, 31, 0.90);
      --line: rgba(177, 222, 255, 0.24);
      --line-soft: rgba(255, 255, 255, 0.13);
      --text: #fbfdff;
      --muted: #aab5c2;
      --muted-2: #d7dee8;
      --accent: #9bd8ff;
      --accent-2: #f8fbff;
      --accent-3: #6fb7ff;
      --user: rgba(18, 24, 34, 0.86);
      --assistant: rgba(7, 9, 14, 0.84);
      --glow: 0 18px 52px rgba(132, 198, 255, 0.12), 0 0 90px rgba(255, 255, 255, 0.045);
    }
    body {
      background:
        radial-gradient(circle at 16% 8%, rgba(155, 216, 255, 0.18), transparent 27rem),
        radial-gradient(circle at 82% 11%, rgba(255, 255, 255, 0.10), transparent 26rem),
        radial-gradient(circle at 82% 78%, rgba(111, 183, 255, 0.10), transparent 24rem),
        linear-gradient(135deg, #000000 0%, #050608 46%, #090b10 100%);
    }
    body::before,
    body::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
    }
    body::before {
      z-index: 0;
      opacity: 0.16;
      background-image:
        linear-gradient(rgba(190, 226, 255, 0.16) 1px, transparent 1px),
        linear-gradient(90deg, rgba(190, 226, 255, 0.16) 1px, transparent 1px);
      background-size: 52px 52px;
      mask-image: radial-gradient(circle at 55% 42%, black 0%, transparent 72%);
    }
    body::after {
      z-index: 0;
      opacity: 0.28;
      background:
        linear-gradient(115deg, transparent 0 32%, rgba(155, 216, 255, 0.10) 36%, transparent 41%),
        linear-gradient(245deg, transparent 0 42%, rgba(255, 255, 255, 0.07) 46%, transparent 52%);
      mix-blend-mode: screen;
    }
    .app,
    .app.standard-shell {
      position: relative;
      z-index: 1;
      background: transparent;
    }
    .standard-shell main,
    main {
      background:
        radial-gradient(circle at 50% 28%, rgba(155, 216, 255, 0.08), transparent 26rem),
        linear-gradient(180deg, rgba(10, 12, 18, 0.62), rgba(0, 0, 0, 0.96));
    }
    aside,
    .workspace,
    .standard-shell aside,
    .standard-shell .workspace {
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.018)),
        rgba(5, 7, 11, 0.78);
      border-color: rgba(177, 222, 255, 0.22);
      box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.06), 0 24px 70px rgba(0, 0, 0, 0.36);
      backdrop-filter: blur(26px) saturate(128%);
    }
    header,
    .standard-shell .topbar {
      background:
        linear-gradient(90deg, rgba(0, 0, 0, 0.88), rgba(14, 18, 26, 0.76)),
        rgba(0, 0, 0, 0.76);
      border-bottom-color: rgba(177, 222, 255, 0.22);
      box-shadow: 0 14px 44px rgba(0, 0, 0, 0.26);
      backdrop-filter: blur(24px) saturate(126%);
    }
    .standard-shell h1,
    h1 {
      letter-spacing: -0.04em;
      text-shadow: 0 0 24px rgba(155, 216, 255, 0.24);
    }
    .subtitle {
      color: var(--muted);
      letter-spacing: 0.01em;
    }
    .logo,
    .avatar {
      border: 1px solid rgba(177, 222, 255, 0.34);
      box-shadow: 0 0 24px rgba(155, 216, 255, 0.20), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    }
    .logo {
      border-radius: 16px;
      background-color: rgba(155, 216, 255, 0.12);
    }
    .assistant .avatar {
      background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.38), rgba(155, 216, 255, 0.22) 46%, rgba(6, 8, 12, 0.92));
    }
    .card,
    .standard-shell .card,
    .bubble,
    form,
    .standard-shell form,
    .add-sheet {
      position: relative;
      overflow: hidden;
      border-color: rgba(177, 222, 255, 0.22);
      background:
        linear-gradient(145deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.025)),
        rgba(5, 7, 11, 0.78);
      box-shadow: 0 20px 70px rgba(0, 0, 0, 0.30), var(--glow);
      backdrop-filter: blur(20px) saturate(120%);
    }
    .card::before,
    .bubble::before,
    form::before,
    .add-sheet::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.10), transparent 33%),
        linear-gradient(315deg, rgba(155, 216, 255, 0.11), transparent 42%);
      opacity: 0.62;
    }
    .card > *,
    .bubble > *,
    form > *,
    .add-sheet > * {
      position: relative;
      z-index: 1;
    }
    .card:hover,
    .standard-shell .card:hover {
      border-color: rgba(177, 222, 255, 0.42);
      box-shadow: 0 24px 78px rgba(0, 0, 0, 0.46), 0 0 32px rgba(155, 216, 255, 0.16);
    }
    .user .bubble {
      background:
        linear-gradient(145deg, rgba(255, 255, 255, 0.075), rgba(155, 216, 255, 0.09)),
        rgba(13, 18, 26, 0.88);
      border-color: rgba(177, 222, 255, 0.30);
    }
    .composer {
      background: linear-gradient(180deg, rgba(0, 0, 0, 0), rgba(5, 7, 11, 0.86) 24%, rgba(0, 0, 0, 0.97));
    }
    form,
    .standard-shell form {
      border-color: rgba(177, 222, 255, 0.34);
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.085), rgba(155, 216, 255, 0.08)),
        rgba(0, 0, 0, 0.74);
    }
    textarea,
    .search input,
    .tool-input,
    .tool-select,
    .tool-textarea {
      color: var(--text);
      background: rgba(0, 0, 0, 0.46);
      border-color: rgba(177, 222, 255, 0.18);
    }
    textarea::placeholder,
    .tool-input::placeholder,
    .tool-textarea::placeholder {
      color: rgba(215, 222, 232, 0.58);
    }
    .pill,
    #chatStatus,
    .model-chip,
    .model-chip span {
      border-color: rgba(177, 222, 255, 0.42);
      color: #f8fbff;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.11), rgba(155, 216, 255, 0.11));
      box-shadow: 0 0 20px rgba(155, 216, 255, 0.11);
    }
    .tool-button,
    .send {
      color: #07111b;
      border-color: rgba(255, 255, 255, 0.46);
      background: linear-gradient(135deg, #ffffff, #bfe7ff 58%, #78c8ff);
      box-shadow: 0 0 26px rgba(155, 216, 255, 0.26), 0 18px 38px rgba(0, 0, 0, 0.38);
      font-weight: 850;
    }
    .attach-inline,
    .screen-record-button,
    .mini-button,
    .quick button,
    .search button,
    .drawer-menu button,
    .action-tray button,
    .rail-button,
    .icon-button,
    .download-button,
    .copy-button,
    .standard-shell .action-tray button,
    .standard-shell .quick button,
    .standard-shell .search button,
    .standard-shell .drawer-menu button {
      border-color: rgba(177, 222, 255, 0.20);
      color: var(--text);
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.075), rgba(155, 216, 255, 0.06)),
        rgba(7, 10, 15, 0.78);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 12px 28px rgba(0, 0, 0, 0.16);
    }
    .attach-inline:hover,
    .screen-record-button:hover,
    .mini-button:hover,
    .quick button:hover,
    .search button:hover,
    .drawer-menu button:hover,
    .action-tray button:hover,
    .rail-button:hover,
    .icon-button:hover,
    .download-button:hover,
    .copy-button:hover {
      border-color: rgba(177, 222, 255, 0.48);
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(155, 216, 255, 0.13)),
        rgba(9, 13, 20, 0.90);
      box-shadow: 0 0 22px rgba(155, 216, 255, 0.16), 0 14px 34px rgba(0, 0, 0, 0.32);
    }
    .section-label {
      color: #eaf7ff;
      letter-spacing: 0.16em;
      text-shadow: 0 0 18px rgba(155, 216, 255, 0.22);
    }
    .bubble table {
      border: 1px solid rgba(177, 222, 255, 0.20);
      box-shadow: 0 0 26px rgba(155, 216, 255, 0.08);
    }
    .bubble th {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.13), rgba(155, 216, 255, 0.13));
      color: #f8fbff;
    }
    .terminal-output {
      border-color: rgba(177, 222, 255, 0.26);
      background: rgba(3, 5, 8, 0.90);
      color: #dff2ff;
      box-shadow: inset 0 0 28px rgba(155, 216, 255, 0.07);
    }
  </style>
</head>
<body>
  <div class="app standard-shell">
    <div class="drawer-backdrop" id="drawerBackdrop"></div>
    <div class="add-sheet-backdrop" id="addSheetBackdrop"></div>
    <nav class="nav-rail" aria-label="Gima navigation">
      <button class="rail-button" id="railHomeBtn" type="button" title="New chat">+</button>
      <button class="rail-button" id="railSystemBtn" type="button" title="System">[]</button>
      <button class="rail-button" type="button" data-open-panel="left" data-focus="search" title="Search">?</button>
      <button class="rail-button" type="button" data-open-panel="left" data-focus="apiKey" title="API and MCP">M</button>
      <button class="rail-button" type="button" data-open-panel="right" data-focus="folderMap" title="Workspace">W</button>
      <div class="rail-spacer"></div>
      <button class="rail-button" type="button" data-open-panel="left" data-focus="settingsPanel" title="Settings">*</button>
    </nav>
    <aside>
      <div class="brand">
        <div class="logo" aria-label="Gima logo">G</div>
        <div>
          <h1>Gima</h1>
          <p class="subtitle">local-first AI command deck <span class="sr-only">soft gray local AI workspace</span></p>
        </div>
      </div>
      <div class="drawer-menu" aria-label="Gima drawer menu">
        <button type="button" data-prompt="Start a new Gima task. Ask me what you want to build or create."><span class="menu-icon">+</span>New chat</button>
        <button type="button" data-open-panel="left" data-focus="search"><span class="menu-icon">?</span>Search</button>
        <button type="button" data-open-panel="left" data-focus="apiKey"><span class="menu-icon">M</span>MCP / AI APIs</button>
        <button type="button" data-open-panel="left" data-focus="settingsPanel"><span class="menu-icon">*</span>Settings</button>
      </div>
      <div class="section-label">Control</div>
      <div class="card">
        <h2 style="font-size: 14px;">System</h2>
        <div class="status-row"><span>Brain</span><span class="pill" id="brain">checking</span></div>
        <div class="status-row"><span>Model</span><span id="model">...</span></div>
        <select class="tool-select" id="localModelSelect" aria-label="Local model level"></select>
        <button class="mini-button" id="localModelUseBtn" type="button">Use Local Model</button>
        <div class="hint" id="localModelHint">Model levels loading...</div>
        <div class="status-row"><span>Memory</span><span id="memory">local</span></div>
        <div class="status-row"><span>Last response</span><span id="lastResponse">waiting</span></div>
        <div class="results" id="doctorMini">doctor checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">API Bindings</h2>
        <p class="hint">Saved locally. Gima uses linked minds as teachers and stores human-language answers in brain.</p>
        <div id="bindingStatus" class="results">checking...</div>
        <div id="quotaStatus" class="results">free quota checking...</div>
        <div class="binding-grid">
          <select class="tool-select" id="chatProvider">
            <option value="local">Chat mode: Local brain + memory</option>
            <option value="chatgpt">Chat mode: ChatGPT / OpenAI</option>
            <option value="openrouter">Chat mode: OpenRouter</option>
            <option value="anthropic">Chat mode: Claude / Anthropic</option>
            <option value="gemini">Chat mode: Gemini</option>
          </select>
          <select class="tool-select" id="apiProvider">
            <option value="openai">ChatGPT / OpenAI</option>
            <option value="gemini">Gemini</option>
            <option value="anthropic">Claude / Anthropic</option>
            <option value="xai">Grok / xAI</option>
            <option value="deepseek">DeepSeek</option>
            <option value="openrouter">OpenRouter Default / Chat</option>
            <option value="openrouter_mai">OpenRouter MAI Speech</option>
            <option value="openrouter_veo">OpenRouter Veo Video</option>
            <option value="openrouter_image">OpenRouter GPT Image</option>
            <option value="openrouter_nano_banana">OpenRouter Nano Banana</option>
            <option value="openrouter_management">OpenRouter Management Key</option>
          </select>
          <input class="tool-input" id="apiKey" type="password" placeholder="Paste API key">
          <button class="tool-button" id="saveApiBtn">Save API Binding</button>
          <button class="mini-button" id="multiMindBtn" type="button">Ask All Linked Minds</button>
          <input class="tool-input" id="openrouterModelSearch" type="search" placeholder="Search OpenRouter models">
          <button class="mini-button" id="openrouterLoadModelsBtn" type="button">Load OpenRouter Models</button>
          <select class="tool-select" id="openrouterModelSelect"></select>
          <button class="mini-button" id="openrouterSaveModelBtn" type="button">Use Selected OpenRouter Model</button>
          <select class="tool-select" id="openrouterRoutingSort">
            <option value="latency">Route by latency</option>
            <option value="throughput">Route by throughput</option>
            <option value="price">Route by price</option>
          </select>
          <select class="tool-select" id="openrouterDataCollection">
            <option value="deny">Deny provider data collection</option>
            <option value="allow">Allow provider data collection</option>
          </select>
          <input class="tool-input" id="openrouterFallbackModels" placeholder="Fallback models, comma separated">
          <button class="mini-button" id="openrouterSaveRoutingBtn" type="button">Save OpenRouter Routing</button>
          <input class="tool-input" id="freeLlmTask" placeholder="Free LLM planner task: voice chat, long PDF, coding, batch summaries">
          <select class="tool-select" id="freeLlmPrivacy">
            <option value="balanced">Balanced privacy</option>
            <option value="strict">Strict/private data</option>
            <option value="open">Open/public data</option>
          </select>
          <button class="mini-button" id="freeLlmPlanBtn" type="button">Plan Free LLM Route</button>
          <textarea class="tool-textarea" id="modelCouncilRequest" placeholder="Model council request: pick best model for voice chat, image OCR, local private coding, MAI speech, video prompt"></textarea>
          <button class="mini-button" id="modelCouncilBtn" type="button">Ask Model Council</button>
        </div>
        <div class="tool-output" id="bindingOutput"></div>
        <div class="tool-output" id="openrouterModelOutput"></div>
        <div class="tool-output" id="freeLlmOutput"></div>
        <div class="tool-output" id="modelCouncilOutput"></div>
      </div>
      <div class="card quick">
        <h2 style="font-size: 14px;">Quick Prompts</h2>
        <button data-prompt="What can you do right now on this PC?">PC capabilities</button>
        <button data-prompt="use brain: What does Gima know right now?">Use Brain</button>
        <button data-prompt="Search your memory for Gima latest upgrades.">Memory summary</button>
        <button data-prompt="browse the web for latest AI news and give sources">Browse Web</button>
        <button data-prompt="Give me the next 5 best improvements for Gima.">Improve Gima</button>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Install App</h2>
        <p class="hint">Mac: install from Safari/Chrome. iPhone/Android: open this address on the same network and Add to Home Screen.</p>
        <button class="tool-button" id="installBtn" type="button">Install Gima App</button>
        <div class="tool-output" id="installOutput"></div>
      </div>
      <div class="card search">
        <h2 style="font-size: 14px; margin-bottom: 10px;">Memory Search</h2>
        <input id="search" placeholder="Search local memory">
        <button id="searchBtn">Search</button>
        <div class="results" id="results"></div>
      </div>
      <div class="card" id="settingsPanel">
        <h2 style="font-size: 14px;">Settings</h2>
        <label class="status-row"><span>Send message on Enter</span><input id="enterSendSetting" type="checkbox" checked></label>
        <label class="status-row"><span>Show response time</span><input id="responseTimeSetting" type="checkbox" checked></label>
        <label class="status-row"><span>Copy text attachments as plain text</span><input id="plainCopySetting" type="checkbox"></label>
        <textarea class="tool-textarea" id="systemMessageDraft" placeholder="Optional system message for your next prompt"></textarea>
        <button class="mini-button" id="insertSystemMessageBtn" type="button">Insert System Message</button>
        <p class="hint">Local UI settings only. They help shape the next chat prompt without changing Gima's protected policy files.</p>
      </div>
    </aside>
    <main>
      <header class="topbar">
        <button class="icon-button" id="leftDrawerBtn" type="button" title="Open system controls">[]</button>
        <div>
          <h1>Gima Command Deck <span class="sr-only">Chat With Gima</span></h1>
          <p class="subtitle">Local-first multimodal AI workspace with memory, tools, files, and guarded internet awareness.</p>
        </div>
        <button class="icon-button" id="rightDrawerBtn" type="button" title="Open tools">Tools</button>
      </header>
      <section class="chat" id="chat">
        <section class="empty-state" id="emptyState">
          <h2>Hello there</h2>
          <p>Type a message or upload files to get started</p>
        </section>
      </section>
      <div class="composer">
        <div class="composer-tools">
          <span class="hint" id="chatStatus">chat ready</span>
          <span class="hint">Uploaded files are saved in `hands/in` and included with your next prompt.</span>
        </div>
        <div id="attachmentBar" class="composer-tools"></div>
        <form id="form">
          <input id="chatFileInput" class="sr-only" type="file" multiple>
          <textarea id="message" placeholder="Type a message..." autofocus></textarea>
          <div class="composer-bottom">
            <button class="attach-inline" id="chatUploadBtn" type="button" title="Attach to chat">+</button>
            <button class="screen-record-button" id="screenRecordBtn" type="button" title="Record screen and attach to chat">REC</button>
            <span class="route-preview local" id="routePreviewChip" title="Gima route preview"><strong>route</strong> <span>local</span></span>
            <span class="model-chip" id="modelChip" hidden></span>
            <button class="send" id="send" type="submit" title="Send">^</button>
          </div>
        </form>
        <div class="action-tray" id="actionTray" aria-label="Gima feature buttons">
          <button type="button" data-prompt="What can you do right now on this PC?">PC</button>
          <button type="button" data-prompt="use brain: What does Gima know right now?">Brain</button>
          <button type="button" data-prompt="Search your memory for Gima latest upgrades.">Memory</button>
          <button type="button" data-prompt="browse the web for latest AI news and give sources">Browse</button>
          <button type="button" data-prompt="Give me the next 5 best improvements for Gima.">Improve</button>
          <button type="button" data-action="attach">Attach</button>
          <button type="button" data-action="screen-record">Screen Rec</button>
          <button type="button" data-open-panel="left" data-focus="search">Search</button>
          <button type="button" data-open-panel="left" data-focus="apiKey">AI APIs</button>
          <button type="button" data-open-panel="right" data-focus="songPrompt">Song</button>
          <button type="button" data-open-panel="right" data-focus="videoPrompt">Audio Video</button>
          <button type="button" data-open-panel="right" data-focus="imageVideoPaths">Images + MP3</button>
          <button type="button" data-open-panel="right" data-focus="directorPrompt">Director</button>
          <button type="button" data-open-panel="right" data-focus="lipPrompt">Lip-Sync</button>
          <button type="button" data-open-panel="right" data-focus="codeFeature">Coding</button>
          <button type="button" data-open-panel="right" data-focus="folderMap">Folders</button>
          <button type="button" data-open-panel="right" data-focus="outputList">Outputs</button>
          <button type="button" data-open-panel="right" data-focus="deploymentList">Deployments</button>
          <button type="button" data-open-panel="right" data-focus="appPlanList">Apps</button>
        </div>
        <div class="hint">Enter sends. Shift+Enter makes a new line. Server is local by default.</div>
      </div>
    </main>
    <section class="add-sheet" id="addSheet" aria-label="Add to chat">
      <div class="sheet-head">
        <div class="sheet-title">Add to chat</div>
        <button class="sheet-close" id="addSheetClose" type="button" title="Close">x</button>
      </div>
      <div class="sheet-list">
        <button class="sheet-action" type="button" data-file-category="all" data-accept="">
          <span class="sheet-icon">F</span><b>Add files</b><span>Any file Gima can store in hands/in</span>
        </button>
        <button class="sheet-action" type="button" data-file-category="images" data-accept="image/*">
          <span class="sheet-icon">I</span><b>Images</b><span>Photos, screenshots, references</span>
        </button>
        <button class="sheet-action" type="button" data-file-category="audio" data-accept="audio/*,.mp3,.wav,.m4a">
          <span class="sheet-icon">A</span><b>Audio Files</b><span>Music, speech, MP3/WAV/M4A</span>
        </button>
        <button class="sheet-action" type="button" data-file-category="video" data-accept="video/*,.mp4,.mov,.mkv">
          <span class="sheet-icon">V</span><b>Video Files</b><span>Clips for analysis or generation inputs</span>
        </button>
        <button class="sheet-action" type="button" data-file-category="text" data-accept=".txt,.md,.csv,.json,.py,.js,.ts,.tsx,.html,.css">
          <span class="sheet-icon">T</span><b>Text Files</b><span>Code, notes, CSV, markdown</span>
        </button>
        <button class="sheet-action" type="button" data-file-category="pdf" data-accept="application/pdf,.pdf">
          <span class="sheet-icon">P</span><b>PDF Files</b><span>Research, documents, papers</span>
        </button>
        <button class="sheet-action" type="button" data-open-panel="left" data-focus="apiKey">
          <span class="sheet-icon">M</span><b>MCP Servers / AI APIs</b><span id="mcpServerCount">0 servers</span>
        </button>
        <button class="sheet-action" type="button" data-open-panel="left" data-focus="systemMessageDraft">
          <span class="sheet-icon">S</span><b>System Message</b><span>Add instruction text to the next prompt</span>
        </button>
      </div>
    </section>
    <section class="workspace">
      <div class="brand">
        <div class="logo">W</div>
        <div>
          <h1>Workspace</h1>
          <p class="subtitle">human folders, files, media, coding split</p>
        </div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Human Folder Map</h2>
        <p class="hint">Standard Gima body layout. Use hands/in for inputs and hands/out for created work.</p>
        <div class="folder-grid" id="folderMap">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Attach Files</h2>
        <p class="hint">Hands input path: <span id="handsInPath">checking...</span></p>
        <p class="hint">Legacy downloads path: <span id="downloadsPath">checking...</span></p>
        <p class="hint">Stomach inventory: <span id="stomachPath">checking...</span></p>
        <p class="hint">Continuous work CSV: <span id="continuousPath">checking...</span></p>
        <p class="hint">Brain CSV: <span id="brainCsvPath">checking...</span></p>
        <input class="tool-input" id="fileInput" type="file" multiple>
        <button class="tool-button" id="uploadBtn">Upload to Gima</button>
        <div class="file-list" id="fileList"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Hands Folder</h2>
        <p class="hint">Generated path: <span id="handsPath">checking...</span></p>
        <p class="hint">Output path: <span id="handsOutPath">checking...</span></p>
        <div class="tool-output">Gima reads from hands/in and puts created songs, videos, and plans in hands/out.</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">What Gima Can Do</h2>
        <div class="results" id="capabilityList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">AI Doctor & Upgrade Plan</h2>
        <p class="hint">PC-aware plan for learning, tools, model size, media, and self-improvement.</p>
        <div class="results" id="doctorPlanList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Local AI Stack for This Laptop</h2>
        <p class="hint">i7-7700HQ + 16GB RAM: unlimited local-first tools, model size limits, and download plan.</p>
        <div class="results" id="localAiStackList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Paid OpenRouter Model Plan</h2>
        <p class="hint">Hybrid routing: local first, cheap paid second, premium only for hard tasks.</p>
        <button class="mini-button" id="refreshPaidOpenRouterBtn" type="button">Refresh Paid Model Plan</button>
        <div class="results" id="paidOpenRouterList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Apps & Automation</h2>
        <p class="hint">PWA now works as installable local app shell. Native Windows/macOS/iOS/Android packaging is tracked as capability work.</p>
        <div class="results" id="appPlanList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Codex Mode</h2>
        <p class="hint">Local coding agent view: what Gima can do like Codex on this PC.</p>
        <div class="results" id="codexModeList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">AI Task Map A-Z</h2>
        <p class="hint">One CSV mapping worldwide AI tasks, sources, providers, evals, and Gima status.</p>
        <div class="results" id="aiTaskMapList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Public API Finder</h2>
        <p class="hint">Search the MIT-licensed public-apis catalog. Discovery only: review docs before sending data.</p>
        <input class="tool-input" id="publicApiQuery" placeholder="weather, finance, music, video, jobs">
        <input class="tool-input" id="publicApiCategory" placeholder="Optional category">
        <label class="status-row"><span>No-auth only</span><input id="publicApiNoAuth" type="checkbox" checked></label>
        <label class="status-row"><span>HTTPS only</span><input id="publicApiHttps" type="checkbox" checked></label>
        <button class="tool-button" id="publicApiBtn" type="button">Find APIs</button>
        <div class="results" id="publicApiList">Search public APIs when needed.</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Deployments</h2>
        <div class="results" id="deploymentList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Agents & Vibe Code</h2>
        <p class="hint">Create review-gated task agents. Self-update agents prepare a backup and isolated working copy, not live edits.</p>
        <input class="tool-input" id="agentName" placeholder="Agent name, e.g. Gima UI Updater">
        <select class="tool-select" id="agentTemplate">
          <option value="self_update">Safe Self-Update Agent</option>
          <option value="research">Research Agent</option>
          <option value="artifact">Artifact Agent</option>
        </select>
        <textarea class="tool-textarea" id="agentGoal" placeholder="Specific task, e.g. improve Gima route preview UI and run tests"></textarea>
        <button class="tool-button" id="agentCreateBtn" type="button">Create Task Agent</button>
        <div class="tool-output" id="agentCreateOutput"></div>
        <div class="results" id="agentList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Outputs</h2>
        <div class="results" id="outputList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Generate Song Sketch</h2>
        <textarea class="tool-textarea" id="songPrompt" placeholder="Example: happy cinematic intro for Gima"></textarea>
        <input class="tool-input" id="songDuration" type="number" min="4" max="60" value="12">
        <button class="tool-button" id="songBtn">Generate Local WAV</button>
        <div class="tool-output" id="songOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">External Music API</h2>
        <p class="hint">Cloud song generation. Requires CLOUD_ALLOWED=true, a provider key, and rights-safe lyrics/prompts.</p>
        <select class="tool-select" id="musicApiProvider">
          <option value="huggingface_musicgen">Open Source MusicGen / Hugging Face</option>
          <option value="suno_compatible">Suno-compatible approved gateway</option>
          <option value="waivepulse_local">WAIvePulse local HeartMuLa server</option>
        </select>
        <textarea class="tool-textarea" id="musicApiPrompt" placeholder="Example: cinematic Sinhala pop ballad, emotional male vocal, live stage energy"></textarea>
        <textarea class="tool-textarea" id="musicApiLyrics" placeholder="Optional lyrics you own or have permission to use"></textarea>
        <input class="tool-input" id="musicApiModel" placeholder="Optional provider model/version">
        <input class="tool-input" id="musicApiDuration" type="number" min="4" max="600" value="30">
        <label class="status-row"><span>Instrumental</span><input id="musicApiInstrumental" type="checkbox"></label>
        <button class="tool-button" id="musicApiBtn">Generate API Song</button>
        <div class="tool-output" id="musicApiOutput">Checking music API status...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Generate Video From Audio</h2>
        <input class="tool-input" id="videoAudioPath" placeholder="Audio path or uploaded file path">
        <textarea class="tool-textarea" id="videoPrompt" placeholder="Describe the video mood"></textarea>
        <select class="tool-select" id="videoStyle">
          <option value="professional">Professional</option>
          <option value="waveform">Waveform</option>
          <option value="spectrum">Spectrum</option>
        </select>
        <button class="tool-button" id="videoBtn">Render Local MP4</button>
        <div class="tool-output" id="videoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">AI Video From Prompt</h2>
        <p class="hint">One prompt to video. Uses OpenRouter/Veo first or Hugging Face/Wan when configured. Requires CLOUD_ALLOWED=true and consent.</p>
        <textarea class="tool-textarea" id="promptVideoPrompt" placeholder="A cinematic 8 second shot of a futuristic blue-glass AI command deck, slow dolly-in, soft light, realistic motion"></textarea>
        <select class="tool-select" id="promptVideoProvider">
          <option value="auto">Auto best available</option>
          <option value="openrouter">OpenRouter / Veo</option>
          <option value="huggingface">Hugging Face / Wan</option>
        </select>
        <select class="tool-select" id="promptVideoAspect">
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
          <option value="1:1">1:1</option>
        </select>
        <input class="tool-input" id="promptVideoDuration" type="number" min="1" max="30" value="8">
        <label class="status-row"><span>Generate audio</span><input id="promptVideoAudio" type="checkbox" checked></label>
        <button class="tool-button" id="promptVideoBtn">Generate AI Video</button>
        <div class="tool-output" id="promptVideoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">OpenRouter Veo Video</h2>
        <p class="hint">Cloud video generation through OpenRouter. This can spend credits; use only rights-safe prompts and assets.</p>
        <textarea class="tool-textarea" id="openrouterVideoPrompt" placeholder="Example: cinematic 8 second shot of a soft gray AI workspace, smooth camera move"></textarea>
        <select class="tool-select" id="openrouterVideoModel">
          <option value="google/veo-3.1">google/veo-3.1</option>
          <option value="google/veo-3.1-lite">google/veo-3.1-lite</option>
        </select>
        <select class="tool-select" id="openrouterVideoAspect">
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
          <option value="1:1">1:1</option>
        </select>
        <select class="tool-select" id="openrouterVideoResolution">
          <option value="720p">720p</option>
          <option value="1080p">1080p</option>
        </select>
        <input class="tool-input" id="openrouterVideoDuration" type="number" min="1" max="30" value="8">
        <label class="status-row"><span>Generate audio</span><input id="openrouterVideoAudio" type="checkbox" checked></label>
        <button class="tool-button" id="openrouterVideoBtn">Generate Veo Video</button>
        <div class="tool-output" id="openrouterVideoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Hugging Face Video</h2>
        <p class="hint">Text-to-video through Hugging Face InferenceClient. Requires HF_TOKEN, CLOUD_ALLOWED=true, and consent.</p>
        <textarea class="tool-textarea" id="hfVideoPrompt" placeholder="A young man walking on the street"></textarea>
        <input class="tool-input" id="hfVideoModel" value="Wan-AI/Wan2.2-TI2V-5B">
        <input class="tool-input" id="hfVideoProvider" value="replicate">
        <button class="tool-button" id="hfVideoBtn">Generate HF Video</button>
        <div class="tool-output" id="hfVideoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Microsoft MAI Speech</h2>
        <p class="hint">OpenRouter TTS through /api/v1/audio/speech. Requires CLOUD_ALLOWED=true, OpenRouter key, consent, and rights-safe text.</p>
        <textarea class="tool-textarea" id="openrouterSpeechText" placeholder="Text for Gima to speak"></textarea>
        <input class="tool-input" id="openrouterSpeechModel" value="microsoft/mai-voice-2">
        <input class="tool-input" id="openrouterSpeechVoice" value="en-US-Harper:MAI-Voice-2">
        <select class="tool-select" id="openrouterSpeechStyle">
          <option value="cheerful">cheerful</option>
          <option value="excited">excited</option>
          <option value="sad">sad</option>
          <option value="angry">angry</option>
          <option value="calm">calm</option>
        </select>
        <input class="tool-input" id="openrouterSpeechSpeed" type="number" min="0.5" max="2" step="0.1" value="1">
        <button class="tool-button" id="openrouterSpeechBtn">Generate MAI Speech MP3</button>
        <div class="tool-output" id="openrouterSpeechOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">My Voice Profile</h2>
        <p class="hint">Register your own consented voice sample as Gima's personal voice reference. This stores a local profile; it does not claim voice cloning is available unless a real backend is connected.</p>
        <input class="tool-input" id="ownVoiceName" value="Gimhan original voice 2" placeholder="Voice profile name">
        <input class="tool-input" id="ownVoicePath" placeholder="Path to your MP3/WAV/M4A voice sample">
        <label class="status-row"><span>This is my own voice</span><input id="ownVoiceConsent" type="checkbox"></label>
        <button class="tool-button" id="ownVoiceBtn">Add My Voice</button>
        <div class="tool-output" id="ownVoiceOutput">No personal voice profile loaded yet.</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">ChatGPT Image Generation</h2>
        <p class="hint">Uses the saved ChatGPT / OpenAI API key. Generates a PNG in hands/out with a provenance manifest.</p>
        <textarea class="tool-textarea" id="openaiImagePrompt" placeholder="Example: professional Gima AI workspace logo, soft gray, cinematic lighting"></textarea>
        <select class="tool-select" id="openaiImageModel">
          <option value="gpt-image-2">gpt-image-2</option>
          <option value="gpt-image-1">gpt-image-1</option>
        </select>
        <select class="tool-select" id="openaiImageSize">
          <option value="1024x1024">1024x1024 Square</option>
          <option value="1024x1536">1024x1536 Portrait</option>
          <option value="1536x1024">1536x1024 Landscape</option>
          <option value="auto">Auto</option>
        </select>
        <select class="tool-select" id="openaiImageQuality">
          <option value="auto">Auto quality</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <button class="tool-button" id="openaiImageBtn">Generate ChatGPT Image</button>
        <div class="tool-output" id="openaiImageOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Hugging Face Image</h2>
        <p class="hint">Text-to-image through Hugging Face InferenceClient. Requires HF_TOKEN, CLOUD_ALLOWED=true, and consent.</p>
        <textarea class="tool-textarea" id="hfImagePrompt" placeholder="Astronaut riding a horse"></textarea>
        <input class="tool-input" id="hfImageModel" value="black-forest-labs/FLUX.1-dev">
        <input class="tool-input" id="hfImageProvider" value="wavespeed">
        <button class="tool-button" id="hfImageBtn">Generate HF Image</button>
        <div class="tool-output" id="hfImageOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Hugging Face Feature Extraction</h2>
        <p class="hint">Creates feature vectors/embeddings for approved text. Requires HF_TOKEN, CLOUD_ALLOWED=true, and consent.</p>
        <textarea class="tool-textarea" id="hfFeatureText" placeholder="Today is a sunny day and I will get some ice cream."></textarea>
        <input class="tool-input" id="hfFeatureModel" value="microsoft/harrier-oss-v1-0.6b">
        <input class="tool-input" id="hfFeatureProvider" value="hf-inference">
        <button class="tool-button" id="hfFeatureBtn">Extract HF Features</button>
        <div class="tool-output" id="hfFeatureOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Local Transformers Chat</h2>
        <p class="hint">Run a local Hugging Face text-generation model such as Gemma. Keep local-files-only on to avoid downloads.</p>
        <textarea class="tool-textarea" id="transformersPrompt" placeholder="Who are you? Please answer in pirate-speak."></textarea>
        <input class="tool-input" id="transformersModel" value="google/gemma-2-2b-it">
        <select class="tool-select" id="transformersDevice">
          <option value="auto">Auto device</option>
          <option value="mps">Mac MPS</option>
          <option value="cpu">CPU</option>
          <option value="cuda">CUDA</option>
        </select>
        <input class="tool-input" id="transformersMaxTokens" type="number" min="1" max="2048" value="256">
        <label class="hint"><input type="checkbox" id="transformersLocalOnly" checked> local files only</label>
        <button class="tool-button" id="transformersBtn">Run Local Transformers</button>
        <div class="tool-output" id="transformersOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Images + MP3 Video</h2>
        <input class="tool-input" id="imageVideoAudioPath" placeholder="MP3/audio path">
        <textarea class="tool-textarea" id="imageVideoPaths" placeholder="Image paths, one per line or comma-separated"></textarea>
        <textarea class="tool-textarea" id="imageVideoPrompt" placeholder="Describe this image music video"></textarea>
        <input class="tool-input" id="imageVideoDuration" type="number" min="4" max="300" value="45">
        <select class="tool-select" id="imageVideoAspect">
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
          <option value="1:1">1:1</option>
        </select>
        <button class="tool-button" id="imageVideoBtn">Render Images + MP3 MP4</button>
        <div class="tool-output" id="imageVideoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Advanced Local Video Draft</h2>
        <p class="hint">Local FFmpeg draft: audio-directed scenes, camera motion, emotion grading, pitch activity, storyboard, and movie prompt pack. This is not true AI-generated video frames.</p>
        <input class="tool-input" id="advancedAudioPath" placeholder="MP3/audio path">
        <textarea class="tool-textarea" id="advancedImagePaths" placeholder="Scene image paths, one per line"></textarea>
        <textarea class="tool-textarea" id="advancedPrompt" placeholder="Movie story, characters, locations, emotion, and visual style"></textarea>
        <textarea class="tool-textarea" id="advancedLyrics" placeholder="Optional lyrics, one line at a time"></textarea>
        <input class="tool-input" id="advancedDuration" type="number" min="4" max="900" value="45">
        <select class="tool-select" id="advancedAspect">
          <option value="16:9">16:9 Movie</option>
          <option value="9:16">9:16 Vertical</option>
          <option value="1:1">1:1 Square</option>
        </select>
        <button class="tool-button" id="advancedVideoBtn">Render Local Movie Draft</button>
        <div class="tool-output" id="advancedVideoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Freebeat-Style Director</h2>
        <input class="tool-input" id="directorAudioPath" placeholder="Audio path or uploaded file path">
        <textarea class="tool-textarea" id="directorPrompt" placeholder="Music video idea, e.g. neon city dance story"></textarea>
        <input class="tool-input" id="directorStyle" value="cinematic" placeholder="Style">
        <select class="tool-select" id="directorMode">
          <option value="story">Story</option>
          <option value="stage">Stage</option>
          <option value="lyrics">Lyrics</option>
          <option value="visualizer">Visualizer</option>
        </select>
        <select class="tool-select" id="directorAspect">
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
          <option value="1:1">1:1</option>
        </select>
        <textarea class="tool-textarea" id="directorLyrics" placeholder="Optional lyrics, one line at a time"></textarea>
        <button class="tool-button" id="directorBtn">Create Director Plan</button>
        <div class="tool-output" id="directorOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">WhatsApp Messenger</h2>
        <p class="hint">Draft a WhatsApp message link locally, or send through the official WhatsApp Cloud API with consent.</p>
        <input class="tool-input" id="whatsappTo" placeholder="Recipient phone, e.g. +94771234567">
        <textarea class="tool-textarea" id="whatsappMessage" placeholder="Message to send"></textarea>
        <button class="tool-button" id="whatsappDraftBtn">Create WhatsApp Draft</button>
        <button class="tool-button" id="whatsappSendBtn">Send via WhatsApp API</button>
        <input class="tool-input" id="whatsappSearchQuery" placeholder="Search saved WhatsApp messages">
        <button class="tool-button" id="whatsappSearchBtn">Retrieve WhatsApp Items</button>
        <div class="tool-output" id="whatsappOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Neural Lip-Sync</h2>
        <div class="hint" id="lipBackendStatus">Checking local neural backend...</div>
        <input class="tool-input" id="lipAudioPath" placeholder="Audio path or uploaded MP3">
        <input class="tool-input" id="lipFacePath" placeholder="Consented face image/video path">
        <textarea class="tool-textarea" id="lipPrompt" placeholder="Example: respectful singer lip-sync for this song, stable face, accurate mouth timing"></textarea>
        <select class="tool-select" id="lipEmotion">
          <option value="cinematic">Cinematic emotion</option>
          <option value="happy">Happy</option>
          <option value="sad">Sad</option>
          <option value="calm">Calm</option>
          <option value="intense">Intense</option>
        </select>
        <input class="tool-input" id="lipDuration" type="number" min="1" max="300" value="2">
        <button class="tool-button" id="lipBtn">Create Lip-Sync Plan</button>
        <button class="tool-button" id="lipRenderBtn">Render Neural Lip-Sync</button>
        <div class="tool-output" id="lipOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Coding App</h2>
        <p class="hint">Coding Split mode: offline coding planner creates a copied workspace, candidate files, patch skeleton, and code-line CSV for review.</p>
        <textarea class="tool-textarea" id="codeFeature" placeholder="Feature to plan offline, e.g. add file preview"></textarea>
        <button class="tool-button" id="codeBtn">Create Vibe Code Plan</button>
        <button class="tool-button" id="selfCodeBtn">Implement in Isolated Copy</button>
        <div class="tool-output" id="codeOutput"></div>
        <div class="code-section-title" style="margin-top:16px;">Code + Output</div>
        <select class="tool-input" id="codeLanguage"><option value="python">Python</option><option value="javascript">JavaScript</option></select>
        <textarea class="tool-textarea" id="codeEditor" spellcheck="false" placeholder="Write code to run in the sandbox">print("Hello from Gima")</textarea>
        <button class="tool-button" id="runCodeBtn">Run Code</button>
        <div class="tool-output" id="codeRunOutput"></div>
      </div>
    </section>
  </div>
  <script>
    const chat = document.getElementById('chat');
    const form = document.getElementById('form');
    const message = document.getElementById('message');
    const send = document.getElementById('send');
    const fileList = document.getElementById('fileList');
    const attachmentBar = document.getElementById('attachmentBar');
    const chatStatus = document.getElementById('chatStatus');
    const emptyState = document.getElementById('emptyState');
    const modelChip = document.getElementById('modelChip');
    const routePreviewChip = document.getElementById('routePreviewChip');
    const drawerBackdrop = document.getElementById('drawerBackdrop');
    const leftDrawerBtn = document.getElementById('leftDrawerBtn');
    const rightDrawerBtn = document.getElementById('rightDrawerBtn');
    const addSheetBackdrop = document.getElementById('addSheetBackdrop');
    const addSheetClose = document.getElementById('addSheetClose');
    const enterSendSetting = document.getElementById('enterSendSetting');
    let pendingAttachments = [];
    let deferredInstallPrompt = null;
    let screenRecorder = null;
    let screenRecordStream = null;
    let screenRecordChunks = [];
    let routePreviewTimer = null;
    let routePreviewController = null;

    function setChatStatus(text) {
      chatStatus.textContent = text;
    }

    function routeModeForChatProvider(provider) {
      if (provider === 'local') return 'LOCAL_ONLY';
      return 'CLOUD_ONLY';
    }

    function inferRoutePrivacy(text) {
      return /api key|password|secret|private document/i.test(text || '') ? 'high' : 'normal';
    }

    function setRoutePreview(plan, provider = 'local') {
      if (!routePreviewChip) return;
      const routeProvider = plan?.provider || (provider === 'local' ? 'local' : provider);
      const task = plan?.task_category || 'GENERAL_CHAT';
      const model = plan?.model || (provider === 'local' ? 'local brain' : provider);
      const cloudBlocked = provider !== 'local' && (routeProvider === 'local' || plan?.cloud_allowed === false);
      routePreviewChip.hidden = false;
      routePreviewChip.classList.toggle('local', routeProvider === 'local');
      routePreviewChip.classList.toggle('cloud', routeProvider !== 'local');
      routePreviewChip.classList.toggle('blocked', cloudBlocked);
      routePreviewChip.innerHTML =
        `<strong>route</strong> ` +
        `<span>${escapeHtml(routeProvider)}</span>` +
        `<span>${escapeHtml(task.replace(/_/g, ' ').toLowerCase())}</span>` +
        `<span>${escapeHtml(modelLabel(model))}</span>` +
        (cloudBlocked ? `<span>${plan?.cloud_allowed === false && routeProvider !== 'local' ? 'cloud off' : 'privacy local'}</span>` : '');
    }

    function scheduleRoutePreview() {
      if (!routePreviewChip) return;
      clearTimeout(routePreviewTimer);
      routePreviewTimer = setTimeout(refreshRoutePreview, 260);
    }

    async function refreshRoutePreview() {
      if (!routePreviewChip) return;
      const text = message.value.trim();
      const provider = document.getElementById('chatProvider')?.value || 'local';
      if (!text) {
        setRoutePreview({provider: provider === 'local' ? 'local' : provider, task_category: 'READY', model: provider === 'local' ? 'local brain' : provider}, provider);
        return;
      }
      if (routePreviewController) routePreviewController.abort();
      routePreviewController = new AbortController();
      const params = new URLSearchParams({
        message: text.slice(0, 4000),
        mode: routeModeForChatProvider(provider),
        privacy: inferRoutePrivacy(text),
        has_images: pendingAttachments.some(file => /^image\\//i.test(file.type || '') || /\\.(png|jpe?g|webp|gif)$/i.test(file.name || file.path || '')) ? '1' : '0',
      });
      try {
        const res = await fetch('/api/ai-router/plan?' + params.toString(), { signal: routePreviewController.signal });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const plan = await res.json();
        setRoutePreview(plan, provider);
      } catch (error) {
        if (error.name === 'AbortError') return;
        setRoutePreview({provider: provider === 'local' ? 'local' : provider, task_category: 'PREVIEW_OFFLINE', model: provider}, provider);
      }
    }

    function addMessage(role, text, files = [], meta = {}) {
      chat.classList.add('has-messages');
      if (emptyState) emptyState.hidden = true;
      const row = document.createElement('div');
      row.className = `message ${role}`;
      row.innerHTML = `<div class="avatar">${role === 'user' ? 'You' : 'G'}</div><div class="bubble"></div>`;
      const bubble = row.querySelector('.bubble');
      if (role === 'assistant') {
        bubble.innerHTML = renderChatContent(text, files, meta);
        attachCopyActions(bubble, text, files);
      } else {
        bubble.textContent = text;
      }
      chat.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
    }

    function openDrawer(side, focusId = '') {
      const compact = window.matchMedia('(max-width: 980px)').matches;
      if (side === 'left' && !compact) {
        document.body.classList.remove('show-left', 'show-right');
        focusPanelTarget(focusId);
        return;
      }
      document.body.classList.toggle('show-left', side === 'left');
      document.body.classList.toggle('show-right', side === 'right');
      focusPanelTarget(focusId);
    }

    function focusPanelTarget(focusId = '') {
      if (focusId) {
        setTimeout(() => {
          const target = document.getElementById(focusId);
          if (target) {
            target.scrollIntoView({ block: 'center', behavior: 'smooth' });
            if (typeof target.focus === 'function') target.focus({ preventScroll: true });
          }
        }, 240);
      }
    }

    function closeDrawers() {
      document.body.classList.remove('show-left', 'show-right');
    }

    function openAddSheet() {
      closeDrawers();
      document.body.classList.add('show-add-sheet');
    }

    function closeAddSheet() {
      document.body.classList.remove('show-add-sheet');
    }

    function chooseFiles(accept = '') {
      const input = document.getElementById('chatFileInput');
      input.setAttribute('accept', accept || '');
      closeAddSheet();
      input.click();
    }

    function updateAssistantMessage(bubble, text, files = [], meta = {}) {
      bubble.innerHTML = renderChatContent(text, files, meta);
      attachCopyActions(bubble, text, files);
      chat.scrollTop = chat.scrollHeight;
    }

    function renderChatContent(text, files = [], meta = {}) {
      let html = renderMarkdownLite(text || '');
      if (files && files.length) {
        html += renderFileCards(files, 'generated');
      }
      if (meta && meta.elapsed_seconds !== undefined) {
        html += `<div class="response-meta">response time: ${escapeHtml(meta.elapsed_seconds)}s${meta.used_brain ? ' | used brain.csv' : ''}${meta.used_internet ? ' | used internet' : ''}</div>`;
      }
      return html;
    }

    function attachCopyActions(bubble, text, files = []) {
      bubble.dataset.fullText = text || '';
      bubble.dataset.fullTextWithFiles = fullCopyText(text || '', files);
      const row = document.createElement('div');
      row.className = 'copy-row';
      row.innerHTML = `
        <button class="copy-button" type="button" data-copy-kind="answer">Copy full answer</button>
        <button class="copy-button" type="button" data-copy-kind="answer-files">Copy answer + files</button>
        <button class="copy-button" type="button" data-copy-kind="plain">Plain text</button>
      `;
      row.querySelectorAll('[data-copy-kind]').forEach(button => {
        button.addEventListener('click', async () => {
          const kind = button.dataset.copyKind;
          const value = kind === 'answer-files'
            ? bubble.dataset.fullTextWithFiles
            : bubble.dataset.fullText;
          await copyText(value);
          const old = button.textContent;
          button.textContent = 'Copied';
          setTimeout(() => { button.textContent = old; }, 1200);
        });
      });
      bubble.appendChild(row);
      bubble.querySelectorAll('[data-code-copy]').forEach(button => {
        button.addEventListener('click', async () => {
          await copyText(button.dataset.code || '');
          const old = button.textContent;
          button.textContent = 'Copied';
          setTimeout(() => { button.textContent = old; }, 1200);
        });
      });
    }

    function fullCopyText(text, files = []) {
      const fileLines = (files || []).map(file => {
        const path = file.path || '';
        return `- ${file.name || path}: ${path}`;
      });
      if (!fileLines.length) return text;
      return `${text}\\n\\nGenerated files:\\n${fileLines.join('\\n')}`;
    }

    async function copyText(value) {
      const text = String(value ?? '');
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.left = '-9999px';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }

    function renderMarkdownLite(text) {
      const lines = String(text ?? '').split('\\n');
      const html = [];
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].trim().startsWith('```')) {
          const codeLines = [];
          i++;
          while (i < lines.length && !lines[i].trim().startsWith('```')) {
            codeLines.push(lines[i]);
            i++;
          }
          const code = codeLines.join('\\n');
          html.push(`<div class="code-wrap"><button class="code-copy" type="button" data-code-copy="1" data-code="${escapeHtml(code)}">Copy code</button><pre><code>${escapeHtml(code)}</code></pre></div>`);
          continue;
        }
        if (lines[i].trim().startsWith('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
          const headers = parseTableRow(lines[i]);
          i += 2;
          const rows = [];
          while (i < lines.length && lines[i].trim().startsWith('|')) {
            rows.push(parseTableRow(lines[i]));
            i++;
          }
          i--;
          html.push('<table><thead><tr>' + headers.map(cell => `<th>${inlineFormat(cell)}</th>`).join('') + '</tr></thead><tbody>' +
            rows.map(row => '<tr>' + row.map(cell => `<td>${inlineFormat(cell)}</td>`).join('') + '</tr>').join('') +
            '</tbody></table>');
          continue;
        }
        const line = lines[i];
        if (!line.trim()) {
          html.push('<br>');
        } else {
          html.push(inlineFormat(line));
        }
      }
      return html.join('\\n');
    }

    function parseTableRow(line) {
      return line.trim().replace(/^\\|/, '').replace(/\\|$/, '').split('|').map(cell => cell.trim());
    }

    function inlineFormat(value) {
      const escaped = escapeHtml(value);
      return escaped
        .replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>')
        .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noreferrer">$1</a>');
    }

    async function refreshStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('brain').textContent = data.brain.ready ? 'running' : (data.brain.running ? 'starting' : 'stopped');
      document.getElementById('model').textContent = modelLabel(data.model || data.brain?.models || '') || 'not configured';
      renderLocalModelSelector(data);
      if (modelChip) modelChip.hidden = true;
      document.getElementById('memory').textContent = data.memory_rows + ' rows';
      document.getElementById('downloadsPath').textContent = data.downloads || '';
      document.getElementById('handsInPath').textContent = data.hands_in || '';
      document.getElementById('handsPath').textContent = data.hands || '';
      document.getElementById('handsOutPath').textContent = data.hands_out || '';
      document.getElementById('stomachPath').textContent = data.stomach || '';
      document.getElementById('continuousPath').textContent = data.continuous || '';
      document.getElementById('brainCsvPath').textContent = `${data.brain_csv || ''} (${data.brain_csv_rows || 0} rows)`;
    }

    function renderLocalModelSelector(data) {
      const select = document.getElementById('localModelSelect');
      const hint = document.getElementById('localModelHint');
      if (!select || !hint) return;
      const levels = data.model_levels || [];
      select.innerHTML = levels.map(level => {
        const status = level.level === data.active_model_level ? `active/${level.status || 'unknown'}` : (level.status || (level.available ? 'ready' : 'missing'));
        const gemmaNote = level.level === 'gemma4_12b' && level.available ? ' — Gemma available' : '';
        const label = `${level.name || level.level} — ${status}${gemmaNote}`;
        return `<option value="${escapeHtml(level.level)}" ${level.available ? '' : 'disabled'}>${escapeHtml(label)}</option>`;
      }).join('');
      if (data.active_model_level) select.value = data.active_model_level;
      const active = levels.find(level => level.level === data.active_model_level);
      const gemma = levels.find(level => level.level === 'gemma4_12b');
      hint.innerHTML =
        `Active: <span class="pill">${escapeHtml(data.active_model_level || 'unknown')}</span>` +
        (active ? `<br>${escapeHtml(active.description || '')}` : '') +
        (gemma ? `<br>Gemma 4 12B: <span class="pill">${escapeHtml(gemma.status || (gemma.available ? 'ready' : 'missing'))}</span>` : '');
    }

    function modelChipHtml(model) {
      const label = modelLabel(model);
      const clean = label.replace(/\.gguf$/i, '');
      const parts = clean.split(/[-_\\s]+/).filter(Boolean);
      const family = parts.slice(0, 2).join(' ') || 'local';
      const badges = [];
      if (/1\\.5b/i.test(label)) badges.push('1.5B');
      if (/3b/i.test(label)) badges.push('3B');
      if (/7b/i.test(label)) badges.push('7B');
      if (/instruct/i.test(label)) badges.push('instruct');
      const quant = (label.match(/q\\d+_k_[msl]/i) || label.match(/q\\d+_[a-z0-9]+/i) || [])[0];
      if (quant) badges.push(quant.toLowerCase() + '.gguf');
      if (!badges.length && label !== family) badges.push(label);
      return escapeHtml(family) + ' ' + badges.slice(0, 3).map(item => `<span>${escapeHtml(item)}</span>`).join('');
    }

    function modelLabel(model) {
      if (!model) return 'local model';
      if (typeof model === 'string') return model.split('/').pop() || model;
      if (model.name) return String(model.name).split('/').pop();
      if (model.id) return String(model.id).split('/').pop();
      if (Array.isArray(model.models) && model.models.length) return modelLabel(model.models[0]);
      if (Array.isArray(model.data) && model.data.length) return modelLabel(model.data[0]);
      return 'local model';
    }

    async function refreshBindings() {
      const [bindingsRes, quotaRes] = await Promise.all([fetch('/api/bindings'), fetch('/api/free-quotas')]);
      const data = await bindingsRes.json();
      const quotaData = await quotaRes.json();
      const bindings = data.bindings || [];
      document.getElementById('bindingStatus').innerHTML = bindings.map(binding => {
        const state = binding.status || (binding.available === 'yes' ? 'linked' : 'missing');
        const label = binding.available === 'yes'
          ? `linked (${escapeHtml(binding.masked)})`
          : state === 'invalid'
            ? `invalid (${escapeHtml(binding.masked)})`
            : 'not linked';
        return `<div class="status-row"><span>${escapeHtml(binding.provider)}</span><span class="pill">${label}</span></div>`;
      }).join('');
      document.getElementById('quotaStatus').innerHTML =
        `<div class="status-row"><span>Free quota mode</span><span class="pill">${quotaData.free_quota_mode ? 'on' : 'off'}</span></div>` +
        (quotaData.quotas || []).map(row =>
          `<div class="status-row"><span>${escapeHtml(row.provider)}</span><span class="pill">${escapeHtml(row.remaining)}/${escapeHtml(row.limit)} left</span></div>`
        ).join('');
    }

    async function refreshOpenRouterModels(refresh = false) {
      const search = document.getElementById('openrouterModelSearch').value.trim();
      const params = new URLSearchParams({ output_modalities: 'all', limit: '300' });
      if (search) params.set('q', search);
      if (refresh) params.set('refresh', '1');
      const [data, routing] = await Promise.all([
        fetch('/api/openrouter/models?' + params.toString()).then(res => res.json()),
        fetch('/api/openrouter/routing').then(res => res.json()),
      ]);
      if (data.error) {
        setOutput('openrouterModelOutput', data);
        return data;
      }
      if (!routing.error) {
        document.getElementById('openrouterRoutingSort').value = routing.routing_sort || 'latency';
        document.getElementById('openrouterDataCollection').value = routing.data_collection || 'deny';
        document.getElementById('openrouterFallbackModels').value = (routing.fallback_models || []).join(', ');
      }
      const select = document.getElementById('openrouterModelSelect');
      select.innerHTML = (data.models || []).map(model => {
        const tags = [
          model.free ? 'free' : '',
          (model.output_modalities || []).join('+'),
          model.context_length ? `${model.context_length} ctx` : '',
        ].filter(Boolean).join(' · ');
        const label = `${model.id}${model.name && model.name !== model.id ? ' — ' + model.name : ''}${tags ? ' — ' + tags : ''}`;
        return `<option value="${escapeHtml(model.id)}">${escapeHtml(label)}</option>`;
      }).join('');
      if (data.selected_model) select.value = data.selected_model;
      document.getElementById('openrouterModelOutput').innerHTML =
        `<b>OpenRouter catalog:</b> ${escapeHtml(data.count)} matched, ${escapeHtml(data.returned)} shown from ${escapeHtml(data.source)}.` +
        (data.selected_model ? `<br>Selected: <span class="pill">${escapeHtml(data.selected_model)}</span>` : '<br>No selected model yet.') +
        (!routing.error ? `<br>Routing: <span class="pill">${escapeHtml(routing.routing_sort)}</span> · data collection ${escapeHtml(routing.data_collection)}` : '');
      return data;
    }

    async function refreshDashboards() {
      const [capabilities, doctor, codexMode, aiTaskMap, localAiStack, paidOpenRouter, deployments, agents, outputs, folders, apps, lipBackend, musicApi] = await Promise.all([
        fetch('/api/capabilities').then(res => res.json()),
        fetch('/api/doctor').then(res => res.json()),
        fetch('/api/codex-mode').then(res => res.json()),
        fetch('/api/ai-task-map').then(res => res.json()),
        fetch('/api/local-ai-stack').then(res => res.json()),
        fetch('/api/openrouter/paid-plan').then(res => res.json()),
        fetch('/api/deployments').then(res => res.json()),
        fetch('/api/agents').then(res => res.json()),
        fetch('/api/outputs').then(res => res.json()),
        fetch('/api/folders').then(res => res.json()),
        fetch('/api/apps').then(res => res.json()),
        fetch('/api/media/lip-sync-status').then(res => res.json()),
        fetch('/api/media/music-api-status').then(res => res.json()),
      ]);
      const lipStatus = document.getElementById('lipBackendStatus');
      if (lipStatus) {
        lipStatus.textContent = lipBackend.ready
          ? `SadTalker ready (${lipBackend.checkpoint_count} checkpoint)`
          : `Neural backend not ready: ${(lipBackend.missing || []).join(', ')}. Expected at ${lipBackend.backend_dir || ''}`;
      }
      const musicApiOutput = document.getElementById('musicApiOutput');
      if (musicApiOutput && musicApi.providers) {
        musicApiOutput.innerHTML = `<b>Cloud allowed:</b> ${musicApi.cloud_allowed ? 'yes' : 'no'}<br>` +
          musicApi.providers.map(provider =>
            `<span class="pill">${escapeHtml(provider.ready ? 'ready' : 'setup needed')}</span> ${escapeHtml(provider.label)}<br><span class="hint">${escapeHtml(provider.endpoint || provider.env.join(', '))}</span>`
          ).join('<br>');
      }
      document.getElementById('folderMap').innerHTML = (folders.folders || []).map(item =>
        `<div class="folder-row"><b>${escapeHtml(item.name)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.purpose)}<br><span class="hint">${escapeHtml(item.path)}</span></div>`
      ).join('') || '<div class="file-chip">No folders yet.</div>';
      document.getElementById('capabilityList').innerHTML = (capabilities.capabilities || []).map(item =>
        `<div class="file-chip"><b>${escapeHtml(item.capability)}</b><br><span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.local_support)}</div>`
      ).join('') || '<div class="file-chip">No capabilities yet.</div>';
      const hardware = doctor.hardware || {};
      const doctorMini = document.getElementById('doctorMini');
      if (doctorMini) {
        doctorMini.innerHTML = `<div class="status-row"><span>PC AI mode</span><span class="pill">${escapeHtml(doctor.mode || 'unknown')}</span></div>` +
          `<div class="hint">${escapeHtml(hardware.cpu || '')}<br>${escapeHtml(hardware.memory_gb || 0)} GB RAM | ${escapeHtml(doctor.recommended_model || '')}</div>`;
      }
      document.getElementById('doctorPlanList').innerHTML =
        `<div class="file-chip"><b>Readiness ${escapeHtml(doctor.readiness_score || 0)}%</b> <span class="pill">${escapeHtml(doctor.mode || 'unknown')}</span><br>${escapeHtml(doctor.strategy || '')}<br><span class="hint">${escapeHtml(doctor.recommended_model || '')}</span></div>` +
        ((doctor.improvement_plan || []).map(item =>
          `<div class="file-chip"><b>${escapeHtml(item.phase)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.action)}<br><span class="hint">${escapeHtml(item.why)}</span></div>`
        ).join('') || '') +
        (doctor.daily_improvement_plan
          ? `<div class="file-chip"><b>Daily world-class plan</b> <span class="pill">${escapeHtml(doctor.daily_improvement_plan.date)}</span><br>${escapeHtml(doctor.daily_improvement_plan.today_priority)}<br><span class="hint">${escapeHtml(doctor.daily_improvement_plan.success_rule)}</span></div>` +
            ((doctor.daily_improvement_plan.daily_actions || []).map(item =>
              `<div class="file-chip"><b>Today: ${escapeHtml(item.track)}</b><br>${escapeHtml(item.action)}<br><span class="hint">${escapeHtml(item.done_when)}</span></div>`
            ).join('') || '')
          : '') +
        ((doctor.growth_plan || []).map(item =>
          `<div class="file-chip"><b>Growth: ${escapeHtml(item.phase)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.action)}<br><span class="hint">${escapeHtml(item.approval_required)}</span></div>`
        ).join('') || '') +
        ((doctor.hardware_upgrade_plan || []).map(item =>
          `<div class="file-chip"><b>Hardware: ${escapeHtml(item.target)}</b><br>${escapeHtml(item.upgrade)}<br><span class="hint">${escapeHtml(item.benefit)}</span></div>`
        ).join('') || '') +
        ((doctor.legal_earning_plan || []).map(item =>
          `<div class="file-chip"><b>Legal offer: ${escapeHtml(item.offer)}</b><br>${escapeHtml(item.output)}<br><span class="hint">${escapeHtml(item.legal_check)}</span></div>`
        ).join('') || '') +
        (doctor.master_ai_director_plan
          ? `<div class="file-chip"><b>Master AI Director</b> <span class="pill">${escapeHtml(doctor.master_ai_director_plan.kind || 'director')}</span><br>${escapeHtml(doctor.master_ai_director_plan.hardware_reality || '')}<br><span class="hint">${escapeHtml(doctor.master_ai_director_plan.north_star || '')}</span></div>` +
            ((doctor.master_ai_director_plan.routing_rules || []).map(item =>
              `<div class="file-chip"><b>Route: ${escapeHtml(item.task)}</b><br>${escapeHtml(item.local_first)}<br><span class="hint">Cloud: ${escapeHtml(item.cloud_when)}<br>Output: ${escapeHtml(item.output)}</span></div>`
            ).join('') || '') +
            ((doctor.master_ai_director_plan.agent_roles || []).map(item =>
              `<div class="file-chip"><b>Agent: ${escapeHtml(item.agent)}</b><br>${escapeHtml(item.job)}</div>`
            ).join('') || '')
          : '') +
        (doctor.own_model_plan
          ? `<div class="file-chip"><b>Own model path</b> <span class="pill">${escapeHtml(doctor.own_model_plan.status)}</span><br>${escapeHtml(doctor.own_model_plan.realistic_strategy)}<br><span class="hint">${escapeHtml(doctor.own_model_plan.why_not_from_scratch)}</span></div>` +
            ((doctor.own_model_plan.stages || []).map(item =>
              `<div class="file-chip"><b>${escapeHtml(item.stage)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.action)}</div>`
            ).join('') || '')
          : '') +
        ((doctor.next_actions || []).length
          ? `<div class="file-chip"><b>Next fixes</b><br>${(doctor.next_actions || []).map(action => `- ${escapeHtml(action)}`).join('<br>')}</div>`
          : '') +
        ((doctor.criticism_defense_matrix || []).length
          ? `<div class="file-chip"><b>Credibility and defense matrix</b><br>${(doctor.criticism_defense_matrix || []).map(row =>
              `<b>${escapeHtml(row.criticism)}</b>: ${escapeHtml(row.defense)}<br><span class="hint">${escapeHtml(row.implementation)}</span>`
            ).join('<br>')}</div>`
          : '');
      const localFiles = localAiStack.files || {};
      document.getElementById('localAiStackList').innerHTML =
        `<div class="file-chip"><b>${escapeHtml(localAiStack.hardware?.cpu || '')}</b> <span class="pill">${escapeHtml(localAiStack.hardware?.ram_gb || 0)} GB RAM</span><br>${escapeHtml(localAiStack.hardware?.strategy || '')}</div>` +
        ((localAiStack.tools || []).map(item =>
          `<div class="file-chip"><b>${escapeHtml(item.area)}</b> <span class="pill">works: ${escapeHtml(item.works_on_laptop || item.fit)}</span><br>` +
          `${escapeHtml(item.tool)} · ${escapeHtml(item.models)}<br>` +
          `<span class="hint">Update: ${escapeHtml(item.update_possible || 'Yes')} · ${escapeHtml(item.notes)}</span></div>`
        ).join('') || '') +
        `<div class="file-chip"><b>Downloads</b><br>` +
        (localFiles.csv ? `<a href="/api/download?path=${encodeURIComponent(localFiles.csv)}">CSV table</a><br>` : '') +
        (localFiles.markdown ? `<a href="/api/download?path=${encodeURIComponent(localFiles.markdown)}">Markdown plan</a><br>` : '') +
        (localFiles.json ? `<a href="/api/download?path=${encodeURIComponent(localFiles.json)}">JSON data</a>` : '') +
        `</div>`;
      renderPaidOpenRouterPlan(paidOpenRouter);
      document.getElementById('appPlanList').innerHTML = (apps.apps || []).map(item =>
        `<div class="file-chip"><b>${escapeHtml(item.name)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.platforms)}<br><span class="hint">${escapeHtml(item.next)}</span></div>`
      ).join('') || '<div class="file-chip">No app plan yet.</div>';
      document.getElementById('codexModeList').innerHTML = (codexMode.capabilities || []).map(item =>
        `<div class="file-chip"><b>${escapeHtml(item.capability)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.gima_support)}<br><span class="hint">${escapeHtml(item.codex_gap)}</span></div>`
      ).join('') || '<div class="file-chip">Codex Mode is not ready yet.</div>';
      document.getElementById('aiTaskMapList').innerHTML =
        `<div class="file-chip"><b>${escapeHtml(aiTaskMap.path || 'ai_task_map.csv')}</b><br><span class="pill">${escapeHtml(aiTaskMap.status || 'unknown')}</span> ${escapeHtml(aiTaskMap.rows || 0)} rows${renderFileCards([{ path: aiTaskMap.path, name: 'ai_task_map.csv', label: 'csv' }])}</div>` +
        ((aiTaskMap.sample || []).map(item =>
          `<div class="file-chip"><b>${escapeHtml(item.letter)}: ${escapeHtml(item.task)}</b> <span class="pill">${escapeHtml(item.gima_status)}</span><br>${escapeHtml(item.provider_examples)}<br>${escapeHtml(item.public_sources)}</div>`
        ).join('') || '');
      document.getElementById('deploymentList').innerHTML = (deployments.deployments || []).map(item =>
        `<div class="file-chip"><b>${escapeHtml(item.name)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.detail)}</div>`
      ).join('') || '<div class="file-chip">No deployment status.</div>';
      document.getElementById('agentList').innerHTML = (agents.agents || []).map(item =>
        `<div class="file-chip"><b>${escapeHtml(item.name)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.detail)}${item.path ? `<br><span>${escapeHtml(item.path)}</span>` : ''}</div>`
      ).join('') || '<div class="file-chip">No agents yet. Create a vibe code plan.</div>';
      document.getElementById('outputList').innerHTML = (outputs.outputs || []).map(item =>
        renderFileCard({ path: item.path, name: item.name, label: item.kind || 'output', size: item.size_label || '' })
      ).join('') || '<div class="file-chip">No outputs yet.</div>';
    }

    function renderPaidOpenRouterPlan(data) {
      const files = data.files || {};
      const rows = data.recommendations || [];
      document.getElementById('paidOpenRouterList').innerHTML =
        `<div class="file-chip"><b>Catalog</b> <span class="pill">${escapeHtml(data.catalog_count || 0)} models</span><br>${escapeHtml(data.source || '')}<br><span class="hint">${escapeHtml((data.cost_controls || [])[0] || '')}</span></div>` +
        rows.map(row =>
          `<div class="file-chip"><b>${escapeHtml(row.area)}</b> <span class="pill">${escapeHtml(row.paid_model_type || 'paid model')}</span><br>` +
          `Use: ${escapeHtml(row.need)}<br>` +
          `First: ${escapeHtml(row.first_choice)}<br>` +
          `Cheap: ${escapeHtml(row.cheap_choice)}<br>` +
          `<span class="hint">Local: ${escapeHtml(row.local_fallback)}</span><br>` +
          `<span class="hint">Note: ${escapeHtml(row.note || row.freshness_warning || '')}</span></div>`
        ).join('') +
        `<div class="file-chip"><b>Downloads</b><br>` +
        (files.csv ? `<a href="/api/download?path=${encodeURIComponent(files.csv)}">CSV table</a><br>` : '') +
        (files.markdown ? `<a href="/api/download?path=${encodeURIComponent(files.markdown)}">Markdown plan</a><br>` : '') +
        (files.json ? `<a href="/api/download?path=${encodeURIComponent(files.json)}">JSON data</a>` : '') +
        `</div>`;
    }

    async function apiPost(path, payload) {
      const res = await fetch(path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      return await res.json();
    }

    function setOutput(id, data) {
      const output = document.getElementById(id);
      if (typeof data === 'string') {
        output.textContent = data;
        return;
      }
      if (data && data.error) {
        output.textContent = 'Error: ' + data.error;
        return;
      }
      output.innerHTML = renderResult(data);
      attachResultActions(output, data);
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[char]));
    }

    function downloadUrl(path) {
      return '/api/download?path=' + encodeURIComponent(path);
    }

    function fileKind(nameOrPath) {
      const value = String(nameOrPath || '').toLowerCase();
      if (/\.(png|jpe?g|gif|webp|svg|heic)$/.test(value)) return 'image';
      if (/\.(mp3|wav|m4a|aac|flac|ogg)$/.test(value)) return 'audio';
      if (/\.(mp4|mov|mkv|webm|avi)$/.test(value)) return 'video';
      if (/\.(pdf)$/.test(value)) return 'pdf';
      if (/\.(csv|tsv|xlsx?)$/.test(value)) return 'table';
      if (/\.(py|js|ts|tsx|html|css|json|md|txt|yml|yaml|sh)$/.test(value)) return 'text';
      return 'file';
    }

    function fileSizeLabel(sizeBytes) {
      const size = Number(sizeBytes || 0);
      if (!size) return 'ready';
      if (size < 1024) return `${size} B`;
      if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
      return `${(size / 1024 / 1024).toFixed(1)} MB`;
    }

    function fileDisplayName(path, fallback = '') {
      const value = String(fallback || path || '');
      return value.split('/').filter(Boolean).pop() || value || 'file';
    }

    function renderFileCards(files = [], defaultLabel = 'file') {
      const cards = (files || []).filter(Boolean).map(file => {
        const path = typeof file === 'string' ? file : (file.path || file.output || file.generated_path || '');
        if (!path) return '';
        const name = typeof file === 'string' ? fileDisplayName(path) : (file.name || fileDisplayName(path));
        const label = typeof file === 'string' ? defaultLabel : (file.label || defaultLabel);
        const size = typeof file === 'string' ? '' : fileSizeLabel(file.size_bytes);
        return renderFileCard({ path, name, label, size });
      }).filter(Boolean);
      return cards.length ? `<div class="file-card-list">${cards.join('')}</div>` : '';
    }

    function renderFileCard({ path, name, label = 'file', size = '' }) {
      if (!path) return '';
      const kind = fileKind(path || name);
      const safePath = escapeHtml(path);
      const safeJsPath = escapeJs(path);
      const safeName = escapeHtml(name || fileDisplayName(path));
      const safeLabel = escapeHtml(label || kind);
      const safeSize = size ? ` · ${escapeHtml(size)}` : '';
      return `
        <div class="file-card">
          <div class="file-card-main">
            <span><span class="file-kind">${safeLabel}</span> <span class="file-name">${safeName}</span>${safeSize}</span>
            <span class="copy-row" style="margin:0;padding:0;border:0;gap:6px;">
              <a class="download-button" href="${downloadUrl(path)}" target="_blank" rel="noreferrer">Open</a>
              <a class="download-button" href="${downloadUrl(path)}" download="${safeName}">Download</a>
              <button class="download-button" type="button" onclick="revealFileLocation('${safeJsPath}', this)">Open Location</button>
            </span>
          </div>
          <div class="file-path">${safePath}</div>
        </div>
      `;
    }

    function resultFileEntries(data = {}) {
      const labels = {
        output: 'output',
        output_file: 'terminal output',
        source_file: 'source',
        generated_path: 'generated',
        storyboard: 'storyboard',
        manifest: 'manifest',
        plan: 'plan',
        patch: 'patch',
        coding_log: 'codex log',
        test_log: 'test log',
        patch_skeleton: 'patch',
        snapshot: 'snapshot',
        timing_plan: 'timing',
        backend_plan: 'backend',
        accuracy_rubric: 'rubric',
        script: 'script',
        prompt_pack: 'prompts',
        storyboard: 'storyboard',
        audio_analysis: 'audio analysis',
        backend_log: 'backend log',
      };
      const seen = new Set();
      const entries = [];
      Object.entries(labels).forEach(([key, label]) => {
        const value = data?.[key];
        if (!value || seen.has(value)) return;
        seen.add(value);
        entries.push({ path: value, name: fileDisplayName(value), label });
      });
      return entries;
    }

    function renderResult(data) {
      if (data && data.kind === 'code_execution') {
        return renderCodeRunResult(data);
      }
      if (data && data.update_id && Array.isArray(data.changed_files) && data.patch) {
        return renderCodeExecutionResult(data);
      }
      const json = escapeHtml(JSON.stringify(data, null, 2));
      const parts = ['<b>Done.</b>'];
      const files = resultFileEntries(data);
      if (files.length) parts.push(renderFileCards(files, 'generated'));
      if (files.length) parts.push(`<div class="copy-row">${files.map(file => `<button class="copy-button" type="button" onclick="copyText('${escapeJs(file.path)}')">Copy ${escapeHtml(file.label)} path</button>`).join('')}</div>`);
      parts.push(`<br><button class="copy-button" type="button" onclick="copyText('${escapeJs(JSON.stringify(data, null, 2))}')">Copy full JSON</button>`);
      parts.push(`<pre>${json}</pre>`);
      return parts.join('');
    }

    function renderCodeRunResult(data) {
      const ok = Number(data.exit_code) === 0 && !data.timed_out;
      const terminal = [data.stdout || '', data.stderr ? `stderr:\\n${data.stderr}` : ''].filter(Boolean).join('\\n') || '[no output]';
      const files = resultFileEntries(data);
      return `<div class="code-report">
        <div class="code-report-head"><div><div class="code-report-title">Code execution</div><div>${escapeHtml(data.language || '')} sandbox</div></div><span class="code-status${ok ? '' : ' failed'}">${ok ? 'completed' : 'failed'}</span></div>
        <div class="code-metrics"><span class="code-metric">exit ${Number(data.exit_code)}</span><span class="code-metric">${escapeHtml(data.elapsed_seconds)}s</span><span class="code-metric">network blocked</span></div>
        ${renderCodePanel('Source code', data.code || '', 'code')}
        <div><div class="code-section-title">Terminal output</div><pre class="terminal-output">${escapeHtml(terminal)}</pre></div>
        <div><div class="code-section-title">Artifacts</div>${renderFileCards(files, 'generated')}</div>
        <div class="copy-row"><button class="copy-button" type="button" data-result-copy="code">Copy code</button><button class="copy-button" type="button" data-result-copy="stdout">Copy stdout</button><button class="copy-button" type="button" data-result-copy="stderr">Copy stderr</button></div>
      </div>`;
    }

    function renderCodeExecutionResult(data) {
      const passed = Boolean(data.tests_passed);
      const failed = String(data.status || '').includes('failed');
      const stats = data.diff_stats || {};
      const changed = (data.changed_files || []).map(path => `<span class="changed-file">${escapeHtml(path)}</span>`).join('');
      const files = resultFileEntries(data);
      return `<div class="code-report">
        <div class="code-report-head">
          <div><div class="code-report-title">Codex implementation</div><div>${escapeHtml(data.update_id)}</div></div>
          <span class="code-status${failed ? ' failed' : ''}">${escapeHtml(data.status || 'complete')}</span>
        </div>
        <div class="code-metrics">
          <span class="code-metric">${Number(stats.files || data.changed_files.length)} files</span>
          <span class="code-metric">+${Number(stats.additions || 0)}</span>
          <span class="code-metric">-${Number(stats.deletions || 0)}</span>
          <span class="code-metric">tests ${passed ? 'passed' : 'failed'}</span>
        </div>
        <div class="code-steps">
          <div class="code-step"><span class="code-step-mark">✓</span> Backup and isolated working copy created</div>
          <div class="code-step"><span class="code-step-mark${failed ? ' failed' : ''}">${failed ? '!' : '✓'}</span> Codex edited ${Number(data.changed_files.length)} file(s)</div>
          <div class="code-step"><span class="code-step-mark${passed ? '' : ' failed'}">${passed ? '✓' : '!'}</span> Test suite ${passed ? 'passed' : 'needs attention'}</div>
          <div class="code-step"><span class="code-step-mark">○</span> Waiting for review and parent-approved sync</div>
        </div>
        <div><div class="code-section-title">Changed files</div><div class="changed-file-list">${changed || '<span>None</span>'}</div></div>
        ${renderCodePanel('Unified diff', data.patch_preview || 'No text diff was generated.', 'patch_preview')}
        ${renderCodePanel('Codex output', data.coding_output || 'No Codex output captured.', 'coding_output')}
        ${renderCodePanel('Test output', data.test_output || 'No test output captured.', 'test_output')}
        <div><div class="code-section-title">Artifacts</div>${renderFileCards(files, 'generated')}</div>
        <div class="copy-row"><button class="copy-button" type="button" data-result-copy="patch_preview">Copy patch</button><button class="copy-button" type="button" data-result-copy="coding_output">Copy Codex output</button><button class="copy-button" type="button" data-result-copy="test_output">Copy test output</button></div>
        <div class="file-path">Working copy: ${escapeHtml(data.working_copy || '')}</div>
        <div>${escapeHtml(data.next_step || '')}</div>
      </div>`;
    }

    function renderCodePanel(label, text, key) {
      return `<div><div class="code-section-title">${escapeHtml(label)}</div><div class="code-wrap"><span class="code-label">${escapeHtml(label)}</span><button class="code-copy" type="button" data-result-copy="${escapeHtml(key)}">Copy</button><pre><code>${escapeHtml(text)}</code></pre></div></div>`;
    }

    function attachResultActions(output, data) {
      output.querySelectorAll('[data-result-copy]').forEach(button => {
        button.addEventListener('click', async () => {
          await copyText(data?.[button.dataset.resultCopy] || '');
          const old = button.textContent;
          button.textContent = 'Copied';
          setTimeout(() => { button.textContent = old; }, 1200);
        });
      });
    }

    async function revealFileLocation(path, button) {
      const original = button?.textContent || 'Open Location';
      if (button) {
        button.disabled = true;
        button.textContent = 'Opening...';
      }
      try {
        const response = await fetch('/api/reveal', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({path}),
        });
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`);
        if (button) button.textContent = 'Opened';
      } catch (error) {
        if (button) {
          button.textContent = 'Open failed';
          button.title = String(error);
        }
      } finally {
        if (button) setTimeout(() => {
          button.disabled = false;
          button.textContent = original;
        }, 1600);
      }
    }

    function escapeJs(value) {
      return String(value ?? '').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'").replace(/\\n/g, '\\\\n').replace(/\\r/g, '');
    }

    function startProgress(outputId, label, estimateSeconds = 20) {
      const output = document.getElementById(outputId);
      const started = Date.now();
      const render = () => {
        const elapsed = Math.floor((Date.now() - started) / 1000);
        const remaining = Math.max(0, estimateSeconds - elapsed);
        const remainingText = remaining > 0 ? `${remaining}s remaining estimate` : 'finishing now';
        const percent = Math.min(98, Math.round((elapsed / Math.max(1, estimateSeconds)) * 100));
        output.innerHTML = `${escapeHtml(label)}... elapsed ${elapsed}s, ${escapeHtml(remainingText)}<div class="progress-shell"><div class="progress-bar" style="width:${percent}%"></div></div>`;
      };
      render();
      const timer = setInterval(render, 1000);
      return () => clearInterval(timer);
    }

    async function runWithProgress(buttonId, outputId, label, estimateSeconds, work) {
      const button = document.getElementById(buttonId);
      button.disabled = true;
      const stopProgress = startProgress(outputId, label, estimateSeconds);
      try {
        const data = await work();
        setOutput(outputId, data);
        if (!data.error) addMessage('assistant', `${label} done. File is ready to download.`);
        await refreshDashboards();
      } catch (error) {
        setOutput(outputId, 'Error: ' + error);
      } finally {
        stopProgress();
        button.disabled = false;
      }
    }

    async function refreshFiles() {
      const res = await fetch('/api/files');
      const data = await res.json();
      fileList.innerHTML = data.files.length
        ? renderFileCards(data.files.map(file => ({...file, label: 'input', size_bytes: file.size_bytes})), 'input')
        : '<div class="file-chip">No uploaded files yet.</div>';
    }

    function renderAttachments() {
      attachmentBar.innerHTML = pendingAttachments.length
        ? pendingAttachments.map(file => `<span class="attachment-pill"><span class="file-kind">${escapeHtml(fileKind(file.path || file.name))}</span>${escapeHtml(file.name || fileDisplayName(file.path))}</span>`).join('')
        : '';
      scheduleRoutePreview();
    }

    async function uploadInputFiles(input) {
      if (!input.files.length) return [];
      const formData = new FormData();
      Array.from(input.files).forEach(file => formData.append('files', file));
      const res = await fetch('/api/files/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      await refreshFiles();
      await refreshStatus();
      await refreshDashboards();
      return data.files || [];
    }

    async function uploadRecordedScreen(blob) {
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      const file = new File([blob], `gima-screen-recording-${stamp}.webm`, { type: blob.type || 'video/webm' });
      const formData = new FormData();
      formData.append('files', file);
      const res = await fetch('/api/files/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      const files = data.files || [];
      pendingAttachments = pendingAttachments.concat(files);
      renderAttachments();
      await refreshFiles();
      await refreshStatus();
      await refreshDashboards();
      addMessage('assistant', `Screen recording saved and attached to your next prompt: ${file.name}`);
    }

    async function toggleScreenRecording() {
      const button = document.getElementById('screenRecordBtn');
      if (screenRecorder && screenRecorder.state === 'recording') {
        screenRecorder.stop();
        button.disabled = true;
        button.textContent = 'SAVING';
        setChatStatus('saving screen recording...');
        return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia || typeof MediaRecorder === 'undefined') {
        addMessage('assistant', 'Screen recording is not available in this browser. Use Chrome or another browser with getDisplayMedia and MediaRecorder support.');
        return;
      }
      try {
        screenRecordStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
        screenRecordChunks = [];
        const options = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
          ? { mimeType: 'video/webm;codecs=vp9,opus' }
          : MediaRecorder.isTypeSupported('video/webm')
            ? { mimeType: 'video/webm' }
            : {};
        screenRecorder = new MediaRecorder(screenRecordStream, options);
        screenRecorder.ondataavailable = event => {
          if (event.data && event.data.size > 0) screenRecordChunks.push(event.data);
        };
        screenRecorder.onstop = async () => {
          const blob = new Blob(screenRecordChunks, { type: screenRecorder.mimeType || 'video/webm' });
          screenRecordStream?.getTracks().forEach(track => track.stop());
          screenRecordStream = null;
          screenRecorder = null;
          button.classList.remove('recording');
          button.disabled = false;
          button.textContent = 'REC';
          try {
            await uploadRecordedScreen(blob);
            setChatStatus('screen recording attached');
          } catch (error) {
            addMessage('assistant', 'Screen recording save failed: ' + error);
            setChatStatus('screen recording save failed');
          }
        };
        screenRecordStream.getVideoTracks()[0]?.addEventListener('ended', () => {
          if (screenRecorder && screenRecorder.state === 'recording') screenRecorder.stop();
        });
        screenRecorder.start();
        button.classList.add('recording');
        button.textContent = 'STOP';
        setChatStatus('screen recording...');
      } catch (error) {
        addMessage('assistant', 'Screen recording was cancelled or blocked: ' + error);
        setChatStatus('screen recording unavailable');
      }
    }

    async function sendMessage(text) {
      async function postChat(body, timeoutMs) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), timeoutMs);
        try {
          const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
            signal: controller.signal
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return await res.json();
        } finally {
          clearTimeout(timeout);
        }
      }
      const attached = pendingAttachments.slice();
      const attachmentText = attached.length
        ? '\\n\\nAttached files in hands/in:\\n' + attached.map(file => `- ${file.name}: ${file.path}`).join('\\n')
        : '';
      const finalText = text + attachmentText;
      addMessage('user', finalText);
      addMessage('assistant', 'Thinking...');
      const pending = chat.lastElementChild.querySelector('.bubble');
      send.disabled = true;
      send.textContent = 'Sending...';
      setChatStatus('sending to Gima...');
      const requestStarted = performance.now();
      try {
        let data;
        try {
          const chat_provider = document.getElementById('chatProvider')?.value || 'local';
          data = await postChat({message: finalText, chat_provider}, 120000);
        } catch (error) {
          if (error.name !== 'AbortError') throw error;
          pending.textContent = 'Gima took more than 120 seconds. Retrying with small AI...';
          setChatStatus('retrying with small AI...');
          const chat_provider = document.getElementById('chatProvider')?.value || 'local';
          data = await postChat({message: finalText, prefer_small_model: true, chat_provider}, 30000);
        }
        const elapsed = data.elapsed_seconds ?? ((performance.now() - requestStarted) / 1000).toFixed(2);
        updateAssistantMessage(pending, data.reply || data.error || 'No reply.', data.files || [], {
          elapsed_seconds: elapsed,
          used_brain: data.used_brain,
          used_internet: data.used_internet,
        });
        document.getElementById('lastResponse').textContent = `${elapsed}s`;
        setChatStatus(data.error ? 'Gima returned an error' : `reply received in ${elapsed}s`);
        if (!data.error && attached.length) {
          pendingAttachments = [];
          renderAttachments();
        }
      } catch (error) {
        const reason = error.name === 'AbortError' ? 'Gima did not answer within 120 seconds.' : String(error);
        pending.textContent = 'Error: ' + reason + '\\nTry refreshing the page, then send again. Backend health is /api/status.';
        setChatStatus('chat error: ' + reason);
      } finally {
        send.disabled = false;
        send.textContent = '^';
        message.focus();
        refreshStatus();
      }
    }

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const text = message.value.trim();
      if (!text) return;
      message.value = '';
      autoGrowMessage();
      sendMessage(text);
    });
    function autoGrowMessage() {
      message.style.height = 'auto';
      message.style.height = Math.min(message.scrollHeight, 180) + 'px';
    }
    message.addEventListener('input', () => {
      autoGrowMessage();
      scheduleRoutePreview();
    });
    document.getElementById('chatProvider')?.addEventListener('change', scheduleRoutePreview);
    message.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey && enterSendSetting.checked) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    document.querySelectorAll('[data-prompt]').forEach(button => {
      button.addEventListener('click', () => sendMessage(button.dataset.prompt));
    });
    leftDrawerBtn.addEventListener('click', () => openDrawer('left'));
    rightDrawerBtn.addEventListener('click', () => openDrawer('right'));
    document.getElementById('railHomeBtn').addEventListener('click', () => {
      closeDrawers();
      closeAddSheet();
      chat.classList.remove('has-messages');
      chat.querySelectorAll('.message').forEach(node => node.remove());
      if (emptyState) emptyState.hidden = false;
      message.value = '';
      message.focus();
      setChatStatus('new chat ready');
    });
    document.getElementById('railSystemBtn').addEventListener('click', () => openDrawer('left'));
    drawerBackdrop.addEventListener('click', closeDrawers);
    addSheetBackdrop.addEventListener('click', closeAddSheet);
    addSheetClose.addEventListener('click', closeAddSheet);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeDrawers();
        closeAddSheet();
      }
    });
    document.querySelectorAll('[data-open-panel]').forEach(button => {
      button.addEventListener('click', () => {
        closeAddSheet();
        openDrawer(button.dataset.openPanel, button.dataset.focus || '');
      });
    });
    document.querySelectorAll('[data-action="attach"]').forEach(button => {
      button.addEventListener('click', openAddSheet);
    });
    document.getElementById('screenRecordBtn').addEventListener('click', toggleScreenRecording);
    document.querySelectorAll('[data-action="screen-record"]').forEach(button => {
      button.addEventListener('click', toggleScreenRecording);
    });
    document.querySelectorAll('[data-file-category]').forEach(button => {
      button.addEventListener('click', () => chooseFiles(button.dataset.accept || ''));
    });
    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      deferredInstallPrompt = event;
      document.getElementById('installOutput').textContent = 'Install is ready. Press Install Gima App.';
    });
    document.getElementById('installBtn').addEventListener('click', async () => {
      if (deferredInstallPrompt) {
        deferredInstallPrompt.prompt();
        const choice = await deferredInstallPrompt.userChoice;
        document.getElementById('installOutput').textContent = `Install result: ${choice.outcome}`;
        deferredInstallPrompt = null;
        return;
      }
      document.getElementById('installOutput').textContent = 'If no install popup appears, use browser menu: Add to Dock or Add to Home Screen.';
    });
    document.getElementById('searchBtn').addEventListener('click', async () => {
      const q = document.getElementById('search').value.trim();
      if (!q) return;
      const res = await fetch('/api/memory/search?q=' + encodeURIComponent(q));
      const data = await res.json();
      document.getElementById('results').innerHTML = data.results.length
        ? data.results.map(row => `<p><b>${row.title}</b><br>${row.content}</p>`).join('')
        : '<p>No matching memory.</p>';
    });
    document.getElementById('uploadBtn').addEventListener('click', async () => {
      const input = document.getElementById('fileInput');
      if (!input.files.length) return;
      document.getElementById('uploadBtn').disabled = true;
      try {
        const files = await uploadInputFiles(input);
        input.value = '';
        addMessage('assistant', `Attached ${files.length} file(s) to Gima memory. Saved in hands/in and indexed in brain.csv.`);
      } finally {
        document.getElementById('uploadBtn').disabled = false;
      }
    });
    document.getElementById('chatUploadBtn').addEventListener('click', () => {
      openAddSheet();
    });
    document.getElementById('chatFileInput').addEventListener('change', async () => {
      const input = document.getElementById('chatFileInput');
      if (!input.files.length) return;
      document.getElementById('chatUploadBtn').disabled = true;
      try {
        const files = await uploadInputFiles(input);
        pendingAttachments = pendingAttachments.concat(files);
        input.value = '';
        renderAttachments();
        addMessage('assistant', `Ready: ${files.length} file(s) attached to your next prompt and saved in hands/in.`);
      } catch (error) {
        addMessage('assistant', 'Upload error: ' + error);
      } finally {
        document.getElementById('chatUploadBtn').disabled = false;
      }
    });
    document.getElementById('insertSystemMessageBtn').addEventListener('click', () => {
      const draft = document.getElementById('systemMessageDraft').value.trim();
      if (!draft) return;
      const prefix = `System message for this request:\\n${draft}\\n\\nUser request:\\n`;
      message.value = prefix + message.value;
      autoGrowMessage();
      closeDrawers();
      message.focus();
    });
    document.getElementById('saveApiBtn').addEventListener('click', async () => {
      const provider = document.getElementById('apiProvider').value;
      const api_key = document.getElementById('apiKey').value.trim();
      if (!api_key) return;
      document.getElementById('saveApiBtn').disabled = true;
      try {
        const data = await apiPost('/api/bindings/save', { provider, api_key });
        document.getElementById('apiKey').value = '';
        setOutput('bindingOutput', data.error ? data : 'Saved. This key stays local in .human-ai/secrets.env.');
        await refreshBindings();
      } finally {
        document.getElementById('saveApiBtn').disabled = false;
      }
    });
    document.getElementById('multiMindBtn').addEventListener('click', async () => {
      const text = message.value.trim();
      if (!text) {
        setOutput('bindingOutput', 'Type a prompt in chat first, then press Ask All Linked Minds.');
        return;
      }
      document.getElementById('multiMindBtn').disabled = true;
      try {
        const data = await apiPost('/api/minds/ask', { prompt: text, providers: [] });
        setOutput('bindingOutput', data);
        if (!data.error) addMessage('assistant', 'Multi mind learning saved to Gima brain for similar future questions.');
        await refreshStatus();
      } finally {
        document.getElementById('multiMindBtn').disabled = false;
      }
    });
    document.getElementById('localModelUseBtn').addEventListener('click', async () => {
      const level = document.getElementById('localModelSelect').value;
      if (!level) return;
      document.getElementById('localModelUseBtn').disabled = true;
      setChatStatus(`switching local model to ${level}...`);
      try {
        const data = await apiPost('/api/model-level/use', { level, restart: true });
        if (data.error) {
          setChatStatus('model switch error: ' + data.error);
        } else {
          setChatStatus(`local model switched to ${data.active_level}${data.brain_restarted ? ' and brain restarted' : ''}`);
          await refreshStatus();
        }
      } finally {
        document.getElementById('localModelUseBtn').disabled = false;
      }
    });
    document.getElementById('openrouterLoadModelsBtn').addEventListener('click', async () => {
      document.getElementById('openrouterLoadModelsBtn').disabled = true;
      try {
        await refreshOpenRouterModels(true);
      } catch (error) {
        setOutput('openrouterModelOutput', 'OpenRouter model load error: ' + error);
      } finally {
        document.getElementById('openrouterLoadModelsBtn').disabled = false;
      }
    });
    document.getElementById('openrouterSaveModelBtn').addEventListener('click', async () => {
      const model = document.getElementById('openrouterModelSelect').value;
      if (!model) {
        setOutput('openrouterModelOutput', 'Load OpenRouter models first, then choose one.');
        return;
      }
      document.getElementById('openrouterSaveModelBtn').disabled = true;
      try {
        const data = await apiPost('/api/openrouter/select', { model });
        setOutput('openrouterModelOutput', data.error ? data : `Selected OpenRouter model: ${data.selected_model}`);
      } finally {
        document.getElementById('openrouterSaveModelBtn').disabled = false;
      }
    });
    document.getElementById('openrouterSaveRoutingBtn').addEventListener('click', async () => {
      const routing_sort = document.getElementById('openrouterRoutingSort').value;
      const data_collection = document.getElementById('openrouterDataCollection').value;
      const fallback_models = document.getElementById('openrouterFallbackModels').value;
      document.getElementById('openrouterSaveRoutingBtn').disabled = true;
      try {
        const data = await apiPost('/api/openrouter/routing', { routing_sort, data_collection, fallback_models });
        setOutput('openrouterModelOutput', data.error ? data : `Saved OpenRouter routing: ${data.routing_sort}, data collection ${data.data_collection}`);
      } finally {
        document.getElementById('openrouterSaveRoutingBtn').disabled = false;
      }
    });
    document.getElementById('freeLlmPlanBtn').addEventListener('click', async () => {
      const task = document.getElementById('freeLlmTask').value.trim();
      const privacy = document.getElementById('freeLlmPrivacy').value;
      const params = new URLSearchParams({ task, privacy, limit: '6' });
      document.getElementById('freeLlmPlanBtn').disabled = true;
      try {
        const data = await fetch('/api/free-llm-plan?' + params.toString()).then(res => res.json());
        const rows = data.recommendations || [];
        document.getElementById('freeLlmOutput').innerHTML =
          `<b>Free LLM route plan</b><br><span class="hint">${escapeHtml(data.source || '')}</span>` +
          rows.map(row =>
            `<div class="file-chip"><b>${escapeHtml(row.name)}</b> <span class="pill">score ${escapeHtml(row.score)}</span><br>` +
            `${escapeHtml(row.free_models)}<br>` +
            `<span class="hint">RPM ${escapeHtml(row.rpm)} · limit ${escapeHtml(row.daily_limit)} · context ${escapeHtml(row.context_window)} · training ${escapeHtml(row.data_training)}</span><br>` +
            `${(row.reasons || []).map(reason => `- ${escapeHtml(reason)}`).join('<br>')}</div>`
          ).join('') +
          `<div class="file-chip"><b>Rules</b><br>${(data.rules || []).map(rule => `- ${escapeHtml(rule)}`).join('<br>')}</div>`;
      } finally {
        document.getElementById('freeLlmPlanBtn').disabled = false;
      }
    });
    document.getElementById('modelCouncilBtn').addEventListener('click', async () => {
      const request = document.getElementById('modelCouncilRequest').value.trim();
      const params = new URLSearchParams({ request, limit: '8' });
      document.getElementById('modelCouncilBtn').disabled = true;
      try {
        const data = await fetch('/api/model-council?' + params.toString()).then(res => res.json());
        const rows = data.recommendations || [];
        document.getElementById('modelCouncilOutput').innerHTML =
          `<b>Winner:</b> ${escapeHtml(data.winner?.name || '')} <span class="pill">score ${escapeHtml(data.winner?.score || 0)}</span><br>` +
          `<span class="hint">${escapeHtml(data.winner?.model || '')}</span>` +
          rows.map(row =>
            `<div class="file-chip"><b>${escapeHtml(row.name)}</b> <span class="pill">${escapeHtml(row.provider)}</span> <span class="pill">score ${escapeHtml(row.score)}</span><br>` +
            `${escapeHtml(row.model)}<br><span class="hint">${escapeHtml(row.status)} · ${escapeHtml((row.modality || []).join(', '))}</span><br>` +
            `${(row.reasons || []).map(reason => `- ${escapeHtml(reason)}`).join('<br>')}</div>`
          ).join('') +
          `<div class="file-chip"><b>Interaction plan</b><br>${(data.interaction_plan || []).map(step => escapeHtml(step)).join('<br>')}</div>`;
      } finally {
        document.getElementById('modelCouncilBtn').disabled = false;
      }
    });
    document.getElementById('publicApiBtn').addEventListener('click', async () => {
      const query = document.getElementById('publicApiQuery').value.trim();
      const category = document.getElementById('publicApiCategory').value.trim();
      const no_auth = document.getElementById('publicApiNoAuth').checked ? '1' : '0';
      const https = document.getElementById('publicApiHttps').checked ? '1' : '0';
      const params = new URLSearchParams({ q: query, category, no_auth, https, limit: '25' });
      document.getElementById('publicApiBtn').disabled = true;
      try {
        const data = await fetch('/api/public-apis?' + params.toString()).then(res => res.json());
        const box = document.getElementById('publicApiList');
        if (data.error) {
          box.textContent = 'Error: ' + data.error;
        } else {
          box.innerHTML = `<div class="file-chip"><b>${escapeHtml(data.count)} APIs matched</b> <span class="pill">${escapeHtml(data.license)}</span><br><span class="hint">${escapeHtml(data.source)}</span></div>` +
            (data.entries || []).map(api =>
              `<div class="file-chip"><b><a href="${escapeHtml(api.url)}" target="_blank" rel="noreferrer">${escapeHtml(api.name)}</a></b> <span class="pill">${escapeHtml(api.category)}</span><br>${escapeHtml(api.description)}<br><span class="hint">Auth: ${escapeHtml(api.auth)} · HTTPS: ${escapeHtml(api.https)} · CORS: ${escapeHtml(api.cors)}</span></div>`
            ).join('');
        }
      } finally {
        document.getElementById('publicApiBtn').disabled = false;
      }
    });
    document.getElementById('refreshPaidOpenRouterBtn').addEventListener('click', async () => {
      document.getElementById('refreshPaidOpenRouterBtn').disabled = true;
      try {
        const data = await fetch('/api/openrouter/paid-plan?refresh=1').then(res => res.json());
        renderPaidOpenRouterPlan(data);
      } catch (error) {
        setOutput('paidOpenRouterList', 'Paid OpenRouter plan refresh error: ' + error);
      } finally {
        document.getElementById('refreshPaidOpenRouterBtn').disabled = false;
      }
    });
    document.getElementById('songBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('songPrompt').value.trim();
      const duration = Number(document.getElementById('songDuration').value || 12);
      if (!prompt) return;
      await runWithProgress('songBtn', 'songOutput', 'Generating song sketch', Math.max(8, duration), () =>
        apiPost('/api/media/song-local', { prompt, duration_seconds: duration })
      );
    });
    document.getElementById('musicApiBtn').addEventListener('click', async () => {
      const provider = document.getElementById('musicApiProvider').value;
      const prompt = document.getElementById('musicApiPrompt').value.trim();
      const lyrics = document.getElementById('musicApiLyrics').value;
      const model = document.getElementById('musicApiModel').value.trim();
      const duration_seconds = Number(document.getElementById('musicApiDuration').value || 30);
      const instrumental = document.getElementById('musicApiInstrumental').checked;
      if (!prompt) return;
      if (!window.confirm('External music APIs can send your prompt/lyrics to cloud providers and may spend credits. Continue?')) return;
      await runWithProgress('musicApiBtn', 'musicApiOutput', 'Generating API song', Math.max(45, duration_seconds * 6), () =>
        apiPost('/api/media/music-api-generate', { provider, prompt, lyrics, model, duration_seconds, instrumental, timeout_seconds: 600, consent: true })
      );
    });
    document.getElementById('ownVoiceBtn').addEventListener('click', async () => {
      const profile_name = document.getElementById('ownVoiceName').value.trim() || 'My original voice';
      const audio_path = document.getElementById('ownVoicePath').value.trim();
      const consent = document.getElementById('ownVoiceConsent').checked;
      if (!audio_path) {
        setOutput('ownVoiceOutput', 'Paste the path to your own MP3/WAV/M4A voice sample first.');
        return;
      }
      document.getElementById('ownVoiceBtn').disabled = true;
      try {
        const data = await apiPost('/api/voice-profile/save', { profile_name, audio_path, consent });
        setOutput('ownVoiceOutput', data.error ? data : `Saved voice profile: ${data.profile_name}\\nSample: ${data.sample_path}\\nManifest: ${data.manifest_path}`);
        await refreshStatus();
      } finally {
        document.getElementById('ownVoiceBtn').disabled = false;
      }
    });
    document.getElementById('openaiImageBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('openaiImagePrompt').value.trim();
      const model = document.getElementById('openaiImageModel').value;
      const size = document.getElementById('openaiImageSize').value;
      const quality = document.getElementById('openaiImageQuality').value;
      if (!prompt) return;
      await runWithProgress('openaiImageBtn', 'openaiImageOutput', 'Generating ChatGPT image', 30, () =>
        apiPost('/api/media/openai-image-generate', { prompt, model, size, quality, consent: true })
      );
    });
    document.getElementById('hfImageBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('hfImagePrompt').value.trim();
      const model = document.getElementById('hfImageModel').value.trim() || 'black-forest-labs/FLUX.1-dev';
      const provider = document.getElementById('hfImageProvider').value.trim() || 'wavespeed';
      if (!prompt) {
        setOutput('hfImageOutput', 'Add an image prompt first.');
        return;
      }
      if (!window.confirm('Hugging Face text-to-image can spend credits through the selected provider. Continue?')) return;
      await runWithProgress('hfImageBtn', 'hfImageOutput', 'Generating Hugging Face image', 120, () =>
        apiPost('/api/media/huggingface-image-generate', { prompt, model, provider, consent: true })
      );
    });
    document.getElementById('hfFeatureBtn').addEventListener('click', async () => {
      const text = document.getElementById('hfFeatureText').value.trim();
      const model = document.getElementById('hfFeatureModel').value.trim() || 'microsoft/harrier-oss-v1-0.6b';
      const provider = document.getElementById('hfFeatureProvider').value.trim() || 'hf-inference';
      if (!text) {
        setOutput('hfFeatureOutput', 'Add text to extract features from first.');
        return;
      }
      if (!window.confirm('Hugging Face feature extraction sends this text to the selected provider and can spend credits. Continue?')) return;
      await runWithProgress('hfFeatureBtn', 'hfFeatureOutput', 'Extracting Hugging Face features', 60, () =>
        apiPost('/api/ai/huggingface-feature-extract', { text, model, provider, consent: true })
      );
    });
    document.getElementById('transformersBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('transformersPrompt').value.trim();
      const model = document.getElementById('transformersModel').value.trim() || 'google/gemma-2-2b-it';
      const device = document.getElementById('transformersDevice').value || 'auto';
      const max_new_tokens = Number(document.getElementById('transformersMaxTokens').value || 256);
      const local_files_only = document.getElementById('transformersLocalOnly').checked;
      if (!prompt) {
        setOutput('transformersOutput', 'Add a local model prompt first.');
        return;
      }
      const note = local_files_only
        ? 'Gima will only use model files already cached locally. Continue?'
        : 'Transformers may download large model files from Hugging Face. Continue?';
      if (!window.confirm(note)) return;
      await runWithProgress('transformersBtn', 'transformersOutput', 'Running local Transformers model', 180, () =>
        apiPost('/api/local/transformers-generate', { prompt, model, device, max_new_tokens, local_files_only, consent: true })
      );
    });
    document.getElementById('videoBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('videoAudioPath').value.trim();
      const prompt = document.getElementById('videoPrompt').value.trim();
      const style = document.getElementById('videoStyle').value;
      if (!audio_path || !prompt) return;
      await runWithProgress('videoBtn', 'videoOutput', 'Rendering video', 30, () =>
        apiPost('/api/media/music-video-local', { audio_path, prompt, style, consent: true })
      );
    });
    document.getElementById('promptVideoBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('promptVideoPrompt').value.trim();
      const provider = document.getElementById('promptVideoProvider').value;
      const aspect_ratio = document.getElementById('promptVideoAspect').value;
      const duration = Number(document.getElementById('promptVideoDuration').value || 8);
      const generate_audio = document.getElementById('promptVideoAudio').checked;
      if (!prompt) {
        setOutput('promptVideoOutput', 'Add a video prompt first.');
        return;
      }
      if (!window.confirm('AI video generation can spend cloud credits. Continue?')) return;
      await runWithProgress('promptVideoBtn', 'promptVideoOutput', 'Generating AI video from prompt', Math.max(90, duration * 45), () =>
        apiPost('/api/media/prompt-video-generate', { prompt, provider, aspect_ratio, duration, generate_audio, consent: true, timeout_seconds: 1200 })
      );
    });
    document.getElementById('openrouterVideoBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('openrouterVideoPrompt').value.trim();
      const model = document.getElementById('openrouterVideoModel').value;
      const aspect_ratio = document.getElementById('openrouterVideoAspect').value;
      const resolution = document.getElementById('openrouterVideoResolution').value;
      const duration = Number(document.getElementById('openrouterVideoDuration').value || 8);
      const generate_audio = document.getElementById('openrouterVideoAudio').checked;
      if (!prompt) return;
      if (!window.confirm('OpenRouter/Veo cloud video can spend credits. Continue?')) return;
      await runWithProgress('openrouterVideoBtn', 'openrouterVideoOutput', 'Generating OpenRouter Veo video', Math.max(90, duration * 45), () =>
        apiPost('/api/media/openrouter-video-generate', { prompt, model, aspect_ratio, resolution, duration, generate_audio, timeout_seconds: 1200, consent: true })
      );
    });
    document.getElementById('hfVideoBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('hfVideoPrompt').value.trim();
      const model = document.getElementById('hfVideoModel').value.trim() || 'Wan-AI/Wan2.2-TI2V-5B';
      const provider = document.getElementById('hfVideoProvider').value.trim() || 'replicate';
      if (!prompt) {
        setOutput('hfVideoOutput', 'Add a video prompt first.');
        return;
      }
      if (!window.confirm('Hugging Face text-to-video can spend credits through the selected provider. Continue?')) return;
      await runWithProgress('hfVideoBtn', 'hfVideoOutput', 'Generating Hugging Face video', 240, () =>
        apiPost('/api/media/huggingface-video-generate', { prompt, model, provider, timeout_seconds: 1200, consent: true })
      );
    });
    document.getElementById('openrouterSpeechBtn').addEventListener('click', async () => {
      const text = document.getElementById('openrouterSpeechText').value.trim();
      const model = document.getElementById('openrouterSpeechModel').value.trim() || 'microsoft/mai-voice-2';
      const voice = document.getElementById('openrouterSpeechVoice').value.trim() || 'en-US-Harper:MAI-Voice-2';
      const style = document.getElementById('openrouterSpeechStyle').value;
      const speed = Number(document.getElementById('openrouterSpeechSpeed').value || 1);
      if (!text) {
        setOutput('openrouterSpeechOutput', 'Add text to speak first.');
        return;
      }
      if (!window.confirm('OpenRouter speech generation can spend credits. Continue?')) return;
      await runWithProgress('openrouterSpeechBtn', 'openrouterSpeechOutput', 'Generating Microsoft MAI speech', 90, () =>
        apiPost('/api/media/openrouter-speech-generate', { text, model, voice, style, speed, response_format: 'mp3', consent: true })
      );
    });
    document.getElementById('imageVideoBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('imageVideoAudioPath').value.trim();
      const rawImages = document.getElementById('imageVideoPaths').value;
      const image_paths = rawImages.split(/[\\n,]+/).map(value => value.trim()).filter(Boolean);
      const prompt = document.getElementById('imageVideoPrompt').value.trim();
      const aspect = document.getElementById('imageVideoAspect').value;
      const max_duration_seconds = Number(document.getElementById('imageVideoDuration').value || 45);
      if (!audio_path || !image_paths.length || !prompt) return;
      await runWithProgress('imageVideoBtn', 'imageVideoOutput', 'Rendering images + MP3 video', Math.max(20, max_duration_seconds), () =>
        apiPost('/api/media/image-music-video-local', { audio_path, image_paths, prompt, aspect, max_duration_seconds, consent: true })
      );
    });
    document.getElementById('advancedVideoBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('advancedAudioPath').value.trim();
      const image_paths = document.getElementById('advancedImagePaths').value.split(/[\\n,]+/).map(value => value.trim()).filter(Boolean);
      const prompt = document.getElementById('advancedPrompt').value.trim();
      const lyrics = document.getElementById('advancedLyrics').value;
      const aspect = document.getElementById('advancedAspect').value;
      const max_duration_seconds = Number(document.getElementById('advancedDuration').value || 45);
      if (!audio_path || !image_paths.length || !prompt) return;
      await runWithProgress('advancedVideoBtn', 'advancedVideoOutput', 'Rendering advanced movie draft', Math.max(30, max_duration_seconds * 2), () =>
        apiPost('/api/media/advanced-video-song', { audio_path, image_paths, prompt, lyrics, aspect, max_duration_seconds, consent: true })
      );
    });
    document.getElementById('directorBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('directorAudioPath').value.trim();
      const prompt = document.getElementById('directorPrompt').value.trim();
      const mode = document.getElementById('directorMode').value;
      const style = document.getElementById('directorStyle').value.trim() || 'cinematic';
      const aspect = document.getElementById('directorAspect').value;
      const lyrics = document.getElementById('directorLyrics').value;
      if (!audio_path || !prompt) return;
      await runWithProgress('directorBtn', 'directorOutput', 'Creating director plan', 10, () =>
        apiPost('/api/media/music-video-director', { audio_path, prompt, mode, style, aspect, lyrics })
      );
    });
    document.getElementById('whatsappDraftBtn').addEventListener('click', async () => {
      const to = document.getElementById('whatsappTo').value.trim();
      const message = document.getElementById('whatsappMessage').value.trim();
      if (!to || !message) {
        setOutput('whatsappOutput', 'Add a recipient phone number and message first.');
        return;
      }
      const data = await apiPost('/api/whatsapp/draft', { to, message });
      setOutput('whatsappOutput', data.error ? data : `WhatsApp draft ready:\\n${data.wa_me_link}\\nManifest: ${data.manifest}`);
      if (data.wa_me_link) window.open(data.wa_me_link, '_blank', 'noopener');
    });
    document.getElementById('whatsappSendBtn').addEventListener('click', async () => {
      const to = document.getElementById('whatsappTo').value.trim();
      const message = document.getElementById('whatsappMessage').value.trim();
      if (!to || !message) {
        setOutput('whatsappOutput', 'Add a recipient phone number and message first.');
        return;
      }
      if (!window.confirm('Send this message using the official WhatsApp Cloud API? Use only for expected, permissioned messages.')) return;
      await runWithProgress('whatsappSendBtn', 'whatsappOutput', 'Sending WhatsApp message', 30, () =>
        apiPost('/api/whatsapp/send', { to, message, consent: true })
      );
    });
    document.getElementById('whatsappSearchBtn').addEventListener('click', async () => {
      const query = document.getElementById('whatsappSearchQuery').value.trim();
      const params = new URLSearchParams({ query, limit: '20' });
      const response = await fetch('/api/whatsapp/messages?' + params.toString());
      const data = await response.json();
      setOutput('whatsappOutput', data.error ? data : data);
    });
    document.getElementById('lipBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('lipAudioPath').value.trim();
      const face_path = document.getElementById('lipFacePath').value.trim();
      const prompt = document.getElementById('lipPrompt').value.trim();
      if (!audio_path || !face_path || !prompt) return;
      await runWithProgress('lipBtn', 'lipOutput', 'Creating lip-sync accuracy plan', 10, () =>
        apiPost('/api/media/lip-sync-plan', { audio_path, face_path, prompt, consent: true })
      );
    });
    document.getElementById('lipRenderBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('lipAudioPath').value.trim();
      const face_path = document.getElementById('lipFacePath').value.trim();
      const prompt = document.getElementById('lipPrompt').value.trim();
      const emotion = document.getElementById('lipEmotion').value;
      const max_duration_seconds = Number(document.getElementById('lipDuration').value || 2);
      if (!audio_path || !face_path || !prompt) return;
      await runWithProgress('lipRenderBtn', 'lipOutput', 'Rendering neural lip-sync preview', Math.max(90, max_duration_seconds * 45), () =>
        apiPost('/api/media/lip-sync-render', { audio_path, face_path, prompt, emotion, camera_motion: 'subtle', max_duration_seconds, preprocess: 'crop', timeout_seconds: 900, consent: true })
      );
    });
    document.getElementById('codeBtn').addEventListener('click', async () => {
      const feature = document.getElementById('codeFeature').value.trim();
      if (!feature) return;
      await runWithProgress('codeBtn', 'codeOutput', 'Preparing code plan', 15, () =>
        apiPost('/api/code/vibe-plan', { feature, max_files: 8 })
      );
    });
    document.getElementById('selfCodeBtn').addEventListener('click', async () => {
      const feature = document.getElementById('codeFeature').value.trim();
      if (!feature) return;
      if (!window.confirm('Let Gima implement this only in a backed-up isolated copy and run tests?')) return;
      await runWithProgress('selfCodeBtn', 'codeOutput', 'Coding and testing isolated copy', 300, () =>
        apiPost('/api/code/self-code', { feature, max_files: 8, timeout_seconds: 900, confirm: true })
      );
    });
    document.getElementById('agentCreateBtn').addEventListener('click', async () => {
      const name = document.getElementById('agentName').value.trim();
      const template = document.getElementById('agentTemplate').value;
      const goal = document.getElementById('agentGoal').value.trim();
      if (!goal) {
        setOutput('agentCreateOutput', 'Add a specific task for the agent first.');
        return;
      }
      await runWithProgress('agentCreateBtn', 'agentCreateOutput', 'Creating review-gated task agent', 20, () =>
        apiPost('/api/agents/create', { name, template, goal })
      );
      await refreshDashboards();
    });
    document.getElementById('runCodeBtn').addEventListener('click', async () => {
      const language = document.getElementById('codeLanguage').value;
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) return;
      await runWithProgress('runCodeBtn', 'codeRunOutput', 'Running sandboxed code', 5, () =>
        apiPost('/api/code/run', { language, code, timeout_seconds: 10, confirm: true })
      );
    });
    refreshStatus().catch(error => setChatStatus('status error: ' + error));
    refreshBindings().catch(error => setChatStatus('binding error: ' + error));
    refreshDashboards().catch(error => setChatStatus('dashboard error: ' + error));
    refreshFiles().catch(error => setChatStatus('file list error: ' + error));
    refreshRoutePreview().catch(() => {});
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').then(registration => registration.update()).catch(() => {});
    }
  </script>
</body>
</html>
"""


APP_MANIFEST = {
    "name": "Gima Local AI",
    "short_name": "Gima",
    "description": "Local-first AI assistant for chat, files, media, memory, coding, and Gima brain.",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#050608",
    "theme_color": "#050608",
    "orientation": "any",
    "icons": [
        {"src": "/api/app-icon.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
    ],
}


SERVICE_WORKER_JS = """
const CACHE_NAME = 'gima-local-app-v4';
const SHELL = ['/manifest.webmanifest', '/api/app-icon.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (url.pathname.startsWith('/api/') && url.pathname !== '/api/app-icon.png') return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then(match => match || caches.match('/'))));
});
""".strip()


APP_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#7c5cff"/>
      <stop offset="1" stop-color="#00d4ff"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="116" fill="#050608"/>
  <circle cx="256" cy="256" r="186" fill="url(#g)" opacity="0.92"/>
  <path fill="#fff" d="M280 118c-74 0-132 57-132 137s58 139 138 139c45 0 82-16 108-43V244H272v52h62v30c-12 8-28 13-48 13-47 0-80-34-80-84s33-83 78-83c27 0 48 9 66 28l38-39c-27-29-63-43-108-43Z"/>
</svg>"""


@dataclass(frozen=True)
class GimaWebServer:
    url: str
    server: ThreadingHTTPServer

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def create_web_server(config: Config, agent: Agent, brain: BrainServer, host: str, port: int) -> GimaWebServer:
    _ensure_storage_paths(config)
    handler = _handler_factory(config, agent, brain)
    server = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = server.server_address
    return GimaWebServer(f"http://{actual_host}:{actual_port}", server)


def run_web_ui(config: Config, agent: Agent, brain: BrainServer, host: str, port: int, open_browser: bool = False) -> str:
    if config.model.enabled:
        _start_brain_in_background(brain)
    web = create_web_server(config, agent, brain, host, port)
    runtime_dir = config.resolved_data_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    pid_path = runtime_dir / "web_ui.pid"
    current_pid = os.getpid()
    pid_path.write_text(f"{current_pid}\n", encoding="utf-8")
    if open_browser:
        _open_browser(web.url)
    print(f"Gima web UI running at {web.url}")
    print("Press Ctrl+C to stop.")
    try:
        web.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        web.stop()
        if _read_pid(pid_path) == current_pid:
            pid_path.unlink(missing_ok=True)
    return web.url


_BRAIN_START_LOCK = threading.Lock()
_BRAIN_START_THREADS: dict[str, threading.Thread] = {}


def _start_brain_in_background(brain: BrainServer) -> bool:
    key = str(brain.config.resolved_workspace)
    with _BRAIN_START_LOCK:
        existing = _BRAIN_START_THREADS.get(key)
        if existing and existing.is_alive():
            return False
        if brain.status()["running"]:
            return False

        def start() -> None:
            try:
                brain.start()
                print("Gima local brain is ready.")
            except Exception as error:
                print(f"Gima local brain startup failed: {error}", file=sys.stderr)
            finally:
                with _BRAIN_START_LOCK:
                    _BRAIN_START_THREADS.pop(key, None)

        thread = threading.Thread(target=start, name="gima-brain-start", daemon=True)
        _BRAIN_START_THREADS[key] = thread
        thread.start()
        return True


def _handler_factory(config: Config, agent: Agent, brain: BrainServer) -> type[BaseHTTPRequestHandler]:
    class GimaWebHandler(BaseHTTPRequestHandler):
        server_version = "GimaWeb/1.0"

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self._send_text(INDEX_HTML, "text/html; charset=utf-8")
            elif parsed.path == "/manifest.webmanifest":
                self._send_json(APP_MANIFEST)
            elif parsed.path == "/service-worker.js":
                self._send_text(SERVICE_WORKER_JS, "text/javascript; charset=utf-8")
            elif parsed.path == "/api/app-icon.png":
                self._send_file(Path(__file__).resolve().parent / "assets" / "gima_logo.png")
            elif parsed.path == "/api/app-icon.svg":
                self._send_text(APP_ICON_SVG, "image/svg+xml; charset=utf-8")
            elif parsed.path == "/api/status":
                self._send_json(_status_payload(config, agent, brain))
            elif parsed.path == "/api/memory/search":
                params = urllib.parse.parse_qs(parsed.query)
                query = params.get("q", [""])[0]
                limit = _safe_int(params.get("limit", ["6"])[0], 6)
                results = [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "category": row["category"],
                        "content": row["content"][:260],
                    }
                    for row in agent.search(query, limit=limit)
                ]
                self._send_json({"results": results})
            elif parsed.path == "/api/brain/search":
                params = urllib.parse.parse_qs(parsed.query)
                query = params.get("q", [""])[0]
                limit = _safe_int(params.get("limit", ["8"])[0], 8)
                self._send_json(
                    {
                        "path": str(config.resolved_brain_csv_path),
                        "results": [_public_brain_row(row) for row in _brain_search_rows(config, query, limit=limit)],
                    }
                )
            elif parsed.path == "/api/files":
                self._send_json({"files": _list_uploaded_files(config)})
            elif parsed.path == "/api/openrouter/models":
                params = urllib.parse.parse_qs(parsed.query)
                refresh = params.get("refresh", ["0"])[0] in {"1", "true", "yes"}
                output_modalities = params.get("output_modalities", ["all"])[0]
                limit = _safe_int(params.get("limit", ["500"])[0], 500)
                query = params.get("q", [""])[0]
                try:
                    self._send_json(
                        OpenRouterCatalog(config).models(
                            refresh=refresh,
                            output_modalities=output_modalities,
                            limit=max(1, min(limit, 1000)),
                            query=query,
                        )
                    )
                except Exception as error:
                    self._send_json({"error": str(error)}, HTTPStatus.BAD_GATEWAY)
            elif parsed.path == "/api/openrouter/routing":
                self._send_json(OpenRouterCatalog(config).routing_config())
            elif parsed.path == "/api/openrouter/paid-plan":
                params = urllib.parse.parse_qs(parsed.query)
                refresh = params.get("refresh", ["0"])[0] in {"1", "true", "yes"}
                self._send_json(paid_openrouter_plan(config, refresh=refresh))
            elif parsed.path == "/api/ai-router/plan":
                self._send_json(_ai_router_plan(config, urllib.parse.parse_qs(parsed.query)))
            elif parsed.path == "/api/bindings":
                self._send_json({"bindings": teacher_secret_status(config.resolved_workspace)})
            elif parsed.path == "/api/free-quotas":
                self._send_json(_free_quota_payload(config))
            elif parsed.path == "/api/free-llm-plan":
                self._send_json(_free_llm_plan_payload(parsed))
            elif parsed.path == "/api/model-council":
                params = urllib.parse.parse_qs(parsed.query)
                request = params.get("request", [""])[0]
                limit = _safe_int(params.get("limit", ["8"])[0], 8)
                attachments = params.get("attachment", [])
                self._send_json(ModelCouncil(config).plan(request, attachments=attachments, limit=max(1, min(limit, 20))))
            elif parsed.path == "/api/capabilities":
                self._send_json({"capabilities": _capability_payload(config, agent, brain)})
            elif parsed.path == "/api/doctor":
                self._send_json(_doctor_payload(config, brain))
            elif parsed.path == "/api/codex-mode":
                self._send_json({"capabilities": _codex_mode_payload(config, brain)})
            elif parsed.path == "/api/ai-task-map":
                self._send_json(_ai_task_map_payload(config))
            elif parsed.path == "/api/local-ai-stack":
                self._send_json(local_ai_stack_payload(config))
            elif parsed.path == "/api/public-apis":
                self._send_json(_public_apis_payload(config, parsed))
            elif parsed.path == "/api/deployments":
                self._send_json({"deployments": _deployment_payload(config, brain)})
            elif parsed.path == "/api/agents":
                self._send_json({"agents": _agent_payload(config), "templates": AgentRegistry(config).templates()})
            elif parsed.path == "/api/outputs":
                self._send_json({"outputs": _output_payload(config)})
            elif parsed.path == "/api/folders":
                self._send_json({"folders": _human_folder_payload(config)})
            elif parsed.path == "/api/apps":
                self._send_json({"apps": _app_plan_payload(config)})
            elif parsed.path == "/api/media/lip-sync-status":
                self._send_json(_lip_sync_renderer(config).status())
            elif parsed.path == "/api/media/music-api-status":
                self._send_json(ExternalMusicApiGenerator(_hands_out_dir(config) / "external_music").status())
            elif parsed.path == "/api/media/open-video-api-status":
                params = urllib.parse.parse_qs(parsed.query)
                base_url = params.get("base_url", [os.environ.get("GIMA_COMFYUI_URL", "http://127.0.0.1:8188")])[0]
                self._send_json(OpenSourceVideoApiRenderer(_hands_out_dir(config) / "open_video_api", base_url=base_url).status())
            elif parsed.path == "/api/media/prompt-video-status":
                self._send_json(_prompt_video_status())
            elif parsed.path == "/api/media/huggingface-video-status":
                self._send_json(HuggingFaceVideoGenerator(_hands_out_dir(config) / "huggingface_video").status())
            elif parsed.path == "/api/media/huggingface-image-status":
                self._send_json(HuggingFaceImageGenerator(_hands_out_dir(config) / "huggingface_images").status())
            elif parsed.path == "/api/ai/huggingface-feature-status":
                self._send_json(HuggingFaceFeatureExtractor(_hands_out_dir(config) / "huggingface_features").status())
            elif parsed.path == "/api/local/transformers-status":
                self._send_json(TransformersTextGenerator(_hands_out_dir(config) / "transformers_text").status())
            elif parsed.path == "/api/whatsapp/status":
                self._send_json(WhatsAppMessenger(_hands_out_dir(config) / "whatsapp_messages").status())
            elif parsed.path == "/api/whatsapp/messages":
                params = urllib.parse.parse_qs(parsed.query)
                result = WhatsAppMessenger(_hands_out_dir(config) / "whatsapp_messages").search_messages(
                    params.get("query", [""])[0],
                    limit=_safe_int(params.get("limit", ["20"])[0], 20),
                    direction=params.get("direction", ["all"])[0],
                )
                self._send_json(result)
            elif parsed.path == "/api/whatsapp/webhook":
                self._handle_whatsapp_webhook_verify(parsed)
            elif parsed.path == "/api/download":
                params = urllib.parse.parse_qs(parsed.query)
                self._handle_download(params.get("path", [""])[0])
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/files/upload":
                self._handle_file_upload()
                return
            if parsed.path == "/api/reveal":
                self._handle_reveal()
                return
            if parsed.path == "/api/bindings/save":
                self._handle_binding_save()
                return
            if parsed.path == "/api/openrouter/select":
                self._handle_openrouter_select()
                return
            if parsed.path == "/api/model-level/use":
                self._handle_model_level_use()
                return
            if parsed.path == "/api/agents/create":
                self._handle_agent_create()
                return
            if parsed.path == "/api/openrouter/routing":
                self._handle_openrouter_routing()
                return
            if parsed.path == "/api/minds/ask":
                self._handle_minds_ask()
                return
            if parsed.path == "/api/media/song-local":
                self._handle_song_local()
                return
            if parsed.path == "/api/media/music-api-generate":
                self._handle_music_api_generate()
                return
            if parsed.path == "/api/media/openai-image-generate":
                self._handle_openai_image_generate()
                return
            if parsed.path == "/api/media/huggingface-image-generate":
                self._handle_huggingface_image_generate()
                return
            if parsed.path == "/api/ai/huggingface-feature-extract":
                self._handle_huggingface_feature_extract()
                return
            if parsed.path == "/api/local/transformers-generate":
                self._handle_transformers_generate()
                return
            if parsed.path == "/api/media/music-video-local":
                self._handle_music_video_local()
                return
            if parsed.path == "/api/media/openrouter-video-generate":
                self._handle_openrouter_video_generate()
                return
            if parsed.path == "/api/media/prompt-video-generate":
                self._handle_prompt_video_generate()
                return
            if parsed.path == "/api/media/huggingface-video-generate":
                self._handle_huggingface_video_generate()
                return
            if parsed.path == "/api/media/openrouter-speech-generate":
                self._handle_openrouter_speech_generate()
                return
            if parsed.path == "/api/voice-profile/save":
                self._handle_voice_profile_save()
                return
            if parsed.path == "/api/voice/speak":
                self._handle_voice_speak()
                return
            if parsed.path == "/api/whatsapp/draft":
                self._handle_whatsapp_draft()
                return
            if parsed.path == "/api/whatsapp/send":
                self._handle_whatsapp_send()
                return
            if parsed.path == "/api/whatsapp/webhook":
                self._handle_whatsapp_webhook_receive()
                return
            if parsed.path == "/api/media/image-music-video-local":
                self._handle_image_music_video_local()
                return
            if parsed.path == "/api/media/advanced-video-song":
                self._handle_advanced_video_song()
                return
            if parsed.path == "/api/media/open-video-api":
                self._handle_open_video_api()
                return
            if parsed.path == "/api/media/music-video-director":
                self._handle_music_video_director()
                return
            if parsed.path == "/api/media/lip-sync-plan":
                self._handle_lip_sync_plan()
                return
            if parsed.path == "/api/media/lip-sync-render":
                self._handle_lip_sync_render()
                return
            if parsed.path == "/api/code/vibe-plan":
                self._handle_vibe_plan()
                return
            if parsed.path == "/api/code/self-code":
                self._handle_self_code()
                return
            if parsed.path == "/api/code/run":
                self._handle_code_run()
                return
            if parsed.path != "/api/chat":
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                message = str(payload.get("message", "")).strip()
                prefer_small_model = payload.get("prefer_small_model") is True
                requested_chat_provider = _chat_provider_from_payload(payload)
                if not message:
                    self._send_json({"error": "message is required"}, HTTPStatus.BAD_REQUEST)
                    return
                started = time.time()
                github_answer = _chat_github_sync_answer(config, message)
                if github_answer:
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", github_answer["reply"])
                    github_answer["elapsed_seconds"] = round(time.time() - started, 3)
                    github_answer["session_id"] = agent.session_id
                    _record_continuous_step(
                        config,
                        "chat_github_sync",
                        message,
                        "checked GitHub CLI authentication and ran the guarded repository sync only after explicit confirmation",
                        outputs=github_answer,
                        source="web_chat",
                    )
                    self._send_json(github_answer)
                    return
                if _should_force_brain(message):
                    reply, brain_rows = _brain_answer(config, agent, message)
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", reply)
                    _record_continuous_step(
                        config,
                        "chat_brain_answer",
                        message,
                        "forced brain-first answer from brain.csv before model, web, or linked teacher engines",
                        outputs={
                            "reply": reply,
                            "brain_rows": [_public_brain_row(row) for row in brain_rows],
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        },
                        source="web_chat",
                    )
                    self._send_json(
                        {
                            "reply": reply,
                            "used_brain": True,
                            "brain_rows": [_public_brain_row(row) for row in brain_rows],
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        }
                    )
                    return
                voice_answer = _chat_voice_profile_answer(config, agent, message)
                if voice_answer:
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", voice_answer["reply"])
                    voice_answer["elapsed_seconds"] = round(time.time() - started, 3)
                    voice_answer["session_id"] = agent.session_id
                    self._send_json(voice_answer)
                    return
                local_multimodal_answer = _chat_local_multimodal_answer(config, agent, message)
                if local_multimodal_answer:
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", local_multimodal_answer["reply"])
                    local_multimodal_answer["elapsed_seconds"] = round(time.time() - started, 3)
                    local_multimodal_answer["session_id"] = agent.session_id
                    _record_continuous_step(
                        config,
                        "chat_local_multimodal",
                        message,
                        "handled local OCR/speech/conversation request before local LLM fallback",
                        outputs=local_multimodal_answer,
                        source="web_chat",
                    )
                    self._send_json(local_multimodal_answer)
                    return
                media_answer = _chat_media_answer(config, message)
                if media_answer:
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", media_answer["reply"])
                    media_answer["elapsed_seconds"] = round(time.time() - started, 3)
                    media_answer["session_id"] = agent.session_id
                    _record_continuous_step(
                        config,
                        "chat_media_route",
                        message,
                        "routed image/audio video intent before the local language model",
                        outputs=media_answer,
                        source="web_chat",
                    )
                    self._send_json(media_answer)
                    return
                huggingface_answer = _chat_huggingface_learning_answer(config, agent, message)
                if huggingface_answer:
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", huggingface_answer["reply"])
                    _refresh_brain_csv(config)
                    huggingface_answer["elapsed_seconds"] = round(time.time() - started, 3)
                    huggingface_answer["session_id"] = agent.session_id
                    _record_continuous_step(
                        config,
                        "chat_huggingface_learning",
                        message,
                        "imported public Hugging Face metadata/card text, saved reviewable learning, and generated local artifacts",
                        outputs=huggingface_answer,
                        record_id=huggingface_answer.get("record_id", ""),
                        source="web_chat",
                    )
                    self._send_json(huggingface_answer)
                    return
                if requested_chat_provider and requested_chat_provider != "local":
                    if not cloud_allowed():
                        reply = (
                            f"{requested_chat_provider} chat is linked but cloud mode is blocked because CLOUD_ALLOWED is not true. "
                            "Gima kept this request local-first for privacy. Restart Gima with CLOUD_ALLOWED=true only when you intentionally want chat prompts sent to linked AI APIs."
                        )
                        agent.memory.append_conversation(agent.session_id, "user", message)
                        agent.memory.append_conversation(agent.session_id, "assistant", reply)
                        self._send_json(
                            {
                                "reply": reply,
                                "cloud_blocked": True,
                                "requested_provider": requested_chat_provider,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            }
                        )
                        return
                    if requested_chat_provider not in _cloud_chat_providers(config):
                        reply = f"{requested_chat_provider} is not linked yet. Save its API key in API Bindings first, or switch Chat mode back to Local brain + memory."
                        agent.memory.append_conversation(agent.session_id, "user", message)
                        agent.memory.append_conversation(agent.session_id, "assistant", reply)
                        self._send_json(
                            {
                                "reply": reply,
                                "provider_unavailable": True,
                                "requested_provider": requested_chat_provider,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            }
                        )
                        return
                    cloud_answer: str | None = None
                    cloud_errors: list[str] = []
                    try:
                        cloud_answer = agent.teacher_models.ask(requested_chat_provider, _cloud_chat_prompt(message))
                    except Exception as error:
                        cloud_errors.append(f"{requested_chat_provider}: {error}")
                        agent.memory.audit("cloud_chat_fallback", requested_chat_provider, str(error), "error")
                    if cloud_answer:
                        answer = cloud_answer
                        agent.memory.append_conversation(agent.session_id, "user", message)
                        agent.memory.append_conversation(agent.session_id, "assistant", answer)
                        record_id = agent.memory.add(
                            Record(
                                category="teacher",
                                subcategory="cloud_chat",
                                kind="teacher_answer",
                                title=f"Cloud chat answer: {message[:80]}",
                                content=answer[:100000],
                                keywords="openai chatgpt claude gemini cloud chat highest model",
                                source=f"{requested_chat_provider} cloud API",
                                confidence="0.60",
                                status="review",
                            )
                        )
                        _refresh_brain_csv(config)
                        _record_continuous_step(
                            config,
                            "chat_cloud_answer",
                            message,
                            "answered explicit linked cloud chat request before local report, weather, search, or memory handlers",
                            outputs={
                                "reply": answer,
                                "provider": requested_chat_provider,
                                "configured_model": _cloud_model_name(config, requested_chat_provider),
                                "cloud_errors": cloud_errors,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            },
                            record_id=record_id,
                            source="web_chat",
                        )
                        self._send_json(
                            {
                                "reply": answer,
                                "provider": requested_chat_provider,
                                "configured_model": _cloud_model_name(config, requested_chat_provider),
                                "cloud_errors": cloud_errors,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            }
                        )
                        return
                    reply = (
                        f"{requested_chat_provider} did not return an answer. "
                        "Gima stopped before local fallback because you explicitly selected this Chat mode. "
                        "Check the provider key, quota, model name, or switch Chat mode back to Local brain + memory."
                    )
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", reply)
                    self._send_json(
                        {
                            "reply": reply,
                            "provider": requested_chat_provider,
                            "cloud_errors": cloud_errors,
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        }
                    )
                    return
                artifact_engine = ChatArtifactEngine(_hands_out_dir(config), config.web.allowed_domains)
                artifact_answer = (
                    artifact_engine._weather_answer(_extract_weather_location(message) or "Osaka")
                    if "weather" in " ".join(message.casefold().split())
                    else artifact_engine.answer(message)
                )
                if artifact_answer:
                    record_id = agent.memory.add(
                        Record(
                            category="chat",
                            subcategory="artifact_answer",
                            kind="generated_report",
                            title=f"Chat artifact answer: {message[:80]}",
                            content=artifact_answer.reply[:100000],
                            keywords=message,
                            source="web_chat_artifact",
                            status="review",
                        )
                    )
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", artifact_answer.reply)
                    _refresh_brain_csv(config)
                    _record_continuous_step(
                        config,
                        "chat_artifact_answer",
                        message,
                        "answered with deterministic reasoning/web/artifact path before slow local model; generated downloadable files when requested",
                        outputs={
                            "reply": artifact_answer.reply,
                            "files": artifact_answer.files,
                            "sources": artifact_answer.sources,
                            "used_internet": artifact_answer.used_internet,
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        },
                        record_id=record_id,
                        source="web_chat",
                    )
                    self._send_json(
                        {
                            "reply": artifact_answer.reply,
                            "files": artifact_answer.files,
                            "sources": artifact_answer.sources,
                            "used_internet": artifact_answer.used_internet,
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        }
                    )
                    return
                if _should_use_all_ai(message):
                    if not cloud_allowed():
                        reply = (
                            "Cloud AI requests are blocked because CLOUD_ALLOWED is not true. "
                            "Gima kept this local-first for privacy. Set CLOUD_ALLOWED=true only when you intentionally want linked AI APIs to receive the request."
                        )
                        agent.memory.append_conversation(agent.session_id, "user", message)
                        agent.memory.append_conversation(agent.session_id, "assistant", reply)
                        self._send_json(
                            {
                                "reply": reply,
                                "cloud_blocked": True,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            }
                        )
                        return
                    online_providers = [provider for provider in _linked_mind_providers(config, []) if provider != "local"]
                    answer, teacher_results = agent.answer_with_all_ai(_strip_all_ai_prefix(message), online_providers)
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", answer)
                    _refresh_brain_csv(config)
                    _record_continuous_step(
                        config,
                        "chat_multi_ai_answer",
                        message,
                        "asked all linked online AI teacher engines, saved human-language answers into brain, and returned a combined answer",
                        outputs={
                            "reply": answer,
                            "providers": [provider for provider, _ in teacher_results],
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        },
                        source="web_chat",
                    )
                    self._send_json(
                        {
                            "reply": answer,
                            "providers": [provider for provider, _ in teacher_results],
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        }
                    )
                    return
                if (requested_chat_provider and requested_chat_provider != "local") or (not requested_chat_provider and _should_use_cloud_chat(config, message)):
                    cloud_answer: str | None = None
                    cloud_provider = ""
                    cloud_errors: list[str] = []
                    cloud_providers = [requested_chat_provider] if requested_chat_provider and requested_chat_provider != "local" else _cloud_chat_providers(config)
                    for provider in cloud_providers:
                        try:
                            cloud_answer = agent.teacher_models.ask(provider, _cloud_chat_prompt(message))
                            cloud_provider = provider
                            break
                        except Exception as error:
                            cloud_errors.append(f"{provider}: {error}")
                            agent.memory.audit("cloud_chat_fallback", provider, str(error), "error")
                    if cloud_answer:
                        answer = cloud_answer
                        agent.memory.append_conversation(agent.session_id, "user", message)
                        agent.memory.append_conversation(agent.session_id, "assistant", answer)
                        record_id = agent.memory.add(
                            Record(
                                category="teacher",
                                subcategory="cloud_chat",
                                kind="teacher_answer",
                                title=f"Cloud chat answer: {message[:80]}",
                                content=answer[:100000],
                                keywords="openai chatgpt claude gemini cloud chat highest model",
                                source=f"{cloud_provider} cloud API",
                                confidence="0.60",
                                status="review",
                            )
                        )
                        _refresh_brain_csv(config)
                        _record_continuous_step(
                            config,
                            "chat_cloud_answer",
                            message,
                            "answered normal chat through linked cloud AI before falling back to the tiny local model",
                            outputs={
                                "reply": answer,
                                "provider": cloud_provider,
                                "configured_model": _cloud_model_name(config, cloud_provider),
                                "cloud_errors": cloud_errors,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            },
                            record_id=record_id,
                            source="web_chat",
                        )
                        self._send_json(
                            {
                                "reply": answer,
                                "provider": cloud_provider,
                                "configured_model": _cloud_model_name(config, cloud_provider),
                                "cloud_errors": cloud_errors,
                                "elapsed_seconds": round(time.time() - started, 3),
                                "session_id": agent.session_id,
                            }
                        )
                        return
                brain_status = brain.status()
                if config.model.enabled and not brain_status["running"]:
                    _start_brain_in_background(brain)
                    brain_status = brain.status()
                brain_ready = brain_status.get("ready", bool(brain_status.get("running")))
                if config.model.enabled and not brain_ready:
                    reply = (
                        "Gima's local brain is starting. This 4B model takes about three minutes to load on this Mac. "
                        "Memory, files, search, and deterministic tools remain available while it initializes."
                    )
                    agent.memory.append_conversation(agent.session_id, "user", message)
                    agent.memory.append_conversation(agent.session_id, "assistant", reply)
                    self._send_json(
                        {
                            "reply": reply,
                            "brain_state": brain_status.get("state", "starting"),
                            "brain_pid": brain_status.get("pid"),
                            "elapsed_seconds": round(time.time() - started, 3),
                            "session_id": agent.session_id,
                        }
                    )
                    return
                model_level_used = "fast" if prefer_small_model else config.model.active_level
                model_timeout_cap = 75
                reply = _with_temporary_model_level(
                    config,
                    "fast" if prefer_small_model else None,
                    lambda: agent.chat(
                        message,
                        model_timeout_seconds=max(15, min(model_timeout_cap, config.model.timeout_seconds)),
                        max_tokens=min(96, config.model.max_tokens),
                        fallback_on_model_error=True,
                    ),
                )
                _record_continuous_step(
                    config,
                    "chat",
                    message,
                    "answered local chat request and saved conversation through agent memory",
                    outputs={
                        "reply": reply,
                        "elapsed_seconds": round(time.time() - started, 3),
                        "session_id": agent.session_id,
                        "model_level_used": model_level_used,
                        "small_model_retry": prefer_small_model,
                    },
                    source="web_chat",
                )
                self._send_json(
                    {
                        "reply": reply,
                        "elapsed_seconds": round(time.time() - started, 3),
                        "session_id": agent.session_id,
                        "model_level_used": model_level_used,
                        "small_model_retry": prefer_small_model,
                    }
                )
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _handle_file_upload(self) -> None:
            try:
                files = self._read_multipart_files()
                saved = []
                upload_dir = _uploads_dir(config)
                upload_dir.mkdir(parents=True, exist_ok=True)
                for file in files:
                    name = _safe_filename(file["name"])
                    target = _unique_path(upload_dir / name)
                    target.write_bytes(file["content"])
                    indexed_chunks = agent.ingest(target)
                    record_id = agent.memory.add(
                        Record(
                            category="files",
                            subcategory="web_upload",
                            kind="uploaded_file",
                            title=name,
                            content=f"Uploaded through Gima web UI: {target}\nReadable chunks indexed: {indexed_chunks}",
                            source=str(target),
                            media_path=str(target),
                            status="active",
                        )
                    )
                    payload = _file_payload(target, record_id)
                    _record_stomach_item(config, payload)
                    _record_continuous_step(
                        config,
                        "file_upload",
                        f"upload file {name}",
                        "saved raw uploaded file to hands/in, indexed memory, recorded stomach inventory, and refreshed brain.csv",
                        inputs={"filename": name, "content_size_bytes": len(file["content"]), "indexed_chunks": indexed_chunks},
                        outputs=payload,
                        record_id=record_id,
                        source="web_upload",
                    )
                    _refresh_brain_csv(config)
                    saved.append(payload)
                self._send_json({"files": saved})
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_binding_save(self) -> None:
            try:
                payload = self._read_json()
                provider = str(payload.get("provider", "")).strip()
                api_key = str(payload.get("api_key", "")).strip()
                path = save_teacher_secret(config.resolved_workspace, provider, api_key)
                _record_continuous_step(
                    config,
                    "save_api_binding",
                    f"save {provider} API binding",
                    "stored a local teacher-model API binding in private secrets.env and refreshed binding status",
                    inputs={"provider": provider},
                    outputs={"secrets_path": str(path), "bindings": teacher_secret_status(config.resolved_workspace)},
                    source="web_api_binding",
                )
                self._send_json({"ok": True, "secrets_path": str(path), "bindings": teacher_secret_status(config.resolved_workspace)})
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_openrouter_select(self) -> None:
            try:
                payload = self._read_json()
                model = str(payload.get("model", "")).strip()
                selected = OpenRouterCatalog(config).select_model(model)
                config.teacher_models.openrouter_model = selected
                _record_continuous_step(
                    config,
                    "select_openrouter_model",
                    f"select OpenRouter model {selected}",
                    "stored the preferred OpenRouter model locally and made it the first model used by Gima cloud chat",
                    inputs={"model": selected},
                    outputs={"selected_model": selected},
                    source="web_api_binding",
                )
                self._send_json({"ok": True, "selected_model": selected})
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_model_level_use(self) -> None:
            try:
                payload = self._read_json()
                level = str(payload.get("level", "")).strip()
                restart = payload.get("restart") is not False
                manager = ModelLevelManager(config, getattr(config, "_config_path", None))
                target = manager.level(level)
                was_running = bool(brain.status().get("running"))
                values = manager.apply_level(target.level)
                brain_restarted = False
                brain_pid = None
                if restart and was_running:
                    brain.stop()
                    brain_pid = brain.start()
                    brain_restarted = True
                _record_continuous_step(
                    config,
                    "switch_local_model_level",
                    f"switch local model level to {target.level}",
                    "updated Gima's local model level from the web UI and restarted the brain server when it was already running",
                    inputs={"level": target.level, "restart": restart},
                    outputs={
                        "active_level": values.get("active_level"),
                        "model": values.get("model"),
                        "model_path": values.get("model_path"),
                        "brain_restarted": brain_restarted,
                        "brain_pid": brain_pid,
                    },
                    source="web_model_selector",
                )
                self._send_json(
                    {
                        "ok": True,
                        "active_level": values.get("active_level"),
                        "model": values.get("model"),
                        "model_path": values.get("model_path"),
                        "brain_restarted": brain_restarted,
                        "brain_pid": brain_pid,
                    }
                )
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_openrouter_routing(self) -> None:
            try:
                payload = self._read_json()
                routing = OpenRouterCatalog(config).save_routing_config(payload)
                _record_continuous_step(
                    config,
                    "save_openrouter_routing",
                    "save OpenRouter routing profile",
                    "stored provider routing, data collection, fallback, auxiliary, and code-router settings for Gima cloud calls",
                    inputs={
                        "routing_sort": routing.get("routing_sort"),
                        "data_collection": routing.get("data_collection"),
                        "fallback_models": routing.get("fallback_models"),
                    },
                    outputs=routing,
                    source="web_api_binding",
                )
                self._send_json(routing)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_minds_ask(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                requested = [str(provider).strip() for provider in payload.get("providers", []) if str(provider).strip()]
                if not prompt:
                    self._send_json({"error": "prompt is required"}, HTTPStatus.BAD_REQUEST)
                    return
                providers = _linked_mind_providers(config, requested)
                started = time.time()
                results = agent.transfer_teacher_knowledge(prompt, providers)
                response = {
                    "results": [{"provider": provider, "answer": answer} for provider, answer in results],
                    "elapsed_seconds": round(time.time() - started, 3),
                    "brain": str(config.resolved_data_dir / "brain" / "teacher-learnings"),
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "multi_mind_ask",
                    prompt,
                    "asked linked teacher minds, saved human-language answers into Gima brain, and refreshed brain.csv",
                    inputs={"providers": providers},
                    outputs=response,
                    source="web_multi_mind",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_song_local(self) -> None:
            try:
                payload = self._read_json()
                project = LocalSongSketcher(_hands_out_dir(config) / "song_sketch").render(
                    str(payload.get("prompt", "")),
                    duration_seconds=_safe_int(str(payload.get("duration_seconds", "12")), 12),
                )
                record_id = agent.memory.add(
                    Record(
                        category="audio",
                        subcategory="local_song_sketch",
                        kind="generated_media",
                        title="Local song sketch",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = _project_payload(project.output_path, project.manifest_path, record_id)
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_song_sketch",
                    str(payload.get("prompt", "")),
                    "generated local WAV song sketch in hands/out folder, stored manifest in memory, and refreshed brain.csv",
                    inputs={"duration_seconds": _safe_int(str(payload.get("duration_seconds", "12")), 12)},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_music_api_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                provider = str(payload.get("provider", "huggingface_musicgen"))
                project = ExternalMusicApiGenerator(_hands_out_dir(config) / "external_music").generate(
                    prompt,
                    provider=provider,
                    lyrics=str(payload.get("lyrics", "")),
                    model=str(payload.get("model", "")),
                    duration_seconds=_safe_int(str(payload.get("duration_seconds", "30")), 30),
                    instrumental=bool(payload.get("instrumental", False)),
                    timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "300")), 300),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="audio",
                        subcategory="external_music_api",
                        kind="generated_media",
                        title=f"External music API: {prompt[:80]}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = _project_payload(project.output_path, project.manifest_path, record_id)
                response.update({"provider": provider, "prompt_file": str(project.prompt_path)})
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_external_music_api",
                    prompt,
                    "generated audio through an approved external music API, saved manifest in hands/out, and indexed it in memory",
                    inputs={
                        "provider": provider,
                        "duration_seconds": _safe_int(str(payload.get("duration_seconds", "30")), 30),
                        "instrumental": bool(payload.get("instrumental", False)),
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_openai_image_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                result = OpenAIImageGenerator(_hands_out_dir(config) / "openai_images").generate(
                    prompt,
                    model=str(payload.get("model", "gpt-image-2")),
                    size=str(payload.get("size", "1024x1024")),
                    quality=str(payload.get("quality", "auto")),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(result["manifest_path"])
                output_path = Path(result["output_path"])
                record_id = agent.memory.add(
                    Record(
                        category="image",
                        subcategory="openai_image_generation",
                        kind="generated_media",
                        title=f"ChatGPT image: {prompt[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        media_path=str(output_path),
                        status="review",
                    )
                )
                response = {
                    "status": "generated",
                    "provider": "openai",
                    "output": str(output_path),
                    "generated_path": str(output_path),
                    "manifest": str(manifest_path),
                    "prompt_file": result["prompt_path"],
                    "model": result["model"],
                    "size": result["size"],
                    "quality": result["quality"],
                    "revised_prompt": result["revised_prompt"],
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_openai_image",
                    prompt,
                    "generated a ChatGPT/OpenAI image into hands/out, saved a provenance manifest, and indexed the result in memory",
                    inputs={"model": result["model"], "size": result["size"], "quality": result["quality"]},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_huggingface_image_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                result = HuggingFaceImageGenerator(_hands_out_dir(config) / "huggingface_images").generate(
                    prompt,
                    model=str(payload.get("model", os.environ.get("GIMA_HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev"))),
                    provider=str(payload.get("provider", os.environ.get("GIMA_HF_IMAGE_PROVIDER", "wavespeed"))),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                output_path = Path(str(result["output_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="image",
                        subcategory="huggingface_text_to_image",
                        kind="generated_media",
                        title=f"Hugging Face image: {prompt[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        media_path=str(output_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": "huggingface",
                    "inference_provider": result.get("inference_provider", ""),
                    "model": result.get("model", ""),
                    "output": str(output_path),
                    "generated_path": str(output_path),
                    "download_url": _download_url(output_path),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "prompt_file": result.get("prompt_path", ""),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_huggingface_image",
                    prompt,
                    "generated text-to-image through Hugging Face InferenceClient with explicit consent and local manifest",
                    inputs={
                        "model": response["model"],
                        "provider": response["inference_provider"],
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_huggingface_feature_extract(self) -> None:
            try:
                payload = self._read_json()
                text = str(payload.get("text", "")).strip()
                result = HuggingFaceFeatureExtractor(_hands_out_dir(config) / "huggingface_features").extract(
                    text,
                    model=str(payload.get("model", os.environ.get("GIMA_HF_FEATURE_MODEL", "microsoft/harrier-oss-v1-0.6b"))),
                    provider=str(payload.get("provider", os.environ.get("GIMA_HF_FEATURE_PROVIDER", "hf-inference"))),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="ai",
                        subcategory="huggingface_feature_extraction",
                        kind="feature_vectors",
                        title=f"Hugging Face features: {text[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": "huggingface",
                    "inference_provider": result.get("inference_provider", ""),
                    "model": result.get("model", ""),
                    "input": result.get("input_path", ""),
                    "features": result.get("features_path", ""),
                    "features_download_url": _download_url(Path(str(result["features_path"]))),
                    "csv": result.get("csv_path", ""),
                    "csv_download_url": _download_url(Path(str(result["csv_path"]))),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "stats": result.get("stats", {}),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "huggingface_feature_extraction",
                    text[:240],
                    "created Hugging Face feature vectors for approved text and saved local JSON/CSV artifacts",
                    inputs={
                        "model": response["model"],
                        "provider": response["inference_provider"],
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_ai",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_transformers_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                result = TransformersTextGenerator(_hands_out_dir(config) / "transformers_text").generate(
                    prompt,
                    model=str(payload.get("model", os.environ.get("GIMA_TRANSFORMERS_MODEL", "google/gemma-2-2b-it"))),
                    device=str(payload.get("device", os.environ.get("GIMA_TRANSFORMERS_DEVICE", "auto"))),
                    max_new_tokens=int(payload.get("max_new_tokens", 256) or 256),
                    local_files_only=bool(payload.get("local_files_only", True)),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="ai",
                        subcategory="local_transformers_text_generation",
                        kind="local_model_response",
                        title=f"Local Transformers: {prompt[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": "local",
                    "model": result.get("model", ""),
                    "device": result.get("device", ""),
                    "answer": result.get("answer", ""),
                    "response": result.get("response_path", ""),
                    "response_download_url": _download_url(Path(str(result["response_path"]))),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "local_files_only": result.get("local_files_only", True),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "local_transformers_text_generation",
                    prompt[:240],
                    "ran a local Hugging Face Transformers text-generation model and saved response artifacts",
                    inputs={
                        "model": response["model"],
                        "device": response["device"],
                        "local_files_only": response["local_files_only"],
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_local_ai",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_whatsapp_draft(self) -> None:
            try:
                payload = self._read_json()
                result = WhatsAppMessenger(_hands_out_dir(config) / "whatsapp_messages").draft_link(
                    str(payload.get("to", "")),
                    str(payload.get("message", "")),
                )
                manifest_path = Path(str(result["manifest_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="communication",
                        subcategory="whatsapp",
                        kind="message_draft",
                        title=f"WhatsApp draft to {result.get('recipient', '')}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "drafted"),
                    "provider": "whatsapp",
                    "recipient": result.get("recipient", ""),
                    "wa_me_link": result.get("wa_me_link", ""),
                    "message_path": result.get("message_path", ""),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "whatsapp_draft",
                    f"draft WhatsApp message to {response['recipient']}",
                    "created a WhatsApp wa.me draft link for user review before sending",
                    inputs={"recipient": response["recipient"]},
                    outputs=response,
                    record_id=record_id,
                    source="web_communication",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_whatsapp_send(self) -> None:
            try:
                payload = self._read_json()
                result = WhatsAppMessenger(_hands_out_dir(config) / "whatsapp_messages").send_text(
                    str(payload.get("to", "")),
                    str(payload.get("message", "")),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="communication",
                        subcategory="whatsapp",
                        kind="message_sent",
                        title=f"WhatsApp sent to {result.get('recipient', '')}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "sent"),
                    "provider": "whatsapp",
                    "recipient": result.get("recipient", ""),
                    "message_path": result.get("message_path", ""),
                    "response_path": result.get("response_path", ""),
                    "response_download_url": _download_url(Path(str(result["response_path"]))),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "record_id": record_id,
                    "api_response": result.get("api_response", {}),
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "whatsapp_send",
                    f"send WhatsApp message to {response['recipient']}",
                    "sent a WhatsApp text message through the official Cloud API after explicit consent",
                    inputs={"recipient": response["recipient"]},
                    outputs=response,
                    record_id=record_id,
                    source="web_communication",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_whatsapp_webhook_verify(self, parsed: urllib.parse.ParseResult) -> None:
            params = urllib.parse.parse_qs(parsed.query)
            mode = params.get("hub.mode", [""])[0]
            token = params.get("hub.verify_token", [""])[0]
            challenge = params.get("hub.challenge", [""])[0]
            expected = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "").strip()
            if mode == "subscribe" and expected and token == expected:
                data = challenge.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._send_json(
                {
                    "error": "WhatsApp webhook verification failed or WHATSAPP_WEBHOOK_VERIFY_TOKEN is not set",
                    "webhook_path": "/api/whatsapp/webhook",
                },
                HTTPStatus.FORBIDDEN,
            )

        def _handle_whatsapp_webhook_receive(self) -> None:
            try:
                length = _safe_int(self.headers.get("Content-Length", "0"), 0)
                raw = self.rfile.read(max(0, min(length, 2_000_000)))
                payload = json.loads(raw.decode("utf-8")) if raw else {}
                result = WhatsAppMessenger(_hands_out_dir(config) / "whatsapp_messages").record_webhook(
                    payload,
                    signature=self.headers.get("X-Hub-Signature-256", ""),
                    raw_body=raw,
                )
                record_ids: list[str] = []
                for row in result.get("messages", []):
                    if not isinstance(row, dict):
                        continue
                    record_ids.append(
                        agent.memory.add(
                            Record(
                                category="communication",
                                subcategory="whatsapp",
                                kind="message_inbound",
                                title=f"WhatsApp inbound from {row.get('contact', '')}",
                                content=str(row.get("text", "")),
                                source=str(row.get("manifest_path", "")),
                                status="review",
                            )
                        )
                    )
                response = {
                    "status": result.get("status", "received"),
                    "provider": "whatsapp",
                    "received_count": result.get("received_count", 0),
                    "webhook_path": result.get("webhook_path", ""),
                    "messages": result.get("messages", []),
                    "record_ids": record_ids,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "whatsapp_webhook_receive",
                    f"received {response['received_count']} WhatsApp message(s)",
                    "stored official WhatsApp webhook messages in local inbox and Gima memory",
                    inputs={"received_count": response["received_count"]},
                    outputs=response,
                    source="web_communication",
                )
                self._send_json(response)
            except PermissionError as error:
                self._send_json({"error": str(error)}, HTTPStatus.FORBIDDEN)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_music_video_local(self) -> None:
            try:
                payload = self._read_json()
                project = LocalMusicVideoRenderer(_hands_out_dir(config) / "music_video").render(
                    Path(str(payload.get("audio_path", ""))),
                    str(payload.get("prompt", "")),
                    style=str(payload.get("style", "waveform")),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="local_music_video",
                        kind="generated_media",
                        title=f"Local music video: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = _project_payload(project.output_path, project.manifest_path, record_id)
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_music_video",
                    str(payload.get("prompt", "")),
                    "rendered local audio visualizer MP4 in hands/out folder, stored manifest in memory, and refreshed brain.csv",
                    inputs={"audio_path": str(payload.get("audio_path", "")), "style": str(payload.get("style", "waveform"))},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_openrouter_video_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                result = OpenRouterVideoGenerator(_hands_out_dir(config) / "openrouter_video").generate(
                    prompt,
                    model=str(payload.get("model", "google/veo-3.1")),
                    aspect_ratio=str(payload.get("aspect_ratio", "16:9")),
                    duration=_safe_int(str(payload.get("duration", "8")), 8),
                    resolution=str(payload.get("resolution", "720p")),
                    generate_audio=bool(payload.get("generate_audio", True)),
                    timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "900")), 900),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                output_path = Path(str(result["output_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="openrouter_veo_video",
                        kind="generated_media",
                        title=f"OpenRouter video: {prompt[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        media_path=str(output_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": "openrouter",
                    "output": str(output_path),
                    "generated_path": str(output_path),
                    "download_url": _download_url(output_path),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "prompt_file": result.get("prompt_path", ""),
                    "model": result.get("model", ""),
                    "job_id": result.get("job_id", ""),
                    "generation_id": result.get("generation_id", ""),
                    "usage": result.get("usage", {}),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_openrouter_video",
                    prompt,
                    "submitted an OpenRouter/Veo video generation job, downloaded the result into hands/out, and saved a provenance manifest",
                    inputs={
                        "model": str(payload.get("model", "google/veo-3.1")),
                        "aspect_ratio": str(payload.get("aspect_ratio", "16:9")),
                        "duration": _safe_int(str(payload.get("duration", "8")), 8),
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_prompt_video_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                provider = str(payload.get("provider", "auto")).strip().casefold()
                if provider == "auto":
                    provider = _select_prompt_video_provider()
                if provider not in {"openrouter", "huggingface"}:
                    raise ValueError("Prompt video provider must be auto, openrouter, or huggingface")
                if provider == "openrouter":
                    result = OpenRouterVideoGenerator(_hands_out_dir(config) / "prompt_video" / "openrouter").generate(
                        prompt,
                        model=str(payload.get("model", "google/veo-3.1")),
                        aspect_ratio=str(payload.get("aspect_ratio", "16:9")),
                        duration=_safe_int(str(payload.get("duration", "8")), 8),
                        resolution=str(payload.get("resolution", "720p")),
                        generate_audio=bool(payload.get("generate_audio", True)),
                        timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "900")), 900),
                        consent=bool(payload.get("consent", False)),
                    )
                    subcategory = "prompt_to_video_openrouter"
                    response_provider = "openrouter"
                    extra = {
                        "job_id": result.get("job_id", ""),
                        "generation_id": result.get("generation_id", ""),
                        "usage": result.get("usage", {}),
                    }
                else:
                    result = HuggingFaceVideoGenerator(_hands_out_dir(config) / "prompt_video" / "huggingface").generate(
                        prompt,
                        model=str(payload.get("model", os.environ.get("GIMA_HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B"))),
                        provider=str(payload.get("inference_provider", os.environ.get("GIMA_HF_VIDEO_PROVIDER", "replicate"))),
                        timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "900")), 900),
                        consent=bool(payload.get("consent", False)),
                    )
                    subcategory = "prompt_to_video_huggingface"
                    response_provider = "huggingface"
                    extra = {"inference_provider": result.get("inference_provider", "")}
                manifest_path = Path(str(result["manifest_path"]))
                output_path = Path(str(result["output_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory=subcategory,
                        kind="generated_media",
                        title=f"Prompt video: {prompt[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        media_path=str(output_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": response_provider,
                    "model": result.get("model", ""),
                    "output": str(output_path),
                    "generated_path": str(output_path),
                    "download_url": _download_url(output_path),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "prompt_file": result.get("prompt_path", ""),
                    "record_id": record_id,
                    **extra,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_prompt_video",
                    prompt,
                    "generated a prompt-only AI video through the selected cloud provider and saved MP4 plus manifest",
                    inputs={"provider": response_provider, "model": response["model"]},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_huggingface_video_generate(self) -> None:
            try:
                payload = self._read_json()
                prompt = str(payload.get("prompt", "")).strip()
                result = HuggingFaceVideoGenerator(_hands_out_dir(config) / "huggingface_video").generate(
                    prompt,
                    model=str(payload.get("model", os.environ.get("GIMA_HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B"))),
                    provider=str(payload.get("provider", os.environ.get("GIMA_HF_VIDEO_PROVIDER", "replicate"))),
                    timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "900")), 900),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                output_path = Path(str(result["output_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="huggingface_text_to_video",
                        kind="generated_media",
                        title=f"Hugging Face video: {prompt[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        media_path=str(output_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": "huggingface",
                    "inference_provider": result.get("inference_provider", ""),
                    "model": result.get("model", ""),
                    "output": str(output_path),
                    "generated_path": str(output_path),
                    "download_url": _download_url(output_path),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "prompt_file": result.get("prompt_path", ""),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_huggingface_video",
                    prompt,
                    "generated text-to-video through Hugging Face InferenceClient with explicit consent and local manifest",
                    inputs={
                        "model": response["model"],
                        "provider": response["inference_provider"],
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_openrouter_speech_generate(self) -> None:
            try:
                payload = self._read_json()
                text = str(payload.get("text", "")).strip()
                result = OpenRouterSpeechGenerator(_hands_out_dir(config) / "openrouter_speech").generate(
                    text,
                    model=str(payload.get("model", "microsoft/mai-voice-2")),
                    voice=str(payload.get("voice", "en-US-Harper:MAI-Voice-2")),
                    response_format=str(payload.get("response_format", "mp3")),
                    speed=float(payload.get("speed", 1.0)),
                    style=str(payload.get("style", "cheerful")),
                    styledegree=float(payload.get("styledegree", 1.0)),
                    consent=bool(payload.get("consent", False)),
                )
                manifest_path = Path(str(result["manifest_path"]))
                output_path = Path(str(result["output_path"]))
                record_id = agent.memory.add(
                    Record(
                        category="audio",
                        subcategory="openrouter_mai_speech",
                        kind="generated_media",
                        title=f"MAI speech: {text[:80]}",
                        content=manifest_path.read_text(encoding="utf-8"),
                        source=str(manifest_path),
                        media_path=str(output_path),
                        status="review",
                    )
                )
                response = {
                    "status": result.get("status", "generated"),
                    "provider": "openrouter",
                    "output": str(output_path),
                    "generated_path": str(output_path),
                    "download_url": _download_url(output_path),
                    "manifest": str(manifest_path),
                    "manifest_download_url": _download_url(manifest_path),
                    "prompt_file": result.get("prompt_path", ""),
                    "model": result.get("model", ""),
                    "voice": result.get("voice", ""),
                    "generation_id": result.get("generation_id", ""),
                    "content_type": result.get("content_type", ""),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_openrouter_speech",
                    text[:500],
                    "generated OpenRouter/Microsoft MAI speech audio into hands/out, saved a provenance manifest, and indexed it in memory",
                    inputs={"model": result.get("model", ""), "voice": result.get("voice", "")},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_voice_profile_save(self) -> None:
            try:
                payload = self._read_json()
                profile = _save_voice_profile(
                    config,
                    agent,
                    Path(str(payload.get("audio_path", ""))),
                    str(payload.get("profile_name", "My original voice")),
                    consent=bool(payload.get("consent", False)),
                )
                _record_continuous_step(
                    config,
                    "save_own_voice_profile",
                    f"save own voice profile {profile['profile_name']}",
                    "registered a consented local personal voice sample and saved a provenance manifest without enabling impersonation",
                    inputs={"profile_name": profile["profile_name"], "audio_path": profile["source_path"]},
                    outputs=profile,
                    record_id=profile["record_id"],
                    source="web_voice_profile",
                )
                self._send_json(profile)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_voice_speak(self) -> None:
            try:
                payload = self._read_json()
                text = " ".join(str(payload.get("text", "")).strip().split())
                if not text:
                    raise ValueError("Speech text is required")
                if len(text) > 1000:
                    raise ValueError("Speech text is limited to 1000 characters for local speak")
                Voice().speak(text)
                agent.memory.append_conversation(agent.session_id, "assistant", text, category="voice")
                response = {
                    "status": "spoken",
                    "provider": "macos_say",
                    "local": True,
                    "text": text,
                }
                _record_continuous_step(
                    config,
                    "local_voice_speak",
                    "speak text locally",
                    "spoke a short response through macOS say without sending text to cloud APIs",
                    outputs=response,
                    source="web_voice",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_image_music_video_local(self) -> None:
            try:
                payload = self._read_json()
                project = LocalImageMusicVideoRenderer(_hands_out_dir(config) / "image_music_video").render(
                    Path(str(payload.get("audio_path", ""))),
                    [Path(str(path)) for path in payload.get("image_paths", [])],
                    str(payload.get("prompt", "")),
                    aspect=str(payload.get("aspect", "16:9")),
                    max_duration_seconds=_safe_int(str(payload.get("max_duration_seconds", "45")), 45),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="image_music_video",
                        kind="generated_media",
                        title=f"Image music video: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = _project_payload(project.output_path, project.manifest_path, record_id)
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "generate_image_music_video",
                    str(payload.get("prompt", "")),
                    "rendered image plus audio MP4 in hands/out folder, stored manifest in memory, and refreshed brain.csv",
                    inputs={
                        "audio_path": str(payload.get("audio_path", "")),
                        "image_paths": [str(path) for path in payload.get("image_paths", [])],
                        "aspect": str(payload.get("aspect", "16:9")),
                        "max_duration_seconds": _safe_int(str(payload.get("max_duration_seconds", "45")), 45),
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_advanced_video_song(self) -> None:
            try:
                payload = self._read_json()
                project = AdvancedVideoSongRenderer(_hands_out_dir(config) / "advanced_video_song").render(
                    Path(str(payload.get("audio_path", ""))),
                    [Path(str(path)) for path in payload.get("image_paths", [])],
                    str(payload.get("prompt", "")),
                    lyrics=str(payload.get("lyrics", "")),
                    aspect=str(payload.get("aspect", "16:9")),
                    max_duration_seconds=_safe_int(str(payload.get("max_duration_seconds", "90")), 90),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="advanced_video_song",
                        kind="generated_media",
                        title=f"Advanced video song: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = {
                    "output": str(project.output_path),
                    "download_url": _download_url(project.output_path),
                    "manifest": str(project.manifest_path),
                    "manifest_download_url": _download_url(project.manifest_path),
                    "storyboard": str(project.storyboard_path),
                    "storyboard_download_url": _download_url(project.storyboard_path),
                    "audio_analysis": str(project.audio_analysis_path),
                    "audio_analysis_download_url": _download_url(project.audio_analysis_path),
                    "prompt_pack": str(project.prompt_pack_path),
                    "prompt_pack_download_url": _download_url(project.prompt_pack_path),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "render_advanced_video_song",
                    str(payload.get("prompt", "")),
                    "rendered audio-directed cinematic scenes with camera motion, emotion grading, analysis, and prompt artifacts",
                    inputs={
                        "audio_path": str(payload.get("audio_path", "")),
                        "image_paths": [str(path) for path in payload.get("image_paths", [])],
                        "aspect": str(payload.get("aspect", "16:9")),
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_open_video_api(self) -> None:
            try:
                payload = self._read_json()
                project = OpenSourceVideoApiRenderer(
                    _hands_out_dir(config) / "open_video_api",
                    base_url=str(payload.get("base_url") or os.environ.get("GIMA_COMFYUI_URL", "http://127.0.0.1:8188")),
                ).render(
                    Path(str(payload.get("workflow_path", ""))),
                    str(payload.get("prompt", "")),
                    image=Path(str(payload.get("image_path"))) if payload.get("image_path") else None,
                    negative_prompt=str(payload.get("negative_prompt", "low quality, warped face, extra limbs, flicker, watermark, unreadable text")),
                    width=_safe_int(str(payload.get("width", "832")), 832),
                    height=_safe_int(str(payload.get("height", "480")), 480),
                    frames=_safe_int(str(payload.get("frames", "81")), 81),
                    seed=_safe_int(str(payload.get("seed", "0")), 0) or None,
                    timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "1800")), 1800),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="open_source_video_api",
                        kind="generated_media",
                        title=f"Open-source video API render: {str(payload.get('prompt', ''))[:80]}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = {
                    "output": str(project.output_path),
                    "download_url": _download_url(project.output_path),
                    "manifest": str(project.manifest_path),
                    "manifest_download_url": _download_url(project.manifest_path),
                    "workflow": str(project.workflow_path),
                    "workflow_download_url": _download_url(project.workflow_path),
                    "prompt": str(project.prompt_path),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "render_open_source_video_api",
                    str(payload.get("prompt", "")),
                    "submitted ComfyUI/open-source video workflow, downloaded generated output, stored manifest, and refreshed brain.csv",
                    inputs={
                        "workflow_path": str(payload.get("workflow_path", "")),
                        "image_path": str(payload.get("image_path", "")),
                        "base_url": str(payload.get("base_url", "")),
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_music_video_director(self) -> None:
            try:
                payload = self._read_json()
                project = LocalMusicVideoDirector(_hands_out_dir(config) / "music_video_director").plan(
                    Path(str(payload.get("audio_path", ""))),
                    str(payload.get("prompt", "")),
                    mode=str(payload.get("mode", "story")),
                    style=str(payload.get("style", "cinematic")),
                    aspect=str(payload.get("aspect", "16:9")),
                    lyrics=str(payload.get("lyrics", "")),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="music_video_director",
                        kind="generation_plan",
                        title=f"Music video director: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        status="review",
                    )
                )
                response = {
                    "storyboard": str(project.storyboard_path),
                    "download_url": _download_url(project.storyboard_path),
                    "manifest": str(project.manifest_path),
                    "manifest_download_url": _download_url(project.manifest_path),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "create_music_video_director_plan",
                    str(payload.get("prompt", "")),
                    "created director storyboard and manifest in hands/out folder and refreshed brain.csv",
                    inputs={
                        "audio_path": str(payload.get("audio_path", "")),
                        "mode": str(payload.get("mode", "story")),
                        "style": str(payload.get("style", "cinematic")),
                        "aspect": str(payload.get("aspect", "16:9")),
                    },
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_lip_sync_plan(self) -> None:
            try:
                payload = self._read_json()
                project = LipSyncPlanner(_hands_out_dir(config) / "lip_sync").create_project(
                    Path(str(payload.get("audio_path", ""))),
                    Path(str(payload.get("face_path", ""))),
                    str(payload.get("prompt", "")),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="lip_sync_plan",
                        kind="generation_plan",
                        title=f"Lip-sync plan: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.project_dir),
                        status="review",
                    )
                )
                response = {
                    "project_dir": str(project.project_dir),
                    "manifest": str(project.manifest_path),
                    "manifest_download_url": _download_url(project.manifest_path),
                    "timing_plan": str(project.timing_path),
                    "timing_download_url": _download_url(project.timing_path) if project.timing_path else "",
                    "backend_plan": str(project.backend_path),
                    "backend_download_url": _download_url(project.backend_path) if project.backend_path else "",
                    "accuracy_rubric": str(project.eval_path),
                    "accuracy_download_url": _download_url(project.eval_path) if project.eval_path else "",
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "create_lip_sync_plan",
                    str(payload.get("prompt", "")),
                    "created consent-gated lip-sync timing, backend, accuracy rubric, and manifest in hands/out",
                    inputs={"audio_path": str(payload.get("audio_path", "")), "face_path": str(payload.get("face_path", ""))},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_lip_sync_render(self) -> None:
            try:
                payload = self._read_json()
                audio_path = Path(str(payload.get("audio_path", "")))
                face_path = Path(str(payload.get("face_path", "")))
                prompt = str(payload.get("prompt", ""))
                try:
                    project = _lip_sync_renderer(config).render(
                        audio_path,
                        face_path,
                        prompt,
                        emotion=str(payload.get("emotion", "cinematic")),
                        camera_motion=str(payload.get("camera_motion", "subtle")),
                        max_duration_seconds=_safe_int(str(payload.get("max_duration_seconds", "30")), 30),
                        preprocess=str(payload.get("preprocess", "crop")),
                        timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "1800")), 1800),
                        consent=bool(payload.get("consent", False)),
                    )
                except RuntimeError as error:
                    if "SadTalker backend is not ready" not in str(error):
                        raise
                    fallback = AdvancedVideoSongRenderer(_hands_out_dir(config) / "advanced_video_song").render(
                        audio_path,
                        [face_path],
                        f"{prompt} fast stage-performance fallback for lip-sync preview",
                        aspect="16:9",
                        max_duration_seconds=min(_safe_int(str(payload.get("max_duration_seconds", "18")), 18), 30),
                        consent=bool(payload.get("consent", False)),
                    )
                    plan = LipSyncPlanner(_hands_out_dir(config) / "lip_sync").create_project(
                        audio_path,
                        face_path,
                        prompt,
                        consent=bool(payload.get("consent", False)),
                    )
                    record_id = agent.memory.add(
                        Record(
                            category="video",
                            subcategory="fast_lip_sync_stage_draft",
                            kind="generated_media",
                            title=f"Fast lip-sync stage draft: {audio_path.name}",
                            content=fallback.manifest_path.read_text(encoding="utf-8"),
                            source=str(fallback.manifest_path),
                            media_path=str(fallback.output_path),
                            status="review",
                        )
                    )
                    response = {
                        "output": str(fallback.output_path),
                        "download_url": _download_url(fallback.output_path),
                        "manifest": str(fallback.manifest_path),
                        "manifest_download_url": _download_url(fallback.manifest_path),
                        "storyboard": str(fallback.storyboard_path),
                        "storyboard_download_url": _download_url(fallback.storyboard_path),
                        "audio_analysis": str(fallback.audio_analysis_path),
                        "audio_analysis_download_url": _download_url(fallback.audio_analysis_path),
                        "prompt_pack": str(fallback.prompt_pack_path),
                        "prompt_pack_download_url": _download_url(fallback.prompt_pack_path),
                        "lip_sync_plan": str(plan.manifest_path),
                        "lip_sync_plan_download_url": _download_url(plan.manifest_path),
                        "timing_plan": str(plan.timing_path),
                        "timing_download_url": _download_url(plan.timing_path) if plan.timing_path else "",
                        "fallback_reason": str(error),
                        "record_id": record_id,
                    }
                    _refresh_brain_csv(config)
                    _record_continuous_step(
                        config,
                        "render_fast_lip_sync_stage_fallback",
                        prompt,
                        "SadTalker was unavailable, so Gima rendered a fast audio-backed stage-performance draft and lip-sync plan",
                        inputs={"audio_path": str(audio_path), "face_path": str(face_path)},
                        outputs=response,
                        record_id=record_id,
                        source="web_media",
                    )
                    self._send_json(response)
                    return
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="neural_lip_sync",
                        kind="generated_media",
                        title=f"Neural lip-sync: {audio_path.name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                response = {
                    "output": str(project.output_path),
                    "download_url": _download_url(project.output_path),
                    "manifest": str(project.manifest_path),
                    "manifest_download_url": _download_url(project.manifest_path),
                    "backend_log": str(project.log_path),
                    "backend_log_download_url": _download_url(project.log_path),
                    "record_id": record_id,
                }
                _refresh_brain_csv(config)
                _record_continuous_step(
                    config,
                    "render_neural_lip_sync",
                    prompt,
                    "rendered consent-gated neural portrait animation through the configured SadTalker backend",
                    inputs={"audio_path": str(audio_path), "face_path": str(face_path)},
                    outputs=response,
                    record_id=record_id,
                    source="web_media",
                )
                self._send_json(response)
            except PermissionError as error:
                self._send_json({"error": str(error)}, HTTPStatus.FORBIDDEN)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_vibe_plan(self) -> None:
            try:
                payload = self._read_json()
                plan = VibeCodingAgent(config.resolved_workspace, config.resolved_data_dir, agent.memory).plan(
                    str(payload.get("feature", "")),
                    max_files=_safe_int(str(payload.get("max_files", "8")), 8),
                )
                response = {
                    "update_id": plan.update_request.update_id,
                    "working_copy": str(plan.update_request.working_copy),
                    "plan": str(plan.plan_path),
                    "patch_skeleton": str(plan.patch_skeleton_path),
                    "snapshot": str(plan.snapshot_path),
                    "record_id": plan.record_id,
                    "candidate_files": [file.__dict__ for file in plan.candidate_files],
                }
                event_id = _record_continuous_step(
                    config,
                    "vibe_code_plan",
                    str(payload.get("feature", "")),
                    "prepared reviewable self-update plan, working copy, patch skeleton, and candidate file list",
                    inputs={"max_files": _safe_int(str(payload.get("max_files", "8")), 8)},
                    outputs=response,
                    record_id=plan.record_id,
                    source="web_code",
                )
                _record_code_lines(config, event_id, [Path(file.path) for file in plan.candidate_files], "vibe code candidate file snapshot")
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_self_code(self) -> None:
            try:
                payload = self._read_json()
                if payload.get("confirm") is not True:
                    raise PermissionError("Self-coding requires explicit confirmation")
                feature = str(payload.get("feature", "")).strip()
                execution = VibeCodingAgent(config.resolved_workspace, config.resolved_data_dir, agent.memory).implement(
                    feature,
                    max_files=_safe_int(str(payload.get("max_files", "8")), 8),
                    timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "900")), 900),
                )
                response = {
                    "update_id": execution.plan.update_request.update_id,
                    "status": execution.status,
                    "working_copy": str(execution.plan.update_request.working_copy),
                    "changed_files": execution.changed_files,
                    "patch": str(execution.patch_path),
                    "coding_log": str(execution.coding_log_path),
                    "test_log": str(execution.test_log_path),
                    "tests_passed": execution.tests_passed,
                    "patch_preview": _text_preview(execution.patch_path, 50000),
                    "coding_output": _text_preview(execution.coding_log_path, 24000, tail=True),
                    "test_output": _text_preview(execution.test_log_path, 16000, tail=True),
                    "diff_stats": _diff_stats(execution.patch_path),
                    "next_step": "Review the copy, mark ready, then use parent-approved sync.",
                }
                _record_continuous_step(
                    config,
                    "self_code_implementation",
                    feature,
                    "implemented code in an isolated copy, generated a patch, and ran tests without syncing live files",
                    outputs=response,
                    record_id=execution.plan.record_id,
                    source="web_code",
                )
                self._send_json(response)
            except PermissionError as error:
                self._send_json({"error": str(error)}, HTTPStatus.FORBIDDEN)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_code_run(self) -> None:
            try:
                payload = self._read_json()
                if payload.get("confirm") is not True:
                    raise PermissionError("Code execution requires an explicit Run Code action")
                code = str(payload.get("code", ""))
                language = str(payload.get("language", "python"))
                result = SandboxedCodeRunner(
                    config.resolved_hands_out_dir / "code_runs",
                    protected_roots=[config.resolved_workspace, config.resolved_data_dir],
                ).run(
                    language,
                    code,
                    timeout_seconds=_safe_int(str(payload.get("timeout_seconds", "10")), 10),
                )
                response = {
                    "kind": "code_execution",
                    "language": result.language,
                    "code": code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "elapsed_seconds": result.elapsed_seconds,
                    "timed_out": result.timed_out,
                    "source_file": str(result.source_path),
                    "output_file": str(result.output_path),
                    "manifest": str(result.manifest_path),
                }
                _record_continuous_step(
                    config,
                    "sandboxed_code_run",
                    f"run {result.language} code",
                    "ran explicitly submitted code in a no-network sandbox and saved source and output artifacts",
                    outputs={key: value for key, value in response.items() if key != "code"},
                    source="web_code",
                )
                self._send_json(response)
            except PermissionError as error:
                self._send_json({"error": str(error)}, HTTPStatus.FORBIDDEN)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_agent_create(self) -> None:
            try:
                payload = self._read_json()
                created = AgentRegistry(config).create(
                    name=str(payload.get("name", "")),
                    template=str(payload.get("template", "artifact")),
                    goal=str(payload.get("goal", "")),
                    memory=agent.memory,
                )
                response = {
                    "id": created.agent_id,
                    "name": created.name,
                    "template": created.template,
                    "goal": created.goal,
                    "status": created.status,
                    "manifest_path": str(created.manifest_path),
                    "self_update_id": created.self_update_id,
                    "working_copy": created.working_copy,
                    "plan_path": created.plan_path,
                }
                _record_continuous_step(
                    config,
                    "agent_create",
                    f"create {created.template} agent {created.name}",
                    "created a review-gated task agent manifest and saved it to local agent registry",
                    outputs=response,
                    source="web_agents",
                )
                self._send_json(response)
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[web] {self.address_string()} {fmt % args}")

        def _handle_download(self, raw_path: str) -> None:
            try:
                file_path = _safe_download_path(config, raw_path)
                data = file_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self._send_json({"error": "file not found"}, HTTPStatus.NOT_FOUND)
            except PermissionError as error:
                self._send_json({"error": str(error)}, HTTPStatus.FORBIDDEN)

        def _handle_reveal(self) -> None:
            try:
                payload = self._read_json()
                file_path = _safe_download_path(config, str(payload.get("path", "")))
                _reveal_file_location(file_path)
                self._send_json({"status": "opened", "path": str(file_path), "folder": str(file_path.parent)})
            except FileNotFoundError:
                self._send_json({"error": "file not found"}, HTTPStatus.NOT_FOUND)
            except PermissionError as error:
                self._send_json({"error": str(error)}, HTTPStatus.FORBIDDEN)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _read_json(self) -> dict[str, Any]:
            length = _safe_int(self.headers.get("Content-Length", "0"), 0)
            raw = self.rfile.read(max(0, min(length, 2_000_000)))
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def _read_multipart_files(self) -> list[dict[str, Any]]:
            content_type = self.headers.get("Content-Type", "")
            match = re.search(r"boundary=([^;]+)", content_type)
            if not match:
                raise ValueError("multipart boundary is missing")
            boundary = match.group(1).strip().strip('"').encode("utf-8")
            length = _safe_int(self.headers.get("Content-Length", "0"), 0)
            raw = self.rfile.read(max(0, min(length, 50_000_000)))
            files: list[dict[str, Any]] = []
            for part in raw.split(b"--" + boundary):
                if b"filename=" not in part:
                    continue
                header, _, content = part.partition(b"\r\n\r\n")
                filename_match = re.search(rb'filename="([^"]*)"', header)
                if not filename_match:
                    continue
                filename = filename_match.group(1).decode("utf-8", errors="replace")
                content = content.rstrip(b"\r\n-")
                if filename and content:
                    files.append({"name": filename, "content": content})
            if not files:
                raise ValueError("No files were uploaded")
            return files

        def _send_text(self, body: str, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_json(self, body: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_file(self, path: Path, status: HTTPStatus = HTTPStatus.OK) -> None:
            if not path.exists() or not path.is_file():
                self._send_text("Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
                return
            content = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return GimaWebHandler


def _status_payload(config: Config, agent: Agent, brain: BrainServer) -> dict[str, Any]:
    brain_status = brain.status()
    model_levels = ModelLevelManager(config).levels()
    return {
        "name": config.name,
        "workspace": str(config.resolved_workspace),
        "memory": str(config.resolved_data_dir),
        "downloads": str(config.resolved_downloads_dir),
        "hands": str(config.resolved_hands_dir),
        "hands_in": str(config.resolved_hands_in_dir),
        "hands_out": str(config.resolved_hands_out_dir),
        "brain_csv": str(config.resolved_brain_csv_path),
        "brain_csv_rows": _count_csv_records(config.resolved_brain_csv_path),
        "stomach": str(config.resolved_stomach_dir),
        "continuous": str(config.resolved_continuous_dir),
        "memory_rows": _count_csv_rows(config.resolved_data_dir / "csv" / "knowledge.csv"),
        "conversation_rows": _count_csv_rows(config.resolved_data_dir / "csv" / "conversations.csv"),
        "brain": brain_status,
        "model": brain_status.get("models") or config.model.model,
        "active_model_level": config.model.active_level,
        "model_levels": [
            {
                "level": level.level,
                "name": level.name,
                "model": level.model,
                "model_path": str(level.model_path),
                "context_size": level.context_size,
                "available": level.available,
                "status": level.status,
                "description": level.description,
                "source": level.source,
            }
            for level in model_levels
        ],
        "session_id": agent.session_id,
    }


def _doctor_payload(config: Config, brain: BrainServer) -> dict[str, Any]:
    return build_doctor_report(config, brain.status())


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _count_csv_records(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        cleaned = (line.replace("\x00", "") for line in handle)
        try:
            return sum(1 for _ in csv.DictReader(cleaned))
        except csv.Error:
            return _count_csv_rows(path)


def _capability_payload(config: Config, agent: Agent, brain: BrainServer) -> list[dict[str, str]]:
    store = CapabilityStore(config.resolved_data_dir)
    if not store.capabilities_path.exists():
        store.build(agent, brain)
    order = {"done": 0, "started": 1, "planned": 2, "missing": 3}
    rows = sorted(store.list_rows(), key=lambda row: (order.get(row.get("status", ""), 9), row.get("family", ""), row.get("capability", "")))
    return [
        {
            "id": row.get("id", ""),
            "family": row.get("family", ""),
            "capability": row.get("capability", ""),
            "status": row.get("status", ""),
            "local_support": row.get("local_support", ""),
            "next_action": row.get("next_action", ""),
        }
        for row in rows[:50]
    ]


def _codex_mode_payload(config: Config, brain: BrainServer) -> list[dict[str, str]]:
    updates = SelfUpdateManager(config.resolved_workspace, config.resolved_data_dir).list_requests()
    vibe_updates = [update for update in updates if update.get("vibe_code_plan_path") or update.get("agent_kind") == "offline_vibe_coding"]
    output_count = len(_output_payload(config))
    brain_rows = _count_csv_records(config.resolved_brain_csv_path)
    brain_status = brain.status()
    web_running = _web_ui_running(config)
    brain_running = bool(brain_status.get("running"))
    codex_path = shutil.which("codex")
    codex_version = ""
    if codex_path:
        try:
            result = subprocess.run([codex_path, "--version"], capture_output=True, text=True, timeout=5, check=False)
            codex_version = (result.stdout or result.stderr).strip().splitlines()[0][:120]
        except Exception as error:
            codex_version = f"version check failed: {error}"

    return [
        {
            "capability": "Codex CLI connection",
            "status": "connected" if codex_path else "missing",
            "gima_support": f"Codex CLI path: {codex_path or 'not found'}; version: {codex_version or 'unknown'}.",
            "codex_gap": "Browser requests still use Gima's isolated-copy coding workflow instead of unrestricted terminal access.",
        },
        {
            "capability": "Chat with repo and file context",
            "status": "done" if brain_rows else "started",
            "gima_support": f"Chat UI, uploaded file memory, hands/in, and brain.csv retrieval are wired. brain.csv rows={brain_rows}.",
            "codex_gap": "Needs stronger embeddings and larger local/teacher models to match Codex reasoning quality.",
        },
        {
            "capability": "Read, search, and organize local files",
            "status": "done",
            "gima_support": "Uploads go to hands/in, stomach inventory records them, continuous CSV records work, and outputs are downloadable.",
            "codex_gap": "Deep binary/media understanding depends on optional tools and installed local models.",
        },
        {
            "capability": "Vibe coding agent",
            "status": "done" if vibe_updates else "ready",
            "gima_support": "Create Vibe Code Plan makes a copied workspace, candidate-file ranking, patch path, snapshot, and approval trail.",
            "codex_gap": "Direct autonomous patching is intentionally staged through copied workspaces and approval.",
        },
        {
            "capability": "Run tests and verify changes",
            "status": "started",
            "gima_support": "Codex can run terminal tests for Gima now; the web UI shows the resulting outputs, agents, and deployment state.",
            "codex_gap": "The local web UI does not expose arbitrary shell execution yet because that needs a careful permission gate.",
        },
        {
            "capability": "Deploy, restart, and track services",
            "status": "done" if web_running and brain_running else "started",
            "gima_support": f"Deployment panel tracks Web UI and Brain Server. web={'running' if web_running else 'stopped'}, brain={'running' if brain_running else 'stopped'}.",
            "codex_gap": "Cloud deploy, PR creation, and remote CI need GitHub/provider bindings before Gima can do them alone.",
        },
        {
            "capability": "Artifacts and outputs",
            "status": "done" if output_count else "ready",
            "gima_support": f"hands/out is scanned for generated files with download links. outputs={output_count}.",
            "codex_gap": "High-end image/video/music quality still depends on free local models or linked APIs.",
        },
    ]


def _ai_task_map_payload(config: Config) -> dict[str, Any]:
    store = AITaskMapStore(config.resolved_data_dir)
    if not store.path.exists():
        return {
            "status": "missing",
            "path": str(store.path),
            "rows": 0,
            "sample": [],
        }
    rows = store.list_rows(limit=500)
    priority_terms = ("Codex", "Seedance", "Source review", "Video generation", "Teacher-model learning")
    sample = [
        {
            "letter": row.get("letter", ""),
            "task": row.get("task", ""),
            "gima_status": row.get("gima_status", ""),
            "provider_examples": row.get("provider_examples", ""),
            "public_sources": row.get("public_sources", ""),
        }
        for row in rows
        if any(term.casefold() in " ".join(row.values()).casefold() for term in priority_terms)
    ][:6]
    if not sample:
        sample = [
            {
                "letter": row.get("letter", ""),
                "task": row.get("task", ""),
                "gima_status": row.get("gima_status", ""),
                "provider_examples": row.get("provider_examples", ""),
                "public_sources": row.get("public_sources", ""),
            }
            for row in rows[:6]
        ]
    return {
        "status": "ready",
        "path": str(store.path),
        "rows": len(rows),
        "sample": sample,
    }


def _public_apis_payload(config: Config, parsed) -> dict[str, Any]:
    params = urllib.parse.parse_qs(parsed.query)
    try:
        return PublicApiCatalogStore(config).search(
            query=params.get("q", [""])[0],
            category=params.get("category", [""])[0],
            auth=params.get("auth", [""])[0],
            https_only=params.get("https", ["0"])[0] in {"1", "true", "yes", "on"},
            no_auth_only=params.get("no_auth", ["0"])[0] in {"1", "true", "yes", "on"},
            refresh=params.get("refresh", ["0"])[0] in {"1", "true", "yes", "on"},
            limit=_safe_int(params.get("limit", ["50"])[0], 50),
        )
    except Exception as error:
        return {
            "error": str(error),
            "source": PublicApiCatalogStore.repo_url,
            "hint": "Check internet access, then retry. Existing cache will be used automatically after the first successful refresh.",
        }


def _deployment_payload(config: Config, brain: BrainServer) -> list[dict[str, str]]:
    brain_status = brain.status()
    web_pid_path = config.resolved_data_dir / "runtime" / "web_ui.pid"
    web_pid = _read_pid(web_pid_path)
    web_running = _web_ui_running(config)
    rows = [
        {
            "name": "Web UI",
            "status": "running" if web_running else "stopped",
            "detail": f"http://127.0.0.1:8787 | pid={web_pid or 'unknown'}",
            "path": str(web_pid_path),
        },
        {
            "name": "Brain Server",
            "status": "running" if brain_status.get("running") else "stopped",
            "detail": f"model={brain_status.get('models') or config.model.model} | pid={brain_status.get('pid') or 'unknown'}",
            "path": str(config.resolved_data_dir / "brain.pid"),
        },
        {
            "name": "Brain CSV",
            "status": "ready" if config.resolved_brain_csv_path.exists() else "missing",
            "detail": f"{_count_csv_records(config.resolved_brain_csv_path)} rows | {config.resolved_brain_csv_path}",
            "path": str(config.resolved_brain_csv_path),
        },
        {
            "name": "Hands Output",
            "status": "ready" if config.resolved_hands_out_dir.exists() else "missing",
            "detail": str(config.resolved_hands_out_dir),
            "path": str(config.resolved_hands_out_dir),
        },
    ]
    return rows


def _agent_payload(config: Config) -> list[dict[str, str]]:
    updates = SelfUpdateManager(config.resolved_workspace, config.resolved_data_dir).list_requests()
    rows: list[dict[str, str]] = []
    daily_agent = latest_daily_improvement_agent(config)
    if daily_agent:
        rows.append(
            {
                "name": daily_agent.get("agent", "Daily Improvement Agent"),
                "status": daily_agent.get("status", "planned"),
                "detail": f"{daily_agent.get('today_priority', '')} | next: {daily_agent.get('next_command', '')}",
                "path": daily_agent.get("run_path", ""),
            }
        )
    ai_era_agent = latest_ai_era_requirements_agent(config)
    if ai_era_agent:
        rows.append(
            {
                "name": ai_era_agent.get("agent", "AI Era Requirements Agent"),
                "status": ai_era_agent.get("cadence", "minute_local_check"),
                "detail": f"{ai_era_agent.get('next_update', '')} | updated={ai_era_agent.get('updated_at', '')}",
                "path": ai_era_agent.get("latest_path", ""),
            }
        )
    area_agent = latest_area_agent_supervisor(config)
    if area_agent:
        rows.append(
            {
                "name": area_agent.get("agent", "24/7 Area Agent Supervisor"),
                "status": area_agent.get("cadence", "continuous_background_loop"),
                "detail": (
                    f"areas={area_agent.get('area_count', 0)} "
                    f"needs_attention={area_agent.get('needs_attention_count', 0)} "
                    f"| next: {area_agent.get('next_action', '')}"
                ),
                "path": area_agent.get("latest_path", ""),
            }
        )
    for created in AgentRegistry(config).list_agents()[:12]:
        rows.append(
            {
                "name": created.get("name", "Gima task agent"),
                "status": created.get("status", "created"),
                "detail": f"{created.get('template', 'agent')}: {created.get('goal', '')}",
                "path": created.get("manifest_path", ""),
            }
        )
    for update in updates[:8]:
        agent_kind = update.get("agent_kind") or ("offline_vibe_coding" if update.get("vibe_code_plan_path") else "self_update")
        rows.append(
            {
                "name": update.get("id", "update"),
                "status": update.get("status", "unknown"),
                "detail": f"{agent_kind}: {update.get('feature', '')}",
                "path": update.get("vibe_code_plan_path") or update.get("plan_path") or update.get("manifest_path", ""),
            }
        )
    if not rows:
        rows.append(
            {
                "name": "Offline vibe coding",
                "status": "ready",
                "detail": "No active plan. Use Create Vibe Code Plan to start a copied-workspace agent run.",
                "path": str(config.resolved_data_dir / "self_updates"),
            }
        )
    return rows


def _output_payload(config: Config) -> list[dict[str, str]]:
    root = config.resolved_hands_out_dir
    if not root.exists():
        return []
    files = [path for path in root.rglob("*") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    rows: list[dict[str, str]] = []
    for path in files[:16]:
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "kind": mimetypes.guess_type(path.name)[0] or path.suffix.lstrip(".") or "file",
                "size_bytes": str(path.stat().st_size),
                "size_label": _size_label(path.stat().st_size),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)),
            }
        )
    return rows


def _human_folder_payload(config: Config) -> list[dict[str, str]]:
    folders = [
        ("brain", config.resolved_data_dir / "brain", "learned knowledge, research CSVs, task map, Dream ideas"),
        ("heart", config.resolved_data_dir / "heart", "policies and rules Gima must not violate"),
        ("hands/in", config.resolved_hands_in_dir, "all uploaded user inputs"),
        ("hands/out", config.resolved_hands_out_dir, "all generated files, reports, songs, videos, code plans"),
        ("stomach", config.resolved_stomach_dir, "inventory of uploaded items before/after processing"),
        ("continuous", config.resolved_continuous_dir, "timestamped work steps, code-line records, process trail"),
        ("conversation", config.resolved_data_dir / "csv" / "conversations.csv", "conversation database"),
        ("dream", config.resolved_data_dir / "brain" / "Dream", "new theory ideas, reviews, experiments, sources"),
        ("apps", config.resolved_data_dir / "apps", "desktop/mobile/cloud app packaging notes"),
    ]
    rows = []
    for name, path, purpose in folders:
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
        rows.append(
            {
                "name": name,
                "path": str(path),
                "purpose": purpose,
                "status": "ready" if path.exists() else "missing",
            }
        )
    return rows


def _app_plan_payload(config: Config) -> list[dict[str, str]]:
    return [
        {
            "name": "Web/PWA",
            "status": "working",
            "platforms": "Mac, Windows, Android, iOS through browser install",
            "next": "Keep local server running, open same LAN URL on phones, then Add to Home Screen.",
        },
        {
            "name": "Native desktop wrapper",
            "status": "planned",
            "platforms": "macOS, Windows",
            "next": "Package the local web UI with a lightweight Tauri/Electron wrapper after core tools stabilize.",
        },
        {
            "name": "Mobile companion",
            "status": "planned",
            "platforms": "Android, iOS",
            "next": "Use the PWA first; native mobile needs a sync API and local-network pairing.",
        },
        {
            "name": "Automation runner",
            "status": "started",
            "platforms": "macOS launchd now; Windows Task Scheduler planned",
            "next": "Keep daily capability learning and AI task map refresh in brain CSVs.",
        },
        {
            "name": "Adaptive small-system mode",
            "status": "started",
            "platforms": "low RAM/CPU machines",
            "next": "Use smaller local model, brain-first retrieval, shorter context, and offline deterministic tools.",
        },
    ]


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _web_ui_running(config: Config) -> bool:
    web_pid = _read_pid(config.resolved_data_dir / "runtime" / "web_ui.pid")
    if web_pid and _pid_running(web_pid):
        return True
    try:
        with socket.create_connection(("127.0.0.1", 8787), timeout=0.2):
            return True
    except OSError:
        return False


def _size_label(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def _uploads_dir(config: Config) -> Path:
    return config.resolved_hands_in_dir


def _legacy_uploads_dir(config: Config) -> Path:
    return config.resolved_data_dir / "web_uploads"


def _hands_dir(config: Config) -> Path:
    return config.resolved_hands_dir


def _hands_out_dir(config: Config) -> Path:
    return config.resolved_hands_out_dir


def _stomach_dir(config: Config) -> Path:
    return config.resolved_stomach_dir


def _continuous_dir(config: Config) -> Path:
    return config.resolved_continuous_dir


def _stomach_inventory_path(config: Config) -> Path:
    return _stomach_dir(config) / "uploaded_items.csv"


def _continuous_steps_path(config: Config) -> Path:
    return _continuous_dir(config) / "work_steps.csv"


def _continuous_code_path(config: Config) -> Path:
    return _continuous_dir(config) / "code_lines.csv"


def _linked_mind_providers(config: Config, requested: list[str] | None = None) -> list[str]:
    available = {row["provider"] for row in teacher_secret_status(config.resolved_workspace) if row["available"] == "yes"}
    aliases = {
        "openai": "chatgpt",
        "chatgpt": "chatgpt",
        "gemini": "gemini",
        "google": "gemini",
        "anthropic": "anthropic",
        "claude": "anthropic",
        "xai": "xai",
        "grok": "xai",
        "deepseek": "deepseek",
        "openrouter": "openrouter",
        "local": "local",
    }
    candidates = requested or ["local", "chatgpt", "gemini", "anthropic", "xai", "deepseek", "openrouter"]
    providers: list[str] = []
    for raw_provider in candidates:
        raw = raw_provider.casefold().strip()
        provider = aliases.get(raw)
        if not provider:
            continue
        provider_available = provider == "local" or provider in available or (provider == "chatgpt" and "openai" in available)
        if not provider_available:
            continue
        if provider not in providers:
            providers.append(provider)
    if requested is None and "local" not in providers:
        providers.insert(0, "local")
    return providers


def _free_quota_payload(config: Config) -> dict[str, Any]:
    tracker = FreeQuotaTracker(config.resolved_usage_dir, config.teacher_models.free_quota_daily_limits)
    return {
        "free_quota_mode": config.teacher_models.free_quota_mode,
        "path": str(tracker.path),
        "quotas": tracker.status(),
        "note": "Local safety caps for free-tier/trial APIs. Provider-side limits still apply.",
    }


def _ai_router_plan(config: Config, params: dict[str, list[str]]) -> dict[str, Any]:
    request = RoutingRequest(
        message=params.get("message", [""])[0],
        mode=params.get("mode", ["AUTO"])[0],
        manual_model=params.get("model", [""])[0],
        quality=params.get("quality", ["balanced"])[0],
        speed=params.get("speed", ["balanced"])[0],
        budget=params.get("budget", ["balanced"])[0],
        privacy=params.get("privacy", ["normal"])[0],
        has_images=params.get("has_images", ["0"])[0].casefold() in {"1", "true", "yes"},
        context_tokens=_safe_int(params.get("context_tokens", ["0"])[0], 0),
        tool_use=params.get("tool_use", ["0"])[0].casefold() in {"1", "true", "yes"},
    )
    decision = OpenRouterTaskRouter(config).decide(request)
    return {
        "request_id": decision.request_id,
        "provider": decision.provider,
        "model": decision.model,
        "task_category": decision.task_category,
        "mode": decision.mode,
        "fallbacks": decision.fallbacks,
        "reason": decision.reason,
        "cloud_allowed": decision.cloud_allowed,
        "estimated_prompt_tokens": decision.estimated_prompt_tokens,
        "estimated_cost_usd": decision.estimated_cost_usd,
        "security": {
            "secrets_returned": False,
            "management_key_used_for_inference": False,
        },
    }


def _free_llm_plan_payload(parsed) -> dict[str, Any]:
    params = urllib.parse.parse_qs(parsed.query)
    return free_llm_plan(
        params.get("task", [""])[0],
        privacy=params.get("privacy", ["balanced"])[0],
        limit=_safe_int(params.get("limit", ["6"])[0], 6),
    )


def _should_use_all_ai(message: str) -> bool:
    normalized = " ".join(message.casefold().split())
    return any(
        phrase in normalized
        for phrase in {
            "ask all ai",
            "ask all ais",
            "all ai engines",
            "all linked minds",
            "all online ai",
            "answer from them",
            "answer from all",
            "learn from ais",
            "learn from all ai",
            "use all ai",
            "use all ais",
            "multi ai",
            "multiple ai",
        }
    )


def _should_use_cloud_chat(config: Config, message: str) -> bool:
    if not cloud_allowed():
        return False
    if not _cloud_chat_providers(config):
        return False
    normalized = " ".join(message.casefold().split())
    if any(term in normalized for term in {"use local", "local only", "offline only", "use brain", "brain:"}):
        return False
    return True


def _chat_provider_from_payload(payload: dict[str, Any]) -> str:
    raw = str(payload.get("chat_provider", "") or "").strip().casefold()
    aliases = {
        "": "",
        "local": "local",
        "brain": "local",
        "memory": "local",
        "openai": "chatgpt",
        "chatgpt": "chatgpt",
        "gpt": "chatgpt",
        "openrouter": "openrouter",
        "anthropic": "anthropic",
        "claude": "anthropic",
        "gemini": "gemini",
        "google": "gemini",
    }
    return aliases.get(raw, "")


def _cloud_chat_providers(config: Config) -> list[str]:
    available = {row["provider"] for row in teacher_secret_status(config.resolved_workspace) if row["available"] == "yes"}
    providers: list[str] = []
    for provider in ["chatgpt", "openrouter", "anthropic", "gemini"]:
        key = "openai" if provider == "chatgpt" else provider
        if key in available:
            providers.append(provider)
    return providers


def _cloud_model_name(config: Config, provider: str) -> str:
    if provider == "chatgpt":
        return config.teacher_models.openai_model
    if provider == "anthropic":
        return config.teacher_models.anthropic_model
    if provider == "gemini":
        return config.teacher_models.gemini_model
    if provider == "openrouter":
        return config.teacher_models.openrouter_model
    return provider


def _cloud_chat_prompt(message: str) -> str:
    return (
        "You are answering inside Gima, Gimhan Gunarathne's local-first AI command deck. "
        "Speak as Gima's assistant layer, not as the raw model provider. "
        "If asked who developed Gima, say Gimhan Gunarathne is the project owner/developer and Codex can help implement reviewable code upgrades. "
        "If asked how Gima can develop or improve, describe the safe engineering loop: inspect the project, preserve working features, edit reviewably, run tests, write an upgrade report, and restart/sync after approval. "
        "You may mention that this particular answer is powered by an external provider only as implementation detail; do not answer 'I am OpenAI' or 'my developers at OpenAI' as Gima's identity. "
        "Be useful, direct, accurate, and concise. "
        "Gima can route explicit web/current-information requests through its own public web search and import system before cloud chat. "
        "If this prompt asks for current information but does not include fetched sources, say you did not browse in this answer and suggest asking Gima to search the internet; do not say this chat has no browsing tool. "
        "For high-stakes facts, recommend source verification. "
        "Do not claim you accessed local files, tools, camera, microphone, or the internet unless the prompt includes that evidence.\n\n"
        f"User message:\n{message}"
    )


def _strip_all_ai_prefix(message: str) -> str:
    cleaned = re.sub(
        r"\b(ask|use|learn from|answer from|all|online|linked|ai|ais|engines|minds|multi|multiple|then|them|please|gima)\b",
        " ",
        message,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :.-")
    return cleaned or message


def _should_force_brain(message: str) -> bool:
    normalized = " ".join(message.casefold().split()).strip()
    return (
        normalized.startswith("use brain")
        or normalized.startswith("brain:")
        or normalized.startswith("brain ")
        or normalized.startswith("check brain")
        or normalized.startswith("search brain")
        or "use your brain" in normalized
        or "answer from brain" in normalized
    )


def _chat_github_sync_answer(config: Config, message: str) -> dict[str, Any] | None:
    normalized = " ".join(message.casefold().split()).strip()
    github_named = "github" in normalized or "git hub" in normalized
    sync_named = any(term in normalized for term in ("sync", "push", "publish", "pull request", " pr"))
    if not (github_named and sync_named):
        return None

    gh_path = shutil.which("gh")
    if not gh_path:
        local_gh = Path.home() / ".local" / "bin" / "gh"
        gh_path = str(local_gh) if local_gh.is_file() and os.access(local_gh, os.X_OK) else ""
    if not gh_path:
        return {
            "reply": "GitHub CLI is not installed. Install `gh`, restart Gima, then ask again.",
            "github_status": "cli_missing",
        }

    try:
        auth = subprocess.run(
            [gh_path, "auth", "status"],
            cwd=str(config.resolved_workspace),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "reply": f"GitHub CLI was found at `{gh_path}`, but its authentication status could not be checked: {error}",
            "github_status": "status_error",
        }

    if auth.returncode != 0:
        return {
            "reply": (
                f"GitHub CLI is installed at `{gh_path}`, but it is not authenticated.\n\n"
                "Run this once in Terminal:\n\n```bash\ngh auth login --hostname github.com --git-protocol ssh --web\n```\n\n"
                "Then return here and send: `confirm GitHub sync`."
            ),
            "github_status": "authentication_required",
        }

    confirmed = "confirm github sync" in normalized or "confirm git hub sync" in normalized
    if not confirmed:
        return {
            "reply": (
                "GitHub CLI is installed and authenticated. The guarded sync will check staged content for likely API keys, "
                "create a branch, commit, push, and open a draft pull request. Send `confirm GitHub sync` to proceed."
            ),
            "github_status": "confirmation_required",
        }

    script = config.resolved_workspace / "scripts" / "github_sync_gima.sh"
    if not script.is_file():
        return {"reply": f"GitHub sync helper is missing: `{script}`", "github_status": "helper_missing"}
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        [str(Path.home() / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    )
    try:
        result = subprocess.run(
            [str(script)],
            cwd=str(config.resolved_workspace),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "reply": "GitHub sync exceeded five minutes and was stopped. No success was reported; review the repository before retrying.",
            "github_status": "timed_out",
        }
    except OSError as error:
        return {"reply": f"GitHub sync could not start: {error}", "github_status": "run_error"}
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode != 0:
        return {
            "reply": f"GitHub sync stopped with exit code {result.returncode}.\n\n```text\n{output[-6000:]}\n```",
            "github_status": "failed",
            "exit_code": result.returncode,
        }
    return {
        "reply": f"GitHub sync completed.\n\n```text\n{output[-6000:]}\n```",
        "github_status": "completed",
        "exit_code": 0,
    }


def _chat_huggingface_learning_answer(config: Config, agent: Agent, message: str) -> dict[str, Any] | None:
    url = extract_huggingface_url(message)
    if not url:
        return None
    try:
        result = HuggingFaceLearner(config, agent.memory).learn(url)
    except Exception as error:
        return {
            "reply": (
                f"I found this Hugging Face URL but could not import it safely:\n{url}\n\n"
                f"Error: {error}\n\n"
                "Gima only imports public Hugging Face metadata/model-card text and stores it for review. "
                "It will not copy private data, hidden prompts, credentials, or restricted model assets."
            ),
            "sources": [url],
            "used_internet": True,
            "huggingface_learning": True,
            "status": "error",
        }
    recommendations = "\n".join(f"- {item}" for item in result.recommendations)
    files_text = "\n".join(f"- {file['path']}" for file in result.files)
    reply = (
        f"I imported and analyzed this public Hugging Face {result.repo_type}:\n"
        f"{result.source_url}\n\n"
        f"**What Gima learned**\n{result.summary}\n\n"
        f"**What Gima can use to improve itself**\n{recommendations}\n\n"
        "Saved as reviewable Gima memory. I did not change Gima's active model or code automatically.\n\n"
        f"Generated files:\n{files_text}"
    )
    return {
        "reply": reply,
        "files": result.files,
        "sources": [result.source_url],
        "used_internet": True,
        "huggingface_learning": True,
        "repo_id": result.repo_id,
        "repo_type": result.repo_type,
        "record_id": result.record_id,
        "review_id": result.review_id,
        "status": "review_saved",
    }


def _strip_brain_prefix(message: str) -> str:
    cleaned = re.sub(
        r"^\s*(use\s+your\s+brain|use\s+brain|answer\s+from\s+brain|check\s+brain|search\s+brain|brain)\s*[:,-]?\s*",
        "",
        message,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned or message


def _brain_answer(config: Config, agent: Agent, message: str) -> tuple[str, list[dict[str, str]]]:
    query = _strip_brain_prefix(message)
    rows = _brain_search_rows(config, query, limit=8)
    research_answer = agent.research_reasoner.answer_from_memory(query, rows)
    if research_answer:
        agent.memory.audit("brain_forced_answer", query[:120], research_answer.trace_id, "ok")
        return research_answer.text, rows
    if rows:
        lines = [
            "I checked Gima brain.csv and found related records, but the evidence was weak.",
            "",
            "Closest brain rows:",
        ]
        lines.extend(f"- {row.get('title', 'Untitled')}: {row.get('content', '')[:240]}" for row in rows[:5])
        return "\n".join(lines), rows
    return (
        "I checked Gima brain.csv but did not find matching knowledge yet. "
        "Upload files, ask Gima to learn a topic, or ask linked minds, then try `use brain:` again.",
        rows,
    )


def _brain_search_rows(config: Config, query: str, limit: int = 8) -> list[dict[str, str]]:
    _refresh_brain_csv(config)
    path = config.resolved_brain_csv_path
    if not path.exists():
        return []
    terms = [term for term in re.findall(r"[^\W_][\w-]{1,}", query.casefold(), flags=re.UNICODE) if term not in _BRAIN_STOPWORDS]
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            shaped = _shape_brain_row(index, row)
            score = _brain_row_score(shaped, terms)
            if score > 0 or not terms:
                shaped["_score"] = f"{score:.3f}"
                rows.append(shaped)
    rows.sort(key=lambda row: float(row.get("_score", "0") or "0"), reverse=True)
    return rows[: max(1, limit)]


def _shape_brain_row(index: int, row: dict[str, str]) -> dict[str, str]:
    content = row.get("content", "") or row.get("summary", "")
    summary = row.get("summary", "")
    source = row.get("path", "") or row.get("media_path", "") or "Gima brain.csv"
    keywords = " ".join(
        value
        for value in [
            row.get("source_type", ""),
            row.get("category", ""),
            row.get("subcategory", ""),
            row.get("kind", ""),
            row.get("title", ""),
            summary,
        ]
        if value
    )
    return {
        "id": f"brain_{index}",
        "source_type": row.get("source_type", ""),
        "category": row.get("category", ""),
        "subcategory": row.get("subcategory", ""),
        "kind": row.get("kind", ""),
        "title": row.get("title", "") or Path(source).name or f"Brain row {index}",
        "content": content,
        "summary": summary,
        "keywords": keywords,
        "source": source,
        "path": row.get("path", ""),
        "media_path": row.get("media_path", ""),
        "status": row.get("status", ""),
        "confidence": row.get("confidence", ""),
        "updated_at": row.get("updated_at", ""),
    }


def _brain_row_score(row: dict[str, str], terms: list[str]) -> float:
    if not terms:
        return 1.0
    title = row.get("title", "").casefold()
    keywords = row.get("keywords", "").casefold()
    content = row.get("content", "").casefold()
    score = 0.0
    for term in terms:
        if term in title:
            score += 4.0
        if term in keywords:
            score += 2.0
        if term in content:
            score += 1.0
    if row.get("source"):
        score += 0.2
    if row.get("status") == "active":
        score += 0.2
    return score


def _public_brain_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "id": row.get("id", ""),
        "title": row.get("title", ""),
        "category": row.get("category", ""),
        "source_type": row.get("source_type", ""),
        "path": row.get("path", "") or row.get("source", ""),
        "summary": (row.get("summary", "") or row.get("content", ""))[:360],
        "score": row.get("_score", ""),
    }


_BRAIN_STOPWORDS = {
    "about",
    "after",
    "again",
    "brain",
    "check",
    "from",
    "gima",
    "have",
    "into",
    "know",
    "learn",
    "right",
    "search",
    "that",
    "the",
    "this",
    "what",
    "with",
    "your",
}

_MODEL_OVERRIDE_LOCK = threading.RLock()


def _with_temporary_model_level(config: Config, level: str | None, action: Callable[[], str]) -> str:
    if not level:
        return action()
    manager = ModelLevelManager(config)
    try:
        target = manager.level(level)
    except ValueError:
        return action()
    if not target.available or config.model.active_level == target.level:
        return action()
    original = dict(config.model.__dict__)
    with _MODEL_OVERRIDE_LOCK:
        manager.apply_level(target.level)
        try:
            return action()
        finally:
            for key, value in original.items():
                setattr(config.model, key, value)


def _ensure_storage_paths(config: Config) -> None:
    _uploads_dir(config).mkdir(parents=True, exist_ok=True)
    _hands_dir(config).mkdir(parents=True, exist_ok=True)
    config.resolved_hands_in_dir.mkdir(parents=True, exist_ok=True)
    config.resolved_hands_out_dir.mkdir(parents=True, exist_ok=True)
    _stomach_dir(config).mkdir(parents=True, exist_ok=True)
    _continuous_dir(config).mkdir(parents=True, exist_ok=True)
    _ensure_csv_header(
        _continuous_steps_path(config),
        [
            "timestamp",
            "event_id",
            "source",
            "action",
            "instruction",
            "step",
            "inputs_json",
            "outputs_json",
            "record_id",
            "status",
        ],
    )
    _ensure_csv_header(_continuous_code_path(config), ["timestamp", "event_id", "reason", "file_path", "line_number", "code"])
    _backfill_hands_storage(config)
    _refresh_brain_csv(config)


def _list_uploaded_files(config: Config) -> list[dict[str, Any]]:
    roots = [_uploads_dir(config), config.resolved_downloads_dir, _legacy_uploads_dir(config)]
    seen: set[Path] = set()
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.iterdir():
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(path)
    files = [_file_payload(path) for path in sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)]
    return files[:50]


def _backfill_hands_storage(config: Config) -> None:
    for root in [config.resolved_downloads_dir, _legacy_uploads_dir(config)]:
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.is_file():
                target = config.resolved_hands_in_dir / path.name
                if not target.exists():
                    shutil.copy2(path, target)
    legacy_media = config.resolved_data_dir / "media"
    if legacy_media.exists():
        target_root = config.resolved_hands_out_dir / "legacy_media"
        for path in legacy_media.rglob("*"):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(legacy_media)
            except ValueError:
                relative = Path(path.name)
            target = target_root / relative
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _file_payload(path: Path, record_id: str = "") -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "download_url": _download_url(path),
        "size_bytes": stat.st_size,
        "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "record_id": record_id,
    }


def _record_stomach_item(config: Config, file_payload: dict[str, Any]) -> None:
    _stomach_dir(config).mkdir(parents=True, exist_ok=True)
    inventory_path = _stomach_inventory_path(config)
    fieldnames = ["uploaded_at", "name", "path", "size_bytes", "content_type", "record_id"]
    write_header = not inventory_path.exists()
    with inventory_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "name": file_payload.get("name", ""),
                "path": file_payload.get("path", ""),
                "size_bytes": file_payload.get("size_bytes", ""),
                "content_type": file_payload.get("content_type", ""),
                "record_id": file_payload.get("record_id", ""),
            }
        )


def _record_continuous_step(
    config: Config,
    action: str,
    instruction: str,
    step: str,
    *,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    record_id: str = "",
    source: str = "web_ui",
    status: str = "ok",
    event_id: str | None = None,
) -> str:
    _continuous_dir(config).mkdir(parents=True, exist_ok=True)
    event = event_id or uuid.uuid4().hex
    fieldnames = [
        "timestamp",
        "event_id",
        "source",
        "action",
        "instruction",
        "step",
        "inputs_json",
        "outputs_json",
        "record_id",
        "status",
    ]
    path = _continuous_steps_path(config)
    _ensure_csv_header(path, fieldnames)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writerow(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "event_id": event,
                "source": source,
                "action": action,
                "instruction": instruction,
                "step": step,
                "inputs_json": json.dumps(inputs or {}, ensure_ascii=False, sort_keys=True),
                "outputs_json": json.dumps(outputs or {}, ensure_ascii=False, sort_keys=True),
                "record_id": record_id,
                "status": status,
            }
        )
    return event


def _record_code_lines(config: Config, event_id: str, paths: list[Path], reason: str) -> None:
    _continuous_dir(config).mkdir(parents=True, exist_ok=True)
    fieldnames = ["timestamp", "event_id", "reason", "file_path", "line_number", "code"]
    path = _continuous_code_path(config)
    _ensure_csv_header(path, fieldnames)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        for raw_path in paths:
            file_path = raw_path.expanduser()
            if not file_path.is_absolute():
                file_path = config.resolved_workspace / file_path
            file_path = file_path.resolve()
            if not file_path.exists() or not file_path.is_file():
                continue
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line_number, line in enumerate(lines, start=1):
                writer.writerow(
                    {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "event_id": event_id,
                        "reason": reason,
                        "file_path": str(file_path),
                        "line_number": line_number,
                        "code": line,
                    }
                )


def _ensure_csv_header(path: Path, fieldnames: list[str]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames).writeheader()


def _project_payload(output_path: Path, manifest_path: Path, record_id: str) -> dict[str, Any]:
    payload = {
        "output": str(output_path),
        "generated_path": str(output_path),
        "download_url": _download_url(output_path),
        "manifest": str(manifest_path),
        "manifest_download_url": _download_url(manifest_path),
        "generated_dir": str(output_path.parent),
        "record_id": record_id,
        "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
    }
    script_path = output_path.parent / "video_script.md"
    prompt_pack_path = output_path.parent / "prompt_pack.md"
    if script_path.exists():
        payload["script"] = str(script_path)
        payload["script_download_url"] = _download_url(script_path)
    if prompt_pack_path.exists():
        payload["prompt_pack"] = str(prompt_pack_path)
        payload["prompt_pack_download_url"] = _download_url(prompt_pack_path)
    return payload


def _download_url(path: Path) -> str:
    return "/api/download?path=" + urllib.parse.quote(str(path))


def _lip_sync_renderer(config: Config) -> NeuralLipSyncRenderer:
    backend_dir = Path(os.environ.get("GIMA_SADTALKER_DIR", str(config.resolved_data_dir / "backends" / "SadTalker")))
    python_value = os.environ.get("GIMA_SADTALKER_PYTHON", "").strip()
    python_path = Path(python_value) if python_value else None
    return NeuralLipSyncRenderer(config.resolved_hands_out_dir / "neural_lip_sync", backend_dir, python_path)


def _voice_profile_dir(config: Config) -> Path:
    return config.resolved_data_dir / "voice" / "profiles"


def _voice_profile_manifest(config: Config) -> Path:
    return _voice_profile_dir(config) / "default_voice_profile.json"


def _save_voice_profile(config: Config, agent: Agent, audio_path: Path, profile_name: str, consent: bool) -> dict[str, Any]:
    if not consent:
        raise PermissionError("Saving a personal voice profile requires confirming this is your own voice or you have explicit permission.")
    source = audio_path.expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Voice sample does not exist: {source}")
    if source.suffix.casefold() not in {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}:
        raise ValueError("Voice sample must be an audio file such as MP3, WAV, M4A, FLAC, AAC, or OGG")
    clean_name = " ".join(profile_name.strip().split()) or "My original voice"
    voice_dir = _voice_profile_dir(config)
    voice_dir.mkdir(parents=True, exist_ok=True)
    sample_path = _unique_path(voice_dir / f"{_safe_filename(clean_name)}{source.suffix.casefold()}")
    shutil.copy2(source, sample_path)
    manifest_path = _voice_profile_manifest(config)
    manifest = {
        "kind": "gima_personal_voice_profile",
        "profile_name": clean_name,
        "owner_confirmed": True,
        "source_path": str(source),
        "sample_path": str(sample_path),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "default": True,
        "backend_status": "reference_saved_not_cloned",
        "usage_limits": [
            "Use only as Gimhan's own voice reference after explicit consent.",
            "Do not impersonate any other person.",
            "Do not claim voice cloning is available unless a configured backend actually supports it.",
            "For public posting, label synthetic or AI-assisted speech/video where appropriate.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    record_id = agent.memory.add(
        Record(
            category="audio",
            subcategory="personal_voice_profile",
            kind="consented_voice_reference",
            title=f"Personal voice profile: {clean_name}",
            content=json.dumps(manifest, indent=2),
            keywords="own voice original voice Gimhan personal voice reference consent speech lip sync",
            source=str(manifest_path),
            media_path=str(sample_path),
            status="active",
        )
    )
    _refresh_brain_csv(config)
    manifest["record_id"] = record_id
    return manifest


def _attached_paths_from_message(message: str) -> list[Path]:
    attached: list[Path] = []
    for line in message.splitlines():
        marker = line.find(": /")
        if marker < 0:
            continue
        path = Path(line[marker + 2 :].strip()).expanduser().resolve()
        if path.exists() and path.is_file():
            attached.append(path)
    return attached


def _chat_voice_profile_answer(config: Config, agent: Agent, message: str) -> dict[str, Any] | None:
    normalized = " ".join(message.casefold().split())
    if not any(term in normalized for term in {"own voice", "my voice", "original voice", "mage original voice", "personal voice"}):
        return None
    attached = _attached_paths_from_message(message)
    audio = next((path for path in attached if path.suffix.casefold() in {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}), None)
    if audio:
        profile = _save_voice_profile(config, agent, audio, "Gimhan original voice 2", consent=True)
        return {
            "reply": (
                "Saved your own voice profile as `Gimhan original voice 2`. "
                "I will treat it as your consented original voice reference. "
                "This does not mean voice cloning is active yet; it is now safely stored for future speech, lip-sync, and video workflows."
            ),
            "voice_profile": profile,
            "media_status": "own_voice_profile_saved",
            "files": [_file_payload(Path(profile["sample_path"])), _file_payload(_voice_profile_manifest(config))],
        }
    manifest = _voice_profile_manifest(config)
    if manifest.exists():
        profile = json.loads(manifest.read_text(encoding="utf-8"))
        return {
            "reply": (
                f"Your personal voice profile is already saved as `{profile.get('profile_name', 'My original voice')}`. "
                "To replace it, upload or paste a new MP3/WAV path and say: `This is my own voice, add it as my original voice`."
            ),
            "voice_profile": profile,
            "media_status": "own_voice_profile_exists",
        }
    return {
        "reply": (
            "Yes. I can add your own voice as Gima's personal voice reference. "
            "Upload an MP3/WAV/M4A sample or paste the file path, then say: "
            "`This is my own voice, add it as Gimhan original voice 2`. "
            "I will save it locally with a consent manifest. I will not impersonate anyone else or claim cloning is active until a real voice backend is connected."
        ),
        "media_status": "own_voice_needs_audio_sample",
    }


def _chat_local_multimodal_answer(config: Config, agent: Agent, message: str) -> dict[str, Any] | None:
    normalized = " ".join(message.casefold().split())
    attached = _attached_paths_from_message(message)
    image_suffixes = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
    images = [path for path in attached if path.suffix.casefold() in image_suffixes]
    wants_ocr = images and any(
        term in normalized
        for term in {
            "image to text",
            "ocr",
            "read image",
            "extract text",
            "text from image",
            "what text",
            "image text",
        }
    )
    if wants_ocr:
        output_dir = config.resolved_hands_out_dir / "image_to_text"
        output_dir.mkdir(parents=True, exist_ok=True)
        sections: list[str] = []
        files: list[dict[str, Any]] = []
        for image in images[:8]:
            records = read_file(image)
            text = "\n\n".join(record.content for record in records)
            sections.extend([f"## {image.name}", "", text or "No local OCR text was found.", ""])
            record_id = agent.memory.add(
                Record(
                    category="vision",
                    subcategory="image_to_text",
                    kind="ocr",
                    title=f"Image to text: {image.name}",
                    content=text[:100000],
                    keywords=f"image OCR text extraction {image.name}",
                    source=str(image),
                    media_path=str(image),
                    status="review",
                )
            )
            files.append(_file_payload(image, record_id))
        report_path = output_dir / f"image_to_text_{uuid.uuid4().hex[:10]}.md"
        report_path.write_text("# Gima Image To Text\n\n" + "\n".join(sections), encoding="utf-8")
        files.insert(0, _file_payload(report_path))
        _refresh_brain_csv(config)
        return {
            "reply": (
                "I extracted local image-to-text/OCR notes from the attached image file(s). "
                "If Tesseract is installed, OCR text is included; otherwise Gima still records image metadata. "
                f"Report saved at:\n{report_path}"
            ),
            "files": files,
            "media_status": "image_to_text_local",
            "used_local_ocr": True,
        }

    wants_speak = any(
        normalized.startswith(prefix)
        for prefix in {
            "speak ",
            "say ",
            "read aloud ",
            "talk to me ",
        }
    ) or "speak with me" in normalized or "conversation ai" in normalized
    if wants_speak:
        if "speak with me" in normalized or "conversation ai" in normalized:
            reply = (
                "Gima can speak locally using macOS `say`, and the CLI voice conversation path is available through "
                "`python3 -m human_ai.gima talk --voice`. In the web UI, use `/api/voice/speak` for local speech output; "
                "browser microphone transcription still needs the next push-to-talk/Whisper UI upgrade."
            )
            return {"reply": reply, "media_status": "local_voice_conversation_ready", "local": True}
        text = re.sub(r"^\s*(speak|say|read aloud|talk to me)\s*[:,-]?\s*", "", message, flags=re.IGNORECASE).strip()
        text = text[:1000]
        if text:
            Voice().speak(text)
            agent.memory.append_conversation(agent.session_id, "assistant", text, category="voice")
            return {
                "reply": f"I spoke this locally with macOS `say`:\n\n{text}",
                "media_status": "local_voice_spoken",
                "local": True,
            }
    return None


def _chat_media_answer(config: Config, message: str) -> dict[str, Any] | None:
    normalized = " ".join(message.casefold().split())
    video_terms = {"video", "movie", "cinematic", "stage", "performing", "performance", "singing", "song"}
    media_terms = {"image", "song", "music", "movie", "cinematic", "lip", "lip sync", "lip-sync", "stage", "performing", "singing"}
    creation_terms = {"make", "create", "generate", "render", "produce", "build", "can you", "need"}
    video_intent = any(term in normalized for term in video_terms) and (
        any(term in normalized for term in media_terms) or any(term in normalized for term in creation_terms)
    )
    if not video_intent:
        return None
    attached = _attached_paths_from_message(message)
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    audio_suffixes = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
    images = [path for path in attached if path.suffix.casefold() in image_suffixes]
    audio = next((path for path in attached if path.suffix.casefold() in audio_suffixes), None)
    if not attached:
        subject = _video_subject_from_message(message)
        prompt = (
            f"Make a cinematic {subject} video.\n\n"
            "Mode: video plan + scene prompts + storyboard.\n"
            "Duration: 20 seconds.\n"
            "Aspect ratio: 16:9.\n"
            "Style: realistic cinematic, dramatic lighting, premium movie color grade.\n"
            f"Subject: {subject}.\n"
            "Scenes:\n"
            "1. Wide establishing shot.\n"
            "2. Low-angle action shot with motion.\n"
            "3. Aerial tracking shot with atmosphere.\n"
            "4. Close detail shot for emotion and realism.\n"
            "5. Final hero shot with title text.\n"
            "Camera: wide angle, slow push-in, smooth pan, drone-style tracking.\n"
            "Effects: lens flare, light film grain, soft motion blur, cinematic color grade.\n"
            "Output: create storyboard, scene-by-scene prompts, video generation prompt pack, and save files in hands/out."
        )
        return {
            "reply": (
                "Yes. I can help you make a video. For the current local setup, the best first step is to create a director plan, storyboard, and video-generation prompt pack. "
                "If you upload an image or MP3, I can also route it to the image/music video tools. For true generated video frames, use OpenRouter/Veo or an open video backend when cloud/API consent is enabled.\n\n"
                "Try sending this to Gima:\n\n"
                f"```text\n{prompt}\n```"
            ),
            "files": [],
            "media_status": "video_conversation_prompt",
            "suggested_prompt": prompt,
        }
    if images and not audio:
        return {
            "reply": (
                f"I found the uploaded image `{images[0].name}`. Attach the MP3/audio file too, then ask again. "
                "I will route it directly to image music video or lip-sync planning without waiting for the chat model."
            ),
            "files": [],
            "media_status": "needs_audio",
        }
    if audio and not images:
        return {
            "reply": "I found the audio. Attach at least one JPG, PNG, or WebP image too, then ask again.",
            "files": [],
            "media_status": "needs_image",
        }
    if not audio or not images:
        return None
    prompt = message.split("\n\nAttached files", 1)[0]
    true_ai_video_requested = any(
        term in normalized
        for term in {
            "ai generated",
            "ai-generated",
            "true ai",
            "real ai",
            "generated frames",
            "generate frames",
            "video model",
            "open source video",
            "comfyui",
            "wan video",
            "hunyuan video",
        }
    )
    if true_ai_video_requested:
        open_status = OpenSourceVideoApiRenderer(config.resolved_hands_out_dir / "open_video_api").status()
        return {
            "reply": (
                "This request needs true AI-generated video frames. I will not label the local FFmpeg draft as AI-generated. "
                "ComfyUI/open-source video generation is not ready on this machine yet, so start ComfyUI with a Wan, Hunyuan, "
                "AnimateDiff, LTX-Video, or similar workflow, then use the Open Video API tool with that workflow JSON. "
                "For talking-head mouth movement only, use the Neural Lip-Sync tool, but it is CPU-slow on this PC."
            ),
            "files": [],
            "media_status": "needs_true_ai_video_backend",
            "generation_truth": "no_ai_video_frames_generated",
            "open_video_backend": open_status,
        }
    lip_sync_intent = any(term in normalized for term in {"lip sync", "lip-sync", "lipsync"}) or (
        "lip" in normalized and any(term in normalized for term in {"sing", "singing", "voice", "song", "mp3", "stage"})
    )
    if lip_sync_intent:
        renderer = _lip_sync_renderer(config)
        backend_status = renderer.status()
        preview_prompt = f"{prompt} cinematic stage live singing performance, close-up lip-sync guide, concert lighting"
        preview = AdvancedVideoSongRenderer(config.resolved_hands_out_dir / "advanced_video_song").render(
            audio,
            images,
            preview_prompt,
            aspect="16:9",
            max_duration_seconds=18,
            consent=True,
        )
        project = LipSyncPlanner(config.resolved_hands_out_dir / "lip_sync").create_project(
            audio,
            images[0],
            prompt,
            consent=True,
        )
        files = [
            preview.output_path,
            preview.manifest_path,
            preview.storyboard_path,
            preview.audio_analysis_path,
            preview.prompt_pack_path,
            project.manifest_path,
            project.timing_path,
            project.backend_path,
            project.eval_path,
        ]
        neural_note = (
            "Neural lip-sync backend is installed, but chat uses the fast renderer so it can return before the browser timeout. "
            "Use the Lip-Sync Render button for the slower true AI mouth animation."
            if backend_status["ready"]
            else f"Neural mouth animation is not installed yet. Missing: {', '.join(backend_status['missing'])}."
        )
        return {
            "reply": (
                "Created a fast local stage-performance draft from the uploaded image and song, plus a lip-sync timing project. "
                "This draft is not true AI-generated video frames; it is a local FFmpeg render with AI-directed timing/storyboard metadata. "
                f"{neural_note} Output MP4 is attached below."
            ),
            "files": [_file_payload(path) for path in files if path],
            "media_status": "fast_lip_sync_stage_draft_rendered",
            "generation_truth": "local_ffmpeg_draft_not_ai_generated_frames",
        }
    advanced_terms = {"advanced", "movie", "cinematic", "scene", "camera angle", "emotion", "film"}
    if any(term in normalized for term in advanced_terms):
        project = AdvancedVideoSongRenderer(config.resolved_hands_out_dir / "advanced_video_song").render(
            audio,
            images,
            prompt,
            aspect="16:9",
            max_duration_seconds=45,
            consent=True,
        )
        return {
            "reply": (
                "Created a 45-second advanced movie draft with audio-directed scenes, camera motion, emotion grading, "
                "pitch-activity analysis, a storyboard, and prompts for generating true new camera angles."
            ),
            "files": [
                _file_payload(project.output_path),
                _file_payload(project.manifest_path),
                _file_payload(project.storyboard_path),
                _file_payload(project.audio_analysis_path),
                _file_payload(project.prompt_pack_path),
            ],
            "media_status": "advanced_video_song_rendered",
        }
    project = LocalImageMusicVideoRenderer(config.resolved_hands_out_dir / "image_music_video").render(
        audio,
        images,
        prompt,
        aspect="1:1",
        max_duration_seconds=45,
        consent=True,
    )
    return {
        "reply": "Created a 45-second image music video preview with the original voice and music.",
        "files": [_file_payload(project.output_path), _file_payload(project.manifest_path)],
        "media_status": "image_music_video_rendered",
    }


def _video_subject_from_message(message: str) -> str:
    cleaned = re.sub(
        r"\b(can you|could you|please|gima|make|create|generate|render|produce|build|a|an|the|video|movie|cinematic|for me)\b",
        " ",
        message,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "short cinematic scene"


def _text_preview(path: Path, limit: int, tail: bool = False) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= limit:
        return text
    if tail:
        return f"[earlier output omitted]\n{text[-limit:]}"
    return f"{text[:limit]}\n[remaining output omitted]"


def _diff_stats(path: Path) -> dict[str, int]:
    text = _text_preview(path, 2_000_000)
    additions = sum(1 for line in text.splitlines() if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in text.splitlines() if line.startswith("-") and not line.startswith("---"))
    files = sum(1 for line in text.splitlines() if line.startswith("+++ b/"))
    return {"files": files, "additions": additions, "deletions": deletions}


def _safe_download_path(config: Config, raw_path: str) -> Path:
    if not raw_path:
        raise FileNotFoundError("No file path was provided")
    requested = Path(raw_path).expanduser()
    if not requested.is_absolute():
        requested = config.resolved_workspace / requested
    requested = requested.resolve()
    allowed_roots = [
        config.resolved_downloads_dir,
        config.resolved_hands_dir,
        config.resolved_hands_in_dir,
        config.resolved_hands_out_dir,
        config.resolved_stomach_dir,
        config.resolved_continuous_dir,
        config.resolved_data_dir / "brain",
        config.resolved_data_dir / "web_uploads",
        config.resolved_data_dir / "self_updates",
    ]
    if not any(_is_relative_to(requested, root) for root in allowed_roots):
        raise PermissionError("Download is limited to Gima storage folders")
    if not requested.exists() or not requested.is_file():
        raise FileNotFoundError(str(requested))
    return requested


def _reveal_file_location(path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", "-R", str(path)]
    elif os.name == "nt":
        command = ["explorer", f"/select,{path}"]
    else:
        opener = shutil.which("xdg-open")
        if not opener:
            raise RuntimeError("No desktop file manager opener is available")
        command = [opener, str(path.parent)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "desktop file manager could not open the location"
        raise RuntimeError(detail)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _refresh_brain_csv(config: Config) -> Path:
    return rebuild_brain_csv(
        config.resolved_data_dir,
        [config.resolved_data_dir / "brain", config.resolved_hands_dir, config.resolved_downloads_dir],
    )


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(name).name).strip(" .")
    return cleaned or f"upload_{int(time.time())}"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}_{uuid.uuid4().hex[:8]}{suffix}")


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _open_browser(url: str) -> None:
    try:
        import subprocess

        subprocess.Popen(["open", url])
    except Exception:
        pass


def serve_in_thread(
    config: Config,
    agent: Agent,
    brain: BrainServer,
    host: str = "127.0.0.1",
    port: int = 0,
) -> GimaWebServer:
    web = create_web_server(config, agent, brain, host, port)
    thread = threading.Thread(target=web.serve_forever, daemon=True)
    thread.start()
    return web
