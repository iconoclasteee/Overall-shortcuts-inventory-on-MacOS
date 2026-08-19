#!/bin/bash
# Generates the keyboard shortcut inventory.
#
#   ./run.sh --test     6 representative apps, to validate the mechanics
#   ./run.sh --all      every installed app
#   ./run.sh --sources  re-reads system shortcuts and global tools without opening a
#                       single application — a few seconds
#
# A pass is resumable: each app is written to its own JSON file and a re-run skips what
# is already there. Interrupting with Ctrl-C loses nothing.
set -euo pipefail
cd "$(dirname "$0")"
# The harvester is launched through LaunchServices, which does not pass on the working
# directory: every path handed to it must be absolute.
RACINE=$(pwd)

# out/ is not versioned: on a fresh clone it does not exist, and the first redirection
# would fail before even the first message.
mkdir -p out
# The output derives from folders Apple keeps owner-only: preferences, menu bars.
# Leaving what comes out of them readable by the machine's other accounts would undo that
# protection. The folder alone is enough: what it holds becomes unreachable to anyone who
# cannot traverse it.
chmod go-rwx out 2>/dev/null || true

BUNDLE="$RACINE/bin/ShortcutHarvester.app"
HARVESTER="$BUNDLE/Contents/MacOS/ShortcutHarvester"
[ -x "$HARVESTER" ] || { echo "Binaire absent — lancer d'abord ./build.sh"; exit 1; }

# Launches the harvester through LaunchServices rather than from this shell.
#
# macOS does not grant accessibility permission to the binary being executed, but to the
# **responsible process** — the one that launched it. Run directly from here, that is the
# terminal: reading menus would then mean authorising the terminal, and therefore
# everything it runs afterwards, today and later. Launched by `open`, the bundle is its
# own responsible process, and its single line in the Accessibility list is enough.
#
# The price: `open` returns neither the program's output nor its exit code. Hence the
# journal, relayed live from here, and the status file, whose appearance is the only
# reliable end-of-run signal.
moissonner() {
  local dossier journal statut pid code lu total inactif
  dossier=$(mktemp -d); journal="$dossier/journal"; statut="$dossier/statut"
  : > "$journal"

  # Finds OUR harvester, and not another one.
  #
  # `pgrep` matches by name: two passes launched in parallel would be confused for one
  # another, and interrupting one would kill the other's harvester. The journal path, by
  # contrast, comes out of `mktemp` and belongs to this call alone — and it sits in the
  # process's command line. We cross it with the program name, since `open` carries the
  # same argument in its own.
  trouver_pid() {
    local candidat
    for candidat in $(pgrep -f -- "$journal" 2>/dev/null || true); do
      case "$(ps -o comm= -p "$candidat" 2>/dev/null)" in
        */ShortcutHarvester) echo "$candidat"; return 0 ;;
      esac
    done
    return 1
  }

  # The trap is set before any waiting. Launched through LaunchServices, the harvester
  # does not descend from this shell: Ctrl-C does not reach it, and an interrupt arriving
  # while we are still looking for its process id would leave it opening applications on
  # its own. So the trap finds it itself, at signal time.
  trap 'kill "$(trouver_pid)" 2>/dev/null || true; rm -rf "$dossier"; exit 130' INT TERM

  if ! open -n -a "$BUNDLE" --args "$@" --journal "$journal" --statut "$statut"; then
    trap - INT TERM; rm -rf "$dossier"
    echo "⛔️ LaunchServices n'a pas pu lancer le moissonneur."
    return 127
  fi

  # The journal is re-read in slices rather than followed with `tail -f`: no background
  # job to kill, no shell message when killing it, and the last lines are read for
  # certain — an interrupted `tail` can leave them behind.
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
      sleep 0.5                     # leaves time to write the status on the way out
      if [ ! -f "$statut" ]; then code=127; break; fi
    fi
    # `open` returned without error: the harvester exists, even if it is slow to appear.
    # Giving up on a short deadline would abandon it very much alive, opening applications
    # with nobody watching — so we give up only after a long spell of complete inactivity,
    # and we say so.
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

# The permission that matters is the bundle's, since the bundle is what gets launched.
# Asking from this shell would query the terminal, which no longer needs anything.
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
  # No answer is not a refusal: saying so avoids sending the user to System Settings over
  # a launch failure.
  if [ ! -f "$verdict" ]; then
    rm -rf "$dossier"
    echo "⚠️  Le moissonneur n'a pas répondu en 30 s : autorisation non vérifiée." >&2
    return 1
  fi
  reponse=$(cat "$verdict")
  rm -rf "$dossier"
  [ "$reponse" = accordee ]
}

