# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**GridfinityGeneratorPlus** — a fork of LevMishin's `GridfinityGenerator` Fusion 360 add-in (Python) that generates parametric [Gridfinity](https://gridfinity.xyz/) storage bins and baseplates directly inside Autodesk Fusion 360. This fork's distinguishing feature is a persistent, dockable HTML palette UI (`adsk.core.Palettes`) replacing the original's `CommandDialog`-based UI. It follows Autodesk's standard Fusion 360 add-in template layout (`lib/fusion360utils/` is unmodified Autodesk boilerplate — leave it alone unless fixing a genuine framework bug).

There is no build system, package manager, linter, or test suite in this repo — it only runs inside Fusion 360's embedded Python interpreter via the Fusion 360 add-in loader. There are no `requirements.txt`/`pyproject.toml`. The repo is tracked in git and hosted as a private GitHub repository (`edjohnson100/GridfinityGeneratorPlus`, `main` branch).

See `docs/Dev_Notes.md` for a running log of notable feature work and design decisions made in this fork (session-by-session notes, not auto-generated — update it when you finish a notable change).

`config.py`'s `ADDIN_NAME` (`'GridfinityGeneratorPlus'`) and `COMPANY_NAME` (`'LevMishin'`) are combined to build unique Fusion command/palette IDs — `ADDIN_NAME` was deliberately changed from the upstream `'GridfinityGenerator'` so this fork can be installed and run side-by-side with the original add-in without ID collisions.

## Running / testing changes

There is no CLI entry point or headless test runner — `adsk.core` / `adsk.fusion` are Fusion 360's runtime API modules and only exist inside the Fusion 360 process. To verify a change:

1. Open Fusion 360 → Utilities → Add-Ins → Scripts and Add-Ins → add this folder as an add-in (or point Fusion at `GridfinityGeneratorPlus.manifest`).
2. Run/reload the add-in, then use the "Gridfinity generator" toolbar button (Solid Create panel) to open the palette and exercise the change interactively.
3. Use `futil.log(...)` (see `lib/fusion360utils/general_utils.py`) to write to the Fusion 360 Text Command window / console for debugging; toggle verbose logging via `config.DEBUG` in `config.py`.

Since there's no automated test suite, manually generate a bin/baseplate with the changed inputs and confirm the resulting solid body is correct in the Fusion 360 viewport before considering a change done.

## Architecture

### Add-in bootstrap
- `GridfinityGeneratorPlus.py` is the add-in entry point Fusion 360 calls (`run(context)` / `stop(context)`), delegating to `commands.start()` / `commands.stop()`.
- `commands/__init__.py` is the registry of top-level commands.
- `config.py` holds add-in-wide constants (`DEBUG` flag, `ADDIN_NAME`, `COMPANY_NAME`, `PALETTE_ID`).

### Commands (`commands/`) — mid-migration state, read carefully

This repo is **mid-migration** from a two-`CommandDialog` UI to a single persistent HTML palette UI. Both old and new command packages currently coexist on disk:

