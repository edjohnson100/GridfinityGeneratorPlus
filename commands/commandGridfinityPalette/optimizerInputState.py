from dataclasses import dataclass


@dataclass
class DimensionItem:
    description: str
    width: float
    depth: float


@dataclass
class OptimizerInputState:
    minSize: float
    maxSize: float
    allowHalfBins: bool
    compareStandard: bool
    priority: str
    items: list

    @staticmethod
    def from_form(form: dict) -> 'OptimizerInputState':
        items = [
            DimensionItem(
                description=str(row.get('description') or ''),
                width=float(row['width']),
                depth=float(row['depth']),
            )
            for row in form.get('items', [])
        ]
        return OptimizerInputState(
            minSize=float(form['minSize']),
            maxSize=float(form['maxSize']),
            allowHalfBins=bool(form['allowHalfBins']),
            compareStandard=bool(form['compareStandard']),
            priority=form.get('priority', 'balanced'),
            items=items,
        )
