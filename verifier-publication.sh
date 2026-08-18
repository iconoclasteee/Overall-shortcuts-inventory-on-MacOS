#!/bin/bash
# Relit ce qui serait publié — fichiers versionnés et historique git — à la recherche
# de ce qui identifie une personne ou une machine.
#
# L'historique compte autant que l'état courant : un chemin absolu retiré aujourd'hui
# reste lisible dans le commit qui l'a introduit.
set -uo pipefail
cd "$(dirname "$0")"

motifs=(
  '/Users/[a-zA-Z0-9._-]+'                     # chemin absolu contenant un compte
  '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}' # adresse e-mail
  '(MacBook|iMac|Mac-mini|Mac-Studio)[a-zA-Z0-9-]*' # nom de machine
  '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'            # adresse IP
  '(ssh-rsa|BEGIN [A-Z ]*PRIVATE KEY)'         # clé privée
)

# Ce fichier contient les motifs eux-mêmes : les chercher en lui reviendrait à
# se signaler soi-même à chaque exécution.
MOI=$(basename "$0")

alerte=0
echo "→ Fichiers versionnés"
for motif in "${motifs[@]}"; do
  if resultat=$(git ls-files -z | grep -zv "^$MOI$" | xargs -0 grep -nIE "$motif" 2>/dev/null); then
    echo "  ⚠️  $motif"; echo "$resultat" | sed 's/^/      /'; alerte=1
  fi
done

echo "→ Historique git (messages et contenus)"
for motif in "${motifs[@]}"; do
  if resultat=$(git log -p --format="%H %s" -- . ":(exclude)$MOI" 2>/dev/null \
                | grep -nIE "$motif" | head -5); then
    echo "  ⚠️  $motif"; echo "$resultat" | sed 's/^/      /'; alerte=1
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
