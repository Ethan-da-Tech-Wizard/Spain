#!/usr/bin/env bash

# ==============================================================================
# Program: build.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Builds the two outputs in order: the data pack (tools/build_pack.py, writes dist/Spain
#          and dist/Spain.zip) and the mod jar (tools/build_mod.py, writes dist/spain-flight-0.1.0.jar).
#          No Gradle is involved. Extra arguments are passed to build_pack.py.
# ==============================================================================

# Used for a quick rebuild without installing or testing. Outputs: dist/Spain, dist/Spain.zip, dist/spain-flight-0.1.0.jar.
# Strict mode: stop on errors, unset variables and failed pipe stages.
set -euo pipefail

# Run from the repository root so the relative tool paths work from any starting directory.
cd "$(dirname "$0")/.."

# Stage 1: the data pack. "$@" passes through options such as --minecraft-jar PATH.
python3 tools/build_pack.py "$@"

# Stage 2: the Java mod. Needs the JDK from setup.sh and Minecraft's libraries from Prism.
python3 tools/build_mod.py