- **`commandGridfinityPalette/`** — the active, current UI. A single palette (`adsk.core.Palettes`), tab-switched between "Bin" and "Baseplate", plus an always-visible "Common settings" panel above the tabs (shared fields: `baseWidthUnit`, `baseLengthUnit`, `xyClearance`, `magnetDiameter`, `magnetDepth`), with explicit "Update Preview"/"Generate"/"Clear Preview" buttons (no always-on live preview). `commands/__init__.py` registers only this command now — the old two are no longer wired up to run, just not yet deleted from disk. Structure:
  - `entry.py` — palette lifecycle: `start()`/`stop()`, `open_palette()`, `HTMLEventHandler` (dispatches JS→Python actions: `get_defaults`, `validate`, `update_preview`, `generate`, `clear_preview`, `edit_active_component`, `update_common`, `save_as`/`update_current`/`load`/`delete` (config manager), `factory_reset`), `PaletteCloseHandler`, `_ensure_safe_to_mutate()` modal-safety guard. `_handle_edit_active_component()` implements re-edit/redo: it reads `Design.activeComponent` (the user double-clicks a component in the browser to activate it first), looks up the `formJson`/`kind` custom attributes `generation.create_and_build()` stamps on every Hybrid-design-intent component it creates, repopulates the palette from that JSON, and adopts the existing `Occurrence` into `previewState` (`adopted=True`) so the existing Update Preview / Generate / Clear Preview flows transparently edit-in-place, rebuild, or delete it. Hybrid design intent only — Part/Assembly-intent builds have no single owning entity to tag/re-adopt.
  - `generation.py` — `create_and_build(kind, form)` / `build_bin(...)` / `build_baseplate(...)`, ported near-verbatim from the old dialogs' `generateBin`/`generateBaseplate`, now driven by plain form dicts instead of `CommandInputs`. Also stamps the originating `form` (as JSON, plus a `kind` marker) as custom attributes on the created component when building in Hybrid design intent — this is what makes `entry._handle_edit_active_component()` possible.
  - `validation.py` — `validate_bin(form)` / `validate_baseplate(form)` → `{valid, fieldErrors, computed}`, ported from the old dialogs' range checks. The `common` pseudo-tab has no direct entry in `VALIDATE_BY_TAB` — it's validated indirectly as part of whichever real tab (`bin`/`baseplate`) is active.
  - `previewState.py` — single-slot preview tracker (module-level state re-resolved via `Design.findEntityByToken`, supporting both a new Occurrence and a list of root-component timeline features); `track_preview(tab, tracked, adopted=False)`/`clear_preview(force=True)`/`has_preview()`. Only one preview component exists at a time across both tabs; the palette's "Clear Preview" button calls `clear_preview()` directly (default `force=True`, so it always deletes). The `adopted`/`force` pair exists for the "edit an already-generated component" flow: an *adopted* component (loaded via `edit_active_component`) is only actually deleted when `force=True` (an explicit Clear Preview / Update Preview / Generate click) — implicit paths (`PaletteCloseHandler`, add-in `stop()`) call `clear_preview(force=False)`, which just releases tracking and leaves the real component untouched, so closing the palette mid-edit never silently deletes work.
  - `binInputState.py` / `baseplateInputState.py` — typed dataclasses (`from_form(dict)`) sitting between the raw JS form dict and the `*GeneratorInput` objects in `lib/gridfinityUtils/`.
  - `commandConfig/config.ini`, `commandConfig/ui_defaults.json` (`{"bin": {"activeConfig": ...}, "baseplate": {"activeConfig": ...}}`), `commandConfig/common.json` (live shared-field values, not tied to a named preset), `commandConfig/presets/{bin,baseplate}/*.json` — file-per-named-config storage backing the palette's config manager (Save As / Update Current / Load / Delete per tab, plus per-tab and per-common Factory Reset). Saved presets never include the `COMMON_FIELDS` (`baseWidthUnit`, `baseLengthUnit`, `xyClearance`, `magnetDiameter`, `magnetDepth`) — those live only in `common.json`.
  - `resources/palette/` — `index.html` / `style.css` / `script.js`, the actual palette UI. Field inputs use `id="{tab}.{fieldName}"` (`tab` is `bin`, `baseplate`, or `common`). `script.js` owns mm↔cm display conversion (Python/Fusion internal unit is cm) via a per-tab `MM_FIELDS` allowlist (including a `common` key), bridges to Python via `window.adsk.fusionSendData` / `window.fusionJavaScriptHandler.handle`, and never uses `localStorage` (all durable state is Python-owned JSON pushed via a `set_state` message). Field-change validation is debounced per-tab (`validateDebounceTimers`, keyed by tab — do not collapse back into a single shared timer, that previously caused validation for one tab to silently get cancelled by a validation request for another tab firing within the same 200ms window).
  - **Design note on `hasMagnetCutouts`**: the boolean toggle stays per-tab (bin and baseplate each keep their own checkbox/gating) while only the physical size (`magnetDiameter`/`magnetDepth`) moved into the shared Common panel — a single shared toggle would conflict with Light-baseplate-type gating, which needs to disable baseplate's magnet toggle independently of bin's.
  - **Light baseplate type gating**: when `baseplate.plateType === 'Light'`, magnet cutouts and screw holes are disabled in the UI with an explanatory hint (mirroring the pre-existing `extraBottomThickness`/`hasConnectionHoles` gating) — this reflects real gating already present in `baseplateGenerator.py` (`hasExtendedBottom`/`hasSkeletonizedBottom`), not a new generator-side restriction.
