import adsk.core, adsk.fusion
import json

from ... import config
from ...lib import fusion360utils as futil
from ...lib.gridfinityUtils import combineUtils
from ...lib.gridfinityUtils import geometryUtils
from ...lib.gridfinityUtils import faceUtils
from ...lib.gridfinityUtils import shellUtils
from ...lib.gridfinityUtils import commonUtils
from ...lib.gridfinityUtils import const
from ...lib.gridfinityUtils.baseGenerator import createBaseBodyPattern, cutBaseClearance
from ...lib.gridfinityUtils.baseGeneratorInput import BaseGeneratorInput
from ...lib.gridfinityUtils.binBodyGenerator import createGridfinityBinBody, uniformCompartments
from ...lib.gridfinityUtils.binBodyGeneratorInput import BinBodyGeneratorInput, BinBodyCompartmentDefinition
from ...lib.gridfinityUtils.binBodyTabGeneratorInput import BinBodyTabGeneratorInput
from ...lib.gridfinityUtils.binBodyTabGenerator import createGridfinityBinBodyTab
from ...lib.gridfinityUtils.baseplateGenerator import createGridfinityBaseplate
from ...lib.gridfinityUtils.baseplateGeneratorInput import BaseplateGeneratorInput
from ...lib.ui.unsupportedDesignTypeException import UnsupportedDesignTypeException

from .binInputState import BinInputState
from .baseplateInputState import BaseplateInputState

app = adsk.core.Application.get()

BIN_TYPE_HOLLOW = 'Hollow'
BIN_TYPE_SHELLED = 'Shelled'
BIN_TYPE_SOLID = 'Solid'

BASEPLATE_TYPE_LIGHT = 'Light'
BASEPLATE_TYPE_FULL = 'Full'
BASEPLATE_TYPE_SKELETONIZED = 'Skeletonized'
BASEPLATE_TYPE_STACKABLE = 'Stackable'

COMPARTMENTS_GRID_TYPE_UNIFORM = 'Uniform'

# Attribute group used to stamp generated (hybrid-design-intent) components with the
# form that built them, so they can later be re-adopted for editing. See
# commandGridfinityPalette.entry._handle_edit_active_component.
GENERATED_FORM_ATTR_GROUP = config.ADDIN_NAME
GENERATED_FORM_ATTR_KIND = 'kind'
GENERATED_FORM_ATTR_FORM_JSON = 'formJson'

# Visual "not finalized yet" marker for preview components.
PREVIEW_NAME_PREFIX = 'PREVIEW_'


def create_and_build(kind: str, form: dict, is_preview: bool = False):
    """Builds the requested geometry and returns the entity(ies) to track for preview cleanup:
    an Occurrence when a new component was created (hybrid design intent), or a list of the
    newly created timeline entities when building directly into the root component (Part/Assembly
    design intent, where addNewComponent is not permitted).

    is_preview=True marks the built component as not-yet-finalized (PREVIEW_ name prefix)
    -- set by Update Preview, not by Generate.
    """
    des = adsk.fusion.Design.cast(app.activeProduct)
    if des is None or des.designType == adsk.fusion.DesignTypes.DirectDesignType:
        raise UnsupportedDesignTypeException(
            'Timeline must be enabled for the generator to work, projects with disabled design history currently are not supported'
        )
    root = adsk.fusion.Component.cast(des.rootComponent)

    originalTimelineCount = des.timeline.count
    isHybrid = des.designIntent == adsk.fusion.DesignIntentTypes.HybridDesignIntentType

    newCmpOcc = None
    if isHybrid:
        # Creating internal components is only permitted in hybrid design intent;
        # Part/Assembly design-intent documents must build directly into the root component.
        newCmpOcc = adsk.fusion.Occurrences.cast(root.occurrences).addNewComponent(adsk.core.Matrix3D.create())
        component = newCmpOcc.component
    else:
        component = root

    if kind == 'bin':
        inputState = BinInputState.from_form(form)
        name = 'Gridfinity bin {}x{}x{}'.format(inputState.binLength, inputState.binWidth, int(inputState.binHeight))
        if newCmpOcc:
            newCmpOcc.component.name = name
            newCmpOcc.activate()
        build_bin(inputState, component, name)
    elif kind == 'baseplate':
        inputState = BaseplateInputState.from_form(form)
        name = 'Gridfinity baseplate {}x{}'.format(inputState.plateLength, inputState.plateWidth)
        if newCmpOcc:
            newCmpOcc.component.name = name
            newCmpOcc.activate()
        build_baseplate(inputState, component, name)
    else:
        raise ValueError(f'Unknown generator kind: {kind}')

    if newCmpOcc and is_preview:
        newCmpOcc.component.name = f'{PREVIEW_NAME_PREFIX}{name}'

    if newCmpOcc:
        attrs = newCmpOcc.component.attributes
        attrs.add(GENERATED_FORM_ATTR_GROUP, GENERATED_FORM_ATTR_KIND, kind)
        attrs.add(GENERATED_FORM_ATTR_GROUP, GENERATED_FORM_ATTR_FORM_JSON, json.dumps(form))

    if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
        group = des.timeline.timelineGroups.add(originalTimelineCount, des.timeline.count - 1)
        group.name = name

    if newCmpOcc:
        return newCmpOcc

    return [des.timeline.item(i).entity for i in range(originalTimelineCount, des.timeline.count)]


