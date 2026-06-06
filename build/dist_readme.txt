TSMIS Reports Exporter
======================

WHAT IT DOES
  Bulk-downloads TSMIS reports for every California state route, then (optionally)
  combines the per-route files into one workbook. Reports supported:
    - TSAR: Ramp Summary        (PDF)
    - TSAR: Ramp Detail         (Excel)
    - Highway Sequence Listing  (Excel)
    - Highway Log               (Excel)

HOW TO RUN
  Double-click  "TSMIS Exporter.exe"  in this folder.
  Keep this whole folder together -- the app needs the "_internal" folder next
  to the .exe. Don't move the .exe out on its own.
  It uses the Microsoft Edge (or Chrome) already installed on this PC. Nothing
  to download; you don't need Python.

FIRST TIME (or whenever it shows "No saved login")
  1. Click  "Log in"  near the top.
  2. A browser window opens -- sign in with your @dot.ca.gov account and
     complete MFA, until the TSMIS report page loads.
  3. Either click  "I've finished logging in"  or just close the browser window
     -- your session is saved either way.
  The dot turns green when you're signed in. You only redo this when it expires.

EXPORT REPORTS
  On the Export tab:
    - Tick ONE OR MORE reports (they run one after another).
    - Routes: leave blank for ALL routes, or type a few (e.g. 5, 99, 101) or use
      "Choose...".
    - Click  "Start export".
  Files are saved in the  "output"  folder (buttons at the bottom open it).
  Already-downloaded routes are skipped, so you can stop and re-run to resume.
  "Save run report..." saves a CSV of how each route turned out.

  Skip / Cancel:
    - "Skip route" moves past one slow route.
    - "Cancel" stops the current export right away.

  Fast mode (optional): runs several browsers at once -- faster, but heavier on
  this PC. 3-4 is a good number. (Per-route Skip is off in fast mode; use Cancel.)

COMBINE FILES
  The Consolidate tab combines the per-route files into one workbook, saved in
  "output\consolidated".

GOOD TO KNOW
  * A route can occasionally fail with a "TSMIS site error" (e.g. "Cannot read
    properties of undefined"). That's a problem on the TSMIS website for that
    route's data, not this tool -- it's recorded as Failed and the run continues.
  * The first time you run it, Windows may say the publisher is unknown. That's
    expected for an in-house, unsigned tool: choose "More info" -> "Run anyway".
    (Code-signing the .exe is the permanent fix; ask the maintainer.)
  * If you received this as a .zip, right-click the zip -> Properties -> tick
    "Unblock" -> OK, BEFORE extracting it. This also helps with IT/Defender.
  * Browser: the header lets you pick Edge or Chrome and shows green/red dots for
    what's ready. "Re-check" re-runs those checks.
  * Logs are under  "data\logs"  (or click "Logs" in the app). Include them if
    you report a problem.
