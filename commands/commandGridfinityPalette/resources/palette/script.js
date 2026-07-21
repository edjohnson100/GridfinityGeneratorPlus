// ---- Unit conversion: Python speaks cm (Fusion's internal unit), this UI displays mm. ----
const CM_TO_MM = 10;

const MM_FIELDS = {
    common: ['baseWidthUnit', 'baseLengthUnit', 'xyClearance', 'magnetDiameter', 'magnetDepth'],
    bin: ['heightUnit', 'wallThickness', 'scoopMaxRadius', 'tabWidth', 'screwDiameter'],
    baseplate: ['screwDiameter', 'screwHeadDiameter', 'paddingLeft', 'paddingTop', 'paddingRight', 'paddingBottom', 'extraBottomThickness', 'binZClearance', 'connectionHoleDiameter', 'interfaceLayerThickness'],
    optimizer: ['minSize', 'maxSize'],
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
            minSize: 3.0, maxSize: 7.5, allowHalfBins: true, compareStandard: false, priority: 'balanced', items: [],
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
            } else if (action === 'config_list') {
                onConfigList(parsed);
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

function _openModal({ title, bodyHtml, confirmLabel, danger, getValue, onOpen }) {
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
    document.getElementById('modal-overlay').classList.remove('hidden');

    return new Promise(resolve => {
        _modalResolve = resolve;
        confirmBtn.onclick = () => _closeModal(getValue ? getValue() : true);
        document.getElementById('modal-btn-cancel').onclick = () => _closeModal(null);
        document.getElementById('modal-overlay').onclick = e => {
            if (e.target.id === 'modal-overlay') _closeModal(null);
        };
        document.addEventListener('keydown', _modalKeydown);
        if (onOpen) onOpen();
    });
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
        } else if (el.tagName === 'SELECT') {
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
    }
}

function renderForm(tab) {
    const displayForm = cmFormToDisplayForm(tab, state.forms[tab]);
    writeFormToDom(tab, displayForm);
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
}

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

function renderOptimizerResults(payload) {
    const results = document.getElementById('optimizer-results');
    if (payload.optimalSizeMm === null || payload.optimalSizeMm === undefined) {
        results.classList.add('hidden');
        return;
    }
    results.classList.remove('hidden');

    document.getElementById('optimizer-results-headline').textContent =
        `Optimal grid size: ${payload.optimalSizeMm} mm — ${formatWasteSummary(payload, payload.priority)}`;
    const tbody = document.querySelector('#optimizer-results-table tbody');
    tbody.innerHTML = '';
    (payload.items || []).forEach(item => tbody.appendChild(renderFitRow(item)));

    const standardSection = document.getElementById('optimizer-standard-section');
    if (payload.standard) {
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
    return tab === 'bin' ? 'Bin' : tab === 'baseplate' ? 'Baseplate' : tab;
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
