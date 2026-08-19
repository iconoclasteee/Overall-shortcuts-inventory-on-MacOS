"""Assembles the final Markdown report.

Three inputs: system shortcuts (out/system-shortcuts.json), the shortcuts harvested app by
app (out/apps/*.json), and the app descriptions, which also serve to correct an app's
classification.

Descriptions come from two files: `data/app-descriptions.json`, the versioned seed that
describes only apps shipped with macOS, and `out/app-descriptions.json`, machine-specific
and not versioned — that is where installed apps get filled in, since enumerating them has
no place in a public repository. The second overrides the first.

The default classification comes from `LSApplicationCategoryType`, declared by the vendor
inside the app itself: factual and verifiable. It is sometimes coarse — hence the ability
to override it explicitly rather than guessing on Apple's behalf.
"""

import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tables import glyph_labels
from model import SHIFT, Keyboard, from_ax, render_modifiers
from overrides import load as load_overrides, normalise_title

ROOT = Path(__file__).parent.parent

CATEGORIES = {
    "public.app-category.productivity": "Productivité",
    "public.app-category.utilities": "Utilitaires",
    "public.app-category.developer-tools": "Outils de développement",
    "public.app-category.music": "Musique & audio",
    "public.app-category.video": "Vidéo",
    "public.app-category.photography": "Photo",
    "public.app-category.graphics-design": "Graphisme & design",
    "public.app-category.social-networking": "Réseaux sociaux & communication",
    "public.app-category.business": "Bureautique & gestion",
    "public.app-category.education": "Éducation",
    "public.app-category.reference": "Référence & documentation",
    "public.app-category.entertainment": "Divertissement",
    "public.app-category.news": "Actualités",
    "public.app-category.books": "Lecture",
    "public.app-category.travel": "Voyage",
    "public.app-category.healthcare-fitness": "Santé & forme",
    "public.app-category.games": "Jeux",
    "public.app-category.board-games": "Jeux",
    "public.app-category.action-games": "Jeux",
    "public.app-category.adventure-games": "Jeux",
}
UNCLASSIFIED = "Non classées (aucune catégorie déclarée)"

def render_shortcut(entry, glyphs, keyboard=None):
    """Renders an AX shortcut in readable notation (⇧⌘K).

    Modifier decoding comes from the shared model: two implementations would eventually
    drift apart with nothing to flag it. The keyboard layout is involved for the same
    reason: on a French keyboard "?" is typed with Shift, and writing it "⌘?" would
    describe a keystroke that triggers nothing.
    """
    bits = from_ax(entry["modificateurs"])
    char = entry.get("caractere") or ""
    if char and char.isprintable() and char.strip():
        if keyboard is not None:
            resolu, besoin_maj = keyboard.resoudre(char)
            if resolu is not None:
                if besoin_maj:
                    bits |= SHIFT
                return render_modifiers(bits) + keyboard.label(resolu, bits)
        key = char.upper() if len(char) == 1 else char
    elif entry.get("glyphe"):
        key = glyphs.get(entry["glyphe"], f"glyphe-{entry['glyphe']}")
    elif char:
        key = repr(char)  # caractère de contrôle sans glyphe : on montre le brut
    else:
        return None
    return render_modifiers(bits) + key


# Folder of application records. Overridden by the first command-line argument; the
# default value lets the script be called with no argument at all.
APPS_DIR = ROOT / "out" / "apps"


def load_apps():
    directory = APPS_DIR
    if not directory.exists():
        return []
    apps = []
    for path in sorted(directory.glob("*.json")):
        try:
            apps.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            print(f"⚠️  illisible, ignoré : {path.name}")
    return apps


def load_descriptions():
    """Versioned seed, then machine-specific descriptions that override it."""
    descriptions = {}
    for path in (ROOT / "data" / "app-descriptions.json",
                 ROOT / "out" / "app-descriptions.json"):
        if path.exists():
            descriptions.update(json.loads(path.read_text(encoding="utf-8")))
    return descriptions


