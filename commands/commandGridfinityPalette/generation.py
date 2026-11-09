import adsk.core, adsk.fusion
import json
import time
import traceback

from ... import config
from ...lib import fusion360utils as futil
from ...lib.gridfinityUtils import combineUtils
from ...lib.gridfinityUtils import geometryUtils
from ...lib.gridfinityUtils import faceUtils
from ...lib.gridfinityUtils import shellUtils
from ...lib.gridfinityUtils import commonUtils
from ...lib.gridfinityUtils import const
from ...lib.gridfinityUtils.baseGenerator import createBaseBodyGrid
from ...lib.gridfinityUtils.baseGeneratorInput import BaseGeneratorInput
from ...lib.gridfinityUtils import gridSlicing
from ...lib.gridfinityUtils.binIrregularGenerator import BinIrregularGeneratorInput, createIrregularBin
from ...lib.gridfinityUtils.binBodyGenerator import createGridfinityBinBody, uniformCompartments
from ...lib.gridfinityUtils.binBodyGeneratorInput import BinBodyGeneratorInput, BinBodyCompartmentDefinition
from ...lib.gridfinityUtils.binBodyTabGeneratorInput import BinBodyTabGeneratorInput
from ...lib.gridfinityUtils.binBodyTabGenerator import createGridfinityBinBodyTab
from ...lib.gridfinityUtils.baseplateGenerator import createGridfinityBaseplate
from ...lib.gridfinityUtils.baseplateGeneratorInput import BaseplateGeneratorInput
from ...lib.ui.unsupportedDesignTypeException import UnsupportedDesignTypeException

from . import drawerLayout
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
    elif kind == 'drawer':
        if newCmpOcc is None:
            raise UnsupportedDesignTypeException('Drawer layouts need Hybrid design intent (they are built from nested components)')
        name = 'Gridfinity drawer'
        newCmpOcc.component.name = name
        newCmpOcc.activate()
        try:
            build_drawer(form, newCmpOcc)
        except DrawerBuildCancelled:
            # Remove the half-built drawer so Cancel leaves the design as it was.
            try:
                newCmpOcc.deleteMe()
            except Exception:
                futil.log(f'drawer: could not remove cancelled drawer: {traceback.format_exc()}')
            raise
    else:
        raise ValueError(f'Unknown generator kind: {kind}')

    if newCmpOcc:
        _hide_sketches(newCmpOcc.component)

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


def promote_preview(occurrenceToken: str, kind: str, form: dict) -> bool:
    """If the tracked preview component was built from exactly this `kind` and `form`, finalizes
    it in place (drops the PREVIEW_ prefix) and returns True, so Generate doesn't have to rebuild
    geometry that already exists. Returns False (touching nothing) if anything doesn't match."""
    des = adsk.fusion.Design.cast(app.activeProduct)
    if des is None or not occurrenceToken:
        return False
    entities = des.findEntityByToken(occurrenceToken)
    if not entities or len(entities) == 0:
        return False
    occ = adsk.fusion.Occurrence.cast(entities[0])
    if occ is None:
        return False
    comp = occ.component
    attrKind = comp.attributes.itemByName(GENERATED_FORM_ATTR_GROUP, GENERATED_FORM_ATTR_KIND)
    attrForm = comp.attributes.itemByName(GENERATED_FORM_ATTR_GROUP, GENERATED_FORM_ATTR_FORM_JSON)
    if attrKind is None or attrForm is None or attrKind.value != kind:
        return False
    try:
        # Round-trip the incoming form through JSON so it is compared exactly as it was stored.
        if json.loads(attrForm.value) != json.loads(json.dumps(form)):
            return False
    except Exception:
        return False
    if not comp.name.startswith(PREVIEW_NAME_PREFIX):
        return False
    comp.name = comp.name[len(PREVIEW_NAME_PREFIX):]
    return True


def _refresh_view():
    """Asks Fusion to redraw the viewport and process pending UI events, so parts added during a
    long build appear as they are made instead of all at once at the end. Never fatal."""
    try:
        app.activeViewport.refresh()
    except Exception:
        pass
    adsk.doEvents()


