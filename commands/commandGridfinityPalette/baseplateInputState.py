from dataclasses import dataclass


@dataclass
class BaseplateInputState:
    baseWidthUnit: float
    baseLengthUnit: float
    xyClearance: float
    plateWidth: int
    plateLength: int

    hasHalfLeft: bool
    hasHalfRight: bool
    hasHalfFront: bool
    hasHalfBack: bool

    plateType: str

    hasMagnetCutouts: bool
    magnetDiameter: float
    magnetDepth: float

    hasScrewHoles: bool
    screwDiameter: float
    screwHeadDiameter: float

    hasSidePadding: bool
    paddingLeft: float
    paddingTop: float
    paddingRight: float
    paddingBottom: float

    extraBottomThickness: float
    binZClearance: float

    hasConnectionHoles: bool
    connectionHoleDiameter: float

    stackCount: int
    interfaceLayerThickness: float

    generateDxfSketch: bool

    @staticmethod
    def from_form(form: dict) -> 'BaseplateInputState':
        return BaseplateInputState(
            baseWidthUnit=float(form['baseWidthUnit']),
            baseLengthUnit=float(form['baseLengthUnit']),
            xyClearance=float(form['xyClearance']),
            plateWidth=int(form['plateWidth']),
            plateLength=int(form['plateLength']),
            hasHalfLeft=bool(form.get('hasHalfLeft', False)),
            hasHalfRight=bool(form.get('hasHalfRight', False)),
            hasHalfFront=bool(form.get('hasHalfFront', False)),
            hasHalfBack=bool(form.get('hasHalfBack', False)),
            plateType=form['plateType'],
            hasMagnetCutouts=bool(form['hasMagnetCutouts']),
            magnetDiameter=float(form['magnetDiameter']),
            magnetDepth=float(form['magnetDepth']),
            hasScrewHoles=bool(form['hasScrewHoles']),
            screwDiameter=float(form['screwDiameter']),
            screwHeadDiameter=float(form['screwHeadDiameter']),
            hasSidePadding=bool(form['hasSidePadding']),
            paddingLeft=float(form['paddingLeft']),
            paddingTop=float(form['paddingTop']),
            paddingRight=float(form['paddingRight']),
            paddingBottom=float(form['paddingBottom']),
            extraBottomThickness=float(form['extraBottomThickness']),
            binZClearance=float(form['binZClearance']),
            hasConnectionHoles=bool(form['hasConnectionHoles']),
            connectionHoleDiameter=float(form['connectionHoleDiameter']),
            stackCount=int(form['stackCount']),
            interfaceLayerThickness=float(form['interfaceLayerThickness']),
            generateDxfSketch=bool(form.get('generateDxfSketch', False)),
        )
