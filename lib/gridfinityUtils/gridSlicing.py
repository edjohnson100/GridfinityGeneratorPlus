"""
Shared "grid slicing" model for half-unit edge support (baseplates and bins).

Builds a per-axis list of cell sizes (a half-size entry at each checked edge,
full-size entries for the core count in between), then decomposes the resulting
2D grid into up to 9 regions (1 center, 4 edge strips, 4 corners) so Fusion's
native rectangular-pattern feature can still be used for each uniform region,
rather than creating every cell individually.

No adsk imports - pure Python, usable/testable outside Fusion.
"""

from dataclasses import dataclass, field


@dataclass
class GridAxisSlice:
    sizes: list
    offsets: list
    hasLeadingHalf: bool
    hasTrailingHalf: bool
    fullCellCount: int
    totalSize: float


def buildAxisSlice(coreCount: int, fullUnitSize: float, halfUnitSize: float, hasLeadingHalf: bool, hasTrailingHalf: bool) -> GridAxisSlice:
    sizes = []
    if hasLeadingHalf:
        sizes.append(halfUnitSize)
    sizes.extend([fullUnitSize] * coreCount)
    if hasTrailingHalf:
        sizes.append(halfUnitSize)

    offsets = []
    runningOffset = 0.0
    for size in sizes:
        offsets.append(runningOffset)
        runningOffset += size

    return GridAxisSlice(
        sizes=sizes,
        offsets=offsets,
        hasLeadingHalf=hasLeadingHalf,
        hasTrailingHalf=hasTrailingHalf,
        fullCellCount=coreCount,
        totalSize=runningOffset,
    )


@dataclass
class GridModel:
    xAxis: GridAxisSlice
    yAxis: GridAxisSlice
    baseWidth: float
    baseLength: float

    @property
    def totalWidth(self) -> float:
        return self.xAxis.totalSize

    @property
    def totalLength(self) -> float:
        return self.yAxis.totalSize


def buildGridModel(
    coreWidthCount: int,
    coreLengthCount: int,
    baseWidth: float,
    baseLength: float,
    hasHalfLeft: bool,
    hasHalfRight: bool,
    hasHalfFront: bool,
    hasHalfBack: bool,
) -> GridModel:
    xAxis = buildAxisSlice(coreWidthCount, baseWidth, baseWidth / 2, hasHalfLeft, hasHalfRight)
    yAxis = buildAxisSlice(coreLengthCount, baseLength, baseLength / 2, hasHalfFront, hasHalfBack)
    return GridModel(xAxis=xAxis, yAxis=yAxis, baseWidth=baseWidth, baseLength=baseLength)


@dataclass
class GridRegion:
    kind: str
    originX: float
    originY: float
    cellWidth: float
    cellLength: float
    countX: int
    countY: int
    isFullSizeCell: bool


def enumerateGridRegions(model: GridModel) -> list:
    regions = []
    xAxis = model.xAxis
    yAxis = model.yAxis

    # center: uniform full-size coreWidthCount x coreLengthCount block
    if xAxis.fullCellCount > 0 and yAxis.fullCellCount > 0:
        centerOriginX = xAxis.offsets[1] if xAxis.hasLeadingHalf else xAxis.offsets[0]
        centerOriginY = yAxis.offsets[1] if yAxis.hasLeadingHalf else yAxis.offsets[0]
        regions.append(GridRegion(
            kind='center',
            originX=centerOriginX,
            originY=centerOriginY,
            cellWidth=model.baseWidth,
            cellLength=model.baseLength,
            countX=xAxis.fullCellCount,
            countY=yAxis.fullCellCount,
            isFullSizeCell=True,
        ))

    # edge-left / edge-right: half-width strips running along Y, one cell per full Y module
    if xAxis.hasLeadingHalf and yAxis.fullCellCount > 0:
        edgeOriginY = yAxis.offsets[1] if yAxis.hasLeadingHalf else yAxis.offsets[0]
        regions.append(GridRegion(
            kind='edge-left',
            originX=xAxis.offsets[0],
            originY=edgeOriginY,
            cellWidth=model.baseWidth / 2,
            cellLength=model.baseLength,
            countX=1,
            countY=yAxis.fullCellCount,
            isFullSizeCell=False,
        ))
    if xAxis.hasTrailingHalf and yAxis.fullCellCount > 0:
        edgeOriginY = yAxis.offsets[1] if yAxis.hasLeadingHalf else yAxis.offsets[0]
        regions.append(GridRegion(
            kind='edge-right',
            originX=xAxis.offsets[-1],
            originY=edgeOriginY,
            cellWidth=model.baseWidth / 2,
            cellLength=model.baseLength,
            countX=1,
            countY=yAxis.fullCellCount,
            isFullSizeCell=False,
        ))

    # edge-front / edge-back: half-length strips running along X, one cell per full X module
    if yAxis.hasLeadingHalf and xAxis.fullCellCount > 0:
        edgeOriginX = xAxis.offsets[1] if xAxis.hasLeadingHalf else xAxis.offsets[0]
        regions.append(GridRegion(
            kind='edge-front',
            originX=edgeOriginX,
            originY=yAxis.offsets[0],
            cellWidth=model.baseWidth,
            cellLength=model.baseLength / 2,
            countX=xAxis.fullCellCount,
            countY=1,
            isFullSizeCell=False,
        ))
    if yAxis.hasTrailingHalf and xAxis.fullCellCount > 0:
        edgeOriginX = xAxis.offsets[1] if xAxis.hasLeadingHalf else xAxis.offsets[0]
        regions.append(GridRegion(
            kind='edge-back',
            originX=edgeOriginX,
            originY=yAxis.offsets[-1],
            cellWidth=model.baseWidth,
            cellLength=model.baseLength / 2,
            countX=xAxis.fullCellCount,
            countY=1,
            isFullSizeCell=False,
        ))

    # corners: single quarter-size cell wherever both adjacent perpendicular edges are checked
    cornerSpecs = [
        ('corner-front-left', xAxis.hasLeadingHalf, yAxis.hasLeadingHalf, xAxis.offsets[0] if xAxis.hasLeadingHalf else None, yAxis.offsets[0] if yAxis.hasLeadingHalf else None),
        ('corner-front-right', xAxis.hasTrailingHalf, yAxis.hasLeadingHalf, xAxis.offsets[-1] if xAxis.hasTrailingHalf else None, yAxis.offsets[0] if yAxis.hasLeadingHalf else None),
        ('corner-back-left', xAxis.hasLeadingHalf, yAxis.hasTrailingHalf, xAxis.offsets[0] if xAxis.hasLeadingHalf else None, yAxis.offsets[-1] if yAxis.hasTrailingHalf else None),
        ('corner-back-right', xAxis.hasTrailingHalf, yAxis.hasTrailingHalf, xAxis.offsets[-1] if xAxis.hasTrailingHalf else None, yAxis.offsets[-1] if yAxis.hasTrailingHalf else None),
    ]
    for kind, hasX, hasY, originX, originY in cornerSpecs:
        if hasX and hasY:
            regions.append(GridRegion(
                kind=kind,
                originX=originX,
                originY=originY,
                cellWidth=model.baseWidth / 2,
                cellLength=model.baseLength / 2,
                countX=1,
                countY=1,
                isFullSizeCell=False,
            ))

    return regions
