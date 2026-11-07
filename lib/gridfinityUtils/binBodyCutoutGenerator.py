import adsk.core, adsk.fusion, traceback
import os
import math

from ...lib.gridfinityUtils import geometryUtils
from ...lib import fusion360utils as futil
from ...lib.gridfinityUtils import filletUtils
from . import const, combineUtils, faceUtils, commonUtils, sketchUtils, extrudeUtils, baseGenerator, edgeUtils
from .baseGeneratorInput import BaseGeneratorInput
from .binBodyCutoutGeneratorInput import BinBodyCutoutGeneratorInput
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface

def getInnerCutoutScoopFace(
    innerCutout: adsk.fusion.BRepBody
    ) -> tuple[adsk.fusion.BRepFace, adsk.fusion.BRepFace]:
    innerCutoutYNormalFaces = [face for face in innerCutout.faces if faceUtils.isYNormal(face)]
    scoopFace = min(innerCutoutYNormalFaces, key=lambda x: x.boundingBox.minPoint.y)
    oppositeFace = max(innerCutoutYNormalFaces, key=lambda x: x.boundingBox.minPoint.y)
    return (scoopFace, oppositeFace)

def getInnerCutoutScoopEdges(
    innerCutout: adsk.fusion.BRepBody,
    scoopSides: set,
    ) -> list[adsk.fusion.BRepEdge]:
    # Must be called on the un-filleted box: each side is a planar wall face.
    yFaces = [face for face in innerCutout.faces if faceUtils.isYNormal(face)]
    xFaces = [face for face in innerCutout.faces if faceUtils.isXNormal(face)]
    sideFaces = {
        'front': min(yFaces, key=lambda x: x.boundingBox.minPoint.y),
        'back': max(yFaces, key=lambda x: x.boundingBox.minPoint.y),
        'left': min(xFaces, key=lambda x: x.boundingBox.minPoint.x),
        'right': max(xFaces, key=lambda x: x.boundingBox.minPoint.x),
    }
    return [faceUtils.getBottomHorizontalEdge(sideFaces[side].edges) for side in ('front', 'left', 'back', 'right') if side in scoopSides]

def createGridfinityBinBodyCutout(
    input: BinBodyCutoutGeneratorInput,
    targetComponent: adsk.fusion.Component,
):

    cutoutPlaneInput: adsk.fusion.ConstructionPlaneInput = targetComponent.constructionPlanes.createInput()
    cutoutPlaneInput.setByOffset(
        targetComponent.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(input.origin.z)
    )
    cutoutConstructionPlane = targetComponent.constructionPlanes.add(cutoutPlaneInput)
    innerCutoutSketch: adsk.fusion.Sketch = targetComponent.sketches.add(cutoutConstructionPlane)
    innerCutoutSketch.name = 'Inner cutout sketch'
    sketchUtils.createRectangle(
        input.width,
        input.length,
        adsk.core.Point3D.create(input.origin.x, input.origin.y, 0),
        innerCutoutSketch,
    )

    innerCutout = extrudeUtils.simpleDistanceExtrude(
        innerCutoutSketch.profiles.item(0),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        input.height,
        adsk.fusion.ExtentDirections.NegativeExtentDirection,
        [],
        targetComponent,
    )
    innerCutout.name = 'Inner cutout extrude'
    innerCutoutBody = innerCutout.bodies.item(0)
    innerCutoutBody.name = 'Inner cutout'

    # scoop
    scoopSides = input.scoopSides if input.hasScoop else set()
    if scoopSides:
        # All selected sides are filleted in a single feature so corners blend.
        scoopEdges = getInnerCutoutScoopEdges(innerCutoutBody, scoopSides)
        scoopMaxRadius = min(input.scoopMaxRadius, input.height) if min(input.scoopMaxRadius, input.height) >= input.filletRadius else input.filletRadius
        filletUtils.createFillet(
            scoopEdges,
            scoopMaxRadius,
            False,
            targetComponent
        )
    # fillet inner cutout
    # A full-depth scoop (radius >= depth) consumes the wall face entirely, so
    # don't assume any particular planar wall (or vertical edge) still exists.
    innerCutoutVerticalFaces = faceUtils.getVerticalEdges(innerCutoutBody.faces)
    if innerCutoutVerticalFaces:
        filletUtils.createFillet(
            innerCutoutVerticalFaces,
            input.filletRadius,
            True,
            targetComponent
        )
    # The back bottom edge is already rounded when the back is scooped.
    if input.hasBottomFillet and 'back' not in scoopSides:
        # recalculate faces after fillet
        backFaces = [face for face in innerCutoutBody.faces if faceUtils.isYNormal(face)]
        if backFaces:
            innerCutoputScoopOppositeFace = max(backFaces, key=lambda x: x.boundingBox.minPoint.y)
            scoopOppositeEdge = faceUtils.getBottomHorizontalEdge(innerCutoputScoopOppositeFace.edges)

            filletUtils.createFillet(
                [scoopOppositeEdge],
                input.filletRadius,
                True,
                targetComponent
            )

    return innerCutoutBody