def _frame_drawer(widthCm: float, depthCm: float):
    """Centers the viewport on the drawer's footprint (which spans 0..width, 0..depth from the
    root origin) and zooms so all of it is visible, keeping the user's current view direction.
    Done once before the first piece is added so the whole drawer stays in frame as it fills in.
    Never fatal."""
    try:
        viewport = app.activeViewport
        camera = viewport.camera
        target = adsk.core.Point3D.create(widthCm / 2.0, depthCm / 2.0, 0)
        direction = camera.eye.vectorTo(camera.target)
        if direction.length < 1e-9:
            direction = adsk.core.Vector3D.create(0, 0, -1)
        direction.normalize()
        span = max(widthCm, depthCm)
        # Back the eye off along the current view direction, far enough to see the whole span.
        back = direction.copy()
        back.scaleBy(-span * 2.0)
        eye = target.copy()
        eye.translateBy(back)
        camera.isFitView = False
        camera.target = target
        camera.eye = eye
        if camera.cameraType == adsk.core.CameraTypes.OrthographicCameraType:
            camera.setExtents(span * 1.4, span * 1.4)
        viewport.camera = camera
        viewport.refresh()
    except Exception:
        futil.log(f'drawer: could not frame the viewport: {traceback.format_exc()}')


def _hide_sketches(component: adsk.fusion.Component):
    """Turns the light bulb off for every sketch in `component` and, recursively, in all the
    components nested inside it. The generators leave dozens of construction sketches visible,
    which clutters the canvas once a bin/baseplate/drawer is generated. Only called with a newly
    created component, so it never touches the user's own sketches. Failures are not fatal."""
    seen = set()

    def visit(comp):
        if comp.entityToken in seen:
            return
        seen.add(comp.entityToken)
        for sketch in comp.sketches:
            try:
                sketch.isLightBulbOn = False
            except Exception:
                futil.log(f'could not hide sketch "{sketch.name}": {traceback.format_exc()}')
        for occ in comp.occurrences:
            visit(occ.component)

    visit(component)


def _translation(xCm: float, yCm: float) -> adsk.core.Matrix3D:
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(xCm, yCm, 0)
    return matrix


class DrawerBuildCancelled(Exception):
    """Raised when the user presses Cancel on the drawer build progress dialog."""


def build_drawer(form: dict, parentOcc: adsk.fusion.Occurrence):
    """Runs _build_drawer behind a progress dialog (Fusion's UI is blocked while it builds, so
    this is the only feedback the user gets). Raises DrawerBuildCancelled on Cancel."""
    progress = app.userInterface.createProgressDialog()
    progress.cancelButtonText = 'Cancel'
    progress.isBackgroundTranslucencyEnabled = True
    progress.show('Building Gridfinity drawer', 'Planning layout...', 0, 1, 0)
    # Give Fusion a moment to actually paint the dialog before the long, blocking build starts.
    adsk.doEvents()
    time.sleep(0.4)
    adsk.doEvents()
    try:
        _build_drawer(form, parentOcc, progress)
    finally:
        progress.hide()


