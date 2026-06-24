"""The shared js_api endpoint decorator (P7c).

Extracted from `gui_api` so both `gui_api.GuiApi` and the new `gui_matrix.GuiMatrixMixin`
can decorate their pywebview-exposed methods without a `gui_api` ↔ `gui_matrix` import
cycle. Behavior-identical to the original `gui_api._api_method`.
"""
import logging


def _api_method(fn):
    """Wrap a js_api method: an uncaught exception in a windowed .exe would
    vanish (no stderr) and leave the UI hanging on a dead Promise, so log the
    full traceback and hand JS a structured error instead."""
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            logging.getLogger("tsmis.crash").critical(
                "uncaught exception in GUI api %s", fn.__name__, exc_info=True)
            try:
                self._emit_log(f"ERROR: {type(e).__name__}: {e} (details in the log file)")
            except Exception:
                pass
            return {"error": f"{type(e).__name__}: {e} (details are in the log file)"}
    wrapper.__name__ = fn.__name__
    return wrapper
