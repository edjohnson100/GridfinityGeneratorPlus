# GridfinityGeneratorPlus
**Version:** 1.0.0.0

**Author:** Ed Johnson (Making With An EdJ)

**A persistent, dockable palette for generating parametric Gridfinity bins and baseplates in Fusion — with live preview, re-editable settings that travel with your design file, a custom grid-size optimizer, native stacking baseplates, and full UI theming.**

<img src="GFPlusAppIcon.png" alt="App Icon" width="300">

## Introduction: The "Why" and "What"

The original GridfinityGenerator add-in is a great parametric bin/baseplate generator, but it works through two separate command dialogs that don't share settings, offer no preview before committing, and forget everything about how a part was built the moment you click OK — so revisiting a design months later, or handing the file to someone else, means starting from scratch. GridfinityGeneratorPlus keeps the original's proven geometry engine and rebuilds the interface and workflow around it.

**GridfinityGeneratorPlus** is a Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast and durable.

* **Feature 1: One persistent palette, not two dialogs.** Bin, Baseplate, Grid Optimizer, and Theme all live in a single dockable palette with shared "Common settings," live Update Preview / Generate / Clear Preview, and named saved configurations per tab.
* **Feature 2: Settings travel with the file.** Every generated part remembers the exact parameters that built it, stored directly on the component itself. Reopen a design months later, or share the `.f3d` with someone else running this add-in, and click **Edit Active Component** to pick up right where you left off.
* **Feature 3: Grid Optimizer.** Building a custom (non-42mm) grid to fit a specific drawer or cabinet? Enter your real measurements and let the optimizer recommend a pitch that minimizes wasted space, instead of guessing.
* **Feature 4: Stackable baseplates.** A fourth baseplate type, made symmetric top-to-bottom so it can be printed and physically stacked with no overhang, with configurable interface layers between plates.
* **Feature 5: Theme tab.** Customize the palette's appearance — built-in themes, automatic OS dark-mode following, and support for importing your own custom themes.

---
## ✨ What's New in v1.0.0

* **Persistent palette UI:** replaced the original's two separate command dialogs with a single dockable palette, with a shared Common settings panel so Bin and Baseplate grids always stay compatible.
* **Edit Active Component:** activate a previously generated part in the browser, click one button, and the palette reloads the exact settings that built it — powered by settings stored on the component itself, not a separate file.
* **Grid Optimizer tab:** recommends an optimal custom grid pitch from your own drawer/cabinet measurements, with half-bin credit and width/depth priority as explicit options.
* **Stackable baseplate type:** a fourth baseplate type built to physically stack, with automatic interface-layer generation for multi-plate stacks.
* **Theme tab:** built-in themes, OS dark-mode following, and importable custom themes.
* **Generate now requires Hybrid design intent**, guaranteeing every generated part can carry its own settings forward.

*For the full development history and the reasoning behind each design decision, see [`docs/Dev_Notes.md`](docs/Dev_Notes.md).*

## Installation

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

## Tech Stack

For the fellow coders and makers out there, here is how GridfinityGeneratorPlus was built:

* **Language:** Python (Fusion API)
* **Interface:** HTML/CSS/JavaScript (Palette)
* **Data Storage:** Each generated part's settings are stored as a Fusion document attribute directly tied to the component, so they travel with the `.f3d` file itself. Add-in preferences (window geometry, active theme), saved configurations, and imported themes are stored locally as JSON alongside the add-in.

## Acknowledgements & Credits

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
