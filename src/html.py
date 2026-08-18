"""Rendu HTML de l'index — un fichier autonome, trois vues.

Parti pris visuel : le sujet, c'est le clavier. Les combinaisons sont donc rendues
comme des touches physiques, et l'élément signature est **la pile d'interception** —
une frappe descend les étages (pilote, capture, système, global, menu) et le premier
qui la réclame l'avale. C'est le mécanisme réel, et c'est ce qui rend « qui gagne ? »
lisible d'un coup d'œil au lieu d'être une phrase à décrypter.
"""

import json
import platform
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent

ORDRE_COUCHES = ["pilote", "capture", "systeme", "global", "autre", "menu"]
NOMS_COUCHES = {
    "pilote": "Pilote", "capture": "Capture", "systeme": "Système",
    "global": "Global", "autre": "Autre", "menu": "Menu",
}

CSS = """
:root {
  --alu: #DAD8D3; --plaque: #F4F3F0; --creux: #C3C0B9; --encre: #16181C;
  --sourdine: #6E7078; --petrol: #0B6E6E; --vermillon: #B8352A;
  --touche-haut: #FBFAF8; --touche-bas: #D8D5CE; --ombre: rgba(22,24,28,.18);
  --display: "Space Grotesk", "Avenir Next Condensed", system-ui, sans-serif;
  --corps: "IBM Plex Sans", -apple-system, system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --alu: #131519; --plaque: #1C1F25; --creux: #2E323A; --encre: #E8E7E3;
    --sourdine: #94979F; --petrol: #4FD1C5; --vermillon: #F0776A;
    --touche-haut: #333842; --touche-bas: #1E2128; --ombre: rgba(0,0,0,.5);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--alu); color: var(--encre);
  font-family: var(--corps); font-size: 15px; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.enveloppe { max-width: 1100px; margin: 0 auto; padding: 0 24px 96px; }

/* — En-tête : la thèse, pas un bandeau décoratif — */
header { padding: 56px 0 28px; border-bottom: 2px solid var(--encre); }
.eyebrow {
  font-family: var(--mono); font-size: 11px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--sourdine); margin: 0 0 14px;
}
h1 {
  font-family: var(--display); font-size: clamp(38px, 7vw, 68px); font-weight: 700;
  letter-spacing: -.03em; line-height: .95; margin: 0 0 18px;
}
h1 em { font-style: normal; color: var(--petrol); }
.chiffres { display: flex; flex-wrap: wrap; gap: 28px; margin-top: 22px; }
.chiffre b {
  font-family: var(--display); font-size: 30px; font-weight: 700;
  display: block; line-height: 1;
}
.chiffre span {
  font-family: var(--mono); font-size: 11px; letter-spacing: .08em;
  text-transform: uppercase; color: var(--sourdine);
}
.chiffre.alerte b { color: var(--vermillon); }

/* — Onglets — */
nav { display: flex; gap: 4px; margin: 0 0 28px; border-bottom: 1px solid var(--creux); }
nav button {
  font-family: var(--display); font-size: 15px; font-weight: 600; letter-spacing: -.01em;
  background: none; border: 0; border-bottom: 3px solid transparent;
  padding: 16px 18px; color: var(--sourdine); cursor: pointer;
}
nav button[aria-selected="true"] { color: var(--encre); border-bottom-color: var(--petrol); }
nav button:hover { color: var(--encre); }
nav button:focus-visible, input:focus-visible, select:focus-visible,
.ligne:focus-visible { outline: 2px solid var(--petrol); outline-offset: 3px; }

/* — Touches — */
.combo { display: inline-flex; gap: 3px; align-items: center; }
.cap {
  font-family: var(--mono); font-size: 13px; font-weight: 500; line-height: 1;
  min-width: 26px; padding: 7px 6px; text-align: center;
  background: linear-gradient(var(--touche-haut), var(--touche-bas));
  border: 1px solid var(--creux); border-radius: 5px;
  box-shadow: 0 1.5px 0 var(--ombre); white-space: nowrap;
}
.cap.large { padding-left: 10px; padding-right: 10px; }

/* — Pile d'interception : l'élément signature — */
.pile { display: grid; gap: 2px; font-family: var(--mono); font-size: 11px; }
.etage {
  display: grid; grid-template-columns: 62px 10px 1fr; align-items: center;
  gap: 8px; padding: 3px 0; color: var(--sourdine);
}
.etage .nom { text-align: right; letter-spacing: .04em; }
.etage .puce {
  width: 9px; height: 9px; border-radius: 50%; border: 1px solid var(--creux);
}
.etage.occupe { color: var(--encre); }
.etage.occupe .puce { background: var(--sourdine); border-color: var(--sourdine); }
.etage.gagne { color: var(--petrol); font-weight: 600; }
.etage.gagne .puce { background: var(--petrol); border-color: var(--petrol);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--petrol) 22%, transparent); }

/* — Listes — */
.ligne {
  display: grid; grid-template-columns: 190px 1fr; gap: 24px; align-items: start;
  padding: 18px 0; border-bottom: 1px solid var(--creux); width: 100%;
  background: none; border-left: 0; border-right: 0; border-top: 0;
  text-align: left; font: inherit; color: inherit; cursor: pointer;
}
.ligne:hover { background: var(--plaque); }
.ligne[aria-expanded="true"] { background: var(--plaque); }
.conflit .titre { color: var(--vermillon); }
.titre { font-family: var(--display); font-weight: 600; font-size: 16px; margin: 0 0 4px; }
.sous { color: var(--sourdine); font-size: 13.5px; margin: 0; }
.detail { padding: 4px 0 26px; border-bottom: 1px solid var(--creux); }
.usages { list-style: none; margin: 14px 0 0; padding: 0; }
.usages li {
  display: grid; grid-template-columns: 84px 150px 1fr; gap: 14px;
  padding: 7px 0; font-size: 13.5px; border-top: 1px dotted var(--creux);
}
.usages .couche {
  font-family: var(--mono); font-size: 10.5px; letter-spacing: .06em;
  text-transform: uppercase; color: var(--sourdine); padding-top: 3px;
}
.usages .qui { font-weight: 600; }
.usages li.inactif { opacity: .5; }
.verdict {
  font-size: 14px; margin: 14px 0 0; padding: 12px 14px;
  background: var(--plaque); border-left: 3px solid var(--petrol);
}
.conflit-detail .verdict { border-left-color: var(--vermillon); }

/* — Contrôles — */
.controles { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
input[type="search"], select {
  font: inherit; font-size: 14px; padding: 10px 13px; color: var(--encre);
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 7px;
}
input[type="search"] { flex: 1; min-width: 220px; }
.groupe-portee { margin: 34px 0 0; }
.groupe-portee h3 {
  font-family: var(--display); font-size: 13px; letter-spacing: .06em;
  text-transform: uppercase; color: var(--sourdine); margin: 0 0 2px;
  padding-bottom: 8px; border-bottom: 1px solid var(--creux);
}
.groupe-portee .pourquoi { font-size: 13px; color: var(--sourdine); margin: 8px 0 0; }
.vide { color: var(--sourdine); font-size: 14px; padding: 40px 0; }
footer {
  margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--creux);
  font-size: 12.5px; color: var(--sourdine);
}
[hidden] { display: none !important; }
@media (max-width: 720px) {
  .ligne { grid-template-columns: 1fr; gap: 10px; }
  .usages li { grid-template-columns: 1fr; gap: 2px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

JS = """
const D = DONNEES;
const ORDRE = ORDRE_COUCHES_JS;
const NOMS = NOMS_COUCHES_JS;

