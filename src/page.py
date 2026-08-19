"""HTML rendering of the index — one self-contained file, six views.

Visual stance: the subject is the keyboard. Combinations are therefore rendered as
physical keys, and the signature element is **the interception stack** — a keystroke
descends the layers (driver, event tap, system, global, menu) and the first one to claim
it swallows it. That is the real mechanism, and it is what makes "who wins?" readable at a
glance instead of a sentence to decipher.
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
  --sourdine: #4C4F57; --petrol: #0B6E6E; --vermillon: #B8352A; --ambre: #9A5B12; --zebre: #EAE8E4; --survol: #E1DED8;
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
    --sourdine: #A3A6AE; --petrol: #4FD1C5; --vermillon: #F0776A; --ambre: #E0A458; --zebre: #191C22; --survol: #23272F;
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

/* — Header: the thesis, not a decorative banner — */
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

/* — Starting a scan — */
.actions-scan { justify-self: center; display: flex; align-items: stretch; gap: 10px; }
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
.scan-outils {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 14px 26px; border-bottom: 1px solid var(--creux);
}
.scan-outils input[type="search"] { flex: 1; min-width: 200px; max-width: 340px; font-size: 14px; padding: 9px 12px; }
/* Buttons — anatomy taken from shadcn/ui: constant height, soft radius, one-pixel
   shadow, colour transition, and a thick focus ring rather than a thin outline. What
   makes them read as buttons is the consistency: same height, same radius, same press
   inset, everywhere in the page. */
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
input:focus-visible, select:focus-visible {
  outline: 3px solid var(--anneau); outline-offset: 1px;
}

/* Input fields — same height and radius as the buttons: that alignment is what makes a
   toolbar read as one thing. */
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
/* Placed in the block's corner rather than after it: the command can scroll, the button
   must stay reachable without scrolling anything. */
.copier {
  position: absolute; top: 8px; right: 8px; font-family: var(--corps);
  font-size: 12px; padding: 5px 10px; border-radius: 6px; cursor: pointer;
  background: var(--plaque); border: 1px solid var(--creux); color: var(--encre);
}
.copier:hover { border-color: var(--petrol); color: var(--petrol); }

/* — Free shortcuts — */
.libres-note { font-size: 14px; color: var(--sourdine); margin: 18px 0 0; }
/* One single cross-table: modifiers as columns, grouped by key count and separated by a
   rule; keys as rows. Nothing wraps — a combination split across two lines stops being
   readable. */
.libres-table { border-collapse: collapse; font-size: 15px; }
.libres-table th, .libres-table td { white-space: nowrap; }
.libres-table thead th {
  position: sticky; background: var(--alu); text-align: center; padding: 6px 8px;
  z-index: 2;
}
.libres-table thead tr:first-child th { top: 0; }
.libres-table thead tr:last-child th { top: 32px; box-shadow: inset 0 -1px 0 var(--creux); }
.libres-table .groupe {
  font-family: var(--display); font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--sourdine); font-weight: 600; padding-bottom: 4px;
}
.libres-total { font-family: var(--mono); font-size: 11px; letter-spacing: .04em; margin-left: 10px; }
.libres-table th[scope="row"] {
  font-family: var(--mono); font-size: 15px; font-weight: 600; text-align: right;
  padding: 0 14px 0 0; color: var(--sourdine);
}
.libres-table td { padding: 2px 3px; }
.libres-table tbody tr:nth-child(even) { background: var(--zebre); }
.libres-table .borne { border-right: 2px solid var(--creux); padding-right: 10px; }
/* Every free combination is a button: one click copies it, since its purpose is to be
   carried over into another program's settings. */
.libres-table .libre {
  font: inherit; font-family: var(--mono); font-size: 14.5px; cursor: pointer;
  display: block; width: 100%; padding: 4px 10px; border-radius: 5px;
  background: var(--touche-haut); border: 1px solid var(--creux); border-bottom-width: 2px;
  color: var(--encre);
  transition: background-color .12s ease, border-color .12s ease;
}
.libres-table .libre:hover { border-color: var(--petrol); color: var(--petrol); }
.libres-table .libre.copie { background: var(--petrol); border-color: var(--petrol); color: var(--plaque); }
.libres-table .libre:focus-visible { outline: 3px solid var(--anneau); outline-offset: 1px; }

/* — Next-scan table — */
/* The warning concerns an action that takes over the screen for several minutes: it must
   be read before the rest, so it is larger and framed, not blended into the text. */
.avertissement {
  display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: start;
  margin: 0 0 16px; padding: 16px 18px; border-radius: var(--rayon);
  border: 1px solid var(--ambre); background: color-mix(in srgb, var(--ambre) 9%, var(--plaque));
}
.avertissement span { font-size: 22px; line-height: 1.2; }
.avertissement p {
  margin: 0; font-size: 16px; font-weight: 600; line-height: 1.5; color: var(--encre);
}
.scan-intro { font-size: 14px; color: var(--sourdine); margin: 0 0 18px; }
.scan-intro p { margin: 0 0 10px; }
.scan-intro ul { margin: 0 0 10px; padding-left: 20px; }
.scan-intro li { margin: 0 0 5px; }
.scan-intro b { color: var(--encre); }
.scan-outils { display: flex; gap: 10px; align-items: center; margin: 0 0 16px; flex-wrap: wrap; }
.scan-outils input { flex: 0 0 260px; }
.scan-outils .sous { margin-left: auto; }
/* Three numbered steps rather than three buttons side by side: order matters, and a row
   of identical buttons does not say which one to start with. */
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
/* The step whose command is on screen: without this marker — three identical blocks and
   one visible command — you no longer know which one you are about to copy. */
.etape.choisie { background: var(--zebre); box-shadow: inset 3px 0 0 var(--petrol); }
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
.ici, .exige, .sans-exige {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase;
  font-style: normal; border: 1px solid currentColor;
  border-radius: 999px; padding: 1px 7px; margin-left: 10px; vertical-align: 2px;
  white-space: nowrap;
}
.ici { color: var(--petrol); }
/* What the step requires of the system, said on the step itself: that is the question you
   ask before running it, not after. */
.exige { color: var(--ambre); }
.sans-exige { color: var(--sourdine); }
#tableau-scan { width: 100%; border-collapse: collapse; font-size: 15px; table-layout: fixed; }
#tableau-scan th {
  text-align: left; font-family: var(--display); font-size: 13px; letter-spacing: .06em;
  text-transform: uppercase; color: var(--sourdine); font-weight: 600;
  padding: 10px 10px 8px;
  /* Headings wrap: bounded in width and kept on one line, they overlapped. */
  white-space: normal; line-height: 1.25; vertical-align: bottom;
  /* Headings stay pinned to the top edge while scrolling: at two hundred rows and eight
     columns, a checkbox without its heading means nothing any more. The background must
     be opaque, otherwise rows scroll through it; and the separating rule goes through an
     inset shadow, since a border does not follow a sticky header when the table's borders
     are collapsed. */
  position: sticky; top: 0; z-index: 2;
  background: var(--alu); box-shadow: inset 0 -1px 0 var(--creux);
}
#tableau-scan td { padding: 7px 10px; border-bottom: 1px solid var(--alu); vertical-align: middle; }
/* Every other row tinted: past two hundred rows and eight columns, the eye loses the row
   between the first checkbox and the date. */
#tableau-scan tbody tr:nth-child(even) { background: var(--zebre); }
#tableau-scan tbody tr:hover { background: var(--survol); }
#tableau-scan th:nth-child(-n+3) { text-align: center; width: 84px; }
#tableau-scan .cocher { text-align: center; }
#tableau-scan input[type="checkbox"] { accent-color: var(--petrol); width: 15px; height: 15px; }
/* Excluding is a subtractive act: it announces itself as one, not as a neutral choice
   among others. */
#tableau-scan .case-exclure { accent-color: var(--vermillon); }
/* A version string can be long without deserving the room it takes. We bound it to about
   fifteen characters and let the rare overflowing ones wrap. */
/* The columns are packed to the left, against the application name: what matters is
   comparing the two versions, and the eye should not cross the page to do it. The last
   column, empty, absorbs the remaining room. */
#tableau-scan th:nth-child(4) { width: 330px; }
#tableau-scan th:nth-child(5), #tableau-scan th:nth-child(6) { width: 150px; }
#tableau-scan th:nth-child(7) { width: 104px; }
#tableau-scan th:nth-child(8) { width: 176px; }
#tableau-scan th:nth-child(9) { width: 96px; text-align: right; }
#tableau-scan .lus { text-align: right; }
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
/* Read without trouble, but finding nothing: that is not a failure, and it is not a
   success either. Saying so beats displaying "ok". */
#tableau-scan .statut-vide { color: var(--ambre); font-weight: 600; }
#tableau-scan .marque {
  font-size: 12px; letter-spacing: .05em; text-transform: uppercase;
  padding: 1px 7px; border-radius: 999px; border: 1px solid currentColor; margin-left: 8px;
  white-space: nowrap;
}
#tableau-scan .m-neuve { color: var(--petrol); }
#tableau-scan .m-majeure { color: var(--ambre); }
#tableau-scan .m-motif { color: var(--sourdine); border: none; padding-left: 0; }

/* — Tabs — */
nav {
  display: flex; justify-content: space-between; align-items: center; gap: 28px;
  margin: 0 0 22px; border-bottom: 1px solid var(--creux);
}
/* Tabs — shadcn/ui's pill: a recessed rail with the active tab resting on it like a
   card. An underline reads as a heading; a raised pill reads as a control you click. */
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

/* — Keys — */
.combo { display: inline-flex; gap: 3px; align-items: center; flex-wrap: wrap; }
.cap {
  font-family: var(--mono); font-size: 13px; font-weight: 500; line-height: 1;
  min-width: 26px; padding: 7px 6px; text-align: center;
  background: linear-gradient(var(--touche-haut), var(--touche-bas));
  border: 1px solid var(--creux); border-radius: 5px;
  box-shadow: 0 1.5px 0 var(--ombre); white-space: nowrap;
}
.cap.large { padding-left: 10px; padding-right: 10px; }

/* — Interception stack: the signature element — */
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

/* — Lists — */
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

/* — Controls — */
/* Two kinds of filter: the key combination on the left, the label search on the right.
   Separating them avoids taking the two for one setting. */
.filtre {
  display: grid; grid-template-columns: minmax(0, max-content) auto minmax(170px, 1fr);
  gap: 10px 28px; margin: 0 0 28px; padding: 16px 20px; align-items: stretch;
  background: var(--plaque); border: 1px solid var(--creux); border-radius: 10px;
}
.colonne-touches { display: grid; gap: 8px; min-width: 0; }
/* Label then control, tight together: a wide gap between the two pulls them apart. */
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
/* Without min-width zero on the column, the field overflows the panel. */
.colonne-texte input {
  width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box;
  font-size: 14px; padding: 9px 12px;
}
.colonne-texte .lien { justify-self: start; }
.colonne-texte .etiquette { width: auto; }
.rangee-filtre { display: flex; align-items: flex-start; gap: 14px; flex-wrap: wrap; }
.rangee-filtre .etiquette { padding-top: 9px; }
/* Searching text is not filtering a combination: the row is separated so the two are not
   taken for one setting. */
/* Function keys get their own row: mixed in with the arrows and editing keys they would
   form an unreadable block of twenty buttons. */
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
/* The free-text field is a key among the others: same shape as the caps. */
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
/* Green: the command belongs to the application itself. Everything else — system
   shortcuts and global tools — keeps the body text colour. */
.resultat.propre-app .titre { color: var(--petrol); }
/* The section heading follows its rows: green for the application's menus, neutral for
   shortcuts coming from elsewhere. */
.groupe-portee h3.titre-app { color: var(--petrol); }
/* The section heading follows its rows: green for the app's menus, neutral for the Apple
   menu and for shortcuts coming from elsewhere. */
.groupe-portee h3.titre-app { color: var(--petrol); }
/* A disputed combination is spotted by colour: the row says what the command does, not
   that another claimant might take it away. */
.resultat.rang-conflit .titre { color: var(--vermillon); }
.resultat.rang-conflit .cap { border-color: var(--vermillon); color: var(--vermillon); }
.resultat.ouvrable { cursor: pointer; }
.resultat.ouvrable:hover { background: var(--alu); }
.resultat.ouvrable:focus-visible { outline: 2px solid var(--vermillon); outline-offset: 2px; }
/* A double tap is not a combination: it flags itself, otherwise "⌘⌘" reads as two keys
   pressed together. */
.marque-double {
  font-family: var(--mono); font-size: 10px; letter-spacing: .07em; text-transform: uppercase;
  padding: 3px 7px; border-radius: 4px; margin-left: 7px; white-space: nowrap;
  background: color-mix(in srgb, var(--petrol) 18%, transparent); color: var(--petrol);
}
.perdu {
  display: block; font-family: var(--mono); font-size: 11.5px; color: var(--sourdine);
  margin-top: 3px; padding-left: 11px; border-left: 2px solid var(--creux);
}
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
  // "fn" is written with two characters: it must be pulled out before walking the rest,
  // otherwise it would end up stuck to the main key inside a single cap.
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
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* The stack: one storey per layer, occupied if a shortcut hooks there.
   The winning storey is the highest occupied one in the ordering. */
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

  /* Filtered on one app, this page keeps only the conflicts it is party to: you come
     here to arbitrate your own shortcuts. A conflict between two global tools is live
     while that app is in front, but it is not settled here — it stays flagged in red in
     "What a keystroke does", where the question really is "what happens if I press this
     right now".
     The detail sheet narrows to the same context: the menus of *other* apps are not in
     the running while this one is frontmost. */
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

/* Modifiers are ticked rather than typed: pressing ⌘⇧ in a search field would fire the
   very shortcut one is trying to identify. */
/* Interface labels exist in both languages. The content, by contrast, is read from
   macOS: menu paths, command names and categories stay exactly as the system supplies
   them — translating them would amount to rewriting a piece of data. */
const TEXTES = {
  fr: {
    onglet_menu: "Commandes par menu", onglet_effet: "Effet d'une frappe",
    onglet_conflits: "Conflits", onglet_combinaisons: "Par combinaison",
    stat_combinaisons: "combinaisons", stat_conflits: "en conflit",
    stat_apps: "applications lues",
    scanner: "Mettre à jour les raccourcis",
    bascule_app: "Filtre par application", toutes_apps: "Toutes applications",
    cherche_app: "Rechercher une application",
    l_modificateurs: "Modificateurs", l_touche: "Touche",
    l_nombre: "Nombre de touches", l_texte: "Libellé de commande",
    pave_numerique: "Pavé numérique",
    effacer_touches: "Effacer les touches", tout_effacer: "Tout effacer",
    copier: "Copier", copie_faite: "Copié ✓", copie_echec: "Copie refusée",
    onglet_scan: "Prochain scan",
    onglet_libres: "Raccourcis libres",
    libres_intro: "<p>Combinaisons qu'aucun raccourci ne revendique — ni macOS, ni un outil "
        + "global, ni le menu d'une des applications relevées. Un raccourci désactivé rend "
        + "sa combinaison à cette liste. Les modificateurs font les colonnes, les touches "
        + "les lignes ; une case porte la combinaison entière, et un clic la met dans le "
        + "presse-papiers. Une ligne dont aucune case n'est libre est omise.</p>"
        + "<p>Trois bornes ramènent l'espace des combinaisons à ce qui est réellement "
        + "attribuable : les quatre modificateurs que tout logiciel sait enregistrer "
        + "(⌃ ⌥ ⇧ ⌘, la touche Globe étant réservée par macOS) ; toutes les touches sauf "
        + "les modificateurs eux-mêmes — pavé numérique compris, dont les touches sont "
        + "distinctes de la rangée du haut ; et des <b>touches physiques</b>, "
        + "désignées par ce qu'elles produisent sans Maj — sur un clavier français la rangée "
        + "des chiffres donne donc « &amp; é \" ' ( », qui est la frappe réelle.</p>",
    couche_pilote: "pilote", couche_capture: "capture", couche_systeme: "système",
    couche_global: "global", couche_autre: "autre", couche_menu: "menu",
    libres_section: (n) => `${n} touches`,
    libres_total: (n) => `${n} libres`,
    libres_cinq: (n) => `${n} combinaisons à cinq touches restent libres, ⌃⌥⇧⌘ suivi d'une `
                      + `touche. Elles ne sont pas listées : une combinaison de cette `
                      + `longueur se trouve toujours, et n'a pas besoin d'un inventaire.`,
    libres_vide: "Aucune combinaison libre dans cette catégorie.",
    col_app: "Application", col_version: "Version installée",
    col_version_lue: "Version au dernier scan", col_statut: "Statut",
    col_date: "Dernier scan", col_lus: "Raccourcis lus",
    col_inclure: "Scanner", col_exclure: "Exclure",
    col_source: "Outil de raccourcis", jamais: "jamais lue", aucun_lu: "0 raccourci",
    lus: (n) => `${n} raccourcis lus`, auto_source: "coché par le programme : des raccourcis globaux ont été trouvés dans les préférences de cette application. Le constat ne se corrige pas à la main.",
    verrouille: "exclusion non modifiable : le lancement déclenche une action lourde",
    motif_neuf: "nouvelle", motif_majeur: "version majeure",
    scan_selection: (n) => `${n} à scanner`,
    scan_majeures: "Cocher les versions majeures",
    vue_tout: "Toutes", vue_cochees: "À scanner", vue_neuves: "Jamais lues",
    vue_majeures: "Version majeure", vue_outils: "Outils de raccourcis",
    vue_vides: "0 raccourci", vue_echecs: "Illisibles", vue_exclues: "Exclues",
    script_liste: "Mettre à jour la liste des applications",
    script_sources: "Relire le système et les applications sources",
    script_global: "Scanner les applications cochées",
    commencer_ici: "commencer ici",
    exige_autorisation: "autorisation du moissonneur",
    sans_autorisation: "aucune autorisation",
    voir_commande: "Voir la commande",
    note_liste: "Le tableau ci-dessous ne connaît que les applications recensées lors de "
              + "la dernière passe. Sans cette étape, une application installée depuis "
              + "n'y figure pas. N'ouvre aucune application.",
    note_sources: "Rouvre seulement les applications qui déclarent des raccourcis "
                + "globaux. Ce sont elles qui l'emportent sur toutes les autres, et une "
                + "poignée suffit à changer l'inventaire.",
    note_global: "Rouvre une par une les applications cochées dans le tableau. C'est la "
               + "passe longue : compter plusieurs minutes.",
    cmd_entete: "# ⚠️  COMMANDE À COPIER, PUIS À COLLER DANS UN TERMINAL.\n"
              + "#    Le navigateur ne peut pas la lancer lui-même : une page web n'a aucun\n"
              + "#    moyen d'exécuter un programme. Le terminal, lui, n'a besoin d'aucune\n"
              + "#    autorisation particulière — le moissonneur détient la sienne.\n#",
    cmd_liste: "# Recense les applications installées, relit les raccourcis système et les\n"
             + "# préférences des outils, puis reconstruit la page.\n"
             + "# N'ouvre aucune application.",
    cmd_sources: "# Rouvre les applications qui déclarent des raccourcis globaux pour relire\n"
               + "# leurs menus, puis reconstruit tout. Ce sont elles qui l'emportent sur les\n"
               + "# autres : leurs raccourcis accrochent la touche avant les menus.",
    cmd_global: "# Rouvre une par une les applications cochées dans le tableau.\n"
              + "# Compter plusieurs minutes, et une application au premier plan à chaque fois.",
    aucune_source: "Aucune application source : rien à scanner ici.",
    ph_touche: "ou saisir la touche", ph_texte: "copier, capture, plein écran…",
    toutes: "Toutes", touche_s: (n) => `${n} touche${n > 1 ? "s" : ""}`,
    double: "double frappe", fermer: "Fermer",
    rien_atteignable: "Rien d'atteignable dans cette application.",
    convention: (n) => `Commande standard de macOS : ${n} applications l'exposent dans `
                     + `leur propre menu. Le raccourci système et ces entrées désignent `
                     + `la même action — ce n'est pas un conflit.`,
    aucun_conflit: "Aucun conflit", aucun_conflit_filtre: " parmi ce que le filtre laisse passer",
    aucun_conflit_suite: ". Chaque combinaison n'a qu'un seul preneur.",
    rien_filtre: "Aucune combinaison", rien_pour: "pour", rien_libre: "Cette combinaison est donc libre.",
    autres_affine: (n) => `${n} autres — affiner le filtre.`,
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
    src_pilote: "pilote clavier", src_menu: "menu de l'application",
    pourquoi_app: "Raccourcis macOS qui agissent sur l'interface de l'application.",
    pourquoi_externe: "Agissent sur la fenêtre de l'application ou par-dessus elle, sans toucher son interface.",
    pourquoi_systeme: "Fonctionnent pendant que l'application est ouverte, mais ne la concernent pas.",
    pourquoi_inconnu: "Portée non déterminée.",
    desactive: "désactivé",
    scan_avertissement: "Chaque application cochée sera ouverte, le temps de lire sa barre "
                      + "de menu, puis refermée. Les applications défilent alors au premier "
                      + "plan : cette passe est à réserver à un moment où la machine n'est "
                      + "pas utilisée.",
    scan_explication: "<p>Les raccourcis d'une application ne sont écrits nulle part sur le "
        + "disque : ils n'existent que dans sa barre de menu, une fois l'application lancée. "
        + "Les relever suppose donc de l'ouvrir — c'est ce que commande cet écran.</p>"
        + "<p>Le tableau réunit, pour chaque application installée, la version présente sur "
        + "le disque et celle lue lors du dernier relevé. Trois réglages sont à la main de "
        + "l'utilisateur :</p><ul>"
        + "<li><b>Scanner</b> — l'application sera relue à la prochaine passe. Cochée "
        + "d'office lorsqu'elle n'a jamais été lue, ou que le premier nombre de son numéro "
        + "de version a changé.</li>"
        + "<li><b>Exclure</b> — l'application est écartée de toute passe. Les jeux et les "
        + "désinstalleurs le sont déjà ; quelques-unes, dont l'ouverture déclenche une "
        + "action lourde ou destructrice, ne peuvent pas être réintégrées.</li>"
        + "<li><b>Outil de raccourcis</b> — l'application déclare des raccourcis globaux, qui "
        + "l'emportent sur les menus de toutes les autres. La case est cochée <b>par le "
        + "programme</b> lorsqu'il a trouvé de tels raccourcis dans les préférences de "
        + "l'application : c'est un constat, il ne se décoche pas. Les autres cases "
        + "restent libres, pour désigner une application dont le format de rangement "
        + "n'est pas encore reconnu.</li></ul>"
        + "<p>Ces réglages sont conservés dans le fichier que la commande produite écrit "
        + "avant de lancer le relevé.</p>",
    scan_filtrer: "Filtrer la liste…", scan_tout: "Tout cocher", scan_rien: "Tout décocher",
    scan_defaut: "Sélection conseillée",
    scan_affichees: (n, total) => `${n} affichées sur ${total}`,
    scan_aucune: "Aucune application pour cette recherche.",
    scan_rien_coche: "Aucune application cochée : rien à scanner.",
    pied: "Les raccourcis d'une application ne vivent que dans sa barre de menu : ils sont "
        + "lus application par application. Une application lue sans document ouvert expose "
        + "moins de commandes qu'en usage "
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
    onglet_libres: "Free shortcuts",
    libres_intro: "<p>Combinations no shortcut claims — neither macOS, nor a global tool, nor "
        + "the menu of any surveyed application. A disabled shortcut returns its combination "
        + "to this list. Modifiers are the columns, keys the rows; a cell carries the whole "
        + "combination, and one click puts it on the clipboard. A row with no free cell is "
        + "left out.</p>"
        + "<p>Three limits reduce the space of combinations to what can actually be assigned: "
        + "the four modifiers every piece of software can register (⌃ ⌥ ⇧ ⌘, the Globe key "
        + "being reserved by macOS); every key except the modifiers themselves — including "
        + "the numeric keypad, whose keys are distinct from the top row; and "
        + "<b>physical keys</b>, named by what they produce without Shift — on a French "
        + "keyboard the number row therefore reads « &amp; é \" ' ( », which is the actual "
        + "keystroke.</p>",
    couche_pilote: "driver", couche_capture: "event tap", couche_systeme: "system",
    couche_global: "global", couche_autre: "other", couche_menu: "menu",
    libres_section: (n) => `${n} keys`,
    libres_total: (n) => `${n} free`,
    libres_cinq: (n) => `${n} five-key combinations remain free, ⌃⌥⇧⌘ followed by a key. `
                      + `They are not listed: a combination that long is always available, `
                      + `and needs no inventory.`,
    libres_vide: "No free combination in this category.",
    col_app: "Application", col_version: "Installed version",
    col_version_lue: "Version at last scan", col_statut: "Status",
    col_date: "Last scan", col_lus: "Shortcuts read",
    col_inclure: "Scan", col_exclure: "Exclude",
    col_source: "Hotkey tool", jamais: "never read", aucun_lu: "0 shortcuts",
    lus: (n) => `${n} shortcuts read`, auto_source: "ticked by the program: global hotkeys were found in this application’s preferences. An observation, not a choice.",
    verrouille: "exclusion cannot be lifted: launching triggers a heavy action",
    motif_neuf: "new", motif_majeur: "major version",
    scan_selection: (n) => `${n} to scan`,
    scan_majeures: "Tick major versions",
    vue_tout: "All", vue_cochees: "To scan", vue_neuves: "Never read",
    vue_majeures: "Major version", vue_outils: "Hotkey tools",
    vue_vides: "0 shortcuts", vue_echecs: "Unreadable", vue_exclues: "Excluded",
    script_liste: "Refresh the application list",
    script_sources: "Re-read the system and source applications",
    script_global: "Scan the ticked applications",
    commencer_ici: "start here",
    exige_autorisation: "harvester permission",
    sans_autorisation: "no permission needed",
    voir_commande: "Show the command",
    note_liste: "The table below only knows the applications listed during the last "
              + "pass. Without this step, an application installed since will not "
              + "appear. Opens no application.",
    note_sources: "Reopens only the applications that declare global hotkeys. They win "
                + "over every other one, and a handful is enough to change the inventory.",
    note_global: "Reopens the ticked applications one by one. This is the long pass: "
               + "expect several minutes.",
    cmd_entete: "# ⚠️  COPY THIS COMMAND AND PASTE IT INTO A TERMINAL.\n"
              + "#    The browser cannot run it itself: a web page has no way to execute a\n"
              + "#    program. The terminal needs no permission of its own — the harvester\n"
              + "#    holds its own.\n#",
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
    pourquoi_app: "macOS shortcuts acting on the app's interface.",
    pourquoi_externe: "Act on the app's window or over it, without touching its interface.",
    pourquoi_systeme: "Work while the app is open, but do not concern it.",
    pourquoi_inconnu: "Scope undetermined.",
    desactive: "disabled",
    scan_avertissement: "Each ticked application will be opened, just long enough to read "
                      + "its menu bar, then closed again. Applications come to the front "
                      + "one after another: run this pass when the machine is not in use.",
    scan_explication: "<p>An application's shortcuts are written nowhere on disk: they only "
        + "exist in its menu bar, once the application is running. Collecting them therefore "
        + "means opening it — that is what this screen commands.</p>"
        + "<p>The table gathers, for every installed application, the version on disk and the "
        + "one read during the last pass. Three settings are yours to set:</p><ul>"
        + "<li><b>Scan</b> — the application will be read again on the next pass. Ticked by "
        + "default when it has never been read, or when the first number of its version "
        + "changed.</li>"
        + "<li><b>Exclude</b> — the application is kept out of every pass. Games and "
        + "uninstallers already are; a few, whose launch triggers a heavy or destructive "
        + "action, cannot be brought back in.</li>"
        + "<li><b>Hotkey tool</b> — the application declares global hotkeys, which win over "
        + "every other application's menus. The box is ticked <b>by the program</b> when it "
        + "found such hotkeys in the application's preferences: an observation, not a "
        + "choice, so it cannot be unticked. The other boxes stay free, to flag an "
        + "application whose storage format is not recognised yet.</li></ul>"
        + "<p>These settings are stored in the file the generated command writes before "
        + "starting the pass.</p>",
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
/* A double tap involves one key only, pressed twice. */
const PORTEES = () => D.libelles_portee[LANGUE] || D.libelles_portee.fr || D.libelles_portee;
const nbTouches = (mods, double) => {
  if (double) return 1;
  let n = 1;
  for (let m = mods; m; m >>= 1) n += m & 1;
  return n;
};
const toucheSeule = (combo) => combo.replace("fn", "").replace(/[⌃⌥⇧⌘]/g, "");

/* The per-application filter applies to the four shortcut views. Switched off, nothing
   is restricted to an app any more, and the selection field is disabled.
   Off on load: you arrive on the overall view, and narrow to an app when you have a
   question about it. */
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

/* The same filter serves the three views: a combination passes if it satisfies every
   criterion that has been filled in. An empty criterion filters nothing. */
function passe(f, combo, mods, usages, double) {
  if (f.actifs && mods !== f.bits) return false;
  if (f.nombre && nbTouches(mods, double) !== f.nombre) return false;
  // Restricted to one app: its own commands, plus everything global.
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

/* A ticked button unticks; on the key side, the selection stays single. */
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
  // Returns the key panel to its neutral state: modifiers included, since they are keys
  // too. Touches neither the label search nor the key count, which answer other
  // questions — clearing those is what "clear all" is for.
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

/* The verdict shown must hold in the context you clicked from: inside an app's view,
   only its menus and the global shortcuts are in the running. Reusing the global
   arbitration would name apps that are not there. */
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

/* Per-app view, two complementary readings.

   "By menu" follows the app's menu bar in its real order: reading Format shortcuts, then
   Window, then Format again does not stick. Global shortcuts come next, arranged by what
   they act upon.

   "What happens" starts from the keystroke rather than the command: for every combination
   reachable in this app, who actually receives it. Sorted by key count, because short
   combinations are what one looks for first. */

const SOURCE_LABEL = () => ({
  systeme: T("src_systeme"), capture: T("src_outil"), global: T("src_outil"),
  pilote: T("src_pilote"), autre: T("src_outil"), menu: T("src_menu"),
});

/* What a given keystroke reaches while this app is frontmost: its own menus, plus
   everything global. The rest does not concern it. */
function atteignables(bundleID) {
  const f = etatFiltre();
  const out = [];
  for (const c of D.combinaisons) {
    if (!passe(f, c.combo, c.mods, c.usages, c.double)) continue;
    // With no application chosen, only global shortcuts resolve: a menu answers only
    // while its app is frontmost.
    const candidats = c.usages.filter(u =>
      u.actif && (u.couche !== "menu" || (bundleID && u.bundle_id === bundleID)));
    if (!candidats.length) continue;
    const gagnante = ORDRE.find(couche => candidats.some(u => u.couche === couche));
    const vainqueurs = candidats.filter(u => u.couche === gagnante);
    const perdants = candidats.filter(u => u.couche !== gagnante);
    // `meme_commande` marks the combinations macOS injects identically into every app's
    // menu (⇧⌘Q, ⌃⌘Q…). Counting them as conflicts would paint half the rows red, and
    // would contradict the arbitration computed on the Python side.
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
    // Sort on the main key, not on the whole string: sorting on "⌘" would gather
    // everything in one place when what one is looking for is a letter.
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
  // Same definition of a conflict as in "What a keystroke does": a combination several
  // claimants dispute *while this app is frontmost*.
  const disputees = new Set(atteignables(cible).filter(it => it.conflit).map(it => it.combo));
  const parMenu = new Map(), parPortee = { app: [], app_externe: [], systeme: [], inconnu: [] };
  for (const c of D.combinaisons) {
    if (!passe(f, c.combo, c.mods, c.usages, c.double)) continue;
    for (const u of c.usages) {
      if (!u.actif) continue;
      const marque = { ...u, conflit: disputees.has(c.combo), double: c.double, cle: c.cle };
      if (u.couche === "menu") {
        if (cible && u.bundle_id !== cible) continue;
        // With no app chosen, group by application before menu: "File" from six
        // different apps inside one block means nothing.
        const m = cible ? (u.menu || "—") : `${u.proprietaire} · ${u.menu || "—"}`;
        if (!parMenu.has(m)) parMenu.set(m, []);
        parMenu.get(m).push(marque);
      } else if (parPortee[u.portee]) parPortee[u.portee].push(marque);
    }
  }
  // Menus are shown in menu-bar order, not alphabetically. The Apple menu does not
  // belong to the app: it is identical everywhere. It therefore comes after the app's own
  // menus, just before the shortcuts coming from elsewhere.
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

  // The Apple menu carries its logo rather than its name: that is how it appears in the
  // menu bar, where the word "Apple" is nowhere to be seen.
  const nommer = (t) => t.replace(/(^|· )Apple$/, "$1\uF8FF")
                         // Every app has a menu named after itself: in all-apps mode the
                         // prefix repeated it verbatim.
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

/* A dropdown of 200 apps cannot be browsed: it is narrowed by typing. The comparison
   ignores accents and case, so that "appstore" finds "AppStore". */
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
  // On click the field empties: the name sitting in it is a display, not a query, and
  // keeping it would narrow the list down to that single app.
  champ.addEventListener("focus", () => {
    saisieApp = ""; champ.value = ""; surligne = -1; ouvrirListe(true);
  });
  // Clicking an item must land before the close triggered by the blur.
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
    // Filter off: show everything, while saying what "everything" means here.
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
  // The key filter applies only to the shortcut views. On the next-scan screen it drives
  // nothing: leaving it there would suggest otherwise.
  // Two views are filtered neither by key nor by application: the next scan, which has its
  // own search box, and the free combinations, which by definition belong to no
  // application. Leaving the filters there would suggest they drive something.
  const sansFiltre = vue === "scan" || vue === "libres";
  document.querySelector(".filtre").hidden = sansFiltre;
  document.querySelector(".bloc-app").hidden = sansFiltre;
  if (vue === "scan") rendreScan();
  if (vue === "libres") rendreLibres();
}
document.querySelectorAll(".onglets button").forEach(b =>
  b.addEventListener("click", () => choisirOnglet(b.dataset.vue)));

/* Next scan. The screen runs nothing itself: it produces the exact command to execute,
   settings included. Choices live in memory until the command writes them into
   out/scan-settings.json — that file remains the single truth, and the page reads it back
   on every generation. */
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
    lus: typeof f.raccourcis === "number" ? f.raccourcis : null,
    raison: a.raison || null, verrou: !!a.verrou, excluCalcule: !!a.exclu,
  };
});

function estExclue(l) {
  if (l.verrou) return true;
  if (incluses.has(l.id)) return false;
  if (exclues.has(l.id)) return true;
  return l.excluCalcule;
}

/* The first number of the version string: "3.7.8" gives "3". An unreadable or missing
   version counts as a difference: better to re-read for nothing than to present stale
   shortcuts as current.
   (Deliberately a three-number example: with four it would look like an IP address and
   would set off check-publication.sh for nothing.) */
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

let vueScan = "tout";

/* The script currently on screen, replayed as soon as the table changes: without this the
   displayed command would describe a stale selection, and it would be copied as is. */
const SCRIPTS = {};
let scriptAffiche = null;
function rejouerScript() { if (scriptAffiche) SCRIPTS[scriptAffiche](); }

/* Each quick view answers a question one genuinely asks in front of two hundred rows:
   what am I about to scan, what has never been read, who catches the key before the
   others, what failed. */
const VUES = {
  tout: () => true,
  cochees: (l) => aScanner.has(l.id),
  neuves: (l) => jamaisLue(l),
  majeures: (l) => ecartMajeur(l),
  outils: (l) => SOURCES_AUTO.has(l.id) || sourcesChoisies.has(l.id),
  vides: (l) => l.statut === "ok" && l.lus === 0,
  echecs: (l) => !!l.statut && l.statut !== "ok",
  exclues: (l) => estExclue(l),
};

function scanFiltre() {
  const q = sansAccent(document.getElementById("scan-recherche").value.trim());
  const garde = VUES[vueScan] || VUES.tout;
  return LIGNES.filter(l => garde(l)
    && (!q || sansAccent(l.nom).includes(q) || sansAccent(l.id).includes(q)));
}

const LIBRES = D.libres || [];

function rendreLibres() {
  const L = LIBRES;
  if (!L.lignes || !L.lignes.length) {
    document.getElementById("vue-libres").innerHTML =
      `<p class="libres-note">${T("libres_vide")}</p>`;
    return;
  }
  // One single grid, groups separated by a rule rather than by three tables: the same key
  // then reads along one row, from shortest to longest.
  let rang = 0;
  const bornes = new Set();          // last column of each group
  const groupes = L.groupes.map(g => {
    rang += g.n;
    bornes.add(rang - 1);
    return `<th colspan="${g.n}" class="groupe">${T("libres_section")(g.touches)}`
         + `<span class="libres-total">${T("libres_total")(g.total)}</span></th>`;
  }).join("");
  const classe = (i) => bornes.has(i) && i !== L.colonnes.length - 1 ? " borne" : "";
  const entete = L.colonnes.map((c, i) =>
    `<th class="mods${classe(i)}"><span class="combo">${esc(c.mods)}</span></th>`).join("");
  const corps = L.lignes.map(l =>
    `<tr><th scope="row">${esc(l.touche)}</th>${
      l.cases.map((c, i) => c
        ? `<td class="${classe(i).trim()}"><button type="button" class="libre" `
          + `data-combo="${esc(c)}">${esc(c)}</button></td>`
        : `<td class="pris${classe(i)}"></td>`).join("")}</tr>`).join("");
  document.getElementById("vue-libres").innerHTML =
    `<table class="libres-table"><thead>
       <tr><th></th>${groupes}</tr>
       <tr><th></th>${entete}</tr></thead>
     <tbody>${corps}</tbody></table>
     <p class="libres-note">${esc(T("libres_cinq")(L.cinq))}</p>`;
}

/* Clicking a free combination puts it on the clipboard: it exists to be carried over
   into another program's settings. */
document.addEventListener("click", async (e) => {
  const bouton = e.target.closest("button.libre");
  if (!bouton) return;
  const combo = bouton.dataset.combo;
  if (await copierTexte(combo)) {
    bouton.classList.add("copie");
    setTimeout(() => bouton.classList.remove("copie"), 900);
  }
});

function rendreScan() {
  const liste = scanFiltre();
  // The three checkboxes first: what one decides, before what one observes.
  const entetes = ["col_inclure", "col_exclure", "col_source", "col_app",
                   "col_version", "col_version_lue", "col_statut", "col_date",
                   "col_lus"];
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
      <td class="statut ${l.statut && l.statut !== "ok" ? "statut-ko"
                        : l.lus === 0 ? "statut-vide" : "statut-ok"}"
          title="${l.lus === null ? "" : esc(T("lus")(l.lus))}">${
        esc(l.statut ? (l.lus === 0 ? T("aucun_lu") : l.statut) : T("jamais"))}</td>
      <td class="num date"><span>${esc(l.scanneLe || "—")}</span></td>
      <td class="num lus ${l.lus === 0 ? "statut-vide" : ""}">${
        l.lus === null ? "—" : l.lus}</td>
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
  rejouerScript();
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
  if (!document.getElementById("onglet-libres").hidden) rendreLibres();
  if (!document.getElementById("onglet-scan").hidden) rendreScan();
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
  document.getElementById("scan-vues").addEventListener("click", (e) => {
    const bouton = e.target.closest("button[data-vue-scan]");
    if (!bouton) return;
    vueScan = bouton.dataset.vueScan;
    document.querySelectorAll("#scan-vues button").forEach(b =>
      b.setAttribute("aria-pressed", String(b === bouton)));
    rendreScan();
  });

  // Bulk ticking applies only to what the filter lets through: without that, "untick all"
  // would also clear the apps one is not looking at.
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
  // Adds to the current selection rather than replacing it: one ticks in successive
  // layers, without losing what was just picked by hand.
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
      // Two lists rather than one: the program already skips games and uninstallers, so
      // there has to be a way to say "take it anyway".
      exclues.delete(id); incluses.delete(id);
      (c.checked ? exclues : incluses).add(id);
      if (c.checked) aScanner.delete(id);
    } else {
      c.checked ? sourcesChoisies.add(id) : sourcesChoisies.delete(id);
    }
    rendreScan();
  });

  // Three actions, three commands. Listing costs nothing and opens no app; re-reading the
  // tools opens a handful; the full pass opens them all. Conflating them would force you
  // to endure the most expensive one to get the cheapest.

  /* Shell-quotes a value. Inside single quotes nothing is interpreted — except the single
     quote itself, which must therefore be pulled out of the string and put back escaped.
     Without this, a bundle identifier containing a space splits the command, and one
     containing an apostrophe closes it: whatever follows would be executed as a command in
     its own right. */
  const shq = (v) => "'" + String(v).replace(/'/g, "'\\''") + "'";

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
    // The comment says what is being copied, but does not go to the clipboard: pasted
    // into zsh, a "#" is not always treated as a comment there.
    bloc.dataset.commande = commande;
    bouton.hidden = false;
  }

  // The command goes through run.sh rather than calling the harvester: only run.sh knows
  // how to launch it through LaunchServices, the one way for the bundle to be its own
  // responsible process and have its own grant applied. Run from the shell, macOS would
  // query the terminal instead. The identifiers stay spelled out: what you paste still
  // describes exactly what will be read.
  function moissonner(ids) {
    const reglages = JSON.stringify({
      exclues: [...exclues], incluses: [...incluses], sources: [...sourcesChoisies],
    });
    return `cd ${shq(RACINE)} && \\
  printf '%s' ${shq(reglages)} > out/scan-settings.json && \\
  ./run.sh --apps ${shq(ids.join(","))}`;
  }

  // A displayed command describes a selection; if the selection changes and the command
  // does not, you copy an instruction that no longer matches what you see. Each script is
  // therefore a function, and the one on screen is replayed on every change to the
  // table.
  SCRIPTS.liste = () => afficher(T("cmd_liste"), `cd ${shq(RACINE)} && ./run.sh --sources`);

  SCRIPTS.sources = () => {
    const ids = LIGNES
      .filter(l => !estExclue(l) && (SOURCES_AUTO.has(l.id) || sourcesChoisies.has(l.id)))
      .map(l => l.id);
    if (!ids.length) return afficher(T("aucune_source"), null);
    afficher(T("cmd_sources"), moissonner(ids));
  };

  SCRIPTS.global = () => {
    if (!aScanner.size) return afficher(T("scan_rien_coche"), null);
    afficher(T("cmd_global"), moissonner([...aScanner]));
  };

  for (const nom of ["liste", "sources", "global"]) {
    document.getElementById("script-" + nom).addEventListener("click", () => {
      scriptAffiche = nom;
      document.querySelectorAll(".etape").forEach(e =>
        e.classList.toggle("choisie", e.contains(document.getElementById("script-" + nom))));
      SCRIPTS[nom]();
    });
  }
}

document.getElementById("recherche").addEventListener("input", rendreTout);
brancherFiltres(); brancherChoixApp(); brancherBasculeApp(); brancherDetail(); brancherScan(); brancherLangues(); brancherCopie();
appliquerLangue();

rendreTout();
"""

