"""Inventaire des raccourcis système macOS, en français.

Deux sources, toutes deux locales et faisant autorité :

1. La table de référence d'Apple, livrée avec le panneau Clavier des Réglages Système :
   KeyboardSettings.appex/.../DefaultShortcutsTable.xml  (+ .loctable pour le français)
   -> donne TOUS les raccourcis système existants et leur combinaison par défaut.

2. Les préférences de l'utilisateur : com.apple.symbolichotkeys
   -> donne l'état réel : activé/désactivé, et la combinaison si elle a été changée.

La source 1 est indispensable : le plist utilisateur ne contient que les raccourcis
"matérialisés", donc l'utiliser seul sous-déclare silencieusement l'inventaire.
"""

import json
import plistlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tables import keycode_labels, render_modifiers
from model import Keyboard, from_nsevent

APPEX = Path(
    "/System/Library/ExtensionKit/Extensions/KeyboardSettings.appex/Contents/Resources"
)
NO_CHAR = 65535  # sentinelle Apple : "pas de caractère, utiliser le code de touche"


def _strip_marker(text):
    """Retire le marqueur interne d'Apple sur les chaînes non traduites."""
    return text.removeprefix("DO_NOT_LOCALIZE: ").strip()


def load_reference(lang="fr"):
    """Charge la table de référence Apple, traduite dans la langue demandée."""
    table_path = APPEX / f"{lang}.lproj" / "DefaultShortcutsTable.xml"
    loc_path = APPEX / "DefaultShortcutsTable.loctable"
    if not table_path.exists():
        raise SystemExit(f"Table de référence Apple introuvable : {table_path}")

    translations = {}
    if loc_path.exists():
        loctable = plistlib.loads(loc_path.read_bytes())
        translations = loctable.get(lang) or loctable.get("en") or {}

    def translate(raw):
        clean = _strip_marker(raw)
        return translations.get(clean, clean), clean

    entries = {}

    def walk(node, cat_fr, cat_en, cat_id, path):
        """Descend récursivement : la table Apple imbrique des sous-groupes
        (ex. Fenêtres > Placer en mosaïque) sous la clé `elements`."""
        for element in node.get("elements", []):
            name_fr, name_en = translate(element.get("name", ""))
            sub_path = path + [name_fr]
            for id_key in ("sybmolichotkey", "prefs_sybmolichotkey", "slow_sybmolichotkey"):
                hotkey_id = element.get(id_key)
                if hotkey_id is None or hotkey_id in entries:
                    continue
                entries[hotkey_id] = {
                    "id": hotkey_id,
                    "variante": id_key.removesuffix("sybmolichotkey").rstrip("_") or "principal",
                    "categorie": cat_fr,
                    "categorie_en": cat_en,
                    "identifiant_categorie": cat_id,
                    "nom": " > ".join(sub_path),
                    "nom_en": name_en,
                    # key/modifier décrivent l'entrée principale. Pour les variantes,
                    # Apple ne publie pas de valeur par défaut : on ne compare donc rien.
                    "defaut": _render(
                        element.get("charKey", NO_CHAR),
                        element.get("key", NO_CHAR),
                        element.get("modifier", 0),
                    ) if id_key == "sybmolichotkey" else None,
                }
            walk(element, cat_fr, cat_en, cat_id, sub_path)

    for category in plistlib.loads(table_path.read_bytes()):
        cat_fr, cat_en = translate(category.get("name", ""))
        walk(category, cat_fr, cat_en, category.get("identifier", ""), [])

    return entries


def load_user_state():
    """Lit com.apple.symbolichotkeys via `defaults` (format plist XML)."""
    raw = subprocess.run(
        ["defaults", "export", "com.apple.symbolichotkeys", "-"],
        capture_output=True,
    )
    if raw.returncode != 0 or not raw.stdout:
        return {}
    plist = plistlib.loads(raw.stdout)
    state = {}
    for key, entry in (plist.get("AppleSymbolicHotKeys") or {}).items():
        params = ((entry.get("value") or {}).get("parameters")) or []
        combo = None
        if len(params) >= 3:
            combo = _render(params[0], params[1], params[2])
        state[int(key)] = {"actif": bool(entry.get("enabled")), "combinaison": combo}
    return state


_keyboard = None


