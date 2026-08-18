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
    """Traduit "@~^$m" en "⌃⌥⇧⌘M"."""
    mods = "".join(sym for token, sym in COCOA_MODIFIERS if token in raw)
    key = "".join(c for c in raw if c not in "@~^$")
    return mods + key.upper()


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
    return {normalise_title(title): (title, parse_cocoa_key_equivalent(value))
            for title, value in (prefs.get("NSUserKeyEquivalents") or {}).items()}
