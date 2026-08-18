"""Rendu HTML de l'index — un fichier autonome, trois vues.

Parti pris visuel : le sujet, c'est le clavier. Les combinaisons sont donc rendues
comme des touches physiques, et l'élément signature est **la pile d'interception** —
une frappe descend les étages (pilote, capture, système, global, menu) et le premier
qui la réclame l'avale. C'est le mécanisme réel, et c'est ce qui rend « qui gagne ? »
lisible d'un coup d'œil au lieu d'être une phrase à décrypter.
"""

import html as html_std
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
.enveloppe { padding: 0 clamp(24px, 3vw, 56px) 96px; }

/* — En-tête : la thèse, pas un bandeau décoratif — */
header { padding: 30px 0 22px; border-bottom: 2px solid var(--encre); }
.eyebrow {
  font-family: var(--mono); font-size: 11px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--sourdine); margin: 0 0 14px;
}
h1 {
  font-family: var(--display); font-size: 30px; font-weight: 700;
  letter-spacing: -.02em; line-height: 1.1; margin: 0; white-space: nowrap;
}
header { display: grid; grid-template-columns: 1fr auto; gap: 48px; align-items: center; }
header .chiffres { justify-content: flex-end; margin-top: 0; }
h1 em { font-style: normal; color: var(--petrol); }
.chiffres { display: flex; flex-wrap: wrap; gap: 40px; margin-top: 22px; }
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
nav {
  display: flex; justify-content: space-between; align-items: center; gap: 28px;
  margin: 0 0 22px; border-bottom: 1px solid var(--creux);
}
.onglets { display: flex; gap: 4px; }
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
  display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 28px; align-items: start;
  padding: 18px 0; border-bottom: 1px solid var(--creux); width: 100%;
  background: none; border-left: 0; border-right: 0; border-top: 0;
  text-align: left; font: inherit; color: inherit; cursor: pointer;
}
.ligne:hover { background: var(--plaque); }
.ligne[aria-expanded="true"] { background: var(--plaque); }
.conflit .titre { color: var(--vermillon); }
.titre { font-family: var(--display); font-weight: 600; font-size: 16px; margin: 0 0 4px; }
.sous { color: var(--sourdine); font-size: 13.5px; margin: 0; }
.detail {
  display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 28px;
  padding: 4px 0 26px; border-bottom: 1px solid var(--creux);
}
.detail .pile { padding-top: 4px; }
.detail > .verdict, .detail > .usages { grid-column: 2; }
.usages { list-style: none; margin: 14px 0 0; padding: 0; }
.usages li {
  display: grid; grid-template-columns: 90px 190px minmax(0, 1fr); gap: 18px;
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
/* Deux natures de filtre : à gauche la combinaison de touches, à droite la recherche
   de libellé. Les séparer évite de les prendre pour un même réglage. */
.filtre {
  display: grid; grid-template-columns: minmax(0, max-content) minmax(220px, 1fr);
  gap: 12px 40px; margin: 0 0 28px; padding: 18px 20px; align-items: start;
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 10px;
}
.colonne-touches { display: grid; gap: 12px; }
.colonne-texte {
  display: grid; gap: 8px; justify-items: start; max-width: 400px;
  padding-left: 40px; border-left: 1px solid var(--creux);
}
.colonne-texte input { width: 100%; font-size: 14px; padding: 10px 13px; }
.colonne-texte .etiquette { width: auto; }
.rangee-filtre { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
/* Chercher un texte n'est pas filtrer une combinaison : la ligne est séparée pour
   qu'on ne prenne pas les deux pour un même réglage. */
/* Les touches de fonction occupent leur propre rangée : mêlées aux flèches et aux
   touches d'édition, elles formeraient un pavé de vingt boutons illisible. */
.rangees-touches { display: flex; flex-direction: column; gap: 6px; }
.etiquette {
  font-family: var(--mono); font-size: 10.5px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--sourdine); width: 104px; flex: none;
}
.capsules { display: flex; flex-wrap: wrap; gap: 5px; }
.capsules button {
  font-family: var(--mono); font-size: 13px; line-height: 1; min-width: 34px;
  padding: 8px 8px; cursor: pointer; color: var(--encre);
  background: linear-gradient(var(--touche-haut), var(--touche-bas));
  border: 1px solid var(--creux); border-radius: 5px;
  box-shadow: 0 1.5px 0 var(--ombre);
}
.capsules button[aria-pressed="true"] {
  background: var(--petrol); border-color: var(--petrol); color: var(--plaque);
  box-shadow: none;
}
.capsules button:focus-visible { outline: 2px solid var(--petrol); outline-offset: 2px; }
#touche-libre { width: 150px; flex: none; text-align: center; }
.combo-app { position: relative; width: 300px; flex: none; margin-bottom: 8px; }
.combo-app input {
  width: 100%; font-size: 14px; padding: 10px 13px;
  background: color-mix(in srgb, var(--petrol) 12%, var(--plaque));
  border: 1.5px solid var(--petrol); color: var(--encre);
}
.combo-app input::placeholder { color: color-mix(in srgb, var(--petrol) 75%, var(--sourdine)); }
#liste-app {
  position: absolute; z-index: 20; top: calc(100% + 4px); left: 0; right: 0;
  max-height: 340px; overflow-y: auto; margin: 0; padding: 5px; list-style: none;
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 8px;
  box-shadow: 0 12px 32px var(--ombre);
}
#liste-app li {
  padding: 8px 11px; border-radius: 5px; cursor: pointer; font-size: 14px;
  display: flex; justify-content: space-between; gap: 16px; align-items: baseline;
}
#liste-app li .compte {
  font-family: var(--mono); font-size: 11px; color: var(--sourdine); flex: none;
}
#liste-app li[aria-selected="true"], #liste-app li:hover {
  background: var(--petrol); color: var(--plaque);
}
#liste-app li[aria-selected="true"] .compte, #liste-app li:hover .compte { color: var(--plaque); }
#liste-app .aucun { color: var(--sourdine); cursor: default; }
#liste-app .aucun:hover { background: none; color: var(--sourdine); }
.lien {
  font: inherit; font-size: 13px; background: none; border: 0; padding: 0;
  color: var(--sourdine); text-decoration: underline; cursor: pointer;
}
.lien:hover { color: var(--encre); }
input[type="search"], input[type="text"] {
  font: inherit; font-size: 15px; padding: 12px 14px; color: var(--encre);
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 7px;
}
.filtre input { background: var(--alu); }
input[type="search"] { flex: 1; max-width: 560px; min-width: 260px; }
.groupe-portee { margin: 34px 0 0; }
.groupe-portee h3 {
  font-family: var(--display); font-size: 13px; letter-spacing: .06em;
  text-transform: uppercase; color: var(--sourdine); margin: 0 0 2px;
  padding-bottom: 8px; border-bottom: 1px solid var(--creux);
}
.groupe-portee .pourquoi { font-size: 13px; color: var(--sourdine); margin: 8px 0 0; }
.grille {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(430px, 1fr));
  column-gap: 52px;
}
.resultat {
  display: grid; grid-template-columns: 185px 1fr; gap: 20px; align-items: start;
  padding: 11px 0; border-bottom: 1px solid var(--creux);
}
.resultat .titre { font-size: 15px; }
.perdu {
  display: block; font-family: var(--mono); font-size: 11.5px; color: var(--sourdine);
  margin-top: 3px; padding-left: 11px; border-left: 2px solid var(--creux);
}
.segmente { display: flex; border: 1px solid var(--creux); border-radius: 7px; overflow: hidden; }
.segmente button {
  font: inherit; font-size: 13.5px; padding: 9px 15px; border: 0; cursor: pointer;
  background: var(--plaque); color: var(--sourdine);
}
.segmente button + button { border-left: 1px solid var(--creux); }
.segmente button[aria-selected="true"] { background: var(--petrol); color: var(--plaque); }
.segmente button:focus-visible { outline: 2px solid var(--petrol); outline-offset: 2px; }
.vide { color: var(--sourdine); font-size: 14px; padding: 40px 0; }
footer {
  margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--creux);
  font-size: 12.5px; color: var(--sourdine);
}
[hidden] { display: none !important; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

JS = """
const D = DONNEES;
const ORDRE = ORDRE_COUCHES_JS;
const NOMS = NOMS_COUCHES_JS;

const caps = (combo) => {
  // « fn » s'écrit sur deux caractères : il faut le retirer avant de parcourir le reste,
  // sinon il finirait collé à la touche principale sur une seule capsule.
  const mods = [];
  let reste = combo;
  if (reste.includes("fn")) { reste = reste.replace("fn", ""); }
  for (const c of [...reste]) if ("⌃⌥⇧⌘".includes(c)) mods.push(c);
  if (combo.includes("fn")) mods.push("fn");
  reste = [...reste].filter(c => !"⌃⌥⇧⌘".includes(c)).join("");
  return [...mods.map(m => `<span class="cap${m.length > 1 ? " large" : ""}">${m}</span>`),
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
  const f = etatFiltre();
  const conflits = D.combinaisons.filter(c => c.conflit && passe(f, c.combo, c.mods, c.usages));
  document.getElementById("vue-conflits").innerHTML = conflits.length
    ? conflits.map((c, i) => ligne(c, i, "cf")).join("")
    : `<p class="vide">Aucun conflit${f.actifs || f.touche || f.libre || f.texte
        ? " parmi ce que le filtre laisse passer" : ""}. `
      + `Chaque combinaison n'a qu'un seul preneur.</p>`;
}

/* Les modificateurs se cochent au lieu de se taper : presser ⌘⇧ dans un champ de
   recherche déclencherait le raccourci qu'on cherche justement à identifier. */
const MODS = MODS_BITS;
const toucheSeule = (combo) => combo.replace("fn", "").replace(/[⌃⌥⇧⌘]/g, "");

function etatFiltre() {
  const bits = [...document.querySelectorAll("#mods button[aria-pressed=true]")]
    .reduce((acc, b) => acc | Number(b.dataset.bit), 0);
  const actifs = document.querySelectorAll("#mods button[aria-pressed=true]").length;
  const touche = document.querySelector("#touches button[aria-pressed=true]");
  return {
    bits, actifs,
    touche: touche ? touche.dataset.touche : "",
    libre: document.getElementById("touche-libre").value.trim().toLowerCase(),
    texte: document.getElementById("recherche").value.trim().toLowerCase(),
  };
}

/* Le même filtre sert aux trois vues : une combinaison passe si elle satisfait
   tous les critères renseignés. Un critère vide ne filtre rien. */
function passe(f, combo, mods, usages) {
  if (f.actifs && mods !== f.bits) return false;
  const k = toucheSeule(combo);
  if (f.touche && k !== f.touche) return false;
  if (f.libre && k.toLowerCase() !== f.libre) return false;
  if (f.texte && !combo.toLowerCase().includes(f.texte)
      && !usages.some(u => (u.action + " " + u.proprietaire).toLowerCase().includes(f.texte)))
    return false;
  return true;
}

function rendreCombinaisons() {
  const f = etatFiltre();
  const liste = D.combinaisons.filter(c => passe(f, c.combo, c.mods, c.usages));
  const cible = document.getElementById("vue-combinaisons");
  if (!liste.length) {
    const quoi = [f.actifs ? "ces modificateurs" : "", f.touche || f.libre, f.texte ? `« ${esc(f.texte)} »` : ""]
      .filter(Boolean).join(" + ");
    cible.innerHTML = `<p class="vide">Aucune combinaison ${quoi ? "pour " + quoi : "trouvée"}. `
      + `Cette combinaison est donc libre.</p>`;
    return;
  }
  cible.innerHTML = liste.slice(0, 400).map((c, i) => ligne(c, i, "cb")).join("")
    + (liste.length > 400
        ? `<p class="vide">${liste.length - 400} autres — affine le filtre.</p>` : "");
}

/* Un bouton coché se décoche ; côté touches, la sélection reste unique. */
const rendreTout = () => { rendreConflits(); rendreCombinaisons(); rendreApp(); };

function brancherFiltres() {
  document.querySelectorAll("#mods button").forEach(b => b.addEventListener("click", () => {
    b.setAttribute("aria-pressed", String(b.getAttribute("aria-pressed") !== "true"));
    rendreTout();
  }));
  document.querySelectorAll("#touches button").forEach(b => b.addEventListener("click", () => {
    const etait = b.getAttribute("aria-pressed") === "true";
    document.querySelectorAll("#touches button").forEach(x => x.setAttribute("aria-pressed", "false"));
    b.setAttribute("aria-pressed", String(!etait));
    if (!etait) document.getElementById("touche-libre").value = "";
    rendreTout();
  }));
  document.getElementById("touche-libre").addEventListener("input", () => {
    document.querySelectorAll("#touches button").forEach(x => x.setAttribute("aria-pressed", "false"));
    rendreTout();
  });
  document.getElementById("vider-filtre").addEventListener("click", () => {
    document.querySelectorAll("#mods button, #touches button")
      .forEach(x => x.setAttribute("aria-pressed", "false"));
    document.getElementById("touche-libre").value = "";
    document.getElementById("recherche").value = "";
    rendreTout();
  });
}

/* Vue par app, deux lectures complémentaires.

   « Par menu » suit la barre de menu de l'app, dans son ordre réel : lire des
   raccourcis Mise en forme, puis Fenêtre, puis Mise en forme à nouveau ne se retient
   pas. Les raccourcis globaux suivent, rangés selon ce sur quoi ils agissent.

   « Ce qui se passe » part de la frappe et non de la commande : pour chaque
   combinaison atteignable dans cette app, qui la reçoit vraiment. Classées par nombre
   de touches, parce qu'on cherche d'abord les combinaisons courtes. */

const nbTouches = (mods) => {
  let n = 1;
  for (let m = mods; m; m >>= 1) n += m & 1;
  return n;
};
const SOURCE_LABEL = {
  systeme: "raccourci système macOS", capture: "outil global", global: "outil global",
  pilote: "pilote clavier", autre: "outil global", menu: "menu de l'app",
};

/* Ce que reçoit une frappe donnée pendant que cette app est au premier plan :
   ses propres menus, plus tout ce qui est global. Le reste ne la concerne pas. */
function atteignables(bundleID) {
  const f = etatFiltre();
  const out = [];
  for (const c of D.combinaisons) {
    if (!passe(f, c.combo, c.mods, c.usages)) continue;
    const candidats = c.usages.filter(u =>
      u.actif && (u.couche !== "menu" || u.bundle_id === bundleID));
    if (!candidats.length) continue;
    const gagnante = ORDRE.find(couche => candidats.some(u => u.couche === couche));
    const vainqueurs = candidats.filter(u => u.couche === gagnante);
    const perdants = candidats.filter(u => u.couche !== gagnante);
    out.push({ combo: c.combo, mods: c.mods, vainqueurs, perdants, couche: gagnante });
  }
  return out;
}

function vueCeQuiSePasse(app) {
  const items = atteignables(app.bundleID);
  const parTaille = new Map();
  for (const it of items) {
    const n = nbTouches(it.mods);
    if (!parTaille.has(n)) parTaille.set(n, []);
    parTaille.get(n).push(it);
  }
  const tailles = [...parTaille.keys()].sort((a, b) => a - b);
  if (!tailles.length) return `<p class="vide">Rien d'atteignable dans cette app.</p>`;

  return tailles.map(n => {
    const liste = parTaille.get(n).sort((a, b) => a.combo.localeCompare(b.combo, "fr"));
    return `<section class="groupe-portee"><h3>${n} touche${n > 1 ? "s" : ""} · ${liste.length}</h3>`
      + liste.map(it => {
        const v = it.vainqueurs[0];
        const multi = it.vainqueurs.length > 1;
        const perdus = it.perdants.map(u =>
          `${esc(u.proprietaire)} — ${esc(u.action)}`).join(" · ");
        return `<div class="resultat">
          <span class="combo">${caps(it.combo)}</span>
          <span>
            <span class="titre">${esc(v.action)}</span>
            <span class="sous">${esc(v.proprietaire)} · ${SOURCE_LABEL[it.couche]}${
              multi ? ` · à égalité avec ${esc(it.vainqueurs.slice(1).map(u => u.proprietaire).join(", "))}` : ""}</span>
            ${perdus ? `<span class="perdu">passe devant ${perdus}</span>` : ""}
          </span></div>`;
      }).join("") + `</div></section>`;
  }).join("");
}

function vueParMenu(app) {
  const f = etatFiltre();
  const parMenu = new Map(), parPortee = { app: [], app_externe: [], systeme: [], inconnu: [] };
  for (const c of D.combinaisons) {
    if (!passe(f, c.combo, c.mods, c.usages)) continue;
    for (const u of c.usages) {
      if (!u.actif) continue;
      if (u.couche === "menu") {
        if (u.bundle_id !== app.bundleID) continue;
        const m = u.menu || "—";
        if (!parMenu.has(m)) parMenu.set(m, []);
        parMenu.get(m).push(u);
      } else if (parPortee[u.portee]) parPortee[u.portee].push(u);
    }
  }
  // Les menus s'affichent dans l'ordre de la barre de menu, pas par ordre alphabétique.
  const menus = [...parMenu.entries()].sort((a, b) =>
    Math.min(...a[1].map(u => u.ordre)) - Math.min(...b[1].map(u => u.ordre)));

  const rangee = (u, sousTitre) => `<div class="resultat">
      <span class="combo">${caps(u.combo)}</span>
      <span><span class="titre">${esc(u.action.split(" > ").slice(1).join(" > ") || u.action)}</span>
      ${sousTitre ? `<span class="sous">${esc(sousTitre)}</span>` : ""}
      ${u.detail ? `<span class="sous">${esc(u.detail)}</span>` : ""}</span></div>`;

  const bloc = (titre, pourquoi, lignes) => !lignes.length ? "" :
    `<section class="groupe-portee"><h3>${esc(titre)} · ${lignes.length}</h3>
     ${pourquoi ? `<p class="pourquoi">${esc(pourquoi)}</p>` : ""}
     <div class="grille">${lignes.join("")}</div></section>`;

  return menus.map(([nom, us]) => bloc(nom, "",
      us.sort((a, b) => a.ordre - b.ordre).map(u => rangee(u, "")))).join("")
    + bloc(D.libelles_portee.app,
        "Raccourcis macOS qui agissent sur l'interface de l'app.",
        parPortee.app.map(u => rangee(u, u.proprietaire)))
    + bloc(D.libelles_portee.app_externe,
        "Agissent sur la fenêtre de l'app ou par-dessus elle, sans toucher son interface.",
        parPortee.app_externe.map(u => rangee(u, u.proprietaire)))
    + bloc(D.libelles_portee.systeme,
        "Fonctionnent pendant que l'app est ouverte, mais ne la concernent pas.",
        parPortee.systeme.map(u => rangee(u, u.proprietaire)))
    + bloc(D.libelles_portee.inconnu, "Portée non déterminée.",
        parPortee.inconnu.map(u => rangee(u, u.proprietaire)));
}

/* Une liste déroulante de 200 apps ne se parcourt pas : on la restreint en tapant.
   La comparaison ignore accents et casse, pour que « appstore » trouve « AppStore ». */
const sansAccent = (t) => (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const LISIBLES = D.apps.filter(a => a.statut === "ok")
  .sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
let appChoisie = LISIBLES.length ? LISIBLES[0].bundleID : "";
let surligne = -1;

let saisieApp = "";

function appsFiltrees() {
  const q = sansAccent(saisieApp.trim());
  if (!q) return LISIBLES;
  return LISIBLES.filter(a => sansAccent(a.nom).includes(q)
                           || sansAccent(a.bundleID).includes(q));
}

function rendreListeApps() {
  const liste = document.getElementById("liste-app");
  const trouvees = appsFiltrees();
  liste.innerHTML = trouvees.length
    ? trouvees.map((a, i) =>
        `<li role="option" data-id="${esc(a.bundleID)}" aria-selected="${i === surligne}">`
        + `<span>${esc(a.nom)}</span>`
        + `<span class="compte">${a.version ? "v" + esc(a.version) : ""}</span></li>`).join("")
    : `<li class="aucun">Aucune application pour cette recherche.</li>`;
  return trouvees;
}

function ouvrirListe(ouvrir) {
  const champ = document.getElementById("filtre-app");
  document.getElementById("liste-app").hidden = !ouvrir;
  champ.setAttribute("aria-expanded", String(ouvrir));
  if (ouvrir) rendreListeApps();
}

function choisirApp(id) {
  const app = LISIBLES.find(a => a.bundleID === id);
  if (!app) return;
  appChoisie = id;
  document.getElementById("filtre-app").value = app.nom;
  saisieApp = "";
  surligne = -1;
  document.getElementById("filtre-app").blur();
  ouvrirListe(false);
  rendreApp();
}

function brancherChoixApp() {
  const champ = document.getElementById("filtre-app");
  const liste = document.getElementById("liste-app");
  champ.addEventListener("input", () => { saisieApp = champ.value; surligne = -1; ouvrirListe(true); });
  // Au clic, le champ se vide : le nom qui s'y trouve est un affichage, pas une
  // recherche, et le conserver réduirait la liste à cette seule app.
  champ.addEventListener("focus", () => {
    saisieApp = ""; champ.value = ""; surligne = -1; ouvrirListe(true);
  });
  // Le clic sur un élément doit passer avant la fermeture déclenchée par le blur.
  champ.addEventListener("blur", () => setTimeout(() => {
    ouvrirListe(false);
    const app = LISIBLES.find(a => a.bundleID === appChoisie);
    if (app) { champ.value = app.nom; saisieApp = ""; }
  }, 140));
  champ.addEventListener("keydown", (e) => {
    const trouvees = appsFiltrees();
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (liste.hidden) ouvrirListe(true);
      surligne = Math.max(0, Math.min(trouvees.length - 1,
        surligne + (e.key === "ArrowDown" ? 1 : -1)));
      rendreListeApps();
      liste.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cible = surligne >= 0 ? trouvees[surligne] : trouvees[0];
      if (cible) choisirApp(cible.bundleID);
    } else if (e.key === "Escape") {
      ouvrirListe(false);
    }
  });
  liste.addEventListener("mousedown", (e) => {
    const item = e.target.closest("li[data-id]");
    if (item) choisirApp(item.dataset.id);
  });
  if (appChoisie) champ.value = LISIBLES[0].nom;
}

function rendreApp() {
  const app = D.apps.find(a => a.bundleID === appChoisie);
  const poser = (cible, contenu, secours) => {
    document.getElementById(cible).innerHTML =
      contenu.trim() ? contenu : `<p class="vide">${secours}</p>`;
  };
  if (!app) {
    poser("vue-menu", "", "Choisis une application.");
    poser("vue-effet", "", "Choisis une application.");
    return;
  }
  if (app.statut !== "ok") {
    const raison = `${esc(app.nom)} n'a pas pu être lue : ${esc(app.detail || app.statut)}.`;
    poser("vue-menu", "", raison);
    poser("vue-effet", "", raison);
    return;
  }
  poser("vue-menu", vueParMenu(app), `Rien dans ${esc(app.nom)} ne correspond au filtre.`);
  poser("vue-effet", vueCeQuiSePasse(app), `Rien dans ${esc(app.nom)} ne correspond au filtre.`);
}

document.addEventListener("click", (e) => {
  const bouton = e.target.closest(".ligne[data-cible]");
  if (!bouton) return;
  const detail = document.getElementById(bouton.dataset.cible);
  const ouvert = bouton.getAttribute("aria-expanded") === "true";
  bouton.setAttribute("aria-expanded", String(!ouvert));
  detail.hidden = ouvert;
});

document.querySelectorAll(".onglets button").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".onglets button").forEach(x =>
    x.setAttribute("aria-selected", String(x === b)));
  document.querySelectorAll("main > section").forEach(s =>
    s.hidden = s.id !== "onglet-" + b.dataset.vue);
}));

document.getElementById("recherche").addEventListener("input", rendreTout);
brancherFiltres(); brancherChoixApp();

rendreConflits(); rendreCombinaisons(); rendreApp();
"""


def _ordre_touche(touche):
    """Les touches de fonction se rangent par leur numéro, pas par ordre alphabétique :
    sinon F10 se glisse entre F1 et F2."""
    if touche.startswith("F") and touche[1:].isdigit():
        return (0, int(touche[1:]), "")
    return (1, 0, touche)


def build(index_path):
    data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    lisibles = [a for a in data["apps"] if a["statut"] == "ok"]
    conflits = sum(1 for c in data["combinaisons"] if c["conflit"])
    machine = subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip()

    # "</" doit être neutralisé : la séquence fermerait la balise script depuis
    # l'intérieur d'une chaîne JSON si un nom de commande la contenait.
    charge = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    # Un bouton ne se justifie que pour une touche qu'on ne peut pas simplement écrire.
    # Tout ce que la disposition clavier produit sans Maj — lettres, chiffres, mais
    # aussi « $ », « ' », « ; » en AZERTY — se tape sans risque dans le champ libre.
    # Un bouton ne se justifie que pour une touche qui n'écrit aucun caractère.
    # Tout ce que la disposition produit, avec ou sans Maj, se tape dans le champ :
    # en AZERTY cela couvre « $ », « ; », mais aussi « . » et « £ », qui demandent Maj.
    keymap = json.loads((ROOT / "data" / "keymap.json").read_text(encoding="utf-8"))
    ecrivables = {c.upper() for niveaux in keymap.values() for c in niveaux if c.strip()}

    vues = {c["combo"].replace("fn", "").translate(str.maketrans("", "", "⌃⌥⇧⌘"))
            for c in data["combinaisons"]}
    autres = sorted({t for t in vues if t.strip() and t.upper() not in ecrivables
                     and not (t.startswith("F") and t[1:].isdigit())},
                    key=_ordre_touche)
    # Les touches de fonction sont proposées au complet, y compris celles qu'aucun
    # raccourci n'utilise : savoir qu'une touche est libre fait partie de la réponse.
    fonctions = [f"F{n}" for n in range(1, 21)]
    # Les touches de ponctuation doivent être échappées : sur AZERTY, le guillemet
    # est une touche, et non échappé il refermerait l'attribut HTML.
    def capsules(touches):
        return "".join(
            '<button type="button" aria-pressed="false" data-touche="{0}">{0}</button>'.format(
                html_std.escape(t, quote=True))
            for t in touches)

    touches_html = (f'<div class="capsules">{capsules(fonctions)}</div>'
                    f'<div class="capsules">{capsules(autres)}</div>')
    mods_html = "".join(
        f'<button type="button" aria-pressed="false" data-bit="{bit}">{sym}</button>'
        for sym, bit in (("⌃", 2), ("⌥", 4), ("⇧", 1), ("⌘", 8), ("fn", 16)))

    script = (JS.replace("DONNEES", charge)
                .replace("ORDRE_COUCHES_JS", json.dumps(ORDRE_COUCHES))
                .replace("NOMS_COUCHES_JS", json.dumps(NOMS_COUCHES, ensure_ascii=False))
                .replace("MODS_BITS", json.dumps({"⇧": 1, "⌃": 2, "⌥": 4, "⌘": 8, "fn": 16},
                                                 ensure_ascii=False)))

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
  <div><h1>MacOS-shortcuts-inventory</h1>
  <p class="eyebrow" style="margin:6px 0 0">{machine} · macOS {platform.mac_ver()[0]} · {date.today().isoformat()}</p></div>
  <div class="chiffres">
    <div class="chiffre"><b>{len(data["combinaisons"])}</b><span>combinaisons</span></div>
    <div class="chiffre {"alerte" if conflits else ""}"><b>{conflits}</b><span>en conflit</span></div>
    <div class="chiffre"><b>{len(lisibles)}</b><span>applications lues</span></div>
  </div>
</header>
<nav>
  <div class="onglets">
    <button data-vue="menu" aria-selected="true">Commandes par menu</button>
    <button data-vue="effet" aria-selected="false">Effet d'une frappe</button>
    <button data-vue="conflits" aria-selected="false">Conflits</button>
    <button data-vue="combinaisons" aria-selected="false">Par combinaison</button>
  </div>
  <div class="combo-app">
    <input type="text" id="filtre-app" role="combobox" aria-expanded="false"
           aria-controls="liste-app" aria-autocomplete="list" autocomplete="off"
           placeholder="Cherche une application">
    <ul id="liste-app" role="listbox" hidden></ul>
  </div>
</nav>
<!-- Un seul filtre pour les trois vues : dupliquer les contrôles ferait diverger
     leurs états, et on perdrait le filtre en changeant d'onglet. -->
<div class="filtre">
  <div class="colonne-touches">
    <div class="rangee-filtre">
      <span class="etiquette">Modificateurs</span>
      <div id="mods" class="capsules">{mods_html}</div>
      <input type="text" id="touche-libre" maxlength="6" placeholder="ou tape la touche">
    </div>
    <div class="rangee-filtre">
      <span class="etiquette">Touche</span>
      <div id="touches" class="rangees-touches">{touches_html}</div>
    </div>
  </div>
  <div class="colonne-texte">
    <span class="etiquette">Libellé de commande</span>
    <input type="search" id="recherche" placeholder="copier, capture, plein écran…">
    <button type="button" id="vider-filtre" class="lien">Tout effacer</button>
  </div>
</div>
<main>
  <section id="onglet-conflits" hidden><div id="vue-conflits"></div></section>
  <section id="onglet-combinaisons" hidden>
    <div class="filtre-place">
    <div id="vue-combinaisons"></div>
  </section>
  <section id="onglet-menu"><div id="vue-menu"></div></section>
  <section id="onglet-effet" hidden><div id="vue-effet"></div></section>
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
