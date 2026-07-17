import adsk.core, adsk.fusion, traceback
import os
import json

from ...lib import configUtils
from ...lib import appConfig
from ...lib import fusion360utils as futil
from ... import config
from ...lib.gridfinityUtils import const
from ...lib.ui.unsupportedDesignTypeException import UnsupportedDesignTypeException

from . import generation
from . import validation
from . import previewState
from . import optimizer
from .optimizerInputState import OptimizerInputState

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdGridfinityPalette'
CMD_NAME = 'GridfinityGeneratorPlus'
CMD_Description = 'Create gridfinity bins and baseplates'

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
RESOURCES_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'resources')

CONFIG_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'commandConfig')
UI_DEFAULTS_CONFIG_PATH = os.path.join(CONFIG_FOLDER_PATH, 'ui_defaults.json')

PALETTE_TITLE = 'GridfinityGeneratorPlus'
PALETTE_VERSION = 13
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Local list of event handlers for the command button.
local_handlers = []
# Module-level list of palette handlers, kept alive for the lifetime of the add-in.
_handlers = []

DEFAULT_BIN = {
    'heightUnit': const.DIMENSION_DEFAULT_HEIGHT_UNIT,
    'binWidth': 2,
    'binLength': 3,
    'binHeight': 5,
    'generateBody': True,
    'binType': 'Hollow',
    'wallThickness': const.BIN_WALL_THICKNESS,
    'withLip': True,
    'withLipNotches': False,
    'compartmentsGridType': 'Uniform',
    'compartmentsGridWidth': 1,
    'compartmentsGridLength': 1,
    'compartments': [],
    'hasScoop': False,
    'scoopMaxRadius': const.BIN_SCOOP_MAX_RADIUS,
    'hasTab': False,
    'tabLength': 1,
    'tabWidth': const.BIN_TAB_WIDTH,
    'tabPosition': 0,
    'tabAngleDeg': 45,
    'generateBase': True,
    'hasScrewHoles': False,
    'screwDiameter': const.DIMENSION_SCREW_HOLE_DIAMETER,
    'hasMagnetCutouts': False,
    'hasMagnetCutoutsTabs': False,
}

DEFAULT_BASEPLATE = {
    'plateWidth': 2,
    'plateLength': 3,
    'plateType': 'Light',
    'hasMagnetCutouts': True,
    'hasScrewHoles': True,
    'screwDiameter': const.DIMENSION_PLATE_SCREW_HOLE_DIAMETER,
    'screwHeadDiameter': const.DIMENSION_SCREW_HEAD_CUTOUT_DIAMETER,
    'hasSidePadding': False,
    'paddingLeft': 0,
    'paddingTop': 0,
    'paddingRight': 0,
    'paddingBottom': 0,
    'extraBottomThickness': const.BASEPLATE_EXTRA_HEIGHT,
    'binZClearance': const.BASEPLATE_BIN_Z_CLEARANCE,
    'hasConnectionHoles': False,
    'connectionHoleDiameter': const.DIMENSION_PLATE_CONNECTION_SCREW_HOLE_DIAMETER,
    'stackCount': 1,
    'interfaceLayerThickness': const.BASEPLATE_STACK_INTERFACE_THICKNESS,
}

# The Grid Optimizer tab is a pure-Python advisory calculator (no Fusion
# geometry involved), but its dimension list uses the same named-preset
# save/load/delete system as Bin and Baseplate (e.g. a "Kitchen Drawers" set).
DEFAULT_OPTIMIZER = {
    'minSize': 3.0,
    'maxSize': 7.5,
    'allowHalfBins': True,
    'compareStandard': False,
    'priority': 'balanced',
    'items': [],
}

DEFAULTS_BY_TAB = {
    'bin': DEFAULT_BIN,
    'baseplate': DEFAULT_BASEPLATE,
    'optimizer': DEFAULT_OPTIMIZER,
}

# Fields shared between the Bin and Baseplate tabs (grid pitch + magnet size)
# so a custom baseplate grid and the bins that go in it always stay compatible.
COMMON_FIELDS = ['baseWidthUnit', 'baseLengthUnit', 'xyClearance', 'magnetDiameter', 'magnetDepth']

