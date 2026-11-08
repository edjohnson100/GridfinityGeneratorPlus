# GridfinityGeneratorPlus

Version: 1.7.1.0

By Ed Johnson (Making With An EdJ)

November, 2026

**A Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast, intuitive, and future-proof with creation settings that aren't lost to time.**

<img src="GFPlusAppIcon.png" alt="App Icon" width="300">

## Introduction: The "Why" and "What"

The original GridfinityGenerator add-in is a great parametric bin/baseplate generator, but it works through two separate command dialogs that don't share settings, offer no preview before committing, and forget everything about how a part was built the moment you click OK — so revisiting a design months later, or handing the file to someone else, means starting from scratch. GridfinityGeneratorPlus keeps the original's proven geometry engine and rebuilds the interface and workflow around it.

**GridfinityGeneratorPlus** is a Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast and durable.

* **Feature 1: One persistent palette, not two dialogs.** Bin, Baseplate, Grid Optimizer, and Theme all live in a single dockable palette with shared "Common settings," live Update Preview / Generate / Clear Preview, and named saved configurations per tab.
* **Feature 2: Settings travel with the file.** Every generated part remembers the exact parameters that built it, stored directly on the component itself. Reopen a design months later, or share the `.f3d` with someone else running this add-in, and click **Edit Active Component** to pick up right where you left off.
* **Feature 3: Grid Optimizer.** Building a custom (non-42mm) grid to fit a specific drawer or cabinet? Enter your real measurements and let the optimizer recommend a pitch that minimizes wasted space, instead of guessing.
* **Feature 4: Stackable baseplates.** A fourth baseplate type, made symmetric top-to-bottom so it can be printed and physically stacked with no overhang, with configurable interface layers between plates.
* **Feature 5: Themes tab.** Customize the palette's appearance — built-in themes, automatic OS dark-mode following, and import/export of your own custom themes as either a single `.theme.json` file or a multi-theme `style.css` bundle.
* **Feature 6: Half-unit grid support & DXF export for laser cutting.** Add a half-unit-wide strip to any edge (Left/Right/Front/Back) of a bin or baseplate — where two checked edges meet at a corner, that cell automatically becomes quarter-size, no extra configuration needed. Baseplates can also generate a DXF-ready sketch for laser-cut fabrication.

* **Feature 7: Whole-drawer layouts.** From a Grid Optimizer result, lay out and build a complete drawer in one step: baseplates auto-tiled to your printer bed, plus bins auto-filled or drawn by hand, all as one nested component.

---
## ✨ What's New in v1.7.1

* **Pinned action bar.** Update Preview, Generate and Clear Preview now sit in a bar pinned to the bottom of the palette, always visible however far you've scrolled. They act on the active tab (Bin or Baseplate). The add-in title and version live in the same bar.
* **One toast, always visible.** Notifications used to appear twice (a top bar plus a per-tab bar). There is now a single toast in the pinned bar.
* **Fixed: a just-generated part was treated as a preview again.** After Preview → Generate, the next Update Preview deleted the generated component, and switching Bin/Baseplate showed a spurious "Replace preview?" prompt.
* **Zero-size bins and baseplates.** A width/length of 0 is accepted when a matching half-unit edge is checked (e.g. a half-size bin).
* **Too-small compartments are caught.** A compartment grid whose cells are too small to build is now flagged on the Grid width/length fields instead of failing during Generate.

---
## ✨ What's New in v1.7

* **Whole-drawer layouts (Grid Optimizer tab).** After you Calculate, the new **Use this layout** section turns an opening into a full set of baseplates and bins:
  * **Choose the grid:** the calculated optimum, the standard 42 mm grid, or the **Common Settings grid unit**.
  * **Baseplates are tiled to your printer bed.** Enter the bed size (remembered, and saved with each set so different printers can have different beds); half-unit edges go only on the outer tiles and leftover space becomes outer padding. A schematic shows the tiles and bins.
  * **Bins:** one per tile, uniform N×M, a mixed-size list (e.g. `2x2, 1x1`), or **draw them by hand** on a drawer-wide grid, where bins can cross baseplate seams. An optional bin printer bed shows a reference and a warning for oversized bins, never a restriction.
  * **Update Preview / Generate drawer** builds everything as one nested component with a progress dialog (cancelable), the viewport framed on the whole drawer, parts appearing as they are made, sketches hidden, and one Undo step. Identical pieces are built once and re-placed.
  * **Send opening to Baseplate tab** and **Apply grid size to Common** are also available. Drawers use Light, Full or Skeletonized baseplates (Stackable is not supported).