- **`commandCreateBin/`**, **`commandCreateBaseplate/`** — the legacy `CommandDialog`-based commands (same shape: `entry.py` builds `CommandInputs`, `commandConfig/` holds `ui_input_defaults*.json`). No longer registered/reachable from `commands/__init__.py`. **Slated for deletion** once the new palette is verified working end-to-end in Fusion — not yet removed. Do not build new features on top of these.
- **`lib/ui/commandUiState.py`** — the `CommandUiState`/`SingleInputState` abstraction the legacy dialogs used to bind `CommandInput` widgets to persisted JSON. Unused by the palette UI. Also slated for deletion alongside the legacy commands above — check with the user before deleting; keep `lib/ui/unsupportedDesignTypeException.py` (still raised by `generation.py`).

When the legacy commands are eventually deleted, this section should be trimmed down to just the `commandGridfinityPalette/` description.

### Geometry generation (`lib/gridfinityUtils/`)
Unchanged by the palette migration — this is where the actual solid-body construction happens, using the Fusion 360 API (`adsk.fusion`) to build sketches, extrude/patch/pattern/shell/fillet features, and boolean-combine bodies. Key modules:
- `const.py` — all Gridfinity standard dimensions (wall thickness, clearances, base/lip heights, tab/scoop sizes, screw/magnet cutout sizes) as module-level constants in centimeters (Fusion 360's internal unit). Change these only to alter the physical Gridfinity spec defaults, not per-command behavior.
- `baseGenerator.py` / `baseGeneratorInput.py` — the Gridfinity "base" (the stacking foot profile shared by both bins and baseplates).
- `binBodyGenerator.py` / `binBodyGeneratorInput.py` — the bin's hollow/shelled/solid body, including `uniformCompartments` and compartment layout.
- `binBodyCutoutGenerator.py`, `binBodyLipGenerator.py`, `binBodyTabGenerator.py` (+ matching `*Input.py`) — bin sub-features: interior compartment cutouts, the stacking lip, and the pull/label tab.
- `baseplateGenerator.py` / `baseplateGeneratorInput.py` — the baseplate body.
- Low-level geometry helpers used across generators: `sketchUtils.py`, `shapeUtils.py`, `extrudeUtils.py`, `combineUtils.py` (boolean join/cut), `filletUtils.py`, `edgeUtils.py`, `faceUtils.py`, `shellUtils.py`, `geometryUtils.py`, `patternUtils.py`, `commonUtils.py`.

**Input-object pattern**: every generator function takes a corresponding `*GeneratorInput` object (e.g. `BaseGeneratorInput`, `BinBodyGeneratorInput`) rather than a long parameter list. These input classes use Python `@property`/setter pairs for every field (not plain attributes) and set sensible defaults from `const.py` in `__init__`. When extending a generator with a new parameter, add a property to its `*Input` class following the existing getter/setter boilerplate style, then thread it through the generator function and `commandGridfinityPalette/generation.py`.

**Units**: Fusion 360's internal length unit is centimeters — all dimension constants and geometry code work in cm. The palette's form dicts also carry cm values matching the `*GeneratorInput` fields directly; `script.js` is responsible for mm↔cm conversion for on-screen display only.

### Shared utilities (`lib/`)
- `lib/fusion360utils/` — Autodesk's own add-in template helpers (event handler registration/cleanup, logging, error handling). Treat as vendored framework code.
- `lib/configUtils.py` — generic `.ini` (via `configparser`) and JSON config read/write helpers.
- `lib/ui/commandUiState.py` — legacy, see Commands section above.
- `lib/ui/unsupportedDesignTypeException.py` — raised when the active Fusion document isn't a supported design type (e.g. timeline disabled) for running a generator command.
