#!/bin/bash
# Compile le moissonneur en app autonome.
#
# Pourquoi une app et pas un simple binaire : macOS rattache l'autorisation
# d'accessibilité à une identité de code. Un bundle .app signé est reconnu de façon
# stable par Réglages Système, et l'autorisation ne concerne que lui — pas le terminal.
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

# Signature ad hoc : donne au bundle une identité de code stable pour cette version.
# Toute recompilation change cette identité — il faudra alors retirer puis remettre
# l'app dans la liste Accessibilité.
codesign --force --sign - "$APP" 2>&1 | sed 's/^/  /'

echo "✅ $APP"
echo "   Vérifier l'autorisation : $APP/Contents/MacOS/$NAME --check"
