// ---- Unit conversion: Python speaks cm (Fusion's internal unit), this UI displays mm. ----
const CM_TO_MM = 10;

const MM_FIELDS = {
    common: ['baseWidthUnit', 'baseLengthUnit', 'xyClearance', 'magnetDiameter', 'magnetDepth'],
    bin: ['heightUnit', 'wallThickness', 'scoopMaxRadius', 'tabWidth', 'screwDiameter'],
    baseplate: ['screwDiameter', 'screwHeadDiameter', 'paddingLeft', 'paddingTop', 'paddingRight', 'paddingBottom', 'extraBottomThickness', 'binZClearance', 'connectionHoleDiameter', 'interfaceLayerThickness'],
    optimizer: ['minSize', 'maxSize', 'bedWidth', 'bedDepth', 'binBedWidth', 'binBedDepth'],
};
const COMPARTMENT_MM_FIELDS = ['depth'];
const OPTIMIZER_ITEM_MM_FIELDS = ['width', 'depth'];

function cmToMm(v) {
    return Math.round(v * CM_TO_MM * 1000) / 1000;
}
function mmToCm(v) {
    return v / CM_TO_MM;
}

function cmFormToDisplayForm(tab, form) {
    const out = Object.assign({}, form);
    for (const field of MM_FIELDS[tab] || []) {
        if (typeof out[field] === 'number') {
            out[field] = cmToMm(out[field]);
        }
    }
    if (tab === 'bin' && Array.isArray(out.compartments)) {
        out.compartments = out.compartments.map(row => {
            const r = Object.assign({}, row);
            for (const field of COMPARTMENT_MM_FIELDS) {
                if (typeof r[field] === 'number') r[field] = cmToMm(r[field]);
            }
            return r;
        });
    }
    if (tab === 'optimizer' && Array.isArray(out.items)) {
        out.items = out.items.map(row => {
            const r = Object.assign({}, row);
            for (const field of OPTIMIZER_ITEM_MM_FIELDS) {
                if (typeof r[field] === 'number') r[field] = cmToMm(r[field]);
            }
            return r;
        });
    }
    return out;
}

function displayFormToCmForm(tab, form) {
    const out = Object.assign({}, form);
    for (const field of MM_FIELDS[tab] || []) {
        if (typeof out[field] === 'number') {
            out[field] = mmToCm(out[field]);
        }
    }
    if (tab === 'bin' && Array.isArray(out.compartments)) {
        out.compartments = out.compartments.map(row => {
            const r = Object.assign({}, row);
            for (const field of COMPARTMENT_MM_FIELDS) {
                if (typeof r[field] === 'number') r[field] = mmToCm(r[field]);
            }
            return r;
        });
    }
    if (tab === 'optimizer' && Array.isArray(out.items)) {
        out.items = out.items.map(row => {
            const r = Object.assign({}, row);
            for (const field of OPTIMIZER_ITEM_MM_FIELDS) {
                if (typeof r[field] === 'number') r[field] = mmToCm(r[field]);
            }
            return r;
        });
    }
    return out;
}

// ---- Application state ----
const state = {
    activeTab: 'bin',
    forms: {
        common: {
            baseWidthUnit: 4.2, baseLengthUnit: 4.2, xyClearance: 0.025,
            magnetDiameter: 0.65, magnetDepth: 0.24,
        },
        bin: {
            heightUnit: 0.7,
            binWidth: 2, binLength: 3, binHeight: 5,
            generateBody: true, binType: 'Hollow', wallThickness: 0.12, withLip: true, withLipNotches: false,
            compartmentsGridType: 'Uniform', compartmentsGridWidth: 1, compartmentsGridLength: 1, compartments: [],
            hasScoop: false, scoopMaxRadius: 2.5,
            scoopFront: true, scoopLeft: false, scoopBack: false, scoopRight: false,
            hasTab: false, tabLength: 1, tabWidth: 1.3, tabPosition: 0, tabAngleDeg: 45,
            generateBase: true, hasScrewHoles: false, screwDiameter: 0.3,
            hasMagnetCutouts: false, hasMagnetCutoutsTabs: false,
        },
        baseplate: {
            plateWidth: 2, plateLength: 3, plateType: 'Light',
            hasMagnetCutouts: true,
            hasScrewHoles: true, screwDiameter: 0.32, screwHeadDiameter: 0.6,
            hasSidePadding: false, paddingLeft: 0, paddingTop: 0, paddingRight: 0, paddingBottom: 0,
            extraBottomThickness: 0.64, binZClearance: 0.05,
            hasConnectionHoles: false, connectionHoleDiameter: 0.32,
            stackCount: 1, interfaceLayerThickness: 0.04,
        },
        optimizer: {
            minSize: 3.0, maxSize: 7.5, allowHalfBins: true, compareStandard: false, priority: 'balanced', layoutGrid: 'optimized', bedWidth: 25.6, bedDepth: 25.6, binBedWidth: null, binBedDepth: null, binStrategy: 'perTile', maxBinCellsWidth: 3, maxBinCellsDepth: 3, binPalette: '2x2, 1x1', tileBinSettings: {}, items: [],
        },
        theme: { name: 'System', fontFamily: '-apple-system, "Segoe UI", Helvetica, Arial, sans-serif', fontSize: 12 },
    },
    fieldErrors: { bin: {}, baseplate: {}, optimizer: {} },
    valid: { bin: true, baseplate: true, optimizer: true },
    configs: { bin: [], baseplate: [], optimizer: [] },
    activeConfig: { bin: null, baseplate: null, optimizer: null },
    // Which tab (if any) currently owns the single shared preview slot -- used to
    // warn before Update Preview/Generate on the *other* tab silently discards it.
    previewTab: null,
    previewAdopted: false,
};

const validateDebounceTimers = {};

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
window.fusionJavaScriptHandler = {
    handle: function (action, data) {
        try {
            const parsed = typeof data === 'string' ? JSON.parse(data) : data;
            if (action === 'set_state') {
                onSetState(parsed);
            } else if (action === 'validation_result') {
                onValidationResult(parsed);
            } else if (action === 'notification') {
                showNotification(parsed.type, parsed.message);
            } else if (action === 'preview_status') {
                onPreviewStatus(parsed);
            } else if (action === 'section_state') {
                applySectionState(parsed.sections || {});
            } else if (action === 'config_list') {
                onConfigList(parsed);
            } else if (action === 'layout_result') {
                renderDrawerLayout(parsed);
            } else if (action === 'optimizer_result') {
                renderOptimizerResults(parsed);
            } else if (action === 'theme_export_result') {
                document.getElementById('theme-import-hint').textContent = `Exported to "${parsed.path}"`;
            }
            return 'OK';
        } catch (e) {
            console.error('fusionJavaScriptHandler failed', e);
            return 'FAIL';
        }
    }
};

function onSetState(payload) {
    const tab = payload.tab;
    const cmForm = payload.form;
    if (tab === 'theme') {
        if (payload.source === 'factory_reset') {
            // The host wiped imported_themes.json entirely -- drop every imported
            // <option> and cached vars rather than just merging in payload.importedThemes
            // (which is now `{}` and would otherwise leave stale entries behind).
            Object.keys(importedThemes).forEach(id => delete importedThemes[id]);
            const select = document.getElementById('theme.name');
            Array.from(select.options).forEach(opt => {
                if (!BUILTIN_THEME_NAMES.includes(opt.value)) select.removeChild(opt);
            });
            const dynamicTag = document.getElementById('dynamic-theme-overrides');
            if (dynamicTag) dynamicTag.remove();
        }
        state.forms.theme = cmForm;
        // Strip any font vars persisted by an older version of the import flow --
        // otherwise a previously-imported theme's baked-in font would still
        // out-specificity applyFontOverrides below (see THEME_VAR_NAMES comment).
        Object.entries(payload.importedThemes || {}).forEach(([id, vars]) => {
            const cleanVars = { ...vars };
            delete cleanVars['--font-family'];
            delete cleanVars['--font-size-base'];
            importedThemes[id] = cleanVars;
            ensureThemeOption(id, `${id} (imported)`);
        });
        renderForm('theme');
        applyTheme(cmForm.name, importedThemes[cmForm.name] || null);
        applyFontOverrides(cmForm.fontFamily, cmForm.fontSize);
        updateThemeRemoveButtonState();
        if (payload.source === 'factory_reset') {
            showNotification('success', 'Themes reset to defaults');
        }
        return;
    }
    state.forms[tab] = cmForm;
    renderForm(tab);
    if (payload.source === 'factory_reset' || payload.source === 'reset') {
        const label = tab === 'bin' ? 'Bin' : tab === 'baseplate' ? 'Baseplate' : 'Common';
        showNotification('success', `${label} settings reset`);
    }
    if (payload.source === 'edit_component') {
        setActiveTab(tab);
        setEditBanner(tab, payload.componentName);
        showNotification('success', `Editing "${payload.componentName}"`);
    } else if (tab !== 'common') {
        setEditBanner(tab, null);
    }
    if (tab === 'common') {
        requestValidation('bin');
        requestValidation('baseplate');
    } else {
        requestValidation(tab);
    }
}

function setEditBanner(tab, componentName) {
    const banner = document.getElementById(`${tab}-edit-banner`);
    if (!banner) return;
    if (!componentName) {
        banner.classList.add('hidden');
        banner.textContent = '';
        return;
    }
    banner.textContent = `Editing "${componentName}" — Update Preview to apply changes, Generate to make it permanent again, or Clear Preview to delete it. Closing without doing any of these leaves it unchanged.`;
    banner.classList.remove('hidden');
}

function onValidationResult(payload) {
    const tab = payload.tab;
    state.valid[tab] = payload.valid;
    state.fieldErrors[tab] = payload.fieldErrors || {};
    renderFieldErrors(tab);
    openSectionsWithErrors();
    if (tab === 'bin' || tab === 'baseplate') {
        renderComputed(tab, payload.computed || {});
    }
    updateActionButtons(tab);
}

function onPreviewStatus(payload) {
    document.querySelectorAll('.clear-preview-button').forEach(btn => {
        btn.disabled = !payload.active;
    });
    state.previewTab = payload.active ? payload.tab : null;
    state.previewAdopted = payload.active && !!payload.adopted;
    if (!payload.active) {
        setEditBanner('bin', null);
        setEditBanner('baseplate', null);
    } else if (!payload.adopted) {
        setEditBanner(payload.tab, null);
    }
}

function onConfigList(payload) {
    const tab = payload.tab;
    state.configs[tab] = payload.configs || [];
    state.activeConfig[tab] = payload.activeConfig || null;
    renderConfigStatus(tab);
}

// No inline dropdown anymore -- Load/Delete open a picker modal sourced from
// state.configs[tab] directly, so this just renders the status line and the
// Update Current button's enabled state.
function renderConfigStatus(tab) {
    const active = state.activeConfig[tab];
    const activeLabel = document.getElementById(`${tab}-config-active`);
    updateSectionSummaries();
    activeLabel.innerHTML = active
        ? `Active config: <strong>${escapeHtml(active)}</strong>`
        : 'Active config: <em>(none, using defaults)</em>';

    document.getElementById(`${tab}-config-update`).disabled = !active;
}

// The top notification bar sits above the tabs, out of view once the palette is
// scrolled down to the action buttons -- also render into a second bar local to the
// active tab (just above its Configurations/Saved sets section, near where Generate/
// Update Preview/config buttons actually get clicked) so the message is visible
// without scrolling back up.
function setNotificationEl(el, type, message) {
    if (!el) return;
    el.textContent = message;
    el.className = `notification ${type}`;
    el.classList.remove('hidden');
    clearTimeout(el._notificationTimer);
    el._notificationTimer = setTimeout(() => {
        el.classList.add('hidden');
    }, 5000);
}

function showNotification(type, message) {
    setNotificationEl(document.getElementById('notification'), type, message);
    setNotificationEl(document.getElementById(`${state.activeTab}-notification`), type, message);
}

