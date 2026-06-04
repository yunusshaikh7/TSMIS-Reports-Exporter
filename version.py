"""Single source of truth for app identity and pinned build versions.

Imported by the build tooling (and later the GUI About box). Keep this file
dependency-free so it can be imported from anywhere, including the .spec.
"""

__version__ = "0.2.0"          # semantic version MAJOR.MINOR.PATCH
APP_NAME = "TSMIS Exporter"    # onefolder / executable name

# Playwright and its bundled Chromium move together: bumping one requires
# re-bundling the other. build\build.ps1 installs the matching browser.
PLAYWRIGHT_VERSION = "1.60.0"
CHROMIUM_REVISION = "1223"     # Chrome for Testing 148.0.7778.96
