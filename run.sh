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
  local dossier journal statut pid code lu total inactif
  dossier=$(mktemp -d); journal="$dossier/journal"; statut="$dossier/statut"
  : > "$journal"

  # Retrouve NOTRE moissonneur, et pas un autre.
  #
  # `pgrep` apparie par nom : deux passes lancées en parallèle se confondraient, et
  # l'interruption de l'une tuerait le moissonneur de l'autre. Le chemin du journal, lui,
  # sort de `mktemp` et n'appartient qu'à cet appel — il est dans la ligne de commande du
  # processus. On le croise avec le nom du programme, `open` portant le même argument
  # dans la sienne.
  trouver_pid() {
    local candidat
    for candidat in $(pgrep -f -- "$journal" 2>/dev/null || true); do
      case "$(ps -o comm= -p "$candidat" 2>/dev/null)" in
        */ShortcutHarvester) echo "$candidat"; return 0 ;;
      esac
    done
    return 1
  }

  # Le piège est posé avant toute attente. Lancé par LaunchServices, le moissonneur ne
  # descend pas de ce shell : Ctrl-C ne l'atteint pas, et une interruption survenue
  # pendant qu'on cherche son identifiant le laisserait ouvrir les applications tout
  # seul. Il le retrouve donc lui-même, au moment du signal.
  trap 'kill "$(trouver_pid)" 2>/dev/null || true; rm -rf "$dossier"; exit 130' INT TERM

  if ! open -n -a "$BUNDLE" --args "$@" --journal "$journal" --statut "$statut"; then
    trap - INT TERM; rm -rf "$dossier"
    echo "⛔️ LaunchServices n'a pas pu lancer le moissonneur."
    return 127
  fi

  # Le journal est relu par tranches plutôt que suivi par `tail -f` : pas de tâche de
  # fond à tuer, pas de message du shell à la tuer, et les dernières lignes sont lues
  # à coup sûr — un `tail` interrompu peut les laisser derrière lui.
  lu=0
  relayer() {
    total=$(wc -l < "$journal" 2>/dev/null | tr -d " " || echo 0)
    if [ "${total:-0}" -gt "$lu" ]; then
      sed -n "$((lu + 1)),${total}p" "$journal"
      lu=$total
    fi
  }

  pid=""; inactif=0
  while :; do
    relayer
    if [ -f "$statut" ]; then break; fi
    if [ -z "$pid" ]; then pid=$(trouver_pid || true); fi
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      sleep 0.5                     # laisse le temps d'écrire le statut en sortant
      if [ ! -f "$statut" ]; then code=127; break; fi
    fi
    # `open` a rendu la main sans erreur : le moissonneur existe, même s'il tarde à
    # apparaître. Renoncer sur un délai court l'abandonnerait bien vivant, à ouvrir les
    # applications hors de toute surveillance — on n'abandonne donc qu'après une longue
    # inactivité complète, et en le disant.
    if [ -z "$pid" ] && [ "$lu" -eq 0 ]; then
      inactif=$((inactif + 1))
      if [ "$inactif" -gt 1200 ]; then code=126; break; fi
    else
      inactif=0
    fi
    sleep 0.1
  done
  relayer

  trap - INT TERM
  code=${code:-$(cat "$statut" 2>/dev/null || echo 127)}
  rm -rf "$dossier"
  if [ "$code" = 126 ]; then
    echo "⛔️ Le moissonneur n'a donné aucun signe de vie en deux minutes."
    echo "   Il tourne peut-être encore : pgrep -x ShortcutHarvester"
  elif [ "$code" = 127 ]; then
    echo "⛔️ Le moissonneur s'est interrompu sans rendre de statut."
  fi
  return "$code"
}

# L'autorisation qui compte est celle du bundle, puisque c'est lui qui sera lancé.
# La demander depuis ce shell interrogerait le terminal, qui n'a plus besoin de rien.
autorisation_bundle() {
  local dossier verdict reponse i
  dossier=$(mktemp -d); verdict="$dossier/verdict"
  if ! open -n -a "$BUNDLE" --args --check --verdict "$verdict" 2>/dev/null; then
    rm -rf "$dossier"
    echo "⚠️  LaunchServices n'a pas pu lancer le moissonneur : autorisation invérifiable." >&2
    return 1
  fi
  i=0
  while [ ! -f "$verdict" ] && [ "$i" -lt 300 ]; do sleep 0.1; i=$((i + 1)); done
  # Une absence de réponse n'est pas un refus : le dire évite de renvoyer l'utilisateur
  # vers Réglages Système pour une panne de lancement.
  if [ ! -f "$verdict" ]; then
    rm -rf "$dossier"
    echo "⚠️  Le moissonneur n'a pas répondu en 30 s : autorisation non vérifiée." >&2
    return 1
  fi
  reponse=$(cat "$verdict")
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
               --out "$RACINE/$APPS_DIR" --reglages "$RACINE/out/reglages-scan.json" \
               ${SUPPL[@]+"${SUPPL[@]}"} || true
  elif [ -n "$PERIMEES" ]; then
    echo "→ Fiches périmées : relecture impossible sans l'autorisation du moissonneur"
  fi
else
  if [ "$AUTORISE" != oui ]; then
    # Message écrit ici, et non délégué au moissonneur : exécuté depuis ce shell, son
    # `--check` répondrait sur le terminal — le processus responsable. Un terminal encore
    # autorisé par une passe antérieure lui ferait afficher « autorisation accordée »
    # juste avant que run.sh s'arrête, sans rien expliquer.
    echo
    echo "⛔️ Le moissonneur n'a pas l'autorisation d'accessibilité."
    echo
    echo "   Ouvrir Réglages Système → Confidentialité et sécurité → Accessibilité,"
    echo "   puis y faire glisser :"
    echo "     $BUNDLE"
    echo
    echo "   S'il y figure déjà, la ligne date d'une compilation antérieure : la retirer"
    echo "   avec « − », puis la remettre. L'autorisation est liée à l'empreinte exacte"
    echo "   du binaire, qu'un aller-retour de l'interrupteur ne réenregistre pas."
    echo
    echo "   Révéler le bundle dans le Finder :"
    echo "     open -R \"$BUNDLE\""
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