// ---- Modal component (shared overlay for confirm/prompt/picker dialogs) ----
// Replaces window.confirm/window.prompt with a themed HTML modal. Only one modal
// can be open at a time -- every call site awaits it to completion before the next
// user action could open another, so this isn't a real constraint in practice.
let _modalOpen = false;
let _modalResolve = null;
let _modalPreviouslyFocused = null;

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function _modalTrapTab(e) {
    const modal = document.querySelector('#modal-overlay .modal');
    const focusable = modal.querySelectorAll('button, input, select, [tabindex]:not([tabindex="-1"])');
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
    }
}

function _modalKeydown(e) {
    if (e.key === 'Escape') {
        e.preventDefault();
        _closeModal(null);
    } else if (e.key === 'Enter') {
        // Ignore Enter while focus is on Cancel, so tabbing there and pressing
        // Enter doesn't accidentally confirm instead.
        if (document.activeElement === document.getElementById('modal-btn-cancel')) return;
        e.preventDefault();
        document.getElementById('modal-btn-confirm').click();
    } else if (e.key === 'Tab') {
        _modalTrapTab(e);
    }
}

function _closeModal(value) {
    if (!_modalOpen) return;
    _modalOpen = false;
    document.getElementById('modal-overlay').classList.add('hidden');
    document.getElementById('modal-body').innerHTML = '';
    document.getElementById('modal-btn-confirm').classList.remove('danger');
    document.removeEventListener('keydown', _modalKeydown);
    if (_modalPreviouslyFocused && _modalPreviouslyFocused.focus) {
        _modalPreviouslyFocused.focus();
    }
    const resolve = _modalResolve;
    _modalResolve = null;
    if (resolve) resolve(value);
}

function _openModal({ title, bodyHtml, confirmLabel, danger, getValue, onOpen, noCancel }) {
    if (_modalOpen) {
        console.error('_openModal called while a modal is already open');
        return Promise.resolve(null);
    }
    _modalOpen = true;
    _modalPreviouslyFocused = document.activeElement;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    const confirmBtn = document.getElementById('modal-btn-confirm');
    confirmBtn.textContent = confirmLabel || 'OK';
    confirmBtn.classList.toggle('danger', !!danger);
    // Notice-style modals have only an OK button and ignore backdrop clicks, so the
    // message can't be dismissed by accident.
    document.getElementById('modal-btn-cancel').style.display = noCancel ? 'none' : '';
    document.getElementById('modal-overlay').classList.remove('hidden');

    return new Promise(resolve => {
        _modalResolve = resolve;
        confirmBtn.onclick = () => _closeModal(getValue ? getValue() : true);
        document.getElementById('modal-btn-cancel').onclick = () => _closeModal(null);
        document.getElementById('modal-overlay').onclick = e => {
            if (!noCancel && e.target.id === 'modal-overlay') _closeModal(null);
        };
        document.addEventListener('keydown', _modalKeydown);
        if (onOpen) onOpen();
    });
}

// Notice with a single OK button; `messages` is a string or an array of paragraphs.
function showAlertModal(messages, opts = {}) {
    const list = Array.isArray(messages) ? messages : [messages];
    return _openModal({
        title: opts.title || 'Notice',
        bodyHtml: list.map(m => `<p>${escapeHtml(m)}</p>`).join(''),
        confirmLabel: 'OK',
        noCancel: true,
        getValue: () => true,
        onOpen: () => document.getElementById('modal-btn-confirm').focus(),
    }).then(() => undefined);
}

function showConfirmModal(message, opts = {}) {
    return _openModal({
        title: opts.title || 'Confirm',
        bodyHtml: `<p>${escapeHtml(message)}</p>`,
        confirmLabel: opts.confirmLabel || 'OK',
        danger: !!opts.danger,
        getValue: () => true,
        onOpen: () => document.getElementById('modal-btn-confirm').focus(),
    }).then(v => !!v);
}

function showPromptModal(message, defaultValue, opts = {}) {
    return _openModal({
        title: opts.title || 'Enter a name',
        bodyHtml: `<p>${escapeHtml(message)}</p><input type="text" id="modal-prompt-input" value="${escapeHtml(defaultValue || '')}">`,
        confirmLabel: opts.confirmLabel || 'OK',
        getValue: () => document.getElementById('modal-prompt-input').value.trim(),
        onOpen: () => {
            const input = document.getElementById('modal-prompt-input');
            input.focus();
            input.select();
        },
    }).then(v => (!v ? null : v));
}

function showPickerModal(message, optionsList, opts = {}) {
    const optionsHtml = optionsList.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
    return _openModal({
        title: opts.title || 'Select a config',
        bodyHtml: `<p>${escapeHtml(message)}</p><select id="modal-picker-select" size="${Math.min(optionsList.length, 8)}">${optionsHtml}</select>`,
        confirmLabel: opts.confirmLabel || 'OK',
        danger: !!opts.danger,
        getValue: () => document.getElementById('modal-picker-select').value,
        onOpen: () => document.getElementById('modal-picker-select').focus(),
    });
}

// ---- Form <-> DOM ----
function readFormFromDom(tab) {
    const form = {};
    document.querySelectorAll(`[id^="${tab}."]`).forEach(el => {
        const field = el.id.slice(tab.length + 1);
        if (el.type === 'checkbox') {
            form[field] = el.checked;
        } else if (el.tagName === 'SELECT' || el.type === 'text') {
            form[field] = el.value;
        } else {
            form[field] = parseFloat(el.value);
        }
    });
    if (tab === 'bin') {
        form.compartments = readCompartmentsFromDom();
    }
    if (tab === 'optimizer') {
        form.items = readOptimizerItemsFromDom();
        form.tileBinSettings = JSON.parse(JSON.stringify(tileBinSettings));
        form.customBins = JSON.parse(JSON.stringify(customBins));
    }
    return form;
}

function writeFormToDom(tab, displayForm) {
    document.querySelectorAll(`[id^="${tab}."]`).forEach(el => {
        if (el === document.activeElement) return;
        const field = el.id.slice(tab.length + 1);
        if (!(field in displayForm)) return;
        const value = displayForm[field];
        if (el.type === 'checkbox') {
            el.checked = !!value;
        } else {
            el.value = value;
        }
    });
    if (tab === 'bin') {
        renderCompartmentsTable(displayForm.compartments || []);
        updateBinConditionalVisibility();
    }
    if (tab === 'baseplate') {
        updateBaseplateConditionalVisibility();
    }
    if (tab === 'optimizer') {
        // A freshly loaded list's saved order isn't necessarily sorted by whatever
        // column was last clicked in this session -- don't claim otherwise.
        optimizerSort = { field: null, dir: 1 };
        renderOptimizerItemsTable(displayForm.items || []);
        // Per-tile bin overrides belong to the saved set; a freshly loaded set invalidates the drawing.
        tileBinSettings = displayForm.tileBinSettings || {};
        customBins = Array.isArray(displayForm.customBins) ? displayForm.customBins : [];
        selectedTileKey = null;
        clearDrawerLayout();
        updateBinFillFieldStates();
    }
}

function renderForm(tab) {
    const displayForm = cmFormToDisplayForm(tab, state.forms[tab]);
    writeFormToDom(tab, displayForm);
    updateSectionSummaries();
}

function renderFieldErrors(tab) {
    const panel = document.getElementById(`tab-${tab}`);
    panel.querySelectorAll('.field-error').forEach(el => {
        const field = el.dataset.errorFor;
        el.textContent = state.fieldErrors[tab][field] || '';
    });
    // Common-panel fields (grid pitch, magnet size) are validated as part of
    // whichever tab is active; reflect that tab's errors for those fields here.
    document.getElementById('common-panel').querySelectorAll('.field-error').forEach(el => {
        const field = el.dataset.errorFor;
        el.textContent = state.fieldErrors[tab][field] || '';
    });
}

function renderComputed(tab, computed) {
    const dims = document.getElementById(`${tab}-computed-dimensions`);
    if (dims) {
        if ('totalWidthMm' in computed) {
            dims.textContent = 'totalHeightMm' in computed
                ? `Actual size: ${computed.totalWidthMm} x ${computed.totalLengthMm} x ${computed.totalHeightMm} mm`
                : `Actual size: ${computed.totalWidthMm} x ${computed.totalLengthMm} mm`;
        } else {
            dims.textContent = '';
        }
    }

    const compartments = document.getElementById('bin-computed-compartments');
    if (compartments) {
        if ('compartmentCellWidthMm' in computed) {
            const widthClass = computed.compartmentCellWidthTooSmall ? 'too-small' : '';
            const lengthClass = computed.compartmentCellLengthTooSmall ? 'too-small' : '';
            compartments.innerHTML = `Cell size: <span class="${widthClass}">${computed.compartmentCellWidthMm} mm</span> x <span class="${lengthClass}">${computed.compartmentCellLengthMm} mm</span>`;
        } else {
            compartments.textContent = '';
        }
    }
}

function updateActionButtons(tab) {
    const panel = document.getElementById(`tab-${tab}`);
    panel.querySelectorAll('button[data-action="update_preview"], button[data-action="generate"]').forEach(btn => {
        btn.disabled = !state.valid[tab];
    });
}

// ---- Compartments table (bin only) ----
function readCompartmentsFromDom() {
    const rows = [];
    document.querySelectorAll('#bin-compartments-table tbody tr').forEach(tr => {
        rows.push({
            x: parseInt(tr.querySelector('[data-field="x"]').value, 10),
            y: parseInt(tr.querySelector('[data-field="y"]').value, 10),
            w: parseInt(tr.querySelector('[data-field="w"]').value, 10),
            l: parseInt(tr.querySelector('[data-field="l"]').value, 10),
            depth: parseFloat(tr.querySelector('[data-field="depth"]').value),
        });
    });
    return rows;
}

function renderCompartmentsTable(rows) {
    const tbody = document.querySelector('#bin-compartments-table tbody');
    tbody.innerHTML = '';
    rows.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.dataset.index = String(index);

        ['x', 'y', 'w', 'l', 'depth'].forEach(field => {
            const td = document.createElement('td');
            const input = document.createElement('input');
            input.type = 'number';
            input.step = field === 'depth' ? '0.1' : '1';
            input.dataset.field = field;
            input.value = row[field];
            input.addEventListener('change', () => {
                requestValidation('bin');
            });
            td.appendChild(input);
            tr.appendChild(td);
        });

        const actionTd = document.createElement('td');
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = 'x';
        removeBtn.addEventListener('click', () => {
            const compartments = readCompartmentsFromDom();
            compartments.splice(index, 1);
            renderCompartmentsTable(compartments);
            requestValidation('bin');
        });
        actionTd.appendChild(removeBtn);
        tr.appendChild(actionTd);

        tbody.appendChild(tr);
    });
}

function uniformCompartments(gridWidth, gridLength, depthMm) {
    const rows = [];
    for (let i = 0; i < gridWidth; i++) {
        for (let j = 0; j < gridLength; j++) {
            rows.push({ x: i, y: j, w: 1, l: 1, depth: depthMm });
        }
    }
    return rows;
}

// Disable a value field (and dim its label) while the checkbox that governs it is off.
// `forceOff` lets a caller fold in additional gating (e.g. plate type).
function setFieldEnabled(id, enabled) {
    const el = document.getElementById(id);
    el.disabled = !enabled;
    const label = el.closest('label');
    if (label) label.classList.toggle('disabled-row', !enabled);
}

