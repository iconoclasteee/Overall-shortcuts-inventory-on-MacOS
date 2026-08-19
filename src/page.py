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
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model import Keyboard
from tables import keypad_codes

ROOT = Path(__file__).parent.parent

ORDRE_COUCHES = ["pilote", "capture", "systeme", "global", "autre", "menu"]

CSS = """
:root {
  --alu: #DAD8D3; --plaque: #F4F3F0; --creux: #C3C0B9; --encre: #16181C;
  --sourdine: #6E7078; --petrol: #0B6E6E; --vermillon: #B8352A; --ambre: #9A5B12; --zebre: #EAE8E4; --survol: #E1DED8;
  --touche-haut: #FBFAF8; --touche-bas: #D8D5CE; --ombre: rgba(22,24,28,.18);
  --largeur-combo: 168px;
  --rayon: 8px; --rayon-sm: 6px;
  --anneau: color-mix(in srgb, var(--petrol) 45%, transparent);
  --ombre-sm: 0 1px 2px 0 rgba(22,24,28,.06);
  --ombre-md: 0 1px 3px 0 rgba(22,24,28,.10), 0 1px 2px -1px rgba(22,24,28,.10);
  --display: "Space Grotesk", "Avenir Next Condensed", system-ui, sans-serif;
  --corps: "IBM Plex Sans", -apple-system, system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --alu: #131519; --plaque: #1C1F25; --creux: #2E323A; --encre: #E8E7E3;
    --sourdine: #94979F; --petrol: #4FD1C5; --vermillon: #F0776A; --ambre: #E0A458; --zebre: #191C22; --survol: #23272F;
    --touche-haut: #333842; --touche-bas: #1E2128; --ombre: rgba(0,0,0,.5);
    --ombre-sm: 0 1px 2px 0 rgba(0,0,0,.35);
    --ombre-md: 0 1px 3px 0 rgba(0,0,0,.45), 0 1px 2px -1px rgba(0,0,0,.45);
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
  padding: 11px 14px; border-radius: 9px; cursor: pointer; text-align: center;
  background: var(--plaque); color: var(--sourdine); border: 1px solid var(--creux);
  display: flex; align-items: center; justify-content: center;
}
.bouton-secondaire:hover { color: var(--encre); border-color: var(--petrol); }
.bouton-secondaire:focus-visible { outline: 2px solid var(--petrol); outline-offset: 3px; }
.bouton-scan {
  font-family: var(--display); font-size: 15px; font-weight: 600; line-height: 1;
  height: 40px; padding: 0 22px; border-radius: var(--rayon-sm); cursor: pointer;
  background: var(--petrol); color: var(--plaque); border: 1px solid var(--petrol);
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: var(--ombre-md);
  transition: background-color .15s ease;
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
#detail-contenu { display: grid; grid-template-columns: var(--largeur-combo) minmax(0, 1fr); gap: 20px; }
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
/* Boutons — anatomie reprise de shadcn/ui : hauteur constante, rayon doux, ombre
   d'un pixel, transition de couleur, et un anneau de focus épais plutôt qu'un
   contour fin. Ce qui les fait lire comme des boutons, c'est la constance : même
   hauteur, même rayon, même retrait au clic, partout dans la page. */
.bouton {
  font: inherit; font-size: 14px; font-weight: 500; line-height: 1;
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  height: 36px; padding: 0 16px; border-radius: var(--rayon-sm); cursor: pointer;
  border: 1px solid var(--creux); background: var(--plaque); color: var(--encre);
  box-shadow: var(--ombre-sm); white-space: nowrap;
  transition: background-color .15s ease, border-color .15s ease, color .15s ease;
}
.bouton:hover { background: var(--survol); border-color: var(--sourdine); }
.bouton:active { transform: translateY(.5px); }
.bouton.primaire {
  background: var(--petrol); border-color: var(--petrol); color: var(--plaque);
  font-weight: 600;
}
.bouton.primaire:hover { background: color-mix(in srgb, var(--petrol) 88%, var(--encre)); }
.bouton[disabled] { opacity: .5; cursor: not-allowed; }
.bouton:focus-visible, .scan-grille label:focus-within,
input:focus-visible, select:focus-visible {
  outline: 3px solid var(--anneau); outline-offset: 1px;
}

/* Champs de saisie — même hauteur et même rayon que les boutons : c'est cet
   alignement qui fait qu'une barre d'outils se lit comme un ensemble. */
.scan-outils input[type="search"], #filtre-app, #recherche, #touche-libre {
  height: 36px; border-radius: var(--rayon-sm); border: 1px solid var(--creux);
  background: var(--plaque); color: var(--encre); padding: 0 12px; font: inherit;
  font-size: 14px; box-shadow: var(--ombre-sm);
}

.bloc-commande { position: relative; margin: 0 26px 18px; }
.commande {
  display: block; font-family: var(--mono); font-size: 12.5px;
  padding: 14px 92px 14px 16px; margin: 0; background: var(--alu);
  border: 1px solid var(--creux); border-radius: 8px; white-space: pre-wrap;
  word-break: break-all; max-height: 150px; overflow-y: auto;
}
/* Posé dans le coin du bloc plutôt qu'à sa suite : la commande peut défiler,
   le bouton doit rester atteignable sans faire défiler quoi que ce soit. */
.copier {
  position: absolute; top: 8px; right: 8px; font-family: var(--corps);
  font-size: 12px; padding: 5px 10px; border-radius: 6px; cursor: pointer;
  background: var(--plaque); border: 1px solid var(--creux); color: var(--encre);
}
.copier:hover { border-color: var(--petrol); color: var(--petrol); }

/* — Tableau du prochain scan — */
.scan-intro { font-size: 14px; color: var(--sourdine); margin: 0 0 14px; max-width: 90ch; }
.scan-outils { display: flex; gap: 10px; align-items: center; margin: 0 0 16px; flex-wrap: wrap; }
.scan-outils input { flex: 0 0 260px; }
.scan-outils .sous { margin-left: auto; }
/* Trois étapes numérotées plutôt que trois boutons côte à côte : l'ordre compte,
   et une rangée de boutons identiques ne dit pas par lequel commencer. */
.etapes {
  list-style: none; margin: 0 0 18px; padding: 6px;
  border: 1px solid var(--creux); border-radius: var(--rayon);
  background: var(--plaque); box-shadow: var(--ombre-sm);
}
.etape {
  display: grid; grid-template-columns: 30px 1fr auto; gap: 14px; align-items: center;
  padding: 12px 14px; border-radius: var(--rayon-sm);
}
.etape + .etape { border-top: 1px solid var(--alu); }
.etape:hover { background: var(--zebre); }
.puce {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; border-radius: 999px; font-family: var(--display);
  font-size: 14px; font-weight: 700; background: var(--alu); color: var(--sourdine);
  border: 1px solid var(--creux);
}
.etape:first-child .puce { background: var(--petrol); color: var(--plaque); border-color: var(--petrol); }
.etape-texte { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.etape-texte b { font-family: var(--display); font-size: 15px; }
.etape-texte span { font-size: 13px; color: var(--sourdine); line-height: 1.45; }
.ici {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase;
  font-style: normal; color: var(--petrol); border: 1px solid currentColor;
  border-radius: 999px; padding: 1px 7px; margin-left: 10px; vertical-align: 2px;
}
#tableau-scan { width: 100%; border-collapse: collapse; font-size: 15px; table-layout: fixed; }
#tableau-scan th {
  text-align: left; font-family: var(--display); font-size: 13px; letter-spacing: .06em;
  text-transform: uppercase; color: var(--sourdine); font-weight: 600;
  padding: 10px 10px 8px;
  /* Les intitulés reviennent à la ligne : bornés en largeur et gardés sur une seule
     ligne, ils se chevauchaient. */
  white-space: normal; line-height: 1.25; vertical-align: bottom;
  /* Les intitulés restent au bord haut pendant le défilement : à deux cents lignes
     et huit colonnes, une case à cocher sans son intitulé ne veut plus rien dire.
     Le fond doit être opaque, sinon les lignes défilent au travers ; et le trait de
     séparation passe par une ombre intérieure, une bordure ne suivant pas un en-tête
     collant quand les bordures du tableau sont fusionnées. */
  position: sticky; top: 0; z-index: 2;
  background: var(--alu); box-shadow: inset 0 -1px 0 var(--creux);
}
#tableau-scan td { padding: 7px 10px; border-bottom: 1px solid var(--alu); vertical-align: middle; }
/* Une ligne sur deux teintée : à plus de deux cents lignes et huit colonnes, l'œil
   perd la ligne entre la première case et la date. */
#tableau-scan tbody tr:nth-child(even) { background: var(--zebre); }
#tableau-scan tbody tr:hover { background: var(--survol); }
#tableau-scan th:nth-child(-n+3) { text-align: center; width: 84px; }
#tableau-scan .cocher { text-align: center; }
#tableau-scan input[type="checkbox"] { accent-color: var(--petrol); width: 15px; height: 15px; }
/* Écarter est un geste qui retranche : il se signale comme tel, pas comme un choix
   neutre parmi d'autres. */
#tableau-scan .case-exclure { accent-color: var(--vermillon); }
/* Un numéro de version peut être long sans mériter la place qu'il prend. On borne à
   une quinzaine de caractères et on laisse revenir à la ligne les rares qui débordent. */
/* Les colonnes sont serrées à gauche, contre le nom de l'application : c'est la
   comparaison des deux versions qui compte, et l'œil ne doit pas traverser la page
   pour la faire. La dernière colonne, vide, absorbe la place restante. */
#tableau-scan th:nth-child(4) { width: 330px; }
#tableau-scan th:nth-child(5), #tableau-scan th:nth-child(6) { width: 150px; }
#tableau-scan th:nth-child(7) { width: 104px; }
#tableau-scan th:nth-child(8) { width: 176px; }
#tableau-scan .appoint { width: auto; padding: 0; }
#tableau-scan .date span { display: block; white-space: nowrap; }
#tableau-scan .num { font-family: var(--mono); font-size: 13.5px; line-height: 1.35; }
#tableau-scan .num span {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; overflow-wrap: anywhere;
}
#tableau-scan tr.neuve .app { color: var(--petrol); font-weight: 600; }
#tableau-scan tr.majeure .num.installee { color: var(--ambre); font-weight: 600; }
#tableau-scan tr.exclue td { color: var(--sourdine); }
#tableau-scan tr.exclue .app,
#tableau-scan tr.exclue .statut { text-decoration: line-through; }
#tableau-scan tr.exclue .app { color: var(--vermillon); font-weight: 600; }
#tableau-scan .statut-ok { color: var(--sourdine); }
#tableau-scan .statut-ko { color: var(--vermillon); font-weight: 600; }
#tableau-scan .marque {
  font-size: 12px; letter-spacing: .05em; text-transform: uppercase;
  padding: 1px 7px; border-radius: 999px; border: 1px solid currentColor; margin-left: 8px;
  white-space: nowrap;
}
#tableau-scan .m-neuve { color: var(--petrol); }
#tableau-scan .m-majeure { color: var(--ambre); }
#tableau-scan .m-motif { color: var(--sourdine); border: none; padding-left: 0; }

/* — Onglets — */
nav {
  display: flex; justify-content: space-between; align-items: center; gap: 28px;
  margin: 0 0 22px; border-bottom: 1px solid var(--creux);
}
/* Onglets — la pilule de shadcn/ui : un rail creusé, l'onglet actif posé dessus
   comme une carte. Un soulignement se lit comme un titre ; une pastille surélevée
   se lit comme un contrôle sur lequel on clique. */
.onglets {
  display: inline-flex; gap: 2px; background: var(--alu); padding: 4px;
  border-radius: var(--rayon); border: 1px solid var(--creux);
}
nav button {
  font-family: var(--display); font-size: 14px; font-weight: 600; letter-spacing: -.01em;
  background: none; border: 1px solid transparent; border-radius: var(--rayon-sm);
  padding: 8px 14px; color: var(--sourdine); cursor: pointer;
  transition: background-color .15s ease, color .15s ease;
}
nav button:hover { color: var(--encre); }
nav button[aria-selected="true"] {
  color: var(--encre); background: var(--plaque);
  border-color: var(--creux); box-shadow: var(--ombre-sm);
}
nav button:focus-visible { outline: 3px solid var(--anneau); outline-offset: 1px; }
nav button:hover { color: var(--encre); }
nav button:focus-visible, input:focus-visible, select:focus-visible,
.ligne:focus-visible { outline: 2px solid var(--petrol); outline-offset: 3px; }

/* — Touches — */
.combo { display: inline-flex; gap: 3px; align-items: center; flex-wrap: wrap; }
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
  display: grid; grid-template-columns: var(--largeur-combo) minmax(0, 1fr);
  gap: 14px; align-items: start;
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
  display: grid; grid-template-columns: var(--largeur-combo) minmax(0, 1fr); gap: 14px;
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

/* — Contrôles — */
.controles { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
/* Deux natures de filtre : à gauche la combinaison de touches, à droite la recherche
   de libellé. Les séparer évite de les prendre pour un même réglage. */
.filtre {
  display: grid; grid-template-columns: minmax(0, max-content) auto minmax(170px, 1fr);
  gap: 10px 28px; margin: 0 0 28px; padding: 16px 20px; align-items: stretch;
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 10px;
}
.colonne-touches { display: grid; gap: 8px; min-width: 0; }
/* Étiquette puis contrôle, collés : un grand vide entre les deux les dissocie. */
.colonne-nombre {
  display: grid; gap: 6px; justify-items: start; align-content: start; min-width: 0;
  padding-left: 28px; border-left: 1px solid var(--creux);
}
.colonne-nombre select {
  font: inherit; font-size: 14px; padding: 10px 13px; color: var(--encre);
  background: var(--alu); border: 1px solid var(--creux); border-radius: 7px;
}
.colonne-texte {
  display: grid; gap: 6px; justify-items: stretch; align-content: start;
  min-width: 0; padding-left: 28px; border-left: 1px solid var(--creux);
}
/* Sans min-width nul sur la colonne, le champ déborde du panneau. */
.colonne-texte input {
  width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box;
  font-size: 14px; padding: 9px 12px;
}
.colonne-texte .lien { justify-self: start; }
.colonne-texte .etiquette { width: auto; }
.rangee-filtre { display: flex; align-items: flex-start; gap: 14px; flex-wrap: wrap; }
.rangee-filtre .etiquette { padding-top: 9px; }
/* Chercher un texte n'est pas filtrer une combinaison : la ligne est séparée pour
   qu'on ne prenne pas les deux pour un même réglage. */
/* Les touches de fonction occupent leur propre rangée : mêlées aux flèches et aux
   touches d'édition, elles formeraient un pavé de vingt boutons illisible. */
.rangees-touches { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
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
/* Le champ libre est une touche parmi les autres : même gabarit que les capsules. */
#touche-libre {
  width: 118px; flex: none; text-align: center; font-family: var(--mono);
  font-size: 13px; padding: 8px 6px; border-radius: 5px;
}
#touche-libre::placeholder { font-size: 11px; }
#vider-touches { margin-left: auto; align-self: center; }
.bloc-app { display: flex; align-items: stretch; gap: 12px; margin-bottom: 8px; }
.bascule {
  display: inline-flex; align-items: center; gap: 8px; font: inherit; font-size: 13px;
  padding: 9px 13px; border-radius: 7px; cursor: pointer; flex: none;
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
.combo-app { position: relative; width: 280px; flex: none; display: flex; }
.combo-app.inactif { opacity: .5; pointer-events: none; }
.combo-app.inactif input { border-color: var(--creux); background: var(--plaque); }
.combo-app input {
  width: 100%; height: 100%; font-size: 14px; padding: 9px 13px;
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
#pave-select {
  font-family: var(--mono); font-size: 12.5px; padding: 7px 8px; border-radius: 5px;
  background: linear-gradient(var(--touche-haut), var(--touche-bas));
  border: 1px solid var(--creux); color: var(--encre); box-shadow: 0 1.5px 0 var(--ombre);
  margin-left: 6px;
}
#pave-select:focus-visible { outline: 2px solid var(--petrol); outline-offset: 2px; }
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
  display: grid; grid-template-columns: var(--largeur-combo) minmax(0, 1fr);
  gap: 12px; align-items: start;
  padding: 11px 0; border-bottom: 1px solid var(--creux);
}
.resultat .titre { font-size: 15px; }
/* Vert : la commande appartient à l'application elle-même. Le reste — raccourcis
   système et outils globaux — garde la couleur du texte courant. */
.resultat.propre-app .titre { color: var(--petrol); }
/* Le titre de section suit ses lignes : vert pour les menus de l'application,
   neutre pour les raccourcis venus d'ailleurs. */
.groupe-portee h3.titre-app { color: var(--petrol); }
/* Le titre de section suit ses lignes : vert pour les menus de l'app, neutre pour
   le menu Apple et pour les raccourcis venus d'ailleurs. */
.groupe-portee h3.titre-app { color: var(--petrol); }
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
      <span class="sous">${esc(c.usages[0].proprietaire)}${nb > 1 ? ` et ${nb - 1} autre${nb > 2 ? "s" : ""}` : ""}</span></span>
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

  /* Filtré sur une app, cette page ne garde que les conflits dont elle est partie
     prenante : on y vient pour arbitrer ses propres raccourcis. Un conflit entre deux
     outils globaux est actif pendant qu'elle est devant, mais il ne se règle pas ici —
     il reste signalé en rouge dans « Effet d'une frappe », où la question posée est
     bien « que se passe-t-il si je tape ça maintenant ».
     La fiche se restreint au même contexte : les menus des *autres* apps ne sont pas
     en lice pendant que celle-ci est au premier plan. */
  if (id) {
    conflits = conflits
      .map(c => ({ ...c, usages: c.usages.filter(u => u.couche !== "menu" || u.bundle_id === id) }))
      .filter(c => c.usages.some(u => u.bundle_id === id && u.actif));
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
    scanner: "Mettre à jour les raccourcis",
    bascule_app: "Filtre par application", toutes_apps: "Toutes applications",
    cherche_app: "Cherche une application",
    l_modificateurs: "Modificateurs", l_touche: "Touche",
    l_nombre: "Nombre de touches", l_texte: "Libellé de commande",
    pave_numerique: "Pavé numérique",
    effacer_touches: "Effacer les touches", tout_effacer: "Tout effacer",
    copier: "Copier", copie_faite: "Copié ✓", copie_echec: "Copie refusée",
    onglet_scan: "Prochain scan",
    col_app: "Application", col_version: "Version installée",
    col_version_lue: "Version au dernier scan", col_statut: "Statut",
    col_date: "Dernier scan", col_inclure: "Scanner", col_exclure: "Exclure",
    col_source: "Source", jamais: "jamais lue", auto_source: "constaté : cette app déclare des raccourcis globaux",
    verrouille: "exclusion non modifiable : le lancement déclenche une action lourde",
    motif_neuf: "nouvelle", motif_majeur: "version majeure",
    scan_selection: (n) => `${n} à scanner`,
    scan_majeures: "Cocher les versions majeures",
    script_liste: "Mettre à jour la liste des applications",
    script_sources: "Relire le système et les applications sources",
    script_global: "Scanner les applications cochées",
    commencer_ici: "commence ici",
    voir_commande: "Voir la commande",
    note_liste: "Le tableau ci-dessous ne connaît que les applications recensées lors de "
              + "la dernière passe. Sans cette étape, une application installée depuis "
              + "n'y figure pas. N'ouvre aucune application.",
    note_sources: "Rouvre seulement les applications qui déclarent des raccourcis "
                + "globaux. Ce sont elles qui l'emportent sur toutes les autres, et une "
                + "poignée suffit à changer l'inventaire.",
    note_global: "Rouvre une par une les applications cochées dans le tableau. C'est la "
               + "passe longue : compte plusieurs minutes.",
    cmd_entete: "# ⚠️  COPIE CETTE COMMANDE ET COLLE-LA DANS UN TERMINAL.\n"
              + "#    Le navigateur ne peut pas la lancer lui-même : lire les menus d'une\n"
              + "#    application exige l'autorisation d'accessibilité de macOS, que ton\n"
              + "#    terminal possède déjà et qu'une page web n'obtiendra jamais.\n#",
    cmd_liste: "# Recense les applications installées, relit les raccourcis système et les\n"
             + "# préférences des outils, puis reconstruit la page.\n"
             + "# N'ouvre aucune application.",
    cmd_sources: "# Rouvre les applications qui déclarent des raccourcis globaux pour relire\n"
               + "# leurs menus, puis reconstruit tout. Ce sont elles qui l'emportent sur les\n"
               + "# autres : leurs raccourcis accrochent la touche avant les menus.",
    cmd_global: "# Rouvre une par une les applications cochées dans le tableau.\n"
              + "# Compte plusieurs minutes, et une application au premier plan à chaque fois.",
    aucune_source: "Aucune app source : rien à scanner ici.",
    ph_touche: "ou tape la touche", ph_texte: "copier, capture, plein écran…",
    toutes: "Toutes", touche_s: (n) => `${n} touche${n > 1 ? "s" : ""}`,
    double: "double frappe", fermer: "Fermer",
    rien_atteignable: "Rien d'atteignable dans cette app.",
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
    scan_intro: "Chaque application cochée sera ouverte le temps de lire sa barre de menu, "
              + "puis refermée. À lancer quand tu n'utilises pas la machine.",
    scan_filtrer: "Filtrer la liste…", scan_tout: "Tout cocher", scan_rien: "Tout décocher",
    scan_defaut: "Sélection conseillée",
    scan_affichees: (n, total) => `${n} affichées sur ${total}`,
    scan_aucune: "Aucune application pour cette recherche.",
    scan_rien_coche: "Aucune application cochée : rien à scanner.",
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
    scanner: "Update the shortcuts",
    bascule_app: "Filter by app", toutes_apps: "All applications",
    cherche_app: "Search an application",
    l_modificateurs: "Modifiers", l_touche: "Key",
    l_nombre: "Key count", l_texte: "Command label",
    pave_numerique: "Numeric keypad",
    effacer_touches: "Clear keys", tout_effacer: "Clear all",
    copier: "Copy", copie_faite: "Copied ✓", copie_echec: "Copy blocked",
    onglet_scan: "Next scan",
    col_app: "Application", col_version: "Installed version",
    col_version_lue: "Version at last scan", col_statut: "Status",
    col_date: "Last scan", col_inclure: "Scan", col_exclure: "Exclude",
    col_source: "Source", jamais: "never read", auto_source: "observed: this app declares global hotkeys",
    verrouille: "exclusion cannot be lifted: launching triggers a heavy action",
    motif_neuf: "new", motif_majeur: "major version",
    scan_selection: (n) => `${n} to scan`,
    scan_majeures: "Tick major versions",
    script_liste: "Refresh the application list",
    script_sources: "Re-read the system and source applications",
    script_global: "Scan the ticked applications",
    commencer_ici: "start here",
    voir_commande: "Show the command",
    note_liste: "The table below only knows the applications listed during the last "
              + "pass. Without this step, an application installed since will not "
              + "appear. Opens no application.",
    note_sources: "Reopens only the applications that declare global hotkeys. They win "
                + "over every other one, and a handful is enough to change the inventory.",
    note_global: "Reopens the ticked applications one by one. This is the long pass: "
               + "expect several minutes.",
    cmd_entete: "# ⚠️  COPY THIS COMMAND AND PASTE IT INTO A TERMINAL.\n"
              + "#    The browser cannot run it: reading an application's menus requires\n"
              + "#    the macOS accessibility permission, which your terminal already has\n"
              + "#    and a web page will never get.\n#",
    cmd_liste: "# Lists installed applications, re-reads system shortcuts and tool\n"
             + "# preferences, then rebuilds the page.\n"
             + "# Opens no application.",
    cmd_sources: "# Reopens the applications that declare global hotkeys to re-read their\n"
               + "# menus, then rebuilds everything. These are the ones that win over the\n"
               + "# rest: their shortcuts catch the key before any menu does.",
    cmd_global: "# Reopens the ticked applications one by one.\n"
              + "# Expect several minutes, with an application coming to the front each time.",
    aucune_source: "No source app: nothing to scan here.",
    ph_touche: "or type the key", ph_texte: "copy, capture, full screen…",
    toutes: "All", touche_s: (n) => `${n} key${n > 1 ? "s" : ""}`,
    double: "double press", fermer: "Close",
    rien_atteignable: "Nothing reachable in this app.",
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
    scan_intro: "Each checked application will be opened just long enough to read its menu "
              + "bar, then closed. Run it when you are not using the machine.",
    scan_filtrer: "Filter the list…", scan_tout: "Check all", scan_rien: "Uncheck all",
    scan_defaut: "Recommended selection",
    scan_affichees: (n, total) => `${n} shown of ${total}`,
    scan_aucune: "No application for this search.",
    scan_rien_coche: "No application checked: nothing to scan.",
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
   restreint à une app, et le champ de sélection est neutralisé.
   Éteint au chargement : on arrive sur la vue d'ensemble, et on se restreint à une
   app quand on a une question sur elle. */
let filtreApp = false;

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
    touche: touche ? touche.dataset.touche
                   : (document.getElementById("pave-select").value || ""),
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
    if (!etait) {
      document.getElementById("touche-libre").value = "";
      document.getElementById("pave-select").value = "";
    }
    rendreTout();
  }));
  document.getElementById("pave-select").addEventListener("change", () => {
    document.querySelectorAll("#touches button").forEach(x => x.setAttribute("aria-pressed", "false"));
    document.getElementById("touche-libre").value = "";
    rendreTout();
  });
  document.getElementById("touche-libre").addEventListener("input", () => {
    document.querySelectorAll("#touches button").forEach(x => x.setAttribute("aria-pressed", "false"));
    rendreTout();
  });
  document.getElementById("filtre-nombre").addEventListener("change", rendreTout);
  // Rend le panneau de touches à son état neutre : modificateurs compris, puisqu'ils
  // sont des touches eux aussi. Ne touche ni à la recherche de libellé ni au nombre de
  // touches, qui répondent à d'autres questions — c'est « tout effacer » qui les vide.
  const viderTouches = () => {
    document.querySelectorAll("#mods button, #touches button")
      .forEach(x => x.setAttribute("aria-pressed", "false"));
    document.getElementById("touche-libre").value = "";
    document.getElementById("pave-select").value = "";
  };
  document.getElementById("vider-touches").addEventListener("click", () => {
    viderTouches();
    rendreTout();
  });
  document.getElementById("vider-filtre").addEventListener("click", () => {
    viderTouches();
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
    return `<section class="groupe-portee"><h3>${T("touche_s")(n)}</h3>`
      + `<div class="grille">`
      + liste.map(it => {
        const v = it.vainqueurs[0];
        const multi = it.vainqueurs.length > 1;
        const perdus = it.perdants.map(u =>
          `${esc(u.proprietaire)} — ${esc(u.action)}`).join(" · ");
        return `<div class="resultat${
          it.couche === "menu" ? " propre-app" : ""}${
          it.conflit ? " rang-conflit ouvrable" : ""}"${
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

  const rangee = (u, sousTitre) => `<div class="resultat${
      u.couche === "menu" ? " propre-app" : ""}${u.conflit ? " rang-conflit ouvrable" : ""}"${
      u.conflit ? ` role="button" tabindex="0" data-cle="${esc(u.cle)}"` : ""}>
      <span class="combo">${caps(u.combo)}${u.double ? `<span class="marque-double">${T("double")}</span>` : ""}</span>
      <span><span class="titre">${esc(u.action.split(" > ").slice(1).join(" > ") || u.action)}</span>
      ${sousTitre ? `<span class="sous">${esc(sousTitre)}</span>` : ""}
      ${u.detail ? `<span class="sous">${esc(u.detail)}</span>` : ""}</span></div>`;

  // Le menu Apple porte son logo plutôt que son nom : c'est ainsi qu'il s'affiche
  // dans la barre de menu, où le mot « Apple » ne figure nulle part.
  const nommer = (t) => t.replace(/(^|· )Apple$/, "$1\uF8FF")
                         // Chaque app a un menu à son nom : en mode toutes apps, le
                         // préfixe le répétait à l'identique.
                         .replace(/^(.+) · \1$/, "$1");
  const bloc = (titre, pourquoi, lignes, vert) => !lignes.length ? "" :
    `<section class="groupe-portee"><h3${vert ? ' class="titre-app"' : ""}>${
       esc(nommer(titre))}</h3>
     ${pourquoi ? `<p class="pourquoi">${esc(pourquoi)}</p>` : ""}
     <div class="grille">${lignes.join("")}</div></section>`;

  return menus.map(([nom, us]) => bloc(nom, "",
      us.sort((a, b) => a.ordre - b.ordre).map(u => rangee(u, "")),
      true)).join("")
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

function choisirOnglet(vue) {
  document.querySelectorAll(".onglets button").forEach(x =>
    x.setAttribute("aria-selected", String(x.dataset.vue === vue)));
  document.querySelectorAll("main > section").forEach(s =>
    s.hidden = s.id !== "onglet-" + vue);
  if (vue === "scan") rendreScan();
}
document.querySelectorAll(".onglets button").forEach(b =>
  b.addEventListener("click", () => choisirOnglet(b.dataset.vue)));

/* Prochain scan. L'écran ne lance rien lui-même : il produit la commande exacte à
   exécuter, réglages compris. Le branchement direct viendra avec la question des
   autorisations. Les choix vivent en mémoire jusqu'à ce que la commande les écrive
   dans out/reglages-scan.json — ce fichier reste la seule vérité, et la page le relit
   à chaque production. */
const CATALOGUE = D.catalogue || [];
const REGLAGES = D.reglages || {};
const SOURCES_AUTO = new Set(D.sources || []);
const exclues = new Set(REGLAGES.exclues || []);
const incluses = new Set(REGLAGES.incluses || []);
const sourcesChoisies = new Set(REGLAGES.sources || []);
const FICHES = Object.fromEntries((D.apps || []).map(a => [a.bundleID, a]));

const LIGNES = CATALOGUE.map(a => {
  const f = FICHES[a.bundleID] || {};
  return {
    id: a.bundleID, nom: a.nom,
    installee: a.version || null, lue: f.version || null,
    statut: f.statut || null, scanneLe: f.scanne_le || null,
    raison: a.raison || null, verrou: !!a.verrou, excluCalcule: !!a.exclu,
  };
});

function estExclue(l) {
  if (l.verrou) return true;
  if (incluses.has(l.id)) return false;
  if (exclues.has(l.id)) return true;
  return l.excluCalcule;
}

/* Le premier nombre du numéro de version : « 3.7.8 » donne « 3 ». Une version
   illisible ou absente compte comme un écart : mieux vaut relire pour rien que
   présenter des raccourcis périmés comme à jour.
   (Exemple volontairement à trois nombres : à quatre, il ressemblerait à une
   adresse IP et ferait sonner verifier-publication.sh à tort.) */
function majeur(v) { const m = String(v == null ? "" : v).match(/\d+/); return m ? m[0] : null; }
function jamaisLue(l) { return !l.scanneLe; }
function ecartMajeur(l) {
  if (jamaisLue(l)) return false;
  const a = majeur(l.installee), b = majeur(l.lue);
  return a === null || b === null || a !== b;
}
function conseillee(l) { return !estExclue(l) && (jamaisLue(l) || ecartMajeur(l)); }

const aScanner = new Set();
function selectionConseillee() {
  aScanner.clear();
  LIGNES.forEach(l => { if (conseillee(l)) aScanner.add(l.id); });
}
selectionConseillee();

function scanFiltre() {
  const q = sansAccent(document.getElementById("scan-recherche").value.trim());
  return q ? LIGNES.filter(l => sansAccent(l.nom).includes(q)
                             || sansAccent(l.id).includes(q))
           : LIGNES;
}

function rendreScan() {
  const liste = scanFiltre();
  // Les trois cases d'abord : ce qu'on décide, avant ce qu'on constate.
  const entetes = ["col_inclure", "col_exclure", "col_source", "col_app",
                   "col_version", "col_version_lue", "col_statut", "col_date"];
  const corps = liste.map(l => {
    const exclue = estExclue(l);
    const neuve = jamaisLue(l), majeure = ecartMajeur(l);
    const classes = [exclue ? "exclue" : "", neuve ? "neuve" : "", majeure ? "majeure" : ""]
      .filter(Boolean).join(" ");
    const marque = neuve ? `<span class="marque m-neuve">${T("motif_neuf")}</span>`
                 : majeure ? `<span class="marque m-majeure">${T("motif_majeur")}</span>`
                 : l.raison ? `<span class="marque m-motif">${esc(l.raison)}</span>` : "";
    const auto = SOURCES_AUTO.has(l.id) && !sourcesChoisies.has(l.id);
    return `<tr class="${classes}">
      <td class="cocher"><input type="checkbox" data-role="inclure" data-id="${esc(l.id)}"
          ${aScanner.has(l.id) ? "checked" : ""} ${exclue ? "disabled" : ""}></td>
      <td class="cocher"><input type="checkbox" class="case-exclure" data-role="exclure"
          data-id="${esc(l.id)}" ${exclue ? "checked" : ""} ${l.verrou ? "disabled" : ""}
          title="${l.verrou ? esc(T("verrouille")) : ""}"></td>
      <td class="cocher"><input type="checkbox" data-role="source" data-id="${esc(l.id)}"
          ${auto || sourcesChoisies.has(l.id) ? "checked" : ""} ${auto ? "disabled" : ""}
          title="${auto ? esc(T("auto_source")) : ""}"></td>
      <td class="app">${esc(l.nom)}${marque}</td>
      <td class="num installee" title="${esc(l.installee || "")}"><span>${
        esc(l.installee || "—")}</span></td>
      <td class="num" title="${esc(l.lue || "")}"><span>${esc(l.lue || "—")}</span></td>
      <td class="statut ${l.statut === "ok" || !l.statut ? "statut-ok" : "statut-ko"}">${
        esc(l.statut || T("jamais"))}</td>
      <td class="num date"><span>${esc(l.scanneLe || "—")}</span></td>
      <td class="appoint"></td>
    </tr>`;
  }).join("");
  document.getElementById("vue-scan").innerHTML = liste.length
    ? `<table id="tableau-scan"><thead><tr>${
        entetes.map(c => `<th>${T(c)}</th>`).join("")}<th class="appoint"></th></tr></thead>`
      + `<tbody>${corps}</tbody></table>`
    : `<p class="vide">${T("scan_aucune")}</p>`;
  document.getElementById("scan-total").textContent =
    `${T("scan_affichees")(liste.length, LIGNES.length)} · ${T("scan_selection")(aScanner.size)}`;
}


function appliquerLangue() {
  document.documentElement.lang = LANGUE;
  document.querySelectorAll("[data-t]").forEach(n => { n.textContent = T(n.dataset.t); });
  document.querySelectorAll("[data-t-html]").forEach(n => { n.innerHTML = T(n.dataset.tHtml); });
  document.querySelectorAll("[data-tp]").forEach(n => { n.placeholder = T(n.dataset.tp); });
  document.querySelectorAll("#pave-select option[data-t]").forEach(o => {
    o.textContent = T(o.dataset.t);
  });
  document.querySelectorAll("[data-tn]").forEach(n => {
    n.textContent = T("touche_s")(Number(n.dataset.tn));
  });
  document.querySelectorAll(".langues button").forEach(b =>
    b.setAttribute("aria-pressed", String(b.dataset.langue === LANGUE)));
  document.getElementById("detail-fermer").setAttribute("aria-label", T("fermer"));
  const champ = document.getElementById("filtre-app");
  if (!filtreApp) champ.value = T("toutes_apps");
  rendreTout();
}

async function copierTexte(texte) {
  try {
    await navigator.clipboard.writeText(texte);
    return true;
  } catch (e) {
    const zone = document.createElement("textarea");
    zone.value = texte;
    zone.setAttribute("readonly", "");
    zone.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(zone);
    zone.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e2) { ok = false; }
    document.body.removeChild(zone);
    return ok;
  }
}

function brancherCopie() {
  document.querySelectorAll("button.copier").forEach(bouton => {
    bouton.addEventListener("click", async () => {
      const bloc = bouton.parentElement.querySelector(".commande");
      const ok = await copierTexte(bloc.dataset.commande || bloc.textContent);
      bouton.textContent = T(ok ? "copie_faite" : "copie_echec");
      setTimeout(() => { bouton.textContent = T("copier"); }, 1600);
    });
  });
}

function brancherLangues() {
  document.querySelectorAll(".langues button").forEach(b => b.addEventListener("click", () => {
    LANGUE = b.dataset.langue;
    localStorage.setItem("langue", LANGUE);
    appliquerLangue();
  }));
}


function brancherScan() {
  document.getElementById("ouvrir-scan").addEventListener("click", () => choisirOnglet("scan"));
  document.getElementById("scan-recherche").addEventListener("input", rendreScan);

  // Cocher en masse ne porte que sur ce que le filtre laisse voir : sans cela,
  // « tout décocher » viderait aussi les apps qu'on ne regarde pas.
  const masse = (etat) => {
    scanFiltre().forEach(l => {
      if (etat && estExclue(l)) return;
      etat ? aScanner.add(l.id) : aScanner.delete(l.id);
    });
    rendreScan();
  };
  document.getElementById("scan-tout").addEventListener("click", () => masse(true));
  document.getElementById("scan-rien").addEventListener("click", () => masse(false));
  document.getElementById("scan-defaut").addEventListener("click", () => {
    selectionConseillee(); rendreScan();
  });
  // Ajoute à la sélection en cours plutôt que de la remplacer : on coche par
  // couches successives, sans perdre ce qu'on venait de choisir à la main.
  document.getElementById("scan-majeures").addEventListener("click", () => {
    LIGNES.forEach(l => { if (!estExclue(l) && ecartMajeur(l)) aScanner.add(l.id); });
    rendreScan();
  });

  document.getElementById("vue-scan").addEventListener("change", (e) => {
    const c = e.target.closest("input[data-id]");
    if (!c) return;
    const id = c.dataset.id;
    if (c.dataset.role === "inclure") {
      c.checked ? aScanner.add(id) : aScanner.delete(id);
    } else if (c.dataset.role === "exclure") {
      // Deux listes plutôt qu'une : le programme écarte déjà les jeux et les
      // désinstalleurs, il faut donc pouvoir dire « malgré tout, prends-la ».
      exclues.delete(id); incluses.delete(id);
      (c.checked ? exclues : incluses).add(id);
      if (c.checked) aScanner.delete(id);
    } else {
      c.checked ? sourcesChoisies.add(id) : sourcesChoisies.delete(id);
    }
    rendreScan();
  });

  // Trois gestes, trois commandes. Recenser ne coûte rien et n'ouvre aucune app ;
  // relire les outils en ouvre une poignée ; la passe complète les ouvre toutes.
  // Les confondre obligerait à subir la plus chère pour obtenir la moins chère.
  const MOISSONNEUR = "bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester";

  function afficher(commentaire, commande) {
    const bloc = document.getElementById("scan-commande");
    const cadre = document.getElementById("bloc-scan-commande");
    const bouton = cadre.querySelector(".copier");
    cadre.hidden = false;
    if (!commande) {
      bloc.textContent = commentaire;
      delete bloc.dataset.commande;
      bouton.hidden = true;
      return;
    }
    bloc.textContent = `${T("cmd_entete")}\n${commentaire}\n${commande}`;
    // Le commentaire dit ce qu'on copie, mais ne part pas dans le presse-papiers :
    // collé dans zsh, un « # » n'y est pas toujours traité comme un commentaire.
    bloc.dataset.commande = commande;
    bouton.hidden = false;
  }

  // --force est indispensable dès qu'on relit : sans lui le moissonneur saute toute
  // app dont la fiche existe déjà, c'est-à-dire précisément celles qu'on vient
  // cocher parce que leur version a changé.
  function moissonner(ids) {
    const reglages = JSON.stringify({
      exclues: [...exclues], incluses: [...incluses], sources: [...sourcesChoisies],
    });
    return `cd ${RACINE} && \\
  printf '%s' '${reglages}' > out/reglages-scan.json && \\
  ${MOISSONNEUR} \\
    --bundle-ids ${ids.join(",")} --force --out out/apps && \\
  ./run.sh --sources`;
  }

  document.getElementById("script-liste").addEventListener("click", () => {
    afficher(T("cmd_liste"), `cd ${RACINE} && ./run.sh --sources`);
  });

  document.getElementById("script-sources").addEventListener("click", () => {
    const ids = LIGNES
      .filter(l => !estExclue(l) && (SOURCES_AUTO.has(l.id) || sourcesChoisies.has(l.id)))
      .map(l => l.id);
    if (!ids.length) return afficher(T("aucune_source"), null);
    afficher(T("cmd_sources"), moissonner(ids));
  });

  document.getElementById("script-global").addEventListener("click", () => {
    if (!aScanner.size) return afficher(T("scan_rien_coche"), null);
    afficher(T("cmd_global"), moissonner([...aScanner]));
  });
}

document.getElementById("recherche").addEventListener("input", rendreTout);
brancherFiltres(); brancherChoixApp(); brancherBasculeApp(); brancherDetail(); brancherScan(); brancherLangues(); brancherCopie();
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
    # Le pavé numérique est proposé au complet, comme les touches de fonction : il
    # forme un bloc physique, en montrer la moitié laisserait croire que le reste
    # n'existe pas. Les libellés viennent de la disposition active.
    clavier = Keyboard()
    pave = [t for t in (clavier.label(c, 0) for c in keypad_codes()) if t]
    # Chiffres d'abord, opérateurs ensuite : l'ordre des codes de touches n'a aucun
    # rapport avec la façon dont on lit un pavé.
    pave.sort(key=lambda t: (not t.split()[-1].isdigit(), t.split()[-1]))

    autres = sorted({t for t in vues if t.strip() and t.upper() not in ecrivables
                     and not (t.startswith("F") and t[1:].isdigit())
                     and t not in pave},
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

    pave_html = "".join(
        f'<option value="{html_std.escape(t, quote=True)}">'
        f'{html_std.escape(t.removeprefix("Pavé "))}</option>' for t in pave)
    touches_html = (
        f'<div class="capsules">{capsules(fonctions)}</div>'
        f'<div class="capsules">{capsules(autres)}'
        f'<select id="pave-select" aria-label="Pavé numérique">'
        f'<option value="" data-t="pave_numerique"></option>{pave_html}</select>'
        f'</div>')
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
  <p class="eyebrow" style="margin:6px 0 0">{machine} · macOS {platform.mac_ver()[0]} · clavier {disposition or "inconnu"} · {datetime.now().strftime("%Y-%m-%d %Hh%M")}</p></div>
  <div class="actions-scan">
    <button type="button" id="ouvrir-scan" class="bouton-scan">
      <span data-t="scanner"></span>
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
    <button data-vue="scan" aria-selected="false" data-t="onglet_scan"></button>
  </div>
  <div class="bloc-app">
  <button type="button" id="bascule-app" class="bascule" aria-pressed="false">
    <span class="temoin"></span><span data-t="bascule_app"></span>
  </button>
  <div class="combo-app">
    <input type="text" id="filtre-app" role="combobox" aria-expanded="false"
           aria-controls="liste-app" aria-autocomplete="list" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
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
      <input type="text" id="touche-libre" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" maxlength="4" data-tp="ph_touche">
      <button type="button" id="vider-touches" class="lien" data-t="effacer_touches"></button>
    </div>
    <div class="rangee-filtre">
      <span class="etiquette" data-t="l_touche"></span>
      <div id="touches" class="rangees-touches">{touches_html}</div>
    </div>
  </div>
  <div class="colonne-nombre">
    <span class="etiquette" data-t="l_nombre"></span>
    <select id="filtre-nombre">{nombres_html}</select>
  </div>
  <div class="colonne-texte">
    <span class="etiquette" data-t="l_texte"></span>
    <input type="search" id="recherche" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" data-tp="ph_texte">
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
  <section id="onglet-scan" hidden>
    <p class="scan-intro" data-t="scan_intro"></p>
    <div class="scan-outils">
      <input type="search" id="scan-recherche" autocomplete="off" autocorrect="off"
             autocapitalize="off" spellcheck="false" data-tp="scan_filtrer">
      <button type="button" class="bouton" id="scan-defaut" data-t="scan_defaut"></button>
      <button type="button" class="bouton" id="scan-majeures" data-t="scan_majeures"></button>
      <button type="button" class="bouton" id="scan-tout" data-t="scan_tout"></button>
      <button type="button" class="bouton" id="scan-rien" data-t="scan_rien"></button>
      <span id="scan-total" class="sous"></span>
    </div>
    <ol class="etapes">
      <li class="etape">
        <span class="puce">1</span>
        <div class="etape-texte">
          <b data-t="script_liste"></b><em class="ici" data-t="commencer_ici"></em>
          <span data-t="note_liste"></span>
        </div>
        <button type="button" class="bouton primaire" id="script-liste" data-t="voir_commande"></button>
      </li>
      <li class="etape">
        <span class="puce">2</span>
        <div class="etape-texte">
          <b data-t="script_sources"></b>
          <span data-t="note_sources"></span>
        </div>
        <button type="button" class="bouton" id="script-sources" data-t="voir_commande"></button>
      </li>
      <li class="etape">
        <span class="puce">3</span>
        <div class="etape-texte">
          <b data-t="script_global"></b>
          <span data-t="note_global"></span>
        </div>
        <button type="button" class="bouton" id="script-global" data-t="voir_commande"></button>
      </li>
    </ol>
    <div class="bloc-commande" id="bloc-scan-commande" hidden>
      <code class="commande" id="scan-commande"></code>
      <button type="button" class="copier" data-t="copier"></button>
    </div>
    <div id="vue-scan"></div>
  </section>
</main>
<dialog id="detail"><div class="detail-corps">
  <div class="detail-tete">
    <span id="detail-combo" class="combo"></span>
    <button type="button" id="detail-fermer" class="croix" aria-label="Fermer">✕</button>
  </div>
  <div id="detail-contenu"></div>
</div></dialog>

<footer data-t="pied"></footer>
</div><script>{script}</script></body></html>"""


if __name__ == "__main__":
    index = sys.argv[1] if len(sys.argv) > 1 else ROOT / "out" / "index.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "raccourcis.html"
    out.write_text(build(index), encoding="utf-8")
    print(f"✅ {out}  ({out.stat().st_size // 1024} Ko)")
