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
# Le contrôle doit passer par LaunchServices : exécuté depuis le shell, il répondrait
# sur le terminal — le processus responsable — et non sur le bundle qu'on vient de
# signer. La recompilation vient d'invalider l'autorisation : l'empreinte a changé.
echo "   ⚠️  L'autorisation d'accessibilité est à réaccorder : retirer la ligne"
echo "      $NAME.app de Réglages Système → Confidentialité et sécurité →"
echo "      Accessibilité avec « − », puis l'y glisser à nouveau."
echo "   Vérifier ensuite :"
echo "      open -n -a \"\$(pwd)/$APP\" --args --check --verdict /tmp/verdict"
echo "      sleep 1 && cat /tmp/verdict"
