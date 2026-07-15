import math

from ...lib.gridfinityUtils import const


def validate_bin(form: dict) -> dict:
    fieldErrors = {}

    def get(key, default=None):
        return form.get(key, default)

    baseWidthUnit = float(get('baseWidthUnit', 0))
    baseLengthUnit = float(get('baseLengthUnit', 0))
    heightUnit = float(get('heightUnit', 0))
    xyClearance = float(get('xyClearance', 0))
    binWidth = float(get('binWidth', 0))
    binLength = float(get('binLength', 0))
    binHeight = float(get('binHeight', 0))
    wallThickness = float(get('wallThickness', 0))
    generateBase = bool(get('generateBase'))
    generateBody = bool(get('generateBody'))
    hasScrewHoles = bool(get('hasScrewHoles'))
    hasMagnetCutouts = bool(get('hasMagnetCutouts'))
    screwDiameter = float(get('screwDiameter', 0))
    magnetDiameter = float(get('magnetDiameter', 0))
    magnetDepth = float(get('magnetDepth', 0))
    binType = get('binType')
    hasScoop = bool(get('hasScoop'))
    scoopMaxRadius = float(get('scoopMaxRadius', 0))
    hasTab = bool(get('hasTab'))
    tabLength = float(get('tabLength', 0))
    tabWidth = float(get('tabWidth', 0))
    tabPosition = float(get('tabPosition', 0))
    tabAngleDeg = float(get('tabAngleDeg', 0))
    compartmentsGridType = get('compartmentsGridType')
    compartmentsGridWidth = int(get('compartmentsGridWidth', 1))
    compartmentsGridLength = int(get('compartmentsGridLength', 1))
    compartments = get('compartments', [])

    if not baseWidthUnit > 1:
        fieldErrors['baseWidthUnit'] = 'Must be greater than 1mm'
    if not baseLengthUnit > 1:
        fieldErrors['baseLengthUnit'] = 'Must be greater than 1mm'
    if not heightUnit > 0.5:
        fieldErrors['heightUnit'] = 'Must be greater than 0.5mm'
    if not (0.01 <= xyClearance <= 0.05):
        fieldErrors['xyClearance'] = 'Must be within [0.01, 0.05]mm'
    if not binWidth > 0:
        fieldErrors['binWidth'] = 'Must be greater than 0'
    if not binLength > 0:
        fieldErrors['binLength'] = 'Must be greater than 0'
    if not binHeight >= 1:
        fieldErrors['binHeight'] = 'Must be at least 1'
    if not (0.04 <= wallThickness <= 0.2):
        fieldErrors['wallThickness'] = 'Must be within [0.04, 0.2]mm'

    if generateBase:
        if hasScrewHoles and not screwDiameter > 0.1:
            fieldErrors['screwDiameter'] = 'Must be greater than 0.1mm'
        if hasMagnetCutouts and not screwDiameter < magnetDiameter:
            fieldErrors['magnetDiameter'] = 'Must be greater than screw diameter'
        if not magnetDepth > 0:
            fieldErrors['magnetDepth'] = 'Must be greater than 0'

    if generateBody and binType == 'Hollow':
        if hasScoop and not scoopMaxRadius > 0:
            fieldErrors['scoopMaxRadius'] = 'Must be greater than 0'
        if hasTab:
            if not tabLength > 0:
                fieldErrors['tabLength'] = 'Must be greater than 0'
            if not tabWidth > 0:
                fieldErrors['tabWidth'] = 'Must be greater than 0'
            if not tabPosition >= 0:
                fieldErrors['tabPosition'] = 'Must be at least 0'
            if not (30 <= tabAngleDeg <= 65):
                fieldErrors['tabAngleDeg'] = 'Must be within [30, 65] degrees'
        if compartmentsGridType == 'Custom':
            for i, row in enumerate(compartments):
                posX = int(row.get('x', 0))
                posY = int(row.get('y', 0))
                width = int(row.get('w', 0))
                length = int(row.get('l', 0))
                if not (posX >= 0 and posX + width <= compartmentsGridWidth and width > 0):
                    fieldErrors[f'compartments[{i}].x'] = 'Compartment exceeds grid width'
                if not (posY >= 0 and posY + length <= compartmentsGridLength and length > 0):
                    fieldErrors[f'compartments[{i}].y'] = 'Compartment exceeds grid length'

    computed = {}
    try:
        actualWidth = baseWidthUnit * binWidth - const.BIN_XY_CLEARANCE * 2
        actualLength = baseLengthUnit * binLength - const.BIN_XY_CLEARANCE * 2
        actualHeight = heightUnit * binHeight + ((const.BIN_LIP_EXTRA_HEIGHT - const.BIN_LIP_TOP_RECESS_HEIGHT) if bool(get('withLip')) else 0)
        computed['totalWidthMm'] = round(actualWidth * 10, 2)
        computed['totalLengthMm'] = round(actualLength * 10, 2)
        computed['totalHeightMm'] = round(actualHeight * 10, 2)

        minCompartmentDimensionLimit = (const.BIN_CORNER_FILLET_RADIUS - wallThickness) * 2 * 10
        cellWidth = round((baseWidthUnit * binWidth - wallThickness * 2 - xyClearance * 2 - wallThickness * (compartmentsGridWidth - 1)) / compartmentsGridWidth * 10, 2)
        cellLength = round((baseLengthUnit * binLength - wallThickness * 2 - xyClearance * 2 - wallThickness * (compartmentsGridLength - 1)) / compartmentsGridLength * 10, 2)
        computed['compartmentCellWidthMm'] = cellWidth
        computed['compartmentCellLengthMm'] = cellLength
        computed['compartmentCellWidthTooSmall'] = cellWidth < minCompartmentDimensionLimit
        computed['compartmentCellLengthTooSmall'] = cellLength < minCompartmentDimensionLimit
    except (ZeroDivisionError, ValueError):
        pass

    return {
        'valid': len(fieldErrors) == 0,
        'fieldErrors': fieldErrors,
        'computed': computed,
    }