* **Generate promotes an unchanged preview.** If the live preview was built from exactly the current settings, Generate just finalizes it, with no rebuild and no waiting.
* **Collapsed-section summaries** on Bin (Basic size, Dimensions, Body) and Baseplate (Main dimensions, Features).
* **Scoop fixes:** left/right scoops on narrow (1u or half-width) bins no longer fail, scoop radius is limited to what fits in the bin's width/length, and the unavoidable skipped back-edge rounding no longer logs errors.

---
## ✨ What's New in v1.6

* **Scoop on any side.** Front / Left / Back / Right checkboxes in the Scoop section (enabled when **Add scoop** is checked); any combination works, and selected sides blend at the corners. Front is the default, so existing configurations are unchanged.
* **Hybrid Design is required for Preview and Generate**, with a clear dialog explaining how to convert the design.
* **Better tooltips and small fixes** for Scoop max radius and Tab position, plus a fix for an error logged when the Tab position field was cleared.

---
## ✨ What's New in v1.5

* **A calmer first launch.** Most sections now start collapsed (Bin: Compartments through Configurations; Baseplate: Stacking through Configurations; plus Common Settings), so new users can walk down the options and open them as needed. Which sections you open or close is remembered between sessions, **Expand all / Collapse all** links sit under the tabs, and a collapsed section opens itself if it holds a validation error. Collapsed headers show a live one-line summary (e.g. "Scoop · on", "Configurations · MyPreset").
* **Explanatory tooltips.** New ⓘ tooltips on the unit and dimension settings explain Gridfinity units vs. millimetres, quote the Gridfinity standards (42 mm grid, 7 mm height unit, 3.8 mm stacking lip) and say *why* each setting exists. Labels now read "(units)" instead of "(u)". The Grid Optimizer has tooltips too.
* **Configurations moved to the top** of the Bin and Baseplate tabs, and a new Bin **Advanced** section holds lip notches and magnet cutout tabs.
* **Fields gray out when their checkbox is off** (scoop radius, label tab values, screw hole diameters, baseplate side padding, connection hole diameter), and **checkboxes are now left-aligned** next to their text.
* **Consistent directions.** Baseplate side padding is now Left/Back/Right/Front, matching Fusion's view cube and the half-unit edge checkboxes (formerly Top/Bottom). Saved presets are unaffected.

## ✨ What's New in v1.4.2

* **Fixed the palette going invisible on multi-monitor setups.** If the palette was last parked on a second monitor and Fusion is later opened with its main window on a different monitor, Fusion refuses to draw a floating palette outside its own display — so the palette would silently fail to appear. The saved position is now checked against Fusion's actual display on open and remapped onto it when they don't match, at the same relative spot. A new standalone `PaletteDisplayCheck` script (Scripts and Add-Ins → Scripts) reports monitor layout, Fusion's window, and the saved position for troubleshooting.

## ✨ What's New in v1.4.1

* **Font Family/Base Font Size now actually reach every control.** A gap in the fleet accessibility pass: buttons, dropdowns, and text fields in the palette were silently ignoring the Themes tab's font settings (only body text scaled) because browsers don't apply an ancestor's font to form controls by default. Fixed — every interactive control in the palette now tracks Font Family and Base Font Size correctly.

## ✨ What's New in v1.4.0

* **Fleet UI standardization, completed.** This add-in's palette now matches the structural standard shared across Ed's Fusion add-in fleet: the "Theme" tab is renamed **Themes** (plural), and **Common Settings** is now a collapsible section like every other panel in the palette, instead of an always-expanded box.
* **CSS-bundle theme import/export.** Alongside the existing single-theme `.theme.json` import/export, the Themes tab can now import/export a multi-theme `style.css` bundle (one `:root[data-theme="Name"]` block per custom theme) — useful for backing up or sharing several custom themes at once.
* **Factory Reset for Themes.** A new Factory Reset button on the Themes tab permanently clears every imported theme and resets font settings back to default (with a confirmation prompt first, since it can't be undone).
* **Accessibility pass.** Every button's text color now goes through a themed `--btn-primary-text`/`--btn-danger-text` variable instead of a hardcoded white, checked against WCAG AA contrast for all four built-in themes (Midnight and Sandstone's bright accent buttons needed dark text, not white, to stay readable). Keyboard (Tab) focus is now visibly outlined on every button, input, dropdown, and collapsible section header, without adding an outline on mouse clicks. The confirmation-modal backdrop is also now themed instead of a fixed black tint.

## ✨ What's New in v1.3.0

