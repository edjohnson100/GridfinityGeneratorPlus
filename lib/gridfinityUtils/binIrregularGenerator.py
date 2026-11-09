"""
Irregular (non-rectangular, e.g. L-shaped) bins built from a set of grid cells.

Version 1 scope: outline body + stacking feet + one open cavity. No lip, scoop, label tab or
compartment dividers. The outline is one polygon (see cellShape) extruded as a single body so
there are no internal walls, with the same footprint conventions as the rectangular bin: the
body spans each cell's own origin out to (cell size - 2 * xyClearance), and the feet are the same
per-cell base bodies baseGenerator makes for rectangular bins.
"""
import adsk.core, adsk.fusion

from . import const, combineUtils, commonUtils, extrudeUtils, filletUtils, gridSlicing, cellShape
from .baseGenerator import createBaseBodyGrid
from .baseGeneratorInput import BaseGeneratorInput


class BinIrregularGeneratorInput():
    def __init__(self):
        self.cells = []  # [(cx, cy, w, d)], see cellShape
        self.baseWidth = const.DIMENSION_DEFAULT_WIDTH_UNIT
        self.baseLength = const.DIMENSION_DEFAULT_WIDTH_UNIT
        self.heightUnit = const.DIMENSION_DEFAULT_HEIGHT_UNIT
        self.binHeight = 3
        self.xyClearance = const.BIN_XY_CLEARANCE
        self.binCornerFilletRadius = const.BIN_CORNER_FILLET_RADIUS - const.BIN_XY_CLEARANCE
        self.wallThickness = const.BIN_WALL_THICKNESS
        self.isSolid = False
        self.generateBase = True
        self.baseInput = None  # BaseGeneratorInput carrying magnet/screw settings, or None


def _extrudePolygon(points, z, distance, direction, name, component, operation=adsk.fusion.FeatureOperations.NewBodyFeatureOperation):
    """Draws a closed polygon (model-space cm points) on the XY plane offset by z and extrudes it."""
    planeInput = component.constructionPlanes.createInput()
    planeInput.setByOffset(component.xYConstructionPlane, adsk.core.ValueInput.createByReal(z))
    plane = component.constructionPlanes.add(planeInput)
    plane.name = name + ' plane'
    sketch = component.sketches.add(plane)
    sketch.name = name + ' sketch'
    lines = sketch.sketchCurves.sketchLines
    sketchPoints = [sketch.modelToSketchSpace(adsk.core.Point3D.create(x, y, z)) for x, y in points]
    first = lines.addByTwoPoints(sketchPoints[0], sketchPoints[1])
    previous = first
    for point in sketchPoints[2:]:
        previous = lines.addByTwoPoints(previous.endSketchPoint, point)
    lines.addByTwoPoints(previous.endSketchPoint, first.startSketchPoint)
    extrude = extrudeUtils.simpleDistanceExtrude(
        sketch.profiles.item(0), operation, distance, direction, [], component)
    extrude.name = name
    return extrude


def createIrregularBin(input: BinIrregularGeneratorInput, component: adsk.fusion.Component) -> adsk.fusion.BRepBody:
    bw, bl, c = input.baseWidth, input.baseLength, input.xyClearance
    outlineUnits = cellShape.trace_outline(input.cells)  # raises ValueError for unusable shapes
    nominal = [(x * bw, y * bl) for x, y in outlineUnits]

    # Same placement as the rectangular bin box: inset by the clearance on every side, then shifted
    # back so the shape starts at its cells' own origin (box spans [0, total - 2 * clearance]).
    outer = [(x - c, y - c) for x, y in cellShape.inset_polygon(nominal, c)]

    binHeightWithoutBase = input.binHeight - 1
    totalHeight = binHeightWithoutBase * input.heightUnit + max(0, input.heightUnit - const.BIN_BASE_HEIGHT)

    bodyExtrude = _extrudePolygon(outer, 0, totalHeight, adsk.fusion.ExtentDirections.PositiveExtentDirection, 'Irregular bin body', component)
    binBody = bodyExtrude.bodies.item(0)
    binBody.name = 'Bin body'
    filletUtils.filletEdgesByLength(bodyExtrude.faces, input.binCornerFilletRadius, totalHeight, component).name = 'Bin body corner fillets'

    if not input.isSolid:
        inner = cellShape.inset_polygon(outer, input.wallThickness)
        depth = totalHeight - const.BIN_COMPARTMENT_BOTTOM_THICKNESS
        cavity = _extrudePolygon(inner, totalHeight, depth, adsk.fusion.ExtentDirections.NegativeExtentDirection, 'Irregular bin cavity', component)
        cavityBody = cavity.bodies.item(0)
        filletRadius = max(const.BIN_BODY_CUTOUT_BOTTOM_FILLET_RADIUS, input.binCornerFilletRadius - input.wallThickness)
        filletUtils.filletEdgesByLength(cavity.faces, filletRadius, depth, component)
        combineUtils.cutBody(binBody, commonUtils.objectCollectionFromList([cavityBody]), component)

    if input.generateBase:
        baseInput = input.baseInput or BaseGeneratorInput()
        baseInput.originPoint = component.originConstructionPoint.geometry
        baseInput.baseWidth = bw
        baseInput.baseLength = bl
        baseInput.xyClearance = c
        # createBaseBodyGrid only needs the true pitch from the grid model; the regions say where cells are
        pitchModel = gridSlicing.buildGridModel(1, 1, bw, bl, False, False, False, False)
        regions = []
        for cx, cy, countX, countY in cellShape.full_cell_rects(input.cells):
            regions.append(gridSlicing.GridRegion(
                kind='irregular-full', originX=cx * bw, originY=cy * bl, cellWidth=bw, cellLength=bl,
                countX=countX, countY=countY, isFullSizeCell=True))
        for cx, cy, w, d in input.cells:
            if w == 1 and d == 1:
                continue
            regions.append(gridSlicing.GridRegion(
                kind='irregular-reduced', originX=cx * bw, originY=cy * bl, cellWidth=w * bw, cellLength=d * bl,
                countX=1, countY=1, isFullSizeCell=False))
        baseBodies = createBaseBodyGrid(baseInput, pitchModel, component, regions)
        combineUtils.joinBodies(binBody, commonUtils.objectCollectionFromList(baseBodies), component)

    return binBody
