# Architecture and data sources

How the inventory is built, where its lookup tables come from, and what the repository
holds. For everyday use, see [Usage](usage.md).

---

## Why build rather than adopt

| Option | Why it was ruled out |
|---|---|
| Read `.app` bundles on disk | Nothing to read: menus exist only in memory. Electron and Qt apps build them in code. |
| Adopt **HotkeyClash** | Covers only apps already running, and aims at conflict detection rather than inventory. Its menu-walking code did serve as a reference. |
| Adopt **KeyMinder** / **CheatSheet** / **KeyCue** | Frontmost app only. No global document. |
| An `osascript` script | Accessibility permission would apply to the whole terminal rather than to a dedicated binary. |

## Who wins a combination

A keystroke descends a stack, and the first layer that claims it swallows it: keyboard
driver (Karabiner) → event tap (Keyboard Maestro) → macOS system shortcut → Carbon global
hotkey (Alfred, CleanShot X) → application menu.

That order is reliable. Deciding between two tools hooked on the **same** layer is not: it
depends on their registration order, which nothing on disk records. The tool reports a tie
rather than picking a winner at random. Model taken from
[HotkeyClash](https://github.com/Wunderlandmedia/HotkeyClash) (GPL-2.0) — see the licence
note in the [README](../README.md).

## Double taps

Some system shortcuts are not a combination but a **double tap** on a modifier alone —
dictation being the common example. macOS stores them with `type: "modifier"` and a mask
distinguishing the left key from the right one (IOKit's `NX_DEVICE*KEYMASK` constants).
The labels come from the Keyboard settings panel itself (`DoubleTapCommandRight` → "Press
Right Command Twice"). These shortcuts are marked "double tap" in the page, and counted as
**one** key.

## Where the data comes from

No lookup table is written from memory — everything is extracted from macOS:

| Data | Source on the machine |
|---|---|
| System shortcuts and their localised labels | `KeyboardSettings.appex/…/DefaultShortcutsTable.xml` and `DefaultSpacesShortcuts.xml` (desktops), translated through `.loctable` |
| Actual state (enabled, redefined) | `defaults export com.apple.symbolichotkeys` |
| Key codes and menu glyphs | `HIToolbox.framework/…/BridgeSupport` (Carbon enumerations `kVK_*` and `kMenu*Glyph`) |
| Application shortcuts | Accessibility API, attributes `AXMenuItemCmdChar` / `CmdGlyph` / `CmdModifiers` |
| Application category and version | `LSApplicationCategoryType` and `CFBundleShortVersionString` from each `Info.plist` |
| User-redefined shortcuts | `NSUserKeyEquivalents` in each app's preferences |
| Key ↔ character mapping | `UCKeyTranslate` on the active keyboard layout — essential on AZERTY, where code 41 produces "m" and not ";" |
| Third-party global hotkeys | `Alfred.alfredpreferences` and `Keyboard Maestro Macros.plist` for their own formats; for everything else, a sweep of `~/Library/Preferences` recognising three widespread conventions — `{keyCode, modifierFlags}`, a JSON string carrying `carbonKeyCode`, and an `NSKeyedArchiver` archive. Read, never written. A preferences domain with no installed app is skipped: a prefs file outlives the uninstall. |

Application role descriptions, by contrast, are written by hand in
`data/app-descriptions.json`. An app with no description shows "role not filled in" rather
than receiving a plausible but invented one.

## Layout

```
build.sh              builds bin/ShortcutHarvester.app
run.sh                orchestration: system → apps → report
check-publication.sh  scans tracked files and git history before a push
src/tables.py            key codes and menu glyphs, extracted from BridgeSupport
src/system_shortcuts.py  system shortcuts → out/system-shortcuts.json
src/Harvester.swift      accessibility harvester → out/apps/<bundle-id>.json
src/index.py             unified index, conflict arbitration → out/index.json
src/report.py            assembles the final Markdown
src/page.py              self-contained HTML page, in French and English
src/free_shortcuts.py    combinations no shortcut claims
src/stale.py             records whose version no longer matches the installed one
src/toggle_shortcut.py   disables or re-enables a system shortcut
data/scopes.json            scope arbitration table (editable)
data/known-shortcuts.json   identifications established for undocumented shortcuts
data/app-descriptions.json  seed of app roles (macOS-shipped apps only)
out/scan-settings.json      exclusions and hotkey tools set by hand (ignored)
out/app-descriptions.json   roles of installed apps (machine-specific, ignored)
out/backups/                timestamped copies of com.apple.symbolichotkeys (ignored)
```

## What the repository holds, and what it does not

The code is publishable as is. Everything that describes **a machine** is produced in
`out/`, which is not versioned:

| Versioned | Ignored (`out/`) |
|---|---|
| The code, the arbitration tables (`data/scopes.json`) | The shortcuts read, app by app |
| Hand-written app descriptions | The HTML page and the Markdown report |
| Established identifications (`data/known-shortcuts.json`) | The keyboard layout, the census of installed apps |
| | Backups of `com.apple.symbolichotkeys` |

⚠️ **The page it produces is a personal document.** It contains real menu paths: browser
bookmark titles, macro names, the session name. It has no place in a repository, nor in a
file share.

The repository says nothing about any particular installation: not the number of apps
read, not the software present, not the shortcuts disabled. Third-party tools are named
only where the code handles them explicitly — Alfred and Keyboard Maestro have a dedicated
reader, and each storage convention is illustrated by the app that uses it. Everywhere
else, the text says "third-party tools". The same rule applies to
`data/app-descriptions.json`: the versioned copy describes only apps shipped with macOS,
because a completed one would amount to publishing the list of installed software.

The exclusion lists, by contrast, are versioned: they are program settings, not machine
data. They contain only identifiers of macOS components and mainstream tools — none
observed on a particular installation. Uninstallers are skipped by a rule on the name
rather than by a list of identifiers.

Before publishing, `./check-publication.sh` re-reads the versioned files **and the git
history**, looking for absolute paths, user names, addresses and machine identifiers.
