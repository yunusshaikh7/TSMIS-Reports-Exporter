"""Bridge protocol SSOT (P7a) — the canonical vocabulary the GUI worker→main
message bus and the single-task gate speak, named in ONE place instead of as bare
string literals scattered across `gui_api.py` / `gui_worker.py` / `ui/app.js`.

These NAME the exact strings the protocol already uses (so importing/using them is
behavior-neutral — the wire values are unchanged); the value is that the dispatch
table, the TaskCoordinator, the lifecycle checks, and `get_initial_state` reference
one declared set, and a drift (a kind added on one side only) is visible. The
frontend mirror lives in `ui/contract.js` (P9); `get_initial_state` surfaces the
subset the UI needs so the two can't silently diverge.

Console-free, dependency-free (stdlib only) — the lowest leaf in the GUI layer.
"""


class Task:
    """The single-task-gate task kinds (the value of `TaskCoordinator.task`)."""
    EXPORT = "export"
    CONSOLIDATE = "consolidate"
    LOGIN = "login"
    BATCH = "batch"
    MATRIX = "matrix"
    ENVCHECK = "envcheck"
    ENVSCAN = "envscan"
    RESET = "reset"
    CHROMIUM = "chromium"
    COMPARE = "compare"
    VALIDATE = "validate"       # W1: one-click sample validation


# Every gate task kind (for validation / the lifecycle checks).
TASKS = frozenset({
    Task.EXPORT, Task.CONSOLIDATE, Task.LOGIN, Task.BATCH, Task.MATRIX,
    Task.ENVCHECK, Task.ENVSCAN, Task.RESET, Task.CHROMIUM, Task.COMPARE,
    Task.VALIDATE,
})


class Msg:
    """Worker → main-thread message kinds posted on the pump queue and dispatched
    by `GuiApi._handle`. TERMINAL kinds end the task that owns the gate (exactly
    once — see TaskCoordinator); the rest are progress/status updates."""
    # --- terminal (free the single-task gate) ---
    EXPORT_DONE = "export_done"
    CONSOLIDATE_DONE = "consolidate_done"
    RESET_DONE = "reset_done"
    VALIDATE_DONE = "validate_done"
    CHROMIUM_DONE = "chromium_done"
    BATCH_DONE = "batch_done"
    MATRIX_DONE = "matrix_done"
    MATRIX_EXPORT_DONE = "matrix_export_done"
    ENV_SHOT = "env_shot"
    ENV_ACCESS_DONE = "env_access_done"
    ERROR = "error"
    CANCELLED = "cancelled"
    LOGIN_SAVED = "login_saved"
    LOGIN_DEVICE_OK = "login_device_ok"
    LOGIN_FAILED = "login_failed"
    # --- non-terminal (progress / status) ---
    LOG = "log"
    PROGRESS = "progress"
    WORKER_STATUS = "worker_status"
    PREVIEW_SHOT = "preview_shot"
    ENV_ACCESS = "env_access"
    ACTIVE_ENV_DONE = "active_env_done"
    EXPORT_PARTIAL = "export_partial"
    LOGIN_OPEN = "login_open"
    CHECK = "check"
    CHECKS_DONE = "checks_done"
    BATCH_PROGRESS = "batch_progress"
    MATRIX_CELL = "matrix_cell"
    UPDATE_STATUS = "update_status"


# The terminal kinds — the ones that, via `_handle`, free the single-task gate.
# (`env_shot`/`reset_done`/`chromium_done`/`matrix_*`/`env_access_done` encode
# cancel/error in their payload rather than emitting a separate kind; they are still
# the one terminal for their task — see check_worker_lifecycle.)
TERMINAL = frozenset({
    Msg.EXPORT_DONE, Msg.CONSOLIDATE_DONE, Msg.RESET_DONE, Msg.CHROMIUM_DONE,
    Msg.BATCH_DONE, Msg.MATRIX_DONE, Msg.MATRIX_EXPORT_DONE, Msg.ENV_SHOT,
    Msg.ENV_ACCESS_DONE, Msg.ERROR, Msg.CANCELLED,
    Msg.LOGIN_SAVED, Msg.LOGIN_DEVICE_OK, Msg.LOGIN_FAILED,
    Msg.VALIDATE_DONE,
})


class LoginPhase:
    """`GuiApi._login_phase` — where an interactive login is in its flow."""
    STARTING = "starting"
    OPEN = "open"
    SAVING = "saving"
    CANCELLING = "cancelling"


class ErrorKind:
    """The first element of an `error` terminal payload `(kind, message)`."""
    AUTH = "auth"
    GENERAL = "general"


class EnvAccess:
    """Per-environment access verdicts (the env-scan / active-env check)."""
    OK = "ok"
    UNVERIFIED = "unverified"
    REPORTS_OFF = "reports_off"
    NO_REPORTS = "no_reports"
    DENIED = "denied"
    NO_SIGNIN = "no_signin"
    WRONG_SITE = "wrong_site"
    UNREACHABLE = "unreachable"
    ERROR = "error"


def initial_state_enums():
    """The subset of the bridge vocabulary `get_initial_state` surfaces to the
    frontend, so `ui/contract.js` (P9) can be checked against the backend SSOT
    instead of re-hardcoding the strings. Plain JSON-safe lists/dicts."""
    return {
        "tasks": sorted(TASKS),
        "terminal_kinds": sorted(TERMINAL),
        "env_access": [EnvAccess.OK, EnvAccess.UNVERIFIED, EnvAccess.REPORTS_OFF,
                       EnvAccess.NO_REPORTS, EnvAccess.DENIED, EnvAccess.NO_SIGNIN,
                       EnvAccess.WRONG_SITE, EnvAccess.UNREACHABLE, EnvAccess.ERROR],
    }
