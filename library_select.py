#!/usr/bin/env python3
"""Backward-compatible facade for the canonical :mod:`asm_protocol` SDK."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from asm_protocol.selection import *