function updateBinConditionalVisibility() {
    const gridType = document.getElementById('bin.compartmentsGridType').value;
    document.getElementById('bin-compartments-table-wrapper').classList.toggle('hidden', gridType !== 'Custom');

    const withLip = document.getElementById('bin.withLip').checked;
    const withLipNotchesInput = document.getElementById('bin.withLipNotches');
    withLipNotchesInput.disabled = !withLip;
    if (!withLip) withLipNotchesInput.checked = false;
    document.getElementById('bin-with-lip-notches-row').classList.toggle('disabled-row', !withLip);

    const hasMagnetCutouts = document.getElementById('bin.hasMagnetCutouts').checked;
    const hasMagnetCutoutsTabsInput = document.getElementById('bin.hasMagnetCutoutsTabs');
    hasMagnetCutoutsTabsInput.disabled = !hasMagnetCutouts;
    if (!hasMagnetCutouts) hasMagnetCutoutsTabsInput.checked = false;
    document.getElementById('bin-has-magnet-cutouts-tabs-row').classList.toggle('disabled-row', !hasMagnetCutouts);

    const hasScoopChecked = document.getElementById('bin.hasScoop').checked;
    setFieldEnabled('bin.scoopMaxRadius', hasScoopChecked);
    ['scoopFront', 'scoopLeft', 'scoopBack', 'scoopRight'].forEach(f => setFieldEnabled('bin.' + f, hasScoopChecked));
    const hasTab = document.getElementById('bin.hasTab').checked;
    ['tabLength', 'tabWidth', 'tabPosition', 'tabAngleDeg'].forEach(f => setFieldEnabled('bin.' + f, hasTab));
    setFieldEnabled('bin.screwDiameter', document.getElementById('bin.hasScrewHoles').checked);
}

['bin.hasScoop', 'bin.hasTab', 'bin.hasScrewHoles'].forEach(id => {
    document.getElementById(id).addEventListener('change', updateBinConditionalVisibility);
});

document.getElementById('bin-compartments-add').addEventListener('click', () => {
    const compartments = readCompartmentsFromDom();
    compartments.push({ x: 0, y: 0, w: 1, l: 1, depth: 5 });
    renderCompartmentsTable(compartments);
    requestValidation('bin');
});

document.getElementById('bin-compartments-reset-uniform').addEventListener('click', () => {
    const gridWidth = parseInt(document.getElementById('bin.compartmentsGridWidth').value, 10) || 1;
    const gridLength = parseInt(document.getElementById('bin.compartmentsGridLength').value, 10) || 1;
    renderCompartmentsTable(uniformCompartments(gridWidth, gridLength, 5));
    requestValidation('bin');
});

document.getElementById('bin.compartmentsGridType').addEventListener('change', () => {
    updateBinConditionalVisibility();
    requestValidation('bin');
});

document.getElementById('bin.withLip').addEventListener('change', () => {
    updateBinConditionalVisibility();
    requestValidation('bin');
});

document.getElementById('bin.hasMagnetCutouts').addEventListener('change', () => {
    updateBinConditionalVisibility();
    requestValidation('bin');
});

// ---- Grid Optimizer: dimension list ----
// Sorting is on-demand only (click a column header) -- the result is a literal
// row reorder, not a persisted "sort by X" rule, so it round-trips for free through
// the existing readOptimizerItemsFromDom/save/load path with no format changes.
let optimizerSort = { field: null, dir: 1 };

function sortOptimizerRows(rows) {
    if (!optimizerSort.field) return rows;
    const { field, dir } = optimizerSort;
    return [...rows].sort((a, b) => {
        if (field === 'description') {
            const av = (a.description || '').toLowerCase();
            const bv = (b.description || '').toLowerCase();
            return av < bv ? -dir : av > bv ? dir : 0;
        }
        return ((a[field] || 0) - (b[field] || 0)) * dir;
    });
}

function updateOptimizerSortIndicators() {
    document.querySelectorAll('#optimizer-items-table th.sortable').forEach(th => {
        const indicator = th.querySelector('.sort-indicator');
        if (th.dataset.sortField === optimizerSort.field) {
            indicator.textContent = optimizerSort.dir === 1 ? '▲' : '▼';
        } else {
            indicator.textContent = '';
        }
    });
}

document.querySelectorAll('#optimizer-items-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const field = th.dataset.sortField;
        optimizerSort = optimizerSort.field === field
            ? { field, dir: -optimizerSort.dir }
            : { field, dir: 1 };
        renderOptimizerItemsTable(sortOptimizerRows(readOptimizerItemsFromDom()));
        requestValidation('optimizer');
    });
});

function readOptimizerItemsFromDom() {
    const rows = [];
    document.querySelectorAll('#optimizer-items-table tbody tr').forEach(tr => {
        rows.push({
            description: tr.querySelector('[data-field="description"]').value,
            width: parseFloat(tr.querySelector('[data-field="width"]').value),
            depth: parseFloat(tr.querySelector('[data-field="depth"]').value),
        });
    });
    return rows;
}

function renderOptimizerItemsTable(rows) {
    const tbody = document.querySelector('#optimizer-items-table tbody');
    tbody.innerHTML = '';
    rows.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.dataset.index = String(index);

        const descTd = document.createElement('td');
        const descInput = document.createElement('input');
        descInput.type = 'text';
        descInput.dataset.field = 'description';
        descInput.value = row.description || '';
        descInput.addEventListener('input', () => {
            requestValidation('optimizer');
        });
        descTd.appendChild(descInput);
        tr.appendChild(descTd);

        ['width', 'depth'].forEach(field => {
            const td = document.createElement('td');
            const input = document.createElement('input');
            input.type = 'number';
            input.step = '0.1';
            input.dataset.field = field;
            input.value = row[field];
            input.addEventListener('input', () => {
                requestValidation('optimizer');
            });
            td.appendChild(input);
            tr.appendChild(td);
        });

        const actionTd = document.createElement('td');
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = 'x';
        removeBtn.addEventListener('click', () => {
            const items = readOptimizerItemsFromDom();
            items.splice(index, 1);
            renderOptimizerItemsTable(items);
            requestValidation('optimizer');
        });
        actionTd.appendChild(removeBtn);
        tr.appendChild(actionTd);

        tbody.appendChild(tr);
    });
    updateOptimizerSortIndicators();
}

document.getElementById('optimizer-items-add').addEventListener('click', () => {
    const items = readOptimizerItemsFromDom();
    items.push({ description: '', width: 100, depth: 100 });
    renderOptimizerItemsTable(sortOptimizerRows(items));
    requestValidation('optimizer');
});

function formatWasteSummary(obj, priority) {
    if (priority === 'widthOnly') {
        return `width leftover: ${obj.widthWasteMm} mm (depth ignored)`;
    }
    if (priority === 'depthOnly') {
        return `depth leftover: ${obj.depthWasteMm} mm (width ignored)`;
    }
    return `total leftover: ${obj.totalWasteMm} mm (width ${obj.widthWasteMm} / depth ${obj.depthWasteMm})`;
}

function renderFitRow(item) {
    const tr = document.createElement('tr');
    [item.description, item.type, item.dimensionMm, `${item.full} + ${item.half} half`, item.wasteMm].forEach(value => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.appendChild(td);
    });
    return tr;
}

// ---- Apply a calculated layout (optimized vs. standard 42 mm) to Common / Baseplate ----
let lastOptimizerResult = null;

// The layout the user picked: { sizeMm, items } from either the optimum or the standard grid.
function selectedOptimizerLayout() {
    const p = lastOptimizerResult;
    if (!p) return null;
    if (document.getElementById('optimizer.layoutGrid').value === 'common') {
        const w = parseFloat(document.getElementById('common.baseWidthUnit').value);
        const l = parseFloat(document.getElementById('common.baseLengthUnit').value);
        // The drawer layout works on one square pitch, so a non-square Common grid can't be used.
        if (!(w > 0) || Math.abs(w - l) > 1e-6) return null;
        const half = document.getElementById('optimizer.allowHalfBins').checked;
        // Same fit math as optimizer.calculate_fit, at the Common Settings grid unit.
        const items = (p.items || []).map(it => {
            const full = Math.floor(it.dimensionMm / w + 1e-9);
            const rem = it.dimensionMm - full * w;
            const useHalf = half && rem >= w / 2 - 1e-9;
            const waste = useHalf ? rem - w / 2 : rem;
            return Object.assign({}, it, { full: full, half: useHalf ? 1 : 0, wasteMm: Math.round(waste * 100) / 100 });
        });
        return { sizeMm: w, items: items };
    }
    if (document.getElementById('optimizer.layoutGrid').value === 'standard' && p.standard) {
        return { sizeMm: p.standard.sizeMm, items: p.standard.items };
    }
    return { sizeMm: p.optimalSizeMm, items: p.items };
}

// Items come as consecutive Width/Depth rows per opening; pair them back up.
function pairOpenings(items) {
    const openings = [];
    for (let i = 0; i + 1 < items.length; i += 2) {
        openings.push({ description: items[i].description, width: items[i], depth: items[i + 1] });
    }
    return openings;
}

function updateOptimizerLayoutSummary() {
    const layout = selectedOptimizerLayout();
    const el = document.getElementById('optimizer-layout-summary');
    if (layout) {
        el.textContent = `Selected grid size: ${layout.sizeMm} mm`;
    } else if (lastOptimizerResult && document.getElementById('optimizer.layoutGrid').value === 'common') {
        el.textContent = 'Common Settings grid must be square (equal width and length units) and above 0 to lay out a drawer.';
    } else {
        el.textContent = '';
    }
}
['common.baseWidthUnit', 'common.baseLengthUnit', 'optimizer.allowHalfBins'].forEach(id => {
    document.getElementById(id).addEventListener('input', updateOptimizerLayoutSummary);
    document.getElementById(id).addEventListener('change', updateOptimizerLayoutSummary);
});

function applyGridSizeToCommon(sizeMm) {
    const cm = mmToCm(sizeMm);
    state.forms.common = Object.assign({}, state.forms.common, { baseWidthUnit: cm, baseLengthUnit: cm });
    renderForm('common');
    sendToFusion('update_common', { form: state.forms.common });
    requestValidation(state.activeTab);
}

document.getElementById('optimizer.layoutGrid').addEventListener('change', updateOptimizerLayoutSummary);

document.getElementById('optimizer-apply-common').addEventListener('click', () => {
    const layout = selectedOptimizerLayout();
    if (!layout) return;
    applyGridSizeToCommon(layout.sizeMm);
    showNotification('success', `Grid size set to ${layout.sizeMm} mm in Common Settings`);
});

document.getElementById('optimizer-send-baseplate').addEventListener('click', () => {
    const layout = selectedOptimizerLayout();
    if (!layout) return;
    const opening = pairOpenings(layout.items)[parseInt(document.getElementById('optimizer-opening').value, 10)];
    if (!opening) return;
    const w = opening.width, d = opening.depth;
    applyGridSizeToCommon(layout.sizeMm);
    // Opening width -> plate width (X), depth -> plate length (Y). A half-size strip goes on
    // the right/back edge; leftover is split evenly into side padding so the plate is centered.
    const wasteW = mmToCm(w.wasteMm), wasteD = mmToCm(d.wasteMm);
    state.forms.baseplate = Object.assign({}, state.forms.baseplate, {
        plateWidth: w.full, plateLength: d.full,
        hasHalfLeft: false, hasHalfRight: w.half > 0, hasHalfFront: false, hasHalfBack: d.half > 0,
        hasSidePadding: w.wasteMm > 0 || d.wasteMm > 0,
        paddingLeft: wasteW / 2, paddingRight: wasteW / 2,
        paddingTop: wasteD / 2, paddingBottom: wasteD / 2,
    });
    // Stacked plates can't be laid out as separate tiles, so never leave a stack count > 1 here.
    const warnings = [];
    // Always start from Light; the user can pick another non-stackable type afterwards.
    const wasType = state.forms.baseplate.plateType;
    state.forms.baseplate.plateType = 'Light';
    state.forms.baseplate.stackCount = 1;
    if (wasType !== 'Light') {
        warnings.push(`Baseplate type set to Light (was ${wasType}); drawer layouts don't support Stackable plates, but you can switch to Full or Skeletonized`);
    }
    // Warn when the single plate won't fit the printer bed (tiling is not built yet).
    const bedW = parseFloat(document.getElementById('optimizer.bedWidth').value);
    const bedD = parseFloat(document.getElementById('optimizer.bedDepth').value);
    const tilesW = bedW > 0 ? Math.ceil(w.dimensionMm / bedW) : 1;
    const tilesD = bedD > 0 ? Math.ceil(d.dimensionMm / bedD) : 1;
    if (tilesW > 1 || tilesD > 1) {
        warnings.push(`Plate is ${w.dimensionMm} x ${d.dimensionMm} mm, larger than the ${bedW} x ${bedD} mm bed: it needs ${tilesW} x ${tilesD} tiles to print, but this sends one plate`);
    }
    renderForm('baseplate');
    setActiveTab('baseplate');
    requestValidation('baseplate');
    if (warnings.length) {
        showAlertModal(warnings, { title: 'Check the Baseplate tab' });
    } else {
        showNotification('success', `Baseplate tab set for "${opening.description || 'opening'}" at ${layout.sizeMm} mm`);
    }
});

