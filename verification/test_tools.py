# ==============================================================================
# Program: test_tools.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Python unit tests for the helper tools: evolution rules, NBT round trips, glTF
#          accessor/transform maths and the installer's refusal to overwrite an unmanaged
#          instance. Needs Pillow (import_assets imports it). Run from the repo root.
# ==============================================================================

# Unit tests for the Python helper tools (not for the Java mod or the data pack; those are checked in the real
# game by run_checks.py and MinecraftChecks.java). They are fast and offline: nothing here needs Minecraft,
# Steam or the network. Run from the repository root:
#     python3 -m unittest discover -s verification -p 'test_*.py'
# (scripts/update.sh runs the same command inside the project's virtual environment, which has Pillow.)
# Requirement: Pillow must be importable because import_assets.py imports PIL at load time.
import gzip
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

# The tools are plain scripts in tools/, not an installed package, so put that folder on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import nbt
import import_assets
import install_prism

import evolution


# One test class for all helpers; each test builds its own data, so tests are independent and order does not matter.
class ToolChecks(unittest.TestCase):
    # Behaviour: a population that meets every gate minimum must stay that way for several consecutive steps
    # before advancing (two steps are not enough, the third advances to stage 1), and a drop in cooperation
    # resets the counter without losing the stage. Why it matters: it is the rule that stops a single lucky step from
    # producing a civilisation.
    def test_evolution_requires_stable_cooperation(self):
        p=evolution.Population(maturity=1,habitat=1,cooperation=1,knowledge=1)
        for _ in range(2):p=evolution.advance(p,game_days=1)
        self.assertEqual(p.stage,0)
        p=evolution.advance(p,game_days=1)
        self.assertEqual(p.stage,1)
        p=evolution.advance(p,game_days=1,shared_help=-.7)
        self.assertEqual(p.stable_steps,0)
        self.assertEqual(p.stage,1)

    # Behaviour: even with 10,000 game days elapsed, only one day's worth of growth is applied (maturity 0.04) and no
    # stage is gained. Why it matters: a player returning after a long absence must not find several stages skipped.
    def test_evolution_cannot_skip_stages_while_away(self):
        p=evolution.advance(evolution.Population(),game_days=10000)
        self.assertEqual(p.stage,0)
        self.assertAlmostEqual(p.maturity,.04)

    # Behaviour: every NBT type (byte through long arrays, strings, lists, nested compounds) survives a write then a
    # typed read unchanged. Why it matters: install_prism.py rewrites a real level.dat this way; losing a type (for
    # example turning a long into an int) would corrupt the save.
    def test_typed_nbt_preserves_save_values(self):
        original = {'byte': (1,-1),'short': (2,32767),'int': (3,5023),'long': (4,2**40),
                    'float': (5,1.5),'double': (6,-2.5),'bytes': (7,[0,127,255]),
                    'name': (8,'Spain · Starforge'),'list': (9,(8,['vanilla','file/Spain'])),
                    'compound': (10,{'flag': (1,1)}),'ints': (11,[-1,2]),'longs': (12,[2**40])}
        data = gzip.compress(b'\x0a\x00\x00'+nbt.payload(10,original))
        self.assertEqual(nbt.read(data,typed=True),original)

    # Behaviour: structure() output keeps the size, writes palette entries with the minecraft: prefix and stores
    # block positions with their palette indexes. Why it matters: wrong indexes would place the wrong blocks in game.
    def test_structure_uses_current_palette_and_preserves_positions(self):
        data = nbt.read(nbt.structure([3,4,5],{(0,0,0):0,(2,3,4):1},['oak_planks','stone']))
        self.assertEqual(data['size'],[3,4,5])
        self.assertEqual(data['palette'][1],{'id':'minecraft:stone'})
        self.assertEqual(data['blocks'][1],{'pos':[2,3,4],'state':1})

    # Scenario: a 4-byte padding prefix, then two 3-float positions each followed by one unused float (stride 16 bytes),
    # the layout of interleaved glTF vertex data. Expect only the real XYZ values (1,2,3) and (4,5,6), not the 99
    # filler. Why it matters: ignoring the stride would read garbage coordinates and distort the converted model.
    def test_interleaved_glb_accessor_obeys_stride_and_offsets(self):
        binary = b'PAD!'+struct.pack('<8f',1,2,3,99,4,5,6,99)
        doc = {'bufferViews':[{'byteOffset':4,'byteStride':16}], 'accessors':[{'bufferView':0,'componentType':5126,'type':'VEC3','count':2}]}
        self.assertEqual(import_assets.accessor(doc,binary,0),[(1,2,3),(4,5,6)])

    # Scenario: point (1,0,0), scaled by 2, rotated 90 degrees about the Y axis (quaternion y = w = sqrt(0.5)),
    # then moved by (3,4,5). Rotating (2,0,0) about Y gives (0,0,-2), and the translation makes (3,4,3). Why it
    # matters: node transforms place every part of a model; a sign error would flip or misplace parts.
    def test_model_transform_handles_rotation_scale_and_translation(self):
        import math
        result = import_assets.node_transform((1,0,0),{'scale':[2,2,2],'rotation':[0,math.sqrt(.5),0,math.sqrt(.5)],'translation':[3,4,5]})
        for actual, expected in zip(result,(3,4,3)): self.assertAlmostEqual(actual,expected)

    # Scenario: a header that announces 200 bytes but a file of only 12. Expect ValueError, not a crash or a
    # silent partial model. Why it matters: interrupted copies of model files are a realistic failure.
    def test_truncated_glb_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'invalid.glb'
            path.write_bytes(struct.pack('<4sII',b'glTF',2,200))
            with self.assertRaises(ValueError): import_assets.load_glb(path)

    # Scenario: a Prism instance folder named Spain exists without this tool's marker file and contains a
    # file the user cares about. Expect install() to raise ValueError and leave that folder byte-for-byte
    # unchanged. ROOT is patched to a temporary project whose test report says "passed", so only the
    # ownership guard can stop the install. Why it matters: the installer must never overwrite someone's own game instance.
    def test_installer_rejects_unmanaged_instance_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'project'
            report = root/'verification/output/results.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps({'passed':True}))
            prism = Path(folder)/'prism'
            existing = prism/'instances/Spain'
            existing.mkdir(parents=True)
            save = existing/'important-save.txt'
            save.write_text('keep me')
            with patch.object(install_prism,'ROOT',root):
                with self.assertRaises(ValueError): install_prism.install(prism)
            self.assertEqual(save.read_text(),'keep me')
            self.assertEqual(list(existing.iterdir()),[save])


if __name__ == '__main__': unittest.main()
