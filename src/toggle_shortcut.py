"""Enable or disable a macOS system shortcut, including those no settings panel exposes.

Every system shortcut lives in the `com.apple.symbolichotkeys` domain, under a numeric
identifier. System Settings shows only some of them: the ones Apple describes in its
reference tables. The rest can be changed only here.

Nothing is written without `--oui`, and a timestamped backup of the whole domain is taken
before any change.
"""

import argparse
import json
import plistlib
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOMAINE = "com.apple.symbolichotkeys"
ACTIVATE = Path("/System/Library/PrivateFrameworks/SystemAdministration.framework"
                "/Resources/activateSettings")


def lire_domaine():
    export = subprocess.run(["defaults", "export", DOMAINE, "-"], capture_output=True)
    if export.returncode != 0 or not export.stdout:
        raise SystemExit(f"Impossible de lire {DOMAINE}")
    return plistlib.loads(export.stdout)


def defauts():
    """Raw factory values, so an entry that does not exist yet can be written."""
    sys.path.insert(0, str(Path(__file__).parent))
    from system_shortcuts import raw_reference
    return raw_reference()


def inventaire():
    """{id: (label, combination)} from what the project has already extracted."""
    chemin = ROOT / "out" / "system-shortcuts.json"
    if not chemin.exists():
        return {}
    return {r["id"]: (r["nom"], r["combinaison"])
            for r in json.loads(chemin.read_text(encoding="utf-8"))}


def sauvegarder(plist):
    dossier = ROOT / "out" / "backups"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"symbolichotkeys-{time.strftime('%Y%m%d-%H%M%S')}.plist"
    chemin.write_bytes(plistlib.dumps(plist))
    return chemin


def lister(actifs_seulement, non_documentes_seulement):
    plist = lire_domaine()
    noms = inventaire()
    for cle, entree in sorted(plist.get("AppleSymbolicHotKeys", {}).items(), key=lambda kv: int(kv[0])):
        identifiant = int(cle)
        actif = bool(entree.get("enabled"))
        libelle, combo = noms.get(identifiant, (f"Raccourci système #{identifiant}", None))
        inconnu = identifiant not in noms or libelle.startswith("Raccourci système #")
        if actifs_seulement and not actif:
            continue
        if non_documentes_seulement and not inconnu:
            continue
        etat = "actif    " if actif else "désactivé"
        print(f"  {identifiant:4}  {etat}  {(combo or '—'):10}  {libelle}")


def basculer(identifiant, activer, confirme):
    plist = lire_domaine()
    table = plist.get("AppleSymbolicHotKeys", {})
    cle = str(identifiant)
    if cle not in table:
        # Missing from the preferences = still at factory setting. macOS writes the entry
        # only on the first change: we create it with the combination Apple publishes.
        brut = defauts().get(identifiant)
        if brut is None:
            raise SystemExit(
                f"L'identifiant {identifiant} n'est ni dans {DOMAINE} ni dans les "
                "tables de référence d'Apple : impossible de connaître sa combinaison "
                "d'usine sans l'inventer.")
        char, code, modificateur = brut
        table[cle] = {"enabled": True,
                      "value": {"parameters": [char, code, modificateur],
                                "type": "standard"}}
        print(f"(entrée absente des préférences — créée depuis les valeurs d'usine "
              f"d'Apple : {brut})")

    noms = inventaire()
    libelle, combo = noms.get(identifiant, (f"Raccourci système #{identifiant}", None))
    avant = bool(table[cle].get("enabled"))
    if avant == activer:
        print(f"Rien à faire : {identifiant} est déjà {'actif' if activer else 'désactivé'}.")
        return

    print(f"Raccourci  : {identifiant} — {libelle}")
    print(f"Combinaison: {combo or 'aucune'}")
    print(f"Changement : {'actif' if avant else 'désactivé'} → "
          f"{'actif' if activer else 'désactivé'}")
    if not confirme:
        print("\nRien n'a été écrit. Ajoute --oui pour appliquer.")
        return

    chemin = sauvegarder(plist)
    table[cle]["enabled"] = activer
    # `defaults write` with a plist as an argument is brittle: the whole domain is
    # re-imported from a file instead, which preserves the types exactly.
    temporaire = ROOT / "out" / "backups" / "domaine-en-cours.plist"
    temporaire.write_bytes(plistlib.dumps(plist))
    subprocess.run(["defaults", "import", DOMAINE, str(temporaire)], check=True)
    temporaire.unlink(missing_ok=True)

    print(f"\n✅ Écrit. Sauvegarde avant modification : {chemin}")
    if ACTIVATE.exists():
        subprocess.run([str(ACTIVATE), "-u"], check=False)
        print("   Réglages rechargés. Si le changement ne prend pas, ferme puis rouvre ta session.")
    else:
        print("   Ferme puis rouvre ta session pour que le changement prenne effet.")
    print(f"\n   Pour revenir en arrière :\n"
          f"     defaults import {DOMAINE} {chemin}\n"
          f"     {ACTIVATE} -u")


if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = parseur.add_subparsers(dest="commande", required=True)

    p_liste = sous.add_parser("liste", help="lister les raccourcis système")
    p_liste.add_argument("--actifs", action="store_true", help="seulement les actifs")
    p_liste.add_argument("--inconnus", action="store_true",
                         help="seulement ceux qu'Apple ne documente pas")

    for nom, valeur in (("off", False), ("on", True)):
        p = sous.add_parser(nom, help=("désactiver" if not valeur else "réactiver")
                            + " un raccourci système")
        p.add_argument("id", type=int)
        p.add_argument("--oui", action="store_true", help="appliquer réellement")
        p.set_defaults(activer=valeur)

    args = parseur.parse_args()
    if args.commande == "liste":
        lister(args.actifs, args.inconnus)
    else:
        basculer(args.id, args.activer, args.oui)
