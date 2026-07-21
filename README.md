# GridfinityGeneratorPlus

Version: 1.2.0.0

By Ed Johnson (Making With An EdJ)

July, 2026

**A Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast, intuitive, and future-proof with creation settings that aren't lost to time.**

<img src="GFPlusAppIcon.png" alt="App Icon" width="300">

## Introduction: The "Why" and "What"

The original GridfinityGenerator add-in is a great parametric bin/baseplate generator, but it works through two separate command dialogs that don't share settings, offer no preview before committing, and forget everything about how a part was built the moment you click OK — so revisiting a design months later, or handing the file to someone else, means starting from scratch. GridfinityGeneratorPlus keeps the original's proven geometry engine and rebuilds the interface and workflow around it.

**GridfinityGeneratorPlus** is a Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast and durable.

* **Feature 1: One persistent palette, not two dialogs.** Bin, Baseplate, Grid Optimizer, and Theme all live in a single dockable palette with shared "Common settings," live Update Preview / Generate / Clear Preview, and named saved configurations per tab.
* **Feature 2: Settings travel with the file.** Every generated part remembers the exact parameters that built it, stored directly on the component itself. Reopen a design months later, or share the `.f3d` with someone else running this add-in, and click **Edit Active Component** to pick up right where you left off.
* **Feature 3: Grid Optimizer.** Building a custom (non-42mm) grid to fit a specific drawer or cabinet? Enter your real measurements and let the optimizer recommend a pitch that minimizes wasted space, instead of guessing.
* **Feature 4: Stackable baseplates.** A fourth baseplate type, made symmetric top-to-bottom so it can be printed and physically stacked with no overhang, with configurable interface layers between plates.
* **Feature 5: Theme tab.** Customize the palette's appearance — built-in themes, automatic OS dark-mode following, and support for importing your own custom themes.
* **Feature 6: Half-unit grid support & DXF export for laser cutting.** Add a half-unit-wide strip to any edge (Left/Right/Front/Back) of a bin or baseplate — where two checked edges meet at a corner, that cell automatically becomes quarter-size, no extra configuration needed. Baseplates can also generate a DXF-ready sketch for laser-cut fabrication.

---
## ✨ What's New in v1.2.0

* **Half-unit edge support for bins and baseplates.** New Left/Right/Front/Back checkboxes on both tabs add a half-unit-wide strip to that edge; where two adjacent checked edges meet at a corner, that cell becomes quarter-size automatically. Core width/length can now be 0 when half-edges supply the rest of that axis — build a bin or baseplate entirely out of half- and quarter-size cells if you want to. Magnet/screw cutouts only ever apply to true full-size cells; a Skeletonized baseplate's decorative bottom groove is likewise full-cells-only, with half/quarter cells staying solid.
* **DXF-ready sketch for laser-cut baseplates.** New "Generate DXF-ready sketch" option on the Baseplate tab adds a sketch of the plate's mid-height cross-section that you can export to DXF/SVG by hand from Fusion, for laser-cutting baseplates out of thin sheet material.
* **Bin foot alignment fix.** Bin stacking feet now center correctly within each baseplate grid opening — previously they sat `xyClearance` off-center, most noticeable on precise/tight-clearance prints.

## ✨ What's New in v1.1.2

* **Fixed tripled bodies in stacked baseplates:** generating a Stackable baseplate with Stack Count > 1 silently produced 3x the expected baseplate/interface-layer bodies, all coincident in the Fusion viewport (so it looked correct there) but appearing as extra duplicate solids once exported/sliced. Root cause was a shared pattern-feature helper that only configured its first direction, leaving Fusion's own default second-direction quantity (3) active. If you've generated any Stackable baseplates with Stack Count > 1, regenerate them to pick up the fix.

## ✨ What's New in v1.1.1

* **Fixed a notch in the bin base's bottom edge:** multi-cell bins previously showed a small visible notch at every interior grid seam along the outer bottom edge. The base is now built at its final, clearance-adjusted size from the very first sketch instead of being reshaped by a separate step afterward, so the outer edge comes out clean — you'll now see a small (expected, spec-accurate) gap between adjacent unit cells' feet instead.
* **Dependent checkbox fixes:** unchecking **With lip** now also unchecks and disables **With lip notches** (re-enabling it when you check lip back on); unchecking **Add magnet cutouts** does the same for **Add magnet cutout tabs** — previously these could be left checked while their parent option was off.

*For the full development history and the reasoning behind each design decision, see [`docs/Dev_Notes.md`](docs/Dev_Notes.md).*

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

### Edit Active Component
Activate a previously generated Gridfinity part in the Fusion browser by hovering over the component name and clicking the radio button that appears to the righ of the name, then click **Edit Active Component** at the top of the palette — it reloads the exact settings used to build that part.

* **Tip:** this requires the design to be in **Hybrid** design mode (Document Settings → Design → Hybrid). If you click **Generate** in a Part or Assembly design, the palette will prompt you to switch modes — your entered values aren't lost, so just switch and click Generate again.

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
