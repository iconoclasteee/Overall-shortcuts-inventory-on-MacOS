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
# Le moissonneur est lancé par LaunchServices, qui ne lui transmet pas le répertoire
# courant : tous les chemins qu'on lui passe doivent être absolus.
RACINE=$(pwd)

# out/ n'est pas versionné : sur un clone frais il n'existe pas, et la première
# redirection échouerait avant même le premier message.
mkdir -p out
# La sortie dérive de dossiers qu'Apple garde en accès exclusif : préférences, barres
# de menus. En laisser le produit lisible par les autres comptes de la machine
# annulerait cette protection. Le dossier suffit : ce qu'il contient devient
# inatteignable pour qui ne peut pas le traverser.
chmod go-rwx out 2>/dev/null || true

BUNDLE="$RACINE/bin/ShortcutHarvester.app"
HARVESTER="$BUNDLE/Contents/MacOS/ShortcutHarvester"
[ -x "$HARVESTER" ] || { echo "Binaire absent — lancer d'abord ./build.sh"; exit 1; }

# Lance le moissonneur par LaunchServices plutôt que depuis ce shell.
#
# macOS n'accorde pas l'autorisation d'accessibilité au binaire exécuté, mais au
# **processus responsable** — celui qui l'a lancé. Exécuté directement ici, c'est le
# terminal : lire des menus supposerait alors d'autoriser le terminal, donc tout ce
# qu'il exécutera ensuite, aujourd'hui et plus tard. Lancé par `open`, le bundle est son
# propre responsable, et sa seule ligne dans la liste Accessibilité suffit.
#
# Le prix : `open` ne rend ni la sortie du programme ni son code d'erreur. D'où le
# journal, relayé ici en direct, et le fichier de statut, dont l'apparition est le seul
# signal de fin fiable.
moissonner() {
  local dossier journal statut pid code lu total
  dossier=$(mktemp -d); journal="$dossier/journal"; statut="$dossier/statut"
  : > "$journal"

  open -n -a "$BUNDLE" --args "$@" --journal "$journal" --statut "$statut"

  # Le PID exact, et non le nom du processus : deux passes lancées en parallèle se
  # confondraient, et l'interruption tuerait la mauvaise.
  pid=""
  for _ in $(seq 1 100); do
    pid=$(pgrep -n -x ShortcutHarvester 2>/dev/null || true)
    if [ -n "$pid" ] || [ -f "$statut" ]; then break; fi
    sleep 0.1
  done

  # Lancé par LaunchServices, le moissonneur ne descend pas de ce shell : Ctrl-C ne
  # l'atteindrait pas, et il continuerait d'ouvrir des applications tout seul.
  trap 'kill "$pid" 2>/dev/null || true; rm -rf "$dossier"; exit 130' INT TERM

  # Le journal est relu par tranches plutôt que suivi par `tail -f` : pas de tâche de
  # fond à tuer, pas de message du shell à la tuer, et les dernières lignes sont lues
  # à coup sûr — un `tail` interrompu peut les laisser derrière lui.
  lu=0
  relayer() {
    total=$(wc -l < "$journal" 2>/dev/null | tr -d ' ' || echo 0)
    if [ "${total:-0}" -gt "$lu" ]; then
      sed -n "$((lu + 1)),${total}p" "$journal"
      lu=$total
    fi
  }

  while :; do
    relayer
    if [ -f "$statut" ]; then break; fi
    if [ -z "$pid" ]; then code=127; break; fi
    if ! kill -0 "$pid" 2>/dev/null; then
      sleep 0.5                     # laisse le temps d'écrire le statut en sortant
      if [ ! -f "$statut" ]; then code=127; break; fi
    fi
    sleep 0.1
  done
  relayer

  trap - INT TERM
  code=${code:-$(cat "$statut" 2>/dev/null || echo 127)}
  rm -rf "$dossier"
  if [ "$code" = 127 ]; then
    echo "⛔️ Le moissonneur s'est interrompu sans rendre de statut."
  fi
  return "$code"
}