const caps = (combo) => {
  const mods = [...combo].filter(c => "⌃⌥⇧⌘".includes(c));
  const reste = [...combo].filter(c => !"⌃⌥⇧⌘".includes(c)).join("");
  return [...mods.map(m => `<span class="cap">${m}</span>`),
          reste ? `<span class="cap${reste.length > 1 ? " large" : ""}">${esc(reste)}</span>` : ""
         ].join("");
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* La pile : un étage par couche, occupé si un raccourci s'y accroche.
   L'étage gagnant est celui, le plus haut dans l'ordre, qui est occupé. */
function pile(usages) {
  const occupees = new Set(usages.filter(u => u.actif).map(u => u.couche));
  const gagnante = ORDRE.find(c => occupees.has(c));
  return `<div class="pile">` + ORDRE.map(c => {
    const cls = c === gagnante ? "etage occupe gagne" : occupees.has(c) ? "etage occupe" : "etage";
    const qui = [...new Set(usages.filter(u => u.couche === c && u.actif).map(u => u.proprietaire))];
    return `<div class="${cls}"><span class="nom">${NOMS[c]}</span>`
         + `<span class="puce"></span><span>${esc(qui.join(", "))}</span></div>`;
  }).join("") + `</div>`;
}

const listeUsages = (usages) => `<ul class="usages">` + usages.map(u =>
  `<li class="${u.actif ? "" : "inactif"}"><span class="couche">${NOMS[u.couche]}</span>`
  + `<span class="qui">${esc(u.proprietaire)}</span>`
  + `<span>${esc(u.action)}${u.detail ? ` <em>— ${esc(u.detail)}</em>` : ""}`
  + `${u.actif ? "" : " — désactivé"}</span></li>`).join("") + `</ul>`;

function ligne(c, i, prefixe) {
  const nb = c.usages.filter(u => u.actif).length;
  return `<button class="ligne ${c.conflit ? "conflit" : ""}" aria-expanded="false"
      data-cible="${prefixe}-${i}">
      <span class="combo">${caps(c.combo)}</span>
      <span><span class="titre">${esc(c.usages[0].action)}</span>
      <span class="sous">${esc(c.usages[0].proprietaire)}${nb > 1 ? ` et ${nb - 1} autre${nb > 2 ? "s" : ""}` : ""}</span></span>
    </button>
    <div class="detail ${c.conflit ? "conflit-detail" : ""}" id="${prefixe}-${i}" hidden>
      ${pile(c.usages)}
      <p class="verdict">${esc(c.arbitrage.texte)}</p>
      ${listeUsages(c.usages)}
    </div>`;
}

function rendreConflits() {
  const conflits = D.combinaisons.filter(c => c.conflit);
  document.getElementById("vue-conflits").innerHTML = conflits.length
    ? conflits.map((c, i) => ligne(c, i, "cf")).join("")
    : `<p class="vide">Aucun conflit. Chaque combinaison n'a qu'un seul preneur.</p>`;
}

function rendreCombinaisons() {
  const q = document.getElementById("recherche").value.trim().toLowerCase();
  const liste = D.combinaisons.filter(c =>
    !q || c.combo.toLowerCase().includes(q)
       || c.usages.some(u => (u.action + " " + u.proprietaire).toLowerCase().includes(q)));
  document.getElementById("vue-combinaisons").innerHTML = liste.length
    ? liste.slice(0, 400).map((c, i) => ligne(c, i, "cb")).join("")
      + (liste.length > 400 ? `<p class="vide">${liste.length - 400} autres — affine la recherche.</p>` : "")
    : `<p class="vide">Rien pour « ${esc(q)} ».</p>`;
}

/* Vue par app : ses propres raccourcis, puis les raccourcis globaux, rangés
   selon qu'ils agissent dans l'app, sur elle, ou à côté d'elle. */
function rendreApp() {
  const id = document.getElementById("choix-app").value;
  const app = D.apps.find(a => a.bundleID === id);
  const propres = [], parPortee = { app: [], app_externe: [], systeme: [], inconnu: [] };

  for (const c of D.combinaisons) {
    for (const u of c.usages) {
      if (!u.actif) continue;
      if (u.couche === "menu") { if (u.bundle_id === id) propres.push({ c, u }); }
      else if (parPortee[u.portee]) parPortee[u.portee].push({ c, u });
    }
  }
  const bloc = (titre, pourquoi, items) => !items.length ? "" :
    `<section class="groupe-portee"><h3>${esc(titre)} · ${items.length}</h3>
     <p class="pourquoi">${esc(pourquoi)}</p>` + items.map(({ c, u }) =>
      `<div class="ligne" style="cursor:default"><span class="combo">${caps(u.combo)}</span>
       <span><span class="titre">${esc(u.action)}</span>
       <span class="sous">${esc(u.proprietaire)}</span></span></div>`).join("") + `</section>`;

  document.getElementById("vue-app").innerHTML =
    (app && app.statut !== "ok"
      ? `<p class="vide">${esc(app.nom)} n'a pas pu être lue : ${esc(app.detail || app.statut)}.</p>` : "")
    + bloc(`Raccourcis de ${app ? app.nom : ""}`,
           "Ses propres commandes de menu. Actives seulement quand elle est au premier plan.", propres)
    + bloc(D.libelles_portee.app, "Raccourcis macOS qui agissent sur l'interface de l'app.", parPortee.app)
    + bloc(D.libelles_portee.app_externe,
           "Agissent sur la fenêtre de l'app ou par-dessus elle, sans toucher son interface.", parPortee.app_externe)
    + bloc(D.libelles_portee.systeme,
           "Fonctionnent pendant que l'app est ouverte, mais ne la concernent pas.", parPortee.systeme)
    + bloc(D.libelles_portee.inconnu, "Portée non déterminée.", parPortee.inconnu);
}

document.addEventListener("click", (e) => {
  const bouton = e.target.closest(".ligne[data-cible]");
  if (!bouton) return;
  const detail = document.getElementById(bouton.dataset.cible);
  const ouvert = bouton.getAttribute("aria-expanded") === "true";
  bouton.setAttribute("aria-expanded", String(!ouvert));
  detail.hidden = ouvert;
});

document.querySelectorAll("nav button").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll("nav button").forEach(x =>
    x.setAttribute("aria-selected", String(x === b)));
  document.querySelectorAll("main > section").forEach(s =>
    s.hidden = s.id !== "onglet-" + b.dataset.vue);
}));