* **New palette header.** The palette now has a header bar at the top with the add-in title, version, and the theme selector (moved here from the Theme tab, which still holds font family/size, import/export, and Remove Selected Theme).
* **Tab bar visual fix.** Corrected inconsistent CSS that was giving every tab button a boxed border instead of the intended flat underline style.

## ✨ What's New in v1.2.1

* **Fixed a crash generating Shelled bins.** Shelled-type bins could fail to generate with a `Shell1 / Compute Failed // ASM_REM_NO_SOLUTION` error, caused by a bin-foot/wall alignment change shipped in v1.2.0 (see below). Reverted — Shelled bins generate correctly again.
* **Fixed off-center baseplate cutout openings.** Baseplate grid openings had `xyClearance` more slack on the back/right of each cell than the front/left, so bin feet sat visibly off-center in the opening. Now centered evenly on all four sides.

## ✨ What's New in v1.2.0

* **Half-unit edge support for bins and baseplates.** New Left/Right/Front/Back checkboxes on both tabs add a half-unit-wide strip to that edge; where two adjacent checked edges meet at a corner, that cell becomes quarter-size automatically. Core width/length can now be 0 when half-edges supply the rest of that axis — build a bin or baseplate entirely out of half- and quarter-size cells if you want to. Magnet/screw cutouts only ever apply to true full-size cells; a Skeletonized baseplate's decorative bottom groove is likewise full-cells-only, with half/quarter cells staying solid.
* **DXF-ready sketch for laser-cut baseplates.** New "Generate DXF-ready sketch" option on the Baseplate tab adds a sketch of the plate's mid-height cross-section that you can export to DXF/SVG by hand from Fusion, for laser-cutting baseplates out of thin sheet material.
* ~~**Bin foot alignment fix.** Bin stacking feet now center correctly within each baseplate grid opening — previously they sat `xyClearance` off-center, most noticeable on precise/tight-clearance prints.~~ *(Superseded by v1.2.1 — this fix was incomplete and caused a Shelled-bin crash; see above.)*

## ✨ What's New in v1.1.2

* **Fixed tripled bodies in stacked baseplates:** generating a Stackable baseplate with Stack Count > 1 silently produced 3x the expected baseplate/interface-layer bodies, all coincident in the Fusion viewport (so it looked correct there) but appearing as extra duplicate solids once exported/sliced. Root cause was a shared pattern-feature helper that only configured its first direction, leaving Fusion's own default second-direction quantity (3) active. If you've generated any Stackable baseplates with Stack Count > 1, regenerate them to pick up the fix.

## ✨ What's New in v1.1.1

* **Fixed a notch in the bin base's bottom edge:** multi-cell bins previously showed a small visible notch at every interior grid seam along the outer bottom edge. The base is now built at its final, clearance-adjusted size from the very first sketch instead of being reshaped by a separate step afterward, so the outer edge comes out clean — you'll now see a small (expected, spec-accurate) gap between adjacent unit cells' feet instead.
* **Dependent checkbox fixes:** unchecking **With lip** now also unchecks and disables **With lip notches** (re-enabling it when you check lip back on); unchecking **Add magnet cutouts** does the same for **Add magnet cutout tabs** — previously these could be left checked while their parent option was off.

## Installation

> **Tip:** For a stable, versioned copy, download the latest packaged release from the **Releases** link in the right-hand sidebar of this repo's GitHub page instead of using the green **Code** button above — the Code button always pulls the current `main` branch, which may include in-progress changes. Or, simply click this link to the [Releases page](https://github.com/edjohnson100/GridfinityGeneratorPlus/releases)

### Manual Installation Options

This add-in requires a quick manual installation. You can choose to install it in Fusion's default directory or a custom folder of your choice.

