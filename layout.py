"""Display placement, including room for node labels and cargo summaries."""
import math
import networkx as nx

GAP_X = 156
GAP_Y = 180


def is_free(x, y, nodes):
    return all(abs(n['x']-x) >= GAP_X or abs(n['y']-y) >= GAP_Y for n in nodes)


def spawn_position(nodes, rng):
    # Grow the sampling area as the map fills; never accept an overlapping fallback.
    xs = [n['x'] for n in nodes] or [450]
    ys = [n['y'] for n in nodes] or [350]
    for margin in (0, 180, 360):
        for _ in range(80):
            x = rng.randint(int(min(90, min(xs))-margin), int(max(810,max(xs))+margin))
            y = rng.randint(int(min(90, min(ys))-margin), int(max(610,max(ys))+margin))
            if is_free(x,y,nodes):
                return x,y
    return max(xs)+GAP_X, sum(ys)/len(ys)


def arrange(nodes, edges):
    graph = nx.Graph()
    graph.add_nodes_from(n['id'] for n in nodes)
    graph.add_edges_from((e['source'],e['target']) for e in edges)
    # Small deterministic force solver, without adding a NumPy dependency.
    size = max(250, math.sqrt(len(nodes))*130)
    positions = {n['id']: [size*math.cos(math.tau*i/len(nodes)),
                           size*math.sin(math.tau*i/len(nodes))]
                 for i,n in enumerate(nodes)}
    for iteration in range(120):
        forces = {key: [-x*.6,-y*.6] for key,(x,y) in positions.items()}
        ids = list(positions)
        for i,a in enumerate(ids):
            for b in ids[i+1:]:
                dx,dy = positions[a][0]-positions[b][0],positions[a][1]-positions[b][1]
                distance = max(1.,math.hypot(dx,dy))
                strength = 200**2/distance
                for axis,value in enumerate((dx,dy)):
                    force = value/distance*strength
                    forces[a][axis] += force
                    forces[b][axis] -= force
        for a,b in graph.edges:
            dx,dy = positions[b][0]-positions[a][0],positions[b][1]-positions[a][1]
            distance = max(1.,math.hypot(dx,dy))
            for axis,value in enumerate((dx,dy)):
                force = value*distance/400
                forces[a][axis] += force
                forces[b][axis] -= force
        for key,force in forces.items():
            length = max(1.,math.hypot(*force))
            step = min(length,25*(1-iteration/120)+.5)
            positions[key][0] += force[0]/length*step
            positions[key][1] += force[1]/length*step
    positions = {key: (x+450,y+350) for key,(x,y) in positions.items()}
    placed = []
    for node in nodes:
        x,y = map(float,positions[node['id']])
        # Find the nearest free position around the force-directed result.
        candidates = [(x,y)]
        radius = 0
        while True:
            free = next(((a,b) for a,b in candidates if is_free(a,b,placed)),None)
            if free is not None:
                break
            radius += 1
            candidates = [(x+dx*GAP_X,y+dy*GAP_Y)
                          for dx in range(-radius,radius+1)
                          for dy in range(-radius,radius+1)
                          if max(abs(dx),abs(dy))==radius]
            candidates.sort(key=lambda p:(p[0]-x)**2+(p[1]-y)**2)
        placed.append(dict(id=node['id'],x=free[0],y=free[1]))
    return placed
