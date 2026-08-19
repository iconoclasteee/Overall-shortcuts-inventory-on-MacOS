"""Records whose recorded version no longer matches the installed one.

Used to re-read what has moved **without opening a single application**: the list
produced here is passed to the harvester with --only-running, which skips anything not
already running. A closed app therefore keeps its record as is until it is explicitly
ticked in the page.

The test looks at the full version string, not just its first number: this is not a
decision to open an app, but a re-read of what is already at hand, so the slightest
difference is worth it.
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
