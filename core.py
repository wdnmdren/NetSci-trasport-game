"""Deterministic simulation; deliberately independent of Qt."""
import json
import random
import sqlite3
from pathlib import Path
import networkx as nx
from layout import is_free, spawn_position, arrange

SHAPES = ['circle', 'triangle', 'square', 'star', 'diamond']
WEIGHTS = [40, 30, 20, 7, 3]
REWARDS = dict(zip(SHAPES, [1, 1, 2, 5, 10]))


class Game:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.state = dict(version=1, seed=seed, tick=0, score=0, ended=False,
                          nodes=[], edges=[], cargo={}, next_cargo=1,
                          threshold=12, overload_duration=12, initial_nodes=5)
        self.events = []
        self.moves = []
        for shape, pos in zip(SHAPES[:3] + ['circle', 'triangle'],
                              [(180, 180), (480, 130), (730, 300), (550, 540), (220, 500)]):
            self.add_node(shape, pos)

    def event(self, kind, **data):
        self.events.append(dict(tick=self.state['tick'], kind=kind, **data))

    @property
    def capacity(self):
        s = self.state
        return len(s['nodes']) + (len(s['nodes']) - s['initial_nodes']) // 3

    def add_node(self, shape=None, pos=None):
        if shape is None:
            shape = self.rng.choices(SHAPES, WEIGHTS)[0]
        if pos is None or not is_free(*pos, self.state['nodes']):
            pos = spawn_position(self.state['nodes'], self.rng)
        node = dict(id=len(self.state['nodes']), shape=shape, x=pos[0], y=pos[1], queue=[], overload=0)
        self.state['nodes'].append(node)
        self.event('node_created', node=dict(node))

    def relayout(self):
        positions = arrange(self.state['nodes'],self.state['edges'])
        for node, pos in zip(self.state['nodes'],positions):
            node.update(x=pos['x'],y=pos['y'])
        self.event('layout_changed', positions=positions)

    def build(self, source, target):
        if self.state['ended'] or source == target or len(self.state['edges']) >= self.capacity:
            return False
        edge = dict(id=len(self.state['edges']), source=source, target=target)
        self.state['edges'].append(edge)
        self.event('edge_built', **edge)
        return True

    def step(self):
        s = self.state
        if s['ended']:
            return []
        s['tick'] += 1
        self.moves = []
        if s['tick'] % 25 == 0:
            self.add_node()
        nodes = s['nodes']
        for _ in range(1 + s['tick'] // 60):
            origin = self.rng.choice(nodes)
            targets = [x for x in SHAPES if x != origin['shape'] and any(n['shape'] == x for n in nodes)]
            target = self.rng.choices(targets, [WEIGHTS[SHAPES.index(x)] for x in targets])[0]
            cid = str(s['next_cargo'])
            s['next_cargo'] += 1
            cargo = dict(id=cid, origin=origin['id'], target=target, reward=REWARDS[target],
                         created=s['tick'], arrived=s['tick'], location=origin['id'], delivered=None)
            s['cargo'][cid] = cargo
            origin['queue'].append(cid)
            self.event('cargo_created', cargo=dict(cargo))
        graph = nx.DiGraph()
        graph.add_nodes_from(n['id'] for n in nodes)
        graph.add_edges_from((e['source'], e['target']) for e in s['edges'])
        routes = {}
        for node in nodes:
            paths = nx.single_source_shortest_path(graph, node['id'])
            for shape in SHAPES:
                candidates = [p for dest, p in paths.items() if nodes[dest]['shape'] == shape and len(p) > 1]
                if candidates:
                    routes[node['id'], shape] = min(candidates, key=lambda p: (len(p), p))[1]
        available = {}
        for edge in s['edges']:
            available.setdefault((edge['source'], edge['target']), []).append(edge['id'])
        # Schedule against old queues; arrivals are applied only after all nodes are scanned.
        for node in nodes:
            remaining = []
            for cid in node['queue']:
                cargo = s['cargo'][cid]
                target = routes.get((node['id'], cargo['target']))
                lanes = available.get((node['id'], target), [])
                if lanes:
                    move = dict(cargo=cid, source=node['id'], target=target, edge=lanes.pop(0), shape=cargo['target'])
                    self.moves.append(move)
                else:
                    remaining.append(cid)
            node['queue'] = remaining
        for move in self.moves:
            cargo = s['cargo'][move['cargo']]
            dest = nodes[move['target']]
            cargo['location'] = dest['id']
            cargo['arrived'] = s['tick']
            self.event('cargo_moved', **move)
            if dest['shape'] == cargo['target']:
                cargo['delivered'] = s['tick']
                s['score'] += cargo['reward']
                self.event('cargo_delivered', cargo=cargo['id'], reward=cargo['reward'], delay=s['tick']-cargo['created'])
            else:
                dest['queue'].append(cargo['id'])
        for node in nodes:
            old = node['overload']
            node['overload'] = old + 1 if len(node['queue']) > s['threshold'] else 0
            if bool(old) != bool(node['overload']):
                self.event('overload_started' if node['overload'] else 'overload_reset', node=node['id'])
            if node['overload'] >= s['overload_duration']:
                s['ended'] = True
                self.event('game_over', node=node['id'], score=s['score'])
        self.event('tick_metrics', queues={str(n['id']):len(n['queue']) for n in nodes},
                   overload={str(n['id']):n['overload'] for n in nodes},
                   edge_usage={str(e['id']):int(any(m['edge']==e['id'] for m in self.moves)) for e in s['edges']},
                   routes={f'{a}:{b}':c for (a,b),c in routes.items()}, score=s['score'])
        return self.moves

    def snapshot(self):
        return dict(state=self.state, random_state=self.rng.getstate(),
                    source_session=getattr(self, 'source_session', None))

    def save(self, path):
        path = Path(path)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.snapshot(), ensure_ascii=False), encoding='utf-8')
        temporary.replace(path)

    @classmethod
    def load(cls, path):
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        if payload['state']['version'] != 1:
            raise ValueError('Unsupported save version')
        game = cls(payload['state']['seed'])
        game.state = payload['state']
        def tuples(x):
            return tuple(tuples(v) for v in x) if isinstance(x, list) else x
        game.rng.setstate(tuples(payload['random_state']))
        game.source_session = payload.get('source_session')
        game.events = []
        return game


