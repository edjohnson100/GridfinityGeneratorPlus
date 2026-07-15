import adsk.core, adsk.fusion

from ...lib import fusion360utils as futil

app = adsk.core.Application.get()

_preview_tab = None
_preview_occurrence_token = None
_preview_feature_tokens = []
_preview_is_adopted = False
_preview_original_name = None


def track_preview(tab: str, tracked, adopted: bool = False, original_name: str = None):
    """tracked is either an Occurrence (new component was created) or a list of the
    timeline entities created directly in the root component.

    adopted=True marks that this isn't a fresh preview built from scratch, but a
    previously-generated (permanent) component that the user chose to re-edit via
    "Edit Active Component". See clear_preview()'s force param.

    original_name is the adopted component's pre-edit name (it was given a PREVIEW_
    prefix when adopted); it's restored if editing is released without being finalized
    or deleted. Unused for fresh previews.
    """
    global _preview_tab, _preview_occurrence_token, _preview_feature_tokens, _preview_is_adopted, _preview_original_name
    _preview_tab = tab
    _preview_is_adopted = adopted
    _preview_original_name = original_name
    if isinstance(tracked, adsk.fusion.Occurrence):
        _preview_occurrence_token = tracked.entityToken
        _preview_feature_tokens = []
    else:
        _preview_occurrence_token = None
        _preview_feature_tokens = [entity.entityToken for entity in tracked if entity]


def clear_preview(force: bool = True):
    """Clears whatever is currently tracked.

    Fresh previews (adopted=False) are always deleted. Adopted components (the user's
    real, previously-generated part, loaded back in for editing) are only deleted when
    force=True (an explicit Clear Preview / Update Preview / Generate click) -- when
    force=False (palette close, add-in stop, switching to edit a different component)
    the tracking is simply released and the component is left untouched.
    """
    global _preview_tab, _preview_occurrence_token, _preview_feature_tokens, _preview_is_adopted, _preview_original_name
    if _preview_occurrence_token is None and not _preview_feature_tokens:
        return
    occurrenceToken = _preview_occurrence_token
    featureTokens = _preview_feature_tokens
    isAdopted = _preview_is_adopted
    originalName = _preview_original_name
    _preview_tab = None
    _preview_occurrence_token = None
    _preview_feature_tokens = []
    _preview_is_adopted = False
    _preview_original_name = None

    if isAdopted and not force:
        try:
            des = adsk.fusion.Design.cast(app.activeProduct)
            if des is not None and occurrenceToken is not None and originalName is not None:
                entities = des.findEntityByToken(occurrenceToken)
                if entities and len(entities) > 0:
                    occurrence = adsk.fusion.Occurrence.cast(entities[0])
                    if occurrence:
                        occurrence.component.name = originalName
        except Exception as err:
            futil.log(f'GridfinityPalette previewState: failed to restore adopted component look, {err}')
        return

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
