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
        theme: { name: 'System' },
    },
    fieldErrors: { bin: {}, baseplate: {}, optimizer: {} },
    valid: { bin: true, baseplate: true, optimizer: true },
    configs: { bin: [], baseplate: [], optimizer: [] },
    activeConfig: { bin: null, baseplate: null, optimizer: null },
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
        Object.entries(payload.importedThemes || {}).forEach(([id, vars]) => {
            importedThemes[id] = vars;
            ensureThemeOption(id, `${id} (imported)`);
        });
        renderForm('theme');
        applyTheme(cmForm.name, importedThemes[cmForm.name] || null);
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
    if (tab === 'bin') {
        renderComputed(payload.computed || {});
    }
    updateActionButtons(tab);
}

function onPreviewStatus(payload) {
    document.querySelectorAll('.clear-preview-button').forEach(btn => {
        btn.disabled = !payload.active;
    });
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
    renderConfigManager(tab);
}

function renderConfigManager(tab) {
    const select = document.getElementById(`${tab}-config-select`);
    const active = state.activeConfig[tab];
    const previousValue = select.value;
    select.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = state.configs[tab].length ? 'Select a config…' : 'No saved configs';
    select.appendChild(placeholder);
    state.configs[tab].forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
    });
    if (active && state.configs[tab].includes(active)) {
        select.value = active;
    } else if (state.configs[tab].includes(previousValue)) {
        select.value = previousValue;
    } else {
        select.value = '';
    }

    const activeLabel = document.getElementById(`${tab}-config-active`);
    activeLabel.textContent = active ? `Active: ${active}` : 'Active: (none, using defaults)';

    document.getElementById(`${tab}-config-update`).disabled = !active;
}

function showNotification(type, message) {
    const el = document.getElementById('notification');
    el.textContent = message;
    el.className = `notification ${type}`;
    clearTimeout(showNotification._timer);
    showNotification._timer = setTimeout(() => {
        el.classList.add('hidden');
    }, 5000);
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

function renderComputed(computed) {
    const dims = document.getElementById('bin-computed-dimensions');
    if ('totalWidthMm' in computed) {
        dims.textContent = `Actual size: ${computed.totalWidthMm} x ${computed.totalLengthMm} x ${computed.totalHeightMm} mm`;
    } else {
        dims.textContent = '';
    }

    const compartments = document.getElementById('bin-computed-compartments');
    if ('compartmentCellWidthMm' in computed) {
        const widthClass = computed.compartmentCellWidthTooSmall ? 'too-small' : '';
        const lengthClass = computed.compartmentCellLengthTooSmall ? 'too-small' : '';
        compartments.innerHTML = `Cell size: <span class="${widthClass}">${computed.compartmentCellWidthMm} mm</span> x <span class="${lengthClass}">${computed.compartmentCellLengthMm} mm</span>`;
    } else {
        compartments.textContent = '';
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

// ---- Grid Optimizer: dimension list ----
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
}

document.getElementById('optimizer-items-add').addEventListener('click', () => {
    const items = readOptimizerItemsFromDom();
    items.push({ description: '', width: 100, depth: 100 });
    renderOptimizerItemsTable(items);
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
document.querySelectorAll('button[data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
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
        const cmForm = readTabFormMergedWithCommon(tab);
        state.forms[tab] = cmForm;
        sendToFusion(action, { tab, form: cmForm });
    });
});

// ---- Config manager buttons ----
document.querySelectorAll('button[data-config-action]').forEach(btn => {
    btn.addEventListener('click', () => {
        const configAction = btn.dataset.configAction;
        const tab = btn.dataset.tab;
        const select = document.getElementById(`${tab}-config-select`);
        const selectedName = select.value;

        if (configAction === 'save_as') {
            const defaultName = state.activeConfig[tab] || '';
            const name = window.prompt('Save config as:', defaultName);
            if (!name) return;
            const cmForm = readTabFormMergedWithCommon(tab);
            state.forms[tab] = cmForm;
            sendToFusion('save_config_as', { tab, form: cmForm, name });
        } else if (configAction === 'update_current') {
            const cmForm = readTabFormMergedWithCommon(tab);
            state.forms[tab] = cmForm;
            sendToFusion('update_current_config', { tab, form: cmForm });
        } else if (configAction === 'load') {
            if (!selectedName) {
                showNotification('error', 'Select a config to load');
                return;
            }
            sendToFusion('load_config', { tab, name: selectedName });
        } else if (configAction === 'delete') {
            if (!selectedName) {
                showNotification('error', 'Select a config to delete');
                return;
            }
            if (!window.confirm(`Delete config "${selectedName}"?`)) return;
            sendToFusion('delete_config', { tab, name: selectedName });
        }
    });
});

// ---- Theme (Theme Designer Pro standard: CSS vars + data-theme attribute) ----
const importedThemes = {};
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
    state.forms.theme = { name };
    applyTheme(name, importedThemes[name] || null);
    sendToFusion('update_theme', { form: state.forms.theme });
    document.getElementById('theme-import-hint').textContent = '';
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
            importedThemes[data.id] = data.vars;
            ensureThemeOption(data.id, `${data.id} (imported)`);
            document.getElementById('theme.name').value = data.id;
            state.forms.theme = { name: data.id };
            applyTheme(data.id, data.vars);
            sendToFusion('save_imported_theme', { id: data.id, vars: data.vars });
            sendToFusion('update_theme', { form: state.forms.theme });
            document.getElementById('theme-import-hint').textContent = `Imported "${data.id}"`;
        } catch (e) {
            document.getElementById('theme-import-hint').textContent = 'Could not read that file — expected a Theme Designer Pro .theme.json export';
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

renderForm('common');
renderForm('bin');
renderForm('baseplate');
renderForm('optimizer');
renderForm('theme');
applyTheme(state.forms.theme.name, null);
renderConfigManager('bin');
renderConfigManager('baseplate');
renderConfigManager('optimizer');
waitForFusionBridge();