# L'autorisation qui compte est celle du bundle, puisque c'est lui qui sera lancé.
# La demander depuis ce shell interrogerait le terminal, qui n'a plus besoin de rien.
autorisation_bundle() {
  local dossier verdict reponse i
  dossier=$(mktemp -d); verdict="$dossier/verdict"
  open -n -a "$BUNDLE" --args --check --verdict "$verdict" 2>/dev/null || true
  i=0
  while [ ! -f "$verdict" ] && [ "$i" -lt 100 ]; do sleep 0.1; i=$((i + 1)); done
  reponse=$(cat "$verdict" 2>/dev/null || echo absente)
  rm -rf "$dossier"
  [ "$reponse" = accordee ]
}

# L'autorisation n'est exigée que pour lire une barre de menu. Recenser les apps,
# exporter la disposition clavier et reconstruire la page n'en ont pas besoin — et
# refuser de le faire rendrait la page impossible à régénérer après une recompilation,
# qui invalide justement l'autorisation.
AUTORISE=oui
autorisation_bundle || AUTORISE=non

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
          TARGET=(--bundle-ids "$TEST_APPS"); SUPPL=("${@:2}") ;;
  --all)  APPS_DIR=out/apps;      REPORT=out/raccourcis.md
          INDEX=out/index.json;    PAGE=out/raccourcis.html
          TARGET=(--all); SUPPL=("${@:2}") ;;
  --sources) APPS_DIR=out/apps; REPORT=out/raccourcis.md
          INDEX=out/index.json;  PAGE=out/raccourcis.html
          TARGET=(); SUPPL=("${@:2}") ;;
  # Liste explicite, telle que la page la produit. --force est indispensable : sans lui
  # le moissonneur saute toute app dont la fiche existe déjà, c'est-à-dire précisément
  # celles qu'on vient de cocher parce que leur version a changé.
  --apps) APPS_DIR=out/apps;      REPORT=out/raccourcis.md
          INDEX=out/index.json;    PAGE=out/raccourcis.html
          [ -n "${2:-}" ] || { echo "Usage: $0 --apps <id1,id2,…>"; exit 2; }
          TARGET=(--bundle-ids "$2" --force); SUPPL=("${@:3}") ;;
  *) echo "Usage: $0 [--test|--all|--sources|--apps <id1,id2,…>]"; exit 2 ;;
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
    moissonner --bundle-ids "$PERIMEES" --force --only-running \
               --out "$RACINE/$APPS_DIR" --reglages "$RACINE/out/reglages-scan.json" || true
  elif [ -n "$PERIMEES" ]; then
    echo "→ Fiches périmées : relecture impossible sans l'autorisation du moissonneur"
  fi
else
  if [ "$AUTORISE" != oui ]; then
    # Le verdict est déjà tombé plus haut, sur le bundle. Exécuter le moissonneur ici
    # ne sert qu'à afficher son mode d'emploi : lancé par `open`, il ne rendrait rien.
    "$HARVESTER" --check || true
    exit 1
  fi
  echo "→ Raccourcis par application"
  moissonner "${TARGET[@]}" --out "$RACINE/$APPS_DIR" \
             --reglages "$RACINE/out/reglages-scan.json" ${SUPPL[@]+"${SUPPL[@]}"}
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
# Le moissonneur étant lancé par LaunchServices, il est son propre processus responsable
# et se voit appliquer sa propre autorisation : plus aucun terminal n'a besoin du droit
# d'accessibilité pour que la passe fonctionne. S'il se trouve que ce shell le détient
# malgré tout, c'est un reste d'une passe antérieure — et tant qu'il reste accordé, tout
# ce que ce terminal exécutera peut lire et piloter n'importe quelle application.
if "$HARVESTER" --check >/dev/null 2>&1; then
  echo
  echo "⚠️  Ce terminal détient l'autorisation d'accessibilité, désormais inutile."
  echo "   Le moissonneur est lancé par LaunchServices et se voit appliquer la sienne."
  echo "   Tant qu'elle reste accordée ici, TOUT ce que ce terminal exécute peut lire"
  echo "   et piloter n'importe quelle application."
  echo "   À retirer : Réglages Système → Confidentialité et sécurité → Accessibilité"
fi

echo
echo "🌐 file://$(pwd)/$PAGE"
echo "📄 $(pwd)/$REPORT"