def _build_drawer(form: dict, parentOcc: adsk.fusion.Occurrence, progress):
    """Builds every baseplate tile and bin of a drawer layout as child components of
    parentOcc. `form` = {'layoutParams': {...drawerLayout.plan_drawer_layout kwargs...},
    'baseplate': <full Baseplate tab form incl. common fields, cm>,
    'bin': <full Bin tab form incl. common fields, cm>}.

    The layout is recomputed here from layoutParams (single source of truth). Each piece is
    built in its own component with the exact same generator code the Bin/Baseplate tabs use,
    then positioned by translating its grid-cell origin (baseplates and bins both build around
    that origin, with padding extending to negative X/Y), so they nest the same way they do when
    generated separately. Identical pieces are built once and re-placed as extra occurrences.
    """
    lp = form['layoutParams']
    layout = drawerLayout.plan_drawer_layout(
        pitch_mm=float(lp['pitchMm']), width_fit=lp['widthFit'], depth_fit=lp['depthFit'],
        bed_width_mm=float(lp['bedWidthMm']), bed_depth_mm=float(lp['bedDepthMm']),
        bin_strategy=lp.get('binStrategy', drawerLayout.BIN_STRATEGY_PER_TILE),
        max_bin_cells_width=int(lp.get('maxBinCellsWidth', 3)),
        max_bin_cells_depth=int(lp.get('maxBinCellsDepth', 3)),
        tile_bin_settings=lp.get('tileBinSettings'),
        bin_palette=lp.get('binPalette', ''),
        custom_bins=lp.get('customBins'),
        mask=lp.get('mask'),
        generate_plates=lp.get('generatePlates', True),
        generate_bins=lp.get('generateBins', True),
        pad_align_x=lp.get('padAlignX', 'center'),
        pad_align_y=lp.get('padAlignY', 'center'),
        cut_cells=lp.get('cutPlateCells', True),
    )
    plateForm = form['baseplate']
    binForm = form['bin']
    if lp.get('generatePlates', True) and plateForm.get('plateType') == BASEPLATE_TYPE_STACKABLE:
        raise ValueError('Stackable baseplates are not supported for drawer layouts: pick Light, Full or Skeletonized')

    parentComp = parentOcc.component
    occurrences = parentComp.occurrences
    mmToCm = lambda mm: mm / 10.0
    built = {}

    _frame_drawer(mmToCm(layout['totalWidthMm']), mmToCm(layout['totalDepthMm']))

    if not layout['generatePlates'] and not layout['generateBins']:
        raise ValueError('Turn on Baseplates and/or Bins to generate')
    plateTiles = layout['tiles'] if layout['generatePlates'] else []
    binList = layout['bins'] if layout['generateBins'] else []
    totalSteps = len(plateTiles) + len(binList)
    progress.maximumValue = max(1, totalSteps)
    stepsDone = 0

    def step(message):
        nonlocal stepsDone
        if progress.wasCancelled:
            raise DrawerBuildCancelled()
        progress.message = message
        progress.progressValue = stepsDone
        stepsDone += 1
        _refresh_view()  # show the piece that was just added, then let the dialog repaint

    def activateChild(occ):
        # Same edit context the single-piece builds use; not fatal if Fusion refuses it.
        try:
            proxy = occ.createForAssemblyContext(parentOcc)
            (proxy or occ).activate()
        except Exception:
            futil.log(f'drawer: could not activate child component: {traceback.format_exc()}')

    def place(kind, key, name, pieceForm, xMm, yMm, buildFn, inputStateCls):
        matrix = _translation(mmToCm(xMm), mmToCm(yMm))
        if (kind, key) in built:
            occurrences.addExistingComponent(built[(kind, key)], matrix)
            return
        occ = occurrences.addNewComponent(matrix)
        occ.component.name = name
        activateChild(occ)
        buildFn(inputStateCls.from_form(pieceForm), occ.component, name)
        occ.component.attributes.add(GENERATED_FORM_ATTR_GROUP, GENERATED_FORM_ATTR_KIND, kind)
        occ.component.attributes.add(GENERATED_FORM_ATTR_GROUP, GENERATED_FORM_ATTR_FORM_JSON, json.dumps(pieceForm))
        # Hide this piece's construction sketches right away so the build can be watched live
        # without a cluttered viewport (the final pass in create_and_build is then a no-op).
        _hide_sketches(occ.component)
        built[(kind, key)] = occ.component

    for index, tile in enumerate(plateTiles):
        paddings = (tile['paddingLeftMm'], tile['paddingRightMm'], tile['paddingFrontMm'], tile['paddingBackMm'])
        pf = dict(plateForm)
        pf.update(
            plateWidth=tile['plateWidth'], plateLength=tile['plateLength'],
            hasHalfLeft=False, hasHalfFront=False,
            hasHalfRight=tile['hasHalfRight'], hasHalfBack=tile['hasHalfBack'],
            stackCount=1,
            removedCells=tile.get('removedCells') or [],
            hasSidePadding=any(p > 0 for p in paddings),
            paddingLeft=mmToCm(tile['paddingLeftMm']), paddingRight=mmToCm(tile['paddingRightMm']),
            paddingBottom=mmToCm(tile['paddingFrontMm']), paddingTop=mmToCm(tile['paddingBackMm']),
        )
        key = (tile['plateWidth'], tile['plateLength'], tile['hasHalfRight'], tile['hasHalfBack']) + tuple(round(p, 3) for p in paddings) + (json.dumps(tile.get('removedCells') or []),)
        step('Baseplate tile {} of {}: {}x{} cells{}'.format(
            index + 1, len(plateTiles), tile['plateWidth'], tile['plateLength'],
            ' (copying an identical tile)' if ('baseplate', key) in built else ''))
        place(
            'baseplate', key,
            'Gridfinity baseplate {}x{}'.format(tile['plateLength'], tile['plateWidth']),
            pf,
            # plate-local origin is the grid origin; padding extends to negative X/Y from it
            tile['xMm'] + tile['paddingLeftMm'], tile['yMm'] + tile['paddingFrontMm'],
            build_baseplate, BaseplateInputState,
        )

    for binIndex, b in enumerate(binList):
        bf = dict(binForm)
        bf.update(
            binWidth=b['binWidth'], binLength=b['binLength'],
            hasHalfLeft=False, hasHalfFront=False,
            hasHalfRight=b['hasHalfRight'], hasHalfBack=b['hasHalfBack'],
        )
        if bf.get('compartmentsGridType') == COMPARTMENTS_GRID_TYPE_UNIFORM:
            # never ask a small bin for more compartments than it has cells
            bf['compartmentsGridWidth'] = max(1, min(int(bf.get('compartmentsGridWidth', 1)), max(1, b['binWidth'])))
            bf['compartmentsGridLength'] = max(1, min(int(bf.get('compartmentsGridLength', 1)), max(1, b['binLength'])))
        shapeCells = b.get('shapeCells')
        key = (b['binWidth'], b['binLength'], b['hasHalfRight'], b['hasHalfBack'])
        buildFn = build_bin
        if shapeCells:
            # irregular (e.g. L-shaped) bin: one outline body, see binIrregularGenerator
            key = key + (json.dumps(shapeCells),)
            bf['irregularCells'] = shapeCells
            buildFn = build_irregular_bin
        step('Bin {} of {}: {}{}{}'.format(
            binIndex + 1, len(binList),
            'irregular, ' + str(len(shapeCells)) + ' cells' if shapeCells else '{}x{} cells'.format(b['binWidth'], b['binLength']),
            '' , ' (copying an identical bin)' if ('bin', key) in built else ''))
        place(
            'bin', key,
            ('Gridfinity irregular bin x{}'.format(int(bf['binHeight'])) if shapeCells
             else 'Gridfinity bin {}x{}x{}'.format(b['binLength'], b['binWidth'], int(bf['binHeight']))),
            bf, b['xMm'], b['yMm'],
            buildFn, BinInputState,
        )

    # leave the parent as the active edit target, like the single-piece builds do
    try:
        parentOcc.activate()
    except Exception:
        pass
    _refresh_view()  # show the last piece too