#### Option 1: Install in the Default Fusion Directory
1. **Download:** Download the source code as a ZIP file and extract the `GridfinityGeneratorPlus-main` folder. Rename the folder to `GridfinityGeneratorPlus` (remove the `-main` suffix) — Fusion requires the folder name to match the add-in name exactly, so it won't run correctly if you skip this step.
Download the zip file using the green `Code` button above or simply click this link: [GridfinityGeneratorPlus Main Branch](https://github.com/edjohnson100/GridfinityGeneratorPlus/archive/refs/heads/main.zip)
2. **Move the Folder:** Move the entire `GridfinityGeneratorPlus` folder into your native Fusion Add-Ins directory:
   * **Windows:** `%appdata%\Autodesk\Autodesk Fusion 360\API\Addins`
   * **Mac:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Addins`
3. **Open Fusion:** Press `Shift + S` to open the **Scripts and Add-Ins** dialog.
4. **Run the Add-in:** Make sure the **Add-ins** filter checkbox is checked. You should see **GridfinityGeneratorPlus** in the list of add-ins. You may want to check the 'Run on startup' option so it automatically runs when Fusion starts. Click the **Run** icon to execute the add-in.

#### Option 2: Install in a Custom Directory
1. **Download:** Download the source code as a ZIP file and extract the `GridfinityGeneratorPlus` folder. Rename the folder to `GridfinityGeneratorPlus`.
2. **Organize:** Create a dedicated folder on your computer for your Fusion tools (e.g., `Documents\Fusion_Tools`) and move the `GridfinityGeneratorPlus` folder inside it (remove the `-main` suffix) — Fusion requires the folder name to match the add-in name exactly, so it won't run correctly if you skip this step.
3. **Open Fusion:** Press `Shift + S` to open the **Scripts and Add-Ins** dialog.
4. **Add the Add-in:** Click the grey **"+"** icon next to the search box at the top of the dialog and select **Script or add-in from device**.
5. **Locate:** Navigate to your custom folder, select the `GridfinityGeneratorPlus` folder, and click **Select Folder**.
6. **Run the Add-in:** Make sure the **Add-ins** filter checkbox is checked. You should see **GridfinityGeneratorPlus** in the list of add-ins. You may want to check the 'Run on startup' option so it automatically runs when Fusion starts. Click the **Run** icon to execute the add-in.

## Using GridfinityGeneratorPlus

### The Gridfinity Generator Palette
In the **DESIGN** workspace, find the **SOLID** toolbar panel's **CREATE** dropdown and select **"GridfinityGeneratorPlus"** to open the palette. It stays docked and open across your session — set your Common settings once, then switch between tabs as needed.

* **Common settings panel:** base grid unit, XY clearance, and magnet cutout size, shared by both Bin and Baseplate so they always stay compatible with each other.
* **Update Preview / Generate / Clear Preview:** preview a part in the viewport before committing to it, make it permanent when you're happy, or discard the preview entirely.
* **Configurations:** save, load, and delete named presets per tab (Bin, Baseplate, Grid Optimizer), so a frequently-used setup is always one click away.
* **Collapsible sections & tooltips:** most sections start collapsed so a new user sees a short list of options; hover the ⓘ icons for plain-language explanations of units vs. millimetres. Your open/closed choices are remembered.

### Edit Active Component
Activate a previously generated Gridfinity part in the Fusion browser by hovering over the component name and clicking the radio button that appears to the righ of the name, then click **Edit Active Component** at the top of the palette — it reloads the exact settings used to build that part.

* **Tip:** this requires the design to be in **Hybrid** design mode (Document Settings → Design → Hybrid). If you click **Update Preview** or **Generate** in a Part or Assembly design, a dialog explains how to convert the design — your entered values aren't lost, so just convert and try again.

For the complete usage guide, including every tab, field, and workflow in detail, see [GGPlus_Help.md](docs/GGPlus_Help.md).

## Tech Stack

For the fellow coders and makers out there, here is how GridfinityGeneratorPlus was built:

* **Language:** Python (Fusion API)
* **Interface:** HTML/CSS/JavaScript (Palette)
* **Data Storage:** Each generated part's settings are stored as a Fusion component attribute directly tied to the component, so they travel with the `.f3d` file itself. Add-in preferences (window geometry, active theme), saved configurations, and imported themes are stored locally as JSON alongside the add-in.

## Acknowledgements & Credits

* **[Gridfinity by Zack Freedman](https://www.youtube.com/c/ZackFreedman/about)** 

* **Original Work:** GridfinityGeneratorPlus is a fork of **[GridfinityGenerator](https://github.com/Le0Michine/FusionGridfinityGenerator) by Lev Mishin**. The core parametric geometry — the base/foot profile, bin body construction, and baseplate generation — originates from his original work, without which this fork wouldn't exist.
* **Developer:** Ed Johnson ([Making With An EdJ](https://www.youtube.com/@makingwithanedj))
* **AI Assistance:** Developed with coding assistance from Claude (Anthropic).
* **Lucy (The Cavachon Puppy):**
***Chief Wellness Officer & Director of Mandatory Breaks***
    * Thank you for ensuring I maintained healthy circulation by interrupting my deep coding sessions with urgent requests for play.
* **License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

---

## ❤️ Support the Maker (and Lucy!)

I develop these tools to improve my own workflows and love sharing them with the community. If you find GridfinityGeneratorPlus useful and want to say thanks, feel free to **[buy Lucy a dog treat on Ko-fi](https://ko-fi.com/makingwithanedj)**!

***

*Happy Making!*
*— EdJ*
