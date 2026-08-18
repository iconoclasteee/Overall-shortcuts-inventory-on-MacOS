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
from tables import keycode_labels
from model import Keyboard, from_nsevent, render_modifiers, SHIFT

APPEX = Path(
    "/System/Library/ExtensionKit/Extensions/KeyboardSettings.appex/Contents/Resources"
)
NO_CHAR = 65535  # sentinelle Apple : "pas de caractère, utiliser le code de touche"

# Certains raccourcis système ne sont pas une combinaison mais une **double frappe**
# sur un modificateur seul — la dictée en est l'exemple courant. Apple les stocke avec
# `type: "modifier"` et un masque qui distingue la touche gauche de la droite.
#
# Les bits de côté sont ceux d'IOKit (`NX_DEVICELCMDKEYMASK` = 8,
# `NX_DEVICERCMDKEYMASK` = 16) et les libellés viennent du panneau Clavier de macOS,
# via `load_double_labels`. Les valeurs numériques sont ici en clair, avec le nom de
# la constante correspondante, plutôt que relues d'un second BridgeSupport pour cinq
# entrées.
MODIFIER_DOUBLE = [
    # (bit de modificateur NSEvent, bit de côté IOKit ou None, clé de libellé, symbole)
    (0x100000, 8,    "DoubleTapCommandLeft",  "⌘"),
    (0x100000, 16,   "DoubleTapCommandRight", "⌘"),
    (0x100000, None, "DoubleTapCommand",      "⌘"),
    (0x040000, None, "DoubleTapControl",      "⌃"),
    (0x800000, None, "DoubleTapFn",           "fn"),
]


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

    # Apple range les raccourcis de bureaux dans un second fichier, à plat. Sans lui,
    # « Passer au Bureau 1 » et ses quinze voisins ressortent en « non documenté ».
    spaces_path = APPEX / "DefaultSpacesShortcuts.xml"
    if spaces_path.exists():
        cat_fr, cat_en = translate("DO_NOT_LOCALIZE: Mission Control")
        walk({"elements": plistlib.loads(spaces_path.read_bytes())},
             cat_fr, cat_en, "expose", [])

    return entries


def load_double_labels(lang="fr"):
    """Libellés des doubles frappes, tels que les affiche le panneau Clavier."""
    path = APPEX / "Localizable.loctable"
    if not path.exists():
        return {}
    table = plistlib.loads(path.read_bytes())
    return table.get(lang) or table.get("en") or {}


def _double_tap(mask, labels):
    """Décrit une double frappe à partir de son masque, ou None si le masque
    ne correspond à aucun modificateur connu."""
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
    """{id: (charKey, key, modifier)} — les valeurs brutes des tables d'Apple.

    Nécessaire pour réécrire une entrée dans `com.apple.symbolichotkeys` au format
    qu'attend macOS, sans inventer la combinaison d'usine.
    """
    out = {}

    def walk(node):
        for element in node.get("elements", []):
            for id_key in ("sybmolichotkey", "prefs_sybmolichotkey", "slow_sybmolichotkey"):
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
    """Lit com.apple.symbolichotkeys via `defaults` (format plist XML)."""
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
        resolu, besoin_maj = _keyboard.resoudre(chr(char_code))
        if besoin_maj:
            mods |= SHIFT
        key = chr(char_code).upper()
        # Le caractère prime sur le code de touche. La table d'Apple stocke des codes
        # de clavier ANSI : pour ⌘M elle donne 46, qui sur AZERTY produit « , ».
        # macOS déclenche sur la touche portant réellement le M, donc on remonte au
        # code par le caractère, dans la disposition active.
        code = resolu if resolu is not None else code
    elif code is not None:
        # Le libellé doit venir de la disposition active : le nom de constante ANSI
        # dirait « 1 » là où le clavier français produit « & ».
        key = _keyboard.label(code, mods) or labels.get(code, f"touche-{code}")
    else:
        return None
    return {"combo": render_modifiers(mods) + key, "mods": mods, "code": code}


def load_connus():
    """Identifications établies hors des tables d'Apple, avec leur source."""
    chemin = Path(__file__).parent.parent / "data" / "raccourcis-connus.json"
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
        record["double"] = bool(state and state.get("double"))
        if record["double"] and touche and touche.get("libelle"):
            record["nom"] = f"{record['nom']} — {touche['libelle']}"
        record["defaut"] = entry["defaut"]["combo"] if entry["defaut"] else None
        results.append(record)

    # Les IDs présents chez l'utilisateur mais absents de la table Apple sont conservés
    # tels quels : un identifiant brut consultable vaut mieux qu'une omission invisible.
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
