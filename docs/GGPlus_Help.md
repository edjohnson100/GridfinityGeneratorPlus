# GridfinityGenerator Plus

**A Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast, intuitive, and future-proof with creation settings that aren't lost to time.**

Version: 1.8.0.0

By Ed Johnson

November, 2026

---

## Introduction: The "Why" and "What"

The original GridfinityGenerator add-in is a great parametric bin/baseplate generator, but it works through two separate command dialogs that don't share settings, offer no preview before committing, and forget everything about how a part was built the moment you click OK — so revisiting a design months later, or handing the file to someone else, means starting from scratch. GridfinityGeneratorPlus keeps the original's proven geometry engine and rebuilds the interface and workflow around it.

**GridfinityGeneratorPlus** is a Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast, intuitive, and future-proof with creation settings that aren't lost to time.

---

## Attribution & License

GridfinityGeneratorPlus is a fork of [GridfinityGenerator](https://apps.autodesk.com/en/Publisher/PublisherHomepage?ID=46K9RTPEHCCN) by Lev Mishin ([GitHub](https://github.com/Le0Michine/FusionGridfinityGenerator)). All of the core parametric geometry — the base/foot profile, bin body construction, baseplate generation, magnet/screw cutouts, and the fundamental Gridfinity dimensioning — originates from Lev Mishin’s original work. This fork owes its existence to that foundation.

What changed in this fork is primarily the user interface (a single persistent palette replacing the original’s two separate command dialogs) and a set of new features built on top of the original generator, detailed below.

This project is distributed under the same license as the original: **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**. See LICENSE.md in the repository root for the full text. In short: you’re free to use, modify, and share this add-in and its source, including commercially-adjacent personal/hobbyist use, but not to sell it, and any derivative work must credit the original author and carry the same license.

---

## What’s New in GridfinityGeneratorPlus

If you’ve used the original GridfinityGenerator, here’s what’s different:Each of these is covered in its own section below.

| Area | Original | GridfinityGeneratorPlus |
| :---- | :---- | :---- |
| UI | Two separate command dialogs (Bin, Baseplate) | One persistent, dockable palette with tabs |
| Settings sharing | Base unit / clearance / magnet size duplicated per dialog | Shared “Common settings” panel keeps Bin and Baseplate in sync |
| Live preview | In-dialog only: a “Show auto update preview” checkbox (re-renders on every input change — can be slow for large bins) plus an “Update preview once” button for on-demand renders | A persistent, explicit **Update Preview** button — always on-demand, no auto-update-while-typing, with a visible preview body in the viewport that stays until you Generate or Clear Preview |
| Re-editing a generated part | Manual timeline editing in Fusion | **Edit Active Component** reloads the exact settings used to build it |
| Saved presets | None | Named, savable/loadable configurations per tab |
| Baseplate types | Light, Skeletonized, Full | Adds **Stackable** — a fourth type designed to physically stack |
| Grid sizing | Manual guesswork for custom (non-42mm) grids | **Grid Optimizer** tab recommends an optimal custom pitch from your real drawer/cabinet measurements |
| Whole-drawer layout | Not available | **Use this layout** (Grid Optimizer) tiles baseplates to your printer bed and builds a full drawer of baseplates and bins as one component |
| Non-rectangular drawers | Not available | **Edit drawer shape** removes cells from a drawer; baseplates are cut to fit and bins can be any connected shape (e.g. an L) |
| Appearance | Fixed light theme | **Themes** tab — built-in themes, OS dark-mode following, and importable custom themes (single `.theme.json` or a multi-theme `style.css` bundle) |
| Window state | Resets every session | Palette size/position/docking remembered across sessions |

---

## General Usage Instructions

**Install the add-in.** Unlike the original (distributed via the Fusion App Store), GridfinityGeneratorPlus is currently installed manually: in Fusion, go to **Utilities → Add-Ins → Scripts and Add-Ins**, and add this folder as an add-in. See [Installation / Uninstallation](#bookmark=id.q8d08gdrh1si) below for details.

**Open the palette.** In the **DESIGN** workspace, find the **SOLID** toolbar panel’s **CREATE** dropdown and select **“GridfinityGeneratorPlus.”** This opens (or brings forward) the palette, which stays docked and open across your session — you don’t need to reopen it for every bin or baseplate.

**Set your Common settings.** At the top of the palette, above the tabs, set your base grid unit (default 42mm), XY clearance, and magnet cutout size once — these are shared by both the Bin and Baseplate tabs so they always stay compatible with each other.

**Pick a tab and set your parameters.** Switch between **Bin**, **Baseplate**, **Grid Optimizer**, and **Themes** using the tab strip. Each field group is a collapsible section — expand or collapse what you need, including the **Common Settings** panel above the tabs. To keep a first launch simple, most sections start collapsed (Bin: Compartments through Configurations; Baseplate: Stacking through Configurations; plus Common Settings); the palette remembers which ones you open or close, **Expand all / Collapse all** under the tabs act on the current tab, and a collapsed section opens itself if it contains a validation error. A collapsed section’s header shows a one-line summary of its current setting (for example “Scoop · on”, or the active preset name on Configurations).

**Hover the ⓘ icons** next to the dimension and unit settings for short explanations. Sizes labelled **(units)** are Gridfinity grid units, not millimetres: width/length count 42 mm grid cells and height counts 7 mm vertical units (both Gridfinity standards, and both editable via Common Settings / Height unit). A bin’s stacking lip adds a further fixed 3.8 mm on top, so a 5-unit bin with a lip is 5 × 7 + 3.8 = 38.8 mm tall. The 3.8 mm lip is fixed in the add-in. The millimetre size is always shown under the bin’s dimensions as **Actual size**.

**Preview, then Generate.** Click **Update Preview** to see the result in the viewport before committing to anything (this can be re-run as many times as you like, replacing the previous preview). When you’re happy with it, click **Generate** to make it a permanent part of your design. **Clear Preview** removes a preview without generating.

**Revisit or fix a mistake later.** Hover over a previously generated Gridfinity component in the Fusion browser and click the radio button that appears to its right to activate it, then click **Edit Active Component** in the palette — this reloads the exact settings used to create it, so you can tweak and regenerate it in place. See [Edit Active Component](#bookmark=id.wncxlkcc67gc) below.

---

## The Palette Tabs

### Bin

Generates a parametric Gridfinity bin: overall size (in grid units), wall type (Hollow/Shelled/Solid), stacking lip, uniform or custom compartment grid, scoop (on any combination of the Front, Left, Back, and Right sides — Front by default), label tab, base screw holes, and magnet cutouts. This is a direct continuation of the original’s bin generator — the underlying geometry logic is Lev Mishin’s.

**Half-unit edges** *(new in this fork)*: check **Left**, **Right**, **Front**, and/or **Back** to add a half-unit-wide strip to that edge of the bin. Where two adjacent checked edges meet at a corner, that cell becomes quarter-size automatically — no extra configuration needed. Width/length can be **0** if the corresponding pair of half-edges (Left+Right, or Front+Back) supplies the whole dimension on that axis, letting you build a bin entirely out of half- and quarter-size cells. Magnet/screw cutouts and lip notches are placed per-module, but magnet/screw cutouts only ever apply to true full-size cells.

**Bin tab layout:** **Configurations** sits at the top of the tab; **Advanced** (lip notches, magnet cutout tabs) is a separate collapsed section. Value fields such as scoop radius, label tab length/width/position/angle, and screw hole diameter are grayed out until their checkbox is checked.

###  

### Baseplate

Generates a parametric Gridfinity baseplate. Four types are available:

* **Light** — thin, minimal-material baseplate, no magnet/screw cutouts.

* **Skeletonized** — lattice-cut bottom to save material, with connection holes.

* **Full** — solid extended bottom, with magnet and screw cutouts.

* **Stackable** *(new in this fork)* — see below.

**Side padding** adds extra solid material outside the grid, in millimetres, on the **Left, Back, Right, and Front** sides (matching Fusion’s view cube; these were labelled Top/Bottom before v1.5). The four padding fields and the screw-hole and connection-hole diameters are grayed out until their checkbox is checked.

**Half-unit edges** *(new in this fork)*: same **Left/Right/Front/Back** checkboxes as the Bin tab, available for all four plate types. A Skeletonized baseplate's decorative bottom groove pattern only applies to true full-size cells — half and quarter cells from checked edges stay solid, same as a Full-type cell.

**DXF-ready sketch for laser cutting** *(new in this fork)*: check **Generate DXF-ready sketch** to add a sketch of the plate's mid-height cross-section, on its own construction plane, which you can export to DXF or SVG by hand from Fusion (this add-in doesn't generate the file itself, so you can use whichever export tool you prefer). Useful for laser-cutting baseplates out of thin sheet material — verified working for the Light and Stackable types.

#### *Stackable baseplates (new)*

A Stackable baseplate is built like a Light baseplate, then made **symmetric top-to-bottom** — the plate is split exactly at its mid-height, the discarded half is cleanly removed, and the remaining half is mirrored back onto itself. This removes the overhang that would otherwise prevent two plates from nesting, so stackable plates can be printed and physically stacked with no unsupported overhangs.

Set a **Stack Count** greater than 1 to generate a whole stack in one operation: a thin **Interface Layer** spacer (thickness configurable — a good starting point is 1–2× your 3D printer’s layer height) is generated between each plate, extruded to exactly match the plate’s real top-surface profile. Interface layers get a visibly contrasting color so they’re easy to distinguish from the baseplates in the viewport, and every body in the stack is clearly and predictably named (Baseplate\_01, Baseplate\_02, … / Interface\_01, Interface\_02, …).

For best results, a **Clearance between baseplate and bin** of at least 1–1.5mm is recommended when using Stackable — the palette will show a hint reminding you of this when the Stackable type is selected.

**Credit:** the split-mirror stacking technique used here is based on the method demonstrated by **James at [Clough42](https://www.youtube.com/@Clough42)** on YouTube, in [*Gridfinity in the Machine Shop: 3D Printed Metrology Toolbox Organization*](https://www.youtube.com/watch?v=RYA0xLryF-g). Many thanks for sharing it.

### 

### Grid Optimizer (new)

If you’re building a custom (non-standard-42mm) grid to fit a specific drawer or cabinet, the Grid Optimizer tab helps you pick a grid pitch that minimizes wasted space, instead of guessing.

1. Add one or more **dimensions** — a description plus width and depth for each opening you’re planning to fill (e.g. “Kitchen Drawer,” “Workbench Cabinet”).

2. Set a **search range** (min/max grid size in mm) and whether **half-size bins** should be credited when scoring candidate sizes — this can noticeably change which size comes out on top, so it’s an explicit toggle rather than a hidden assumption.

3. Choose whether to **optimize for width, depth, balance both, or ignore one entirely** — useful if, for example, you don’t care about wasted space at the back of a drawer and only want the front-facing width to fit cleanly.

4. Click **Calculate** to see the recommended grid size, the total leftover space, and a per-dimension breakdown, with an optional side-by-side comparison against the standard 42mm grid.

Click any column heading (**Description**, **Width**, or **Depth**) to sort the dimensions table by that column, click again to reverse the order — handy for scanning a long list. Newly added dimensions slot into the current sort automatically. The order you leave the table in is what gets saved when you save or update a set.

#### Laying out a whole drawer (Use this layout)

After you Calculate, **Use this layout** turns one opening at a time into a complete set of baseplates and bins.

1. **What to generate:** the **Generate baseplates** and **Generate bins** checkboxes at the top choose whether the drawer gets baseplates, bins, or both (both use the same drawer shape).
2. **Grid and printer bed:** pick the grid (the calculated optimum, the standard 42 mm grid, or the **Common Settings grid unit**, whose base width and length must be equal), the opening to lay out, and the printer bed. Baseplates are split into the fewest tiles that fit; half-unit edges go only on the outer tiles and leftover space becomes outer padding. The bed is remembered between sessions and saved with each set. An optional **bin printer bed** adds a reference line and a warning for oversized bins (never a limit).
3. **Show tiled layout** draws the schematic (the button becomes **Hide tiled layout**, which clears the view and any hand-drawn bins or shape).
4. **Drawer shape:** **Edit drawer shape** lets you click cells out of (or back into) the drawer to make L-shapes, notches or cut corners; gray cells are outside the drawer. **Reset to rectangle** undoes it. Where the leftover space goes is set here too: **Padding location**, left/right (centered, left, right) and front/back (centered, front, back), applied to the drawer's bounding box. With **Cut removed cells out of larger plates** on, the whole drawer is tiled to the printer bed first and the gray cells are cut out of those plates ("Removed cells" steps before the Final baseplate cut, with rounded corners), giving fewer, bigger baseplates; a tile whose cells end up in separate pieces falls back to plain rectangles. Turn it off to always use plain rectangular plates.
5. **Bins:** pick the fill: one bin per tile, **uniform** bins up to a max size, a **mixed-size list** (e.g. `2x2, 1x1`, always topped up with 1x1), or **Draw bins by hand**. With a per-tile panel you can override the fill for one tile. To draw by hand, click **Add a bin**, then click the cells that make up the bin (any connected shape, such as an L) or click one corner cell and **Shift+click** the opposite corner to fill a rectangle, then **Save bin**. Bins can cross baseplate boundaries, and **Fill empty cells with 1x1 bins** completes a layout. A shape that isn't a plain rectangle becomes one irregular bin: base, outline walls and one open cavity, with no lip, scoop, label tab or compartments yet (Shelled is built Hollow).
6. **Drawer details** lists each tile and the Baseplate/Bin settings the drawer will use.
7. **Build:** **Update Preview** and **Generate drawer** in the pinned bar build the drawer for review and finalize it, as one nested component and one Undo step, with a progress dialog you can cancel. The drawer uses the current Baseplate and Bin tab settings (Light, Full or Skeletonized baseplates; Stackable is not supported). The pieces of a drawer, including irregular bins, can't be re-opened with Edit Active Component; rebuild the drawer instead.

**Send opening to Baseplate tab** fills the Baseplate form for a single opening instead (forced to Light, stack count 1).

Dimension lists can be saved as named, reloadable sets (e.g. “Kitchen Drawers,” “Workbench Cabinet”) just like Bin and Baseplate configurations.

### Themes (new)

Customize the palette's appearance. The theme selector lives in the **header at the top of the palette** (not on this tab) — choose **System** (follows your OS's light/dark setting automatically — the default), or one of the built-in themes: **Light**, **Dark**, **Midnight**, or **Sandstone**. You can also import custom themes from the Themes tab below — every theme you import is remembered and stays available in the header dropdown across restarts, whether or not it's the one currently active. Sample themes are provided in the resources/themes/ folder.

Two additional controls apply on top of whichever theme is selected:

- **Font family** — Sans-serif, Serif, or Monospace.  
- **Base font size (px)** — scales the whole palette (text, buttons, dropdowns, and text fields); hint and error text scale proportionally with it.

Once you're happy with a look (including any font tweaks), click **Export theme.json…** to save it as a shareable file — this captures the full effective theme, whether it started as a built-in or an imported one. **Import theme.json…** brings one back in. For backing up or sharing several custom themes at once, **Export style.css…** / **Import style.css…** bundle every custom theme's colors into (or out of) a single CSS file (one `:root[data-theme="Name"]` block per theme) — built-in-named blocks are skipped on import, since the built-in themes can't be overridden this way. **Remove imported theme** deletes a theme you previously imported (disabled for the built-in themes, which can't be removed); re-importing a theme with the same name as an existing one simply overwrites it, so there's no need to remove one before importing an updated version of it. **Factory Reset** permanently clears every imported theme and resets the font controls back to default — it asks for confirmation first, since it can't be undone.

---

## 

## Configurations (Saved Presets)

Each of the Bin, Baseplate, and Grid Optimizer tabs has a **Configurations** (or **Saved sets**) section, showing an **Active config** status line and letting you:

- **Save As…** — opens a dialog to save the current field values as a new named preset.  
- **Update Current** — overwrite the active preset with the current values, no dialog.  
- **Load…** — opens a dialog listing your saved presets; pick one and click Load.  
- **Delete…** — opens the same kind of dialog to pick a preset to remove.  
- **Factory Reset** — revert the tab to its built-in defaults. On Bin or Baseplate, this also resets the shared Common settings panel (and resetting Common resets both Bin and Baseplate back), since they're meant to stay in sync — Grid Optimizer's reset stays independent, since it doesn't use Common.

Bin and Baseplate presets also remember the Common settings panel’s values at the time they were saved (base unit, clearance, magnet size) and restore them on load — so loading a preset always reproduces the exact grid it was originally designed for, even if you’ve since changed the Common panel for other work.

---

## 

## Edit Active Component (re-editing a generated part)

Every part generated with this add-in remembers its own settings — the exact parameters you used are stored directly on the component as a Fusion component attribute, not in a separate file or database. That means:

* **Reopening a saved design months or years later**, the settings for every Gridfinity part you generated are still there, ready to be reloaded and adjusted.

* **Sharing your design file with someone else** who also has GridfinityGeneratorPlus installed carries the settings along with it — they can pick up right where you left off.

To use it: hover over the component you want to change in the Fusion browser tree and click the radio button that appears to its right to activate it, then click **Edit Active Component** at the top of the palette. The palette reloads with the exact settings that built that part, on whichever tab it belongs to. From there, adjust anything you like and click **Update Preview** to see the change, or **Generate** to make it permanent again.

**Note:** this requires the design to be in **Hybrid** design mode (Document Settings → Design → Hybrid) — this is what allows each generated part to own and carry its own settings. **Update Preview** and **Generate** show a dialog if the active document isn’t set to Hybrid, with steps to convert it (Browser → Document Settings → hover the Design Type → pencil icon → Hybrid Design → Convert); your entered field values are never lost, so you can simply convert and try again.

---

## Screenshots

**Screenshot:** \[PLACEHOLDER\] overview collage or additional supplementary screenshots as needed. Additional screenshots

---

## Commands

| Command | Description |
| :---- | :---- |
| **GridfinityGeneratorPlus** | Opens the GridfinityGeneratorPlus palette (Solid Create panel). The palette stays open and docked; use its tabs to switch between Bin, Baseplate, Grid Optimizer, and Themes. |

*(The original GridfinityGenerator exposed two separate commands, “Gridfinity bin” and “Gridfinity baseplate,” each opening its own dialog. This fork consolidates both — and the newer tabs — into the single palette command above.)*

---

## 

## Installation / Uninstallation

GridfinityGeneratorPlus is not currently distributed via the Fusion App Store. To install it manually:

1. Download or clone this repository to a folder on your computer.

2. In Fusion, open **Utilities → Add-Ins → Scripts and Add-Ins** (or press Shift+S).

3. On the **Add-Ins** tab, click the green **\+** and select this repository’s folder (or point Fusion at the GridfinityGeneratorPlus.manifest file within it).

4. Select **GridfinityGeneratorPlus** in the list and click **Run**. Check **Run on Startup** if you want it to load automatically in future Fusion sessions.

To uninstall or stop the add-in:

* Click **Stop** in the Add-Ins dialog to unload it for the current session without removing it.

* Uncheck **Run on Startup** to stop it from loading automatically.

* To fully remove it, delete the folder you installed it to and remove any add-in reference Fusion may still show in the Add-Ins list (right-click → Delete, or use the “−” button).

Because this fork can run independently from the original GridfinityGenerator, both can be installed side-by-side without ID collisions — no need to uninstall one to use the other.

---

## Support

This is an independent, community fork. For issues, questions, or feature requests specific to **GridfinityGeneratorPlus**, please use this repository’s own GitHub Issues page.

For questions about the underlying Gridfinity geometry generation that predates this fork, the original project’s resources may also be useful:

* Original project: [github.com/Le0Michine/FusionGridfinityGenerator](https://github.com/Le0Michine/FusionGridfinityGenerator)

* Original project wiki: [github.com/Le0Michine/FusionGridfinityGenerator/wiki](https://github.com/Le0Michine/FusionGridfinityGenerator/wiki)

* Gridfinity standard: [gridfinity.xyz](https://gridfinity.xyz/)

---

## 

## Development History

A condensed summary of major milestones:

- **Palette UI migration** — replaced the original's two separate command dialogs with a single persistent, dockable HTML palette.  
- **Common settings panel, config manager, persistent preview workflow** — shared Bin/Baseplate settings, named saved presets, and an explicit Update Preview / Generate / Clear Preview workflow across the palette (replacing the original's in-dialog auto-update/on-demand preview toggle).  
- **Edit Active Component** — re-edit a previously generated part by reloading the settings stored on it as a Fusion component attribute.  
- **Grid Optimizer tab** — recommends an optimal custom grid pitch from user-entered drawer/cabinet dimensions.  
- **Stackable baseplate type** — a fourth baseplate type, symmetric top-to-bottom for physical stacking, with configurable interface layers.  
- **Theme tab** — customizable palette appearance with built-in and importable custom themes, plus font family/size controls, theme export, and removing imported themes.  
- **Preview and Generate require Hybrid design intent** — guarantees every generated part can carry its own settings for later editing or sharing.  
- **Grouped Undo & Undo/Redo-aware preview tracking** — Update Preview/Generate each collapse to a single Undo step, and the Clear Preview button stays correctly in sync as you step through Fusion's Undo/Redo.  
- **Redesigned Configurations manager & themed dialogs** — Load/Delete/Save As now open focused dialogs instead of sharing an inline dropdown, and every popup in the palette (including a warning before an Update Preview/Generate on one tab would discard an unfinalized preview on the other) uses a themed dialog matching the palette instead of a native browser popup.
- **Bin base bottom-edge notch fix** — multi-cell bins no longer show a small notch at interior grid seams along the outer bottom edge; the base is now built at its final size from the first sketch instead of being reshaped by a separate step afterward.
- **Stacked baseplate tripling fix (v1.1.2)** — Stackable baseplates with Stack Count > 1 no longer silently produce 3x the expected bodies on export/slicing; a shared pattern-feature helper was leaving Fusion's default second-direction quantity active.
- **DXF-ready sketch for laser-cut baseplates (v1.2.0)** — new opt-in sketch of a baseplate's mid-height cross-section, for manual DXF/SVG export and laser-cutting.
- **Half-unit edge support for bins and baseplates (v1.2.0)** — Left/Right/Front/Back checkboxes add a half-unit-wide strip to any edge, with corners between two checked edges becoming quarter-size automatically; core width/length can be 0 when half-edges supply the rest of that axis.
- ~~**Bin foot alignment fix (v1.2.0)** — bin stacking feet now center correctly within each baseplate grid opening instead of sitting `xyClearance` off-center.~~ *(Superseded by v1.2.1 — this fix was incomplete and caused a Shelled-bin crash; see below.)*
- **Shelled-bin crash fix (v1.2.1)** — reverted the v1.2.0 bin-foot alignment shift, which desynced the bin foot from the bin body's wall and caused Shelled-type bins to fail generation with an `ASM_REM_NO_SOLUTION` error.
- **Off-center baseplate cutout fix (v1.2.1)** — corrected the actual root cause of the off-center grid openings (an incorrect clearance offset in the baseplate cutout geometry itself), now centered evenly on all four sides.
- **Palette header & tab bar fixes (v1.3.0)** — the palette gained a header bar (title, version, theme selector) at the top, matching the layout used across Ed's other Fusion add-ins; the theme selector moved here from the Theme tab. Also fixed inconsistent tab-button CSS that was drawing a boxed border around every tab instead of the intended flat underline style.
- **Fleet UI standardization completed, plus an accessibility pass (v1.4.0)** — the "Theme" tab is renamed **Themes** (plural) and its content restructured to match the fleet standard; **Common Settings** is now collapsible like every other panel; the Themes tab gained CSS-bundle (`style.css`) import/export alongside the existing single-theme `.theme.json` import/export, and a Factory Reset button for clearing every imported theme at once. Separately, every button's foreground color now goes through a themed `--btn-primary-text`/`--btn-danger-text` variable (checked against WCAG AA contrast per built-in theme — Midnight and Sandstone needed dark text, not white, on their bright accent buttons), every interactive element shows a visible keyboard-only focus ring, and the confirmation-modal backdrop is themed instead of a fixed black tint.
- **Font controls now reach every element (v1.4.1)** — Font Family/Base Font Size on the Themes tab previously only scaled body text; buttons, dropdowns, and text fields silently kept the browser's default UI font. Fixed fleet-wide with an explicit font inheritance rule for form controls.
- **Multi-monitor palette visibility fix (v1.4.2)** — Fusion won't draw a floating palette outside the display its own main window occupies, so a palette last parked on a second monitor could go silently invisible when Fusion was later opened on a different one. The saved position is now checked against Fusion's actual display on open and remapped onto it at the same relative spot when they don't match. A new standalone `PaletteDisplayCheck` script reports monitor layout and the saved-position verdict for troubleshooting.
- **Calmer first launch, remembered sections, tooltips, and UI polish (v1.5)** — most sections start collapsed with live one-line summaries in their headers, open/closed state is remembered, Expand all / Collapse all and auto-open-on-error were added, ⓘ tooltips explain grid units vs. millimetres (and the Grid Optimizer’s settings), Configurations moved to the top of the Bin and Baseplate tabs, Bin gained an Advanced section, dependent fields gray out until their checkbox is on, checkboxes are left-aligned, and baseplate padding labels now use Left/Back/Right/Front.
- **Whole-drawer layouts, instant Generate and scoop fixes (v1.7)** — the Grid Optimizer can lay out and build a full drawer of baseplates (tiled to your printer bed) and bins (auto-filled or hand-drawn, crossing seams) as one nested component; Generate now just finalizes an unchanged preview instead of rebuilding it; more collapsed-section summaries; and left/right scoops on narrow bins no longer fail.
- **Pinned action bar & single toast (v1.7.1)** — Update Preview / Generate / Clear Preview and notifications are pinned to the bottom of the palette, and a just-generated part is no longer mistaken for a preview.
- **Non-rectangular drawers (v1.8)** — drawers can be any rectilinear shape: click cells out of the drawer, choose where padding goes, build baseplates and bins independently, cut the missing cells out of bed-sized baseplates (with rounded corners), and draw bins of any connected shape by clicking cells or Shift+clicking a rectangle. The drawer section was also reorganized into collapsible sub-sections, with its Preview/Generate buttons moved to the pinned bar.

---

*GridfinityGeneratorPlus — a fork of [GridfinityGenerator](https://github.com/Le0Michine/FusionGridfinityGenerator) by Lev Mishin. Licensed under CC BY-NC-SA 4.0.*
