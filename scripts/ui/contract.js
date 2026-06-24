/* TSMIS Reports Exporter -- frontend mirror of the bridge enum SSOT.
 *
 * The backend declares the worker<->GUI protocol vocabulary in scripts/contract.py
 * (P7a) and surfaces it via gui_api.get_initial_state().contract
 * (contract.initial_state_enums). This file is the FRONTEND mirror of that surface:
 * one place the UI + the #mock preview can name the task kinds, the terminal worker
 * messages, and the per-environment access verdicts instead of re-hardcoding the
 * strings. Classic <script>, loaded before app.js; exposed as `window.CONTRACT`.
 *
 * build/check_ui_contract.py LOCKS this to contract.initial_state_enums() (and the
 * report lists to report_catalog), so the frontend can't silently drift from the
 * backend SSOT. Keep the values in sync with contract.py -- the check is the guard.
 */
window.CONTRACT = {
  // The single-task-gate task kinds (contract.Task), sorted -- mirrors
  // initial_state_enums().tasks.
  tasks: ["batch", "chromium", "compare", "consolidate", "envcheck",
          "envscan", "export", "login", "matrix", "reset"],
  // The worker messages that END a task (contract.TERMINAL), sorted.
  terminal_kinds: ["batch_done", "cancelled", "chromium_done", "consolidate_done",
                   "env_access_done", "env_shot", "error", "export_done",
                   "login_device_ok", "login_failed", "login_saved", "matrix_done",
                   "matrix_export_done", "reset_done"],
  // Per-environment access verdicts (contract.EnvAccess), in the backend's
  // declared order.
  env_access: ["ok", "unverified", "reports_off", "no_reports", "denied",
               "no_signin", "wrong_site", "unreachable", "error"],
};
