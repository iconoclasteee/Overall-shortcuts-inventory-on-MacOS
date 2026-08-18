"""Raccourcis globaux enregistrés par les outils tiers.

Ils comptent parce qu'ils **gagnent contre les menus d'application** : un menu ne
répond que lorsque son app est au premier plan, un raccourci global répond partout.
Les ignorer ferait rater à la détection de conflits précisément ceux qui se
manifestent en usage réel.

Chaque outil est lu dans sa propre configuration, sans jamais l'écrire. Seules les
clés décrivant un raccourci sont extraites : rien d'autre du fichier n'est parcouru
ni conservé.
"""

import json
import plistlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model import Binding, Keyboard, from_carbon, from_nsevent, render_modifiers

ROOT = Path(__file__).parent.parent

HOME = Path.home()


def _combo(keyboard, code, mods):
    label = keyboard.label(code, mods)
    return (render_modifiers(mods) + label) if label else None


def scan_alfred(keyboard):
    """Alfred garde ses raccourcis dans le bundle Alfred.alfredpreferences.

    Couche « global » : Alfred passe par RegisterEventHotKey (Carbon).
    """
    base = HOME / "Library/Application Support/Alfred/Alfred.alfredpreferences"
    # prefs.json indique un dossier synchronisé (Dropbox, iCloud) quand il y en a un.
    prefs = HOME / "Library/Application Support/Alfred/prefs.json"
    if prefs.exists():
        try:
            current = json.loads(prefs.read_text(encoding="utf-8")).get("current") or ""
            if current:
                candidate = Path(current).expanduser() / "Alfred.alfredpreferences"
                if candidate.exists():
                    base = candidate
        except (json.JSONDecodeError, OSError):
            pass
    if not base.exists():
        return []

    found = []

    def emit(action, spec):
        code, mask = spec.get("key"), spec.get("mod")
        # Un raccourci sur touche seule (F19 est courant chez Alfred) a un masque nul :
        # seul le code de touche absent signifie « non attribué ».
        if code is None:
            return
        mods = from_nsevent(mask)
        combo = _combo(keyboard, code, mods)
        if combo:
            found.append(Binding(mods=mods, combo=combo, action=action, source="outil",
                                 couche="global", portee="systeme", proprietaire="Alfred",
                                 bundle_id="com.runningwithcrayons.Alfred", code=code))

    for plist in (base / "preferences").rglob("*.plist"):
        try:
            data = plistlib.loads(plist.read_bytes())
        except Exception:
            continue
        for key, value in data.items():
            if isinstance(value, dict) and "key" in value and "mod" in value:
                emit(f"Alfred — {plist.parent.name} ({key})", value)

    # Déclencheurs de raccourci des workflows. Un workflow désactivé n'enregistre rien,
    # et un déclencheur sans « hotstring » n'a jamais reçu de combinaison.
    for info in (base / "workflows").glob("*/info.plist"):
        try:
            data = plistlib.loads(info.read_bytes())
        except Exception:
            continue
        if data.get("disabled"):
            continue
        name = data.get("name") or info.parent.name
        for obj in data.get("objects", []):
            if obj.get("type") != "alfred.workflow.trigger.hotkey":
                continue
            config = obj.get("config") or {}
            if not config.get("hotstring"):
                continue
            emit(f"Alfred — workflow « {name} »",
                 {"key": config.get("hotkey"), "mod": config.get("hotmod")})
    return found


def scan_keyboard_maestro(keyboard):
    """Keyboard Maestro : bibliothèque de macros, déclencheurs de type HotKey.

    Couche « capture » : son moteur intercepte via un CGEventTap, donc **avant** les
    raccourcis système. Un groupe ou une macro désactivé n'enregistre rien.
    """
    path = HOME / "Library/Application Support/Keyboard Maestro/Keyboard Maestro Macros.plist"
    if not path.exists():
        return []
    try:
        data = plistlib.loads(path.read_bytes())
    except Exception:
        return []

    found = []
    for group in data.get("MacroGroups", []):
        if group.get("IsActive") is False:
            continue
        for macro in group.get("Macros", []):
            if macro.get("IsActive") is False:
                continue
            name = macro.get("Name") or "(macro sans nom)"
            for trigger in macro.get("Triggers", []):
                if trigger.get("MacroTriggerType") != "HotKey":
                    continue
                code = trigger.get("KeyCode")
                if code is None:
                    continue
                mods = from_carbon(trigger.get("Modifiers"))
                combo = _combo(keyboard, code, mods)
                if not combo:
                    continue
                scope = group.get("Name") or ""
                found.append(Binding(
                    mods=mods, combo=combo,
                    action=f"Keyboard Maestro — {name}" + (f" [{scope}]" if scope else ""),
                    source="outil", couche="capture", portee="systeme",
                    proprietaire="Keyboard Maestro",
                    bundle_id="com.stairways.keyboardmaestro.engine", code=code))
    return found


# --- Balayage générique des préférences ------------------------------------------

# Trois conventions couvrent la plupart des apps qui enregistrent un raccourci global :
#   · un dictionnaire {keyCode, modifierFlags} — masque NSEvent (Rectangle Pro)
#   · une chaîne JSON sous une clé préfixée, avec carbonKeyCode/carbonModifiers —
#     c'est la bibliothèque KeyboardShortcuts, très répandue (ChatGPT, CleanShot X)
#   · une archive NSKeyedArchiver, que produit ShortcutRecorder (PopClip)
# Les lire génériquement plutôt qu'app par app fait apparaître les nouvelles sources
# sans qu'il faille les prévoir.
PREFIXES_JSON = ("KeyboardShortcuts_", "LAVA")


