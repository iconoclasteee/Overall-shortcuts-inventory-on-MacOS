"""Inventory of macOS system shortcuts, in the system language.

Two sources, both local and authoritative:

1. Apple's reference table, shipped with the Keyboard panel of System Settings:
   KeyboardSettings.appex/.../DefaultShortcutsTable.xml  (+ .loctable for the labels)
   -> gives EVERY existing system shortcut and its default combination.

2. The user's preferences: com.apple.symbolichotkeys
   -> gives the actual state: enabled/disabled, and the combination if it was changed.

Source 1 is indispensable: the user plist holds only the shortcuts that have been
"materialised", so using it alone silently under-reports the inventory.
"""

import json
import plistlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tables import keycode_labels
from model import Keyboard, from_nsevent, render_modifiers, SHIFT

APPEX = Path(
    "/System/Library/ExtensionKit/Extensions/KeyboardSettings.appex/Contents/Resources"
)
NO_CHAR = 65535  # sentinelle Apple : "pas de caractère, utiliser le code de touche"

# Some system shortcuts are not a combination but a **double tap** on a modifier alone —
# dictation being the common example. Apple stores them with `type: "modifier"` and a mask
# that distinguishes the left key from the right one.
#
# The side bits are IOKit's (`NX_DEVICELCMDKEYMASK` = 8, `NX_DEVICERCMDKEYMASK` = 16) and
# the labels come from the macOS Keyboard panel, through `load_double_labels`. The numeric
# values are written out here, next to the name of the matching constant, rather than read
# back from a second BridgeSupport file for five entries.
MODIFIER_DOUBLE = [
    # (NSEvent modifier bit, IOKit side bit or None, label key, symbol)
    (0x100000, 8,    "DoubleTapCommandLeft",  "⌘"),
    (0x100000, 16,   "DoubleTapCommandRight", "⌘"),
    (0x100000, None, "DoubleTapCommand",      "⌘"),
    (0x040000, None, "DoubleTapControl",      "⌃"),
    (0x800000, None, "DoubleTapFn",           "fn"),
]


def _strip_marker(text):
    """Strips Apple's internal marker from untranslated strings."""
    return text.removeprefix("DO_NOT_LOCALIZE: ").strip()


def load_reference(lang="fr"):
    """Loads Apple's reference table, translated into the requested language."""
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
        """Descends recursively: Apple's table nests sub-groups (e.g. Windows > Tile)
        under the `elements` key."""
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
                    # key/modifier describe the main entry. For the variants, Apple
                    # publishes no default value: so nothing is compared.
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

    # Apple keeps the desktop shortcuts in a second, flat file. Without it, "Switch to
    # Desktop 1" and its fifteen neighbours come out as "undocumented".
    spaces_path = APPEX / "DefaultSpacesShortcuts.xml"
    if spaces_path.exists():
        cat_fr, cat_en = translate("DO_NOT_LOCALIZE: Mission Control")
        walk({"elements": plistlib.loads(spaces_path.read_bytes())},
             cat_fr, cat_en, "expose", [])

    return entries


def load_double_labels(lang="fr"):
    """Labels for double taps, as the Keyboard panel displays them."""
    path = APPEX / "Localizable.loctable"
    if not path.exists():
        return {}
    table = plistlib.loads(path.read_bytes())
    return table.get(lang) or table.get("en") or {}


def _double_tap(mask, labels):
    """Describes a double tap from its mask, or None if the mask matches no known
    modifier."""
    for bit, cote, cle, symbole in MODIFIER_DOUBLE:
        if not mask & bit:
            continue
        if cote is not None and not mask & cote:
            continue
        if cote is None and mask & 0x18 and bit == 0x100000:
            continue  # un côté est précisé : une entrée plus spécifique s'en charge
        return {"combo": symbole * 2, "mods": 0, "code": None,
                "libelle": labels.get(cle, cle)}
    return None


def raw_reference(lang="fr"):
    """{id: (charKey, key, modifier)} — the raw values from Apple's tables.

    Needed to write an entry back into `com.apple.symbolichotkeys` in the format macOS
    expects, without inventing the factory combination.
    """
    out = {}

    def walk(node):
        for element in node.get("elements", []):
            # The only identifier that really carries the described combination is the
            # main one. Its "prefs_" and "slow_" variants name other shortcuts, about which
            # the table says nothing — lending them the main one's value would amount to
            # inventing a combination and then writing it into the system preferences.
            for id_key in ("sybmolichotkey",):
                hotkey_id = element.get(id_key)
                if hotkey_id is not None and hotkey_id not in out and "key" in element:
                    out[hotkey_id] = (element.get("charKey", NO_CHAR),
                                      element.get("key", NO_CHAR),
                                      element.get("modifier", 0))
            walk(element)

    table = APPEX / f"{lang}.lproj" / "DefaultShortcutsTable.xml"
    if table.exists():
        for category in plistlib.loads(table.read_bytes()):
            walk(category)
    spaces = APPEX / "DefaultSpacesShortcuts.xml"
    if spaces.exists():
        walk({"elements": plistlib.loads(spaces.read_bytes())})
    return out


