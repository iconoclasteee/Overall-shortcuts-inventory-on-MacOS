"""Assemble le rapport Markdown final.

Trois entrées : les raccourcis système (out/system-shortcuts.json), les raccourcis
moissonnés app par app (out/apps/*.json), et un fichier curé de descriptions
(data/app-descriptions.json) qui sert aussi à corriger le classement d'une app.

Le classement par défaut vient de `LSApplicationCategoryType`, déclaré par l'éditeur
dans l'app elle-même : factuel et vérifiable. Il est parfois grossier — d'où la
possibilité de le surcharger explicitement plutôt que de deviner à la place d'Apple.
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

# Ordre canonique des modificateurs dans la notation Apple.
AX_MODIFIERS = [(0x04, "⌃"), (0x02, "⌥"), (0x01, "⇧")]
NO_COMMAND = 0x08


def render_shortcut(entry, glyphs):
    """Rend un raccourci AX en notation lisible (⇧⌘K)."""
    mods = "".join(sym for bit, sym in AX_MODIFIERS if entry["modificateurs"] & bit)
    # Dans les menus AX, Command est implicite sauf si le bit 0x08 l'exclut
    # explicitement (cas des raccourcis à touche F seule, par exemple).
    if not entry["modificateurs"] & NO_COMMAND:
        mods += "⌘"

    char = entry.get("caractere") or ""
    if char and char.isprintable() and char.strip():
        key = char.upper() if len(char) == 1 else char
    elif entry.get("glyphe"):
        key = glyphs.get(entry["glyphe"], f"glyphe-{entry['glyphe']}")
    elif char:
        key = repr(char)  # caractère de contrôle sans glyphe : on montre le brut
    else:
        return None
    return mods + key


# Syntaxe des équivalents clavier Cocoa, telle qu'écrite dans NSUserKeyEquivalents.
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


def load_overrides(bundle_id):
    """Raccourcis redéfinis par l'utilisateur pour une app (Réglages → Clavier).

    Ils vivent dans les préférences de l'app, indexés par *titre* d'élément de menu —
    c'est donc le titre qui sert de clé de jointure avec ce que l'accessibilité renvoie.
    """
    result = subprocess.run(
        ["defaults", "read", bundle_id, "NSUserKeyEquivalents"],
        capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    # `defaults read` sort de l'ancien format texte ; le relire en plist est plus sûr
    # que de l'analyser à la main.
    export = subprocess.run(["defaults", "export", bundle_id, "-"], capture_output=True)
    if export.returncode != 0 or not export.stdout:
        return {}
    import plistlib
    try:
        prefs = plistlib.loads(export.stdout)
    except Exception:
        return {}
    return {normalise_title(title): (title, parse_cocoa_key_equivalent(value))
            for title, value in (prefs.get("NSUserKeyEquivalents") or {}).items()}


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
    path = ROOT / "data" / "app-descriptions.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def escape(text):
    """Neutralise les caractères qui casseraient une cellule de tableau Markdown."""
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def build_report():
    glyphs = glyph_labels()
    system = json.loads((ROOT / "out" / "system-shortcuts.json").read_text(encoding="utf-8"))
    apps = load_apps()
    descriptions = load_descriptions()

    harvested = [a for a in apps if a["statut"] == "ok" and a["raccourcis"]]
    failed = [a for a in apps if a not in harvested]
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
                    combo = render_shortcut(entry, glyphs)
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
                # Une redéfinition sans élément de menu correspondant est signalée plutôt
                # qu'ignorée : c'est souvent un titre qui ne colle plus (app traduite,
                # commande renommée), donc un raccourci qui ne fonctionne plus.
                orphans = [overrides[k] for k in overrides if k not in matched]
                if orphans:
                    lines += ["> ⚠️ Raccourcis redéfinis sans commande de menu "
                              "correspondante (probablement inactifs) : "
                              + ", ".join(f"`{combo}` → « {title} »"
                                          for title, combo in sorted(orphans)), ""]

    if failed:
        lines += ["---", "", "## 3. Applications non lisibles", "",
                  "| Application | Statut | Raison |", "|---|---|---|"]
        for app in sorted(failed, key=lambda a: a["nom"].lower()):
            lines.append(f"| {escape(app['nom'])} | {app['statut']} | "
                         f"{escape(app.get('detail') or '—')} |")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        APPS_DIR = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "raccourcis-macos.md"
    out.write_text(build_report(), encoding="utf-8")
    print(f"✅ {out}")
