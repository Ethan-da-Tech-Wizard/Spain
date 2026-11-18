#!/usr/bin/env bash

# ==============================================================================
# Program: build.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Mod compiler automation invoking Gradle to package the Fabric mod JAR.
# ==============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/build_pack.py "$@"
python3 tools/build_mod.py
