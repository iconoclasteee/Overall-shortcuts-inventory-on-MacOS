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
        if code is None or not mask:
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


def scan_cleanshot(keyboard):
    """CleanShot X : ses raccourcis sont des blobs JSON dans ses préférences.

    Couche « global » : les champs `carbonKey`/`carbonModifiers` trahissent un
    enregistrement Carbon. Seules les clés `LAVA*` sont lues — rien d'autre du
    fichier de préférences n'est touché.
    """
    path = HOME / "Library/Preferences/pl.maketheweb.cleanshotx.plist"
    if not path.exists():
        return []
    try:
        data = plistlib.loads(path.read_bytes())
    except Exception:
        return []

    labels = {
        "LAVAtakeArea": "Capturer une zone", "LAVAtakeFullscreen": "Capturer l'écran",
        "LAVAtakeAllInOne": "Capture tout-en-un", "LAVAtakeOCR": "Reconnaissance de texte",
    }
    found = []
    for key, value in data.items():
        if not key.startswith("LAVA"):
            continue
        try:
            spec = json.loads(value if isinstance(value, (str, bytes)) else "")
        except (json.JSONDecodeError, TypeError):
            continue
        code = spec.get("carbonKey")
        if code is None:
            continue
        mods = from_carbon(spec.get("carbonModifiers"))
        combo = _combo(keyboard, code, mods)
        if combo:
            found.append(Binding(
                mods=mods, combo=combo,
                action=f"CleanShot X — {labels.get(key, key.removeprefix('LAVA'))}",
                source="outil", couche="global", portee="systeme",
                proprietaire="CleanShot X", bundle_id="pl.maketheweb.cleanshotx", code=code))
    return found


def scan_all(keyboard=None):
    keyboard = keyboard or Keyboard()
    return (scan_alfred(keyboard) + scan_keyboard_maestro(keyboard)
            + scan_cleanshot(keyboard))


if __name__ == "__main__":
    for binding in scan_all():
        print(f"{binding.couche:8} {binding.combo:12} {binding.action}")
