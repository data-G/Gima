#!/usr/bin/env python3
import sys
from pathlib import Path
workspace = Path('/Users/gimhangunarathne/Documents/Gima')
sys.path.insert(0, str(workspace))
from human_ai.gima import main
raise SystemExit(main(['web', '--host', '127.0.0.1', '--port', '8787']))
