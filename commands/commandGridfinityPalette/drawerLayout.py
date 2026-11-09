"""Pure-Python drawer layout engine (no adsk imports).

Turns one optimizer fit (per axis: full cells, optional half cell, leftover mm) plus a
printer bed size into a list of baseplate tiles and the bins that fill them. All values
are millimetres; the caller converts to Fusion's centimetres when building forms.

Axis convention matches the Baseplate/Bin forms: "width" runs along X (left to right) and
"depth" along Y (front to back). A half-size strip always sits on the trailing edge
(right / back), and leftover space is split evenly into padding at both ends of the axis.
Tiles are numbered by (col, row), starting at the left / front.
"""
import itertools
import math

BIN_STRATEGY_PER_TILE = 'perTile'
BIN_STRATEGY_UNIFORM = 'uniform'
BIN_STRATEGY_PALETTE = 'palette'
BIN_STRATEGY_CUSTOM = 'custom'  # bins drawn by hand on one drawer-wide grid (see _custom_grid_bins)


def _distribute(total: int, parts: int) -> list:
    """Splits `total` into `parts` near-equal integers, larger ones first."""
    base, rem = divmod(total, parts)
    return [base + (1 if i < rem else 0) for i in range(parts)]


def axis_paddings(waste: float, align: str = 'center') -> tuple:
    """(padStart, padEnd) for an axis. 'center' splits the leftover evenly; 'start' (left / front) or
    'end' (right / back) puts all of it at that end."""
    if align == 'start':
        return waste, 0.0
    if align == 'end':
        return 0.0, waste
    return waste / 2.0, waste / 2.0


def split_axis(full: int, half: int, pitch: float, waste: float, bed: float, align: str = 'center') -> dict:
    """Splits one axis of the drawer into the fewest printable tiles.

    Returns {'segments': [...], 'fits': bool}. Each segment has: startMm, sizeMm, cells
    (full cells), half (bool), padStart, padEnd (mm). `fits` is False when no split can
    keep every tile within the bed (e.g. bed smaller than one pitch).
    """
    pad_start, pad_end = axis_paddings(waste, align)
    return _split_span(full, half, pitch, pad_start, pad_end, bed)


def _split_span(full: int, half: int, pitch: float, pad_start: float, pad_end: float, bed: float) -> dict:
    """Like split_axis but for any span of cells with explicit padding at its two ends (a
    non-rectangular drawer's plate rectangles only carry padding on edges at the drawer's outer
    boundary). startMm is relative to the start of the span (padding included)."""
    half = 1 if half else 0
    total = full * pitch + half * pitch / 2.0 + pad_start + pad_end
    n = max(1, math.ceil(total / bed - 1e-9)) if bed > 0 else 1
    max_n = max(1, full)  # more tiles than full cells would create empty tiles

    segments, fits = [], False
    while True:
        cells = _distribute(full, n)
        segments, start, fits = [], 0.0, True
        for i, c in enumerate(cells):
            first, last = i == 0, i == n - 1
            seg_pad_start = pad_start if first else 0.0
            seg_pad_end = pad_end if last else 0.0
            has_half = bool(half) and last
            size = c * pitch + (pitch / 2.0 if has_half else 0.0) + seg_pad_start + seg_pad_end
            if bed > 0 and size > bed + 1e-6:
                fits = False
            segments.append({
                'startMm': round(start, 3), 'sizeMm': round(size, 3), 'cells': c,
                'half': has_half, 'padStart': round(seg_pad_start, 3), 'padEnd': round(seg_pad_end, 3),
            })
            start += size
        if fits or n >= max_n:
            break
        n += 1
    return {'segments': segments, 'fits': fits}


def normalize_mask(mask, cols: int, rows: int):
    """Returns (mask, resized, is_rectangular): mask as rows (front row first) of bools sized
    rows x cols, or None when there is no mask. Cells added by a resize (the layout grew) are on."""
    if not mask:
        return None, False, True
    resized = len(mask) != rows or any(len(r) != cols for r in mask)
    out = []
    for y in range(rows):
        src = mask[y] if y < len(mask) else []
        out.append([bool(src[x]) if x < len(src) else True for x in range(cols)])
    return out, resized, all(all(r) for r in out)


def _row_rects(mask: list) -> list:
    rects, open_runs = [], {}  # open_runs: (x0, x1) -> start row
    rows = len(mask)
    for y in range(rows + 1):
        runs = set()
        if y < rows:
            x, cols = 0, len(mask[y])
            while x < cols:
                if mask[y][x]:
                    x0 = x
                    while x + 1 < cols and mask[y][x + 1]:
                        x += 1
                    runs.add((x0, x))
                x += 1
        for run in sorted(open_runs):
            if run not in runs:
                rects.append({'x0': run[0], 'x1': run[1], 'y0': open_runs.pop(run), 'y1': y - 1})
        for run in sorted(runs):
            open_runs.setdefault(run, y)
    return rects