# Bin/Baseplate presets snapshot the Common panel values in effect when saved,
# and restore them (updating the live shared panel) when loaded, so a preset
# always reproduces the exact grid it was designed for. The Optimizer tab has
# no relationship to the physical grid, so its presets never touch this.
TABS_WITH_SHARED_COMMON = ('bin', 'baseplate')

DEFAULT_COMMON = {
    'baseWidthUnit': const.DIMENSION_DEFAULT_WIDTH_UNIT,
    'baseLengthUnit': const.DIMENSION_DEFAULT_WIDTH_UNIT,
    'xyClearance': const.BIN_XY_CLEARANCE,
    'magnetDiameter': const.DIMENSION_MAGNET_CUTOUT_DIAMETER,
    'magnetDepth': const.DIMENSION_MAGNET_CUTOUT_DEPTH,
}

VALIDATE_BY_TAB = {
    'bin': validation.validate_bin,
    'baseplate': validation.validate_baseplate,
    'optimizer': validation.validate_optimizer,
}


def getErrorMessage():
    stackTrace = traceback.format_exc()
    return f'An unknown error occurred, please validate your inputs and try again:\n{stackTrace}'


# The palette's remembered on-screen size/position/docking, stored in the
# add-in-wide GGPlus_config.json (via lib/appConfig.py) rather than anything
# under commandGridfinityPalette/commandConfig/, since it's not tied to a tab
# or preset. Fusion's Palette has no move/resize event, so this is captured
# at the two points a palette actually goes away: the user closing it, and
# the add-in stopping.
PALETTE_GEOMETRY_KEY = 'paletteGeometry'
DEFAULT_PALETTE_WIDTH = 420
DEFAULT_PALETTE_HEIGHT = 700
DEFAULT_PALETTE_DOCKING_STATE = int(adsk.core.PaletteDockingStates.PaletteDockStateRight)


def _load_palette_geometry() -> dict:
    geometry = appConfig.load().get(PALETTE_GEOMETRY_KEY, {})
    return {
        'width': geometry.get('width', DEFAULT_PALETTE_WIDTH),
        'height': geometry.get('height', DEFAULT_PALETTE_HEIGHT),
        'left': geometry.get('left'),
        'top': geometry.get('top'),
        'dockingState': geometry.get('dockingState', DEFAULT_PALETTE_DOCKING_STATE),
    }


def _save_palette_geometry(palette: adsk.core.Palette):
    try:
        appConfig.update({PALETTE_GEOMETRY_KEY: {
            'width': palette.width,
            'height': palette.height,
            'left': palette.left,
            'top': palette.top,
            'dockingState': int(palette.dockingState),
        }})
    except Exception:
        futil.log(f'{CMD_NAME} failed to save palette geometry:\n{traceback.format_exc()}')


# The Theme tab's selection (Theme Designer Pro standard: CSS vars + data-theme
# attribute, applied entirely client-side in script.js). Python only persists
# the active theme's name, same pattern as palette geometry above -- the actual
# CSS variables for any imported (non-built-in) theme live in
# appConfig.load_imported_themes()/save_imported_theme(), keyed by theme id, so
# every theme ever imported survives a restart, not just whichever was active.
THEME_CONFIG_KEY = 'theme'
DEFAULT_THEME = {'name': 'System'}


def _load_theme() -> dict:
    theme = appConfig.load().get(THEME_CONFIG_KEY, {})
    return {'name': theme.get('name', DEFAULT_THEME['name'])}


def _save_theme(form: dict):
    appConfig.update({THEME_CONFIG_KEY: {
        'name': form.get('name', DEFAULT_THEME['name']),
    }})


# Executed when add-in is run.
def start():
    futil.log(f'{CMD_NAME} Command Start Event')
    addinConfig = configUtils.readConfig(CONFIG_FOLDER_PATH)

    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    tool_clip_path = os.path.join(RESOURCES_FOLDER, '128x128.png')
    if os.path.exists(tool_clip_path):
        cmd_def.toolClipFilename = tool_clip_path

    futil.add_handler(cmd_def.commandCreated, command_created, local_handlers=local_handlers)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = addinConfig['UI'].getboolean('is_promoted')