// ---- Tiled drawer layout: request from Python, draw a read-only SVG schematic ----
// Layout inputs for the selected grid + opening + bed + bin fill settings (shared by the
// schematic request and the drawer build, so both always describe the same layout).
function currentLayoutParams() {
    const layout = selectedOptimizerLayout();
    if (!layout) return null;
    const opening = pairOpenings(layout.items)[parseInt(document.getElementById('optimizer-opening').value, 10)];
    if (!opening) return null;
    const num = id => parseFloat(document.getElementById(id).value);
    const fitOf = r => ({ full: r.full, half: r.half, wasteMm: r.wasteMm });
    return {
        pitchMm: layout.sizeMm,
        widthFit: fitOf(opening.width),
        depthFit: fitOf(opening.depth),
        bedWidthMm: num('optimizer.bedWidth'),
        bedDepthMm: num('optimizer.bedDepth'),
        binStrategy: document.getElementById('optimizer.binStrategy').value,
        maxBinCellsWidth: num('optimizer.maxBinCellsWidth') || 3,
        maxBinCellsDepth: num('optimizer.maxBinCellsDepth') || 3,
        tileBinSettings: tileBinSettings,
        customBins: customBins,
        binPalette: document.getElementById('optimizer.binPalette').value,
    };
}

// ---- Per-tile bin overrides (keyed "col,row"); click a tile in the schematic to edit ----
let tileBinSettings = {};
let selectedTileKey = null;

// Hand-drawn bins ("Draw bins by hand"): [{tile: 'col,row', x0, x1, y0, y1}], inclusive column/row
// ranges within a tile's cell grid counted from its front-left (a tile's half strip, if any, is one
// extra half-width last column/row). Saved with the optimizer set; Python validates them.
let customBins = [];
let drawMode = false;          // "Add a bin" is active: clicks on cells build a selection
let drawAnchor = null;         // first clicked cell {tile, col, row}
let drawSel = null;            // current rectangle {tile, x0, x1, y0, y1}, waiting for "Save bin"
let selectedCustomIndex = null; // a drawn bin picked (outside draw mode) for deletion
let lastDrawerLayout = null;   // latest layout_result, used to hit-test cells and bins

// Max bin width/depth only apply to "Uniform bins"; gray them out otherwise (globally and per tile),
// and only enable the size list when some tile actually uses "Mixed sizes".
function updateBinFillFieldStates() {
    const globalStrategy = document.getElementById('optimizer.binStrategy').value;
    const uniform = globalStrategy === 'uniform';
    setFieldEnabled('optimizer.maxBinCellsWidth', uniform);
    setFieldEnabled('optimizer.maxBinCellsDepth', uniform);
    const anyPalette = globalStrategy === 'palette' ||
        Object.values(tileBinSettings).some(s => s.strategy === 'palette');
    setFieldEnabled('optimizer.binPalette', anyPalette);
    document.getElementById('optimizer-fill-hint').textContent = uniform ? '' :
        'Max bin width/depth only apply to "Uniform bins"; "Mixed sizes" uses the bin size list instead.';

    const tileStrategy = document.getElementById('optimizer-tile-strategy').value || globalStrategy;
    const tileUniform = tileStrategy === 'uniform';
    setFieldEnabled('optimizer-tile-maxw', tileUniform);
    setFieldEnabled('optimizer-tile-maxd', tileUniform);
    updateCustomPanel();
}

// ---- Draw bins by hand ----
// Hand-drawn bins use one cell grid for the whole drawer (so they can cross baseplate tile seams);
// it is only active when the *global* fill is "Draw bins by hand".
function customModeActive() {
    return document.getElementById('optimizer.binStrategy').value === 'custom';
}

function emptyCellCount() {
    const grid = lastDrawerLayout && lastDrawerLayout.customGrid;
    return grid ? grid.uncovered.length : 0;
}

function updateCustomPanel() {
    const active = customModeActive();
    document.getElementById('optimizer-custom-panel').classList.toggle('hidden', !active);
    if (!active) {
        drawMode = false; drawAnchor = null; drawSel = null; selectedCustomIndex = null;
        return;
    }
    // per-tile fill settings don't apply while hand-drawing on the drawer-wide grid
    document.getElementById('optimizer-tile-panel').classList.add('hidden');
    selectedTileKey = null;
    document.getElementById('optimizer-custom-add').textContent = drawMode ? 'Done adding bins' : 'Add a bin';
    document.getElementById('optimizer-custom-save').disabled = !drawSel;
    document.getElementById('optimizer-custom-delete').disabled = selectedCustomIndex === null || drawMode;
    document.getElementById('optimizer-custom-fill').disabled = !lastDrawerLayout || emptyCellCount() === 0;
    let status;
    if (!lastDrawerLayout) status = 'Click "Show tiled layout" first, then Add a bin.';
    else if (drawMode) status = drawSel
        ? 'Click another cell to resize the selection, or Save bin.'
        : 'Click one corner cell of the bin, then the opposite corner cell (one cell is fine), then Save bin. Bins can cross baseplate tile boundaries.';
    else status = 'Add a bin to draw one, or click a drawn bin in the drawing to select it.';
    if (lastDrawerLayout) status += ` ${emptyCellCount()} empty cell(s) have no bin yet.`;
    document.getElementById('optimizer-custom-status').textContent = status;
}

function cellInDrawnBin(col, row) {
    return lastDrawerLayout.bins.some(b => b.customIndex !== undefined &&
        col >= b.cx0 && col <= b.cx1 && row >= b.cy0 && row <= b.cy1);
}

function rectOverlapsDrawnBin(sel) {
    for (let r = sel.y0; r <= sel.y1; r++) {
        for (let c = sel.x0; c <= sel.x1; c++) {
            if (cellInDrawnBin(c, r)) return true;
        }
    }
    return false;
}

function onDrawCellClick(col, row) {
    if (cellInDrawnBin(col, row)) {
        showNotification('error', 'That cell already belongs to a drawn bin');
        return;
    }
    if (!drawAnchor) {
        // first corner: a one-cell selection that the second click can stretch
        drawAnchor = { col, row };
        drawSel = { x0: col, x1: col, y0: row, y1: row };
    } else {
        const sel = {
            x0: Math.min(drawAnchor.col, col), x1: Math.max(drawAnchor.col, col),
            y0: Math.min(drawAnchor.row, row), y1: Math.max(drawAnchor.row, row),
        };
        if (rectOverlapsDrawnBin(sel)) {
            showNotification('error', 'That area overlaps a bin you already drew');
            return;
        }
        drawSel = sel;
        drawAnchor = null;  // the next click starts a new selection
    }
    updateCustomPanel();
    renderDrawerLayout(lastDrawerLayout);
}

document.getElementById('optimizer-custom-add').addEventListener('click', () => {
    if (!lastDrawerLayout) {
        showNotification('error', 'Click "Show tiled layout" first');
        return;
    }
    drawMode = !drawMode;
    drawAnchor = null; drawSel = null; selectedCustomIndex = null;
    updateCustomPanel();
    renderDrawerLayout(lastDrawerLayout);
});

document.getElementById('optimizer-custom-save').addEventListener('click', () => {
    if (!drawSel) return;
    customBins.push({ x0: drawSel.x0, x1: drawSel.x1, y0: drawSel.y0, y1: drawSel.y1 });
    drawSel = null; drawAnchor = null;
    requestLayoutRefresh();  // Python re-validates; the redraw also refreshes the buttons/status
});

document.getElementById('optimizer-custom-delete').addEventListener('click', () => {
    if (selectedCustomIndex === null) return;
    customBins.splice(selectedCustomIndex, 1);
    selectedCustomIndex = null;
    requestLayoutRefresh();
});

document.getElementById('optimizer-custom-fill').addEventListener('click', () => {
    if (!lastDrawerLayout) return;
    const grid = lastDrawerLayout.customGrid;
    if (!grid) return;
    grid.uncovered.forEach(c => customBins.push({ x0: c.col, x1: c.col, y0: c.row, y1: c.row }));
    requestLayoutRefresh();
});

document.getElementById('optimizer-custom-clear').addEventListener('click', async () => {
    if (!customBins.length) return;
    const ok = await showConfirmModal(`Remove all ${customBins.length} bins you drew? This cannot be undone.`, {
        title: 'Clear drawn bins', confirmLabel: 'Clear', danger: true,
    });
    if (!ok) return;
    customBins = []; drawSel = null; drawAnchor = null; selectedCustomIndex = null;
    requestLayoutRefresh();
});

['optimizer.binStrategy', 'optimizer-tile-strategy'].forEach(id => {
    document.getElementById(id).addEventListener('change', updateBinFillFieldStates);
});
// Changing the global fill changes what the drawing should show (and which tiles are hand-drawn).
document.getElementById('optimizer.binStrategy').addEventListener('change', () => {
    if (lastDrawerLayout) requestLayoutRefresh();
});

function requestLayoutRefresh() {
    const params = currentLayoutParams();
    if (params) sendToFusion('layout', params);
}

function showTilePanel() {
    const panel = document.getElementById('optimizer-tile-panel');
    if (!selectedTileKey) {
        panel.classList.add('hidden');
        return;
    }
    const s = tileBinSettings[selectedTileKey] || {};
    document.getElementById('optimizer-tile-title').textContent = `Selected tile (column, row): ${selectedTileKey.replace(',', ', ')} (counting from the front-left)`;
    document.getElementById('optimizer-tile-strategy').value = s.strategy || '';
    document.getElementById('optimizer-tile-maxw').value = s.maxBinCellsWidth || '';
    document.getElementById('optimizer-tile-maxd').value = s.maxBinCellsDepth || '';
    panel.classList.remove('hidden');
    updateBinFillFieldStates();
}

function onTileBinSettingChanged() {
    if (!selectedTileKey) return;
    const strategy = document.getElementById('optimizer-tile-strategy').value;
    const w = parseInt(document.getElementById('optimizer-tile-maxw').value, 10);
    const d = parseInt(document.getElementById('optimizer-tile-maxd').value, 10);
    const s = {};
    if (strategy) s.strategy = strategy;
    if (w > 0) s.maxBinCellsWidth = w;
    if (d > 0) s.maxBinCellsDepth = d;
    if (Object.keys(s).length) tileBinSettings[selectedTileKey] = s;
    else delete tileBinSettings[selectedTileKey];
    updateBinFillFieldStates();
    requestLayoutRefresh();
}

['optimizer-tile-strategy', 'optimizer-tile-maxw', 'optimizer-tile-maxd'].forEach(id => {
    document.getElementById(id).addEventListener('change', onTileBinSettingChanged);
});

