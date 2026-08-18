"""Raccourcis redéfinis par l'utilisateur (Réglages → Clavier → Raccourcis d'app).

macOS les range dans les préférences de chaque app, indexés par **titre d'élément de
menu**. C'est donc le titre qui sert de clé de jointure avec ce que l'accessibilité
renvoie — et c'est aussi pourquoi un titre qui ne colle plus (app traduite, commande
renommée) rend le raccourci inopérant sans rien signaler.
"""

import plistlib
import subprocess

# Syntaxe des équivalents clavier Cocoa telle qu'écrite dans NSUserKeyEquivalents.
COCOA_MODIFIERS = [("^", "⌃"), ("~", "⌥"), ("$", "⇧"), ("@", "⌘")]


def parse_cocoa_key_equivalent(raw):
    """Traduit "@~^$m" en "⌃⌥⇧⌘M".

    Les caractères @ ~ ^ $ ne désignent des modificateurs qu'**en préfixe** : sur un
    clavier français, « $ » est une touche à part entière. Les dépouiller partout
    ferait disparaître la touche et ajouterait un Maj fantôme à « ⌘$ ».
    """
    raw = raw or ""
    i = 0
    while i < len(raw) - 1 and raw[i] in "@~^$":
        i += 1
    prefixe, touche = raw[:i], raw[i:]
    mods = "".join(sym for token, sym in COCOA_MODIFIERS if token in prefixe)
    return mods + touche.upper()


def decomposer(raw):
    """(modificateurs Cocoa, touche) d'un équivalent clavier, sans les fusionner.

    Le combo affichable ne suffit pas : pour comparer une redéfinition aux autres
    raccourcis, il faut ses modificateurs et sa touche séparément.
    """
    raw = raw or ""
    i = 0
    while i < len(raw) - 1 and raw[i] in "@~^$":
        i += 1
    return raw[:i], raw[i:]


def normalise_title(title):
    """Rapproche un titre de menu d'une clé NSUserKeyEquivalents.

    Les deux décrivent le même élément mais pas toujours à l'identique : points de
    suspension typographiques contre trois points, casse, espaces.
    """
    return (title or "").replace("...", "…").rstrip("… ").strip().casefold()


def load(bundle_id):
    """{titre normalisé: (titre d'origine, combinaison)} pour une app."""
    export = subprocess.run(["defaults", "export", bundle_id, "-"], capture_output=True)
    if export.returncode != 0 or not export.stdout:
        return {}
    try:
        prefs = plistlib.loads(export.stdout)
    except Exception:
        return {}
    return {normalise_title(title): (title, parse_cocoa_key_equivalent(value), value)
            for title, value in (prefs.get("NSUserKeyEquivalents") or {}).items()}