def validate_baseplate(form: dict) -> dict:
    fieldErrors = {}

    def get(key, default=None):
        return form.get(key, default)

    baseWidthUnit = float(get('baseWidthUnit', 0))
    baseLengthUnit = float(get('baseLengthUnit', 0))
    xyClearance = float(get('xyClearance', 0))
    plateWidth = float(get('plateWidth', 0))
    plateLength = float(get('plateLength', 0))
    hasMagnetCutouts = bool(get('hasMagnetCutouts'))
    magnetDiameter = float(get('magnetDiameter', 0))
    magnetDepth = float(get('magnetDepth', 0))
    hasScrewHoles = bool(get('hasScrewHoles'))
    screwDiameter = float(get('screwDiameter', 0))
    screwHeadDiameter = float(get('screwHeadDiameter', 0))
    hasConnectionHoles = bool(get('hasConnectionHoles'))
    connectionHoleDiameter = float(get('connectionHoleDiameter', 0))
    extraBottomThickness = float(get('extraBottomThickness', 0))

    if not baseWidthUnit >= 1:
        fieldErrors['baseWidthUnit'] = 'Must be at least 1mm'
    if not baseLengthUnit >= 1:
        fieldErrors['baseLengthUnit'] = 'Must be at least 1mm'
    if not (0.01 <= xyClearance <= 0.05):
        fieldErrors['xyClearance'] = 'Must be within [0.01, 0.05]mm'
    if not plateWidth > 0:
        fieldErrors['plateWidth'] = 'Must be greater than 0'
    if not plateLength > 0:
        fieldErrors['plateLength'] = 'Must be greater than 0'

    if hasMagnetCutouts:
        if not (0 < magnetDiameter <= 1):
            fieldErrors['magnetDiameter'] = 'Must be within (0, 1]mm'
        if not magnetDepth > 0:
            fieldErrors['magnetDepth'] = 'Must be greater than 0'

    if hasScrewHoles:
        if not (0 < screwDiameter <= 1):
            fieldErrors['screwDiameter'] = 'Must be within (0, 1]mm'
        if not (screwHeadDiameter > screwDiameter and screwHeadDiameter <= 1.5):
            fieldErrors['screwHeadDiameter'] = 'Must be greater than screw diameter and at most 1.5mm'

    if hasConnectionHoles and not (0 < connectionHoleDiameter <= 0.5):
        fieldErrors['connectionHoleDiameter'] = 'Must be within (0, 0.5]mm'

    if not extraBottomThickness > 0:
        fieldErrors['extraBottomThickness'] = 'Must be greater than 0'

    return {
        'valid': len(fieldErrors) == 0,
        'fieldErrors': fieldErrors,
        'computed': {},
    }
