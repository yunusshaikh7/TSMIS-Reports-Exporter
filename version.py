"""Single source of truth for app identity and pinned build versions.

Imported by the build tooling (and later the GUI About box). Keep this file
dependency-free so it can be imported from anywhere, including the .spec.
"""

__version__ = "0.4.0"          # semantic version MAJOR.MINOR.PATCH
APP_NAME = "TSMIS Exporter"    # onefolder / executable name

# Playwright pins the bundled Node DRIVER (node.exe). The app does NOT bundle a
# browser -- it drives the machine's installed Microsoft Edge / Google Chrome via
# channel="msedge"/"chrome" (Playwright's CDP works across evergreen Edge/Chrome),
# so there is no Chromium revision to keep in lockstep. Bumping Playwright only
# changes the bundled driver.
PLAYWRIGHT_VERSION = "1.60.0"