def _nom_app(bundle_id, catalogue):
    return catalogue.get(bundle_id, bundle_id)


def _catalogue():
    chemin = ROOT / "out" / "catalogue.json"
    if not chemin.exists():
        return {}
    return {a["bundleID"]: a["nom"] for a in json.loads(chemin.read_text(encoding="utf-8"))}


def _depuis_archive(donnees):
    """Convention 3 : raccourci sérialisé dans une archive NSKeyedArchiver.

    C'est ce que produit ShortcutRecorder, la bibliothèque de saisie de raccourcis
    la plus répandue (PopClip et d'autres). L'objet porte `keyCode` et
    `modifierFlags` comme la convention 1, mais chaque valeur est remplacée par un
    UID renvoyant vers la table `$objects` : sans déréférencement, on ne lit que des
    numéros d'emplacement. Le masque reste celui de NSEvent.
    """
    try:
        archive = plistlib.loads(donnees)
    except Exception:
        return None
    if not isinstance(archive, dict) or archive.get("$archiver") != "NSKeyedArchiver":
        return None
    objets = archive.get("$objects") or []

    def resoudre(reference):
        if isinstance(reference, plistlib.UID):
            indice = reference.data
            return objets[indice] if 0 <= indice < len(objets) else None
        return reference

    for objet in objets:
        if not isinstance(objet, dict) or "keyCode" not in objet:
            continue
        code = resoudre(objet["keyCode"])
        masque = resoudre(objet.get("modifierFlags"))
        if isinstance(code, int) and isinstance(masque, int):
            return code, masque
    return None


def scan_preferences(keyboard, ignorer=()):
    """Raccourcis globaux déclarés dans les préférences, toutes apps confondues."""
    # Un fichier de préférences survit à la désinstallation de son app. Sans ce
    # recoupement avec les apps réellement installées, on attribuerait des raccourcis
    # actifs à un logiciel absent — vu ici avec com.openai.chat, dont les prefs
    # traînent alors que l'app installée est com.openai.codex.
    catalogue = _catalogue()
    orphelins = set()
    found = []

    def ajouter(bundle_id, action, code, mods):
        if catalogue and bundle_id not in catalogue:
            orphelins.add(bundle_id)
            return
        combo = _combo(keyboard, code, mods)
        if not combo:
            return
        nom = _nom_app(bundle_id, catalogue)
        found.append(Binding(
            mods=mods, combo=combo, action=f"{nom} — {action}", source="outil",
            couche="global", portee="systeme", proprietaire=nom,
            bundle_id=bundle_id, code=code))

    for chemin in sorted((HOME / "Library/Preferences").glob("*.plist")):
        bundle_id = chemin.stem
        if any(bundle_id.startswith(prefixe) for prefixe in ignorer):
            continue
        try:
            prefs = plistlib.loads(chemin.read_bytes())
        except Exception:
            continue
        if not isinstance(prefs, dict):
            continue

        for cle, valeur in prefs.items():
            # Convention 1 : dictionnaire à masque NSEvent.
            if isinstance(valeur, dict) and "keyCode" in valeur:
                masque = valeur.get("modifierFlags")
                if valeur.get("keyCode") is not None and masque is not None:
                    ajouter(bundle_id, cle, valeur["keyCode"], from_nsevent(masque))
                continue
            # Convention 3 : archive NSKeyedArchiver. Testée avant la convention 2,
            # qui accepte elle aussi des octets : on ne retient la clé ici que si
            # l'archive livre vraiment un raccourci, sinon elle poursuit sa route.
            if isinstance(valeur, bytes):
                archive = _depuis_archive(valeur)
                if archive:
                    code, masque = archive
                    ajouter(bundle_id, cle, code, from_nsevent(masque))
                    continue
            # Convention 2 : JSON sous clé préfixée, masques Carbon.
            if not any(cle.startswith(prefixe) for prefixe in PREFIXES_JSON):
                continue
            brut = valeur if isinstance(valeur, (str, bytes)) else None
            if brut is None:
                continue
            try:
                spec = json.loads(brut)
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                continue
            code = spec.get("carbonKeyCode", spec.get("carbonKey"))
            if code is None:
                continue
            action = cle
            for prefixe in PREFIXES_JSON:
                action = action.removeprefix(prefixe)
            ajouter(bundle_id, action, code, from_carbon(spec.get("carbonModifiers")))

    if orphelins:
        print(f"  ℹ️  {len(orphelins)} domaines de préférences sans app installée, "
              f"ignorés : {', '.join(sorted(orphelins))}")
    return found


def scan_all(keyboard=None):
    keyboard = keyboard or Keyboard()
    # Alfred et Keyboard Maestro ont des formats qui leur sont propres ; tout le reste
    # passe par le balayage générique, y compris les apps qu'on n'a pas prévues.
    return (scan_alfred(keyboard) + scan_keyboard_maestro(keyboard)
            + scan_preferences(keyboard,
                               ignorer=("com.runningwithcrayons.Alfred",
                                        "com.stairways.keyboardmaestro")))


if __name__ == "__main__":
    from collections import Counter
    tout = scan_all()
    print(Counter(b.proprietaire for b in tout).most_common(), "\n")
    for binding in sorted(tout, key=lambda b: (b.proprietaire, b.combo)):
        print(f"{binding.couche:8} {binding.combo:12} {binding.action}")