# Permission is required only to read a menu bar. Listing installed apps, exporting the
# keyboard layout and rebuilding the page need none — and refusing to do them would make
# the page impossible to regenerate right after a rebuild, which is precisely what
# invalidates the grant.
AUTORISE=oui
autorisation_bundle || AUTORISE=non

# Test set: each app covers a different failure mode.
#   Finder      always-running app, rich menus
#   TextEdit    document-based app, read without a document open
#   Safari      deep native menus
#   cmux        Electron app, menus built in JavaScript
#   Alfred      agent app with no conventional menu bar
#   PowerPoint  heavy app + user-redefined shortcuts
TEST_APPS=com.apple.finder,com.apple.TextEdit,com.apple.Safari,com.cmuxterm.app,com.runningwithcrayons.Alfred,com.microsoft.Powerpoint

case "${1:---test}" in
  --test) APPS_DIR=out/apps-test; REPORT=out/shortcuts-test.md
          INDEX=out/index-test.json; PAGE=out/shortcuts-test.html
          TARGET=(--bundle-ids "$TEST_APPS"); SUPPL=("${@:2}") ;;
  --all)  APPS_DIR=out/apps;      REPORT=out/shortcuts.md
          INDEX=out/index.json;    PAGE=out/shortcuts.html
          TARGET=(--all); SUPPL=("${@:2}") ;;
  --sources) APPS_DIR=out/apps; REPORT=out/shortcuts.md
          INDEX=out/index.json;  PAGE=out/shortcuts.html
          TARGET=(); SUPPL=("${@:2}") ;;
  # Explicit list, as the page produces it. --force is essential: without it the harvester
  # skips every app whose record already exists — that is, precisely the ones just ticked
  # because their version changed.
  --apps) APPS_DIR=out/apps;      REPORT=out/shortcuts.md
          INDEX=out/index.json;    PAGE=out/shortcuts.html
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
  # --sources mode: application shortcuts already read are kept as they are.
  echo "→ Raccourcis par application : conservés ($(ls "$APPS_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ') fiches)"
  # Except those whose version changed AND that are already running: re-reading them costs
  # nothing and makes no window appear. A closed app keeps its record until it is ticked
  # in the page — opening apps stays something the user asks for, never a side effect.
  PERIMEES=$(python3 src/stale.py "$APPS_DIR" || true)
  if [ -n "$PERIMEES" ] && [ "$AUTORISE" = oui ]; then
    echo "→ Fiches périmées relues, sans ouvrir d'application"
    moissonner --bundle-ids "$PERIMEES" --force --only-running \
               --out "$RACINE/$APPS_DIR" --reglages "$RACINE/out/scan-settings.json" \
               ${SUPPL[@]+"${SUPPL[@]}"} || true
  elif [ -n "$PERIMEES" ]; then
    echo "→ Fiches périmées : relecture impossible sans l'autorisation du moissonneur"
  fi
else
  if [ "$AUTORISE" != oui ]; then
    # Message written here rather than delegated to the harvester: run from this shell,
    # its `--check` would answer about the terminal — the responsible process. A terminal
    # still authorised by an earlier pass would make it print "permission granted" right
    # before run.sh stops, explaining nothing.
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
             --reglages "$RACINE/out/scan-settings.json" ${SUPPL[@]+"${SUPPL[@]}"}
fi

echo "→ Index unifié (système + apps + outils tiers)"
python3 src/index.py "$APPS_DIR" "$INDEX"

echo "→ Restitution"
python3 src/report.py "$APPS_DIR" "$REPORT"
python3 src/page.py "$INDEX" "$PAGE"

# A syntax error in the JavaScript makes the page ENTIRELY inert: headings, tabs, tables
# and labels are all written by the script. Python produces the file without ever reading
# it back, and generation succeeds regardless — the page then ships broken, in silence.
# This check is the only thing that notices.
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
# End-of-pass reminder, shown only when it serves a purpose.
#
# Since the harvester is launched through LaunchServices, it is its own responsible
# process and its own grant applies: no terminal needs accessibility permission for a pass
# to work any more. If this shell holds it regardless, that is a leftover from an earlier
# pass — and for as long as it stands, everything this terminal runs can read and drive
# any application.
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
