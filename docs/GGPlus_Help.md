# GridfinityGenerator Plus

**A Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast, intuitive, and future-proof with creation settings that aren't lost to time.**

Version: 1.1.0.0

By Ed Johnson

July, 2026

---

## Introduction: The "Why" and "What"

The original GridfinityGenerator add-in is a great parametric bin/baseplate generator, but it works through two separate command dialogs that don't share settings, offer no preview before committing, and forget everything about how a part was built the moment you click OK — so revisiting a design months later, or handing the file to someone else, means starting from scratch. GridfinityGeneratorPlus keeps the original's proven geometry engine and rebuilds the interface and workflow around it.

**GridfinityGeneratorPlu**s is a Fusion add-in designed to make generating, previewing, and revisiting Gridfinity parts fast, intuitive, and future-proof with creation settings that aren't lost to time.

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
| Appearance | Fixed light theme | **Theme** tab — built-in themes, OS dark-mode following, and importable custom themes |
| Window state | Resets every session | Palette size/position/docking remembered across sessions |

---

## 

## 

## General Usage Instructions

**Install the add-in.** Unlike the original (distributed via the Fusion App Store), GridfinityGeneratorPlus is currently installed manually: in Fusion, go to **Utilities → Add-Ins → Scripts and Add-Ins**, and add this folder as an add-in. See [Installation / Uninstallation](#bookmark=id.q8d08gdrh1si) below for details.

**Open the palette.** In the **DESIGN** workspace, find the **SOLID** toolbar panel’s **CREATE** dropdown and select **“GridfinityGeneratorPlus.”** This opens (or brings forward) the palette, which stays docked and open across your session — you don’t need to reopen it for every bin or baseplate.

**Set your Common settings.** At the top of the palette, above the tabs, set your base grid unit (default 42mm), XY clearance, and magnet cutout size once — these are shared by both the Bin and Baseplate tabs so they always stay compatible with each other.

**Pick a tab and set your parameters.** Switch between **Bin**, **Baseplate**, **Grid Optimizer**, and **Theme** using the tab strip. Each field group is a collapsible section — expand or collapse what you need.

**Preview, then Generate.** Click **Update Preview** to see the result in the viewport before committing to anything (this can be re-run as many times as you like, replacing the previous preview). When you’re happy with it, click **Generate** to make it a permanent part of your design. **Clear Preview** removes a preview without generating.

**Revisit or fix a mistake later.** Hover over a previously generated Gridfinity component in the Fusion browser and click the radio button that appears to its right to activate it, then click **Edit Active Component** in the palette — this reloads the exact settings used to create it, so you can tweak and regenerate it in place. See [Edit Active Component](#bookmark=id.wncxlkcc67gc) below.

---

## The Palette Tabs

### Bin

Generates a parametric Gridfinity bin: overall size (in grid units), wall type (Hollow/Shelled/Solid), stacking lip, uniform or custom compartment grid, scoop, label tab, base screw holes, and magnet cutouts. This is a direct continuation of the original’s bin generator — the underlying geometry logic is Lev Mishin’s.

###  

### Baseplate

Generates a parametric Gridfinity baseplate. Four types are available:

* **Light** — thin, minimal-material baseplate, no magnet/screw cutouts.

* **Skeletonized** — lattice-cut bottom to save material, with connection holes.

* **Full** — solid extended bottom, with magnet and screw cutouts.

* **Stackable** *(new in this fork)* — see below.

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

Dimension lists can be saved as named, reloadable sets (e.g. “Kitchen Drawers,” “Workbench Cabinet”) just like Bin and Baseplate configurations.

### Theme (new)

Customize the palette's appearance. Choose **System** (follows your OS's light/dark setting automatically — the default), or one of the built-in themes: **Light**, **Dark**, **Midnight**, or **Sandstone**. You can also **import a custom .theme.json** file exported from any Theme Designer Pro–compatible tool — every theme you import is remembered and stays available in the dropdown across restarts, whether or not it's the one currently active. Sample themes are provided in the resources/themes/ folder.

Two additional controls apply on top of whichever theme is selected:

- **Font family** — Sans-serif, Serif, or Monospace.  
- **Base font size (px)** — scales the palette's body text; hint and error text scale proportionally with it.

Once you're happy with a look (including any font tweaks), click **Export theme.json…** to save it as a shareable file — this captures the full effective theme, whether it started as a built-in or an imported one. **Remove imported theme** deletes a theme you previously imported (disabled for the built-in themes, which can't be removed); re-importing a .theme.json with the same name as an existing one simply overwrites it, so there's no need to remove one before importing an updated version of it.

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

**Note:** this requires the design to be in **Hybrid** design mode (Document Settings → Design → Hybrid) — this is what allows each generated part to own and carry its own settings. **Generate** will prompt you to switch modes if the active document isn’t set to Hybrid; your entered field values are never lost when this happens, so you can simply switch modes and click Generate again.

---

## Screenshots

**Screenshot:** \[PLACEHOLDER\] overview collage or additional supplementary screenshots as needed. Additional screenshots

---

## Commands

| Command | Description |
| :---- | :---- |
| **GridfinityGeneratorPlus** | Opens the GridfinityGeneratorPlus palette (Solid Create panel). The palette stays open and docked; use its tabs to switch between Bin, Baseplate, Grid Optimizer, and Theme. |

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

This fork's development is logged in detail in [Dev\_Notes.md](http://Dev_Notes.md), session by session, including the reasoning behind each design decision. A condensed summary of major milestones:

- **Palette UI migration** — replaced the original's two separate command dialogs with a single persistent, dockable HTML palette.  
- **Common settings panel, config manager, persistent preview workflow** — shared Bin/Baseplate settings, named saved presets, and an explicit Update Preview / Generate / Clear Preview workflow across the palette (replacing the original's in-dialog auto-update/on-demand preview toggle).  
- **Edit Active Component** — re-edit a previously generated part by reloading the settings stored on it as a Fusion component attribute.  
- **Grid Optimizer tab** — recommends an optimal custom grid pitch from user-entered drawer/cabinet dimensions.  
- **Stackable baseplate type** — a fourth baseplate type, symmetric top-to-bottom for physical stacking, with configurable interface layers.  
- **Theme tab** — customizable palette appearance with built-in and importable custom themes, plus font family/size controls, theme export, and removing imported themes.  
- **Generate requires Hybrid design intent** — guarantees every generated part can carry its own settings for later editing or sharing.  
- **Grouped Undo & Undo/Redo-aware preview tracking** — Update Preview/Generate each collapse to a single Undo step, and the Clear Preview button stays correctly in sync as you step through Fusion's Undo/Redo.  
- **Redesigned Configurations manager & themed dialogs** — Load/Delete/Save As now open focused dialogs instead of sharing an inline dropdown, and every popup in the palette (including a warning before an Update Preview/Generate on one tab would discard an unfinalized preview on the other) uses a themed dialog matching the palette instead of a native browser popup.

---

*GridfinityGeneratorPlus — a fork of [GridfinityGenerator](https://github.com/Le0Michine/FusionGridfinityGenerator) by Lev Mishin. Licensed under CC BY-NC-SA 4.0.*
