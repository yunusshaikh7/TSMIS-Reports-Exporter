"""TSMIS Exporter -- the ArcGIS layer export worker.

This file runs INSIDE ArcGIS Pro's own Python (the `arcgispro-py3` environment),
never inside the app: the app cannot carry ArcPy, so it launches this script
with ArcGIS Pro's python.exe (see `arcgis_pro.py`), hands it a request JSON and
reads the events it appends, one JSON object per line, to an events file. The
app does everything else -- checking each exported file, swapping it into the
layer library and rewriting the 00_INDEX.xlsx manifest (`arcgis_refresh.py`).

Each layer is read straight from the TSMIS feature service by URL and written
with ArcGIS's own Table To Excel tool: field NAMES as the header row and coded
domains written as their DESCRIPTIONS ("District 12", "Orange", "Right"), the
dialect of the manual per-layer exports the clean-road builds were verified on.
ArcGIS Pro's sign-in supplies the credentials, the same way the vendor's own
Pro tools reach these services (`arcpy.GetSigninToken`). The service's layer
list is read once, with that token, so every layer is matched by NAME; the ids
in the request are only the fallback.

Two modes:
  * probe  -- start ArcPy, report the ArcGIS Pro version + sign-in, read one
              small layer and export it to a scratch file (a quick end-to-end
              check of everything a refresh needs);
  * export -- export every requested layer to its own .xlsx.

Keep this file standard library + ArcPy only and compatible with Python 3.9
(ArcGIS Pro 3.0 ships 3.9; Pro 3.3 ships 3.11). Never write the sign-in token to
an event, a message or a file.
"""
import argparse
import json
import os
import re
import sys
import threading
import time
import traceback

PROTOCOL = 1
# An Excel sheet holds 1,048,576 rows; one is the header.
EXCEL_MAX_DATA_ROWS = 1048575
HEARTBEAT_SECONDS = 10
# Stop early when the service keeps refusing: the same failure on every layer
# (signed out, server down) would otherwise repeat forty times.
MAX_FAILURES_IN_A_ROW = 3

_TOKEN_RE = re.compile(r"(token=)[^&\s'\"]+", re.IGNORECASE)


def _redact(text):
    return _TOKEN_RE.sub(r"\1<redacted>", str(text))