def decompose_mask(mask: list) -> list:
    """Splits the on-cells of a mask (rows x cols booleans, front row first) into non-overlapping
    rectangles [{x0, x1, y0, y1}] (inclusive cell indices). Tries merging equal runs row by row and
    column by column and keeps whichever gives fewer rectangles (row-wise on a tie)."""
    by_rows = _row_rects(mask)
    rows = len(mask)
    cols = len(mask[0]) if rows else 0
    transposed = [[mask[y][x] for y in range(rows)] for x in range(cols)]
    by_cols = [{'x0': r['y0'], 'x1': r['y1'], 'y0': r['x0'], 'y1': r['x1']} for r in _row_rects(transposed)]
    best = by_cols if len(by_cols) < len(by_rows) else by_rows
    return sorted(best, key=lambda r: (r['y0'], r['x0']))


def _rect_spans(rect, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_w, bed_d):
    """Bed-split spans (xspan, yspan) of one plate rectangle; pads = (x0, x1, y0, y1) outer padding."""
    pad_x0, pad_x1, pad_y0, pad_y1 = pads
    hx = half_x and rect['x1'] == grid_cols - 1
    hy = half_y and rect['y1'] == grid_rows - 1
    xspan = _split_span(rect['x1'] - rect['x0'] + 1 - (1 if hx else 0), hx, pitch_mm,
                        pad_x0 if rect['x0'] == 0 else 0.0, pad_x1 if rect['x1'] == grid_cols - 1 else 0.0, bed_w)
    yspan = _split_span(rect['y1'] - rect['y0'] + 1 - (1 if hy else 0), hy, pitch_mm,
                        pad_y0 if rect['y0'] == 0 else 0.0, pad_y1 if rect['y1'] == grid_rows - 1 else 0.0, bed_d)
    return xspan, yspan


def _rects_score(rects, span_fn) -> tuple:
    """Lower is better: the largest smallest tile (no tiny plates), then fewest printed tiles, then fewest rectangles."""
    tiles, smallest = 0, None
    for r in rects:
        xspan, yspan = span_fn(r)
        tiles += len(xspan['segments']) * len(yspan['segments'])
        for ys in yspan['segments']:
            for xs in xspan['segments']:
                area = xs['sizeMm'] * ys['sizeMm']
                smallest = area if smallest is None else min(smallest, area)
    return (-(smallest or 0.0), tiles, len(rects))


def _greedy_rects(mask, fits_fn) -> list:
    """Repeatedly takes the largest rectangle of remaining on-cells (preferring ones that fit the
    bed as one tile), so big plates come first and the leftovers are what is small."""
    rows = len(mask)
    cols = len(mask[0]) if rows else 0
    left = [row[:] for row in mask]
    out = []
    while any(any(r) for r in left):
        best, best_key = None, None
        for y0 in range(rows):
            for x0 in range(cols):
                if not left[y0][x0]:
                    continue
                max_x = cols - 1
                for y1 in range(y0, rows):
                    x1 = x0
                    while x1 <= max_x and left[y1][x1]:
                        x1 += 1
                    x1 -= 1
                    if x1 < x0:
                        break
                    max_x = x1
                    for xe in range(x0, x1 + 1):
                        rect = {'x0': x0, 'x1': xe, 'y0': y0, 'y1': y1}
                        key = (fits_fn(rect), (xe - x0 + 1) * (y1 - y0 + 1), -y0, -x0)
                        if best_key is None or key > best_key:
                            best, best_key = rect, key
        for y in range(best['y0'], best['y1'] + 1):
            for x in range(best['x0'], best['x1'] + 1):
                left[y][x] = False
        out.append(best)
    return out


def _merge_rects(rects, span_fn) -> list:
    """Joins neighbouring rectangles whose union is itself a rectangle when that scores better
    (no smaller a smallest tile, and fewer printed tiles), e.g. a thin strip into the plate beside it."""
    rects = [dict(r) for r in rects]
    changed = True
    while changed:
        changed = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a['x0'] == b['x0'] and a['x1'] == b['x1'] and (a['y1'] + 1 == b['y0'] or b['y1'] + 1 == a['y0']):
                    merged = {'x0': a['x0'], 'x1': a['x1'], 'y0': min(a['y0'], b['y0']), 'y1': max(a['y1'], b['y1'])}
                elif a['y0'] == b['y0'] and a['y1'] == b['y1'] and (a['x1'] + 1 == b['x0'] or b['x1'] + 1 == a['x0']):
                    merged = {'x0': min(a['x0'], b['x0']), 'x1': max(a['x1'], b['x1']), 'y0': a['y0'], 'y1': a['y1']}
                else:
                    continue
                sm, sab = _rects_score([merged], span_fn), _rects_score([a, b], span_fn)
                if sm[0] <= sab[0] and sm[1] < sab[1]:
                    rects[i] = merged
                    del rects[j]
                    changed = True
                    break
            if changed:
                break
    return rects


