"""Single source of truth for app identity and pinned build versions.

Imported by the build tooling (and later the GUI About box). Keep this file
dependency-free so it can be imported from anywhere, including the .spec.
"""

__version__ = "0.26.0"         # semantic version MAJOR.MINOR.PATCH
APP_NAME = "TSMIS Exporter"    # onefolder / executable name

# Playwright pins the bundled Node DRIVER (node.exe). The default build does NOT
# bundle a browser -- it drives the machine's installed Microsoft Edge / Google
# Chrome via channel="msedge"/"chrome" (Playwright's CDP works across evergreen
# Edge/Chrome). The with-browser release variant (build.ps1 -BundleChromium) and
# the .bat setup additionally carry Playwright's own Chromium, whose revision IS
# tied to this driver version -- `playwright install chromium` always fetches the
# revision this pin expects, so they can't drift.
PLAYWRIGHT_VERSION = "1.60.0"