// Remember the last-typed printer bed on this machine, for sessions that start without a
// saved set (a set that stores its own bed size still takes precedence when loaded).
let bedSaveTimer = null;
['optimizer.bedWidth', 'optimizer.bedDepth', 'optimizer.binBedWidth', 'optimizer.binBedDepth'].forEach(id => {
    document.getElementById(id).addEventListener('input', () => {
        clearTimeout(bedSaveTimer);
        bedSaveTimer = setTimeout(() => {
            const mm = fieldId => parseFloat(document.getElementById(fieldId).value);
            const w = mm('optimizer.bedWidth'), d = mm('optimizer.bedDepth');
            const bw = mm('optimizer.binBedWidth'), bd = mm('optimizer.binBedDepth');
            if (w > 0 && d > 0) {
                sendToFusion('update_printer_bed', {
                    bedWidth: mmToCm(w), bedDepth: mmToCm(d),
                    binBedWidth: bw > 0 ? mmToCm(bw) : null, binBedDepth: bd > 0 ? mmToCm(bd) : null,
                });
            }
        }, 500);
    });
});

document.getElementById('optimizer-show-layout').addEventListener('click', async () => {
    if (lastDrawerLayout) {
        // Hide = start over with a clean slate: drop the schematic plus any hand-drawn bins and
        // per-tile fill overrides, which only make sense relative to the layout being shown.
        const hasWork = (customBins && customBins.length) || Object.keys(tileBinSettings || {}).length;
        if (hasWork && !(await showConfirmModal(
            'Hide the layout and discard the bins you drew and any per-tile bin settings?',
            { title: 'Hide tiled layout', confirmLabel: 'Hide and reset' }))) return;
        customBins = [];
        tileBinSettings = {};
        clearDrawerLayout();
        updateBinFillFieldStates();
        return;
    }
    const params = currentLayoutParams();
    if (params) sendToFusion('layout', params);
});

function syncShowLayoutButton() {
    document.getElementById('optimizer-show-layout').textContent =
        lastDrawerLayout ? 'Hide tiled layout' : 'Show tiled layout';
}

// Describes which Baseplate/Bin tab settings the drawer will be built from.
function updateDrawerSettingsSummary() {
    const bp = readTabFormMergedWithCommon('baseplate');
    const bn = readTabFormMergedWithCommon('bin');
    document.getElementById('optimizer-drawer-settings').textContent =
        `Drawer is built from the current Baseplate tab (type: ${bp.plateType}, magnets: ${bp.hasMagnetCutouts ? 'on' : 'off'}, ` +
        `screw holes: ${bp.hasScrewHoles ? 'on' : 'off'}) and Bin tab (${bn.binType}, height ${bn.binHeight} units, ` +
        `lip: ${bn.withLip ? 'on' : 'off'}). Change those tabs to change the drawer.`;
}

async function requestDrawerBuild(action) {
    const params = currentLayoutParams();
    if (!params) {
        showNotification('error', 'Calculate and pick an opening first');
        return;
    }
    const baseplateType = document.getElementById('baseplate.plateType').value;
    if (baseplateType === 'Stackable') {
        await showAlertModal(
            'Drawer layouts cannot use Stackable baseplates. Switch the Baseplate tab to Light, Full or Skeletonized (or use "Send opening to Baseplate tab", which sets Light).',
            { title: 'Stackable baseplate' });
        return;
    }
    if (!(await confirmPreviewReplace('update_preview', 'optimizer'))) return;
    // Pieces must use the same grid size as the layout, so make Common Settings match first.
    applyGridSizeToCommon(params.pitchMm);
    const baseplate = readTabFormMergedWithCommon('baseplate');
    const bin = readTabFormMergedWithCommon('bin');
    sendToFusion(action, { tab: 'optimizer', form: { layoutParams: params, baseplate, bin } });
}

document.getElementById('optimizer-drawer-preview').addEventListener('click', () => requestDrawerBuild('drawer_preview'));
document.getElementById('optimizer-drawer-generate').addEventListener('click', () => requestDrawerBuild('drawer_generate'));
document.getElementById('optimizer-drawer-clear').addEventListener('click', () => sendToFusion('clear_preview', { tab: 'optimizer' }));
document.getElementById('optimizer-show-layout').addEventListener('click', updateDrawerSettingsSummary);
document.getElementById('optimizer-send-baseplate').addEventListener('click', updateDrawerSettingsSummary);

function clearDrawerLayout() {
    document.getElementById('optimizer-layout-schematic').innerHTML = '';
    document.getElementById('optimizer-layout-details').textContent = '';
    document.getElementById('optimizer-tile-panel').classList.add('hidden');
    selectedTileKey = null;
    lastDrawerLayout = null;
    drawMode = false; drawAnchor = null; drawSel = null; selectedCustomIndex = null;
    updateCustomPanel();
    syncShowLayoutButton();
}

// The printer bed bins are printed on: the optional "bin printer bed" if both fields are filled,
// otherwise the baseplate printer bed. Reference/warning only -- never limits the layout.
function binPrinterBed() {
    const num = id => parseFloat(document.getElementById(id).value);
    const bw = num('optimizer.binBedWidth'), bd = num('optimizer.binBedDepth');
    if (bw > 0 && bd > 0) return { w: bw, d: bd, separate: true };
    return { w: num('optimizer.bedWidth'), d: num('optimizer.bedDepth'), separate: false };
}

// A footprint fits the bed if it fits either way round (the slicer can rotate the part).
function fitsBed(wMm, dMm, bed) {
    return (wMm <= bed.w + 1e-6 && dMm <= bed.d + 1e-6) || (wMm <= bed.d + 1e-6 && dMm <= bed.w + 1e-6);
}

function renderDrawerLayout(layout) {
    lastDrawerLayout = layout;
    // A refreshed layout can invalidate a selection (tiles or bins moved/changed): drop dangling ones.
    if (selectedCustomIndex !== null && !layout.bins.some(b => b.customIndex === selectedCustomIndex)) selectedCustomIndex = null;
    if (drawSel && !layout.customGrid) { drawSel = null; drawAnchor = null; }
    const W = layout.totalWidthMm, D = layout.totalDepthMm;
    const binBed = binPrinterBed();
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${D}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `Drawer layout: ${layout.cols} by ${layout.rows} baseplate tiles, ${layout.bins.length} bins`);
    const rect = (x, y, w, h, attrs) => {
        // Front of the drawer (y = 0) is drawn at the bottom, matching Fusion's top view.
        const r = document.createElementNS(NS, 'rect');
        r.setAttribute('x', x);
        r.setAttribute('y', D - y - h);
        r.setAttribute('width', w);
        r.setAttribute('height', h);
        Object.entries(attrs).forEach(([k, v]) => r.setAttribute(k, v));
        return r;
    };
    const stroke = Math.max(W, D) / 300;
    layout.tiles.forEach(t => svg.appendChild(rect(t.xMm, t.yMm, t.widthMm, t.depthMm,
        { fill: 'none', stroke: 'var(--text-main)', 'stroke-width': stroke * 2, 'stroke-dasharray': `${stroke * 6} ${stroke * 3}` })));
    // Bins too big for the bin printer bed are outlined in the danger color (a warning, not a block).
    const oversized = layout.bins.filter(b => binBed.w > 0 && binBed.d > 0 && !fitsBed(b.widthMm, b.depthMm, binBed));
    layout.bins.forEach(b => {
        const tooBig = oversized.includes(b);
        svg.appendChild(rect(b.xMm, b.yMm, b.widthMm, b.depthMm, {
            fill: tooBig ? 'var(--text-danger)' : 'var(--btn-primary)',
            'fill-opacity': tooBig ? 0.35 : 0.45,
            stroke: tooBig ? 'var(--text-danger)' : 'var(--btn-primary)',
            'stroke-width': tooBig ? stroke * 2 : stroke,
        }));
    });
    // Transparent click targets on top: select a tile to give it its own bin fill. A tile with
    // custom settings gets a heavier outline; the selected tile gets a focus-ring colored one.
    if (!layout.customGrid) layout.tiles.forEach(t => {
        const custom = !!tileBinSettings[t.key];
        const selected = t.key === selectedTileKey;
        const hit = rect(t.xMm, t.yMm, t.widthMm, t.depthMm, {
            fill: selected ? 'var(--focus-ring)' : 'transparent',
            'fill-opacity': selected ? 0.18 : 0,
            stroke: selected || custom ? 'var(--focus-ring)' : 'none',
            'stroke-width': stroke * 3,
            cursor: 'pointer',
        });
        hit.addEventListener('click', () => {
            selectedTileKey = t.key;
            showTilePanel();
            renderDrawerLayout(layout);
        });
        const title = document.createElementNS(NS, 'title');
        title.textContent = `Tile ${t.col + 1}, ${t.row + 1}: click to set its bin fill`;
        hit.appendChild(title);
        svg.appendChild(hit);
    });

    // Hand-drawn bins live on ONE cell grid for the whole drawer (so bins can cross baseplate tile
    // seams). Grid geometry: one column per full cell plus, if the drawer has a half strip, one extra
    // half-width last column/row; padding only exists at the outer edges (originXMm/originYMm).
    const grid = layout.customGrid;
    if (grid) {
        const pitch = layout.pitchMm;
        const fullCols = grid.cols - (grid.hasHalfX ? 1 : 0);
        const fullRows = grid.rows - (grid.hasHalfY ? 1 : 0);
        const gx = i => grid.originXMm + i * pitch;
        const gy = j => grid.originYMm + j * pitch;
        const gw = i => (i < fullCols ? pitch : pitch / 2);
        const gh = j => (j < fullRows ? pitch : pitch / 2);
        const spanW = (a, b) => (b - a + 1) * pitch - (b >= fullCols ? pitch / 2 : 0);
        const spanH = (a, b) => (b - a + 1) * pitch - (b >= fullRows ? pitch / 2 : 0);
        grid.uncovered.forEach(c => svg.appendChild(rect(gx(c.col), gy(c.row), gw(c.col), gh(c.row), {
            fill: 'var(--text-sub)', 'fill-opacity': 0.15, stroke: 'var(--text-sub)',
            'stroke-width': stroke * 0.6, 'stroke-dasharray': `${stroke * 2} ${stroke * 2}`,
        })));
        if (drawMode) {
            for (let j = 0; j < grid.rows; j++) {
                for (let i = 0; i < grid.cols; i++) {
                    const cell = rect(gx(i), gy(j), gw(i), gh(j), {
                        fill: 'transparent', stroke: 'var(--border-color)', 'stroke-width': stroke * 0.4, cursor: 'crosshair',
                    });
                    cell.addEventListener('click', () => onDrawCellClick(i, j));
                    svg.appendChild(cell);
                }
            }
        } else {
            layout.bins.filter(b => b.customIndex !== undefined).forEach(b => {
                const picked = b.customIndex === selectedCustomIndex;
                const hit = rect(b.xMm, b.yMm, b.widthMm, b.depthMm, {
                    fill: picked ? 'var(--focus-ring)' : 'transparent', 'fill-opacity': picked ? 0.3 : 0,
                    stroke: picked ? 'var(--focus-ring)' : 'none', 'stroke-width': stroke * 3, cursor: 'pointer',
                });
                hit.addEventListener('click', () => {
                    selectedCustomIndex = b.customIndex;
                    updateCustomPanel();
                    renderDrawerLayout(layout);
                });
                svg.appendChild(hit);
            });
        }
        if (drawSel) {
            svg.appendChild(rect(gx(drawSel.x0), gy(drawSel.y0), spanW(drawSel.x0, drawSel.x1), spanH(drawSel.y0, drawSel.y1), {
                fill: 'var(--focus-ring)', 'fill-opacity': 0.35, stroke: 'var(--focus-ring)',
                'stroke-width': stroke * 3, 'pointer-events': 'none',
            }));
        }
    }
    const holder = document.getElementById('optimizer-layout-schematic');
    holder.innerHTML = '';
    holder.appendChild(svg);

    const lines = [`${layout.cols} x ${layout.rows} baseplate tiles, ${layout.bins.length} bins, ${layout.totalWidthMm} x ${layout.totalDepthMm} mm. Dashed = baseplate tile, filled = bin. Front is at the bottom.`];
    layout.tiles.forEach((t, i) => lines.push(
        `Tile ${i + 1}: ${t.plateWidth}${t.hasHalfRight ? '+½' : ''} x ${t.plateLength}${t.hasHalfBack ? '+½' : ''} cells, ${t.widthMm} x ${t.depthMm} mm`));
    // Reference: how the biggest bin compares with the printer bed it will be printed on.
    if (layout.bins.length && binBed.w > 0 && binBed.d > 0) {
        const biggest = layout.bins.reduce((a, b) => (b.widthMm * b.depthMm > a.widthMm * a.depthMm ? b : a));
        lines.push(`Largest bin: ${biggest.widthMm} x ${biggest.depthMm} mm. ` +
            `${binBed.separate ? 'Bin printer bed' : 'Printer bed'}: ${binBed.w} x ${binBed.d} mm.`);
        if (oversized.length) {
            lines.push(`Warning: ${oversized.length} of ${layout.bins.length} bins are larger than the ` +
                `${binBed.separate ? 'bin printer bed' : 'printer bed'} (outlined in red). This is only a warning; they will still be generated.`);
        }
    }
    (layout.warnings || []).forEach(w => lines.push(`Warning: ${w}`));
    const details = document.getElementById('optimizer-layout-details');
    details.textContent = '';
    lines.forEach(l => { const p = document.createElement('div'); p.textContent = l; details.appendChild(p); });
    updateCustomPanel();
    syncShowLayoutButton();
}

