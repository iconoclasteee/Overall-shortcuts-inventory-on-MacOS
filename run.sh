#!/bin/bash
# Génère l'inventaire des raccourcis clavier.
#
#   ./run.sh --test     6 apps représentatives, pour valider la mécanique
#   ./run.sh --all      toutes les apps installées
#   ./run.sh --sources  relit les raccourcis système et les outils globaux, sans
#                       ouvrir la moindre application — quelques secondes
#
# La passe est reprenable : chaque app est écrite dans son propre fichier JSON et
# une relance saute ce qui est déjà là. Interrompre avec Ctrl-C ne perd rien.
set -euo pipefail
cd "$(dirname "$0")"

# out/ n'est pas versionné : sur un clone frais il n'existe pas, et la première
# redirection échouerait avant même le premier message.
mkdir -p out

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
  --all)  APPS_DIR=out/apps;      REPORT=out/raccourcis.md
          INDEX=out/index.json;    PAGE=out/raccourcis.html
          TARGET=(--all) ;;
  --sources) APPS_DIR=out/apps; REPORT=out/raccourcis.md
          INDEX=out/index.json;  PAGE=out/raccourcis.html
          TARGET=() ;;
  *) echo "Usage: $0 [--test|--all|--sources]"; exit 2 ;;
esac

echo "→ Disposition clavier"
"$HARVESTER" --keymap > out/keymap.json

echo "→ Recensement des apps installées"
"$HARVESTER" --catalogue > out/catalogue.json

echo "→ Raccourcis système"
python3 src/system_shortcuts.py

if [ ${#TARGET[@]} -eq 0 ]; then
  # Mode --sources : les raccourcis d'application déjà lus sont conservés tels quels.
  echo "→ Raccourcis par application : conservés ($(ls "$APPS_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ') fiches)"
else
  echo "→ Raccourcis par application"
  "$HARVESTER" "${TARGET[@]}" --out "$APPS_DIR" "${@:2}"
fi

echo "→ Index unifié (système + apps + outils tiers)"
python3 src/index.py "$APPS_DIR" "$INDEX"

echo "→ Restitution"
python3 src/report.py "$APPS_DIR" "$REPORT"
python3 src/page.py "$INDEX" "$PAGE"
echo
echo "🌐 file://$(pwd)/$PAGE"
echo "📄 $(pwd)/$REPORT"
