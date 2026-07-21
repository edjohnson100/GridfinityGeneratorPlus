import math
import adsk.core, adsk.fusion, traceback
import copy
import os

from . import const, commonUtils, filletUtils, combineUtils, faceUtils, extrudeUtils, sketchUtils, baseGenerator, patternUtils, shapeUtils, geometryUtils, gridSlicing
from .baseGeneratorInput import BaseGeneratorInput
from .baseplateGeneratorInput import BaseplateGeneratorInput

def createGridfinityBaseplate(input: BaseplateGeneratorInput, targetComponent: adsk.fusion.Component):
    features = targetComponent.features
    # half-unit edge support: build a grid model from the core unit counts and the
    # 4 half-edge flags, then decompose into up to 9 regions (center/edge-strips/
    # corners) - see gridSlicing.py. Degenerates to a single center region (this
    # function's original behavior, unchanged) when no half-edges are configured.
    targetOrigin = targetComponent.originConstructionPoint.geometry
    coreWidthCount = input.baseplateWidth
    coreLengthCount = input.baseplateLength
    gridModel = gridSlicing.buildGridModel(
        coreWidthCount, coreLengthCount,
        input.baseWidth, input.baseLength,
        input.hasHalfLeft, input.hasHalfRight, input.hasHalfFront, input.hasHalfBack,
    )
    allRegions = gridSlicing.enumerateGridRegions(gridModel)
    centerRegion = next((r for r in allRegions if r.kind == 'center'), None)
    edgeAndCornerRegions = [r for r in allRegions if r.kind != 'center']

    cuttingTools: list[adsk.fusion.BRepBody] = []
    extraCutoutBodies: list[adsk.fusion.BRepBody] = []
    connectionHoleYTool = None
    connectionHoleXTool = None
    # only used for the connection-hole mirror planes below, which are skipped
    # unless centerRegion exists (i.e. connectionHoleYTool/XTool get set) -
    # default is never actually read otherwise
    centerOriginPoint = targetOrigin

    if centerRegion is not None:
        # the core grid's one representative full cell - carries skeletonized-
        # bottom/magnet-groove/connection-hole extras (decision: half/quarter
        # cells never get these, only true 1x1 cells do), then gets patterned
        # across the core coreWidthCount x coreLengthCount grid below
        centerOriginPoint = geometryUtils.createOffsetPoint(targetOrigin, byX=centerRegion.originX, byY=centerRegion.originY)

        cutoutInput = BaseGeneratorInput()
        cutoutInput.xyClearance = input.xyClearance
        # Oversized by 2*xyClearance total (baseWidth/Length below) so the cutout has
        # xyClearance of slack around a same-size bin foot on every side; the opening must
        # therefore be offset -xyClearance (not -2*xyClearance) from the nominal cell origin
        # to actually center that slack evenly front/back and left/right - offsetting by the
        # full -2*xyClearance left the opening shifted toward the front/left, measurably
        # closer to the outer wall on the front/left than the back/right.
        cutoutInput.originPoint = geometryUtils.createOffsetPoint(
            centerOriginPoint,
            byX=-cutoutInput.xyClearance,
            byY=-cutoutInput.xyClearance,
        )
        cutoutInput.baseWidth = input.baseWidth + cutoutInput.xyClearance * 2
        cutoutInput.baseLength = input.baseLength + cutoutInput.xyClearance * 2
        cutoutInput.cornerFilletRadius = input.cornerFilletRadius + cutoutInput.xyClearance
        baseBody = baseGenerator.createSingleGridfinityBaseBody(cutoutInput, targetComponent)
        cuttingTools.append(baseBody)

        holeCenterPoint = adsk.core.Point3D.create(
            centerOriginPoint.x + const.DIMENSION_SCREW_HOLES_OFFSET - input.xyClearance,
            centerOriginPoint.y + const.DIMENSION_SCREW_HOLES_OFFSET - input.xyClearance,
            0
        )

        if input.hasSkeletonizedBottom:
            centerCutoutSketch,centerCutoutSketchCircle = baseGenerator.createCircleAtPointSketch(
                faceUtils.getBottomFace(baseBody),
                input.magnetCutoutsDiameter / 2,
                holeCenterPoint,
                targetComponent
            )
            centerCutoutSketch.name = "center bottom cutout"
            sketchUtils.convertToConstruction(centerCutoutSketch.sketchCurves)
            sketchCurves = centerCutoutSketch.sketchCurves
            dimensions = centerCutoutSketch.sketchDimensions
            constraints = centerCutoutSketch.geometricConstraints
            sketchLines = sketchCurves.sketchLines
            screwHoleCircle = sketchCurves.sketchCircles.item(0)
            arcStartingPoint = screwHoleCircle.centerSketchPoint.geometry.asVector()
            arcStartingPoint.add(adsk.core.Vector3D.create(0, max(input.magnetCutoutsDiameter, input.screwHeadCutoutDiameter) / 2 + 0.1, 0))
            arc = sketchCurves.sketchArcs.addByCenterStartSweep(
                screwHoleCircle.centerSketchPoint,
                arcStartingPoint.asPoint(),
                math.radians(90),
            )

            # Edge/midpoint selection is anchored entirely to the screw-hole circle's own
            # sketch-local position (already correctly placed via modelToSketchSpace, so
            # it's translation-invariant) rather than absolute sketch (0,0) or hardcoded
            # +/-half-width offsets - a plain "nearest to sketch-local zero" comparison
            # silently picked the wrong edge (and the hardcoded offsets landed outside the
            # cell) once the center cell no longer sits at the true origin, which only
            # happens when a leading half-edge (Left/Front) is checked.
            circleCenter = screwHoleCircle.centerSketchPoint.geometry
            verticalLines = [line for line in sketchLines if sketchUtils.isVertical(line)]
            horizontalLines = [line for line in sketchLines if sketchUtils.isHorizontal(line)]
            verticalEdgeLine = min(verticalLines, key=lambda x: abs(x.startSketchPoint.geometry.x - circleCenter.x))
            horizontalEdgeLine = min(horizontalLines, key=lambda x: abs(x.startSketchPoint.geometry.y - circleCenter.y))
            farVerticalEdgeLine = max(verticalLines, key=lambda x: abs(x.startSketchPoint.geometry.x - circleCenter.x))
            farHorizontalEdgeLine = max(horizontalLines, key=lambda x: abs(x.startSketchPoint.geometry.y - circleCenter.y))
            # stop xyClearance short of the true midpoint (not exactly at it), matching
            # the original design's small structural web where the 4 rotated L-cutouts
            # meet at the cell's center, rather than meeting/overlapping exactly there
            nearVerticalX = verticalEdgeLine.startSketchPoint.geometry.x
            farVerticalX = farVerticalEdgeLine.startSketchPoint.geometry.x
            nearHorizontalY = horizontalEdgeLine.startSketchPoint.geometry.y
            farHorizontalY = farHorizontalEdgeLine.startSketchPoint.geometry.y
            midX = nearVerticalX + math.copysign(abs(farVerticalX - nearVerticalX) / 2 - input.xyClearance, farVerticalX - nearVerticalX)
            midY = nearHorizontalY + math.copysign(abs(farHorizontalY - nearHorizontalY) / 2 - input.xyClearance, farHorizontalY - nearHorizontalY)

            line1 = sketchLines.addByTwoPoints(arc.startSketchPoint, adsk.core.Point3D.create(verticalEdgeLine.startSketchPoint.geometry.x, arc.startSketchPoint.geometry.y, 0))
            line2 = sketchLines.addByTwoPoints(line1.endSketchPoint, adsk.core.Point3D.create(line1.endSketchPoint.geometry.x, midY, 0))
            line3 = sketchLines.addByTwoPoints(line2.endSketchPoint, adsk.core.Point3D.create(midX, midY, 0))
            line4 = sketchLines.addByTwoPoints(line3.endSketchPoint, adsk.core.Point3D.create(line3.endSketchPoint.geometry.x, horizontalEdgeLine.startSketchPoint.geometry.y, 0))
            line5 = sketchLines.addByTwoPoints(line4.endSketchPoint, adsk.core.Point3D.create(arc.endSketchPoint.geometry.x, line4.endSketchPoint.geometry.y, 0))
            line6 = sketchLines.addByTwoPoints(line5.endSketchPoint, arc.endSketchPoint)

            constraints.addCoincident(line1.endSketchPoint, verticalEdgeLine)
            constraints.addCoincident(line6.startSketchPoint, horizontalEdgeLine)
            constraints.addCoincident(screwHoleCircle.centerSketchPoint, arc.centerSketchPoint)
            constraints.addHorizontal(line1)
            constraints.addPerpendicular(line1, line2)
            constraints.addPerpendicular(line2, line3)
            constraints.addPerpendicular(line3, line4)
            constraints.addPerpendicular(line4, line5)
            constraints.addPerpendicular(line5, line6)
            constraints.addTangent(arc, line1)
            constraints.addEqual(line1, line6)
            constraints.addEqual(line2, line5)
            dimensions.addRadialDimension(arc, arc.endSketchPoint.geometry, True)
            dimensions.addDistanceDimension(
                arc.endSketchPoint,
                line3.endSketchPoint,
                adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                line2.endSketchPoint.geometry
                )

            centerCutoutExtrudeFeature = extrudeUtils.simpleDistanceExtrude(
                centerCutoutSketch.profiles.item(0),
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                input.bottomExtensionHeight,
                adsk.fusion.ExtentDirections.PositiveExtentDirection,
                [],
                targetComponent,
            )

            constructionAxisInput: adsk.fusion.ConstructionAxisInput = targetComponent.constructionAxes.createInput()
            constructionAxisInput.setByNormalToFaceAtPoint(
                faceUtils.getBottomFace(baseBody),
                line3.endSketchPoint,
            )
            constructionAxis = targetComponent.constructionAxes.add(constructionAxisInput)
            constructionAxis.isLightBulbOn = False

            centerCutoutPattern = patternUtils.circPattern(
                commonUtils.objectCollectionFromList(centerCutoutExtrudeFeature.bodies),
                constructionAxis,
                4,
                targetComponent,
            )
            centerCutoutBody = centerCutoutExtrudeFeature.bodies.item(0)
            combineUtils.joinBodies(
                centerCutoutBody,
                commonUtils.objectCollectionFromList([body for body in list(centerCutoutPattern.bodies) if not body.name == centerCutoutBody.name]),
                targetComponent,
            )
            extraCutoutBodies.append(centerCutoutBody)
            if input.hasConnectionHoles:
                connectionHoleFaceY = min([face for face in centerCutoutBody.faces if faceUtils.isYNormal(face)], key=lambda x: x.boundingBox.minPoint.y)
                connectionHoleYTool = createConnectionHoleTool(connectionHoleFaceY, input.connectionScrewHolesDiameter / 2, input.baseWidth / 2, targetComponent)
                connectionHoleFaceX = min([face for face in centerCutoutBody.faces if faceUtils.isXNormal(face)], key=lambda x: x.boundingBox.minPoint.x)
                connectionHoleXTool = createConnectionHoleTool(connectionHoleFaceX, input.connectionScrewHolesDiameter / 2, input.baseWidth / 2, targetComponent)

        holeCuttingBodies: list[adsk.fusion.BRepBody] = []

        if input.hasExtendedBottom and input.hasMagnetCutouts:
            magnetSocketBody = shapeUtils.simpleCylinder(
                faceUtils.getBottomFace(baseBody),
                0,
                input.magnetCutoutsDepth,
                input.magnetCutoutsDiameter / 2,
                holeCenterPoint,
                targetComponent,
            )
            holeCuttingBodies.append(magnetSocketBody)

        if input.hasExtendedBottom and input.hasScrewHoles:
            screwHoleBody = shapeUtils.simpleCylinder(
                faceUtils.getBottomFace(baseBody),
                0,
                input.bottomExtensionHeight,
                input.screwHolesDiameter / 2,
                holeCenterPoint,
                targetComponent,
            )
            holeCuttingBodies.append(screwHoleBody)

            screwHeadHeight = const.DIMENSION_SCREW_HEAD_CUTOUT_OFFSET_HEIGHT + (input.screwHeadCutoutDiameter - input.screwHolesDiameter) / 2
            screwHeadBody = shapeUtils.simpleCylinder(
                faceUtils.getBottomFace(screwHoleBody),
                -screwHeadHeight,
                screwHeadHeight,
                input.screwHeadCutoutDiameter / 2,
                holeCenterPoint,
                targetComponent,
            )
            filletUtils.createChamfer(
                commonUtils.objectCollectionFromList(faceUtils.getTopFace(screwHeadBody).edges),
                (input.screwHeadCutoutDiameter - input.screwHolesDiameter) / 2,
                targetComponent,
            )
            holeCuttingBodies.append(screwHeadBody)

        if len(holeCuttingBodies) > 0:
            patternSpacingX = input.baseWidth - const.DIMENSION_SCREW_HOLES_OFFSET * 2
            patternSpacingY = input.baseLength - const.DIMENSION_SCREW_HOLES_OFFSET * 2
            magnetScrewCutoutsPattern = patternUtils.recPattern(
                commonUtils.objectCollectionFromList(holeCuttingBodies),
                (targetComponent.xConstructionAxis, targetComponent.yConstructionAxis),
                (patternSpacingX, patternSpacingY),
                (2, 2),
                targetComponent
            )
            extraCutoutBodies = extraCutoutBodies + holeCuttingBodies + list(magnetScrewCutoutsPattern.bodies)

        if len(extraCutoutBodies) > 0:
            combineUtils.joinBodies(
                baseBody,
                commonUtils.objectCollectionFromList(extraCutoutBodies),
                targetComponent,
            )

        # replicate the center cell across the core coreWidthCount x coreLengthCount grid
        rectangularPatternFeatures: adsk.fusion.RectangularPatternFeatures = features.rectangularPatternFeatures
        patternInputBodies = adsk.core.ObjectCollection.create()
        patternInputBodies.add(baseBody)
        patternInput = rectangularPatternFeatures.createInput(patternInputBodies,
            targetComponent.xConstructionAxis,
            adsk.core.ValueInput.createByReal(coreWidthCount),
            adsk.core.ValueInput.createByReal(input.baseWidth),
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        patternInput.directionTwoEntity = targetComponent.yConstructionAxis
        patternInput.quantityTwo = adsk.core.ValueInput.createByReal(coreLengthCount)
        patternInput.distanceTwo = adsk.core.ValueInput.createByReal(input.baseLength)
        rectangularPattern = rectangularPatternFeatures.add(patternInput)
        cuttingTools = cuttingTools + list(rectangularPattern.bodies)

    if edgeAndCornerRegions:
        # plain half/quarter cutout cells for the half-unit edges/corners - no
        # skeletonized-bottom/magnet-groove/connection-hole extras (decision #1:
        # magnet/screw cutouts never apply to non-full-size cells)
        reducedCutoutInput = BaseGeneratorInput()
        reducedCutoutInput.xyClearance = input.xyClearance
        # See the matching comment on cutoutInput.originPoint above - same centering fix.
        reducedCutoutInput.originPoint = geometryUtils.createOffsetPoint(
            targetOrigin,
            byX=-reducedCutoutInput.xyClearance,
            byY=-reducedCutoutInput.xyClearance,
        )
        reducedCutoutInput.baseWidth = input.baseWidth + reducedCutoutInput.xyClearance * 2
        reducedCutoutInput.baseLength = input.baseLength + reducedCutoutInput.xyClearance * 2
        reducedCutoutInput.cornerFilletRadius = input.cornerFilletRadius + reducedCutoutInput.xyClearance
        reducedCutoutInput.isReducedCell = True
        cuttingTools = cuttingTools + baseGenerator.createBaseBodyGrid(reducedCutoutInput, gridModel, targetComponent, regions=edgeAndCornerRegions)

    # create baseplate body
    baseplateTrueWidth = gridModel.totalWidth - input.xyClearance * 2
    baseplateTrueLength = gridModel.totalLength - input.xyClearance * 2
    binInterfaceBody = shapeUtils.simpleBox(
        targetComponent.xYConstructionPlane,
        0,
        gridModel.totalWidth - input.xyClearance * 2,
        gridModel.totalLength - input.xyClearance * 2,
        -const.BIN_BASE_HEIGHT,
        targetComponent.originConstructionPoint.geometry,
        targetComponent,
    )

    if input.binZClearance > 0:
        binZClearance = shapeUtils.simpleBox(
                targetComponent.xYConstructionPlane,
                0,
                baseplateTrueWidth + input.paddingLeft + input.paddingRight,
                baseplateTrueLength + input.paddingBottom + input.paddingTop,
                -input.binZClearance,
                geometryUtils.createOffsetPoint(
                    targetComponent.originConstructionPoint.geometry,
                    byX=-input.paddingLeft,
                    byY=-input.paddingBottom
                ),
                targetComponent
            )
        binZClearance.name = "Top negative volume"
        cuttingTools.append(binZClearance)

    if input.hasPadding:
        paddingHeigth = const.BIN_BASE_HEIGHT
        mergeTools = []
        if input.paddingLeft > 0:
            paddingLeftBody = shapeUtils.simpleBox(
                targetComponent.xYConstructionPlane,
                0,
                input.paddingLeft,
                baseplateTrueLength + input.paddingBottom + input.paddingTop,
                -paddingHeigth,
                geometryUtils.createOffsetPoint(
                    targetComponent.originConstructionPoint.geometry,
                    byX=-input.paddingLeft,
                    byY=-input.paddingBottom
                ),
                targetComponent
            )
            paddingLeftBody.name = "Padding left"
            mergeTools.append(paddingLeftBody)
        if input.paddingTop > 0:
            paddingTopBody = shapeUtils.simpleBox(
                targetComponent.xYConstructionPlane,
                0,
                baseplateTrueWidth + input.paddingLeft + input.paddingRight,
                input.paddingTop,
                -paddingHeigth,
                geometryUtils.createOffsetPoint(
                    targetComponent.originConstructionPoint.geometry,
                    byX=-input.paddingLeft,
                    byY=baseplateTrueLength
                ),
                targetComponent
            )
            paddingTopBody.name = "Padding top"
            mergeTools.append(paddingTopBody)
        if input.paddingRight > 0:
            paddingRightBody = shapeUtils.simpleBox(
                targetComponent.xYConstructionPlane,
                0,
                input.paddingRight,
                baseplateTrueLength + input.paddingTop + input.paddingBottom,
                -paddingHeigth,
                geometryUtils.createOffsetPoint(
                    targetComponent.originConstructionPoint.geometry,
                    byX=baseplateTrueWidth,
                    byY=-input.paddingBottom
                ),
                targetComponent
            )
            paddingRightBody.name = "Padding right"
            mergeTools.append(paddingRightBody)
        if input.paddingBottom > 0:
            paddingBottomBody = shapeUtils.simpleBox(
                targetComponent.xYConstructionPlane,
                0,
                baseplateTrueWidth + input.paddingLeft + input.paddingRight,
                input.paddingBottom,
                -paddingHeigth,
                geometryUtils.createOffsetPoint(
                    targetComponent.originConstructionPoint.geometry,
                    byX=-input.paddingLeft,
                    byY=-input.paddingBottom
                ),
                targetComponent
            )
            paddingBottomBody.name = "Padding bottom"
            mergeTools.append(paddingBottomBody)
        if len(mergeTools) > 0:
            paddingCombineFeature = combineUtils.joinBodies(
                binInterfaceBody,
                commonUtils.objectCollectionFromList(mergeTools),
                targetComponent,
            )
            paddingCombineFeature.name = "Combine base with padding bodies"
            binInterfaceBody = paddingCombineFeature.bodies.item(0)

    cornerFillet = filletUtils.filletEdgesByLength(
        binInterfaceBody.faces,
        input.cornerFilletRadius - input.xyClearance,
        const.BIN_BASE_HEIGHT,
        targetComponent,
        )
    cornerFillet.name = "Round outer corners"
    
    if input.hasExtendedBottom:
        baseplateBottomLayer = extrudeUtils.simpleDistanceExtrude(
            faceUtils.getBottomFace(binInterfaceBody),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            input.bottomExtensionHeight,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
            [],
            targetComponent,
        )
        baseplateBottomLayerBody = baseplateBottomLayer.bodies.item(0)
        combineUtils.joinBodies(binInterfaceBody, commonUtils.objectCollectionFromList([baseplateBottomLayerBody]), targetComponent)

    bottomChamfer = filletUtils.chamferEdgesByLength(
        [faceUtils.getBottomFace(binInterfaceBody)],
        0.05,
        baseplateTrueLength + (input.paddingTop + input.paddingBottom if input.hasPadding else 0),
        const.BIN_CORNER_FILLET_RADIUS * 3,
        targetComponent,
    )
    bottomChamfer.name = "Bottom chamfer"

    if not connectionHoleYTool is None and not connectionHoleXTool is None:
        holeToolsXFeature = patternUtils.recPattern(
            commonUtils.objectCollectionFromList(connectionHoleXTool.bodies),
            (targetComponent.xConstructionAxis, targetComponent.yConstructionAxis),
            (input.baseWidth, input.baseLength),
            (1, input.baseplateLength),
            targetComponent
        )
        connectionHoleXToolList = list(connectionHoleXTool.bodies) + list(holeToolsXFeature.bodies)

        holeToolsYFeature = patternUtils.recPattern(
            commonUtils.objectCollectionFromList(connectionHoleYTool.bodies),
            (targetComponent.xConstructionAxis, targetComponent.yConstructionAxis),
            (input.baseLength, input.baseLength),
            (input.baseplateWidth, 1),
            targetComponent
        )
        connectionHoleYToolList = list(connectionHoleYTool.bodies) + list(holeToolsYFeature.bodies)

        constructionPlaneXZInput: adsk.fusion.ConstructionPlaneInput = targetComponent.constructionPlanes.createInput()
        constructionPlaneXZInput.setByOffset(targetComponent.xZConstructionPlane, adsk.core.ValueInput.createByReal(centerOriginPoint.y + input.baseplateLength * input.baseLength / 2 - input.xyClearance))
        constructionPlaneXZ = targetComponent.constructionPlanes.add(constructionPlaneXZInput)
        constructionPlaneXZ.isLightBulbOn = False

        constructionPlaneYZInput: adsk.fusion.ConstructionPlaneInput = targetComponent.constructionPlanes.createInput()
        constructionPlaneYZInput.setByOffset(targetComponent.yZConstructionPlane, adsk.core.ValueInput.createByReal(centerOriginPoint.x + input.baseplateWidth * input.baseWidth / 2 - input.xyClearance))
        constructionPlaneYZ = targetComponent.constructionPlanes.add(constructionPlaneYZInput)
        constructionPlaneYZ.isLightBulbOn = False

        mirrorConnectionHolesYZInput = features.mirrorFeatures.createInput(commonUtils.objectCollectionFromList(connectionHoleXToolList), constructionPlaneYZ)
        mirrorConnectionHolesYZ = features.mirrorFeatures.add(mirrorConnectionHolesYZInput)

        mirrorConnectionHolesXZInput = features.mirrorFeatures.createInput(commonUtils.objectCollectionFromList(connectionHoleYToolList), constructionPlaneXZ)
        mirrorConnectionHolesXZ = features.mirrorFeatures.add(mirrorConnectionHolesXZInput)

        cuttingTools = cuttingTools + list(mirrorConnectionHolesYZ.bodies) + list(mirrorConnectionHolesXZ.bodies) + connectionHoleYToolList + connectionHoleXToolList


    # cut everything
    toolBodies = commonUtils.objectCollectionFromList(cuttingTools)
    finalCut = combineUtils.cutBody(
        binInterfaceBody,
        toolBodies,
        targetComponent,
    )
    finalCut.name = "Final baseplate cut"

    # mid-height construction plane, shared by the Stackable split/mirror step below
    # and the DXF sketch step, both of which need to reference the same plane
    bbox = binInterfaceBody.boundingBox
    midZ = (bbox.minPoint.z + bbox.maxPoint.z) / 2

    midplaneInput: adsk.fusion.ConstructionPlaneInput = targetComponent.constructionPlanes.createInput()
    midplaneInput.setByOffset(targetComponent.xYConstructionPlane, adsk.core.ValueInput.createByReal(midZ))
    midplane = targetComponent.constructionPlanes.add(midplaneInput)
    midplane.name = "Baseplate midplane"
    midplane.isLightBulbOn = False

    if input.generateDxfSketch:
        # captures the lone, pre-symmetric/pre-stacking baseplate body, per user request
        dxfSketch = targetComponent.sketches.add(midplane)
        dxfSketch.projectCutEdges(binInterfaceBody)
        dxfSketch.name = f"DXF baseplate {input.baseplateLength}x{input.baseplateWidth}"

    if input.isStackable:
        splitBodyFeatures = features.splitBodyFeatures
        splitBodyInput = splitBodyFeatures.createInput(binInterfaceBody, midplane, True)
        splitBodies = splitBodyFeatures.add(splitBodyInput)
        if splitBodies.bodies.count != 2:
            raise RuntimeError("Stackable baseplate split did not produce exactly two bodies; the grid geometry may be incompatible with mid-height splitting.")
        bottomBody = min(splitBodies.bodies, key=lambda x: x.boundingBox.minPoint.z)
        topBody = max(splitBodies.bodies, key=lambda x: x.boundingBox.minPoint.z)

        targetComponent.features.removeFeatures.add(bottomBody)

        mirrorInput = features.mirrorFeatures.createInput(commonUtils.objectCollectionFromList([topBody]), midplane)
        mirrorFeature = features.mirrorFeatures.add(mirrorInput)
        mirroredBody = mirrorFeature.bodies.item(0)

        symmetricJoinFeature = combineUtils.joinBodies(
            topBody,
            commonUtils.objectCollectionFromList([mirroredBody]),
            targetComponent,
        )
        symmetricJoinFeature.name = "Baseplate stack symmetric join"
        binInterfaceBody = symmetricJoinFeature.bodies.item(0)

        if input.stackCount > 1:
            stackBbox = binInterfaceBody.boundingBox
            plateHeight = stackBbox.maxPoint.z - stackBbox.minPoint.z
            spacing = plateHeight + input.interfaceLayerThickness

            interfaceLayerExtrude = extrudeUtils.simpleDistanceExtrude(
                faceUtils.getTopFace(binInterfaceBody),
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                input.interfaceLayerThickness,
                adsk.fusion.ExtentDirections.PositiveExtentDirection,
                [],
                targetComponent,
            )
            interfaceLayerBody = interfaceLayerExtrude.bodies.item(0)

            _applyInterfaceLayerAppearance(binInterfaceBody, interfaceLayerBody, targetComponent)

            binInterfaceBody.name = "Baseplate_01"
            interfaceLayerBody.name = "Interface_01"

            baseplatePattern = patternUtils.linearPattern(
                commonUtils.objectCollectionFromList([binInterfaceBody]),
                targetComponent.zConstructionAxis,
                input.stackCount,
                spacing,
                targetComponent,
            )
            for i, body in enumerate(baseplatePattern.bodies, start=2):
                body.name = f"Baseplate_{i:02d}"

            interfaceLayerPattern = patternUtils.linearPattern(
                commonUtils.objectCollectionFromList([interfaceLayerBody]),
                targetComponent.zConstructionAxis,
                input.stackCount - 1,
                spacing,
                targetComponent,
            )
            for i, body in enumerate(interfaceLayerPattern.bodies, start=2):
                body.name = f"Interface_{i:02d}"
        else:
            binInterfaceBody.name = "Baseplate"

    return binInterfaceBody


def _applyInterfaceLayerAppearance(
    baseplateBody: adsk.fusion.BRepBody,
    interfaceLayerBody: adsk.fusion.BRepBody,
    targetComponent: adsk.fusion.Component,
    ):
    # Applied to the seed body only; the rectangular pattern copies inherit it automatically.
    app = adsk.core.Application.get()
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        sourceAppearance = baseplateBody.appearance or targetComponent.appearance
        if sourceAppearance is None:
            library = app.materialLibraries.itemByName('Fusion 360 Appearance Library')
            sourceAppearance = library.appearances.itemByName('Plastic - Matte (White)') if library else None
        if sourceAppearance is None:
            return

        appearanceName = 'Gridfinity interface layer'
        interfaceAppearance = design.appearances.itemByName(appearanceName)
        if interfaceAppearance is None:
            interfaceAppearance = design.appearances.addByCopy(sourceAppearance, appearanceName)
        colorProp = adsk.core.ColorProperty.cast(interfaceAppearance.appearanceProperties.itemByName('Color'))
        if colorProp:
            colorProp.value = adsk.core.Color.create(255, 127, 0, 0)
        interfaceLayerBody.appearance = interfaceAppearance
    except Exception:
        app.log(f'Failed to apply interface layer appearance:\n{traceback.format_exc()}')

def createConnectionHoleTool(connectionHoleFace: adsk.fusion.BRepFace, diameter: float, depth: float, targetComponent: adsk.fusion.Component):
    connectionHoleSketch: adsk.fusion.Sketch = targetComponent.sketches.add(connectionHoleFace)
    connectionHoleSketch.name = "side connector hole"
    sketchCurves = connectionHoleSketch.sketchCurves
    dimensions = connectionHoleSketch.sketchDimensions
    constraints = connectionHoleSketch.geometricConstraints
    sketchUtils.convertToConstruction(sketchCurves)
    [sketchHorizontalEdge1, sketchHorizontalEdge2] = [line for line in sketchCurves.sketchLines if sketchUtils.isHorizontal(line)]
    line1 = sketchCurves.sketchLines.addByTwoPoints(sketchHorizontalEdge1.startSketchPoint.geometry, sketchHorizontalEdge2.endSketchPoint.geometry)
    line1.isConstruction = True
    constraints.addMidPoint(line1.startSketchPoint, sketchHorizontalEdge1)
    constraints.addMidPoint(line1.endSketchPoint, sketchHorizontalEdge2)
    
    circle = sketchCurves.sketchCircles.addByCenterRadius(
        connectionHoleSketch.originPoint.geometry,
        diameter
    )
    constraints.addMidPoint(circle.centerSketchPoint, line1)
    dimensions.addRadialDimension(circle, line1.startSketchPoint.geometry, True)
    connectionHoleTool = extrudeUtils.simpleDistanceExtrude(
        connectionHoleSketch.profiles.item(0),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        depth,
        adsk.fusion.ExtentDirections.PositiveExtentDirection,
        [],
        targetComponent,
    )
    return connectionHoleTool