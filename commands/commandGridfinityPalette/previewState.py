import adsk.core, adsk.fusion

from ...lib import fusion360utils as futil

app = adsk.core.Application.get()

_preview_tab = None
_preview_occurrence_token = None
_preview_feature_tokens = []
_preview_is_adopted = False
_preview_original_name = None

# Every distinct preview ever tracked this session (appended on track_preview(), never
# overwritten), so resync() can recognize *any* of them reappearing after Undo/Redo --
# not just the single most recently cleared one. A user who does Preview -> Generate ->
# Preview -> Generate and then steps back several Undo's should still get the Clear
# Preview button re-synced when the *first* preview resurfaces, not just the last.
# Bounded so a long session doesn't grow this unboundedly; only the most recent entries
# are realistically reachable by Undo anyway.
_preview_history = []
_PREVIEW_HISTORY_LIMIT = 50


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

    _preview_history.append({
        'tab': _preview_tab,
        'occurrence_token': _preview_occurrence_token,
        'feature_tokens': _preview_feature_tokens,
        'is_adopted': _preview_is_adopted,
        'original_name': _preview_original_name,
    })
    del _preview_history[:-_PREVIEW_HISTORY_LIMIT]


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


def get_preview_tab():
    return _preview_tab


def get_preview_adopted() -> bool:
    return _preview_is_adopted


def get_preview_occurrence_token():
    return _preview_occurrence_token


def _resolves(des: adsk.fusion.Design, occurrenceToken, featureTokens) -> bool:
    if occurrenceToken is not None:
        entities = des.findEntityByToken(occurrenceToken)
        return bool(entities) and len(entities) > 0
    if featureTokens:
        # Any one surviving feature is enough to say "still there" -- Undo/Redo
        # moves the whole group together, it won't partially resurrect it.
        entities = des.findEntityByToken(featureTokens[0])
        return bool(entities) and len(entities) > 0
    return False


def resync():
    """Reconciles module-level tracking with the actual document state after an
    Undo/Redo -- Fusion's undo/redo doesn't fire any per-mutation event we can hook,
    so the palette's "Clear Preview" button can otherwise go stale: undoing an Update
    Preview/Generate leaves has_preview() reporting True for a component that's gone,
    and undoing far enough to resurrect an *earlier* preview (e.g. Preview -> Generate
    -> Preview -> Generate, then several Undo's) leaves it reporting False even though
    that earlier preview is back and clearable again.

    Returns (changed, tab, active): `changed` is True if tracking was swapped, in
    which case `tab` names the affected tab and `active` is its new has_preview()-
    equivalent state -- exactly what the palette's 'preview_status' message expects.
    """
    global _preview_tab, _preview_occurrence_token, _preview_feature_tokens, _preview_is_adopted, _preview_original_name

    des = adsk.fusion.Design.cast(app.activeProduct)
    if des is None:
        return False, None, False

    dropped_tab = None
    if has_preview() and not _resolves(des, _preview_occurrence_token, _preview_feature_tokens):
        # The tracked preview/adopted component was undone away.
        dropped_tab = _preview_tab
        _preview_tab = None
        _preview_occurrence_token = None
        _preview_feature_tokens = []
        _preview_is_adopted = False
        _preview_original_name = None

    if not has_preview():
        # Look for any past preview attempt that's reappeared (in most-recently-
        # tracked-first order), whether or not one was just dropped above -- e.g. an
        # Undo can resurrect an earlier preview in a single step without the current
        # slot having been tracking anything to begin with.
        for entry in reversed(_preview_history):
            if _resolves(des, entry['occurrence_token'], entry['feature_tokens']):
                _preview_tab = entry['tab']
                _preview_occurrence_token = entry['occurrence_token']
                _preview_feature_tokens = entry['feature_tokens']
                _preview_is_adopted = entry['is_adopted']
                _preview_original_name = entry['original_name']
                return True, _preview_tab, True

    if dropped_tab is not None:
        return True, dropped_tab, False

    return False, None, False
