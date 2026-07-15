import math


def calculate_fit(dimension_mm: float, grid_size_mm: float, allow_half_bins: bool) -> dict:
    full = int(dimension_mm // grid_size_mm)
    remainder = math.fmod(dimension_mm, grid_size_mm)
    if allow_half_bins and remainder >= grid_size_mm / 2.0:
        return {'full': full, 'half': 1, 'waste': remainder - grid_size_mm / 2.0}
    return {'full': full, 'half': 0, 'waste': remainder}


PRIORITY_WEIGHTS = {
    'widthOnly': {'Width': 1.0, 'Depth': 0.0},
    'width': {'Width': 3.0, 'Depth': 1.0},
    'balanced': {'Width': 1.0, 'Depth': 1.0},
    'depth': {'Width': 1.0, 'Depth': 3.0},
    'depthOnly': {'Width': 0.0, 'Depth': 1.0},
}


def run_optimization(dims: list, min_size_mm: int, max_size_mm: int, allow_half_bins: bool, priority: str = 'balanced') -> list:
    weights = PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS['balanced'])
    results = []
    for size in range(min_size_mm, max_size_mm + 1):
        score = 0.0
        actual_waste = 0.0
        for dim in dims:
            waste = calculate_fit(dim['mm'], size, allow_half_bins)['waste']
            score += waste * weights.get(dim['type'], 1.0)
            actual_waste += waste
        results.append({'size': size, 'score': score, 'waste': actual_waste})
    results.sort(key=lambda item: item['score'])
    return results


def _expand_items(items: list) -> list:
    dims = []
    for item in items:
        dims.append({'description': item['description'], 'type': 'Width', 'mm': item['widthMm']})
        dims.append({'description': item['description'], 'type': 'Depth', 'mm': item['depthMm']})
    return dims


def _fit_breakdown(dims: list, grid_size_mm: float, allow_half_bins: bool) -> list:
    breakdown = []
    for dim in dims:
        fit = calculate_fit(dim['mm'], grid_size_mm, allow_half_bins)
        breakdown.append({
            'description': dim['description'],
            'type': dim['type'],
            'dimensionMm': round(dim['mm'], 2),
            'full': fit['full'],
            'half': fit['half'],
            'wasteMm': round(fit['waste'], 2),
        })
    return breakdown


STANDARD_GRID_SIZE_MM = 42


def compute_best_fit(items: list, min_size_mm: int, max_size_mm: int, allow_half_bins: bool, compare_standard: bool, priority: str = 'balanced') -> dict:
    dims = _expand_items(items)

    results = run_optimization(dims, min_size_mm, max_size_mm, allow_half_bins, priority)
    if not results:
        return {'optimalSizeMm': None, 'totalWasteMm': 0, 'items': [], 'standard': None}

    best = results[0]
    optimalSizeMm = best['size']
    totalWasteMm = round(best['waste'], 2)
    itemsBreakdown = _fit_breakdown(dims, optimalSizeMm, allow_half_bins)
    widthWasteMm = round(sum(i['wasteMm'] for i in itemsBreakdown if i['type'] == 'Width'), 2)
    depthWasteMm = round(sum(i['wasteMm'] for i in itemsBreakdown if i['type'] == 'Depth'), 2)

    standard = None
    if compare_standard:
        standardItems = _fit_breakdown(dims, STANDARD_GRID_SIZE_MM, allow_half_bins)
        standard = {
            'sizeMm': STANDARD_GRID_SIZE_MM,
            'totalWasteMm': round(sum(i['wasteMm'] for i in standardItems), 2),
            'widthWasteMm': round(sum(i['wasteMm'] for i in standardItems if i['type'] == 'Width'), 2),
            'depthWasteMm': round(sum(i['wasteMm'] for i in standardItems if i['type'] == 'Depth'), 2),
            'items': standardItems,
        }

    return {
        'optimalSizeMm': optimalSizeMm,
        'totalWasteMm': totalWasteMm,
        'widthWasteMm': widthWasteMm,
        'depthWasteMm': depthWasteMm,
        'priority': priority,
        'items': itemsBreakdown,
        'standard': standard,
    }
