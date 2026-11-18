# Program: Spain - evolution.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Small, deterministic model of how a creature population moves through evolution stages over game days (a prototype not yet connected to the game).
"""Deterministic population progression prototype; not yet attached to Minecraft ticks."""
# Imports: dataclass for a simple data holder, json and Path to read the settings file.
from dataclasses import dataclass
import json
from pathlib import Path
# Load the stage requirements (gates) from content/evolution.json.
CONFIG=json.loads((Path(__file__).resolve().parents[1]/'content/evolution.json').read_text())

# A Population is an immutable record of the population's current progress.
@dataclass(frozen=True)
class Population:
    """Progress of one population: stage, maturity, habitat, cooperation, knowledge and stable_steps."""
    # stage = which stage; the other fields are values from 0 to 1 except stable_steps, which counts steps in a row that met the gate.
    stage:int=0
    maturity:float=0
    habitat:float=.5
    cooperation:float=.3
    knowledge:float=0
    stable_steps:int=0

def advance(population:Population, *, game_days:float, habitat_help:float=0, shared_help:float=0, discovery:float=0)->Population:
    """One bounded simulation step. Stage gates reward survival, learning and cooperation."""
    if game_days<0:raise ValueError('Game days cannot be negative')
    # Cap each step at one game day.
    days=min(game_days,1) # Returning after a long absence cannot skip multiple civilizations.
    # clamp keeps a value between 0 and 1.
    clamp=lambda n:max(0,min(1,n))
    # Update the four progress values.
    values=dict(maturity=clamp(population.maturity+.04*days),habitat=clamp(population.habitat+habitat_help),cooperation=clamp(population.cooperation+shared_help),knowledge=clamp(population.knowledge+discovery))
    # Stage gates: all values must meet the gate for enough steps in a row to advance.
    stage=population.stage;stable=0
    # Only check a gate if there is a next stage.
    if stage<len(CONFIG['gates']):
        gate=CONFIG['gates'][stage]
        if all(values[k]>=gate[k] for k in values):stable=population.stable_steps+1
        if stable>=gate['stable_steps']:stage+=1;stable=0
    # Return a new Population (the old one is never changed).
    return Population(stage=stage,stable_steps=stable,**values)
