# ==============================================================================
# Program: evolution.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Prototype rules for how a creature population advances through stages (creature,
#          tribe, city, space) from maturity, habitat, cooperation and knowledge values read
#          from content/evolution.json. Not yet connected to the game.
# ==============================================================================

"""Deterministic population progression prototype; not yet attached to Minecraft ticks."""

# Fit in the repo: a self-contained prototype of the "civilisation grows over time" idea in GAME_DESIGN.md. It is
# only exercised by verification/test_tools.py and is NOT connected to the game yet (the docstring says so). Its
# rules come from content/evolution.json: a list of `gates`, one per stage change, each with minimum values for
# maturity, habitat, cooperation and knowledge and a number of consecutive steps (`stable_steps`) the minimums must hold.
#
# Idea: a population only moves up a stage when it has stayed healthy for several steps in a row, not just once; a
# bad step (for example falling cooperation) resets the count. It is deterministic: the same inputs always give the same result.
from dataclasses import dataclass
import json
from pathlib import Path

# Loaded at import time; the file is small and read-only configuration (stages, gates, and a policy note about real-time idling).
CONFIG=json.loads((Path(__file__).resolve().parents[1]/'content/evolution.json').read_text())

# Frozen (immutable): advance() returns a new Population instead of changing one, so earlier states can be kept and compared in tests.
@dataclass(frozen=True)
# State of one creature population. Fields: stage (index into the stages list, 0 = creature), maturity, habitat,
# cooperation and knowledge (each clamped to 0..1) and stable_steps (consecutive steps meeting the current gate).
class Population:
    stage:int=0
    maturity:float=0
    habitat:float=.5
    cooperation:float=.3
    knowledge:float=0
    stable_steps:int=0

# See the docstring. Arguments after `*` must be named. habitat_help, shared_help and discovery are added to
# habitat, cooperation and knowledge for this step (they may be negative); maturity grows by 0.04 per game day.
def advance(population:Population, *, game_days:float, habitat_help:float=0, shared_help:float=0, discovery:float=0)->Population:
    """One bounded simulation step. Stage gates reward survival, learning and cooperation."""

    # Time cannot run backwards.
    if game_days<0:raise ValueError('Game days cannot be negative')

    # Cap one step at one game day: after a long absence the population gets one normal step, not ten thousand,
    # so it cannot jump through several stages. Verified by test_evolution_cannot_skip_stages_while_away.
    days=min(game_days,1) # Returning after a long absence cannot skip multiple civilizations.

    # Keep every value inside 0..1 so gate comparisons and later maths stay in range.
    clamp=lambda n:max(0,min(1,n))
    values=dict(maturity=clamp(population.maturity+.04*days),habitat=clamp(population.habitat+habitat_help),cooperation=clamp(population.cooperation+shared_help),knowledge=clamp(population.knowledge+discovery))
    stage=population.stage;stable=0

    # Only evaluate a gate if a next stage exists; the last stage has none.
    if stage<len(CONFIG['gates']):
        gate=CONFIG['gates'][stage]

        # Count a step as "stable" only when ALL four values meet the minimums; otherwise the counter restarts from 0.
        if all(values[k]>=gate[k] for k in values):stable=population.stable_steps+1

        # Enough consecutive stable steps: advance one stage and start counting again for the next gate.
        if stable>=gate['stable_steps']:stage+=1;stable=0
    return Population(stage=stage,stable_steps=stable,**values)
