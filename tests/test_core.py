import tempfile
import unittest
from pathlib import Path
from core import Game, Recorder
from layout import is_free


class SimulationTests(unittest.TestCase):
    def test_spawn_and_layout_avoid_label_overlaps(self):
        g = Game()
        for _ in range(80):
            g.add_node()
        for i,node in enumerate(g.state['nodes']):
            self.assertTrue(is_free(node['x'],node['y'],g.state['nodes'][:i]))
        for i in range(5):
            g.build(i,(i+1)%5)
        edges = [dict(e) for e in g.state['edges']]
        queues = [list(n['queue']) for n in g.state['nodes']]
        random_state = g.rng.getstate()
        g.relayout()
        for i,node in enumerate(g.state['nodes']):
            self.assertTrue(is_free(node['x'],node['y'],g.state['nodes'][:i]))
        self.assertEqual(g.state['edges'],edges)
        self.assertEqual([n['queue'] for n in g.state['nodes']],queues)
        self.assertEqual(g.rng.getstate(),random_state)

    def test_capacity_growth_and_build_limit(self):
        g = Game()
        self.assertEqual(g.capacity, 5)
        for _ in range(5):
            self.assertTrue(g.build(0,1))
        self.assertFalse(g.build(0,1))
        for expected in [6,7,9,10,11,13]:
            g.add_node('circle', (100,100))
            self.assertEqual(g.capacity, expected)
        self.assertTrue(g.build(0,1))

    def test_save_resume_determinism(self):
        a = Game(123)
        for i in range(5):
            a.build(i,(i+1)%5)
        for _ in range(15):
            a.step()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'save.json'
            a.save(path)
            b = Game.load(path)
            for _ in range(50):
                a.step()
                b.step()
                self.assertEqual(a.snapshot(),b.snapshot())

    def test_one_hop_and_parallel_capacity(self):
        g = Game()
        g.build(0,1)
        g.build(0,1)
        g.build(1,2)
        for i in range(3):
            cid = str(i+100)
            g.state['cargo'][cid] = dict(id=cid,origin=0,target='square',reward=2,created=0,arrived=0,location=0,delivered=None)
            g.state['nodes'][0]['queue'].append(cid)
        moves = g.step()
        custom = [m for m in moves if int(m['cargo'])>=100]
        self.assertEqual(len(custom),2)
        self.assertTrue(all(m['source']==0 and m['target']==1 for m in custom))
        self.assertEqual(g.state['nodes'][1]['queue'],['100','101'])

    def test_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            g = Game()
            r = Recorder(Path(folder)/'data.sqlite',g)
            g.step()
            r.flush(g)
            kinds = [row[0] for row in r.db.execute('SELECT kind FROM events')]
            self.assertIn('tick_metrics',kinds)
            self.assertIn('cargo_created',kinds)
            r.export(Path(folder)/'events.csv')
            self.assertTrue((Path(folder)/'events.csv').exists())
            r.db.close()


if __name__ == '__main__':
    unittest.main()
