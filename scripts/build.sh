#!/usr/bin/env bash
# Program: Spain - build.sh
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Builds the Spain data pack and then the Fabric mod jar.
# Stop on any error, on unset variables, and on failures inside pipes.
set -euo pipefail
# Move to the project root (the folder above this script) so paths work from anywhere.
cd "$(dirname "$0")/.."
# Build the data pack; any extra arguments are passed along.
python3 tools/build_pack.py "$@"
# Compile the mod and package the jar.
python3 tools/build_mod.py