def load_user_state():
    """Reads com.apple.symbolichotkeys through `defaults` (XML plist format)."""
    raw = subprocess.run(
        ["defaults", "export", "com.apple.symbolichotkeys", "-"],
        capture_output=True,
    )
    if raw.returncode != 0 or not raw.stdout:
        return {}
    plist = plistlib.loads(raw.stdout)
    labels = load_double_labels()
    state = {}
    for key, entry in (plist.get("AppleSymbolicHotKeys") or {}).items():
        value = entry.get("value") or {}
        params = value.get("parameters") or []
        combo, double = None, None
        if value.get("type") == "modifier" and params:
            double = _double_tap(params[0], labels)
            combo = double
        elif len(params) >= 3:
            combo = _render(params[0], params[1], params[2])
        state[int(key)] = {"actif": bool(entry.get("enabled")), "combinaison": combo,
                           "double": bool(double)}
    return state


_keyboard = None


def _render(char_code, key_code, modifier_mask):
    """Assembles a readable combination and its comparable form.

    Returns a dict {combo, mods, code}: `combo` for display, `mods` and `code` for
    comparison against shortcuts coming from menus and third-party tools.
    """
    global _keyboard
    if _keyboard is None:
        _keyboard = Keyboard()
    labels = keycode_labels()
    mods = from_nsevent(modifier_mask or 0)
    # charKey first: it is the character actually produced, so it is right whatever the
    # keyboard layout (a raw key code would assume an ANSI keyboard). But a non-printing
    # character (space, tab) is not readable as is: in that case we fall back to the label
    # of the key code.
    code = key_code if isinstance(key_code, int) and key_code != NO_CHAR else None
    if isinstance(char_code, int) and char_code not in (0, NO_CHAR) and chr(char_code).strip():
        resolu, besoin_maj = _keyboard.resoudre(chr(char_code))
        if besoin_maj:
            mods |= SHIFT
        key = chr(char_code).upper()
        # The character wins over the key code. Apple's table stores ANSI keyboard codes:
        # for ⌘M it gives 46, which on AZERTY produces ",". macOS fires on the key that
        # actually carries the M, so the code is derived from the character, in the active
        # layout.
        code = resolu if resolu is not None else code
    elif code is not None:
        # The label must come from the active layout: the ANSI constant name would say
        # "1" where the French keyboard produces "&".
        key = _keyboard.label(code, mods) or labels.get(code, f"touche-{code}")
    else:
        return None
    return {"combo": render_modifiers(mods) + key, "mods": mods, "code": code}


def load_connus():
    """Identifications established outside Apple's tables, with their source."""
    chemin = Path(__file__).parent.parent / "data" / "known-shortcuts.json"
    if not chemin.exists():
        return {}
    return json.loads(chemin.read_text(encoding="utf-8")).get("connus", {})


def build():
    reference = load_reference()
    connus = load_connus()
    user_state = load_user_state()
    results = []

    for hotkey_id, entry in reference.items():
        state = user_state.get(hotkey_id)
        record = dict(entry)
        if state is None:
            # Absent from the user plist = never changed = factory setting, active.
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
        record["double"] = bool(state and state.get("double"))
        if record["double"] and touche and touche.get("libelle"):
            record["nom"] = f"{record['nom']} — {touche['libelle']}"
        record["defaut"] = entry["defaut"]["combo"] if entry["defaut"] else None
        results.append(record)

    # IDs present in the user's preferences but absent from Apple's table are kept as they
    # are: a raw identifier one can look up beats an invisible omission.
    for hotkey_id, state in user_state.items():
        if hotkey_id in reference:
            continue
        identifie = connus.get(str(hotkey_id))
        results.append({
            "id": hotkey_id,
            "categorie": "Non documenté par Apple",
            "categorie_en": "Undocumented",
            "source_identification": identifie["source"] if identifie else None,
            "identifiant_categorie": "unknown",
            "nom": (identifie["nom"] if identifie else f"Raccourci système #{hotkey_id}")
                   + (f" — {(state['combinaison'] or {}).get('libelle')}"
                      if state.get("double") else ""),
            "nom_en": f"Symbolic hotkey #{hotkey_id}",
            "defaut": None,
            "combinaison": (state["combinaison"] or {}).get("combo"),
            "mods": (state["combinaison"] or {}).get("mods", 0),
            "code": (state["combinaison"] or {}).get("code"),
            "double": state.get("double", False),
            "actif": state["actif"],
            "etat": "identifié hors table" if identifie else "non documenté",
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
