# Fusion Palette UI — Implementation Reference

A generic, reusable reference for wiring an HTML/CSS/JS palette into **any** Fusion add-in. This is distilled from building and debugging the palette in the LiveUtilities add-in, and is meant to be handed to an AI coding assistant (or your future self) as a briefing doc before implementing a palette in a new or existing project — not a spec of LiveUtilities itself.

It covers: the moving parts required, boilerplate code for each piece, the message-passing contract between Python and HTML, and a list of pitfalls that are easy to hit and non-obvious to debug.

---

## 1. What a "palette" is in Fusion

`adsk.core.Palettes` lets an add-in show a **docked or floating panel that renders an arbitrary local HTML file** inside an embedded Chromium browser, living alongside the native Fusion UI. It is Fusion's equivalent of a task pane. There is no framework requirement — it's just HTML/CSS/JS loaded via a `file://` URL, communicating with your Python add-in code through a proprietary JS↔Python bridge (`window.adsk` / `HTMLEventArgs`), not `postMessage` and not any web-standard IPC.

Minimum pieces you need:
1. A Python **command** that creates/shows the palette.
2. A local **HTML/CSS/JS bundle** the palette loads.
3. A Python-side **`HTMLEventHandler`** to receive messages from the HTML.
4. A JS-side **handler function** to receive pushes from Python.
5. A Python-side **`PaletteCloseHandler`** for cleanup.
6. Entries in the add-in's **manifest** (JSON, not XML) — minimal; most wiring is imperative in Python, not declarative.

---

## 2. Minimal Python boilerplate

```python
import adsk.core, adsk.fusion, traceback
import os, json

app = adsk.core.Application.get()
ui = app.userInterface

PALETTE_ID = 'myAddinPaletteId'          # must be unique within the add-in
PALETTE_TITLE = 'My Palette'
PALETTE_URL = 'myPalette/index.html'      # relative to your add-in's resources folder

_handlers = []  # keep references alive — Fusion drops handlers that get GC'd

def open_palette():
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.isVisible = True
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, 'resources', PALETTE_URL)
    url = 'file:///' + html_path.replace('\\', '/')

    palette = ui.palettes.add(
        PALETTE_ID, PALETTE_TITLE, url,
        True,   # isVisible
        True,   # showCloseButton
        True,   # isResizable
        360, 500
    )
    palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight

    on_html_event = HTMLEventHandler()
    palette.incomingFromHTML.add(on_html_event)
    _handlers.append(on_html_event)

    on_closed = PaletteCloseHandler()
    palette.closed.add(on_closed)
    _handlers.append(on_closed)


class HTMLEventHandler(adsk.core.HTMLEventHandler):
    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            data = json.loads(html_args.data)
            action = data.get('action')
            palette = ui.palettes.itemById(PALETTE_ID)

            if action == 'refresh_data':
                payload = build_state_payload()   # your own function
                palette.sendInfoToHTML('update_ui', json.dumps(payload))

            elif action == 'do_something':
                result = do_something(data)        # your own function
                palette.sendInfoToHTML('notification', json.dumps({
                    'type': 'success', 'message': 'Done'
                }))

        except:
            app.log('HTMLEventHandler failed:\n{}'.format(traceback.format_exc()))


class PaletteCloseHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def notify(self, args):
        pass  # cleanup if needed; palette object itself is already gone
```

Key decision up front: **show/hide vs. destroy/recreate.**
- `palette.isVisible = True/False` — cheap, preserves in-page JS state (form inputs, scroll position) between opens. Preferred default.
- `palette.deleteMe()` then `ui.palettes.add(...)` again — forces a full reload of the HTML/JS. Only do this if you need to guarantee a clean state (e.g. after a version bump to the palette's HTML/JS files, since Fusion's embedded browser can cache aggressively — see pitfall §6.1).

---

## 3. Minimal HTML/JS boilerplate

