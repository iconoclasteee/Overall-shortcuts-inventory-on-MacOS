"""Assemble le rapport Markdown final.

Trois entrées : les raccourcis système (out/system-shortcuts.json), les raccourcis
moissonnés app par app (out/apps/*.json), et les descriptions d'apps, qui servent
aussi à corriger le classement d'une app.

Les descriptions viennent de deux fichiers : `data/app-descriptions.json`, l'amorce
versionnée qui ne décrit que des apps livrées avec macOS, et `out/app-descriptions.json`,
propre à la machine et non versionné — c'est là que se remplissent les apps installées,
puisque leur énumération n'a pas sa place dans un dépôt public. Le second prime sur
la première.

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
from model import from_ax, render_modifiers
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

def render_shortcut(entry, glyphs):
    """Rend un raccourci AX en notation lisible (⇧⌘K).

    Le décodage des modificateurs vient du modèle commun : deux implémentations
    finiraient par diverger sans que rien ne le signale.
    """
    mods = render_modifiers(from_ax(entry["modificateurs"]))
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


# Dossier des fiches d'application. Surchargé par le premier argument de ligne de
# commande ; la valeur par défaut permet d'appeler le script sans argument.
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
    """Amorce versionnée, puis descriptions propres à la machine qui la surchargent."""
    descriptions = {}
    for path in (ROOT / "data" / "app-descriptions.json",
                 ROOT / "out" / "app-descriptions.json"):
        if path.exists():
            descriptions.update(json.loads(path.read_text(encoding="utf-8")))
    return descriptions


def escape(text):
    """Neutralise les caractères qui casseraient une cellule de tableau Markdown."""
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def build_report():
    glyphs = glyph_labels()
    system = json.loads((ROOT / "out" / "system-shortcuts.json").read_text(encoding="utf-8"))
    apps = load_apps()
    descriptions = load_descriptions()

    # Trois états distincts : lue avec des raccourcis, lue sans en avoir, illisible.
    # Les confondre faisait passer une app d'arrière-plan sans menu pour un échec.
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
                orphans = [(overrides[k][0], overrides[k][1])
                           for k in overrides if k not in matched]
                if orphans:
                    # Sans document ouvert, une partie du menu n'existe pas : l'absence
                    # de correspondance n'y prouve pas que le raccourci est cassé.
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
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "raccourcis.md"
    out.write_text(build_report(), encoding="utf-8")
    print(f"✅ {out}")
