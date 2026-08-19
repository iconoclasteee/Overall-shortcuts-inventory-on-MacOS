#!/bin/bash
# Builds the harvester as a stand-alone app.
#
# Why an app rather than a plain binary: macOS ties accessibility permission to a code
# identity. A signed .app bundle is recognised stably by System Settings, and the grant
# covers it alone — not the terminal.
set -euo pipefail
cd "$(dirname "$0")"

NAME=ShortcutHarvester
APP="bin/$NAME.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>$NAME</string>
    <key>CFBundleIdentifier</key><string>local.shortcuts-inventory.harvester</string>
    <key>CFBundleName</key><string>$NAME</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>LSUIElement</key><true/>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
</dict>
</plist>
PLIST

swiftc -O -o "$APP/Contents/MacOS/$NAME" src/Harvester.swift \
    -framework AppKit -framework ApplicationServices

# Ad-hoc signature: gives the bundle a code identity that is stable for this build.
# Any rebuild changes that identity — the app must then be removed from, and re-added
# to, the Accessibility list.
codesign --force --sign - "$APP" 2>&1 | sed 's/^/  /'

echo "✅ $APP"
# The check must go through LaunchServices: run from the shell, it would answer about
# the terminal — the responsible process — rather than about the bundle just signed.
# The rebuild has invalidated the grant: the fingerprint changed.
echo "   ⚠️  L'autorisation d'accessibilité est à réaccorder : retirer la ligne"
echo "      $NAME.app de Réglages Système → Confidentialité et sécurité →"
echo "      Accessibilité avec « − », puis l'y glisser à nouveau."
echo "   Vérifier ensuite :"
# The file is deleted first, then waited for: left in place, it would return the verdict
# of the previous run — "accordee" when the build just performed has invalidated the
# right. Exactly the false positive to avoid.
echo "      rm -f /tmp/verdict"
echo "      open -n -a \"\$(pwd)/$APP\" --args --check --verdict /tmp/verdict"
echo "      until [ -f /tmp/verdict ]; do sleep 0.2; done; cat /tmp/verdict"