# Executed when add-in is stopped.
def stop():
    futil.log(f'{CMD_NAME} Command Stop Event')
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control: adsk.core.CommandControl = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    addinConfig = configUtils.readConfig(CONFIG_FOLDER_PATH)
    addinConfig['UI']['is_promoted'] = 'yes' if command_control and command_control.isPromoted else 'no'
    configUtils.writeConfig(addinConfig, CONFIG_FOLDER_PATH)

    if command_control:
        command_control.deleteMe()
    if command_definition:
        command_definition.deleteMe()

    try:
        previewState.clear_preview(force=False)
    except Exception as err:
        futil.log(f'{CMD_NAME} failed to clear preview on stop, {err}')

    palette = ui.palettes.itemById(config.PALETTE_ID)
    if palette:
        _save_palette_geometry(palette)
        palette.deleteMe()

    global _handlers
    _handlers = []


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')
    # This command has no dialog inputs of its own, so Fusion auto-executes it
    # immediately after creation instead of showing an empty dialog.
    futil.add_handler(args.command.execute, lambda _: open_palette(), local_handlers=local_handlers)


def open_palette():
    palette = ui.palettes.itemById(config.PALETTE_ID)
    if palette:
        palette.isVisible = True
        return

    html_path = os.path.join(SCRIPT_DIR, 'resources', 'palette', 'index.html')
    url = 'file:///' + html_path.replace('\\', '/') + f'?v={PALETTE_VERSION}'

    geometry = _load_palette_geometry()

    palette = ui.palettes.add(
        config.PALETTE_ID, PALETTE_TITLE, url,
        True,
        True,
        True,
        geometry['width'], geometry['height'],
    )
    palette.dockingState = geometry['dockingState']
    if geometry['left'] is not None and geometry['top'] is not None:
        palette.setPosition(geometry['left'], geometry['top'])

    on_html_event = HTMLEventHandler()
    palette.incomingFromHTML.add(on_html_event)
    _handlers.append(on_html_event)

    on_closed = PaletteCloseHandler()
    palette.closed.add(on_closed)
    _handlers.append(on_closed)


def _send(palette: adsk.core.Palette, action: str, payload: dict):
    palette.sendInfoToHTML(action, json.dumps(payload))


def _ensure_safe_to_mutate():
    activeCmd = ui.activeCommand
    if activeCmd and activeCmd != 'SelectCommand':
        return False, 'Please finish or cancel the active command before generating or previewing.'
    return True, ''


def _ensure_hybrid_design_intent():
    # Generate (not Preview) requires Hybrid design intent -- it's what lets every
    # generated component carry its own settings as a document attribute (see
    # generation.GENERATED_FORM_ATTR_*), so a saved file can be reopened, shared, or
    # revisited months later and still be editable via "Edit Active Component". The
    # palette stays open across document tabs, so this is checked at Generate time
    # rather than once on palette open -- the user could switch from a Hybrid to a
    # Part/Assembly design mid-session without closing the palette.
    des = adsk.fusion.Design.cast(app.activeProduct)
    if des is None:
        return False, 'No active Fusion design.'
    if des.designIntent != adsk.fusion.DesignIntentTypes.HybridDesignIntentType:
        return False, (
            'Generate requires Hybrid design intent (Document Settings → Design → Hybrid). '
            'This is what lets each generated component remember its own settings, so you can '
            'revisit or share your design later. Switch to Hybrid Design and click Generate again '
            '— your current field values are unaffected.'
        )
    return True, ''


COMMON_CONFIG_PATH = os.path.join(CONFIG_FOLDER_PATH, 'common.json')

PRESETS_DIR = os.path.join(CONFIG_FOLDER_PATH, 'presets')

INVALID_CONFIG_NAME_CHARS = '\\/:*?"<>|'


def _presets_dir(tab: str) -> str:
    path = os.path.join(PRESETS_DIR, tab)
    os.makedirs(path, exist_ok=True)
    return path