def _ordre_touche(touche):
    """Function keys sort by their number, not alphabetically: otherwise F10 slips in
    between F1 and F2."""
    if touche.startswith("F") and touche[1:].isdigit():
        return (0, int(touche[1:]), "")
    return (1, 0, touche)

def build(index_path):
    data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    lisibles = [a for a in data["apps"] if a["statut"] == "ok"]
    conflits = sum(1 for c in data["combinaisons"] if c["conflit"])
    machine = subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip()

    # "</" must be neutralised: the sequence would close the script tag from inside a
    # JSON string if a command name happened to contain it.
    charge = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    # A button is only warranted for a key that writes no character at all. Everything the
    # layout produces, with or without Shift, can be typed into the free field: on AZERTY
    # that covers "$" and ";", but also "." and "£", which need Shift.
    keymap = json.loads((ROOT / "out" / "keymap.json").read_text(encoding="utf-8"))
    touches = keymap.get("touches", keymap)
    disposition = keymap.get("disposition", "")
    ecrivables = {c.upper() for niveaux in touches.values() for c in niveaux if c.strip()}

    vues = {c["combo"].replace("fn", "").translate(str.maketrans("", "", "⌃⌥⇧⌘"))
            for c in data["combinaisons"]}
    # The numeric keypad is offered in full, like the function keys: it forms a physical
    # block, and showing half of it would suggest the rest does not exist. The labels come
    # from the active layout.
    clavier = Keyboard()
    pave = [t for t in (clavier.label(c, 0) for c in keypad_codes()) if t]
    # Digits first, operators next: key-code order bears no relation to the way one reads
    # a keypad.
    pave.sort(key=lambda t: (not t.split()[-1].isdigit(), t.split()[-1]))

    autres = sorted({t for t in vues if t.strip() and t.upper() not in ecrivables
                     and not (t.startswith("F") and t[1:].isdigit())
                     and t not in pave},
                    key=_ordre_touche)
    # Function keys are offered in full, including those no shortcut uses: knowing a key is
    # free is part of the answer.
    fonctions = [f"F{n}" for n in range(1, 21)]
    # Punctuation keys must be escaped: on AZERTY the quotation mark is a key, and
    # unescaped it would close the HTML attribute.
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

    # The small tokens are substituted BEFORE the data payload: the other way round, an
    # application name containing "MODS_BITS" would have the token replaced inside the
    # JSON, and the whole page would become invalid JavaScript.
    script = (JS.replace("ORDRE_COUCHES_JS", json.dumps(ORDRE_COUCHES))
                .replace("MODS_BITS", json.dumps({"⇧": 1, "⌃": 2, "⌥": 4, "⌘": 8, "fn": 16},
                                                 ensure_ascii=False))
                .replace("RACINE_PROJET", json.dumps(str(ROOT)))
                .replace("DONNEES", charge))

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
    <button data-vue="libres" aria-selected="false" data-t="onglet_libres"></button>
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
<!-- One filter for the three views: duplicating the controls would let their states
     drift apart, and the filter would be lost when switching tabs. -->
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
  <section id="onglet-libres" hidden>
    <p class="scan-intro" data-t-html="libres_intro"></p>
    <div id="vue-libres"></div>
  </section>
  <section id="onglet-scan" hidden>
    <div class="avertissement" role="note">
      <span aria-hidden="true">⚠️</span>
      <p data-t="scan_avertissement"></p>
    </div>
    <div class="scan-intro" data-t-html="scan_explication"></div>
    <ol class="etapes">
      <li class="etape">
        <span class="puce">1</span>
        <div class="etape-texte">
          <b data-t="script_liste"></b><em class="ici" data-t="commencer_ici"></em>
          <em class="sans-exige" data-t="sans_autorisation"></em>
          <span data-t="note_liste"></span>
        </div>
        <button type="button" class="bouton primaire" id="script-liste" data-t="voir_commande"></button>
      </li>
      <li class="etape">
        <span class="puce">2</span>
        <div class="etape-texte">
          <b data-t="script_sources"></b><em class="exige" data-t="exige_autorisation"></em>
          <span data-t="note_sources"></span>
        </div>
        <button type="button" class="bouton" id="script-sources" data-t="voir_commande"></button>
      </li>
      <li class="etape">
        <span class="puce">3</span>
        <div class="etape-texte">
          <b data-t="script_global"></b><em class="exige" data-t="exige_autorisation"></em>
          <span data-t="note_global"></span>
        </div>
        <button type="button" class="bouton" id="script-global" data-t="voir_commande"></button>
      </li>
    </ol>
    <div class="bloc-commande" id="bloc-scan-commande" hidden>
      <code class="commande" id="scan-commande"></code>
      <button type="button" class="copier" data-t="copier"></button>
    </div>
    <div class="scan-outils">
      <input type="search" id="scan-recherche" autocomplete="off" autocorrect="off"
             autocapitalize="off" spellcheck="false" data-tp="scan_filtrer">
      <button type="button" class="bouton" id="scan-defaut" data-t="scan_defaut"></button>
      <button type="button" class="bouton" id="scan-majeures" data-t="scan_majeures"></button>
      <button type="button" class="bouton" id="scan-tout" data-t="scan_tout"></button>
      <button type="button" class="bouton" id="scan-rien" data-t="scan_rien"></button>
      <span id="scan-total" class="sous"></span>
    </div>
    <div class="scan-vues" id="scan-vues" role="group">
      <button type="button" data-vue-scan="tout" aria-pressed="true" data-t="vue_tout"></button>
      <button type="button" data-vue-scan="cochees" aria-pressed="false" data-t="vue_cochees"></button>
      <button type="button" data-vue-scan="neuves" aria-pressed="false" data-t="vue_neuves"></button>
      <button type="button" data-vue-scan="majeures" aria-pressed="false" data-t="vue_majeures"></button>
      <button type="button" data-vue-scan="outils" aria-pressed="false" data-t="vue_outils"></button>
      <button type="button" data-vue-scan="vides" aria-pressed="false" data-t="vue_vides"></button>
      <button type="button" data-vue-scan="echecs" aria-pressed="false" data-t="vue_echecs"></button>
      <button type="button" data-vue-scan="exclues" aria-pressed="false" data-t="vue_exclues"></button>
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
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "shortcuts.html"
    out.write_text(build(index), encoding="utf-8")
    print(f"✅ {out}  ({out.stat().st_size // 1024} Ko)")