document.getElementById("recherche").addEventListener("input", rendreCombinaisons);
document.getElementById("choix-app").addEventListener("change", rendreApp);
rendreConflits(); rendreCombinaisons(); rendreApp();
"""


def build(index_path):
    data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    lisibles = [a for a in data["apps"] if a["statut"] == "ok"]
    conflits = sum(1 for c in data["combinaisons"] if c["conflit"])
    machine = subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip()

    options = "\n".join(
        f'<option value="{a["bundleID"]}">{a["nom"]}</option>'
        for a in sorted(lisibles, key=lambda a: a["nom"].lower()))

    # "</" doit être neutralisé : la séquence fermerait la balise script depuis
    # l'intérieur d'une chaîne JSON si un nom de commande la contenait.
    charge = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    script = (JS.replace("DONNEES", charge)
                .replace("ORDRE_COUCHES_JS", json.dumps(ORDRE_COUCHES))
                .replace("NOMS_COUCHES_JS", json.dumps(NOMS_COUCHES, ensure_ascii=False)))

    return f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Raccourcis · {machine}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="enveloppe">
<header>
  <p class="eyebrow">{machine} · macOS {platform.mac_ver()[0]} · {date.today().isoformat()}</p>
  <h1>Une frappe descend<br>la pile. <em>Le premier<br>étage la garde.</em></h1>
  <div class="chiffres">
    <div class="chiffre"><b>{len(data["combinaisons"])}</b><span>combinaisons</span></div>
    <div class="chiffre {"alerte" if conflits else ""}"><b>{conflits}</b><span>en conflit</span></div>
    <div class="chiffre"><b>{len(lisibles)}</b><span>applications lues</span></div>
  </div>
</header>
<nav>
  <button data-vue="conflits" aria-selected="true">Conflits</button>
  <button data-vue="combinaisons" aria-selected="false">Par combinaison</button>
  <button data-vue="app" aria-selected="false">Par application</button>
</nav>
<main>
  <section id="onglet-conflits"><div id="vue-conflits"></div></section>
  <section id="onglet-combinaisons" hidden>
    <div class="controles">
      <input type="search" id="recherche" placeholder="Cherche une touche, une commande ou une app — ⌘D, copier, Safari">
    </div>
    <div id="vue-combinaisons"></div>
  </section>
  <section id="onglet-app" hidden>
    <div class="controles"><select id="choix-app">{options}</select></div>
    <div id="vue-app"></div>
  </section>
</main>
<footer>
  Les raccourcis d'une app ne vivent que dans sa barre de menu : ils sont lus app par app.
  Une app lue sans document ouvert expose moins de commandes qu'en usage réel.
  L'ordre des étages est fiable, mais deux outils accrochés au même étage sont
  départagés par leur ordre d'enregistrement, que rien sur le disque ne consigne.
</footer>
</div><script>{script}</script></body></html>"""


if __name__ == "__main__":
    index = sys.argv[1] if len(sys.argv) > 1 else ROOT / "out" / "index.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "raccourcis.html"
    out.write_text(build(index), encoding="utf-8")
    print(f"✅ {out}  ({out.stat().st_size // 1024} Ko)")
