TSMIS Reports Exporter
======================

HOW TO RUN
  Double-click  "TSMIS Exporter.exe"  in this folder.
  Keep this whole folder together -- the app needs the "_internal" folder next
  to the .exe. Don't move the .exe out on its own.

FIRST TIME (or whenever it shows "No saved login")
  1. Click  "Log in"  near the top.
  2. A browser window opens -- sign in with your @dot.ca.gov account and
     complete MFA.
  3. Come back to the app and click  "I've finished logging in".
  The dot turns green when you're signed in. You only need to do this again
  when the session expires.

EXPORT REPORTS
  On the Export tab, pick a report and click  "Start export".
  Files are saved in the  "output"  folder (use the buttons at the bottom to
  open it). "Save run report..." saves a CSV of how each route turned out.

COMBINE FILES
  The Consolidate tab combines the per-route files into one workbook, saved in
  "output\consolidated".

GOOD TO KNOW
  * The first time you run it, Windows may say the publisher is unknown. That's
    expected for an in-house tool: choose "More info" -> "Run anyway".
  * If you received this as a .zip, right-click the zip -> Properties -> tick
    "Unblock" -> OK, BEFORE extracting it.
  * Logs are under  "data\logs"  (or click "Logs" in the app). Include them if
    you report a problem.
