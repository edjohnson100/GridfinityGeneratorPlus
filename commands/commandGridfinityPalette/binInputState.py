from dataclasses import dataclass


@dataclass
class CompartmentState:
    positionX: int
    positionY: int
    width: int
    length: int
    depth: float


@dataclass
class BinInputState:
    baseWidthUnit: float
    baseLengthUnit: float
    heightUnit: float
    xyClearance: float
    binWidth: int
    binLength: int
    binHeight: float

    generateBody: bool
    binType: str
    wallThickness: float
    withLip: bool
    withLipNotches: bool

    compartmentsGridType: str
    compartmentsGridWidth: int
    compartmentsGridLength: int
    compartments: list

    hasScoop: bool
    scoopMaxRadius: float

    hasTab: bool
    tabLength: float
    tabWidth: float
    tabPosition: float
    tabAngle: float

    generateBase: bool
    hasScrewHoles: bool
    screwDiameter: float
    hasMagnetCutouts: bool
    hasMagnetCutoutsTabs: bool
    magnetDiameter: float
    magnetDepth: float

    @staticmethod
    def from_form(form: dict) -> 'BinInputState':
        import math
        compartments = [
            CompartmentState(
                positionX=int(row['x']),
                positionY=int(row['y']),
                width=int(row['w']),
                length=int(row['l']),
                depth=float(row['depth']),
            )
            for row in form.get('compartments', [])
        ]
        return BinInputState(
            baseWidthUnit=float(form['baseWidthUnit']),
            baseLengthUnit=float(form['baseLengthUnit']),
            heightUnit=float(form['heightUnit']),
            xyClearance=float(form['xyClearance']),
            binWidth=int(form['binWidth']),
            binLength=int(form['binLength']),
            binHeight=float(form['binHeight']),
            generateBody=bool(form['generateBody']),
            binType=form['binType'],
            wallThickness=float(form['wallThickness']),
            withLip=bool(form['withLip']),
            withLipNotches=bool(form['withLipNotches']),
            compartmentsGridType=form['compartmentsGridType'],
            compartmentsGridWidth=int(form['compartmentsGridWidth']),
            compartmentsGridLength=int(form['compartmentsGridLength']),
            compartments=compartments,
            hasScoop=bool(form['hasScoop']),
            scoopMaxRadius=float(form['scoopMaxRadius']),
            hasTab=bool(form['hasTab']),
            tabLength=float(form['tabLength']),
            tabWidth=float(form['tabWidth']),
            tabPosition=float(form['tabPosition']),
            tabAngle=math.radians(float(form['tabAngleDeg'])),
            generateBase=bool(form['generateBase']),
            hasScrewHoles=bool(form['hasScrewHoles']),
            screwDiameter=float(form['screwDiameter']),
            hasMagnetCutouts=bool(form['hasMagnetCutouts']),
            hasMagnetCutoutsTabs=bool(form['hasMagnetCutoutsTabs']),
            magnetDiameter=float(form['magnetDiameter']),
            magnetDepth=float(form['magnetDepth']),
        )
