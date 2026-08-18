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
header { display: grid; grid-template-columns: 1fr auto 1fr; gap: 32px; align-items: center; }
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
.langues { display: flex; gap: 3px; align-self: center; }
.langues button {
  font-size: 15px; line-height: 1; padding: 5px 6px; cursor: pointer; border-radius: 5px;
  background: none; border: 1px solid transparent; filter: grayscale(1); opacity: .45;
}
.langues button[aria-pressed="true"] {
  filter: none; opacity: 1; border-color: var(--creux); background: var(--plaque);
}
.langues button:hover { filter: none; opacity: .85; }
.langues button:focus-visible { outline: 2px solid var(--petrol); outline-offset: 2px; }

/* — Lancement d'un scan — */
.actions-scan { justify-self: center; display: flex; align-items: stretch; gap: 10px; }
.bouton-secondaire {
  font-family: var(--display); font-size: 12px; font-weight: 600; line-height: 1.25;
  padding: 10px 14px; border-radius: 9px; cursor: pointer; text-align: center;
  background: var(--plaque); color: var(--sourdine); border: 1px solid var(--creux);
}
.bouton-secondaire:hover { color: var(--encre); border-color: var(--petrol); }
.bouton-secondaire:focus-visible { outline: 2px solid var(--petrol); outline-offset: 3px; }
.bouton-scan { font-family: var(--display); font-size: 15px; font-weight: 600;
  padding: 13px 24px; border-radius: 9px; cursor: pointer;
  background: var(--petrol); color: var(--plaque); border: 0;
  display: flex; flex-direction: column; align-items: center; gap: 2px; line-height: 1.2;
}
.bouton-scan #compte-scan {
  font-family: var(--mono); font-size: 10.5px; font-weight: 400; opacity: .8;
  letter-spacing: .04em;
}
.bouton-scan:hover { background: color-mix(in srgb, var(--petrol) 85%, var(--encre)); }
.bouton-scan:focus-visible { outline: 2px solid var(--encre); outline-offset: 3px; }

#detail {
  width: min(720px, 92vw); padding: 0; border: 0; border-radius: 12px;
  background: var(--plaque); color: var(--encre);
}
#detail::backdrop { background: rgba(0,0,0,.45); }
.detail-corps { padding: 20px 26px 26px; }
.detail-tete {
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  padding-bottom: 16px; margin-bottom: 18px; border-bottom: 1px solid var(--creux);
}
.croix {
  font: inherit; font-size: 17px; line-height: 1; padding: 7px 11px; cursor: pointer;
  background: none; border: 1px solid var(--creux); border-radius: 7px; color: var(--sourdine);
}
.croix:hover { color: var(--encre); border-color: var(--sourdine); }
.croix:focus-visible { outline: 2px solid var(--petrol); outline-offset: 2px; }
#detail-contenu { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 26px; }
#detail-contenu .verdict, #detail-contenu .usages { grid-column: 2; margin-top: 0; }

#scan {
  width: min(1100px, 92vw); max-height: 86vh; padding: 0; border: 0; border-radius: 12px;
  background: var(--plaque); color: var(--encre); overflow: hidden;
}
#scan::backdrop { background: rgba(0,0,0,.45); }
.scan-corps { display: grid; grid-template-rows: auto auto 1fr auto; max-height: 86vh; }
.scan-tete { padding: 22px 26px 14px; border-bottom: 1px solid var(--creux); }
.scan-tete h2 { font-family: var(--display); font-size: 22px; margin: 0 0 6px; }
.scan-tete p { margin: 0; font-size: 13.5px; color: var(--sourdine); }
.scan-outils {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 14px 26px; border-bottom: 1px solid var(--creux);
}
.scan-outils input[type="search"] { flex: 1; min-width: 200px; max-width: 340px; font-size: 14px; padding: 9px 12px; }
.scan-liste { overflow-y: auto; padding: 14px 26px; }
.scan-grille { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 2px 32px; }
.scan-grille label {
  display: grid; grid-template-columns: auto 1fr; gap: 10px; align-items: baseline;
  padding: 7px 8px; border-radius: 6px; cursor: pointer; font-size: 14px;
}
.scan-grille label:hover { background: var(--alu); }
.scan-grille .motif {
  display: block; font-family: var(--mono); font-size: 10.5px; color: var(--sourdine);
}
.scan-pied {
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  padding: 16px 26px; border-top: 1px solid var(--creux); flex-wrap: wrap;
}
.bouton {
  font: inherit; font-size: 14px; font-weight: 600; padding: 10px 18px; border-radius: 7px;
  cursor: pointer; border: 1px solid var(--creux); background: var(--alu); color: var(--encre);
}
.bouton.primaire { background: var(--petrol); border-color: var(--petrol); color: var(--plaque); }
.bouton:focus-visible, .scan-grille label:focus-within { outline: 2px solid var(--petrol); outline-offset: 2px; }
.commande {
  display: block; font-family: var(--mono); font-size: 12.5px; padding: 14px 16px;
  margin: 0 26px 18px; background: var(--alu); border: 1px solid var(--creux);
  border-radius: 8px; white-space: pre-wrap; word-break: break-all; max-height: 150px;
  overflow-y: auto;
}

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
.verdict.convention { border-left-color: var(--sourdine); color: var(--sourdine); }
.hors-app {
  font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase;
  margin-left: 9px; padding: 2px 7px; border-radius: 4px; white-space: nowrap;
  border: 1px solid var(--creux); color: var(--sourdine);
}

