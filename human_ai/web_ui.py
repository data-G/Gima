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
from .ai_task_map import AITaskMapStore
from .artifacts import ChatArtifactEngine, _extract_weather_location
from .brain import BrainServer
from .brain_index import rebuild_brain_csv
from .capabilities import CapabilityStore
from .config import Config
from .memory import Record
from .model_levels import ModelLevelManager
from .quota import FreeQuotaTracker
from .secrets import save_teacher_secret, teacher_secret_status
from .self_update import SelfUpdateManager
from .services import AdvancedVideoSongRenderer, LipSyncPlanner, LocalImageMusicVideoRenderer, LocalMusicVideoDirector, LocalMusicVideoRenderer, LocalSongSketcher, NeuralLipSyncRenderer, OpenSourceVideoApiRenderer, SandboxedCodeRunner
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
          <p class="subtitle">soft gray local AI workspace</p>
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
          <select class="tool-select" id="apiProvider">
            <option value="openai">ChatGPT / OpenAI</option>
            <option value="gemini">Gemini</option>
            <option value="anthropic">Claude / Anthropic</option>
            <option value="xai">Grok / xAI</option>
            <option value="deepseek">DeepSeek</option>
            <option value="openrouter">OpenRouter</option>
          </select>
          <input class="tool-input" id="apiKey" type="password" placeholder="Paste API key">
          <button class="tool-button" id="saveApiBtn">Save API Binding</button>
          <button class="mini-button" id="multiMindBtn" type="button">Ask All Linked Minds</button>
        </div>
        <div class="tool-output" id="bindingOutput"></div>
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
          <h1>Chat With Gima</h1>
          <p class="subtitle">Local web UI. Conversations save to brain, conversation CSV, and continuous work logs.</p>
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
        <h2 style="font-size: 14px;">Deployments</h2>
        <div class="results" id="deploymentList">checking...</div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Agents & Vibe Code</h2>
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
    const drawerBackdrop = document.getElementById('drawerBackdrop');
    const leftDrawerBtn = document.getElementById('leftDrawerBtn');
    const rightDrawerBtn = document.getElementById('rightDrawerBtn');
    const addSheetBackdrop = document.getElementById('addSheetBackdrop');
    const addSheetClose = document.getElementById('addSheetClose');
    const enterSendSetting = document.getElementById('enterSendSetting');
    let pendingAttachments = [];
    let deferredInstallPrompt = null;

    function setChatStatus(text) {
      chatStatus.textContent = text;
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
        const label = binding.available === 'yes' ? `linked (${escapeHtml(binding.masked)})` : 'not linked';
        return `<div class="status-row"><span>${escapeHtml(binding.provider)}</span><span class="pill">${label}</span></div>`;
      }).join('');
      document.getElementById('quotaStatus').innerHTML =
        `<div class="status-row"><span>Free quota mode</span><span class="pill">${quotaData.free_quota_mode ? 'on' : 'off'}</span></div>` +
        (quotaData.quotas || []).map(row =>
          `<div class="status-row"><span>${escapeHtml(row.provider)}</span><span class="pill">${escapeHtml(row.remaining)}/${escapeHtml(row.limit)} left</span></div>`
        ).join('');
    }

    async function refreshDashboards() {
      const [capabilities, doctor, codexMode, aiTaskMap, deployments, agents, outputs, folders, apps, lipBackend] = await Promise.all([
        fetch('/api/capabilities').then(res => res.json()),
        fetch('/api/doctor').then(res => res.json()),
        fetch('/api/codex-mode').then(res => res.json()),
        fetch('/api/ai-task-map').then(res => res.json()),
        fetch('/api/deployments').then(res => res.json()),
        fetch('/api/agents').then(res => res.json()),
        fetch('/api/outputs').then(res => res.json()),
        fetch('/api/folders').then(res => res.json()),
        fetch('/api/apps').then(res => res.json()),
        fetch('/api/media/lip-sync-status').then(res => res.json()),
      ]);
      const lipStatus = document.getElementById('lipBackendStatus');
      if (lipStatus) {
        lipStatus.textContent = lipBackend.ready
          ? `SadTalker ready (${lipBackend.checkpoint_count} checkpoint)`
          : `Neural backend not ready: ${(lipBackend.missing || []).join(', ')}. Expected at ${lipBackend.backend_dir || ''}`;
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
        (doctor.own_model_plan
          ? `<div class="file-chip"><b>Own model path</b> <span class="pill">${escapeHtml(doctor.own_model_plan.status)}</span><br>${escapeHtml(doctor.own_model_plan.realistic_strategy)}<br><span class="hint">${escapeHtml(doctor.own_model_plan.why_not_from_scratch)}</span></div>` +
            ((doctor.own_model_plan.stages || []).map(item =>
              `<div class="file-chip"><b>${escapeHtml(item.stage)}</b> <span class="pill">${escapeHtml(item.status)}</span><br>${escapeHtml(item.action)}</div>`
            ).join('') || '')
          : '') +
        ((doctor.next_actions || []).length
          ? `<div class="file-chip"><b>Next fixes</b><br>${(doctor.next_actions || []).map(action => `- ${escapeHtml(action)}`).join('<br>')}</div>`
          : '');
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
          data = await postChat({message: finalText}, 45000);
        } catch (error) {
          if (error.name !== 'AbortError') throw error;
          pending.textContent = 'Gima took more than 45 seconds. Retrying with small AI...';
          setChatStatus('retrying with small AI...');
          data = await postChat({message: finalText, prefer_small_model: true}, 30000);
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
        const reason = error.name === 'AbortError' ? 'Gima did not answer within 45 seconds.' : String(error);
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
    message.addEventListener('input', autoGrowMessage);
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
    document.getElementById('songBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('songPrompt').value.trim();
      const duration = Number(document.getElementById('songDuration').value || 12);
      if (!prompt) return;
      await runWithProgress('songBtn', 'songOutput', 'Generating song sketch', Math.max(8, duration), () =>
        apiPost('/api/media/song-local', { prompt, duration_seconds: duration })
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
            elif parsed.path == "/api/bindings":
                self._send_json({"bindings": teacher_secret_status(config.resolved_workspace)})
            elif parsed.path == "/api/free-quotas":
                self._send_json(_free_quota_payload(config))
            elif parsed.path == "/api/capabilities":
                self._send_json({"capabilities": _capability_payload(config, agent, brain)})
            elif parsed.path == "/api/doctor":
                self._send_json(_doctor_payload(config, brain))
            elif parsed.path == "/api/codex-mode":
                self._send_json({"capabilities": _codex_mode_payload(config, brain)})
            elif parsed.path == "/api/ai-task-map":
                self._send_json(_ai_task_map_payload(config))
            elif parsed.path == "/api/deployments":
                self._send_json({"deployments": _deployment_payload(config, brain)})
            elif parsed.path == "/api/agents":
                self._send_json({"agents": _agent_payload(config)})
            elif parsed.path == "/api/outputs":
                self._send_json({"outputs": _output_payload(config)})
            elif parsed.path == "/api/folders":
                self._send_json({"folders": _human_folder_payload(config)})
            elif parsed.path == "/api/apps":
                self._send_json({"apps": _app_plan_payload(config)})
            elif parsed.path == "/api/media/lip-sync-status":
                self._send_json(_lip_sync_renderer(config).status())
            elif parsed.path == "/api/media/open-video-api-status":
                params = urllib.parse.parse_qs(parsed.query)
                base_url = params.get("base_url", [os.environ.get("GIMA_COMFYUI_URL", "http://127.0.0.1:8188")])[0]
                self._send_json(OpenSourceVideoApiRenderer(_hands_out_dir(config) / "open_video_api", base_url=base_url).status())
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
            if parsed.path == "/api/minds/ask":
                self._handle_minds_ask()
                return
            if parsed.path == "/api/media/song-local":
                self._handle_song_local()
                return
            if parsed.path == "/api/media/music-video-local":
                self._handle_music_video_local()
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
                if _should_use_cloud_chat(config, message):
                    cloud_answer: str | None = None
                    cloud_provider = ""
                    cloud_errors: list[str] = []
                    for provider in _cloud_chat_providers(config):
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
                reply = _with_temporary_model_level(
                    config,
                    "fast" if prefer_small_model else None,
                    lambda: agent.chat(
                        message,
                        model_timeout_seconds=max(15, min(75, config.model.timeout_seconds)),
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

    return [
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
    if not _cloud_chat_providers(config):
        return False
    normalized = " ".join(message.casefold().split())
    if any(term in normalized for term in {"use local", "local only", "offline only", "use brain", "brain:"}):
        return False
    return True


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
        "You are helping inside Gima, a local AI workspace. Answer like ChatGPT: useful, direct, accurate, and concise. "
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


def _chat_media_answer(config: Config, message: str) -> dict[str, Any] | None:
    normalized = " ".join(message.casefold().split())
    video_terms = {"video", "movie", "cinematic", "stage", "performing", "performance", "singing", "song"}
    media_terms = {"image", "song", "music", "movie", "cinematic", "lip", "lip sync", "lip-sync", "stage", "performing", "singing"}
    video_intent = any(term in normalized for term in video_terms) and any(term in normalized for term in media_terms)
    if not video_intent:
        return None
    attached: list[Path] = []
    for line in message.splitlines():
        marker = line.find(": /")
        if marker < 0:
            continue
        path = Path(line[marker + 2 :].strip()).expanduser().resolve()
        if path.exists() and path.is_file():
            attached.append(path)
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    audio_suffixes = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
    images = [path for path in attached if path.suffix.casefold() in image_suffixes]
    audio = next((path for path in attached if path.suffix.casefold() in audio_suffixes), None)
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