def plan_plate_rects(mask, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_w, bed_d) -> list:
    """Plate rectangles for a drawer shape: tries the row-wise, column-wise and largest-first
    decompositions, merges neighbours where that gives bigger plates, and keeps the best (largest
    smallest tile, then fewest printed tiles). Rectangles are sorted front-left first."""
    def span_fn(r):
        return _rect_spans(r, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_w, bed_d)

    def fits_fn(r):
        xspan, yspan = span_fn(r)
        return 1 if (len(xspan['segments']) == 1 and len(yspan['segments']) == 1 and xspan['fits'] and yspan['fits']) else 0

    candidates = [decompose_mask(mask), _greedy_rects(mask, fits_fn)]
    best, best_score = None, None
    for cand in candidates:
        for rects in (cand, _merge_rects(cand, span_fn)):
            score = _rects_score(rects, span_fn)
            if best_score is None or score < best_score:
                best, best_score = rects, score
    return sorted(best, key=lambda r: (r['y0'], r['x0']))


def _connected(cells) -> bool:
    cells = set(cells)
    if not cells:
        return False
    start = next(iter(cells))
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in cells and n not in seen:
                seen.add(n)
                stack.append(n)
    return len(seen) == len(cells)


def plan_cut_plates(mask, xs, ys, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_w, bed_d) -> list:
    """Plates for a drawer shape made the other way round: tile the whole bounding grid to the bed
    first, then take each tile's on-cells. A tile whose on-cells are one connected piece becomes ONE
    plate (the bounding box of those cells) with the off-cells inside it listed as `removed`
    (cell offsets relative to the plate) to be cut out of the plate; a tile whose on-cells are in
    separate pieces falls back to plain rectangles. Returns [(rect, removed)]."""
    def ranges(segments):
        out, start = [], 0
        for seg in segments:
            n = seg['cells'] + (1 if seg['half'] else 0)
            out.append((start, start + n - 1))
            start += n
        return out

    plates = []
    for ry0, ry1 in ranges(ys['segments']):
        for rx0, rx1 in ranges(xs['segments']):
            on = {(x, y) for y in range(ry0, ry1 + 1) for x in range(rx0, rx1 + 1) if mask[y][x]}
            if not on:
                continue
            if _connected(on):
                x0, x1 = min(x for x, _ in on), max(x for x, _ in on)
                y0, y1 = min(y for _, y in on), max(y for _, y in on)
                removed = [[x - x0, y - y0] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if (x, y) not in on]
                plates.append(({'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1}, removed))
            else:
                local = [[(x, y) in on for x in range(rx0, rx1 + 1)] for y in range(ry0, ry1 + 1)]
                for r in decompose_mask(local):
                    plates.append(({'x0': r['x0'] + rx0, 'x1': r['x1'] + rx0, 'y0': r['y0'] + ry0, 'y1': r['y1'] + ry0}, []))
    return plates


def _cut_plates_score(plates, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_w, bed_d) -> tuple:
    """(largest-smallest-plate, plate count) for plates with removed cells; same shape as _rects_score[:2]."""
    smallest = None
    for rect, removed in plates:
        xspan, yspan = _rect_spans(rect, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_w, bed_d)
        area = sum(x['sizeMm'] for x in xspan['segments']) * sum(y['sizeMm'] for y in yspan['segments'])
        for cx, cy in removed:
            w = pitch_mm / 2.0 if (half_x and rect['x0'] + cx == grid_cols - 1) else pitch_mm
            d = pitch_mm / 2.0 if (half_y and rect['y0'] + cy == grid_rows - 1) else pitch_mm
            area -= w * d
        smallest = area if smallest is None else min(smallest, area)
    return (-(smallest or 0.0), len(plates))


def _mask_regions(mask: list) -> int:
    """Number of 4-connected groups of on-cells."""
    rows, cols = len(mask), (len(mask[0]) if mask else 0)
    seen, regions = set(), 0
    for y in range(rows):
        for x in range(cols):
            if mask[y][x] and (x, y) not in seen:
                regions += 1
                stack = [(x, y)]
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < cols and 0 <= ny < rows and mask[ny][nx] and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
    return regions


def _chunk_cells(cells: int, half: bool, max_cells: int) -> list:
    """Splits one tile's cells along an axis into bin-sized chunks of at most `max_cells`
    full cells. The half strip rides with the last chunk. Returns [{offset, cells, half}]."""
    if cells <= 0:
        return [{'offset': 0, 'cells': 0, 'half': half}] if half else []
    max_cells = max(1, int(max_cells))
    parts = math.ceil(cells / max_cells)
    counts = _distribute(cells, parts)
    chunks, offset = [], 0
    for i, c in enumerate(counts):
        chunks.append({'offset': offset, 'cells': c, 'half': half and i == parts - 1})
        offset += c
    return chunks


def parse_bin_palette(text) -> tuple:
    """Parses a palette like '3x2, 2x2, 1x1' (cells wide x cells deep) into ([(w, d), ...], [errors]).
    Both orientations of every size are allowed; 1x1 is always added so any tile can be filled.
    Invalid entries are reported in the error list and skipped."""
    sizes, errors = set(), []
    for raw in str(text or '').replace(';', ',').split(','):
        token = raw.strip().lower().replace('×', 'x')
        if not token:
            continue
        parts = token.split('x')
        try:
            if len(parts) != 2:
                raise ValueError
            w, d = int(parts[0]), int(parts[1])
            if w < 1 or d < 1:
                raise ValueError
        except ValueError:
            errors.append(f'"{raw.strip()}" is not a size like 2x3')
            continue
        sizes.add((w, d))
        sizes.add((d, w))
    sizes.add((1, 1))
    # largest area first, then wider first, so the greedy fill below is deterministic
    return sorted(sizes, key=lambda s: (-s[0] * s[1], -s[0])), errors


_MAX_PALETTE_ORDERINGS = 720  # 6! -- beyond ~6 distinct sizes fall back to the single largest-first order


def _pack_palette(cells_w: int, cells_d: int, half_x: bool, half_y: bool, palette: list) -> list:
    """Fills a tile from the palette, trying each priority order of the distinct sizes (greedy
    scan for each) and keeping the arrangement with the fewest bins, then the fewest 1x1 bins."""
    distinct = []
    for w, d in palette:
        key = (max(w, d), min(w, d))
        if key != (1, 1) and key not in distinct:
            distinct.append(key)
    orders = [distinct]
    if 1 < len(distinct) <= 6:
        orders = [list(p) for p in itertools.permutations(distinct)][:_MAX_PALETTE_ORDERINGS]

    best, bestScore = None, None
    for order in orders:
        candidate = []
        for big, small in order:
            candidate.append((big, small))
            if big != small:
                candidate.append((small, big))
        candidate.append((1, 1))
        packed = _pack_greedy(cells_w, cells_d, half_x, half_y, candidate)
        score = (len(packed), sum(1 for b in packed if b['w'] == 1 and b['d'] == 1))
        if bestScore is None or score < bestScore:
            best, bestScore = packed, score
    return best


def _pack_greedy(cells_w: int, cells_d: int, half_x: bool, half_y: bool, palette: list) -> list:
    """Greedily covers a cells_w x cells_d block of full cells with palette-sized bins, scanning
    from the front-left and always taking the largest size that still fits. The half strip (if any)
    rides with whichever bins touch the right / back edge. Returns [{offsetX, offsetY, w, d, halfRight, halfBack}]."""
    used = [[False] * cells_w for _ in range(cells_d)]
    bins = []
    for y in range(cells_d):
        for x in range(cells_w):
            if used[y][x]:
                continue
            for w, d in palette:  # always ends: (1, 1) is in the palette
                if x + w > cells_w or y + d > cells_d:
                    continue
                if any(used[yy][xx] for yy in range(y, y + d) for xx in range(x, x + w)):
                    continue
                for yy in range(y, y + d):
                    for xx in range(x, x + w):
                        used[yy][xx] = True
                bins.append({
                    'offsetX': x, 'offsetY': y, 'w': w, 'd': d,
                    'halfRight': half_x and x + w == cells_w,
                    'halfBack': half_y and y + d == cells_d,
                })
                break
    return bins


def shape_problem(cells) -> str:
    """Why a set of (col, row) cells can't be one irregular bin, or '' if it can: it must be one
    edge-connected piece with no enclosed gap and no spots where cells only touch at a corner."""
    cells = set(cells)
    if not cells:
        return 'empty'
    start = next(iter(cells))
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in cells and n not in seen:
                seen.add(n)
                stack.append(n)
    if seen != cells:
        return 'not one connected piece'
    x0, x1 = min(x for x, _ in cells), max(x for x, _ in cells)
    y0, y1 = min(y for _, y in cells), max(y for _, y in cells)
    for y in range(y0 - 1, y1 + 1):
        for x in range(x0 - 1, x1 + 1):
            a, b = (x, y) in cells, (x + 1, y) in cells
            c, d = (x, y + 1) in cells, (x + 1, y + 1) in cells
            if (a and d and not b and not c) or (b and c and not a and not d):
                return 'cells touch only at a corner'
    outside, stack = {(x0 - 1, y0 - 1)}, [(x0 - 1, y0 - 1)]
    while stack:
        x, y = stack.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if x0 - 1 <= n[0] <= x1 + 1 and y0 - 1 <= n[1] <= y1 + 1 and n not in cells and n not in outside:
                outside.add(n)
                stack.append(n)
    if any((x, y) not in cells and (x, y) not in outside for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)):
        return 'encloses a gap'
    return ''


def _custom_grid_bins(xs_segments: list, ys_segments: list, custom_bins: list, mask: list = None) -> tuple:
    """Bins the user drew by hand, on ONE cell grid spanning the whole drawer, so a bin can cross
    baseplate tile seams (inner seams always fall exactly on cell boundaries; only the outer edges
    carry padding and the trailing half strip).

    Each custom bin is {'x0', 'x1', 'y0', 'y1'}: an inclusive rectangle of columns/rows counted from
    the front-left of the drawer. The grid has one column per full cell plus, if the drawer has a
    half strip, one extra half-width last column/row; a bin covering it includes the half strip.
    (Older bins saved with a 'tile': 'col,row' key and tile-local coordinates are shifted onto this grid.)

    Returns (bins, uncovered, dropped, grid): bins as [{x0, x1, y0, y1, w, d, halfRight, halfBack,
    customIndex}], the still-empty cells as [{'col', 'row'}], how many custom bins were ignored
    (outside the grid after the layout changed, or overlapping an earlier one), and grid dimensions."""
    full_cols = sum(s['cells'] for s in xs_segments)
    full_rows = sum(s['cells'] for s in ys_segments)
    half_x = any(s['half'] for s in xs_segments)
    half_y = any(s['half'] for s in ys_segments)
    cols = full_cols + (1 if half_x else 0)
    rows = full_rows + (1 if half_y else 0)
    occupied, bins, dropped = set(), [], 0
    for index, cb in enumerate(custom_bins or []):
        shape_cells = None
        try:
            if cb.get('cells'):  # irregular bin: any edge-connected set of cells
                shape_cells = {(int(c[0]), int(c[1])) for c in cb['cells']}
                x0 = min(x for x, _ in shape_cells)
                x1 = max(x for x, _ in shape_cells)
                y0 = min(y for _, y in shape_cells)
                y1 = max(y for _, y in shape_cells)
                if len(shape_cells) == (x1 - x0 + 1) * (y1 - y0 + 1):
                    shape_cells = None  # actually a rectangle: handled like a plain bin
            else:
                x0, x1, y0, y1 = int(cb['x0']), int(cb['x1']), int(cb['y0']), int(cb['y1'])
            if cb.get('tile'):  # legacy tile-local bin
                tcol, trow = (int(v) for v in str(cb['tile']).split(','))
                shift_x = sum(s['cells'] for s in xs_segments[:tcol])
                shift_y = sum(s['cells'] for s in ys_segments[:trow])
                if not (0 <= tcol < len(xs_segments) and 0 <= trow < len(ys_segments)):
                    raise ValueError
                x0, x1, y0, y1 = x0 + shift_x, x1 + shift_x, y0 + shift_y, y1 + shift_y
        except (KeyError, TypeError, ValueError):
            dropped += 1
            continue
        if not (0 <= x0 <= x1 < cols and 0 <= y0 <= y1 < rows):
            dropped += 1
            continue
        cells = shape_cells if shape_cells is not None else {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
        if mask is not None and not all(mask[y][x] for x, y in cells):
            dropped += 1  # covers a cell outside the drawer shape
            continue
        if cells & occupied or (shape_cells is not None and shape_problem(shape_cells)):
            dropped += 1
            continue
        occupied |= cells
        half_right = half_x and x1 == cols - 1
        half_back = half_y and y1 == rows - 1
        entry = {
            'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1,
            'w': (x1 - x0 + 1) - (1 if half_right else 0),
            'd': (y1 - y0 + 1) - (1 if half_back else 0),
            'halfRight': half_right, 'halfBack': half_back, 'customIndex': index,
        }
        if shape_cells is not None:
            # (column, row, width, depth) relative to the bounding box; half strips are 0.5
            entry['shapeCells'] = [
                [x - x0, y - y0, 0.5 if (half_x and x == cols - 1) else 1, 0.5 if (half_y and y == rows - 1) else 1]
                for x, y in sorted(shape_cells, key=lambda c: (c[1], c[0]))]
        bins.append(entry)
    uncovered = [{'col': x, 'row': y} for y in range(rows) for x in range(cols)
                 if (x, y) not in occupied and (mask is None or mask[y][x])]
    grid = {'cols': cols, 'rows': rows, 'hasHalfX': half_x, 'hasHalfY': half_y}
    return bins, uncovered, dropped, grid


def plan_drawer_layout(
    pitch_mm: float,
    width_fit: dict,
    depth_fit: dict,
    bed_width_mm: float,
    bed_depth_mm: float,
    bin_strategy: str = BIN_STRATEGY_PER_TILE,
    max_bin_cells_width: int = 3,
    max_bin_cells_depth: int = 3,
    tile_bin_settings: dict = None,
    bin_palette: str = '',
    custom_bins: list = None,
    mask: list = None,
    generate_plates: bool = True,
    generate_bins: bool = True,
    pad_align_x: str = 'center',
    pad_align_y: str = 'center',
    cut_cells: bool = True,
) -> dict:
    """width_fit / depth_fit: {'full': int, 'half': int, 'wasteMm': float} (optimizer breakdown rows).

    tile_bin_settings: optional per-tile overrides of the bin fill, keyed '<col>,<row>':
    {'strategy': 'perTile'|'uniform', 'maxBinCellsWidth': int, 'maxBinCellsDepth': int}.
    Any missing key (or tile) falls back to the global bin_strategy / max_bin_cells_*.

    mask: optional drawer shape, rows x cols booleans (front row first) over the drawer's cell grid
    (one column/row per full cell plus a trailing half column/row). Off cells are outside the drawer.
    The on-cells are split into plate rectangles (each further split to the printer bed); padding
    sits only on rectangle edges at the outer boundary of the grid. A missing or all-on mask gives
    the plain rectangular layout. generate_plates / generate_bins are echoed for the builder.

    pad_align_x: 'center' | 'start' (left) | 'end' (right); pad_align_y: 'center' | 'start' (front) | 'end' (back)
    -- where the leftover space (wasteMm) goes along each axis of the drawer's bounding box.
    cut_cells: for shaped drawers, prefer bed-sized plates with the off-cells cut out of them (tile
    entries then carry removedCells) over splitting the shape into many small rectangles.
    """
    tile_bin_settings = tile_bin_settings or {}
    xs = split_axis(width_fit['full'], width_fit['half'], pitch_mm, width_fit['wasteMm'], bed_width_mm, pad_align_x)
    ys = split_axis(depth_fit['full'], depth_fit['half'], pitch_mm, depth_fit['wasteMm'], bed_depth_mm, pad_align_y)

    half_x, half_y = bool(width_fit['half']), bool(depth_fit['half'])
    grid_cols = width_fit['full'] + (1 if half_x else 0)
    grid_rows = depth_fit['full'] + (1 if half_y else 0)
    mask, mask_resized, is_rect = normalize_mask(mask, grid_cols, grid_rows)
    shaped = mask is not None and not is_rect

    # (rect index, col, row, x segment, y segment) for every tile, in build order
    specs = []
    shape_fits = True
    plate_rects = []
    if not shaped:
        for row, ys_seg in enumerate(ys['segments']):
            for col, xs_seg in enumerate(xs['segments']):
                specs.append((None, col, row, xs_seg, ys_seg, None))
    else:
        pad_x0, pad_x1 = axis_paddings(width_fit['wasteMm'], pad_align_x)
        pad_y0, pad_y1 = axis_paddings(depth_fit['wasteMm'], pad_align_y)
        pads = (pad_x0, pad_x1, pad_y0, pad_y1)
        chosen = [(r, []) for r in plan_plate_rects(mask, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads,
                                                    bed_width_mm, bed_depth_mm)]
        if cut_cells:
            cut = plan_cut_plates(mask, xs, ys, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads,
                                  bed_width_mm, bed_depth_mm)
            if any(rem for _, rem in cut):
                old_score = _rects_score([r for r, _ in chosen], lambda r: _rect_spans(
                    r, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads, bed_width_mm, bed_depth_mm))[:2]
                new_score = _cut_plates_score(cut, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads,
                                              bed_width_mm, bed_depth_mm)
                if new_score <= old_score:
                    chosen = cut
        for ri, (rect, removed) in enumerate(chosen):
            plate_rects.append(rect)
            xspan, yspan = _rect_spans(rect, grid_cols, grid_rows, half_x, half_y, pitch_mm, pads,
                                       bed_width_mm, bed_depth_mm)
            shape_fits = shape_fits and xspan['fits'] and yspan['fits']
            x_base = 0.0 if rect['x0'] == 0 else pad_x0 + rect['x0'] * pitch_mm
            y_base = 0.0 if rect['y0'] == 0 else pad_y0 + rect['y0'] * pitch_mm
            for row, ys_seg in enumerate(yspan['segments']):
                for col, xs_seg in enumerate(xspan['segments']):
                    specs.append((
                        ri, col, row,
                        dict(xs_seg, startMm=round(x_base + xs_seg['startMm'], 3)),
                        dict(ys_seg, startMm=round(y_base + ys_seg['startMm'], 3)),
                        removed or None,
                    ))

    tiles, bins = [], []
    dropped_custom = 0
    for rect_index, col, row, xs_seg, ys_seg, removed_cells in specs:
        if True:
            tile_index = len(tiles)
            tiles.append({
                'col': col, 'row': row,
                'key': f'{col},{row}' if rect_index is None else f'r{rect_index}:{col},{row}',
                'rect': rect_index,
                'xMm': xs_seg['startMm'], 'yMm': ys_seg['startMm'],
                'widthMm': xs_seg['sizeMm'], 'depthMm': ys_seg['sizeMm'],
                'plateWidth': xs_seg['cells'], 'plateLength': ys_seg['cells'],
                'hasHalfRight': xs_seg['half'], 'hasHalfBack': ys_seg['half'],
                'paddingLeftMm': xs_seg['padStart'], 'paddingRightMm': xs_seg['padEnd'],
                'paddingFrontMm': ys_seg['padStart'], 'paddingBackMm': ys_seg['padEnd'],
                'removedCells': removed_cells or [],
            })

            if bin_strategy == BIN_STRATEGY_CUSTOM:
                continue  # hand-drawn bins live on one drawer-wide grid; they are added after the tile loop
            override = tile_bin_settings.get(tiles[-1]['key']) or {}
            strategy = override.get('strategy') or bin_strategy
            if strategy == BIN_STRATEGY_CUSTOM:
                strategy = BIN_STRATEGY_PER_TILE  # stale per-tile 'custom' from an older save
            units = [(xs_seg, ys_seg)]
            if removed_cells:
                # bins only fill the cells that are left: pack each kept rectangle as its own mini tile
                full_w = xs_seg['cells'] + (1 if xs_seg['half'] else 0)
                full_d = ys_seg['cells'] + (1 if ys_seg['half'] else 0)
                gone = {(c, r) for c, r in removed_cells}
                local = [[(x, y) not in gone for x in range(full_w)] for y in range(full_d)]
                units = []
                for r in decompose_mask(local):
                    hx = bool(xs_seg['half']) and r['x1'] == full_w - 1
                    hy = bool(ys_seg['half']) and r['y1'] == full_d - 1
                    units.append((
                        {'cells': r['x1'] - r['x0'] + 1 - (1 if hx else 0), 'half': hx,
                         'startMm': xs_seg['startMm'] if r['x0'] == 0 else xs_seg['startMm'] + xs_seg['padStart'] + r['x0'] * pitch_mm,
                         'padStart': xs_seg['padStart'] if r['x0'] == 0 else 0.0},
                        {'cells': r['y1'] - r['y0'] + 1 - (1 if hy else 0), 'half': hy,
                         'startMm': ys_seg['startMm'] if r['y0'] == 0 else ys_seg['startMm'] + ys_seg['padStart'] + r['y0'] * pitch_mm,
                         'padStart': ys_seg['padStart'] if r['y0'] == 0 else 0.0},
                    ))
            for xs_seg, ys_seg in units:
                if (strategy == BIN_STRATEGY_PALETTE and xs_seg['cells'] > 0 and ys_seg['cells'] > 0):
                    palette = parse_bin_palette(bin_palette)[0]
                    for pb in _pack_palette(xs_seg['cells'], ys_seg['cells'], xs_seg['half'], ys_seg['half'], palette):
                        bins.append({
                            'tileIndex': tile_index,
                            'xMm': round(xs_seg['startMm'] + xs_seg['padStart'] + pb['offsetX'] * pitch_mm, 3),
                            'yMm': round(ys_seg['startMm'] + ys_seg['padStart'] + pb['offsetY'] * pitch_mm, 3),
                            'binWidth': pb['w'], 'binLength': pb['d'],
                            'hasHalfRight': pb['halfRight'], 'hasHalfBack': pb['halfBack'],
                            'widthMm': round(pb['w'] * pitch_mm + (pitch_mm / 2.0 if pb['halfRight'] else 0.0), 3),
                            'depthMm': round(pb['d'] * pitch_mm + (pitch_mm / 2.0 if pb['halfBack'] else 0.0), 3),
                        })
                    continue
                if strategy == BIN_STRATEGY_UNIFORM:
                    max_w = int(override.get('maxBinCellsWidth') or max_bin_cells_width)
                    max_d = int(override.get('maxBinCellsDepth') or max_bin_cells_depth)
                else:
                    max_w, max_d = max(1, xs_seg['cells']), max(1, ys_seg['cells'])
                for cy in _chunk_cells(ys_seg['cells'], ys_seg['half'], max_d):
                    for cx in _chunk_cells(xs_seg['cells'], xs_seg['half'], max_w):
                        bins.append({
                            'tileIndex': tile_index,
                            'xMm': round(xs_seg['startMm'] + xs_seg['padStart'] + cx['offset'] * pitch_mm, 3),
                            'yMm': round(ys_seg['startMm'] + ys_seg['padStart'] + cy['offset'] * pitch_mm, 3),
                            'binWidth': cx['cells'], 'binLength': cy['cells'],
                            'hasHalfRight': cx['half'], 'hasHalfBack': cy['half'],
                            'widthMm': round(cx['cells'] * pitch_mm + (pitch_mm / 2.0 if cx['half'] else 0.0), 3),
                            'depthMm': round(cy['cells'] * pitch_mm + (pitch_mm / 2.0 if cy['half'] else 0.0), 3),
                        })

    custom_grid = None
    if bin_strategy == BIN_STRATEGY_CUSTOM:
        cbins, uncovered, dropped_custom, grid = _custom_grid_bins(xs['segments'], ys['segments'], custom_bins, mask if shaped else None)
        origin_x = xs['segments'][0]['padStart']
        origin_y = ys['segments'][0]['padStart']
        custom_grid = dict(grid, originXMm=origin_x, originYMm=origin_y, uncovered=uncovered)
        for cb in cbins:
            bins.append({
                'tileIndex': None,
                'xMm': round(origin_x + cb['x0'] * pitch_mm, 3),
                'yMm': round(origin_y + cb['y0'] * pitch_mm, 3),
                'binWidth': cb['w'], 'binLength': cb['d'],
                'hasHalfRight': cb['halfRight'], 'hasHalfBack': cb['halfBack'],
                'widthMm': round(cb['w'] * pitch_mm + (pitch_mm / 2.0 if cb['halfRight'] else 0.0), 3),
                'depthMm': round(cb['d'] * pitch_mm + (pitch_mm / 2.0 if cb['halfBack'] else 0.0), 3),
                'customIndex': cb['customIndex'],
                'cx0': cb['x0'], 'cx1': cb['x1'], 'cy0': cb['y0'], 'cy1': cb['y1'],
                'shapeCells': cb.get('shapeCells'),
            })

    warnings = []
    if dropped_custom:
        warnings.append(f'{dropped_custom} hand-drawn bin(s) no longer fit the drawer grid (the layout changed, or they overlap) and were ignored')
    if shaped:
        if _mask_regions(mask) == 0:
            warnings.append('The drawer shape has no cells turned on')
        elif _mask_regions(mask) > 1:
            warnings.append('The drawer shape is split into separate regions')
        if mask_resized:
            warnings.append('The drawer shape was resized to match the new layout; new cells are on')
    if (not shape_fits) if shaped else (not xs['fits'] or not ys['fits']):
        warnings.append('Some tiles are larger than the printer bed even after splitting (bed smaller than the grid size?)')

    return {
        'pitchMm': pitch_mm,
        'totalWidthMm': round(sum(s['sizeMm'] for s in xs['segments']), 3),
        'totalDepthMm': round(sum(s['sizeMm'] for s in ys['segments']), 3),
        'cols': len(xs['segments']), 'rows': len(ys['segments']),
        'tiles': tiles, 'bins': bins, 'warnings': warnings, 'customGrid': custom_grid,
        'mask': mask if shaped else None, 'plateRects': plate_rects,
        'shapeGrid': {'cols': grid_cols, 'rows': grid_rows, 'hasHalfX': half_x, 'hasHalfY': half_y,
                      'originXMm': xs['segments'][0]['padStart'], 'originYMm': ys['segments'][0]['padStart']},
        'generatePlates': bool(generate_plates), 'generateBins': bool(generate_bins),
    }
