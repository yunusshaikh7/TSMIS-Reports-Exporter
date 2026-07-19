"""The single owner of GUI task state (P7a / R1-R06 / D03).

`GuiApi` runs ONE task at a time behind a single-flight gate, with a small queue of
matrix jobs that auto-advance as the gate frees. Before P7a that state (`_task`, the
running job, the queue, the job-id counter) and its claim/release/advance logic were
inlined across `gui_api.py`; this module is the one place that owns them, so the
gate's invariants live together and the lifecycle is testable in isolation.

`GuiApi` keeps a single `TaskCoordinator`, shares its own re-entrant-free `_lock`
(the coordinator guards every state mutation under it, the same lock GuiApi uses for
its other snapshot state), and exposes `_task` / `_current_job` / `_queue` /
`_job_seq` as thin proxies so the rest of `gui_api` reads them unchanged. The
exactly-once terminal guarantee (a late/duplicate terminal can't clobber a successor
that already started) is enforced where terminals are dispatched — see
`GuiApi._handle` — by a per-claim EPOCH: every claim (`try_claim` / `claim_direct` /
`take_next`) bumps a monotonic counter that identifies that exact task instance, the
worker started for the claim tags its terminal with it, and `is_live()` drops a
terminal tagged with anything but the live claim's epoch. A kind-only guard could
not tell a stale terminal apart from a same-kind (or wildcard `error`/`cancelled`)
successor (P7a-B01).

Console-free, dependency-free (stdlib only). No upward import (never imports
`gui_api`); `GuiApi` imports this.
"""
from collections import deque


class TaskCoordinator:
    """Owns the single-task gate, the running matrix job, the matrix job queue, and
    the monotonic job-id counter. Every mutation is guarded by the shared lock."""

    def __init__(self, lock, queue_limit):
        self._lock = lock                 # SHARED with GuiApi (its self._lock)
        self._queue_limit = queue_limit
        self.task = None                  # str|None — the single-flight gate (a Task.*)
        self.current_job = None           # dict|None — the running matrix job
        self.queue = deque()              # pending matrix jobs (FIFO)
        self._job_seq = 0                 # monotonic job-id source
        self._epoch = 0                   # monotonic claim id — the live task instance's identity

    # ---- gate ---------------------------------------------------------------
    def try_claim(self, name):
        """Atomically claim the single slot: True if claimed, False if a task is
        already running. (Claim+set in one critical section so two fast clicks can't
        both pass the gate.) A successful claim bumps the epoch — the new task
        instance's identity — so its worker's terminal can be told apart from a
        straggler of the just-finished one."""
        with self._lock:
            if self.task:
                return False
            self.task = name
            self._epoch += 1
            return True

    def claim_direct(self, name):
        """Claim the gate for a caller that has ALREADY verified it is free under the
        shared lock (the login/envcheck/envscan/chromium endpoints, which set extra
        state in the same critical section). Bumps the epoch exactly like `try_claim`
        so every claim path — not just `try_claim`/`take_next` — gives its worker a
        fresh task-instance identity. (Re-enters the shared RLock; safe to call inside
        the caller's `with self._lock`.)"""
        with self._lock:
            self.task = name
            self._epoch += 1

    def release(self):
        """Free the gate + drop the running job (the unconditional clear the terminal
        path uses once it has decided the terminal is the live one)."""
        with self._lock:
            self.task = None
            self.current_job = None

    def current_epoch(self):
        """The live claim's epoch — captured when a worker is started (the gate is
        held, so it is this claim's identity) and stamped onto the worker's terminal."""
        with self._lock:
            return self._epoch

    def is_live(self, epoch):
        """The exactly-once guard. True iff a terminal tagged with `epoch` belongs to
        the claim CURRENTLY holding the gate, so it may free it. A terminal tagged with
        a prior claim's epoch is a straggler (its task ended; a successor may now hold
        the gate, even one of the same kind, or a wildcard `error`/`cancelled`) and is
        dropped — kind alone can't tell those apart (P7a-B01). `epoch=None` means an
        UNTAGGED terminal (a direct test/legacy caller, never a production worker, which
        always tags via the gated queue): treat it as the current claim's — i.e. honored
        iff a task is running — preserving pre-epoch behavior for such callers."""
        with self._lock:
            if self.task is None:
                return False                  # gate idle: every terminal is late
            return epoch is None or epoch == self._epoch

    def is_busy(self):
        with self._lock:
            return self.task is not None or self.current_job is not None

    # ---- matrix job queue ---------------------------------------------------
    def next_seq(self):
        """The next monotonic job id."""
        with self._lock:
            self._job_seq += 1
            return self._job_seq

    def enqueue(self, job):
        """Append a job. Returns (depth, was_busy), or None if the queue is full."""
        with self._lock:
            if len(self.queue) >= self._queue_limit:
                return None
            self.queue.append(job)
            busy = self.task is not None or self.current_job is not None
            return len(self.queue), busy

    def depth(self):
        with self._lock:
            return len(self.queue)

    def drop_matching(self, predicate):
        """Remove queued jobs for which ``predicate(job)`` is True, keeping the rest in
        FIFO order; return ``(removed, retained)``. The auth/browser error handler uses
        this to drop ONLY the jobs that need the failed prerequisite (exports), so local
        comparison/evidence jobs on the SHARED queue survive (CMP-AUD-088). A predicate
        that raises is treated as non-matching (the job is kept — fail safe: never drop
        a job we cannot classify)."""
        with self._lock:
            def _drop(job):
                try:
                    return bool(predicate(job))
                except Exception:  # silent-ok: an unclassifiable job is KEPT (never dropped) — fail safe
                    return False
            kept = deque(job for job in self.queue if not _drop(job))
            removed = len(self.queue) - len(kept)
            self.queue = kept
            return removed, len(kept)

    def take_next(self):
        """If the gate is free and the queue is non-empty, ATOMICALLY pop the next
        job, claim the gate as 'matrix', set it as the running job, mark it running,
        and return it. Else None (gate busy or queue empty). The atomic pop+claim is
        what stops a non-matrix task slipping in between popping and claiming."""
        with self._lock:
            if self.task or self.current_job is not None or not self.queue:
                return None
            job = self.queue.popleft()
            self.task = "matrix"
            self.current_job = job
            job["status"] = "running"
            self._epoch += 1          # a fresh claim -> a fresh task-instance identity
            return job
