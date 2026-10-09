import gzip
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import nbt
import import_assets
import install_prism

import evolution


class ToolChecks(unittest.TestCase):
    def test_evolution_requires_stable_cooperation(self):
        p=evolution.Population(maturity=1,habitat=1,cooperation=1,knowledge=1)
        for _ in range(2):p=evolution.advance(p,game_days=1)
        self.assertEqual(p.stage,0)
        p=evolution.advance(p,game_days=1)
        self.assertEqual(p.stage,1)
        p=evolution.advance(p,game_days=1,shared_help=-.7)
        self.assertEqual(p.stable_steps,0)
        self.assertEqual(p.stage,1)

    def test_evolution_cannot_skip_stages_while_away(self):
        p=evolution.advance(evolution.Population(),game_days=10000)
        self.assertEqual(p.stage,0)
        self.assertAlmostEqual(p.maturity,.04)

    def test_typed_nbt_preserves_save_values(self):
        original = {'byte': (1,-1),'short': (2,32767),'int': (3,5023),'long': (4,2**40),
                    'float': (5,1.5),'double': (6,-2.5),'bytes': (7,[0,127,255]),
                    'name': (8,'Spain · Starforge'),'list': (9,(8,['vanilla','file/Spain'])),
                    'compound': (10,{'flag': (1,1)}),'ints': (11,[-1,2]),'longs': (12,[2**40])}
        data = gzip.compress(b'\x0a\x00\x00'+nbt.payload(10,original))
        self.assertEqual(nbt.read(data,typed=True),original)

    def test_structure_uses_current_palette_and_preserves_positions(self):
        data = nbt.read(nbt.structure([3,4,5],{(0,0,0):0,(2,3,4):1},['oak_planks','stone']))
        self.assertEqual(data['size'],[3,4,5])
        self.assertEqual(data['palette'][1],{'id':'minecraft:stone'})
        self.assertEqual(data['blocks'][1],{'pos':[2,3,4],'state':1})

    def test_interleaved_glb_accessor_obeys_stride_and_offsets(self):
        binary = b'PAD!'+struct.pack('<8f',1,2,3,99,4,5,6,99)
        doc = {'bufferViews':[{'byteOffset':4,'byteStride':16}], 'accessors':[{'bufferView':0,'componentType':5126,'type':'VEC3','count':2}]}
        self.assertEqual(import_assets.accessor(doc,binary,0),[(1,2,3),(4,5,6)])

    def test_model_transform_handles_rotation_scale_and_translation(self):
        import math
        result = import_assets.node_transform((1,0,0),{'scale':[2,2,2],'rotation':[0,math.sqrt(.5),0,math.sqrt(.5)],'translation':[3,4,5]})
        for actual, expected in zip(result,(3,4,3)): self.assertAlmostEqual(actual,expected)

    def test_truncated_glb_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'invalid.glb'
            path.write_bytes(struct.pack('<4sII',b'glTF',2,200))
            with self.assertRaises(ValueError): import_assets.load_glb(path)

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
