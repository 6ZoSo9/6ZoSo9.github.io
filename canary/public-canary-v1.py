#!/usr/bin/env python3
"""Compatibility entrypoint for the superseded V1 public canary."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("public-canary-v2.py")), run_name="__main__")