def _render(char_code, key_code, modifier_mask):
    """Assemble une combinaison lisible et sa forme comparable.

    Renvoie un dict {combo, mods, code} : `combo` pour l'affichage, `mods` et `code`
    pour la comparaison avec les raccourcis venus des menus et des outils tiers.
    """
    global _keyboard
    if _keyboard is None:
        _keyboard = Keyboard()
    labels = keycode_labels()
    mods = from_nsevent(modifier_mask or 0)
    # charKey d'abord : c'est le caractère réellement produit, donc juste quelle que
    # soit la disposition clavier (un code de touche brut supposerait un clavier ANSI).
    # Mais un caractère non imprimable (espace, tabulation) n'est pas lisible tel quel :
    # dans ce cas on retombe sur le libellé du code de touche.
    code = key_code if isinstance(key_code, int) and key_code != NO_CHAR else None
    if isinstance(char_code, int) and char_code not in (0, NO_CHAR) and chr(char_code).strip():
        key = chr(char_code).upper()
        # Le caractère prime sur le code de touche. La table d'Apple stocke des codes
        # de clavier ANSI : pour ⌘M elle donne 46, qui sur AZERTY produit « , ».
        # macOS déclenche sur la touche portant réellement le M, donc on remonte au
        # code par le caractère, dans la disposition active.
        code = _keyboard.code_for(chr(char_code)) or code
    elif code is not None:
        key = labels.get(code, f"touche-{code}")
    else:
        return None
    return {"combo": render_modifiers(modifier_mask or 0) + key, "mods": mods, "code": code}


def build():
    reference = load_reference()
    user_state = load_user_state()
    results = []

    for hotkey_id, entry in reference.items():
        state = user_state.get(hotkey_id)
        record = dict(entry)
        if state is None:
            # Absent du plist utilisateur = jamais modifié = réglage d'usine actif.
            record["touche"] = entry["defaut"]
            record["actif"] = entry["defaut"] is not None
            record["etat"] = "défaut"
        else:
            record["touche"] = state["combinaison"] or entry["defaut"]
            record["actif"] = state["actif"]
            if not state["actif"]:
                record["etat"] = "désactivé"
            elif entry["defaut"] is None:
                record["etat"] = "actif"  # pas de valeur d'usine connue : rien à comparer
            elif state["combinaison"] and state["combinaison"] != entry["defaut"]:
                record["etat"] = "personnalisé"
            else:
                record["etat"] = "défaut"
        touche = record.pop("touche", None)
        record["combinaison"] = touche["combo"] if touche else None
        record["mods"] = touche["mods"] if touche else 0
        record["code"] = touche["code"] if touche else None
        record["defaut"] = entry["defaut"]["combo"] if entry["defaut"] else None
        results.append(record)

    # Les IDs présents chez l'utilisateur mais absents de la table Apple sont conservés
    # tels quels : un identifiant brut consultable vaut mieux qu'une omission invisible.
    for hotkey_id, state in user_state.items():
        if hotkey_id in reference:
            continue
        results.append({
            "id": hotkey_id,
            "categorie": "Non documenté par Apple",
            "categorie_en": "Undocumented",
            "identifiant_categorie": "unknown",
            "nom": f"Raccourci système #{hotkey_id}",
            "nom_en": f"Symbolic hotkey #{hotkey_id}",
            "defaut": None,
            "combinaison": (state["combinaison"] or {}).get("combo"),
            "mods": (state["combinaison"] or {}).get("mods", 0),
            "code": (state["combinaison"] or {}).get("code"),
            "actif": state["actif"],
            "etat": "non documenté",
        })

    results.sort(key=lambda r: (r["categorie"], r["nom"]))
    return results


if __name__ == "__main__":
    out_path = Path(__file__).parent.parent / "out" / "system-shortcuts.json"
    data = build()
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    documented = sum(1 for r in data if r["etat"] != "non documenté")
    print(f"{len(data)} raccourcis système -> {out_path}")
    print(f"  {documented} documentés par Apple, {len(data) - documented} inconnus")
    for etat in ("défaut", "actif", "personnalisé", "désactivé", "non documenté"):
        n = sum(1 for r in data if r["etat"] == etat)
        if n:
            print(f"  {etat:16} {n}")
