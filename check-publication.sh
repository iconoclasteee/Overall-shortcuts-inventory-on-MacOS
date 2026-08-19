#!/bin/bash
# Re-reads what would be published — tracked files and git history — looking for
# anything that identifies a person or a machine.
#
# History counts as much as the current state: an absolute path removed today is still
# readable in the commit that introduced it.
set -uo pipefail
cd "$(dirname "$0")"

motifs=(
  '/Users/[a-zA-Z0-9._-]+'                     # absolute path carrying an account name
  '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}' # e-mail address
  '(MacBook|iMac|Mac-mini|Mac-Studio)[a-zA-Z0-9-]*' # machine name
  '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'            # IP address
  '(ssh-rsa|BEGIN [A-Z ]*PRIVATE KEY)'         # private key
)

# This file holds the patterns themselves: searching it would flag the script on every
# run. The history exclusion is a glob rather than the exact current name: the script has
# already been renamed once, and every earlier version carries the same patterns — under
# an exact name they would flag themselves out of the git history for ever.
MOI=$(basename "$0")
EXCLUSION=':(exclude,glob)*publication.sh'

alerte=0
echo "→ Fichiers versionnés"
for motif in "${motifs[@]}"; do
  # The test looks at what was found, never at the exit code: xargs returns non-zero as
  # soon as one of its grep invocations finds nothing, which under pipefail would erase
  # the alert raised by the other batches. Same family as the `grep | head` defect fixed
  # below.
  resultat=$(git ls-files -z | grep -zv "^$MOI$" | xargs -0 grep -nIE "$motif" 2>/dev/null || true)
  if [ -n "$resultat" ]; then
    echo "  ⚠️  $motif"; echo "$resultat" | sed 's/^/      /'; alerte=1
  fi
done

echo "→ Historique git (messages et contenus)"
for motif in "${motifs[@]}"; do
  # No `head` inside the test: on a large history, grep dies of SIGPIPE as soon as head
  # has had its fill, the pipeline turns non-zero and the alert vanishes — precisely when
  # the leak is largest. Truncation happens at display time instead.
  if resultat=$(git log -p --format="%H %s" -- . "$EXCLUSION" 2>/dev/null \
                | grep -nIE "$motif"); then
    echo "  ⚠️  $motif"; echo "$resultat" | head -5 | sed 's/^/      /'; alerte=1
  fi
done

echo "→ Fichiers de données versionnés"
git ls-files 'data/*' | while read -r f; do echo "      $f ($(wc -c < "$f" | tr -d ' ') octets)"; done

if [ "$alerte" -eq 0 ]; then
  echo
  echo "✅ Rien d'identifiant trouvé. Vérifie tout de même que out/ est bien ignoré :"
  git check-ignore -q out && echo "   ✅ out/ est ignoré" || echo "   ⚠️  out/ N'EST PAS ignoré"
else
  echo
  echo "⛔️ Des éléments identifiants sont présents. Corriger avant de publier."
  echo "   Un motif trouvé dans l'historique impose une réécriture (git filter-repo),"
  echo "   pas seulement un nouveau commit."
  exit 1
fi