def escape(text):
    """Neutralises the characters that would break a Markdown table cell."""
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def build_report():
    glyphs = glyph_labels()
    keyboard = Keyboard()
    system = json.loads((ROOT / "out" / "system-shortcuts.json").read_text(encoding="utf-8"))
    apps = load_apps()
    descriptions = load_descriptions()

    # Three distinct states: read with shortcuts, read with none, unreadable. Conflating
    # them made a background app with no menu look like a failure.
    harvested = [a for a in apps if a["statut"] == "ok" and a["raccourcis"]]
    sans_raccourci = [a for a in apps if a["statut"] == "ok" and not a["raccourcis"]]
    failed = [a for a in apps if a["statut"] != "ok"]
    total = sum(len(a["raccourcis"]) for a in harvested)

    machine = subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip()
    lines = [
        "# Inventaire des raccourcis clavier",
        "",
        f"**Machine :** {machine} · **macOS :** {platform.mac_ver()[0]} · "
        f"**Généré le :** {date.today().isoformat()}",
        "",
        f"{len(system)} raccourcis système · {total} raccourcis d'application "
        f"répartis sur {len(harvested)} apps"
        + (f" · {len(sans_raccourci)} apps sans aucun raccourci" if sans_raccourci else "")
        + (f" · {len(failed)} apps non lisibles" if failed else ""),
        "",
        "> **Portée.** Les raccourcis d'une app n'existent que dans sa barre de menu, "
        "construite en mémoire au lancement : ils sont lus app par app via l'API "
        "d'accessibilité. Pour les apps à documents, la barre de menu sans document "
        "ouvert est plus pauvre qu'avec — l'inventaire est alors partiel.",
        "",
        "---",
        "",
        "## 1. Raccourcis système",
        "",
    ]

    by_category = defaultdict(list)
    for entry in system:
        by_category[entry["categorie"]].append(entry)

    for category in sorted(by_category):
        lines += [f"### {category}", "", "| Raccourci | Action | État |", "|---|---|---|"]
        for entry in sorted(by_category[category], key=lambda e: e["nom"]):
            combo = entry["combinaison"] or "—"
            name = escape(entry["nom"])
            if entry.get("variante", "principal") != "principal":
                name += f" _(variante {entry['variante']})_"
            lines.append(f"| `{combo}` | {name} | {entry['etat']} |")
        lines.append("")

    lines += ["---", "", "## 2. Raccourcis par application", ""]

    if not harvested:
        lines += ["_Aucune app moissonnée pour l'instant._", ""]
    else:
        grouped = defaultdict(list)
        for app in harvested:
            meta = descriptions.get(app["bundleID"], {})
            category = meta.get("categorie") or CATEGORIES.get(app.get("categorie") or "", None)
            grouped[category or UNCLASSIFIED].append(app)

        for category in sorted(grouped, key=lambda c: (c == UNCLASSIFIED, c)):
            lines += [f"### {category}", ""]
            for app in sorted(grouped[category], key=lambda a: a["nom"].lower()):
                version = f" · v{app['version']}" if app.get("version") else ""
                lines.append(f"#### {app['nom']}{version} — {len(app['raccourcis'])} raccourcis")
                description = (descriptions.get(app["bundleID"], {}) or {}).get("description")
                lines += ["", f"_{description}_" if description
                          else "_Rôle non renseigné._", ""]
                if app["deja_lance"] is False and app["lance_par_nous"]:
                    lines += ["> Lue sans document ouvert : l'inventaire peut être "
                              "partiel pour cette app.", ""]
                overrides = load_overrides(app["bundleID"])
                matched = set()
                lines += ["| Raccourci | Commande |", "|---|---|"]
                seen = set()
                for entry in app["raccourcis"]:
                    combo = render_shortcut(entry, glyphs, keyboard)
                    if not combo:
                        continue
                    leaf = normalise_title(entry["chemin"].split(" > ")[-1])
                    suffix = ""
                    if leaf in overrides:
                        combo = overrides[leaf][1]
                        suffix = " _(redéfini par toi)_"
                        matched.add(leaf)
                    row = (combo, entry["chemin"])
                    if row in seen:
                        continue
                    seen.add(row)
                    lines.append(f"| `{combo}` | {escape(entry['chemin'])}{suffix} |")
                lines.append("")
                # A redefinition with no matching menu item is reported rather than
                # ignored: it usually means a title that no longer matches (translated app,
                # renamed command), and therefore a shortcut that no longer works.
                orphans = [(overrides[k][0], overrides[k][1])
                           for k in overrides if k not in matched]
                if orphans:
                    # Without a document open, part of the menu does not exist: a missing
                    # match there does not prove the shortcut is broken.
                    cause = ("sans correspondance dans le menu lu — mais cette app a été "
                             "lue sans document ouvert, donc la commande peut simplement "
                             "être absente à ce moment-là"
                             if app["lance_par_nous"]
                             else "sans commande de menu correspondante, donc probablement "
                                  "inactifs (titre renommé ou app traduite)")
                    lines += [f"> ⚠️ Raccourcis que tu as redéfinis, {cause} : "
                              + ", ".join(f"`{combo}` → « {title} »"
                                          for title, combo in sorted(orphans)), ""]

    if sans_raccourci:
        lines += ["---", "", "## 3. Applications sans aucun raccourci", "",
                  "_Lues sans erreur, mais leur barre de menu n'expose aucun raccourci._",
                  "", "| Application |", "|---|"]
        for app in sorted(sans_raccourci, key=lambda a: a["nom"].lower()):
            lines.append(f"| {escape(app['nom'])} |")
        lines.append("")

    if failed:
        lines += ["---", "", "## 4. Applications non lisibles", "",
                  "| Application | Statut | Raison |", "|---|---|---|"]
        for app in sorted(failed, key=lambda a: a["nom"].lower()):
            lines.append(f"| {escape(app['nom'])} | {app['statut']} | "
                         f"{escape(app.get('detail') or '—')} |")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        globals()["APPS_DIR"] = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "shortcuts.md"
    out.write_text(build_report(), encoding="utf-8")
    print(f"✅ {out}")