`resources/myPalette/index.html`:
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="app">Loading…</div>
  <script src="script.js"></script>
</body>
</html>
```

`resources/myPalette/script.js`:
```js
// ---- Outgoing: JS -> Python ----
function sendToFusion(action, data = {}) {
    data.action = action;
    const json = JSON.stringify(data);
    try {
        if (window.adsk && window.adsk.fusionSendData) {
            window.adsk.fusionSendData('send', json);
        }
    } catch (e) {
        console.error('sendToFusion failed', e);
    }
}

// ---- Incoming: Python -> JS ----
// Fusion calls this global directly; the function name/shape is fixed by Fusion's API.
window.fusionJavaScriptHandler = {
    handle: function (action, data) {
        try {
            const parsed = typeof data === 'string' ? JSON.parse(data) : data;
            if (action === 'update_ui') {
                renderUI(parsed);
            } else if (action === 'notification') {
                showStatus(parsed.message, parsed.type);
            }
            return 'OK';
        } catch (e) {
            console.error('fusionJavaScriptHandler failed', e);
            return 'FAIL';
        }
    }
};

function renderUI(state) {
    document.getElementById('app').textContent = JSON.stringify(state);
}

function showStatus(message, type) {
    console.log(`[${type}] ${message}`);
}

// ---- Bridge readiness ----
// window.adsk is injected by Fusion asynchronously — it may not exist yet
// at DOMContentLoaded. Poll until it does before requesting initial data.
function waitForFusionBridge(retries = 40) {
    if (window.adsk && window.adsk.fusionSendData) {
        sendToFusion('refresh_data');
    } else if (retries > 0) {
        setTimeout(() => waitForFusionBridge(retries - 1), 250);
    } else {
        console.error('Fusion bridge never became available');
    }
}