def build_baseplate(inputState: BaseplateInputState, component: adsk.fusion.Component, name: str):
    baseplateGeneratorInput = BaseplateGeneratorInput()
    baseplateGeneratorInput.baseWidth = inputState.baseWidthUnit
    baseplateGeneratorInput.baseLength = inputState.baseLengthUnit
    baseplateGeneratorInput.xyClearance = inputState.xyClearance
    baseplateGeneratorInput.baseplateWidth = inputState.plateWidth
    baseplateGeneratorInput.baseplateLength = inputState.plateLength
    baseplateGeneratorInput.hasHalfLeft = inputState.hasHalfLeft
    baseplateGeneratorInput.hasHalfRight = inputState.hasHalfRight
    baseplateGeneratorInput.hasHalfFront = inputState.hasHalfFront
    baseplateGeneratorInput.hasHalfBack = inputState.hasHalfBack
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
    baseplateGeneratorInput.generateDxfSketch = inputState.generateDxfSketch
    baseplateGeneratorInput.removedCells = [tuple(c) for c in (inputState.removedCells or [])]

    baseplateBody = createGridfinityBaseplate(baseplateGeneratorInput, component)
    if not baseplateGeneratorInput.isStackable:
        baseplateBody.name = name


def build_irregular_bin(inputState: BinInputState, component: adsk.fusion.Component, name: str):
    """Irregular bin from inputState.irregularCells (see binIrregularGenerator): outline body, feet and
    one open cavity. Lip, scoop, label tab and compartment dividers are not supported on these bins,
    and Shelled bins are built Hollow."""
    shape = BinIrregularGeneratorInput()
    shape.cells = [tuple(c) for c in inputState.irregularCells]
    shape.baseWidth = inputState.baseWidthUnit
    shape.baseLength = inputState.baseLengthUnit
    shape.heightUnit = inputState.heightUnit
    shape.binHeight = inputState.binHeight
    shape.xyClearance = inputState.xyClearance
    shape.binCornerFilletRadius = const.BIN_CORNER_FILLET_RADIUS - inputState.xyClearance
    shape.wallThickness = inputState.wallThickness
    shape.isSolid = inputState.binType == BIN_TYPE_SOLID
    shape.generateBase = inputState.generateBase
    baseInput = BaseGeneratorInput()
    baseInput.hasScrewHoles = inputState.hasScrewHoles
    baseInput.hasMagnetCutouts = inputState.hasMagnetCutouts
    baseInput.hasMagnetCutoutsTabs = inputState.hasMagnetCutoutsTabs
    baseInput.screwHolesDiameter = inputState.screwDiameter
    baseInput.magnetCutoutsDiameter = inputState.magnetDiameter
    baseInput.magnetCutoutsDepth = inputState.magnetDepth
    shape.baseInput = baseInput
    body = createIrregularBin(shape, component)
    body.name = name