function renderOptimizerResults(payload) {
    clearDrawerLayout();
    const results = document.getElementById('optimizer-results');
    if (payload.optimalSizeMm === null || payload.optimalSizeMm === undefined) {
        results.classList.add('hidden');
        lastOptimizerResult = null;
        return;
    }
    lastOptimizerResult = payload;
    results.classList.remove('hidden');

    const openingSelect = document.getElementById('optimizer-opening');
    const previousOpening = openingSelect.value;
    openingSelect.innerHTML = '';
    pairOpenings(payload.items || []).forEach((o, i) => {
        const opt = document.createElement('option');
        opt.value = String(i);
        opt.textContent = o.description || `Opening ${i + 1}`;
        openingSelect.appendChild(opt);
    });
    if (previousOpening && openingSelect.querySelector(`option[value="${previousOpening}"]`)) {
        openingSelect.value = previousOpening;
    }
    updateOptimizerLayoutSummary();

    document.getElementById('optimizer-results-headline').textContent =
        `Optimal grid size: ${payload.optimalSizeMm} mm — ${formatWasteSummary(payload, payload.priority)}`;
    const tbody = document.querySelector('#optimizer-results-table tbody');
    tbody.innerHTML = '';
    (payload.items || []).forEach(item => tbody.appendChild(renderFitRow(item)));

    const standardSection = document.getElementById('optimizer-standard-section');
    if (payload.standard && payload.showStandard) {
        standardSection.classList.remove('hidden');
        document.getElementById('optimizer-standard-headline').textContent =
            `Standard ${payload.standard.sizeMm} mm grid — ${formatWasteSummary(payload.standard, payload.priority)}`;
        const standardTbody = document.querySelector('#optimizer-standard-table tbody');
        standardTbody.innerHTML = '';
        (payload.standard.items || []).forEach(item => standardTbody.appendChild(renderFitRow(item)));
    } else {
        standardSection.classList.add('hidden');
    }
}

// ---- Baseplate: extra bottom thickness and connection holes are only ----
// ---- meaningful for certain plate types; gray them out otherwise.    ----
function updateBaseplateConditionalVisibility() {
    const plateType = document.getElementById('baseplate.plateType').value;

    const hasExtendedBottom = plateType !== 'Light' && plateType !== 'Stackable';
    const extraBottomThicknessInput = document.getElementById('baseplate.extraBottomThickness');
    extraBottomThicknessInput.disabled = !hasExtendedBottom;
    document.getElementById('baseplate-extra-bottom-thickness-hint').textContent =
        hasExtendedBottom ? '' : 'Only applies when baseplate type is Full or Skeletonized';
    document.getElementById('baseplate-extra-bottom-thickness-row').classList.toggle('disabled-row', !hasExtendedBottom);

    const hasSkeletonizedBottom = plateType === 'Skeletonized';
    const hasConnectionHolesInput = document.getElementById('baseplate.hasConnectionHoles');
    const connectionHoleDiameterInput = document.getElementById('baseplate.connectionHoleDiameter');
    hasConnectionHolesInput.disabled = !hasSkeletonizedBottom;
    connectionHoleDiameterInput.disabled = !hasSkeletonizedBottom;
    document.getElementById('baseplate-connection-holes-hint').textContent =
        hasSkeletonizedBottom ? '' : 'Only applies when baseplate type is Skeletonized';
    document.getElementById('baseplate-connection-holes-row').classList.toggle('disabled-row', !hasSkeletonizedBottom);

    // Magnet cutouts and screw holes are cut into the extended bottom layer,
    // so like extraBottomThickness they have no effect on Light baseplates.
    const magnetInputs = document.querySelectorAll('#baseplate-magnet-cutouts-fieldset input');
    magnetInputs.forEach(el => { el.disabled = !hasExtendedBottom; });
    document.getElementById('baseplate-magnet-cutouts-hint').textContent =
        hasExtendedBottom ? '' : 'Only applies when baseplate type is Full or Skeletonized';
    document.getElementById('baseplate-magnet-cutouts-fieldset').classList.toggle('disabled-row', !hasExtendedBottom);

    const screwInputs = document.querySelectorAll('#baseplate-screw-holes-fieldset input');
    screwInputs.forEach(el => { el.disabled = !hasExtendedBottom; });
    document.getElementById('baseplate-screw-holes-hint').textContent =
        hasExtendedBottom ? '' : 'Only applies when baseplate type is Full or Skeletonized';
    document.getElementById('baseplate-screw-holes-fieldset').classList.toggle('disabled-row', !hasExtendedBottom);

    const isStackable = plateType === 'Stackable';
    const stackCount = parseInt(document.getElementById('baseplate.stackCount').value, 10) || 1;
    // Value fields follow their own checkbox, on top of the plate-type gating above.
    const hasScrewHoles = document.getElementById('baseplate.hasScrewHoles').checked;
    setFieldEnabled('baseplate.screwDiameter', hasExtendedBottom && hasScrewHoles);
    setFieldEnabled('baseplate.screwHeadDiameter', hasExtendedBottom && hasScrewHoles);
    const hasSidePadding = document.getElementById('baseplate.hasSidePadding').checked;
    ['paddingLeft', 'paddingTop', 'paddingRight', 'paddingBottom'].forEach(f => setFieldEnabled('baseplate.' + f, hasSidePadding));
    setFieldEnabled('baseplate.connectionHoleDiameter',
        hasSkeletonizedBottom && document.getElementById('baseplate.hasConnectionHoles').checked);

    document.getElementById('baseplate-stackable-fieldset').classList.toggle('disabled-row', !isStackable);
    document.getElementById('baseplate.stackCount').disabled = !isStackable;
    document.getElementById('baseplate-stackable-hint').textContent =
        isStackable ? '' : 'Only applies when baseplate type is Stackable';

    const interfaceLayerThicknessInput = document.getElementById('baseplate.interfaceLayerThickness');
    interfaceLayerThicknessInput.disabled = !isStackable || stackCount <= 1;
    document.getElementById('baseplate-interface-thickness-hint').textContent =
        !isStackable ? '' : (stackCount <= 1
            ? 'Only applies when Stack count is greater than 1'
            : 'For best results, use 1x or 2x the layer height you plan to print the baseplates with (e.g. 0.3 or 0.6mm for a 0.3mm layer height, 0.2 or 0.4mm for a 0.2mm layer height)');

    document.getElementById('baseplate-bin-z-clearance-stack-hint').textContent =
        isStackable ? 'For best print results, a clearance of at least 1-1.5mm is recommended for stackable baseplates' : '';
}

['baseplate.hasScrewHoles', 'baseplate.hasSidePadding', 'baseplate.hasConnectionHoles'].forEach(id => {
    document.getElementById(id).addEventListener('change', updateBaseplateConditionalVisibility);
});

document.getElementById('baseplate.plateType').addEventListener('change', () => {
    updateBaseplateConditionalVisibility();
    requestValidation('baseplate');
});

document.getElementById('baseplate.stackCount').addEventListener('input', () => {
    updateBaseplateConditionalVisibility();
    requestValidation('baseplate');
});

// ---- Tabs ----
function setActiveTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll('.tab-button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));
}

document.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        setActiveTab(tab);
        requestValidation(tab);
    });
});

// ---- Field change -> debounced validate ----
document.querySelectorAll('#tab-bin input[id^="bin."], #tab-bin select[id^="bin."], #tab-baseplate input[id^="baseplate."], #tab-baseplate select[id^="baseplate."], #tab-optimizer input[id^="optimizer."], #tab-optimizer select[id^="optimizer."]').forEach(el => {
    const evt = (el.tagName === 'SELECT' || el.type === 'checkbox') ? 'change' : 'input';
    el.addEventListener(evt, () => {
        const tab = el.id.split('.')[0];
        requestValidation(tab);
    });
});

// Fields shared between tabs (grid pitch + magnet size) live in a form of
// their own; anything sent to Python for a bin/baseplate tab needs them merged in.
function readTabFormMergedWithCommon(tab) {
    const displayForm = readFormFromDom(tab);
    const cmForm = displayFormToCmForm(tab, displayForm);
    return Object.assign({}, cmForm, state.forms.common);
}

function requestValidation(tab) {
    clearTimeout(validateDebounceTimers[tab]);
    validateDebounceTimers[tab] = setTimeout(() => {
        const cmForm = readTabFormMergedWithCommon(tab);
        state.forms[tab] = cmForm;
        sendToFusion('validate', { tab, form: cmForm });
    }, 200);
}

let commonDebounceTimer = null;
function requestCommonUpdate() {
    clearTimeout(commonDebounceTimer);
    commonDebounceTimer = setTimeout(() => {
        const displayForm = readFormFromDom('common');
        const cmForm = displayFormToCmForm('common', displayForm);
        state.forms.common = cmForm;
        sendToFusion('update_common', { form: cmForm });
        requestValidation(state.activeTab);
    }, 200);
}

document.querySelectorAll('#common-panel input[id^="common."]').forEach(el => {
    el.addEventListener('input', requestCommonUpdate);
});

// ---- Action buttons ----
function tabLabel(tab) {
    return tab === 'bin' ? 'Bin' : tab === 'baseplate' ? 'Baseplate' : tab === 'optimizer' ? 'Grid Optimizer drawer' : tab;
}

// Update Preview/Generate replace the single shared preview slot outright -- if it
// currently belongs to the *other* tab, doing this silently discards that unlocked
// work. Tab switching itself is left unwarned (the user may just be peeking at the
// other tab's settings), only the actions that would actually destroy it are.
async function confirmPreviewReplace(action, tab) {
    if ((action !== 'update_preview' && action !== 'generate') || !state.previewTab || state.previewTab === tab) {
        return true;
    }
    const verb = state.previewAdopted ? 'discard your in-progress edit of' : 'discard the unlocked preview for';
    return showConfirmModal(`This will ${verb} the ${tabLabel(state.previewTab)} tab. Continue?`, {
        title: 'Replace preview?',
        confirmLabel: 'Continue',
    });
}

document.querySelectorAll('button[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
        const action = btn.dataset.action;
        const tab = btn.dataset.tab;
        if (!tab) {
            sendToFusion(action, {});
            return;
        }
        if (tab === 'common') {
            sendToFusion(action, { tab });
            return;
        }
        if (tab === 'theme') {
            if (action === 'factory_reset') {
                const ok = await showConfirmModal(
                    'This permanently deletes every imported theme and resets font settings to default. Continue?',
                    { title: 'Factory Reset Themes', confirmLabel: 'Reset', danger: true },
                );
                if (!ok) return;
            }
            sendToFusion(action, { tab });
            return;
        }
        if (!(await confirmPreviewReplace(action, tab))) return;
        const cmForm = readTabFormMergedWithCommon(tab);
        state.forms[tab] = cmForm;
        sendToFusion(action, { tab, form: cmForm });
    });
});