def build_baseplate(inputState: BaseplateInputState, component: adsk.fusion.Component, name: str):
    baseplateGeneratorInput = BaseplateGeneratorInput()
    baseplateGeneratorInput.baseWidth = inputState.baseWidthUnit
    baseplateGeneratorInput.baseLength = inputState.baseLengthUnit
    baseplateGeneratorInput.xyClearance = inputState.xyClearance
    baseplateGeneratorInput.baseplateWidth = inputState.plateWidth
    baseplateGeneratorInput.baseplateLength = inputState.plateLength
    baseplateGeneratorInput.hasExtendedBottom = inputState.plateType not in (BASEPLATE_TYPE_LIGHT, BASEPLATE_TYPE_STACKABLE)
    baseplateGeneratorInput.hasSkeletonizedBottom = inputState.plateType == BASEPLATE_TYPE_SKELETONIZED
    baseplateGeneratorInput.hasMagnetCutouts = inputState.hasMagnetCutouts
    baseplateGeneratorInput.magnetCutoutsDiameter = inputState.magnetDiameter
    baseplateGeneratorInput.magnetCutoutsDepth = inputState.magnetDepth
    baseplateGeneratorInput.hasScrewHoles = inputState.hasScrewHoles
    baseplateGeneratorInput.screwHolesDiameter = inputState.screwDiameter
    baseplateGeneratorInput.screwHeadCutoutDiameter = inputState.screwHeadDiameter
    baseplateGeneratorInput.hasPadding = inputState.hasSidePadding
    baseplateGeneratorInput.paddingLeft = inputState.paddingLeft
    baseplateGeneratorInput.paddingTop = inputState.paddingTop
    baseplateGeneratorInput.paddingRight = inputState.paddingRight
    baseplateGeneratorInput.paddingBottom = inputState.paddingBottom
    baseplateGeneratorInput.bottomExtensionHeight = inputState.extraBottomThickness
    baseplateGeneratorInput.binZClearance = inputState.binZClearance
    baseplateGeneratorInput.hasConnectionHoles = inputState.hasConnectionHoles
    baseplateGeneratorInput.connectionScrewHolesDiameter = inputState.connectionHoleDiameter
    baseplateGeneratorInput.cornerFilletRadius = const.BIN_CORNER_FILLET_RADIUS
    baseplateGeneratorInput.isStackable = inputState.plateType == BASEPLATE_TYPE_STACKABLE
    baseplateGeneratorInput.stackCount = inputState.stackCount
    baseplateGeneratorInput.interfaceLayerThickness = inputState.interfaceLayerThickness

    baseplateBody = createGridfinityBaseplate(baseplateGeneratorInput, component)
    if not baseplateGeneratorInput.isStackable:
        baseplateBody.name = name


