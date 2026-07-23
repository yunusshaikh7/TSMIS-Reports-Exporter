"""Worker threads for the GUI.

Playwright's sync API is thread-affine, so all browser work happens on a
dedicated worker thread -- never on the GUI's main/UI thread. Workers
communicate by putting messages on a queue.Queue (thread-safe); the GuiApi
pump drains it and forwards each to the WebView2 renderer via evaluate_js.
Workers never touch the window or the DOM directly.

Message protocol (all are (kind, payload) tuples):
    ("log", str)                       one status line
    ("progress", dict)                 {done,total,route,report,report_i,report_n,saved,empty,skipped,failed,exists}
    ("worker_status", (worker, text))  what browser `worker` (1-based) is doing
                                       right now (statuses replace each other)
    ("preview_shot", (worker, b64, note, url))  an on-demand page screenshot
                                       for browser `worker` — b64 is a base64
                                       JPEG string, or None when the capture
                                       failed (note then says why); url is the
                                       page's address at capture time
    ("env_shot", dict)                 the idle "Verify environment" result:
                                       {ok, img (b64 JPEG|None), env, src,
                                        matches, url, error} — url is the
                                       page's address at screenshot time (the
                                       intended one when it never opened)
    ("env_access", dict)               one combo's verdict from the Settings
                                       "Check all environments" scan, posted
                                       as it finishes: {key, source,
                                       environment, label, status, detail,
                                       url, reports} — status is one of ok |
                                       unverified | reports_off | no_reports |
                                       denied | no_signin | wrong_site |
                                       unreachable | error; reports maps each report
                                       type's dropdown label to
                                       ok | greyed | missing (empty when the
                                       dropdown couldn't be read)
    ("env_access_done", dict)          the scan ended:
                                       {ok, done, total, cancelled, error}
    ("reset_done", dict)               outcome of "Delete all reports":
                                       {files, mb, errors: [str, ...]}
    ("chromium_done", dict)            outcome of the Built-in Chromium
                                       download/delete: {ok, action,
                                       cancelled, error}
    ("export_done", [(spec, RunResult), ...])   all selected reports finished
    ("export_partial", [(spec, RunResult), ...]) reports done before an error (then an "error" follows)
    ("consolidate_done", ConsolidateResult)
    ("login_open", None)               headed browser is up; user should finish SSO
    ("login_saved", None)              a VALID session was captured and written
    ("login_device_ok", None)          silent device sign-in works on this PC, but the
                                       session is device-bound: no file saved; exports
                                       sign themselves in live (device sign-in mode)
    ("login_failed", None)             window closed/finished without a real login
    ("cancelled", None)                task stopped at user request
    ("error", (kind, message))         kind is "auth" or "general"
    ("update_status", dict)            one-click update progress; the dict is the
                                       GUI's whole update state (phase, version,
                                       progress, ...) -- see gui_api._on_update_status
"""

# S2 (v0.19.0): the workers moved to four per-cluster modules; this module is
# the RE-EXPORT SHIM (the common.py precedent) so every existing import — the
# GUI mixins, the checks, the docs — keeps working unchanged. Import from the
# owning module in NEW code.
from gui_worker_export import (ConsolidateWorker, BatchWorker, ExportWorker,   # noqa: F401
                               _swap_store_dir)
from gui_worker_env import (ActiveEnvCheckWorker, EnvCheckWorker,              # noqa: F401
                            EnvScanWorker, LoginWorker, env_verdict,
                            _REPORT_OPTIONS_JS)
from gui_worker_maint import (CheckWorker, ChromiumWorker, ResetWorker,        # noqa: F401
                              UpdateWorker, ValidationWorker,
                              measure_targets, reset_targets)
from gui_worker_matrix import (BaselineMatrixCompareWorker,                    # noqa: F401
                               DayMatrixCompareWorker, MatrixBatchExportWorker,
                               MatrixCompareWorker, MatrixEvidenceWorker,
                               MatrixTsnConsolidateWorker,
                               PdfExcelMatrixCompareWorker,
                               _run_matrix_export_step)

# Collaborators historically reachable AS gui_worker attributes (the checks and
# older callers read them here); the workers themselves use their own module's
# bindings — patch the OWNING module to stub a worker's collaborator.
import baseline_matrix  # noqa: F401
import batch_manifest  # noqa: F401
import day_matrix      # noqa: F401
import matrix          # noqa: F401
import outcome         # noqa: F401
from common import AuthError, BrowserNotFoundError, get_site, set_site  # noqa: F401
from events import Events  # noqa: F401