// ---- Config manager buttons ----
// Load/Delete/Save As all open a modal instead of acting on an inline dropdown --
// only Update Current acts directly on the currently active config, with no dialog.
document.querySelectorAll('button[data-config-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
        const configAction = btn.dataset.configAction;
        const tab = btn.dataset.tab;

        if (configAction === 'save_as') {
            const defaultName = state.activeConfig[tab] || '';
            const name = await showPromptModal('Save config as:', defaultName, {
                title: 'Save config as',
                confirmLabel: 'Save',
            });
            if (!name) return;
            const cmForm = readTabFormMergedWithCommon(tab);
            state.forms[tab] = cmForm;
            sendToFusion('save_config_as', { tab, form: cmForm, name });
        } else if (configAction === 'update_current') {
            const cmForm = readTabFormMergedWithCommon(tab);
            state.forms[tab] = cmForm;
            sendToFusion('update_current_config', { tab, form: cmForm });
        } else if (configAction === 'load') {
            if (!state.configs[tab].length) {
                showNotification('error', 'No saved configs to load');
                return;
            }
            const name = await showPickerModal('Choose a config to load:', state.configs[tab], {
                title: 'Load config',
                confirmLabel: 'Load',
            });
            if (!name) return;
            sendToFusion('load_config', { tab, name });
        } else if (configAction === 'delete') {
            if (!state.configs[tab].length) {
                showNotification('error', 'No saved configs to delete');
                return;
            }
            const name = await showPickerModal('Choose a config to delete:', state.configs[tab], {
                title: 'Delete config',
                confirmLabel: 'Delete',
                danger: true,
            });
            if (!name) return;
            sendToFusion('delete_config', { tab, name });
        }
    });
});

// ---- Theme (Theme Designer Pro standard: CSS vars + data-theme attribute) ----
const importedThemes = {};
const BUILTIN_THEME_NAMES = ['System', 'Light', 'Dark', 'Midnight', 'Sandstone'];
// Every color CSS custom property style.css's :root block actually declares -- kept
// in sync with that block by hand. Used to snapshot the full effective theme's colors
// when exporting. Deliberately excludes --font-family/--font-size-base: those are
// independent Font Family/Size controls (see applyFontOverrides), sent/restored as
// their own top-level export fields instead -- baking them in here previously let a
// theme's font silently out-specificity the independent controls on import (higher
// CSS specificity of :root[data-theme=X] vs plain :root), so font never reliably
// round-tripped.
const THEME_VAR_NAMES = [
    '--bg-body', '--text-main', '--text-sub', '--border-color',
    '--row-bg', '--row-border', '--row-hover',
    '--input-bg', '--input-border', '--input-text', '--input-placeholder',
    '--header-hover', '--tab-bg', '--tab-active-bg', '--tab-text', '--tab-active-text',
    '--btn-primary', '--btn-primary-hover', '--btn-secondary', '--btn-secondary-hover', '--btn-secondary-text',
    '--status-success-bg', '--status-success-text',
    '--status-error-bg', '--status-error-text',
    '--status-info-bg', '--status-info-text',
    '--banner-warning-bg', '--banner-warning-text', '--banner-warning-border',
];
let systemThemeMediaQuery = null;

function systemThemeListener(e) {
    if (e.matches) {
        document.documentElement.setAttribute('data-theme', 'Dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
}

function watchSystemTheme() {
    if (!systemThemeMediaQuery) {
        systemThemeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        systemThemeMediaQuery.addEventListener('change', systemThemeListener);
    }
    systemThemeListener(systemThemeMediaQuery);
}

function stopWatchingSystemTheme() {
    if (systemThemeMediaQuery) {
        systemThemeMediaQuery.removeEventListener('change', systemThemeListener);
        systemThemeMediaQuery = null;
    }
}

function injectCustomTheme(name, vars) {
    let styleTag = document.getElementById('dynamic-theme-overrides');
    if (!styleTag) {
        styleTag = document.createElement('style');
        styleTag.id = 'dynamic-theme-overrides';
        document.head.appendChild(styleTag);
    }
    const decls = Object.entries(vars).map(([k, v]) => `${k}: ${v};`).join(' ');
    styleTag.textContent = `:root[data-theme="${name}"] { ${decls} }`;
}

function applyTheme(name, customVars) {
    if (customVars) {
        injectCustomTheme(name, customVars);
    }
    if (name === 'System') {
        watchSystemTheme();
    } else {
        stopWatchingSystemTheme();
        if (name && name !== 'Light') {
            document.documentElement.setAttribute('data-theme', name);
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }
}

// Font family/size are edited independently of which theme is selected -- applied
// as a plain :root override so they take effect on top of any theme (built-in or
// imported), rather than being tied to a specific data-theme value like
// injectCustomTheme's per-theme color overrides are.
function applyFontOverrides(fontFamily, fontSize) {
    let styleTag = document.getElementById('font-overrides');
    if (!styleTag) {
        styleTag = document.createElement('style');
        styleTag.id = 'font-overrides';
        document.head.appendChild(styleTag);
    }
    styleTag.textContent = `:root { --font-family: ${fontFamily}; --font-size-base: ${fontSize}px; }`;
}

function updateThemeRemoveButtonState() {
    const name = state.forms.theme.name;
    document.getElementById('theme-remove').disabled = BUILTIN_THEME_NAMES.includes(name) || !(name in importedThemes);
}

function ensureThemeOption(name, label) {
    const select = document.getElementById('theme.name');
    let opt = Array.from(select.options).find(o => o.value === name);
    if (!opt) {
        opt = document.createElement('option');
        opt.value = name;
        select.appendChild(opt);
    }
    opt.textContent = label || name;
}

document.getElementById('theme.name').addEventListener('change', () => {
    const name = document.getElementById('theme.name').value;
    state.forms.theme = { ...state.forms.theme, name };
    applyTheme(name, importedThemes[name] || null);
    updateThemeRemoveButtonState();
    sendToFusion('update_theme', { form: state.forms.theme });
    document.getElementById('theme-import-hint').textContent = '';
});

document.getElementById('theme.fontFamily').addEventListener('change', () => {
    const fontFamily = document.getElementById('theme.fontFamily').value;
    state.forms.theme = { ...state.forms.theme, fontFamily };
    applyFontOverrides(state.forms.theme.fontFamily, state.forms.theme.fontSize);
    sendToFusion('update_theme', { form: state.forms.theme });
});

document.getElementById('theme.fontSize').addEventListener('change', () => {
    const fontSize = parseFloat(document.getElementById('theme.fontSize').value);
    state.forms.theme = { ...state.forms.theme, fontSize };
    applyFontOverrides(state.forms.theme.fontFamily, state.forms.theme.fontSize);
    sendToFusion('update_theme', { form: state.forms.theme });
});

document.getElementById('theme-import').addEventListener('click', () => {
    document.getElementById('theme-import-input').click();
});

document.getElementById('theme-import-input').addEventListener('change', (evt) => {
    const file = evt.target.files && evt.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
        try {
            const data = JSON.parse(reader.result);
            if (!data || !data.id || !data.vars) {
                throw new Error('Missing "id" or "vars"');
            }
            // Strip any font vars baked into older exports -- font is independent of
            // theme colors now (see THEME_VAR_NAMES comment), but fall back to reading
            // them out of vars for files exported before that change.
            const vars = { ...data.vars };
            const legacyFontFamily = vars['--font-family'];
            const legacyFontSize = vars['--font-size-base'];
            delete vars['--font-family'];
            delete vars['--font-size-base'];
            const fontFamily = data.fontFamily || legacyFontFamily || state.forms.theme.fontFamily;
            const fontSize = data.fontSize != null
                ? Number(data.fontSize)
                : (legacyFontSize ? parseFloat(legacyFontSize) : state.forms.theme.fontSize);

            importedThemes[data.id] = vars;
            ensureThemeOption(data.id, `${data.id} (imported)`);
            document.getElementById('theme.name').value = data.id;
            state.forms.theme = { ...state.forms.theme, name: data.id, fontFamily, fontSize };
            applyTheme(data.id, vars);
            applyFontOverrides(fontFamily, fontSize);
            // Font Family is a closed 3-option list -- only reflect the imported value
            // in the dropdown if it's an exact match; otherwise leave it on its current
            // option while the literal string above still applies visually.
            const fontFamilySelect = document.getElementById('theme.fontFamily');
            if (Array.from(fontFamilySelect.options).some(opt => opt.value === fontFamily)) {
                fontFamilySelect.value = fontFamily;
            }
            document.getElementById('theme.fontSize').value = fontSize;
            updateThemeRemoveButtonState();
            sendToFusion('save_imported_theme', { id: data.id, vars });
            sendToFusion('update_theme', { form: state.forms.theme });
            document.getElementById('theme-import-hint').textContent = `Imported "${data.id}"`;
        } catch (e) {
            document.getElementById('theme-import-hint').textContent = 'Could not read that file — expected a Theme Designer Pro .theme.json export';
        }
    };
    reader.readAsText(file);
    evt.target.value = '';
});

// Exports a full snapshot of every currently effective themed color variable,
// regardless of which built-in/imported theme produced it -- read via
// getComputedStyle rather than reassembled from state, so it's always exactly what's
// currently on screen. Font Family/Size are sent as separate top-level fields sourced
// directly from state (not getComputedStyle) since they're independent of the color
// theme -- see THEME_VAR_NAMES comment. The actual file write happens on the Python
// side via a native Save dialog (see entry._handle_export_theme) -- a plain Blob/
// anchor download has no reliable destination inside Fusion's embedded webview.
document.getElementById('theme-export').addEventListener('click', async () => {
    const defaultName = BUILTIN_THEME_NAMES.includes(state.forms.theme.name) ? '' : state.forms.theme.name;
    const id = await showPromptModal('Export theme as:', defaultName, {
        title: 'Export theme',
        confirmLabel: 'Export',
    });
    if (!id) return;
    const computed = getComputedStyle(document.documentElement);
    const vars = {};
    THEME_VAR_NAMES.forEach(name => {
        vars[name] = computed.getPropertyValue(name).trim();
    });
    sendToFusion('export_theme', {
        id,
        vars,
        fontFamily: state.forms.theme.fontFamily,
        fontSize: state.forms.theme.fontSize,
    });
});

document.getElementById('theme-remove').addEventListener('click', async () => {
    const name = state.forms.theme.name;
    if (BUILTIN_THEME_NAMES.includes(name) || !(name in importedThemes)) return;
    const ok = await showConfirmModal(`Remove imported theme "${name}"? This cannot be undone.`, {
        title: 'Remove theme',
        confirmLabel: 'Remove',
        danger: true,
    });
    if (!ok) return;
    delete importedThemes[name];
    const select = document.getElementById('theme.name');
    const opt = Array.from(select.options).find(o => o.value === name);
    if (opt) opt.remove();
    select.value = 'System';
    state.forms.theme = { ...state.forms.theme, name: 'System' };
    applyTheme('System', null);
    updateThemeRemoveButtonState();
    sendToFusion('remove_imported_theme', { id: name });
    sendToFusion('update_theme', { form: state.forms.theme });
    document.getElementById('theme-import-hint').textContent = `Removed "${name}"`;
});

// ---- Theme CSS-bundle import/export ----
// GGPlus's own style.css is full of project-specific layout rules (tabs, tables,
// compartments...) that aren't portable to another project, so unlike the fleet's
// LiveUtilities reference (which exports a complete drop-in stylesheet), this bundle
// is just the color-variable blocks -- the same var set as the single-theme .theme.json
// export above, one `:root[data-theme="Name"]` block per theme. Built-in-named blocks
// are never accepted on import since there's no per-variable color editor here to make
// overriding a built-in meaningful (unlike LiveUtilities' live-editable theme model).
function parseStyleCssThemeBlocks(cssText) {
    const blockRegex = /:root(?:\[data-theme=["']([^"']+)["']\])?\s*\{([^}]*)\}/g;
    const themes = {};
    let match;
    while ((match = blockRegex.exec(cssText)) !== null) {
        const id = match[1] || 'Light';
        const content = match[2];
        const vars = {};
        const varRegex = /(--[\w-]+)\s*:\s*([^;]+?)(?=\s*;|\s*$)/g;
        let vMatch;
        while ((vMatch = varRegex.exec(content)) !== null) {
            vars[vMatch[1].trim()] = vMatch[2].trim();
        }
        themes[id] = vars;
    }
    return themes;
}

function themeBlockToCss(id, vars) {
    const selector = id === 'Light' ? ':root' : `:root[data-theme="${id}"]`;
    let out = `${selector} {\n`;
    THEME_VAR_NAMES.forEach(name => {
        if (vars[name]) out += `  ${name}: ${vars[name]};\n`;
    });
    out += `}\n\n`;
    return out;
}

document.getElementById('theme-export-css').addEventListener('click', async () => {
    let builtIn = {};
    try {
        const res = await fetch('style.css');
        if (!res.ok) throw new Error('fetch failed');
        builtIn = parseStyleCssThemeBlocks(await res.text());
    } catch (e) {
        showNotification('error', 'Could not read style.css to build the export bundle');
        return;
    }
    let out = '';
    BUILTIN_THEME_NAMES.filter(name => name !== 'System').forEach(id => {
        if (builtIn[id]) out += themeBlockToCss(id, builtIn[id]);
    });
    Object.entries(importedThemes).forEach(([id, vars]) => {
        out += themeBlockToCss(id, vars);
    });
    sendToFusion('export_theme', { file_type: 'css', content: out.trim() + '\n', default_name: 'GGPlus_themes.css' });
});

document.getElementById('theme-import-css').addEventListener('click', () => {
    document.getElementById('theme-import-css-input').click();
});

document.getElementById('theme-import-css-input').addEventListener('change', (evt) => {
    const file = evt.target.files && evt.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
        try {
            const parsed = parseStyleCssThemeBlocks(reader.result);
            const customIds = Object.keys(parsed).filter(id => !BUILTIN_THEME_NAMES.includes(id));
            if (customIds.length === 0) {
                document.getElementById('theme-import-hint').textContent =
                    'No custom (non-built-in) theme blocks found in that file';
                return;
            }
            customIds.forEach(id => {
                importedThemes[id] = parsed[id];
                ensureThemeOption(id, `${id} (imported)`);
                sendToFusion('save_imported_theme', { id, vars: parsed[id] });
            });
            const firstId = customIds[0];
            document.getElementById('theme.name').value = firstId;
            state.forms.theme = { ...state.forms.theme, name: firstId };
            applyTheme(firstId, importedThemes[firstId]);
            updateThemeRemoveButtonState();
            sendToFusion('update_theme', { form: state.forms.theme });
            const skipped = Object.keys(parsed).length - customIds.length;
            document.getElementById('theme-import-hint').textContent =
                `Imported ${customIds.length} theme(s)${skipped ? `, skipped ${skipped} built-in-named block(s)` : ''}`;
        } catch (e) {
            document.getElementById('theme-import-hint').textContent =
                'Could not read that file — expected a Theme Designer Pro style.css export';
        }
    };
    reader.readAsText(file);
    evt.target.value = '';
});

