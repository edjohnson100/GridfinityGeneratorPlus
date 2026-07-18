# GridfinityGeneratorPlus

Version: 1.1.0.0

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

---
## ✨ What's New in v1.1.0

* **Grouped Undo:** Update Preview and Generate each collapse to a single Undo step, instead of leaving several separate entries on Fusion's Undo stack.
* **Undo/Redo-aware preview tracking:** the Clear Preview button now stays in sync as you step through Fusion's Undo/Redo — including recognizing an earlier preview reappearing several steps back, not just the most recent one.
* **Cross-tab preview warning:** switching to the other tab and clicking Update Preview or Generate now warns you first if it would discard an unfinalized preview you built on the tab you're leaving.
* **Redesigned Configurations manager:** Load, Delete, and Save As now each open a focused dialog instead of sharing an inline dropdown, with a clear "Active config" status line — Update Current is now the only button that acts on the current selection directly.
* **Custom themed dialogs:** every native browser confirm/prompt popup in the palette has been replaced with a themed HTML modal that matches whichever theme you have selected.
* **Theme tab: font controls, export, and cleanup.** Choose a font family and base font size on top of any theme, export the current look (including your font tweaks, which now correctly round-trip on re-import) as a shareable `.theme.json` via a native Save dialog defaulted to `resources/themes/`, and remove imported themes you no longer want.
* **Linked Factory Reset:** resetting Bin or Baseplate now also resets the shared Common settings (base unit, clearance, magnet size), and vice versa — previously each Factory Reset button only reset its own section, so a loaded custom-grid preset could leave Common looking un-reset.
* **Sortable Grid Optimizer dimensions table:** click a column heading (Description/Width/Depth) to sort your dimension list, click again to reverse — the order you leave it in is what gets saved.
* **Visual polish:** a more distinct tab bar in dark themes, and hint/error text that now scales with the base font size setting.

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

## Tech Stack

For the fellow coders and makers out there, here is how GridfinityGeneratorPlus was built:

* **Language:** Python (Fusion API)
* **Interface:** HTML/CSS/JavaScript (Palette)
* **Data Storage:** Each generated part's settings are stored as a Fusion component attribute directly tied to the component, so they travel with the `.f3d` file itself. Add-in preferences (window geometry, active theme), saved configurations, and imported themes are stored locally as JSON alongside the add-in.

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
