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


def split_axis(full: int, half: int, pitch: float, waste: float, bed: float) -> dict:
    """Splits one axis of the drawer into the fewest printable tiles.

    Returns {'segments': [...], 'fits': bool}. Each segment has: startMm, sizeMm, cells
    (full cells), half (bool), padStart, padEnd (mm). `fits` is False when no split can
    keep every tile within the bed (e.g. bed smaller than one pitch).
    """
    half = 1 if half else 0
    total = full * pitch + half * pitch / 2.0 + waste
    pad = waste / 2.0
    n = max(1, math.ceil(total / bed - 1e-9)) if bed > 0 else 1
    max_n = max(1, full)  # more tiles than full cells would create empty tiles

    segments, fits = [], False
    while True:
        cells = _distribute(full, n)
        segments, start, fits = [], 0.0, True
        for i, c in enumerate(cells):
            first, last = i == 0, i == n - 1
            pad_start = pad if first else 0.0
            pad_end = pad if last else 0.0
            has_half = bool(half) and last
            size = c * pitch + (pitch / 2.0 if has_half else 0.0) + pad_start + pad_end
            if bed > 0 and size > bed + 1e-6:
                fits = False
            segments.append({
                'startMm': round(start, 3), 'sizeMm': round(size, 3), 'cells': c,
                'half': has_half, 'padStart': round(pad_start, 3), 'padEnd': round(pad_end, 3),
            })
            start += size
        if fits or n >= max_n:
            break
        n += 1
    return {'segments': segments, 'fits': fits}


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


def _custom_grid_bins(xs_segments: list, ys_segments: list, custom_bins: list) -> tuple:
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
        try:
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
        cells = {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
        if cells & occupied:
            dropped += 1
            continue
        occupied |= cells
        half_right = half_x and x1 == cols - 1
        half_back = half_y and y1 == rows - 1
        bins.append({
            'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1,
            'w': (x1 - x0 + 1) - (1 if half_right else 0),
            'd': (y1 - y0 + 1) - (1 if half_back else 0),
            'halfRight': half_right, 'halfBack': half_back, 'customIndex': index,
        })
    uncovered = [{'col': x, 'row': y} for y in range(rows) for x in range(cols) if (x, y) not in occupied]
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
) -> dict:
    """width_fit / depth_fit: {'full': int, 'half': int, 'wasteMm': float} (optimizer breakdown rows).

    tile_bin_settings: optional per-tile overrides of the bin fill, keyed '<col>,<row>':
    {'strategy': 'perTile'|'uniform', 'maxBinCellsWidth': int, 'maxBinCellsDepth': int}.
    Any missing key (or tile) falls back to the global bin_strategy / max_bin_cells_*.
    """
    tile_bin_settings = tile_bin_settings or {}
    xs = split_axis(width_fit['full'], width_fit['half'], pitch_mm, width_fit['wasteMm'], bed_width_mm)
    ys = split_axis(depth_fit['full'], depth_fit['half'], pitch_mm, depth_fit['wasteMm'], bed_depth_mm)

    tiles, bins = [], []
    dropped_custom = 0
    for row, ys_seg in enumerate(ys['segments']):
        for col, xs_seg in enumerate(xs['segments']):
            tile_index = len(tiles)
            tiles.append({
                'col': col, 'row': row, 'key': f'{col},{row}',
                'xMm': xs_seg['startMm'], 'yMm': ys_seg['startMm'],
                'widthMm': xs_seg['sizeMm'], 'depthMm': ys_seg['sizeMm'],
                'plateWidth': xs_seg['cells'], 'plateLength': ys_seg['cells'],
                'hasHalfRight': xs_seg['half'], 'hasHalfBack': ys_seg['half'],
                'paddingLeftMm': xs_seg['padStart'], 'paddingRightMm': xs_seg['padEnd'],
                'paddingFrontMm': ys_seg['padStart'], 'paddingBackMm': ys_seg['padEnd'],
            })

            if bin_strategy == BIN_STRATEGY_CUSTOM:
                continue  # hand-drawn bins live on one drawer-wide grid; they are added after the tile loop
            override = tile_bin_settings.get(f'{col},{row}') or {}
            strategy = override.get('strategy') or bin_strategy
            if strategy == BIN_STRATEGY_CUSTOM:
                strategy = BIN_STRATEGY_PER_TILE  # stale per-tile 'custom' from an older save
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
        cbins, uncovered, dropped_custom, grid = _custom_grid_bins(xs['segments'], ys['segments'], custom_bins)
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
            })

    warnings = []
    if dropped_custom:
        warnings.append(f'{dropped_custom} hand-drawn bin(s) no longer fit the drawer grid (the layout changed, or they overlap) and were ignored')
    if not xs['fits'] or not ys['fits']:
        warnings.append('Some tiles are larger than the printer bed even after splitting (bed smaller than the grid size?)')

    return {
        'pitchMm': pitch_mm,
        'totalWidthMm': round(sum(s['sizeMm'] for s in xs['segments']), 3),
        'totalDepthMm': round(sum(s['sizeMm'] for s in ys['segments']), 3),
        'cols': len(xs['segments']), 'rows': len(ys['segments']),
        'tiles': tiles, 'bins': bins, 'warnings': warnings, 'customGrid': custom_grid,
    }
