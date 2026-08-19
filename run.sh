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
# La sortie dérive de dossiers qu'Apple garde en accès exclusif : préférences, barres
# de menus. En laisser le produit lisible par les autres comptes de la machine
# annulerait cette protection. Le dossier suffit : ce qu'il contient devient
# inatteignable pour qui ne peut pas le traverser.
chmod go-rwx out 2>/dev/null || true

HARVESTER=bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester
[ -x "$HARVESTER" ] || { echo "Binaire absent — lance d'abord ./build.sh"; exit 1; }

# L'autorisation n'est exigée que pour lire une barre de menu. Recenser les apps,
# exporter la disposition clavier et reconstruire la page n'en ont pas besoin — et
# refuser de le faire rendrait la page impossible à régénérer après une recompilation,
# qui invalide justement l'autorisation.
AUTORISE=oui
"$HARVESTER" --check >/dev/null 2>&1 || AUTORISE=non

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
  # Sauf celles dont la version a changé ET qui sont déjà ouvertes : les relire ne
  # coûte rien et ne fait surgir aucune fenêtre. Une app fermée garde sa fiche
  # jusqu'à ce qu'elle soit cochée dans la page — ouvrir les apps reste un geste
  # que l'utilisateur demande, jamais un effet de bord.
  PERIMEES=$(python3 src/perimees.py "$APPS_DIR" || true)
  if [ -n "$PERIMEES" ] && [ "$AUTORISE" = oui ]; then
    echo "→ Fiches périmées relues, sans ouvrir d'application"
    "$HARVESTER" --bundle-ids "$PERIMEES" --force --only-running --out "$APPS_DIR" || true
  elif [ -n "$PERIMEES" ]; then
    echo "→ Fiches périmées : relecture impossible sans l'autorisation d'accessibilité"
  fi
else
  if [ "$AUTORISE" != oui ]; then
    "$HARVESTER" --check    # affiche le mode d'emploi complet, puis s'arrête
  fi
  echo "→ Raccourcis par application"
  "$HARVESTER" "${TARGET[@]}" --out "$APPS_DIR" "${@:2}"
fi

echo "→ Index unifié (système + apps + outils tiers)"
python3 src/index.py "$APPS_DIR" "$INDEX"

echo "→ Restitution"
python3 src/report.py "$APPS_DIR" "$REPORT"
python3 src/page.py "$INDEX" "$PAGE"

# Une erreur de syntaxe dans le JavaScript rend la page ENTIÈREMENT inerte : titres,
# onglets, tableaux et libellés sont tous écrits par le script. Python produit le
# fichier sans jamais le relire, et la génération réussit quand même — la page part
# alors cassée en silence. Ce contrôle est le seul qui s'en aperçoive.
if command -v node >/dev/null 2>&1; then
  JSDIR=$(mktemp -d)
  JS="$JSDIR/page.js"
  python3 -c 'import sys
from pathlib import Path
h = Path(sys.argv[1]).read_text(encoding="utf-8")
Path(sys.argv[2]).write_text(h[h.rindex("<script>") + 8:h.rindex("</script>")],
                             encoding="utf-8")' "$PAGE" "$JS"
  if ! node --check "$JS"; then
    rm -rf "$JSDIR"
    echo "⛔️ JavaScript invalide : la page serait inerte. Rien n'est publiable en l'état."
    exit 1
  fi
  rm -rf "$JSDIR"
else
  echo "   ℹ️  node absent : syntaxe du JavaScript non vérifiée"
fi
# Rappel de fin de passe, affiché seulement quand il sert à quelque chose.
#
# Ouvrir et fermer les applications ne demande aucune autorisation ; lire leurs menus
# si. Or le binaire est exécuté directement depuis le shell, et macOS attribue alors
# le droit d'accessibilité au **processus responsable** — le terminal — plutôt qu'au
# bundle. Une passe complète suppose donc en général d'avoir autorisé son terminal,
# ce qui étend le droit à tout ce qu'il exécutera ensuite.
#
# Pour savoir si c'est le cas, on relance le contrôle via LaunchServices : lancé par
# `open`, le bundle est son propre processus responsable. S'il se déclare autorisé,
# l'autorisation lui appartient et il n'y a rien à retirer — le rappel se tait.
if [ ${#TARGET[@]} -ne 0 ]; then
  VERDICT_DIR=$(mktemp -d); VERDICT="$VERDICT_DIR/verdict"
  open -W -a "$(pwd)/bin/ShortcutHarvester.app"        --args --check --verdict "$VERDICT" >/dev/null 2>&1 || true
  if [ "$(cat "$VERDICT" 2>/dev/null)" != "accordee" ]; then
    echo
    echo "⚠️  Autorisation d'accessibilité — à retirer si elle était temporaire"
    echo "   Les menus ont été lus grâce à l'autorisation de ce terminal, pas à celle"
    echo "   du moissonneur. Tant qu'elle reste accordée, TOUT ce que ce terminal"
    echo "   exécute peut lire et piloter n'importe quelle application."
    echo "   Réglages Système → Confidentialité et sécurité → Accessibilité"
  fi
  rm -rf "$VERDICT_DIR"
fi

echo
echo "🌐 file://$(pwd)/$PAGE"
echo "📄 $(pwd)/$REPORT"
