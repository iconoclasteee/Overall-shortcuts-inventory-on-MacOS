"""Fiches dont la version lue ne correspond plus à la version installée.

Sert à relire ce qui a bougé **sans ouvrir la moindre application** : la liste
produite ici est passée au moissonneur avec --only-running, qui écarte tout ce qui
n'est pas déjà lancé. Une app fermée garde donc sa fiche telle quelle jusqu'à ce
qu'elle soit cochée explicitement dans la page.

Le test porte sur le numéro complet, pas seulement sur le premier nombre : ici on ne
décide pas d'ouvrir une app, on relit ce qui est déjà sous la main, donc le moindre
écart vaut la peine.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def perimees(apps_dir=None, catalogue=None):
    apps_dir = Path(apps_dir or ROOT / "out" / "apps")
    catalogue = Path(catalogue or ROOT / "out" / "catalogue.json")
    if not catalogue.exists():
        return []
    installees = {a["bundleID"]: a.get("version")
                  for a in json.loads(catalogue.read_text(encoding="utf-8"))
                  if not a.get("exclu")}
    dehors = []
    for fiche in sorted(apps_dir.glob("*.json")):
        try:
            lue = json.loads(fiche.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        bundle_id = lue.get("bundleID")
        if bundle_id in installees and installees[bundle_id] != lue.get("version"):
            dehors.append(bundle_id)
    return dehors


if __name__ == "__main__":
    liste = perimees(*sys.argv[1:3])
    if liste:
        print(",".join(liste))
