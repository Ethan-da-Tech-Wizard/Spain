"""Deterministic population progression prototype; not yet attached to Minecraft ticks."""
from dataclasses import dataclass
import json
from pathlib import Path
CONFIG=json.loads((Path(__file__).resolve().parents[1]/'content/evolution.json').read_text())

@dataclass(frozen=True)
class Population:
    stage:int=0
    maturity:float=0
    habitat:float=.5
    cooperation:float=.3
    knowledge:float=0
    stable_steps:int=0

def advance(population:Population, *, game_days:float, habitat_help:float=0, shared_help:float=0, discovery:float=0)->Population:
    """One bounded simulation step. Stage gates reward survival, learning and cooperation."""
    if game_days<0:raise ValueError('Game days cannot be negative')
    days=min(game_days,1) # Returning after a long absence cannot skip multiple civilizations.
    clamp=lambda n:max(0,min(1,n))
    values=dict(maturity=clamp(population.maturity+.04*days),habitat=clamp(population.habitat+habitat_help),cooperation=clamp(population.cooperation+shared_help),knowledge=clamp(population.knowledge+discovery))
    stage=population.stage;stable=0
    if stage<len(CONFIG['gates']):
        gate=CONFIG['gates'][stage]
        if all(values[k]>=gate[k] for k in values):stable=population.stable_steps+1
        if stable>=gate['stable_steps']:stage+=1;stable=0
    return Population(stage=stage,stable_steps=stable,**values)