class Recorder:
    def __init__(self, path, game, parent=None):
        import uuid
        self.session = uuid.uuid4().hex
        parent = parent or getattr(game, 'source_session', None)
        game.source_session = self.session
        self.db = sqlite3.connect(path)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS sessions
            (id TEXT PRIMARY KEY, parent TEXT, seed INTEGER, initial_state TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS events
            (id INTEGER PRIMARY KEY, session TEXT, tick INTEGER, kind TEXT, data TEXT);
            CREATE TABLE IF NOT EXISTS snapshots
            (session TEXT, tick INTEGER, data TEXT);''')
        self.db.execute('INSERT INTO sessions(id,parent,seed,initial_state) VALUES(?,?,?,?)',
                        (self.session, parent, game.state['seed'], json.dumps(game.snapshot())))
        self.flush(game)

    def flush(self, game):
        with self.db:
            self.db.executemany('INSERT INTO events(session,tick,kind,data) VALUES(?,?,?,?)',
                                [(self.session,e['tick'],e['kind'],json.dumps(e)) for e in game.events])
            if game.state['tick'] % 20 == 0:
                self.db.execute('INSERT INTO snapshots VALUES(?,?,?)',
                                (self.session, game.state['tick'], json.dumps(game.snapshot())))
        game.events.clear()

    def export(self, path):
        import csv
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['event_id','session','tick','kind','data_json'])
            writer.writerows(self.db.execute('SELECT * FROM events WHERE session=? ORDER BY id', (self.session,)))
