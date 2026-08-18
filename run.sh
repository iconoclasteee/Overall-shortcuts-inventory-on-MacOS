#!/bin/bash
# Génère l'inventaire des raccourcis clavier.
#
#   ./run.sh --test   6 apps représentatives, pour valider la mécanique
#   ./run.sh --all    les 211 apps installées
#
# La passe est reprenable : chaque app est écrite dans son propre fichier JSON et
# une relance saute ce qui est déjà là. Interrompre avec Ctrl-C ne perd rien.
set -euo pipefail
cd "$(dirname "$0")"

HARVESTER=bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester
[ -x "$HARVESTER" ] || { echo "Binaire absent — lance d'abord ./build.sh"; exit 1; }
"$HARVESTER" --check

# Jeu de test : chaque app couvre un mode de défaillance différent.
#   Finder      app toujours lancée, menus riches
#   TextEdit    app à documents, lue sans document ouvert
#   Safari      menus natifs profonds
#   cmux        app Electron, menus construits en JavaScript
#   Alfred      app agent sans barre de menu classique
#   PowerPoint  app lourde + raccourcis redéfinis par l'utilisateur
TEST_APPS=com.apple.finder,com.apple.TextEdit,com.apple.Safari,com.cmuxterm.app,com.runningwithcrayons.Alfred,com.microsoft.Powerpoint

case "${1:---test}" in
  --test) APPS_DIR=out/apps-test; REPORT=out/raccourcis-test.md
          INDEX=out/index-test.json; PAGE=out/raccourcis-test.html
          TARGET=(--bundle-ids "$TEST_APPS") ;;
  --all)  APPS_DIR=out/apps;      REPORT=out/raccourcis-macos.md
          INDEX=out/index.json;    PAGE=out/raccourcis.html
          TARGET=(--all) ;;
  *) echo "Usage: $0 [--test|--all]"; exit 2 ;;
esac

echo "→ Disposition clavier"
"$HARVESTER" --keymap > data/keymap.json

echo "→ Raccourcis système"
python3 src/system_shortcuts.py

echo "→ Raccourcis par application"
"$HARVESTER" "${TARGET[@]}" --out "$APPS_DIR" "${@:2}"

echo "→ Index unifié (système + apps + Alfred, Keyboard Maestro, CleanShot X)"
python3 src/index.py "$APPS_DIR" "$INDEX"

echo "→ Restitution"
python3 src/report.py "$APPS_DIR" "$REPORT"
python3 src/html.py "$INDEX" "$PAGE"
echo
echo "🌐 file://$(pwd)/$PAGE"
echo "📄 $(pwd)/$REPORT"