waitForFusionBridge();
```

---

## 4. The message-passing contract (define this explicitly, early)

Both directions should use a single consistent envelope. Recommended shape:

**JS → Python:**
```json
{ "action": "action_name", "...payload fields": "..." }
```
Always one JSON object, always includes `action`. Python's `HTMLEventHandler.notify` dispatches on `data['action']`.

**Python → JS:**
```
palette.sendInfoToHTML(eventName, jsonString)
```
`eventName` is the first arg to `fusionJavaScriptHandler.handle(action, data)` on the JS side; `jsonString` is always a JSON *string* (JS does one `JSON.parse` on receipt — don't double-encode, don't send raw objects sometimes and strings other times, pick one and stay consistent throughout the codebase).

Decide and document, before writing feature code:
- A closed list of `action` names for each direction (e.g. `refresh_data`, `update_ui`, `notification`, `close`).
- Whether write-actions from JS need a "is it safe to mutate the document right now" guard (see §6.7).
- Whether Python ever needs to *push* updates unprompted (e.g. on selection change, document activation, command termination) vs. only responding to JS requests. If yes, register the relevant Fusion application-level event handlers (`app.documentActivated`, `ui.commandTerminated`, `ui.activeSelectionChanged`, etc.) at add-in startup, not inside the palette-open function, so pushes still work correctly across show/hide cycles.

---

## 5. Manifest / add-in registration

Fusion add-ins use a JSON manifest (`YourAddin.manifest`), and it does **not** need palette-specific entries — palette creation is 100% imperative Python (see §2). The manifest only needs the standard add-in metadata:
```json
{
    "autodeskProduct": "Fusion",
    "type": "addin",
    "id": "<a-guid>",
    "author": "Your Name",
    "description": { "": "..." },
    "version": "1.0.0",
    "runOnStartup": false,
    "supportedOS": "windows|mac",
    "editEnabled": true,
    "iconFilename": "AddinIcon.png"
}
```
Don't go looking for a `<Taskpane>`-style declarative section like Office add-ins have — it doesn't exist here. Everything about the palette's size, docking, URL, and lifecycle is controlled by the `ui.palettes.add(...)` call and subsequent property sets in Python.

---

## 6. Pitfalls (the part worth reading closely)

### 6.1 The embedded browser caches HTML/CSS/JS aggressively
Editing `script.js` or `style.css` and reopening the palette can silently serve the **old cached version**, especially across multiple Fusion sessions. Symptoms: your fix "doesn't work" even though the file on disk is correct.
- Cache-bust script/style tags with a version query param you bump on every change: `<script src="script.js?v=7">`.
- When debugging a "my change isn't showing up" issue, force a full palette recreate (`deleteMe()` + `add()`) rather than just `isVisible = true`, to rule out caching before you go chase a phantom bug.

### 6.2 `window.adsk` is not guaranteed to exist at page load
The bridge object is injected asynchronously by Fusion and is not always present by `DOMContentLoaded` or even shortly after. If your JS calls `sendToFusion(...)` too early, the message is silently dropped (no error, no exception) because the guarded `if (window.adsk && ...)` check just no-ops.
- Always gate your first outgoing call behind a poll/retry loop (see `waitForFusionBridge` in §3), not a single `if` check on load.
- This is the single most common cause of "the palette opens but shows nothing / never loads data."

### 6.3 Handler objects must be kept alive from Python
`HTMLEventHandler` and other Fusion event handler instances get garbage-collected if you don't hold a reference to them somewhere that outlives the function that created them (e.g. a module-level list). If this happens, your handler silently stops firing with no error — messages from JS just go nowhere.
- Keep a module-level list (`_handlers = []`) and append every handler you create to it. Never let a handler be a purely local variable in a function that returns.

### 6.4 Rapid successive sends from JS can race
If JS fires multiple `sendToFusion` calls back-to-back (e.g. in a loop, or from multiple UI event listeners firing near-simultaneously), Python-side handling isn't guaranteed to process them in a way your JS expects, and Fusion's UI thread can get contended if a handler does anything slow (creating features, computing timelines, etc.) synchronously.
- Keep `HTMLEventHandler.notify` handlers fast. Do expensive work (scanning large parameter/feature lists) only when actually requested, and consider debouncing rapid-fire JS-side triggers (e.g. from text input `oninput`) before calling `sendToFusion`.

### 6.5 Mutating the document while a modal command is active can corrupt state or throw
If the user has an active command running (mid-sketch, mid-feature-edit, an in-progress dialog) and a palette action tries to mutate the document (rename a parameter, delete a feature, etc.) at that moment, you risk exceptions or an inconsistent document state.
- Before executing any write action from `HTMLEventHandler.notify`, check `ui.activeCommand` and bail out with a user-facing error/notification if it indicates a blocking modal state (i.e. anything other than a benign default like `'SelectCommand'`). Send this back to JS as a `notification` (type `error`) rather than letting an exception propagate silently.

### 6.6 Exceptions inside `HTMLEventHandler.notify` fail silently
If your `notify()` method throws, Fusion does **not** surface a JS-visible error or crash — it just fails quietly, and the palette will appear "stuck" (spinner never resolves, button click does nothing).
- Wrap the entire body of `notify()` in `try/except` and log via `app.log(traceback.format_exc())` (visible in Fusion's Text Commands / log). Skipping this makes every bug in write-action logic essentially invisible during development.

### 6.7 The palette's HTML lives at a `file://` origin — some browser APIs behave differently there
`localStorage`/`sessionStorage` work but are scoped to the `file://` origin of that specific HTML file's path — if your add-in's install path ever changes (e.g. reinstalled to a different folder, or loaded from a network path), previously stored `localStorage` data won't be visible anymore. `fetch()` of local relative files works but can behave inconsistently across OS/Chromium-embedding versions — prefer bundling all needed data directly into the initial HTML/JS rather than relying on runtime `fetch()` of sibling files if you can avoid it.
- Don't treat `localStorage` in the palette as durable, cross-install persistent storage. For anything that must survive add-in reinstallation/relocation, write it to a JSON file on disk from the Python side instead (e.g. next to the add-in, or in a user config directory), and have Python push it into the palette on load rather than relying on the browser's own storage.