def _config_path(tab: str, name: str) -> str:
    return os.path.join(_presets_dir(tab), f'{name}.json')


def _sanitize_config_name(name: str) -> str:
    name = (name or '').strip()
    for ch in INVALID_CONFIG_NAME_CHARS:
        name = name.replace(ch, '_')
    if not name:
        raise ValueError('Config name cannot be empty')
    return name


def _list_configs(tab: str) -> list:
    directory = _presets_dir(tab)
    names = [
        os.path.splitext(f)[0]
        for f in os.listdir(directory)
        if f.lower().endswith('.json')
    ]
    return sorted(names, key=str.lower)


def _load_ui_defaults() -> dict:
    data = configUtils.readJsonConfig(UI_DEFAULTS_CONFIG_PATH)
    return data if data else {}


def _get_active_config_name(tab: str):
    data = _load_ui_defaults()
    return data.get(tab, {}).get('activeConfig')


def _set_active_config_name(tab: str, name):
    data = _load_ui_defaults()
    data.setdefault(tab, {})['activeConfig'] = name
    configUtils.dumpJsonConfig(UI_DEFAULTS_CONFIG_PATH, data)


def _get_tab_form(tab: str) -> dict:
    """The form shown when the palette opens: the active saved config if one is
    set (merged over the hardcoded defaults, so older configs missing newer
    fields still work), otherwise the hardcoded Gridfinity-standard defaults."""
    active = _get_active_config_name(tab)
    form = dict(DEFAULTS_BY_TAB[tab])
    if active:
        saved = configUtils.readJsonConfig(_config_path(tab, active))
        if saved is not None:
            form.update(saved)
        else:
            _set_active_config_name(tab, None)
    return form


def _load_common() -> dict:
    """The live shared values for grid pitch + magnet size, used by both tabs."""
    data = configUtils.readJsonConfig(COMMON_CONFIG_PATH)
    form = dict(DEFAULT_COMMON)
    if data:
        form.update({k: v for k, v in data.items() if k in COMMON_FIELDS})
    return form


def _save_common(form: dict):
    configUtils.dumpJsonConfig(COMMON_CONFIG_PATH, {k: form[k] for k in COMMON_FIELDS if k in form})


def _send_config_list(palette: adsk.core.Palette, tab: str):
    _send(palette, 'config_list', {
        'tab': tab,
        'configs': _list_configs(tab),
        'activeConfig': _get_active_config_name(tab),
    })