// ---- Bridge readiness ----
function waitForFusionBridge(retries = 40) {
    if (window.adsk && window.adsk.fusionSendData) {
        sendToFusion('get_defaults');
    } else if (retries > 0) {
        setTimeout(() => waitForFusionBridge(retries - 1), 250);
    } else {
        console.error('Fusion bridge never became available');
    }
}

// ---- Tooltips: keep them inside the palette, and don't let a click on an icon
// ---- inside a <label> focus/toggle that label's input.
function positionTooltip(icon) {
    const tip = icon.querySelector('.tooltip');
    if (!tip) return;
    tip.style.left = '0';
    tip.classList.remove('tooltip-below');
    let rect = tip.getBoundingClientRect();
    const overflow = rect.right - (window.innerWidth - 8);
    if (overflow > 0) tip.style.left = `${-overflow}px`;
    if (rect.top < 4) tip.classList.add('tooltip-below');
}
document.addEventListener('mouseover', e => {
    const icon = e.target.closest && e.target.closest('.info-icon');
    if (icon) positionTooltip(icon);
});
document.addEventListener('focusin', e => {
    const icon = e.target.closest && e.target.closest('.info-icon');
    if (icon) positionTooltip(icon);
});
document.addEventListener('click', e => {
    if (e.target.closest && e.target.closest('label .info-icon')) e.preventDefault();
});

// (Initial render and bridge handshake live at the very end of this file so every
// const/let above -- including the section-summary tables -- is initialized first.)
// Left-align checkbox labels (box + text together) instead of space-between.
document.querySelectorAll('label > input[type="checkbox"]').forEach(cb => {
    cb.parentElement.classList.add('checkbox-label');
});

// ---- Collapsible sections: remember open/closed per section ----
// index.html sets the first-launch defaults via the `open` attribute; Python
// persists only the sections the user has toggled (GGPlus_config.json).
function sectionKey(details) {
    const panel = details.closest('.tab-panel');
    // Own text nodes only -- the summary also holds a live .summary-hint span.
    const title = Array.from(details.querySelector(':scope > summary').childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE).map(n => n.textContent).join('').trim();
    return (panel ? panel.id : 'app') + ':' + title;
}

let applyingSectionState = false;

function applySectionState(saved) {
    applyingSectionState = true;
    document.querySelectorAll('details.section').forEach(d => {
        const key = sectionKey(d);
        if (key in saved) d.open = !!saved[key];
    });
    // toggle events fire asynchronously; release the guard after they've run
    setTimeout(() => { applyingSectionState = false; }, 0);
}

// `toggle` doesn't bubble, so listen in the capture phase.
document.addEventListener('toggle', e => {
    if (applyingSectionState) return;
    const d = e.target;
    if (!(d instanceof HTMLDetailsElement) || !d.classList.contains('section')) return;
    sendToFusion('update_section_state', { key: sectionKey(d), open: d.open });
}, true);

// ---- Collapsed-section summary hints + expand/collapse all ----
function _val(id) { return document.getElementById(id).value; }
function _on(id) { return document.getElementById(id).checked; }
function _onOff(id, extra) { return _on(id) ? (extra ? 'on, ' + extra : 'on') : 'off'; }

const SECTION_SUMMARIES = {
    'common-panel': () => `${_val('common.baseWidthUnit')}\u00d7${_val('common.baseLengthUnit')} mm grid, clr ${_val('common.xyClearance')}, magnet \u00d8${_val('common.magnetDiameter')}\u00d7${_val('common.magnetDepth')}`,
    'tab-bin:Basic size': () => `${_val('bin.heightUnit')} mm height unit`,
    'tab-bin:Dimensions': () => {
        const half = ['Left', 'Right', 'Front', 'Back'].some(s => _on('bin.hasHalf' + s));
        return `${_val('bin.binWidth')}×${_val('bin.binLength')}×${_val('bin.binHeight')}` + (half ? ', half edges' : '');
    },
    'tab-bin:Body': () => {
        if (!_on('bin.generateBody')) return 'no body';
        return _val('bin.binType').toLowerCase() + (_on('bin.withLip') ? ', lip' : ', no lip');
    },
    'tab-baseplate:Main dimensions': () => {
        const half = ['Left', 'Right', 'Front', 'Back'].some(s => _on('baseplate.hasHalf' + s));
        return `${_val('baseplate.plateWidth')}×${_val('baseplate.plateLength')}` + (half ? ', half edges' : '');
    },
    'tab-baseplate:Features': () => _val('baseplate.plateType'),
    'tab-bin:Compartments': () => _val('bin.compartmentsGridType') === 'Custom'
        ? 'custom' : `${_val('bin.compartmentsGridWidth')}\u00d7${_val('bin.compartmentsGridLength')}`,
    'tab-bin:Scoop': () => _onOff('bin.hasScoop', _val('bin.scoopMaxRadius') + ' mm'),
    'tab-bin:Label tab': () => _onOff('bin.hasTab'),
    'tab-bin:Base': () => {
        const parts = [];
        if (_on('bin.hasScrewHoles')) parts.push('screw holes');
        if (_on('bin.hasMagnetCutouts')) parts.push('magnets');
        return parts.length ? parts.join(', ') : 'plain';
    },
    'tab-bin:Advanced': () => {
        const parts = [];
        if (_on('bin.withLipNotches')) parts.push('lip notches');
        if (_on('bin.hasMagnetCutoutsTabs')) parts.push('magnet tabs');
        return parts.length ? parts.join(', ') : 'defaults';
    },
    'tab-bin:Configurations': () => activeConfigHint('bin'),
    'tab-baseplate:Configurations': () => activeConfigHint('baseplate'),
    'tab-baseplate:Stacking': () => _val('baseplate.plateType') === 'Stackable'
        ? `\u00d7${_val('baseplate.stackCount')}` : 'n/a',
    'tab-baseplate:Laser cutting': () => _onOff('baseplate.generateDxfSketch'),
    'tab-baseplate:Magnet cutouts': () => _onOff('baseplate.hasMagnetCutouts'),
    'tab-baseplate:Screw holes': () => _onOff('baseplate.hasScrewHoles'),
    'tab-baseplate:Side padding': () => _onOff('baseplate.hasSidePadding'),
    'tab-baseplate:Advanced': () => _val('baseplate.plateType') === 'Skeletonized'
        ? _onOff('baseplate.hasConnectionHoles', null).replace(/^/, 'connection holes ') : 'defaults',
};

function activeConfigHint(tab) {
    return (state.activeConfig && state.activeConfig[tab]) || 'none';
}

function updateSectionSummaries() {
    document.querySelectorAll('details.section').forEach(d => {
        const key = d.id === 'common-panel' ? 'common-panel' : sectionKey(d);
        const fn = SECTION_SUMMARIES[key];
        if (!fn) return;
        const summary = d.querySelector(':scope > summary');
        let hint = summary.querySelector('.summary-hint');
        if (!hint) {
            hint = document.createElement('span');
            hint.className = 'summary-hint';
            summary.appendChild(hint);
        }
        try { hint.textContent = '\u00b7 ' + fn(); } catch (e) { hint.textContent = ''; }
    });
}

document.addEventListener('input', updateSectionSummaries);
document.addEventListener('change', updateSectionSummaries);

function setSectionsOpen(open) {
    document.querySelectorAll('.tab-panel.active details.section').forEach(d => { d.open = open; });
}
document.getElementById('sections-expand-all').addEventListener('click', () => setSectionsOpen(true));
document.getElementById('sections-collapse-all').addEventListener('click', () => setSectionsOpen(false));

// Auto-open a collapsed section that holds a validation error, without
// persisting that as the user's own open/closed choice.
function openSectionsWithErrors() {
    document.querySelectorAll('.field-error').forEach(el => {
        if (!el.textContent) return;
        const d = el.closest('details.section');
        if (d && !d.open) {
            applyingSectionState = true;
            d.open = true;
            setTimeout(() => { applyingSectionState = false; }, 0);
        }
    });
}

renderForm('common');
renderForm('bin');
renderForm('baseplate');
renderForm('optimizer');
renderForm('theme');
applyTheme(state.forms.theme.name, null);
applyFontOverrides(state.forms.theme.fontFamily, state.forms.theme.fontSize);
updateThemeRemoveButtonState();
renderConfigStatus('bin');
renderConfigStatus('baseplate');
renderConfigStatus('optimizer');
waitForFusionBridge();
