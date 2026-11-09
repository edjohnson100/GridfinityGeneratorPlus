"""
Pure-Python helpers for irregular (non-rectangular) bins built from grid cells.
No adsk imports, so it can be tested outside Fusion.

A shape is a list of cells (cx, cy, w, d): integer column/row index (counted from the
front-left of the shape's bounding box) and the cell's width/depth in grid units (1.0 for a
full cell, 0.5 for a half-width / half-depth edge strip). Half strips only ever sit on the
trailing (right / back) edge, so a cell's lower-left corner is always (cx, cy) in grid units.
"""


def trace_outline(cells: list) -> list:
    """Returns the outline of the union of `cells` as one counter-clockwise rectilinear polygon
    [(x, y), ...] in grid units (collinear vertices removed). Raises ValueError when the shape
    has an enclosed gap, touches itself only at a corner, or is not a single piece."""
    edges = {}  # start point -> end point (directed, counter-clockwise around each cell)
    cell_edges = []
    for cx, cy, w, d in cells:
        x0, y0, x1, y1 = float(cx), float(cy), cx + float(w), cy + float(d)
        cell_edges += [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    pairs = set(cell_edges)
    for a, b in cell_edges:
        if (b, a) in pairs:
            continue  # shared by two cells: interior
        if a in edges:
            raise ValueError('The shape touches itself at a corner')
        edges[a] = b
    if not edges:
        raise ValueError('The shape is empty')
    start = min(edges)
    loop, point = [], start
    while True:
        loop.append(point)
        point = edges[point]
        if point == start:
            break
        if len(loop) > len(edges):
            raise ValueError('The shape outline is not a single loop')
    if len(loop) != len(edges):
        raise ValueError('The shape has an enclosed gap or is in separate pieces')
    return _drop_collinear(loop)


def _drop_collinear(loop: list) -> list:
    out = []
    n = len(loop)
    for i in range(n):
        p, q, r = loop[i - 1], loop[i], loop[(i + 1) % n]
        if (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0]) != 0:
            out.append(q)
    return out


def inset_polygon(loop: list, distance: float) -> list:
    """Moves every edge of a counter-clockwise rectilinear polygon inward by `distance` (negative
    grows it). Each vertex shifts by distance along both adjacent inward normals."""
    n = len(loop)
    out = []
    for i in range(n):
        p, q, r = loop[i - 1], loop[i], loop[(i + 1) % n]
        nx = ny = 0.0
        for a, b in ((p, q), (q, r)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = abs(dx) + abs(dy)
            nx += -dy / length  # left of the travel direction = inside for a counter-clockwise loop
            ny += dx / length
        out.append((q[0] + distance * nx, q[1] + distance * ny))
    return out


def full_cell_rects(cells: list) -> list:
    """Groups the full-size (1 x 1) cells into rectangles by merging equal row runs.
    Returns [(cx, cy, countX, countY)]. Half-size cells are not included."""
    full = {(cx, cy) for cx, cy, w, d in cells if w == 1 and d == 1}
    if not full:
        return []
    rows = max(y for _, y in full) + 1
    cols = max(x for x, _ in full) + 1
    rects, open_runs = [], {}
    for y in range(rows + 1):
        runs = set()
        x = 0
        while y < rows and x < cols:
            if (x, y) in full:
                x0 = x
                while (x + 1, y) in full:
                    x += 1
                runs.add((x0, x))
            x += 1
        for run in sorted(open_runs):
            if run not in runs:
                y0 = open_runs.pop(run)
                rects.append((run[0], y0, run[1] - run[0] + 1, y - y0))
        for run in sorted(runs):
            open_runs.setdefault(run, y)
    return rects


def cell_rects(cells) -> list:
    """Groups a set of (col, row) cells into non-overlapping rectangles [(x0, x1, y0, y1)] (inclusive):
    horizontal runs per row, then identical runs in consecutive rows are stacked."""
    rows = {}
    for x, y in cells:
        rows.setdefault(y, set()).add(x)
    runs = {}
    for y in sorted(rows):
        xs = sorted(rows[y])
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            runs.setdefault((start, prev), []).append(y)
            if x is not None:
                start = prev = x
    rects = []
    for (x0, x1), ys in runs.items():
        ys = sorted(ys)
        y_start = prev_y = ys[0]
        for y in ys[1:] + [None]:
            if y is not None and y == prev_y + 1:
                prev_y = y
                continue
            rects.append((x0, x1, y_start, prev_y))
            if y is not None:
                y_start = prev_y = y
    return sorted(rects, key=lambda r: (r[2], r[0]))