def _norm(name):
    """A layer name reduced to lowercase letters and digits, so 'SHS Tolls',
    'SHS_Tolls' and 'shs tolls' all match."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def _traceback():
    return _redact(traceback.format_exc())[-4000:]


class Emitter:
    """Append one JSON event per line and flush it, so the app can follow the
    file while this process runs. Thread-safe (the heartbeat writes too)."""

    def __init__(self, path):
        self._lock = threading.Lock()
        self._f = open(path, "a", encoding="utf-8", newline="\n")

    def __call__(self, kind, **fields):
        record = {"type": kind, "t": round(time.time(), 3)}
        record.update(fields)
        line = json.dumps(record, ensure_ascii=True, default=str)
        with self._lock:
            self._f.write(line + "\n")
            self._f.flush()

    def close(self):
        with self._lock:
            self._f.close()


class _Heartbeat(threading.Thread):
    """An 'alive' event every few seconds while the worker runs, so the app can
    tell a long single-layer export from a dead process."""

    def __init__(self, emit, every=HEARTBEAT_SECONDS):
        super().__init__(name="arcgis-worker-heartbeat", daemon=True)
        self._emit = emit
        self._every = every
        self._halt = threading.Event()

    def run(self):
        while not self._halt.wait(self._every):
            try:
                self._emit("alive")
            except Exception:   # the events file closed under us: the run is over
                return

    def stop(self):
        self._halt.set()


def _runtime_facts(arcpy):
    """The ArcGIS Pro facts a failure report needs. Never the token itself."""
    facts = {}
    try:
        info = arcpy.GetInstallInfo() or {}
        facts["arcgis_version"] = info.get("Version")
        facts["product"] = info.get("ProductName")
    except Exception as e:
        facts["install_error"] = _redact(e)
    try:
        facts["license"] = arcpy.ProductInfo()
    except Exception as e:
        facts["license_error"] = _redact(e)
    try:
        facts["portal"] = arcpy.GetActivePortalURL()
    except Exception as e:
        facts["portal_error"] = _redact(e)
    try:
        token = arcpy.GetSigninToken() or {}
        facts["signed_in"] = bool(token.get("token"))
    except Exception as e:
        facts["signed_in"] = False
        facts["signin_error"] = _redact(e)
    return facts


def _service_catalog(arcpy, service, emit):
    """{normalized layer name: (id, service name)} for the feature service's
    layers and tables, read from its REST description with ArcGIS Pro's sign-in
    token, or None when it cannot be read (the request's ids are used then).
    POSTed so the token never appears in a URL."""
    import urllib.parse
    import urllib.request

    try:
        token = arcpy.GetSigninToken() or {}
    except Exception:
        token = {}
    if not token.get("token"):
        emit("catalog", ok=False,
             error="ArcGIS Pro is not signed in to its active portal")
        return None
    body = urllib.parse.urlencode({"f": "json", "token": token["token"]}).encode()
    request = urllib.request.Request(
        service.rstrip("/"), data=body, method="POST",
        headers={"Referer": token.get("referer") or "",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "TSMIS-Exporter-layer-export"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        emit("catalog", ok=False, error=_redact("%s: %s" % (type(e).__name__, e)))
        return None
    if not isinstance(data, dict) or data.get("error"):
        err = data.get("error") if isinstance(data, dict) else data
        emit("catalog", ok=False, error=_redact(err))
        return None
    entries = {}
    for kind in ("layers", "tables"):
        for item in data.get(kind) or []:
            try:
                entries.setdefault(_norm(item.get("name")),
                                   (int(item["id"]), str(item.get("name"))))
            except (KeyError, TypeError, ValueError):
                continue
    emit("catalog", ok=True, count=len(entries))
    return entries


def _resolve(layer, catalog):
    """(layer id, the service's own name for it, error). With the catalog the
    layer is matched by NAME; without it the request's id stands."""
    if catalog is None:
        return int(layer["id"]), None, None
    hit = catalog.get(_norm(layer["name"]))
    if hit is None:
        return None, None, ("The service has no layer named %r -- its layer "
                            "list changed, so the app needs an update."
                            % layer["name"])
    return hit[0], hit[1], None


def _described_name(arcpy, view):
    try:
        d = arcpy.Describe(view)
        return str(getattr(d, "name", "") or getattr(d, "baseName", "") or "")
    except Exception:
        return ""


def _arcpy_message(arcpy, e):
    """The tool's own error lines when ArcGIS raised them, else the exception."""
    text = ""
    try:
        if isinstance(e, arcpy.ExecuteError):
            text = arcpy.GetMessages(2)
    except Exception:
        text = ""
    return _redact((text or "%s: %s" % (type(e).__name__, e)).strip())


def _export_one(arcpy, service, layer, index, total, emit):
    """Export one layer. Returns True on success; emits layer_done or
    layer_failed either way (never raises)."""
    name = layer["name"]
    out = layer["out"]
    started = time.time()
    emit("layer_start", name=name, index=index, total=total)
    view = None
    try:
        layer_id, service_name, error = _resolve(layer, layer.get("_catalog"))
        if error:
            emit("layer_failed", name=name, message=error)
            return False
        url = "%s/%d" % (service.rstrip("/"), layer_id)
        view = name
        arcpy.management.MakeTableView(url, view)
        if service_name is None:
            described = _described_name(arcpy, view)
            if described and _norm(name) not in _norm(described) \
                    and _norm(described) not in _norm(name):
                emit("layer_warning", name=name,
                     message="the service calls layer %d %r" % (layer_id, described))
        rows = int(arcpy.management.GetCount(view)[0])
        emit("layer_count", name=name, rows=rows)
        if rows > EXCEL_MAX_DATA_ROWS:
            emit("layer_failed", name=name, rows=rows,
                 message=("%s has %s rows -- more than one Excel sheet holds "
                          "(%s)." % (name, format(rows, ","),
                                     format(EXCEL_MAX_DATA_ROWS, ","))))
            return False
        if os.path.exists(out):
            os.remove(out)
        arcpy.conversion.TableToExcel(view, out, "NAME", "DESCRIPTION")
        if not os.path.isfile(out):
            emit("layer_failed", name=name,
                 message="Table To Excel finished but wrote no file.")
            return False
        emit("layer_done", name=name, id=layer_id, service_name=service_name,
             url=url, rows=rows, size=os.path.getsize(out), file=out,
             started=round(started, 3), seconds=round(time.time() - started, 1))
        return True
    except Exception as e:
        emit("layer_failed", name=name, message=_arcpy_message(arcpy, e),
             detail=_traceback())
        return False
    finally:
        if view is not None:
            try:
                arcpy.management.Delete(view)
            except Exception:
                pass


def _export(arcpy, request, catalog, emit):
    service = request["service"]
    layers = list(request.get("layers") or [])
    exported = failed = in_a_row = 0
    last_failure = ""
    for i, layer in enumerate(layers, start=1):
        layer = dict(layer, _catalog=catalog)
        if _export_one(arcpy, service, layer, i, len(layers), emit):
            exported += 1
            in_a_row = 0
        else:
            failed += 1
            in_a_row += 1
            last_failure = layer["name"]
            if in_a_row >= MAX_FAILURES_IN_A_ROW and i < len(layers):
                emit("fatal", stage="export",
                     message=("Stopped after %d layers failed in a row (the "
                              "last was %s) -- see each layer's message."
                              % (in_a_row, last_failure)))
                emit("done", ok=False, exported=exported, failed=failed,
                     stopped_early=True)
                return 2
    emit("done", ok=failed == 0, exported=exported, failed=failed)
    return 0 if failed == 0 else 2


def _probe(arcpy, request, catalog, emit):
    """Read one small layer and export it, end to end."""
    layer = dict(request["probe_layer"], _catalog=catalog)
    ok = _export_one(arcpy, request["service"], layer, 1, 1, emit)
    emit("done", ok=ok, exported=1 if ok else 0, failed=0 if ok else 1)
    return 0 if ok else 2


def run(request, emit, arcpy=None):
    """Run one request. `emit(kind, **fields)` records an event. `arcpy` is
    injected only by the app's self-test (a stand-in for the real module);
    a real run imports ArcGIS Pro's own. Returns the process exit code."""
    emit("begin", protocol=PROTOCOL, mode=request.get("mode"),
         python=sys.version.split()[0], pid=os.getpid())
    if request.get("protocol") != PROTOCOL:
        emit("fatal", stage="request",
             message="This worker speaks protocol %d; the request is %r."
                     % (PROTOCOL, request.get("protocol")))
        return 5
    beat = _Heartbeat(emit)
    beat.start()
    try:
        if arcpy is None:
            emit("progress", message="Starting ArcGIS Pro's Python (ArcPy)...")
            began = time.time()
            try:
                import arcpy as _arcpy
            except Exception as e:
                emit("fatal", stage="import",
                     message=("ArcPy could not start: %s -- open ArcGIS Pro once, "
                              "sign in (tick 'Sign me in automatically'), then "
                              "retry." % _redact(e)),
                     detail=_traceback())
                return 3
            arcpy = _arcpy
            emit("progress", message="ArcPy ready in %.0f s" % (time.time() - began))
        arcpy.env.overwriteOutput = True
        emit("runtime", **_runtime_facts(arcpy))
        catalog = _service_catalog(arcpy, request["service"], emit)
        if request.get("mode") == "probe":
            return _probe(arcpy, request, catalog, emit)
        return _export(arcpy, request, catalog, emit)
    except Exception as e:
        emit("fatal", stage="run", message=_redact("%s: %s" % (type(e).__name__, e)),
             detail=_traceback())
        return 4
    finally:
        beat.stop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--request", required=True)
    parser.add_argument("--events", required=True)
    args = parser.parse_args(argv)
    emit = Emitter(args.events)
    try:
        with open(args.request, encoding="utf-8") as f:
            request = json.load(f)
        return run(request, emit)
    except Exception as e:
        emit("fatal", stage="start", message=_redact("%s: %s" % (type(e).__name__, e)),
             detail=_traceback())
        return 4
    finally:
        emit.close()


if __name__ == "__main__":
    sys.exit(main())