class HTMLEventHandler(adsk.core.HTMLEventHandler):
    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            data = json.loads(html_args.data)
            action = data.get('action')
            tab = data.get('tab')
            form = data.get('form')
            palette = ui.palettes.itemById(config.PALETTE_ID)
            if palette is None:
                return

            if action == 'get_defaults':
                _send(palette, 'set_state', {
                    'tab': 'common',
                    'form': _load_common(),
                    'source': 'defaults',
                })
                for t in ('bin', 'baseplate', 'optimizer'):
                    _send(palette, 'set_state', {
                        'tab': t,
                        'form': _get_tab_form(t),
                        'source': 'defaults',
                    })
                    _send_config_list(palette, t)
                _send(palette, 'set_state', {
                    'tab': 'theme',
                    'form': _load_theme(),
                    'importedThemes': appConfig.load_imported_themes(),
                    'source': 'defaults',
                })

            elif action == 'update_theme':
                _save_theme(form)

            elif action == 'save_imported_theme':
                themeId = data.get('id')
                themeVars = data.get('vars')
                if themeId and isinstance(themeVars, dict):
                    appConfig.save_imported_theme(themeId, themeVars)

            elif action == 'update_common':
                _save_common(form)
                _send(palette, 'set_state', {
                    'tab': 'common',
                    'form': _load_common(),
                    'source': 'update_common',
                })

            elif action == 'optimize':
                self._handle_optimize(palette, form)

            elif action == 'validate':
                result = VALIDATE_BY_TAB[tab](form)
                _send(palette, 'validation_result', {
                    'tab': tab,
                    'valid': result['valid'],
                    'fieldErrors': result['fieldErrors'],
                    'computed': result['computed'],
                })

            elif action == 'update_preview':
                self._handle_update_preview(palette, tab, form)

            elif action == 'clear_preview':
                self._handle_clear_preview(palette, tab)

            elif action == 'generate':
                self._handle_generate(palette, tab, form)

            elif action == 'edit_active_component':
                self._handle_edit_active_component(palette)

            elif action == 'save_config_as':
                self._handle_save_as(palette, tab, form, data.get('name'))

            elif action == 'update_current_config':
                self._handle_update_current(palette, tab, form)

            elif action == 'load_config':
                self._handle_load_config(palette, tab, data.get('name'))

            elif action == 'delete_config':
                self._handle_delete_config(palette, tab, data.get('name'))

            elif action == 'factory_reset':
                if tab == 'common':
                    configUtils.dumpJsonConfig(COMMON_CONFIG_PATH, dict(DEFAULT_COMMON))
                    _send(palette, 'set_state', {
                        'tab': 'common',
                        'form': dict(DEFAULT_COMMON),
                        'source': 'factory_reset',
                    })
                else:
                    _set_active_config_name(tab, None)
                    _send(palette, 'set_state', {
                        'tab': tab,
                        'form': dict(DEFAULTS_BY_TAB[tab]),
                        'source': 'factory_reset',
                    })
                    _send_config_list(palette, tab)

        except Exception:
            app.log(f'{CMD_NAME} HTMLEventHandler failed:\n{traceback.format_exc()}')

    def _handle_save_as(self, palette: adsk.core.Palette, tab: str, form: dict, rawName: str):
        try:
            name = _sanitize_config_name(rawName)
        except ValueError:
            _send(palette, 'notification', {'type': 'error', 'message': 'Enter a name for the config'})
            return
        saveForm = dict(form) if tab in TABS_WITH_SHARED_COMMON else {k: v for k, v in form.items() if k not in COMMON_FIELDS}
        configUtils.dumpJsonConfig(_config_path(tab, name), saveForm)
        _set_active_config_name(tab, name)
        _send_config_list(palette, tab)
        _send(palette, 'notification', {'type': 'success', 'message': f'Saved as "{name}"'})

    def _handle_update_current(self, palette: adsk.core.Palette, tab: str, form: dict):
        active = _get_active_config_name(tab)
        if not active:
            _send(palette, 'notification', {'type': 'error', 'message': 'No active config to update, use Save As instead'})
            return
        saveForm = dict(form) if tab in TABS_WITH_SHARED_COMMON else {k: v for k, v in form.items() if k not in COMMON_FIELDS}
        configUtils.dumpJsonConfig(_config_path(tab, active), saveForm)
        _send(palette, 'notification', {'type': 'success', 'message': f'Updated "{active}"'})

    def _handle_load_config(self, palette: adsk.core.Palette, tab: str, name: str):
        if not name:
            _send(palette, 'notification', {'type': 'error', 'message': 'Select a config to load'})
            return
        saved = configUtils.readJsonConfig(_config_path(tab, name))
        if saved is None:
            _send(palette, 'notification', {'type': 'error', 'message': f'Config "{name}" not found'})
            return
        form = dict(DEFAULTS_BY_TAB[tab])
        form.update(saved)
        _set_active_config_name(tab, name)
        _send(palette, 'set_state', {'tab': tab, 'form': form, 'source': 'load_config'})
        _send_config_list(palette, tab)

        if tab in TABS_WITH_SHARED_COMMON:
            commonOverrides = {k: saved[k] for k in COMMON_FIELDS if k in saved}
            if commonOverrides:
                commonForm = _load_common()
                commonForm.update(commonOverrides)
                _save_common(commonForm)
                _send(palette, 'set_state', {'tab': 'common', 'form': commonForm, 'source': 'load_config'})

        _send(palette, 'notification', {'type': 'success', 'message': f'Loaded "{name}"'})

    def _handle_delete_config(self, palette: adsk.core.Palette, tab: str, name: str):
        if not name:
            _send(palette, 'notification', {'type': 'error', 'message': 'Select a config to delete'})
            return
        configUtils.deleteConfigFile(_config_path(tab, name))
        if _get_active_config_name(tab) == name:
            _set_active_config_name(tab, None)
        _send_config_list(palette, tab)
        _send(palette, 'notification', {'type': 'success', 'message': f'Deleted "{name}"'})

    def _handle_clear_preview(self, palette: adsk.core.Palette, tab: str):
        if not previewState.has_preview():
            _send(palette, 'preview_status', {'tab': tab, 'active': False})
            return

        safe, message = _ensure_safe_to_mutate()
        if not safe:
            _send(palette, 'notification', {'type': 'error', 'message': message})
            return

        try:
            previewState.clear_preview()
            _send(palette, 'preview_status', {'tab': tab, 'active': False})
        except Exception:
            app.log(f'{CMD_NAME} clear_preview failed:\n{traceback.format_exc()}')
            _send(palette, 'notification', {'type': 'error', 'message': getErrorMessage()})

    def _handle_update_preview(self, palette: adsk.core.Palette, tab: str, form: dict):
        result = VALIDATE_BY_TAB[tab](form)
        if not result['valid']:
            _send(palette, 'validation_result', {
                'tab': tab, 'valid': False,
                'fieldErrors': result['fieldErrors'], 'computed': result['computed'],
            })
            _send(palette, 'notification', {'type': 'error', 'message': 'Fix the highlighted fields before previewing'})
            return

        safe, message = _ensure_safe_to_mutate()
        if not safe:
            _send(palette, 'notification', {'type': 'error', 'message': message})
            return

        try:
            previewState.clear_preview()
            occurrence = generation.create_and_build(tab, form, is_preview=True)
            previewState.track_preview(tab, occurrence)
            _send(palette, 'preview_status', {'tab': tab, 'active': True, 'adopted': False})
        except UnsupportedDesignTypeException:
            _send(palette, 'notification', {
                'type': 'error',
                'message': 'Design type is unsupported. Please enable the timeline feature to proceed.',
            })
        except Exception:
            app.log(f'{CMD_NAME} update_preview failed:\n{traceback.format_exc()}')
            _send(palette, 'notification', {'type': 'error', 'message': getErrorMessage()})

    def _handle_generate(self, palette: adsk.core.Palette, tab: str, form: dict):
        result = VALIDATE_BY_TAB[tab](form)
        if not result['valid']:
            _send(palette, 'validation_result', {
                'tab': tab, 'valid': False,
                'fieldErrors': result['fieldErrors'], 'computed': result['computed'],
            })
            _send(palette, 'notification', {'type': 'error', 'message': 'Fix the highlighted fields before generating'})
            return

        safe, message = _ensure_safe_to_mutate()
        if not safe:
            _send(palette, 'notification', {'type': 'error', 'message': message})
            return

        hybridOk, hybridMessage = _ensure_hybrid_design_intent()
        if not hybridOk:
            _send(palette, 'notification', {'type': 'error', 'message': hybridMessage})
            return

        try:
            previewState.clear_preview()
            generation.create_and_build(tab, form)
            _send(palette, 'preview_status', {'tab': tab, 'active': False})
            _send(palette, 'notification', {'type': 'success', 'message': 'Generated'})
        except UnsupportedDesignTypeException:
            _send(palette, 'notification', {
                'type': 'error',
                'message': 'Design type is unsupported. Please enable the timeline feature to proceed.',
            })
        except Exception:
            app.log(f'{CMD_NAME} generate failed:\n{traceback.format_exc()}')
            _send(palette, 'notification', {'type': 'error', 'message': getErrorMessage()})

    def _handle_optimize(self, palette: adsk.core.Palette, form: dict):
        result = validation.validate_optimizer(form)
        if not result['valid']:
            _send(palette, 'validation_result', {
                'tab': 'optimizer', 'valid': False,
                'fieldErrors': result['fieldErrors'], 'computed': result['computed'],
            })
            _send(palette, 'notification', {'type': 'error', 'message': 'Fix the highlighted fields before calculating'})
            return

        try:
            state = OptimizerInputState.from_form(form)
            items = [
                {'description': item.description, 'widthMm': item.width * 10, 'depthMm': item.depth * 10}
                for item in state.items
            ]
            optimizerResult = optimizer.compute_best_fit(
                items,
                min_size_mm=round(state.minSize * 10),
                max_size_mm=round(state.maxSize * 10),
                allow_half_bins=state.allowHalfBins,
                compare_standard=state.compareStandard,
                priority=state.priority,
            )
            _send(palette, 'optimizer_result', optimizerResult)
        except Exception:
            app.log(f'{CMD_NAME} optimize failed:\n{traceback.format_exc()}')
            _send(palette, 'notification', {'type': 'error', 'message': getErrorMessage()})

    def _handle_edit_active_component(self, palette: adsk.core.Palette):
        safe, message = _ensure_safe_to_mutate()
        if not safe:
            _send(palette, 'notification', {'type': 'error', 'message': message})
            return

        try:
            des = adsk.fusion.Design.cast(app.activeProduct)
            if des is None:
                _send(palette, 'notification', {'type': 'error', 'message': 'No active Fusion design.'})
                return

            comp = des.activeComponent
            if comp is None or comp.entityToken == des.rootComponent.entityToken:
                _send(palette, 'notification', {
                    'type': 'error',
                    'message': 'Hover over a Gridfinity component in the browser and click the radio button that appears to its right to activate it first, then click this button.',
                })
                return

            attrs = comp.attributes
            kindAttr = attrs.itemByName(generation.GENERATED_FORM_ATTR_GROUP, generation.GENERATED_FORM_ATTR_KIND)
            formAttr = attrs.itemByName(generation.GENERATED_FORM_ATTR_GROUP, generation.GENERATED_FORM_ATTR_FORM_JSON)
            if kindAttr is None or formAttr is None:
                _send(palette, 'notification', {
                    'type': 'error',
                    'message': "The active component wasn't generated by GridfinityGeneratorPlus.",
                })
                return

            kind = kindAttr.value
            if kind not in VALIDATE_BY_TAB:
                _send(palette, 'notification', {'type': 'error', 'message': f'Unknown component kind "{kind}".'})
                return

            try:
                form = json.loads(formAttr.value)
            except (ValueError, TypeError):
                _send(palette, 'notification', {'type': 'error', 'message': 'Saved parameters for this component are unreadable.'})
                return

            occurrences = des.rootComponent.allOccurrencesByComponent(comp)
            if occurrences.count == 0:
                _send(palette, 'notification', {'type': 'error', 'message': 'Could not find the active component in the design.'})
                return
            occurrence = occurrences.item(0)
            componentName = comp.name

            # Release (not delete) whatever was previously tracked, then return to
            # root so the adopted occurrence isn't "inside" the active edit context.
            previewState.clear_preview(force=False)
            des.activateRootComponent()
            comp.name = f'{generation.PREVIEW_NAME_PREFIX}{componentName}'
            previewState.track_preview(kind, occurrence, adopted=True, original_name=componentName)

            _send(palette, 'set_state', {
                'tab': kind, 'form': form, 'source': 'edit_component', 'componentName': componentName,
            })

            if kind in TABS_WITH_SHARED_COMMON:
                commonOverrides = {k: form[k] for k in COMMON_FIELDS if k in form}
                if commonOverrides:
                    commonForm = _load_common()
                    commonForm.update(commonOverrides)
                    _save_common(commonForm)
                    _send(palette, 'set_state', {'tab': 'common', 'form': commonForm, 'source': 'edit_component_common'})

            _send(palette, 'preview_status', {'tab': kind, 'active': True, 'adopted': True})
        except Exception:
            app.log(f'{CMD_NAME} edit_active_component failed:\n{traceback.format_exc()}')
            _send(palette, 'notification', {'type': 'error', 'message': getErrorMessage()})


class PaletteCloseHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def notify(self, args):
        try:
            palette = ui.palettes.itemById(config.PALETTE_ID)
            if palette:
                _save_palette_geometry(palette)
            previewState.clear_preview(force=False)
        except Exception:
            app.log(f'{CMD_NAME} PaletteCloseHandler failed:\n{traceback.format_exc()}')