def build_bin(inputState: BinInputState, component: adsk.fusion.Component, name: str):
    features: adsk.fusion.Features = component.features

    isHollow = inputState.binType == BIN_TYPE_HOLLOW
    isSolid = inputState.binType == BIN_TYPE_SOLID
    isShelled = inputState.binType == BIN_TYPE_SHELLED

    xyClearance = inputState.xyClearance

    baseGeneratorInput = BaseGeneratorInput()
    # Must stay flush with the bin body's own wall box (binBodyGenerator.createGridfinityBinBody
    # draws its box unshifted, from the true origin) - the base/foot is a continuous physical
    # surface with the wall above it, so offsetting one without the other leaves a non-coincident
    # seam in the combined body. combineFeatures' boolean join (Hollow/Solid bins) tolerates that
    # seam silently, but ShellFeatures' face-deletion/repair pass does not, producing
    # "ASM_REM_NO_SOLUTION" on Shelled bins. A prior attempt shifted this by -xyClearance to
    # better center the foot within the baseplate's own cutout opening, but that broke the bin's
    # internal foot/wall alignment instead - reverted.
    baseGeneratorInput.originPoint = component.originConstructionPoint.geometry
    baseGeneratorInput.baseWidth = inputState.baseWidthUnit
    baseGeneratorInput.baseLength = inputState.baseLengthUnit
    baseGeneratorInput.xyClearance = xyClearance
    baseGeneratorInput.hasScrewHoles = inputState.hasScrewHoles and not isShelled
    baseGeneratorInput.hasMagnetCutouts = inputState.hasMagnetCutouts and not isShelled
    baseGeneratorInput.hasMagnetCutoutsTabs = inputState.hasMagnetCutoutsTabs and not isShelled
    baseGeneratorInput.screwHolesDiameter = inputState.screwDiameter
    baseGeneratorInput.magnetCutoutsDiameter = inputState.magnetDiameter
    baseGeneratorInput.magnetCutoutsDepth = inputState.magnetDepth

    gridModel = gridSlicing.buildGridModel(
        inputState.binWidth, inputState.binLength,
        inputState.baseWidthUnit, inputState.baseLengthUnit,
        inputState.hasHalfLeft, inputState.hasHalfRight, inputState.hasHalfFront, inputState.hasHalfBack,
    )

    baseBodies: list[adsk.fusion.BRepBody] = []
    if inputState.generateBase:
        baseBodies = createBaseBodyGrid(
            baseGeneratorInput,
            gridModel,
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
    binBodyInput.hasHalfLeft = inputState.hasHalfLeft
    binBodyInput.hasHalfRight = inputState.hasHalfRight
    binBodyInput.hasHalfFront = inputState.hasHalfFront
    binBodyInput.hasHalfBack = inputState.hasHalfBack
    binBodyInput.xyClearance = xyClearance
    binBodyInput.binCornerFilletRadius = const.BIN_CORNER_FILLET_RADIUS - xyClearance
    binBodyInput.isSolid = isSolid or isShelled
    binBodyInput.wallThickness = inputState.wallThickness
    binBodyInput.hasScoop = inputState.hasScoop and isHollow
    binBodyInput.scoopMaxRadius = inputState.scoopMaxRadius
    binBodyInput.scoopSides = {
        side for side, checked in (
            ('front', inputState.scoopFront),
            ('left', inputState.scoopLeft),
            ('back', inputState.scoopBack),
            ('right', inputState.scoopRight),
        ) if checked
    }
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
                const.BIN_LIP_WALL_THICKNESS if binBodyInput.hasLip and binBodyInput.hasFrontScoop else binBodyInput.wallThickness + binBodyInput.binLength * binBodyInput.baseLength - binBodyInput.wallThickness - binBodyInput.xyClearance * 2,
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
