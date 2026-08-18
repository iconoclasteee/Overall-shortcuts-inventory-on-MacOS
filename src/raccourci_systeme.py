"""Activer ou désactiver un raccourci système macOS, y compris ceux qu'aucun panneau
de réglages n'expose.

Les raccourcis système vivent tous dans le domaine `com.apple.symbolichotkeys`, sous
un identifiant numérique. Réglages Système n'en montre qu'une partie : ceux qu'Apple
décrit dans ses tables de référence. Les autres ne sont modifiables que là.

Rien n'est écrit sans `--oui`, et une sauvegarde horodatée du domaine complet est
faite avant toute modification.
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


def inventaire():
    """{id: (libellé, combinaison)} d'après ce que le projet a déjà extrait."""
    chemin = ROOT / "out" / "system-shortcuts.json"
    if not chemin.exists():
        return {}
    return {r["id"]: (r["nom"], r["combinaison"])
            for r in json.loads(chemin.read_text(encoding="utf-8"))}


def sauvegarder(plist):
    dossier = ROOT / "out" / "sauvegardes"
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
        raise SystemExit(f"L'identifiant {identifiant} n'existe pas dans {DOMAINE}.")

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
    # `defaults write` avec un plist en argument est fragile : on réimporte le domaine
    # complet depuis un fichier, ce qui préserve les types exactement.
    temporaire = ROOT / "out" / "sauvegardes" / "domaine-en-cours.plist"
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