/* — Contrôles — */
.controles { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
/* Deux natures de filtre : à gauche la combinaison de touches, à droite la recherche
   de libellé. Les séparer évite de les prendre pour un même réglage. */
.filtre {
  display: grid; grid-template-columns: minmax(0, max-content) auto minmax(200px, 1fr);
  gap: 12px 36px; margin: 0 0 28px; padding: 18px 20px; align-items: start;
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 10px;
}
.colonne-touches { display: grid; gap: 12px; }
.colonne-nombre {
  display: grid; gap: 8px; justify-items: start;
  padding-left: 36px; border-left: 1px solid var(--creux);
}
.colonne-nombre select {
  font: inherit; font-size: 14px; padding: 10px 13px; color: var(--encre);
  background: var(--alu); border: 1px solid var(--creux); border-radius: 7px;
}
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
.bloc-touches { display: grid; gap: 6px; }
/* Le bouton se pose au-dessus de la grille, du côté où elle se termine. */
.entete-touches { display: flex; justify-content: flex-end; }
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
.bloc-app { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.bascule {
  display: inline-flex; align-items: center; gap: 8px; font: inherit; font-size: 13px;
  padding: 9px 13px; border-radius: 7px; cursor: pointer;
  border: 1px solid var(--creux); background: var(--plaque); color: var(--sourdine);
}
.bascule .temoin {
  width: 30px; height: 17px; border-radius: 9px; background: var(--creux);
  position: relative; flex: none; transition: background .12s;
}
.bascule .temoin::after {
  content: ""; position: absolute; top: 2px; left: 2px; width: 13px; height: 13px;
  border-radius: 50%; background: var(--plaque); transition: transform .12s;
}
.bascule[aria-pressed="true"] { color: var(--encre); border-color: var(--petrol); }
.bascule[aria-pressed="true"] .temoin { background: var(--petrol); }
.bascule[aria-pressed="true"] .temoin::after { transform: translateX(13px); }
.bascule:focus-visible { outline: 2px solid var(--petrol); outline-offset: 2px; }
.combo-app { position: relative; width: 280px; flex: none; }
.combo-app.inactif { opacity: .5; pointer-events: none; }
.combo-app.inactif input { border-color: var(--creux); background: var(--plaque); }
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
/* Une combinaison disputée se repère à la couleur : la ligne dit ce que la commande
   fait, pas qu'un autre preneur pourrait la lui prendre. */
.resultat.rang-conflit .titre { color: var(--vermillon); }
.resultat.rang-conflit .cap { border-color: var(--vermillon); color: var(--vermillon); }
.resultat.ouvrable { cursor: pointer; }
.resultat.ouvrable:hover { background: var(--alu); }
.resultat.ouvrable:focus-visible { outline: 2px solid var(--vermillon); outline-offset: 2px; }
/* Une double frappe n'est pas une combinaison : elle se signale, sinon « ⌘⌘ » se lit
   comme deux touches enfoncées ensemble. */
.marque-double {
  font-family: var(--mono); font-size: 10px; letter-spacing: .07em; text-transform: uppercase;
  padding: 3px 7px; border-radius: 4px; margin-left: 7px; white-space: nowrap;
  background: color-mix(in srgb, var(--petrol) 18%, transparent); color: var(--petrol);
}
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

JS = r"""
const D = DONNEES;
const ORDRE = ORDRE_COUCHES_JS;
const NOMS = () => Object.fromEntries(ORDRE.map(c => [c, T("couche_" + c)]));

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
    const noms = NOMS();
    return `<div class="${cls}"><span class="nom">${noms[c]}</span>`
         + `<span class="puce"></span><span>${esc(qui.join(", "))}</span></div>`;
  }).join("") + `</div>`;
}

const listeUsages = (usages) => `<ul class="usages">` + usages.map(u =>
  `<li class="${u.actif ? "" : "inactif"}"><span class="couche">${NOMS()[u.couche]}</span>`
  + `<span class="qui">${esc(u.proprietaire)}</span>`
  + `<span>${esc(u.action)}${u.detail ? ` <em>— ${esc(u.detail)}</em>` : ""}`
  + `${u.actif ? "" : " — " + T("desactive")}</span></li>`).join("") + `</ul>`;

function ligne(c, i, prefixe) {
  const nb = c.usages.filter(u => u.actif).length;
  return `<button class="ligne ${c.conflit ? "conflit" : ""}" aria-expanded="false"
      data-cible="${prefixe}-${i}">
      <span class="combo">${caps(c.combo)}</span>
      <span><span class="titre">${esc(c.usages[0].action)}</span>
      <span class="sous">${esc(c.usages[0].proprietaire)}${nb > 1 ? ` et ${nb - 1} autre${nb > 2 ? "s" : ""}` : ""}${
        c.horsApp ? `<span class="hors-app">${T("hors_app")}</span>` : ""}</span></span>
    </button>
    <div class="detail ${c.conflit ? "conflit-detail" : ""}" id="${prefixe}-${i}" hidden>
      ${pile(c.usages)}
      ${c.convention ? `<p class="verdict convention">${T("convention")(c.apps_exposant)}</p>` : ""}
      <p class="verdict">${esc(c.arbitrage.texte)}</p>
      ${listeUsages(c.usages)}
    </div>`;
}

function rendreConflits() {
  const f = etatFiltre();
  const id = appFiltrante();
  const disputees = id
    ? new Set(atteignables(id).filter(it => it.conflit).map(it => it.combo))
    : null;
  let conflits = D.combinaisons.filter(c =>
    (disputees ? disputees.has(c.combo) : c.conflit)
    && passe(f, c.combo, c.mods, c.usages, c.double));

  /* Filtré sur une app, la fiche doit montrer les mêmes prétendants que la liste :
     les menus des *autres* apps ne sont pas en lice pendant que celle-ci est devant.
     Et un conflit purement global — deux outils qui se disputent la touche — est
     actif ici sans concerner l'app : le dire, plutôt que de laisser chercher son nom
     dans une fiche où il ne figure pas. */
  if (id) {
    conflits = conflits.map(c => {
      const usages = c.usages.filter(u => u.couche !== "menu" || u.bundle_id === id);
      return { ...c, usages, horsApp: !usages.some(u => u.bundle_id === id && u.actif) };
    }).sort((a, b) => (a.horsApp ? 1 : 0) - (b.horsApp ? 1 : 0));
  }
  document.getElementById("vue-conflits").innerHTML = conflits.length
    ? conflits.map((c, i) => ligne(c, i, "cf")).join("")
    : `<p class="vide">${T("aucun_conflit")}${f.actifs || f.touche || f.libre || f.texte
        ? T("aucun_conflit_filtre") : ""}${T("aucun_conflit_suite")}</p>`;
}

/* Les modificateurs se cochent au lieu de se taper : presser ⌘⇧ dans un champ de
   recherche déclencherait le raccourci qu'on cherche justement à identifier. */
/* Les libellés de l'interface existent dans les deux langues. Le contenu, lui, est lu
   dans macOS : chemins de menus, noms de commandes et catégories restent tels que le
   système les fournit — les traduire reviendrait à réécrire une donnée. */
const TEXTES = {
  fr: {
    onglet_menu: "Commandes par menu", onglet_effet: "Effet d'une frappe",
    onglet_conflits: "Conflits", onglet_combinaisons: "Par combinaison",
    stat_combinaisons: "combinaisons", stat_conflits: "en conflit",
    stat_apps: "applications lues",
    scanner: "Scanner tout le Mac", scanner_apps: "apps",
    relire: "Relire les raccourcis<br>système et les outils",
    bascule_app: "Filtre par application", toutes_apps: "Toutes applications",
    cherche_app: "Cherche une application",
    l_modificateurs: "Modificateurs", l_touche: "Touche",
    l_nombre: "Filtre par nombre de touches", l_texte: "Libellé de commande",
    effacer_touches: "Effacer les touches", tout_effacer: "Tout effacer",
    ph_touche: "ou tape la touche", ph_texte: "copier, capture, plein écran…",
    toutes: "Toutes", touche_s: (n) => `${n} touche${n > 1 ? "s" : ""}`,
    double: "double frappe", fermer: "Fermer",
    rien_atteignable: "Rien d'atteignable dans cette app.",
    hors_app: "actif ici, mais ne concerne pas cette app",
    convention: (n) => `Commande standard de macOS : ${n} applications l'exposent dans `
                     + `leur propre menu. Le raccourci système et ces entrées désignent `
                     + `la même action — ce n'est pas un conflit.`,
    aucun_conflit: "Aucun conflit", aucun_conflit_filtre: " parmi ce que le filtre laisse passer",
    aucun_conflit_suite: ". Chaque combinaison n'a qu'un seul preneur.",
    rien_filtre: "Aucune combinaison", rien_pour: "pour", rien_libre: "Cette combinaison est donc libre.",
    autres_affine: (n) => `${n} autres — affine le filtre.`,
    choisis_app: "Choisis une application.",
    rien_app: (nom) => `Rien dans ${nom} ne correspond au filtre.`,
    illisible: (nom, raison) => `${nom} n'a pas pu être lue : ${raison}.`,
    sans_app: "Aucune application choisie : seuls les raccourcis globaux sont résolus ici. "
            + "Un raccourci de menu ne répond que lorsque son application est au premier plan.",
    seul_ici: (qui) => `Seul ${qui} utilise cette combinaison ici.`,
    emporte: (qui) => `${qui} l'emporte.`,
    egalite: (qui) => `${qui} s'accrochent au même étage : c'est celui qui s'est enregistré `
                    + `en premier qui gagne, et cet ordre n'est écrit nulle part.`,
    egalite_avec: (qui) => `à égalité avec ${qui}`,
    passe_devant: "passe devant",
    src_systeme: "raccourci système macOS", src_outil: "outil global",
    src_pilote: "pilote clavier", src_menu: "menu de l'app",
    pourquoi_propres: "Ses propres commandes de menu. Actives seulement quand elle est au premier plan.",
    pourquoi_app: "Raccourcis macOS qui agissent sur l'interface de l'app.",
    pourquoi_externe: "Agissent sur la fenêtre de l'app ou par-dessus elle, sans toucher son interface.",
    pourquoi_systeme: "Fonctionnent pendant que l'app est ouverte, mais ne la concernent pas.",
    pourquoi_inconnu: "Portée non déterminée.",
    couche_pilote: "Pilote", couche_capture: "Capture", couche_systeme: "Système",
    couche_global: "Global", couche_autre: "Autre", couche_menu: "Menu",
    desactive: "désactivé",
    scan_titre: "Scanner tout le Mac",
    scan_intro: "Chaque application cochée sera ouverte le temps de lire sa barre de menu, "
              + "puis refermée. À lancer quand tu n'utilises pas la machine.",
    scan_filtrer: "Filtrer la liste…", scan_tout: "Tout cocher", scan_rien: "Tout décocher",
    scan_defaut: "Rétablir les exclusions", scan_lancer: "Lancer le scan",
    scan_affichees: (n, total) => `${n} affichées sur ${total}`,
    scan_a_scanner: (n) => `${n} application${n > 1 ? "s" : ""} à scanner`,
    scan_ecartee: (raison) => `écartée par défaut — ${raison}`,
    scan_aucune: "Aucune application pour cette recherche.",
    scan_rien_coche: "Aucune application cochée : rien à scanner.",
    scan_defaut_cmd: "# Sélection par défaut — la commande complète suffit",
    scan_perso_cmd: "# Sélection personnalisée — à coller dans le terminal",
    relire_titre: "Relire les raccourcis système et les outils",
    relire_intro: "Relit les raccourcis de macOS, d'Alfred, de Keyboard Maestro et de "
                + "CleanShot X, puis reconstruit cette page. <strong>Aucune application "
                + "n'est ouverte</strong> — les raccourcis de menu déjà lus sont conservés "
                + "tels quels. Environ dix secondes.",
    relire_apres: "À lancer dans le terminal, puis recharge cette page. Le déclenchement "
                + "depuis le navigateur viendra avec la question des autorisations.",
    pied: "Les raccourcis d'une app ne vivent que dans sa barre de menu : ils sont lus app "
        + "par app. Une app lue sans document ouvert expose moins de commandes qu'en usage "
        + "réel. L'ordre des étages est fiable, mais deux outils accrochés au même étage "
        + "sont départagés par leur ordre d'enregistrement, que rien sur le disque ne "
        + "consigne. Les combinaisons sont écrites pour le clavier intégré : en AZERTY, un "
        + "chiffre demande Maj, d'où les ⇧ affichés. Un clavier externe à pavé numérique "
        + "donne les chiffres directement, sans Maj.",
  },
  en: {
    onglet_menu: "Commands by menu", onglet_effet: "What a keystroke does",
    onglet_conflits: "Conflicts", onglet_combinaisons: "By combination",
    stat_combinaisons: "combinations", stat_conflits: "in conflict",
    stat_apps: "apps read",
    scanner: "Scan the whole Mac", scanner_apps: "apps",
    relire: "Re-read system shortcuts<br>and tools",
    bascule_app: "Filter by app", toutes_apps: "All applications",
    cherche_app: "Search an application",
    l_modificateurs: "Modifiers", l_touche: "Key",
    l_nombre: "Filter by key count", l_texte: "Command label",
    effacer_touches: "Clear keys", tout_effacer: "Clear all",
    ph_touche: "or type the key", ph_texte: "copy, capture, full screen…",
    toutes: "All", touche_s: (n) => `${n} key${n > 1 ? "s" : ""}`,
    double: "double press", fermer: "Close",
    rien_atteignable: "Nothing reachable in this app.",
    hors_app: "live here, but does not involve this app",
    convention: (n) => `Standard macOS command: ${n} applications expose it in their own `
                     + `menu. The system shortcut and those entries mean the same action `
                     + `— this is not a conflict.`,
    aucun_conflit: "No conflict", aucun_conflit_filtre: " among what the filter lets through",
    aucun_conflit_suite: ". Every combination has a single taker.",
    rien_filtre: "No combination", rien_pour: "for", rien_libre: "This combination is free.",
    autres_affine: (n) => `${n} more — narrow the filter.`,
    choisis_app: "Choose an application.",
    rien_app: (nom) => `Nothing in ${nom} matches the filter.`,
    illisible: (nom, raison) => `${nom} could not be read: ${raison}.`,
    sans_app: "No application selected: only global shortcuts resolve here. "
            + "A menu shortcut answers only while its application is frontmost.",
    seul_ici: (qui) => `Only ${qui} uses this combination here.`,
    emporte: (qui) => `${qui} most likely wins.`,
    egalite: (qui) => `${qui} hook the same layer, so whichever registered first wins — `
                    + `and that order is recorded nowhere.`,
    egalite_avec: (qui) => `tied with ${qui}`,
    passe_devant: "beats",
    src_systeme: "macOS system shortcut", src_outil: "global tool",
    src_pilote: "keyboard driver", src_menu: "app menu",
    pourquoi_propres: "Its own menu commands. Live only while it is frontmost.",
    pourquoi_app: "macOS shortcuts acting on the app's interface.",
    pourquoi_externe: "Act on the app's window or over it, without touching its interface.",
    pourquoi_systeme: "Work while the app is open, but do not concern it.",
    pourquoi_inconnu: "Scope undetermined.",
    couche_pilote: "Driver", couche_capture: "Event tap", couche_systeme: "System",
    couche_global: "Global", couche_autre: "Other", couche_menu: "Menu",
    desactive: "disabled",
    scan_titre: "Scan the whole Mac",
    scan_intro: "Each checked application will be opened just long enough to read its menu "
              + "bar, then closed. Run it when you are not using the machine.",
    scan_filtrer: "Filter the list…", scan_tout: "Check all", scan_rien: "Uncheck all",
    scan_defaut: "Restore exclusions", scan_lancer: "Start the scan",
    scan_affichees: (n, total) => `${n} shown of ${total}`,
    scan_a_scanner: (n) => `${n} application${n > 1 ? "s" : ""} to scan`,
    scan_ecartee: (raison) => `excluded by default — ${raison}`,
    scan_aucune: "No application for this search.",
    scan_rien_coche: "No application checked: nothing to scan.",
    scan_defaut_cmd: "# Default selection — the plain command is enough",
    scan_perso_cmd: "# Custom selection — paste into the terminal",
    relire_titre: "Re-read system shortcuts and tools",
    relire_intro: "Re-reads shortcuts from macOS, Alfred, Keyboard Maestro and CleanShot X, "
                + "then rebuilds this page. <strong>No application is opened</strong> — menu "
                + "shortcuts already read are kept as they are. About ten seconds.",
    relire_apres: "Run it in the terminal, then reload this page. Triggering it from the "
                + "browser comes with the permissions question.",
    pied: "An app's shortcuts live only in its menu bar, so they are read app by app. An app "
        + "read with no document open exposes fewer commands than in real use. The layer "
        + "order is reliable, but two tools hooking the same layer are decided by their "
        + "registration order, which nothing on disk records. Combinations are written for "
        + "the built-in keyboard. Menu paths, command names and categories come from macOS "
        + "in its own language and are shown unchanged.",
  },
};
let LANGUE = (localStorage.getItem("langue") === "en") ? "en" : "fr";
const T = (cle) => TEXTES[LANGUE][cle];

const MODS = MODS_BITS;
const RACINE = RACINE_PROJET;
/* Une double frappe n'engage qu'une touche, pressée deux fois. */
const PORTEES = () => D.libelles_portee[LANGUE] || D.libelles_portee.fr || D.libelles_portee;
const nbTouches = (mods, double) => {
  if (double) return 1;
  let n = 1;
  for (let m = mods; m; m >>= 1) n += m & 1;
  return n;
};
const toucheSeule = (combo) => combo.replace("fn", "").replace(/[⌃⌥⇧⌘]/g, "");

/* Le filtre par application vaut pour les quatre vues. Désactivé, plus rien n'est
   restreint à une app, et le champ de sélection est neutralisé. */
let filtreApp = true;

function appFiltrante() {
  return filtreApp ? appChoisie : "";
}

function etatFiltre() {
  const bits = [...document.querySelectorAll("#mods button[aria-pressed=true]")]
    .reduce((acc, b) => acc | Number(b.dataset.bit), 0);
  const actifs = document.querySelectorAll("#mods button[aria-pressed=true]").length;
  const touche = document.querySelector("#touches button[aria-pressed=true]");
  return {
    bits, actifs,
    touche: touche ? touche.dataset.touche : "",
    libre: document.getElementById("touche-libre").value.trim().toLowerCase(),
    nombre: Number(document.getElementById("filtre-nombre").value) || 0,
    texte: document.getElementById("recherche").value.trim().toLowerCase(),
  };
}

/* Le même filtre sert aux trois vues : une combinaison passe si elle satisfait
   tous les critères renseignés. Un critère vide ne filtre rien. */
function passe(f, combo, mods, usages, double) {
  if (f.actifs && mods !== f.bits) return false;
  if (f.nombre && nbTouches(mods, double) !== f.nombre) return false;
  // Restreint à une app : ses propres commandes, plus tout ce qui est global.
  const id = appFiltrante();
  if (id && !usages.some(u => u.couche !== "menu" || u.bundle_id === id)) return false;
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
  const liste = D.combinaisons.filter(c => passe(f, c.combo, c.mods, c.usages, c.double));
  const cible = document.getElementById("vue-combinaisons");
  if (!liste.length) {
    const quoi = [f.actifs ? "ces modificateurs" : "", f.touche || f.libre, f.texte ? `« ${esc(f.texte)} »` : ""]
      .filter(Boolean).join(" + ");
    cible.innerHTML = `<p class="vide">${T("rien_filtre")}${quoi ? " " + T("rien_pour") + " " + quoi : ""}. `
      + `${T("rien_libre")}</p>`;
    return;
  }
  cible.innerHTML = liste.slice(0, 400).map((c, i) => ligne(c, i, "cb")).join("")
    + (liste.length > 400
        ? `<p class="vide">${T("autres_affine")(liste.length - 400)}</p>` : "");
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
  document.getElementById("filtre-nombre").addEventListener("change", rendreTout);
  // Efface la sélection de touche — capsules et saisie libre — sans toucher aux
  // modificateurs ni à la recherche de libellé, qui répondent à d'autres questions.
  document.getElementById("vider-touches").addEventListener("click", () => {
    document.querySelectorAll("#touches button").forEach(x => x.setAttribute("aria-pressed", "false"));
    document.getElementById("touche-libre").value = "";
    rendreTout();
  });
  document.getElementById("vider-filtre").addEventListener("click", () => {
    document.querySelectorAll("#mods button, #touches button")
      .forEach(x => x.setAttribute("aria-pressed", "false"));
    document.getElementById("touche-libre").value = "";
    document.getElementById("recherche").value = "";
    document.getElementById("filtre-nombre").value = "";
    rendreTout();
  });
}

/* Le verdict affiché doit valoir dans le contexte où on clique : depuis la vue d'une
   app, seuls ses menus et les raccourcis globaux sont en lice. Reprendre l'arbitrage
   global mentionnerait des apps qui ne sont pas là. */
function verdictLocal(it) {
  const noms = [...new Set(it.vainqueurs.map(u => u.proprietaire))];
  const explication = (D.couches[LANGUE] || D.couches.fr || {})[it.couche] || "";
  if (!it.perdants.length) return T("seul_ici")(noms[0]);
  if (noms.length === 1) return `${T("emporte")(noms[0])} ${explication}`;
  return `${T("egalite")(noms.join(", "))} ${explication}`;
}

function ouvrirDetail(cle) {
  const items = atteignables(appFiltrante());
  const it = items.find(x => x.cle === cle);
  if (!it) return;
  const usages = [...it.vainqueurs, ...it.perdants];
  document.getElementById("detail-combo").innerHTML =
    caps(it.combo) + (it.double ? `<span class="marque-double">${T("double")}</span>` : "");
  document.getElementById("detail-contenu").innerHTML =
    pile(usages) + `<p class="verdict">${esc(verdictLocal(it))}</p>` + listeUsages(usages);
  document.getElementById("detail").showModal();
}

function brancherDetail() {
  const boite = document.getElementById("detail");
  document.getElementById("detail-fermer").addEventListener("click", () => boite.close());
  const ouvrir = (e) => {
    const ligne = e.target.closest(".resultat.ouvrable[data-cle]");
    if (ligne) ouvrirDetail(ligne.dataset.cle);
  };
  ["vue-menu", "vue-effet"].forEach(id => {
    const zone = document.getElementById(id);
    zone.addEventListener("click", ouvrir);
    zone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ouvrir(e); }
    });
  });
}

function brancherBasculeApp() {
  const bouton = document.getElementById("bascule-app");
  const zone = document.querySelector(".combo-app");
  const champ = document.getElementById("filtre-app");
  const appliquer = () => {
    bouton.setAttribute("aria-pressed", String(filtreApp));
    zone.classList.toggle("inactif", !filtreApp);
    champ.disabled = !filtreApp;
    const app = LISIBLES.find(a => a.bundleID === appChoisie);
    champ.value = filtreApp ? (app ? app.nom : "") : T("toutes_apps");
    rendreTout();
  };
  bouton.addEventListener("click", () => { filtreApp = !filtreApp; appliquer(); });
  appliquer();
}

/* Vue par app, deux lectures complémentaires.

   « Par menu » suit la barre de menu de l'app, dans son ordre réel : lire des
   raccourcis Mise en forme, puis Fenêtre, puis Mise en forme à nouveau ne se retient
   pas. Les raccourcis globaux suivent, rangés selon ce sur quoi ils agissent.

   « Ce qui se passe » part de la frappe et non de la commande : pour chaque
   combinaison atteignable dans cette app, qui la reçoit vraiment. Classées par nombre
   de touches, parce qu'on cherche d'abord les combinaisons courtes. */


const SOURCE_LABEL = () => ({
  systeme: T("src_systeme"), capture: T("src_outil"), global: T("src_outil"),
  pilote: T("src_pilote"), autre: T("src_outil"), menu: T("src_menu"),
});

/* Ce que reçoit une frappe donnée pendant que cette app est au premier plan :
   ses propres menus, plus tout ce qui est global. Le reste ne la concerne pas. */
function atteignables(bundleID) {
  const f = etatFiltre();
  const out = [];
  for (const c of D.combinaisons) {
    if (!passe(f, c.combo, c.mods, c.usages, c.double)) continue;
    // Sans application choisie, seuls les raccourcis globaux se résolvent : un menu
    // ne répond que lorsque son app est au premier plan.
    const candidats = c.usages.filter(u =>
      u.actif && (u.couche !== "menu" || (bundleID && u.bundle_id === bundleID)));
    if (!candidats.length) continue;
    const gagnante = ORDRE.find(couche => candidats.some(u => u.couche === couche));
    const vainqueurs = candidats.filter(u => u.couche === gagnante);
    const perdants = candidats.filter(u => u.couche !== gagnante);
    // `meme_commande` marque les combinaisons que macOS injecte à l'identique dans
    // le menu de chaque app (⇧⌘Q, ⌃⌘Q…). Les compter comme conflits colorerait en
    // rouge la moitié des lignes, et contredirait l'arbitrage calculé côté Python.
    out.push({ cle: c.cle, combo: c.combo, mods: c.mods, double: c.double,
               vainqueurs, perdants, couche: gagnante,
               conflit: perdants.length > 0 && !c.meme_commande && !c.convention });
  }
  return out;
}

function vueCeQuiSePasse(app) {
  const items = atteignables(app.bundleID);
  const parTaille = new Map();
  for (const it of items) {
    const n = nbTouches(it.mods, it.double);
    if (!parTaille.has(n)) parTaille.set(n, []);
    parTaille.get(n).push(it);
  }
  const tailles = [...parTaille.keys()].sort((a, b) => a - b);
  if (!tailles.length) return `<p class="vide">${T("rien_atteignable")}</p>`;

  return tailles.map(n => {
    // Trier sur la touche principale, pas sur la chaîne entière : classer sur « ⌘ »
    // rassemblerait tout au même endroit alors qu'on cherche une lettre.
    const liste = parTaille.get(n).sort((a, b) =>
      toucheSeule(a.combo).localeCompare(toucheSeule(b.combo), "fr")
      || a.mods - b.mods);
    return `<section class="groupe-portee"><h3>${T("touche_s")(n)} · ${liste.length}</h3>`
      + `<div class="grille">`
      + liste.map(it => {
        const v = it.vainqueurs[0];
        const multi = it.vainqueurs.length > 1;
        const perdus = it.perdants.map(u =>
          `${esc(u.proprietaire)} — ${esc(u.action)}`).join(" · ");
        return `<div class="resultat${it.conflit ? " rang-conflit ouvrable" : ""}"${
          it.conflit ? ` role="button" tabindex="0" data-cle="${esc(it.cle)}"` : ""}>
          <span class="combo">${caps(it.combo)}${it.double ? `<span class="marque-double">${T("double")}</span>` : ""}</span>
          <span>
            <span class="titre">${esc(v.action)}</span>
            <span class="sous">${esc(v.proprietaire)} · ${SOURCE_LABEL()[it.couche]}${
              multi ? ` · ${T("egalite_avec")(esc(it.vainqueurs.slice(1).map(u => u.proprietaire).join(", ")))}` : ""}</span>
            ${perdus ? `<span class="perdu">${T("passe_devant")} ${perdus}</span>` : ""}
          </span></div>`;
      }).join("") + `</div></section>`;
  }).join("");
}

function vueParMenu(app) {
  const f = etatFiltre();
  const cible = app ? app.bundleID : "";
  // Même définition du conflit que dans « Effet d'une frappe » : une combinaison que
  // plusieurs preneurs se disputent *pendant que cette app est au premier plan*.
  const disputees = new Set(atteignables(cible).filter(it => it.conflit).map(it => it.combo));
  const parMenu = new Map(), parPortee = { app: [], app_externe: [], systeme: [], inconnu: [] };
  for (const c of D.combinaisons) {
    if (!passe(f, c.combo, c.mods, c.usages, c.double)) continue;
    for (const u of c.usages) {
      if (!u.actif) continue;
      const marque = { ...u, conflit: disputees.has(c.combo), double: c.double, cle: c.cle };
      if (u.couche === "menu") {
        if (cible && u.bundle_id !== cible) continue;
        // Sans app choisie, on regroupe par application avant le menu : « Fichier »
        // de six apps différentes dans un même bloc ne veut rien dire.
        const m = cible ? (u.menu || "—") : `${u.proprietaire} · ${u.menu || "—"}`;
        if (!parMenu.has(m)) parMenu.set(m, []);
        parMenu.get(m).push(marque);
      } else if (parPortee[u.portee]) parPortee[u.portee].push(marque);
    }
  }
  // Les menus s'affichent dans l'ordre de la barre de menu, pas par ordre alphabétique.
  // Le menu Apple n'appartient pas à l'app : il est identique partout. Il passe donc
  // après ses menus propres, juste avant les raccourcis venus d'ailleurs.
  const estApple = (x) => /(^|· )Apple$/.test(x[0]);
  const menus = [...parMenu.entries()].sort((a, b) => {
    const app = (x) => x[1][0].proprietaire;
    return (cible ? 0 : app(a).localeCompare(app(b), "fr"))
        || (estApple(a) - estApple(b))
        || Math.min(...a[1].map(u => u.ordre)) - Math.min(...b[1].map(u => u.ordre));
  });

  const rangee = (u, sousTitre) => `<div class="resultat${u.conflit ? " rang-conflit ouvrable" : ""}"${
      u.conflit ? ` role="button" tabindex="0" data-cle="${esc(u.cle)}"` : ""}>
      <span class="combo">${caps(u.combo)}${u.double ? `<span class="marque-double">${T("double")}</span>` : ""}</span>
      <span><span class="titre">${esc(u.action.split(" > ").slice(1).join(" > ") || u.action)}</span>
      ${sousTitre ? `<span class="sous">${esc(sousTitre)}</span>` : ""}
      ${u.detail ? `<span class="sous">${esc(u.detail)}</span>` : ""}</span></div>`;

  const bloc = (titre, pourquoi, lignes) => !lignes.length ? "" :
    `<section class="groupe-portee"><h3>${esc(titre)} · ${lignes.length}</h3>
     ${pourquoi ? `<p class="pourquoi">${esc(pourquoi)}</p>` : ""}
     <div class="grille">${lignes.join("")}</div></section>`;

  return menus.map(([nom, us]) => bloc(nom, "",
      us.sort((a, b) => a.ordre - b.ordre).map(u => rangee(u, "")))).join("")
    + bloc(PORTEES().app, T("pourquoi_app"),
        parPortee.app.map(u => rangee(u, u.proprietaire)))
    + bloc(PORTEES().app_externe, T("pourquoi_externe"),
        parPortee.app_externe.map(u => rangee(u, u.proprietaire)))
    + bloc(PORTEES().systeme, T("pourquoi_systeme"),
        parPortee.systeme.map(u => rangee(u, u.proprietaire)))
    + bloc(PORTEES().inconnu, T("pourquoi_inconnu"),
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
    : `<li class="aucun">${T("scan_aucune")}</li>`;
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
  rendreTout();
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
  const app = filtreApp ? D.apps.find(a => a.bundleID === appChoisie) : null;
  const poser = (cible, contenu, secours) => {
    document.getElementById(cible).innerHTML =
      contenu.trim() ? contenu : `<p class="vide">${secours}</p>`;
  };
  if (!app) {
    // Filtre désactivé : on montre tout, en précisant ce que « tout » veut dire ici.
    poser("vue-menu", vueParMenu(null), T("rien_app")(""));
    poser("vue-effet",
      `<p class="pourquoi" style="margin:0 0 18px">${T("sans_app")}</p>`
      + vueCeQuiSePasse({ bundleID: "" }), T("rien_app")(""));
    return;
  }
  if (app.statut !== "ok") {
    const raison = T("illisible")(esc(app.nom), esc(app.detail || app.statut));
    poser("vue-menu", "", raison);
    poser("vue-effet", "", raison);
    return;
  }
  poser("vue-menu", vueParMenu(app), T("rien_app")(esc(app.nom)));
  poser("vue-effet", vueCeQuiSePasse(app), T("rien_app")(esc(app.nom)));
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

/* Sélection des apps à scanner. L'écran ne lance encore rien lui-même : il produit
   la commande exacte à exécuter, exclusions comprises. Le branchement viendra avec
   la question des autorisations. */
const CATALOGUE = D.catalogue || [];
const aScanner = new Set(CATALOGUE.filter(a => !a.exclu).map(a => a.bundleID));

function scanFiltre() {
  const q = sansAccent(document.getElementById("scan-recherche").value.trim());
  return q ? CATALOGUE.filter(a => sansAccent(a.nom).includes(q)
                                || sansAccent(a.bundleID).includes(q))
           : CATALOGUE;
}

function rendreScan() {
  const liste = scanFiltre();
  document.getElementById("scan-grille").innerHTML = liste.length ? liste.map(a =>
    `<label><input type="checkbox" data-id="${esc(a.bundleID)}"
       ${aScanner.has(a.bundleID) ? "checked" : ""}>
     <span>${esc(a.nom)}${a.raison ? `<span class="motif">${T("scan_ecartee")(esc(a.raison))}</span>` : ""}</span>
     </label>`).join("") : `<p class="vide">Aucune application pour cette recherche.</p>`;
  document.getElementById("scan-total").textContent =
    T("scan_affichees")(liste.length, CATALOGUE.length);
  document.getElementById("scan-etat").textContent = T("scan_a_scanner")(aScanner.size);
}

/* Applique la langue à tout ce qui est écrit en dur dans la page, puis redessine
   les vues, dont les libellés sont produits à la volée. */
function appliquerLangue() {
  document.documentElement.lang = LANGUE;
  document.querySelectorAll("[data-t]").forEach(n => { n.textContent = T(n.dataset.t); });
  document.querySelectorAll("[data-t-html]").forEach(n => { n.innerHTML = T(n.dataset.tHtml); });
  document.querySelectorAll("[data-tp]").forEach(n => { n.placeholder = T(n.dataset.tp); });
  document.querySelectorAll("[data-tn]").forEach(n => {
    n.textContent = T("touche_s")(Number(n.dataset.tn));
  });
  document.querySelectorAll(".langues button").forEach(b =>
    b.setAttribute("aria-pressed", String(b.dataset.langue === LANGUE)));
  document.getElementById("detail-fermer").setAttribute("aria-label", T("fermer"));
  document.getElementById("relire-fermer").setAttribute("aria-label", T("fermer"));
  const champ = document.getElementById("filtre-app");
  if (!filtreApp) champ.value = T("toutes_apps");
  document.getElementById("compte-scan").textContent = `${aScanner.size} ${T("scanner_apps")}`;
  rendreTout();
}

function brancherLangues() {
  document.querySelectorAll(".langues button").forEach(b => b.addEventListener("click", () => {
    LANGUE = b.dataset.langue;
    localStorage.setItem("langue", LANGUE);
    appliquerLangue();
  }));
}

function brancherRelire() {
  const boite = document.getElementById("relire");
  document.getElementById("ouvrir-relire").addEventListener("click", () => boite.showModal());
  document.getElementById("relire-fermer").addEventListener("click", () => boite.close());
}

function brancherScan() {
  const boite = document.getElementById("scan");
  document.getElementById("compte-scan").textContent = `${aScanner.size} ${T("scanner_apps")}`;
  document.getElementById("ouvrir-scan").addEventListener("click", () => {
    rendreScan(); boite.showModal();
  });
  document.getElementById("scan-fermer").addEventListener("click", () => boite.close());
  document.getElementById("scan-recherche").addEventListener("input", rendreScan);

  // Cocher en masse ne porte que sur ce que le filtre laisse voir : sans cela,
  // « tout décocher » viderait aussi les apps qu'on ne regarde pas.
  const masse = (etat) => {
    scanFiltre().forEach(a => etat ? aScanner.add(a.bundleID) : aScanner.delete(a.bundleID));
    majCompte();
  };
  const majCompte = () => {
    rendreScan();
    document.getElementById("compte-scan").textContent = `${aScanner.size} ${T("scanner_apps")}`;
  };
  document.getElementById("scan-tout").addEventListener("click", () => masse(true));
  document.getElementById("scan-rien").addEventListener("click", () => masse(false));
  document.getElementById("scan-defaut").addEventListener("click", () => {
    aScanner.clear();
    CATALOGUE.filter(a => !a.exclu).forEach(a => aScanner.add(a.bundleID));
    majCompte();
  });
  document.getElementById("scan-grille").addEventListener("change", (e) => {
    const c = e.target.closest("input[data-id]");
    if (!c) return;
    c.checked ? aScanner.add(c.dataset.id) : aScanner.delete(c.dataset.id);
    document.getElementById("scan-etat").textContent = T("scan_a_scanner")(aScanner.size);
    document.getElementById("compte-scan").textContent = `${aScanner.size} ${T("scanner_apps")}`;
  });
  document.getElementById("scan-lancer").addEventListener("click", () => {
    const bloc = document.getElementById("scan-commande");
    if (!aScanner.size) {
      bloc.hidden = false;
      bloc.textContent = T("scan_rien_coche");
      return;
    }
    const complet = aScanner.size === CATALOGUE.filter(a => !a.exclu).length
      && CATALOGUE.filter(a => !a.exclu).every(a => aScanner.has(a.bundleID));
    bloc.hidden = false;
    bloc.textContent = complet
      ? `${T("scan_defaut_cmd")}
cd ${RACINE} && ./run.sh --all`
      : `${T("scan_perso_cmd")}
cd ${RACINE} && \\
  bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester \\
    --bundle-ids ${[...aScanner].join(",")} --out out/apps && ./run.sh --all`;
  });
}

document.getElementById("recherche").addEventListener("input", rendreTout);
brancherFiltres(); brancherChoixApp(); brancherBasculeApp(); brancherDetail(); brancherScan(); brancherRelire(); brancherLangues();
appliquerLangue();

rendreTout();
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
    keymap = json.loads((ROOT / "out" / "keymap.json").read_text(encoding="utf-8"))
    touches = keymap.get("touches", keymap)
    disposition = keymap.get("disposition", "")
    ecrivables = {c.upper() for niveaux in touches.values() for c in niveaux if c.strip()}

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

    tailles = sorted({
        1 if c.get("double") else 1 + bin(c["mods"]).count("1")
        for c in data["combinaisons"]})
    nombres_html = '<option value="" data-t="toutes"></option>' + "".join(
        f'<option value="{n}" data-tn="{n}"></option>' for n in tailles)

    script = (JS.replace("DONNEES", charge)
                .replace("ORDRE_COUCHES_JS", json.dumps(ORDRE_COUCHES))
                .replace("MODS_BITS", json.dumps({"⇧": 1, "⌃": 2, "⌥": 4, "⌘": 8, "fn": 16},
                                                 ensure_ascii=False))
                .replace("RACINE_PROJET", json.dumps(str(ROOT))))

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
  <div><h1>Overall-shortcuts-inventory-on-MacOS</h1>
  <p class="eyebrow" style="margin:6px 0 0">{machine} · macOS {platform.mac_ver()[0]} · clavier {disposition or "inconnu"} · {date.today().isoformat()}</p></div>
  <div class="actions-scan">
    <button type="button" id="ouvrir-scan" class="bouton-scan">
      <span data-t="scanner"></span>
      <span id="compte-scan"></span>
    </button>
    <button type="button" id="ouvrir-relire" class="bouton-secondaire">
      <span data-t-html="relire"></span>
    </button>
  </div>
  <div class="chiffres">
    <div class="chiffre"><b>{len(data["combinaisons"])}</b><span data-t="stat_combinaisons"></span></div>
    <div class="chiffre {"alerte" if conflits else ""}"><b>{conflits}</b><span data-t="stat_conflits"></span></div>
    <div class="chiffre"><b>{len(lisibles)}</b><span data-t="stat_apps"></span></div>
    <div class="langues" role="group" aria-label="Langue / Language">
      <button type="button" data-langue="fr" aria-pressed="true" title="Français">🇫🇷</button>
      <button type="button" data-langue="en" aria-pressed="false" title="English">🇬🇧</button>
    </div>
  </div>
</header>
<nav>
  <div class="onglets">
    <button data-vue="menu" aria-selected="true" data-t="onglet_menu"></button>
    <button data-vue="effet" aria-selected="false" data-t="onglet_effet"></button>
    <button data-vue="conflits" aria-selected="false" data-t="onglet_conflits"></button>
    <button data-vue="combinaisons" aria-selected="false" data-t="onglet_combinaisons"></button>
  </div>
  <div class="bloc-app">
  <button type="button" id="bascule-app" class="bascule" aria-pressed="true">
    <span class="temoin"></span><span data-t="bascule_app"></span>
  </button>
  <div class="combo-app">
    <input type="text" id="filtre-app" role="combobox" aria-expanded="false"
           aria-controls="liste-app" aria-autocomplete="list" autocomplete="off"
           data-tp="cherche_app">
    <ul id="liste-app" role="listbox" hidden></ul>
  </div>
  </div>
</nav>
<!-- Un seul filtre pour les trois vues : dupliquer les contrôles ferait diverger
     leurs états, et on perdrait le filtre en changeant d'onglet. -->
<div class="filtre">
  <div class="colonne-touches">
    <div class="rangee-filtre">
      <span class="etiquette" data-t="l_modificateurs"></span>
      <div id="mods" class="capsules">{mods_html}</div>
      <input type="text" id="touche-libre" maxlength="6" data-tp="ph_touche">
    </div>
    <div class="rangee-filtre">
      <span class="etiquette" data-t="l_touche"></span>
      <div class="bloc-touches">
        <div class="entete-touches">
          <button type="button" id="vider-touches" class="lien" data-t="effacer_touches"></button>
        </div>
        <div id="touches" class="rangees-touches">{touches_html}</div>
      </div>
    </div>
  </div>
  <div class="colonne-nombre">
    <span class="etiquette" data-t="l_nombre"></span>
    <select id="filtre-nombre">{nombres_html}</select>
  </div>
  <div class="colonne-texte">
    <span class="etiquette" data-t="l_texte"></span>
    <input type="search" id="recherche" data-tp="ph_texte">
    <button type="button" id="vider-filtre" class="lien" data-t="tout_effacer"></button>
  </div>
</div>
<main>
  <section id="onglet-conflits" hidden><div id="vue-conflits"></div></section>
  <section id="onglet-combinaisons" hidden>
    <div id="vue-combinaisons"></div>
  </section>
  <section id="onglet-menu"><div id="vue-menu"></div></section>
  <section id="onglet-effet" hidden><div id="vue-effet"></div></section>
</main>
<dialog id="relire"><div class="detail-corps">
  <div class="detail-tete">
    <h2 style="font-family:var(--display);font-size:20px;margin:0" data-t="relire_titre"></h2>
    <button type="button" id="relire-fermer" class="croix" aria-label="Fermer">✕</button>
  </div>
  <p style="margin:0 0 14px;font-size:14px" data-t-html="relire_intro"></p>
  <code class="commande" style="margin:0">cd {ROOT} && ./run.sh --sources</code>
  <p style="margin:14px 0 0;font-size:13px;color:var(--sourdine)" data-t="relire_apres"></p>
</div></dialog>

<dialog id="detail"><div class="detail-corps">
  <div class="detail-tete">
    <span id="detail-combo" class="combo"></span>
    <button type="button" id="detail-fermer" class="croix" aria-label="Fermer">✕</button>
  </div>
  <div id="detail-contenu"></div>
</div></dialog>

<dialog id="scan"><div class="scan-corps">
  <div class="scan-tete">
    <h2 data-t="scan_titre"></h2>
    <p data-t="scan_intro"></p>
  </div>
  <div class="scan-outils">
    <input type="search" id="scan-recherche" data-tp="scan_filtrer">
    <button type="button" class="bouton" id="scan-tout" data-t="scan_tout"></button>
    <button type="button" class="bouton" id="scan-rien" data-t="scan_rien"></button>
    <button type="button" class="bouton" id="scan-defaut" data-t="scan_defaut"></button>
    <span id="scan-total" class="eyebrow" style="margin:0"></span>
  </div>
  <div class="scan-liste"><div class="scan-grille" id="scan-grille"></div></div>
  <div class="scan-pied">
    <span class="sous" id="scan-etat"></span>
    <span style="display:flex;gap:10px">
      <button type="button" class="bouton" id="scan-fermer" data-t="fermer"></button>
      <button type="button" class="bouton primaire" id="scan-lancer" data-t="scan_lancer"></button>
    </span>
  </div>
  <code class="commande" id="scan-commande" hidden></code>
</div></dialog>

<footer data-t="pied"></footer>
</div><script>{script}</script></body></html>"""


if __name__ == "__main__":
    index = sys.argv[1] if len(sys.argv) > 1 else ROOT / "out" / "index.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "raccourcis.html"
    out.write_text(build(index), encoding="utf-8")
    print(f"✅ {out}  ({out.stat().st_size // 1024} Ko)")