### 6.8 `innerHTML`-based rendering + inline `onclick=""` breaks on special characters
If you build rows/lists by concatenating HTML strings and embedding user-provided values (names, paths) directly into `onclick="doThing('${name}')"`, any apostrophe/quote/backslash in that value breaks the generated HTML or, worse, allows an injection bug.
- Prefer `addEventListener` + `element.dataset.xxx` over inline `onclick` + string concatenation. If you must support inline handlers for a quick prototype, `encodeURIComponent`/`decodeURIComponent` the value round-trip rather than interpolating raw strings into an attribute.

### 6.9 Double-JSON-encoding creates confusing bugs
It's easy to end up with code paths where a payload gets `json.dumps`'d, then something re-parses it just to inspect a field, then forwards the *original string* onward — versus other code paths that forward a freshly re-serialized object. If these two conventions coexist, JS-side `JSON.parse` calls will intermittently throw ("Unexpected token" on a double-encoded string) in ways that are hard to reproduce.
- Pick one rule for the whole codebase: Python always calls `json.dumps()` exactly once, immediately before calling `sendInfoToHTML`, on a plain dict — never on an already-stringified value. Enforce this by never storing "the JSON string" as an intermediate variable that outlives the function that created it; keep dicts as dicts until the final send call.

### 6.10 CSS theming via custom properties is far more portable/maintainable than regex-parsing CSS
If you want user-selectable visual themes in the palette, define each theme as a **JSON object of CSS-variable-name → value**, not as separate `.css` files you regex-parse at runtime. Regex-based CSS parsing (matching `:root { ... }` / `[data-theme="..."] { ... }` blocks) is fragile — it breaks if comment placement, block ordering, or file structure shifts even slightly, and there's no compile-time or lint-time way to catch a broken regex until it silently fails to find a theme.
- Store themes as JSON (bundled statically, or in a Python-side settings file pushed to JS on load). Apply a theme by setting CSS variables directly via JS (`document.documentElement.style.setProperty('--var-name', value)` or by toggling a `data-theme` attribute matched against `[data-theme="..."]` CSS blocks you wrote by hand, not generated/parsed at runtime).

### 6.11 Don't assume `deleteMe()` + `add()` implicitly resets everything you expect
Recreating the palette object does destroy the DOM/JS runtime, but anything the JS stored in that origin's `localStorage` (see 6.7) survives across recreation — so "close and reopen the palette" is not a reliable way to fully reset UI state if you're relying on `localStorage` for persistence. Be deliberate about what "reset" means for your palette (a dedicated Python-triggered `localStorage.clear()` message, vs. destroy/recreate, vs. just `isVisible` toggling) and don't conflate the three.

---

## 7. Suggested build order for a new palette feature

1. Get an empty palette opening reliably (§2–3) with a visible "Hello World" and confirm `waitForFusionBridge` → `refresh_data` → `update_ui` round-trip works, before writing any real feature logic. This isolates bridge/plumbing bugs from feature bugs.
2. Define your `action` name list (§4) on paper first — resist the urge to invent a new ad hoc action name per feature as you go; a small closed vocabulary keeps the Python-side dispatcher simple and reviewable.
3. Add `try/except` + logging around `HTMLEventHandler.notify` from the start (§6.6) — you will need it almost immediately.
4. Add the modal-safety guard (§6.5) before wiring up any write/mutate action, not after you hit a corruption bug.
5. Decide your persistence strategy (disk JSON vs. `localStorage`, §6.7/6.11) explicitly per piece of state, rather than defaulting to `localStorage` for everything because it's the path of least resistance in the JS.
6. Only after the above is solid, layer on visual polish (themes, animations, layout) — CSS-variable theming (§6.10) if you want user-switchable themes.
