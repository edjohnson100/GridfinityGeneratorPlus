import adsk.core, adsk.fusion

from ...lib import fusion360utils as futil

app = adsk.core.Application.get()

_preview_tab = None
_preview_occurrence_token = None
_preview_feature_tokens = []


def track_preview(tab: str, tracked):
    """tracked is either an Occurrence (new component was created) or a list of the
    timeline entities created directly in the root component."""
    global _preview_tab, _preview_occurrence_token, _preview_feature_tokens
    _preview_tab = tab
    if isinstance(tracked, adsk.fusion.Occurrence):
        _preview_occurrence_token = tracked.entityToken
        _preview_feature_tokens = []
    else:
        _preview_occurrence_token = None
        _preview_feature_tokens = [entity.entityToken for entity in tracked if entity]


def clear_preview():
    global _preview_tab, _preview_occurrence_token, _preview_feature_tokens
    if _preview_occurrence_token is None and not _preview_feature_tokens:
        return
    occurrenceToken = _preview_occurrence_token
    featureTokens = _preview_feature_tokens
    _preview_tab = None
    _preview_occurrence_token = None
    _preview_feature_tokens = []
    try:
        des = adsk.fusion.Design.cast(app.activeProduct)
        if des is None:
            return
        if occurrenceToken is not None:
            entities = des.findEntityByToken(occurrenceToken)
            if entities and len(entities) > 0:
                occurrence = adsk.fusion.Occurrence.cast(entities[0])
                if occurrence:
                    occurrence.deleteMe()
        else:
            # Delete in reverse creation order so dependent features go first.
            for token in reversed(featureTokens):
                entities = des.findEntityByToken(token)
                if entities and len(entities) > 0 and hasattr(entities[0], 'deleteMe'):
                    entities[0].deleteMe()
    except Exception as err:
        futil.log(f'GridfinityPalette previewState: failed to clear preview, {err}')


def has_preview() -> bool:
    return _preview_occurrence_token is not None or bool(_preview_feature_tokens)