def build_bin(inputState: BinInputState, component: adsk.fusion.Component, name: str):
    features: adsk.fusion.Features = component.features

    isHollow = inputState.binType == BIN_TYPE_HOLLOW
    isSolid = inputState.binType == BIN_TYPE_SOLID
    isShelled = inputState.binType == BIN_TYPE_SHELLED

    xyClearance = inputState.xyClearance

    baseGeneratorInput = BaseGeneratorInput()
    baseGeneratorInput.originPoint = geometryUtils.createOffsetPoint(
        component.originConstructionPoint.geometry,
        byX=-xyClearance,
        byY=-xyClearance,
    )
    baseGeneratorInput.baseWidth = inputState.baseWidthUnit
    baseGeneratorInput.baseLength = inputState.baseLengthUnit
    baseGeneratorInput.xyClearance = xyClearance
    baseGeneratorInput.hasScrewHoles = inputState.hasScrewHoles and not isShelled
    baseGeneratorInput.hasMagnetCutouts = inputState.hasMagnetCutouts and not isShelled
    baseGeneratorInput.hasMagnetCutoutsTabs = inputState.hasMagnetCutoutsTabs and not isShelled
    baseGeneratorInput.screwHolesDiameter = inputState.screwDiameter
    baseGeneratorInput.magnetCutoutsDiameter = inputState.magnetDiameter
    baseGeneratorInput.magnetCutoutsDepth = inputState.magnetDepth

    baseBodies: list[adsk.fusion.BRepBody] = []
    if inputState.generateBase:
        baseBodies = createBaseBodyPattern(
            baseGeneratorInput,
            inputState.binWidth,
            inputState.binLength,
            component,
        )

    binBodyInput = BinBodyGeneratorInput()
    binBodyInput.hasLip = inputState.withLip
    binBodyInput.hasLipNotches = inputState.withLipNotches
    binBodyInput.binWidth = inputState.binWidth
    binBodyInput.binLength = inputState.binLength
    binBodyInput.binHeight = inputState.binHeight
    binBodyInput.baseWidth = inputState.baseWidthUnit
    binBodyInput.baseLength = inputState.baseLengthUnit
    binBodyInput.heightUnit = inputState.heightUnit
    binBodyInput.xyClearance = xyClearance
    binBodyInput.binCornerFilletRadius = const.BIN_CORNER_FILLET_RADIUS - xyClearance
    binBodyInput.isSolid = isSolid or isShelled
    binBodyInput.wallThickness = inputState.wallThickness
    binBodyInput.hasScoop = inputState.hasScoop and isHollow
    binBodyInput.scoopMaxRadius = inputState.scoopMaxRadius
    binBodyInput.hasTab = inputState.hasTab and isHollow
    binBodyInput.tabLength = inputState.tabLength
    binBodyInput.tabWidth = inputState.tabWidth
    binBodyInput.tabPosition = inputState.tabPosition
    binBodyInput.tabOverhangAngle = inputState.tabAngle
    binBodyInput.compartmentsByX = inputState.compartmentsGridWidth
    binBodyInput.compartmentsByY = inputState.compartmentsGridLength

    if inputState.compartmentsGridType == COMPARTMENTS_GRID_TYPE_UNIFORM:
        binBodyInput.compartments = uniformCompartments(binBodyInput.compartmentsByX, binBodyInput.compartmentsByY)
    else:
        binBodyInput.compartments = [
            BinBodyCompartmentDefinition(row.positionX, row.positionY, row.width, row.length, row.depth)
            for row in inputState.compartments
        ]

    binBody: adsk.fusion.BRepBody = None

    if inputState.generateBody:
        binBody = createGridfinityBinBody(
            binBodyInput,
            component,
        )
    if inputState.generateBody or inputState.generateBase:
        cutBaseClearance(
            baseGeneratorInput,
            inputState.binWidth,
            inputState.binLength,
            component,
        )

    if inputState.generateBody and inputState.generateBase:
        toolBodies = commonUtils.objectCollectionFromList(baseBodies)
        combineFeatures = component.features.combineFeatures
        combineFeatureInput = combineFeatures.createInput(binBody, toolBodies)
        combineFeatures.add(combineFeatureInput)
        component.bRepBodies.item(0).name = name

    if isShelled and inputState.generateBody:
        combineFeatures = component.features.combineFeatures
        horizontalFaces = [face for face in binBody.faces if geometryUtils.isHorizontal(face)]
        topFace = faceUtils.maxByArea(horizontalFaces)
        if binBodyInput.hasLip:
            splitBodyFeatures = features.splitBodyFeatures
            splitBodyInput = splitBodyFeatures.createInput(
                binBody,
                topFace,
                True
            )
            splitBodies = splitBodyFeatures.add(splitBodyInput)
            bottomBody = min(splitBodies.bodies, key=lambda x: x.boundingBox.minPoint.z)
            topBody = max(splitBodies.bodies, key=lambda x: x.boundingBox.minPoint.z)
            horizontalFaces = [face for face in bottomBody.faces if geometryUtils.isHorizontal(face)]
            topFace = faceUtils.maxByArea(horizontalFaces)
            shellUtils.simpleShell([topFace], binBodyInput.wallThickness - xyClearance, component)
            toolBodies = adsk.core.ObjectCollection.create()
            toolBodies.add(topBody)
            combineAfterShellFeatureInput = combineFeatures.createInput(bottomBody, toolBodies)
            combineFeatures.add(combineAfterShellFeatureInput)
            binBody = component.bRepBodies.item(0)
        else:
            shellUtils.simpleShell([topFace], binBodyInput.wallThickness - xyClearance, component)

        if inputState.hasTab:
            compartmentTabInput = BinBodyTabGeneratorInput()
            tabOriginPoint = adsk.core.Point3D.create(
                binBodyInput.wallThickness + max(0, min(binBodyInput.tabPosition, binBodyInput.binWidth - binBodyInput.tabLength)) * binBodyInput.baseWidth,
                const.BIN_LIP_WALL_THICKNESS if binBodyInput.hasLip and binBodyInput.hasScoop else binBodyInput.wallThickness + binBodyInput.binLength * binBodyInput.baseLength - binBodyInput.wallThickness - binBodyInput.xyClearance * 2,
                (binBodyInput.binHeight - 1) * binBodyInput.heightUnit + max(0, binBodyInput.heightUnit - const.BIN_BASE_HEIGHT),
            )
            compartmentTabInput.origin = tabOriginPoint
            compartmentTabInput.length = max(0, min(binBodyInput.tabLength, binBodyInput.binWidth)) * binBodyInput.baseWidth - binBodyInput.wallThickness * 2 - binBodyInput.xyClearance * 2
            compartmentTabInput.width = binBodyInput.tabWidth
            compartmentTabInput.overhangAngle = binBodyInput.tabOverhangAngle
            compartmentTabInput.topClearance = const.BIN_TAB_TOP_CLEARANCE
            tabBody = createGridfinityBinBodyTab(compartmentTabInput, component)
            combineInput = combineFeatures.createInput(tabBody, commonUtils.objectCollectionFromList([binBody]))
            combineInput.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            combineInput.isKeepToolBodies = True
            combineFeature = combineFeatures.add(combineInput)
            tabBodies = [body for body in combineFeature.bodies if body.faces != binBody.faces]
            tabMainBody = max([body for body in tabBodies], key=lambda x: x.edges.count)
            bodiesToRemove = [body for body in tabBodies if body is not tabMainBody]
            for body in bodiesToRemove:
                component.features.removeFeatures.add(body)
            combineUtils.joinBodies(binBody, commonUtils.objectCollectionFromList([tabMainBody]), component)
