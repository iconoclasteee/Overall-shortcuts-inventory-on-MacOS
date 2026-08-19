// macOS menu shortcut harvester.
//
// Why this binary exists: an app's shortcuts are written nowhere on disk. They live only
// in the menu bar built in memory at launch. The only way to read them is the
// accessibility API (AX), which requires an explicit grant — hence a dedicated binary
// rather than a script: the grant covers it alone, and not the whole terminal.
//
// It emits raw JSON (character, modifier mask, glyph). Readable rendering (⌘⇧K) happens on
// the Python side, where the tables extracted from macOS live.

import AppKit
import ApplicationServices
import Carbon.HIToolbox

// MARK: - Options

struct Options {
    var bundleIDs: [String] = []
    var outDir = "out/apps"
    var timeout: Double = 25       // plafond par app, en secondes
    var checkOnly = false
    var scanAll = false
    var force = false              // redo apps already harvested
    var reglages = "out/scan-settings.json"   // hand-set exclusions
    var onlyRunning = false        // re-read only apps already running
    var includeGames = false       // games are skipped by default
    var dryRun = false             // lister les cibles sans rien lancer
    var verdict: String?           // where to write the result of --check
    var keymap = false             // export the key code -> character mapping
    var catalogue = false          // export the installed-app list, launching nothing
    var keepRunning = false        // do not quit the apps we launched
    var journal: String?           // where to copy standard output and error
    var statut: String?            // where to write the exit code
}

/// Where to write the exit code. Nil until the options have been read.
var cheminStatut: String?

/// Application we have just opened and have not closed yet.
///
/// An interrupt must close it. Without that, every Ctrl-C abandons one, and they pile up
/// with nothing to flag it — measured on two passes interrupted fifteen minutes apart, two
/// applications still open an hour later.
var appEnCours: NSRunningApplication?

/// The program's only exit.
///
/// Launched by `open` — the one way for this bundle to be its own responsible process, and
/// therefore to have its own accessibility grant applied rather than the terminal's — the
/// program returns neither standard output nor an exit code to whoever launched it. This
/// file is then the sole channel back, and its appearance the only reliable end signal.
func sortir(_ code: Int32) -> Never {
    if let chemin = cheminStatut {
        try? "\(code)".write(toFile: chemin, atomically: true, encoding: .utf8)
    }
    exit(code)
}

/// Opens the channel back before anything else.
///
/// It must be in place before the options are parsed, since parsing is what rejects an
/// unknown option: without this, its message would go nowhere and run.sh would wait for a
/// status that never arrived.
func preparerCanaux() {
    let args = CommandLine.arguments
    func valeur(_ nom: String) -> String? {
        guard let i = args.firstIndex(of: nom), i + 1 < args.count else { return nil }
        return args[i + 1]
    }
    cheminStatut = valeur("--statut")
    guard let chemin = valeur("--journal") else { return }
    let fd = open(chemin, O_WRONLY | O_CREAT | O_APPEND, 0o600)
    guard fd >= 0 else { return }
    dup2(fd, STDOUT_FILENO)
    dup2(fd, STDERR_FILENO)
    close(fd)
    // Into a file, standard output switches to block buffering: progress would appear
    // only at the very end. Line by line, it can be read during the pass.
    setvbuf(stdout, nil, _IOLBF, 0)
}

func parseArgs() -> Options {
    preparerCanaux()
    var o = Options()
    var it = CommandLine.arguments.dropFirst().makeIterator()
    while let arg = it.next() {
        switch arg {
        case "--check": o.checkOnly = true
        case "--all": o.scanAll = true
        case "--force": o.force = true
        case "--reglages": o.reglages = it.next() ?? o.reglages
        case "--only-running": o.onlyRunning = true
        case "--keep-running": o.keepRunning = true
        case "--include-games": o.includeGames = true
        case "--dry-run": o.dryRun = true
        case "--verdict": o.verdict = it.next()
        case "--journal": o.journal = it.next()
        case "--statut": o.statut = it.next()
        case "--keymap": o.keymap = true
        case "--catalogue": o.catalogue = true
        case "--bundle-ids": o.bundleIDs = (it.next() ?? "").split(separator: ",").map(String.init)
        case "--out": o.outDir = it.next() ?? o.outDir
        case "--timeout": o.timeout = Double(it.next() ?? "") ?? o.timeout
        default:
            FileHandle.standardError.write("Option inconnue : \(arg)\n".data(using: .utf8)!)
            sortir(2)
        }
    }
    return o
}

// MARK: - Accessibility

enum AX {
    static func isTrusted() -> Bool {
        AXIsProcessTrustedWithOptions(
            [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: false] as CFDictionary)
    }

    static func app(_ pid: pid_t, timeout: Float) -> AXUIElement {
        let element = AXUIElementCreateApplication(pid)
        // Without a ceiling, an app stuck on a dialog freezes the read.
        AXUIElementSetMessagingTimeout(element, timeout)
        return element
    }

    static func element(_ parent: AXUIElement, _ attribute: String) -> AXUIElement? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(parent, attribute as CFString, &value) == .success,
              let value, CFGetTypeID(value) == AXUIElementGetTypeID() else { return nil }
        return (value as! AXUIElement)
    }

    static func children(_ element: AXUIElement) -> [AXUIElement] {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &value) == .success,
              let array = value as? [AXUIElement] else { return [] }
        return array
    }

    static func string(_ element: AXUIElement, _ attribute: String) -> String? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success
        else { return nil }
        return value as? String
    }

    static func int(_ element: AXUIElement, _ attribute: String) -> Int? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success
        else { return nil }
        return value as? Int
    }
}

// MARK: - Walking the menus

struct Shortcut: Encodable {
    let chemin: String        // "Fichier > Enregistrer sous…"
    let menu: String          // menu de premier niveau
    let caractere: String?    // AXMenuItemCmdChar
    let glyphe: Int?          // AXMenuItemCmdGlyph (touches non imprimables)
    let modificateurs: Int    // AXMenuItemCmdModifiers, format AX
    let source: String        // "menubar" ou "extras"
}

let maxDepth = 12  // real menus top out near 5; beyond that, the tree is suspect

func walk(_ items: [AXUIElement], path: [String], menu: String, source: String,
          depth: Int, limite: Date, into found: inout [Shortcut], tronque: inout Bool) {
    guard depth < maxDepth else { return }
    for item in items {
        // The budget also bounds the walk through the tree, not just the wait for the
        // menu bar. Without that, the only ceiling is the **per-message** accessibility
        // timeout, applied to each of hundreds of requests: a slow server answers within
        // time every single time while pinning the pass far beyond the announced budget.
        if Date() >= limite { tronque = true; return }
        let title = AX.string(item, kAXTitleAttribute as String) ?? ""
        let subPath = title.isEmpty ? path : path + [title]

        let char = AX.string(item, "AXMenuItemCmdChar")
        let glyph = AX.int(item, "AXMenuItemCmdGlyph")
        // A shortcut exists if a character OR a glyph is present. HotkeyClash uses only
        // the character; an inventory needs the glyphs too, otherwise every arrow and
        // function key vanishes silently.
        let hasChar = !(char ?? "").isEmpty
        let hasGlyph = (glyph ?? 0) != 0
        if hasChar || hasGlyph {
            found.append(Shortcut(
                chemin: subPath.joined(separator: " > "),
                menu: menu,
                caractere: hasChar ? char : nil,
                glyphe: hasGlyph ? glyph : nil,
                modificateurs: AX.int(item, "AXMenuItemCmdModifiers") ?? 0,
                source: source))
        }
        walk(AX.children(item), path: subPath, menu: menu, source: source,
             depth: depth + 1, limite: limite, into: &found, tronque: &tronque)
        if tronque { return }
    }
}

func harvest(pid: pid_t, timeout: Double, limite: Date) -> (raccourcis: [Shortcut],
                                                            tronque: Bool) {
    let app = AX.app(pid, timeout: Float(timeout))
    var found: [Shortcut] = []
    var tronque = false
    for (attribute, source) in [(kAXMenuBarAttribute as String, "menubar"),
                                (kAXExtrasMenuBarAttribute as String, "extras")] {
        guard let bar = AX.element(app, attribute) else { continue }
        for topMenu in AX.children(bar) {
            if tronque { break }
            let title = AX.string(topMenu, kAXTitleAttribute as String) ?? ""
            walk(AX.children(topMenu), path: [title], menu: title, source: source,
                 depth: 0, limite: limite, into: &found, tronque: &tronque)
        }
    }
    return (found, tronque)
}

enum EtatMenu { case pret, sansMenu, expire }

/// Grace period given to a freshly launched app to build its menu bar, before concluding
/// that it has none.
let delaiDeGrace: Double = 4

/// Waits until the menu bar is readable.
///
/// Three outcomes, and the distinction matters: a background app exposes no menu bar at
/// all, and knowing that in four seconds avoids waiting the full budget for each one.
/// Conflating the two cases cost several minutes per pass and gave a false diagnosis.
func waitForMenuBar(pid: pid_t, deadline: Date, timeout: Double) -> EtatMenu {
    let finDeGrace = Date().addingTimeInterval(delaiDeGrace)
    var barreVue = false

    while Date() < deadline {
        let app = AX.app(pid, timeout: Float(min(timeout, 5)))
        if let bar = AX.element(app, kAXMenuBarAttribute as String) {
            barreVue = true
            let titres = AX.children(bar)
            // Two conditions, and the second counts as much as the first. Menu titles can
            // exist while none of them has content yet: that is the state of an app sitting
            // on a project picker or a modal window. Settling for that gave an "ok" status
            // to a read that returned zero shortcuts — a failure presented as a success.
            let peuple = titres.contains { !AX.children($0).isEmpty }
            // More than one menu = the bar is built. A single menu can be a transient
            // launch state: it is accepted only once the grace period has passed, failing
            // which a single-menu app would time out.
            if peuple && (titres.count > 1 || (titres.count >= 1 && Date() > finDeGrace)) {
                return .pret
            }
        }
        // Background apps have no conventional menu bar: their shortcuts live in the menu
        // of their status icon.
        if let extras = AX.element(app, kAXExtrasMenuBarAttribute as String) {
            barreVue = true
            if !AX.children(extras).isEmpty { return .pret }
        }
        if !barreVue && Date() > finDeGrace { return .sansMenu }
        Thread.sleep(forTimeInterval: 0.3)
    }
    return .expire
}

// MARK: - Per-app result

struct AppResult: Encodable {
    let nom: String
    let bundleID: String
    let chemin: String
    let version: String?
    let categorie: String?
    let deja_lance: Bool
    let lance_par_nous: Bool
    let statut: String          // "ok" | "sans_menu" | "timeout" | "echec_lancement"
    let detail: String?
    let duree_s: Double
    let raccourcis: [Shortcut]
}

func infoValue(_ bundle: Bundle?, _ key: String) -> String? {
    bundle?.object(forInfoDictionaryKey: key) as? String
}

func process(bundleID: String, options: Options) -> AppResult {
    let started = Date()
    let workspace = NSWorkspace.shared
    let url = workspace.urlForApplication(withBundleIdentifier: bundleID)
    let bundle = url.flatMap { Bundle(url: $0) }
    let name = url.flatMap {
        FileManager.default.displayName(atPath: $0.path).replacingOccurrences(of: ".app", with: "")
    } ?? bundleID

    func result(_ statut: String, _ detail: String?, _ shortcuts: [Shortcut],
                running: Bool, launched: Bool) -> AppResult {
        AppResult(nom: name, bundleID: bundleID, chemin: url?.path ?? "",
                  version: infoValue(bundle, "CFBundleShortVersionString"),
                  categorie: infoValue(bundle, "LSApplicationCategoryType"),
                  deja_lance: running, lance_par_nous: launched,
                  statut: statut, detail: detail,
                  duree_s: (Date().timeIntervalSince(started) * 10).rounded() / 10,
                  raccourcis: shortcuts)
    }

    guard let url else {
        return result("echec_lancement", "Aucune app installée avec cet identifiant",
                      [], running: false, launched: false)
    }

    // Apps published by Parallels are gateways to a Windows virtual machine: opening one
    // would boot the VM. Out of scope, and never launched, even if a bundle identifier
    // leads there.
    if url.path.contains("Applications (Parallels)") {
        return result("hors_perimetre", "App Windows publiée par Parallels",
                      [], running: false, launched: false)
    }

    var running = workspace.runningApplications.first { $0.bundleIdentifier == bundleID }
    let wasRunning = running != nil
    var launchedByUs = false

    if running == nil {
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = false        // do not steal the user's focus
        configuration.hides = true             // hide the windows that open
        configuration.addsToRecentItems = false
        let semaphore = DispatchSemaphore(value: 0)
        var launchError: Error?
        workspace.openApplication(at: url, configuration: configuration) { app, error in
            running = app
            launchError = error
            semaphore.signal()
        }
        if semaphore.wait(timeout: .now() + options.timeout) == .timedOut {
            // The open was genuinely requested: if the app does eventually come up, it
            // would stay open when we alone launched it. We close it once the system
            // finally answers, and the record tells the truth — "launched by us", not
            // "never launched".
            if !options.keepRunning {
                DispatchQueue.global(qos: .utility).async {
                    if semaphore.wait(timeout: .now() + options.timeout) == .success {
                        running?.terminate()
                    }
                }
            }
            return result("timeout", "Lancement non terminé dans le délai imparti",
                          [], running: false, launched: true)
        }
        if let launchError {
            return result("echec_lancement", launchError.localizedDescription,
                          [], running: false, launched: false)
        }
        launchedByUs = true
    }

    guard let process = running else {
        return result("echec_lancement", "Processus introuvable après lancement",
                      [], running: wasRunning, launched: launchedByUs)
    }

    // Held for the duration of the read, so an interrupt knows what to close.
    if launchedByUs && !options.keepRunning { appEnCours = process }

    // The budget restarts here: the launch has already consumed its own, and counting it
    // twice would class a slow-to-open but healthy app as "timed out".
    let deadline = Date().addingTimeInterval(options.timeout)
    let etat = waitForMenuBar(pid: process.processIdentifier, deadline: deadline,
                              timeout: options.timeout)
    var tronque = false
    var shortcuts: [Shortcut] = []
    if etat == .pret {
        let lecture = harvest(pid: process.processIdentifier, timeout: options.timeout,
                              limite: Date().addingTimeInterval(options.timeout))
        shortcuts = lecture.raccourcis
        tronque = lecture.tronque
    }

    // We quit only what we launched, and never by force: a forceTerminate can lose
    // unsaved work.
    if launchedByUs && !options.keepRunning {
        process.terminate()
    }
    appEnCours = nil

    let statut: String
    let detail: String?
    switch etat {
    case .pret:
        // A truncated read is still usable, but it is incomplete: saying so beats letting
        // it pass for an exhaustive inventory.
        statut = "ok"
        detail = tronque
            ? "Lecture interrompue au délai imparti : la barre de menu n'a pas été "
              + "parcourue en entier"
            : nil
    case .sansMenu:
        statut = "sans_menu"
        detail = "Aucune barre de menu exposée (app sans menu, ou agent d'arrière-plan)"
    case .expire:
        statut = "timeout"
        detail = "Barre de menu présente mais jamais peuplée avant expiration du "
               + "délai — l'app est peut-être arrêtée sur un sélecteur ou une fenêtre modale"
    }
    return result(statut, detail, shortcuts, running: wasRunning, launched: launchedByUs)
}

// MARK: - Entry point

let options = parseArgs()

// The journal merges standard output and standard error — which is what one wants of
// progress meant to be read. But --catalogue and --keymap emit their data on standard
// output: mixing them in would produce invalid JSON, with nothing to flag it. Refusing
// beats a corrupted file.
if options.journal != nil && (options.catalogue || options.keymap) {
    FileHandle.standardError.write(
        "--journal est incompatible avec --catalogue et --keymap, dont la sortie standard porte les données.\n"
            .data(using: .utf8)!)
    sortir(2)
}

// Key code -> character mapping, for the active keyboard layout.
//
// Essential for comparing shortcuts from different sources: menus expose a character
// ("V"), third-party tools a raw key code (9). Translating one into the other with an ANSI
// table would give wrong answers on an AZERTY keyboard — code 41 produces "m" there, not
// ";". So the answer is asked of the system, for the layout actually in service.
func dumpKeymap() {
    guard let source = TISCopyCurrentKeyboardLayoutInputSource()?.takeRetainedValue(),
          let pointer = TISGetInputSourceProperty(source, kTISPropertyUnicodeKeyLayoutData)
    else {
        FileHandle.standardError.write("Disposition clavier illisible\n".data(using: .utf8)!)
        sortir(1)
    }
    // The layout governs every combination displayed: its name belongs in the result, not
    // in a comment.
    func propriete(_ cle: CFString) -> String {
        guard let brut = TISGetInputSourceProperty(source, cle) else { return "" }
        return (Unmanaged<CFString>.fromOpaque(brut).takeUnretainedValue() as String)
    }
    let nom = propriete(kTISPropertyLocalizedName)
    let identifiant = propriete(kTISPropertyInputSourceID)

    let layoutData = Unmanaged<CFData>.fromOpaque(pointer).takeUnretainedValue() as Data
    var entries: [String] = []

    layoutData.withUnsafeBytes { raw in
        guard let layout = raw.baseAddress?.assumingMemoryBound(to: UCKeyboardLayout.self)
        else { return }

        func echapper(_ texte: String) -> String {
            texte.replacingOccurrences(of: "\\", with: "\\\\")
                 .replacingOccurrences(of: "\"", with: "\\\"")
        }

        func translate(_ code: UInt16, shifted: Bool) -> String? {
            var deadKeyState: UInt32 = 0
            var length = 0
            var characters = [UniChar](repeating: 0, count: 8)
            // UCKeyTranslate expects the modifier state shifted by 8 bits.
            let modifierState = shifted ? UInt32(shiftKey >> 8) : 0
            let status = UCKeyTranslate(
                layout, code, UInt16(kUCKeyActionDown), modifierState, UInt32(LMGetKbdType()),
                UInt32(kUCKeyTranslateNoDeadKeysMask), &deadKeyState,
                characters.count, &length, &characters)
            guard status == noErr, length > 0 else { return nil }
            let text = String(utf16CodeUnits: characters, count: length)
            // Control characters (return, tab) are not displayable: their label comes
            // from the glyph table, not from here.
            guard text.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) })
            else { return nil }
            return echapper(text)
        }

        for code in UInt16(0)...127 {
            guard let plain = translate(code, shifted: false) else { continue }
            // Both levels are needed: on AZERTY the "4" key produces "'" without Shift.
            // Apple still displays ⇧⌘4 — the shifted character serves as the label as soon
            // as Shift is part of the combination.
            let shifted = translate(code, shifted: true) ?? plain
            entries.append("  \"\(code)\": [\"\(plain)\", \"\(shifted)\"]")
        }
    }
    print("""
    {
      "disposition": "\(nom.replacingOccurrences(of: "\"", with: "\\\""))",
      "identifiant": "\(identifiant.replacingOccurrences(of: "\"", with: "\\\""))",
      "touches": {
    \(entries.joined(separator: ",\n"))
      }
    }
    """)
    sortir(0)
}

if options.keymap { dumpKeymap() }

/// Refuses to continue without accessibility permission.
///
/// Called only by the modes that genuinely read a menu bar. Listing installed apps or
/// exporting the keyboard layout requires nothing: demanding the grant for those modes
/// would make the page impossible to regenerate after a rebuild, when no application is
/// being opened at all.
func exigerAutorisation() {
    guard AX.isTrusted() else {
        FileHandle.standardError.write("""
        ⛔️ Autorisation d'accessibilité absente.

        Ouvrir Réglages Système → Confidentialité et sécurité → Accessibilité, puis
        y faire glisser ce bundle :
          \(Bundle.main.bundleURL.path)

        S'il y figure déjà, c'est que la ligne date d'une compilation antérieure : la
        retirer avec « − » puis la remettre. L'autorisation est liée à l'empreinte
        exacte du binaire, qu'un aller-retour de l'interrupteur ne réenregistre pas.

        """.data(using: .utf8)!)
        sortir(1)
    }
}

if let chemin = options.verdict {
    try? (AX.isTrusted() ? "accordee" : "absente")
        .write(toFile: chemin, atomically: true, encoding: .utf8)
    if options.checkOnly { sortir(AX.isTrusted() ? 0 : 1) }
}

if options.checkOnly {
    exigerAutorisation()
    print("✅ Autorisation d'accessibilité accordée.")
    sortir(0)
}

struct Installee: Encodable {
    let nom: String
    let bundleID: String
    let chemin: String
    let version: String?
    let categorie: String?
    let exclu: Bool
    let raison: String?
    // Locked: an exclusion the user cannot lift from the page. These apps trigger a heavy
    // or destructive action on launch alone.
    let verrou: Bool
}

/// Exclusions set by hand from the page. The file is written by the user, not by the
/// program: its absence is the normal case, not an error.
func reglagesManuels(_ chemin: String) -> (exclues: Set<String>, incluses: Set<String>) {
    // Absent, the file gives the same result as an empty one: no exclusions. That is the
    // normal case on a fresh install, but it is also what would happen if the path were
    // relative and the program launched by `open` — hand-set exclusions would then be
    // ignored in silence, and skipped apps would open anyway.
    if !FileManager.default.fileExists(atPath: chemin) {
        FileHandle.standardError.write(
            "ℹ️  Aucun réglage manuel : \(URL(fileURLWithPath: chemin).path) est absent.\n"
                .data(using: .utf8)!)
        return ([], [])
    }
    guard let data = FileManager.default.contents(atPath: chemin),
          let objet = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    else { return ([], []) }
    return (Set(objet["exclues"] as? [String] ?? []),
            Set(objet["incluses"] as? [String] ?? []))
}

/// Lists the apps installed in the folders swept, saying for each whether the pass skips
/// it and why. Nothing is launched here.
func recenser(includeGames: Bool,
              exclues: Set<String> = [], incluses: Set<String> = []) -> [Installee] {
    // Explicit paths, no recursion. Two folders are deliberately absent:
    //   ~/Applications              personal library, most often a game collection
    //   ~/Applications (Parallels)  gateways to a Windows virtual machine
    // Opening those would cost gigabytes of loading for an empty menu bar, or would boot a
    // VM outright.
    var directories = ["/Applications", "/Applications/Utilities",
                       "/System/Applications", "/System/Applications/Utilities"]
    directories.append(NSHomeDirectory() + "/Applications")

    // Installers commonly file their apps under a sub-folder named after themselves
    // (/Applications/<vendor>/, /Applications/<product>.localized), sometimes two levels
    // deep (/Applications/<vendor>/<product>/). Without this descent they are invisible to
    // the census, therefore absent from the page and impossible to tick.
    //
    // A folder whose name carries an extension is a **package**, not a filing cabinet:
    // descending into it would surface internal executables nobody launches, such as the
    // driver installer lodged inside a .bundle.
    let paquets = [".app", ".bundle", ".framework", ".plugin", ".kext", ".prefPane",
                   ".qlgenerator", ".appex", ".xpc"]
    func sousDossiers(_ racine: String, profondeur: Int) -> [String] {
        guard profondeur > 0 else { return [] }
        var trouves: [String] = []
        let contenu = ((try? FileManager.default.contentsOfDirectory(atPath: racine)) ?? []).sorted()
        for entree in contenu where !paquets.contains(where: { entree.hasSuffix($0) }) {
            let chemin = racine + "/" + entree
            var estDossier: ObjCBool = false
            guard FileManager.default.fileExists(atPath: chemin, isDirectory: &estDossier),
                  estDossier.boolValue else { continue }
            trouves.append(chemin)
            trouves += sousDossiers(chemin, profondeur: profondeur - 1)
        }
        return trouves
    }
    for chemin in sousDossiers("/Applications", profondeur: 2)
    where !directories.contains(chemin) {
        directories.append(chemin)
    }

    // Game launchers: no declared category, but the same launch cost.
    let gameLaunchers: Set<String> = ["com.valvesoftware.steam"]

    // Apps never launched automatically: opening one triggers a heavy or destructive
    // action, unrelated to reading a menu bar.
    let neverLaunch: [String: String] = [
        "com.apple.MigrateAssistant": "ferme toutes les apps et déconnecte la session",
        "com.apple.bootcampassistant": "assistant de partitionnement de disque",
        "com.apple.backup.launcher": "ouvre l'interface de restauration en plein écran",
        // System-function triggers: they have no menu bar, and two passes (25 s then
        // 45 s) confirmed it. Nothing is lost — their shortcuts are inventoried on the
        // system side, through the tables of the macOS Keyboard panel.
        "com.apple.exposelauncher": "déclencheur système, aucune barre de menu",
        // Observed: it fires a capture on opening and takes over the screen.
        "com.apple.screenshot.launcher": "déclenche une capture dès le lancement",
        "com.apple.siri.launcher": "déclencheur système, aucune barre de menu",
        "com.apple.apps.launcher": "déclencheur système, aucune barre de menu",
        "com.apple.ScreenContinuity": "déclencheur système, aucune barre de menu",
    ]

    // Uninstallers are recognised by name, whichever the vendor: a general rule beats a
    // list of identifiers collected from one machine.
    func estDesinstalleur(_ nom: String) -> Bool {
        let minuscule = nom.lowercased()
        return ["uninstall", "désinstall", "desinstall", "deinstall"]
            .contains { minuscule.contains($0) }
    }

    var seen = Set<String>()
    var out: [Installee] = []
    for directory in directories {
        let bibliothequeJeux = directory == NSHomeDirectory() + "/Applications"
        let contents = (try? FileManager.default.contentsOfDirectory(atPath: directory)) ?? []
        for entry in contents.sorted() where entry.hasSuffix(".app") {
            let path = directory + "/" + entry
            guard let bundle = Bundle(path: path), let id = bundle.bundleIdentifier
            else { continue }
            // Two apps can share one identifier: since launching goes by identifier, the
            // second is unreachable. We keep the first and say so rather than letting it
            // disappear in silence.
            guard seen.insert(id.lowercased()).inserted else {
                FileHandle.standardError.write(
                    "  ℹ️  \(entry) partage l'identifiant \(id), déjà recensé — ignorée\n"
                        .data(using: .utf8)!)
                continue
            }
            let category = infoValue(bundle, "LSApplicationCategoryType")
            var raison: String?
            let nom = FileManager.default.displayName(atPath: path)
                .replacingOccurrences(of: ".app", with: "")
            let verrou = neverLaunch[id] != nil
            if let motif = neverLaunch[id] {
                raison = motif
            } else if incluses.contains(id) {
                // The user's explicit choice: it wins over the program's rules, except
                // over the locked exclusions above.
                raison = nil
            } else if exclues.contains(id) {
                raison = "écartée à la main"
            } else if estDesinstalleur(nom) {
                raison = "désinstalleur"
            } else if !includeGames {
                if bibliothequeJeux {
                    raison = "dossier d'applications personnel (~/Applications)"
                } else if (category ?? "").contains("games") {
                    raison = "jeu"
                } else if gameLaunchers.contains(id) {
                    raison = "lanceur de jeux"
                }
            }
            out.append(Installee(
                nom: nom, bundleID: id, chemin: path,
                version: infoValue(bundle, "CFBundleShortVersionString"),
                categorie: category, exclu: raison != nil, raison: raison,
                verrou: verrou))
        }
    }
    return out.sorted { $0.nom.localizedCaseInsensitiveCompare($1.nom) == .orderedAscending }
}

let catalogueEncoder = JSONEncoder()
catalogueEncoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]

if options.catalogue {
    let reglages = reglagesManuels(options.reglages)
    let liste = recenser(includeGames: options.includeGames,
                         exclues: reglages.exclues, incluses: reglages.incluses)
    if let data = try? catalogueEncoder.encode(liste),
       let texte = String(data: data, encoding: .utf8) { print(texte) }
    sortir(0)
}

var targets = options.bundleIDs
if options.scanAll {
    let reglages = reglagesManuels(options.reglages)
    let installees = recenser(includeGames: options.includeGames,
                              exclues: reglages.exclues, incluses: reglages.incluses)
    targets += installees.filter { !$0.exclu }.map(\.bundleID)
    print("\(targets.count) apps à parcourir"
        + (options.includeGames ? " (jeux inclus)" : " (jeux exclus — --include-games pour les garder)"))
    for app in installees where app.exclu {
        print("  écartée : \(app.nom) — \(app.raison ?? "")")
    }
}

guard !targets.isEmpty else {
    FileHandle.standardError.write("Rien à faire : passe --bundle-ids ou --all.\n".data(using: .utf8)!)
    sortir(2)
}

// Exit before any write and any launch: --dry-run must stay harmless.
if options.dryRun {
    for (index, bundleID) in targets.enumerated() {
        print("[\(index + 1)/\(targets.count)] \(bundleID)")
    }
    sortir(0)
}

// The output folder is tested BEFORE opening a single application. Without this check, a
// whole pass can unfold — each app opened, read, closed — only to write nowhere, and the
// program would still exit announcing success.
//
// The case is not theoretical: LaunchServices does not pass on the working directory, so a
// program launched by `open` starts at the root of the disk. A relative path there means
// "/out/apps", where nothing is writable. Hence the reminder of the absolute path actually
// aimed at, which makes the cause readable at a glance.
do {
    try FileManager.default.createDirectory(atPath: options.outDir,
                                            withIntermediateDirectories: true)
} catch {
    FileHandle.standardError.write("""
    ⛔️ Dossier de sortie inutilisable : \(options.outDir)
       \(error.localizedDescription)
       Chemin absolu visé   : \(URL(fileURLWithPath: options.outDir).path)
       Répertoire courant   : \(FileManager.default.currentDirectoryPath)

       Un chemin relatif ne veut rien dire pour un programme lancé par `open` :
       passer --out avec un chemin absolu.

    """.data(using: .utf8)!)
    sortir(1)
}
guard FileManager.default.isWritableFile(atPath: options.outDir) else {
    FileHandle.standardError.write(
        "⛔️ Dossier de sortie en lecture seule : \(URL(fileURLWithPath: options.outDir).path)\n"
            .data(using: .utf8)!)
    sortir(1)
}
exigerAutorisation()

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]

/// Writes that failed. A pass that could write nothing must say so through its exit code:
/// run.sh does not read messages, it reads the status.
var echecsEcriture = 0

func runAll() {
    for (index, bundleID) in targets.enumerated() {
        // A bundle identifier serves as a file name here. It is read from disk, so it is
        // not trusted: a "/" in it would write outside the output folder. The characters
        // allowed are the ones Apple recommends for an identifier.
        guard !bundleID.isEmpty,
              bundleID.allSatisfy({ $0.isLetter || $0.isNumber || ".-_ ".contains($0) })
        else {
            FileHandle.standardError.write(
                "⛔️ Identifiant refusé, caractères inattendus : \(bundleID)\n"
                    .data(using: .utf8)!)
            continue
        }
        let file = "\(options.outDir)/\(bundleID).json"
        // Resume: an interrupted pass does not redo what is already on disk.
        if !options.force && FileManager.default.fileExists(atPath: file) {
            print("[\(index + 1)/\(targets.count)] \(bundleID) — déjà fait, ignoré")
            continue
        }
        // Re-read without opening. Opening an app is the only genuinely intrusive part of
        // a pass: it appears while you are working. Limiting the pass to apps already
        // running refreshes stale records without anything moving on screen.
        if options.onlyRunning,
           !NSWorkspace.shared.runningApplications.contains(
                where: { $0.bundleIdentifier == bundleID }) {
            print("[\(index + 1)/\(targets.count)] \(bundleID) — non lancée, inchangée")
            continue
        }
        let outcome = process(bundleID: bundleID, options: options)
        // An automatic re-read must never impoverish the inventory. An app opened without
        // a document exposes fewer commands: overwriting a full record with an empty one
        // would lose shortcuts nobody asked to lose.
        if options.onlyRunning, outcome.raccourcis.isEmpty,
           let brut = FileManager.default.contents(atPath: file),
           let objet = try? JSONSerialization.jsonObject(with: brut) as? [String: Any],
           let avant = objet["raccourcis"] as? [Any], !avant.isEmpty {
            print("[\(index + 1)/\(targets.count)] ⚠️  \(outcome.nom) — "
                + "0 raccourci lu, fiche précédente conservée (\(avant.count))")
            continue
        }
        var ecrit = false
        do {
            try encoder.encode(outcome).write(to: URL(fileURLWithPath: file))
            ecrit = true
        } catch {
            echecsEcriture += 1
            FileHandle.standardError.write(
                "⛔️ Écriture impossible : \(file) — \(error.localizedDescription)\n"
                    .data(using: .utf8)!)
        }
        let mark = !ecrit ? "⛔️" : (outcome.statut == "ok" ? "✅" : "⚠️ ")
        print("[\(index + 1)/\(targets.count)] \(mark) \(outcome.nom) — "
            + "\(outcome.raccourcis.count) raccourcis, \(outcome.statut), \(outcome.duree_s)s"
            + (outcome.lance_par_nous ? " (lancée par nous)"
           : outcome.deja_lance ? " (déjà lancée)" : " (non lancée)"))
        fflush(stdout)
    }
}

// An interrupt — Ctrl-C, or the signal run.sh sends to stop a pass — must close the
// application open at the moment it arrives.
//
// The handler cannot be a POSIX signal handler: almost nothing is callable from one, and
// `terminate()` least of all. DispatchSource delivers the signal as an ordinary event on
// the main loop, which this program keeps free on purpose. The default disposition must be
// neutralised first, though, otherwise the process is killed before the event reaches
// it.
let sourcesSignal: [DispatchSourceSignal] = [SIGINT, SIGTERM].map { numero in
    signal(numero, SIG_IGN)
    let source = DispatchSource.makeSignalSource(signal: numero, queue: .main)
    source.setEventHandler {
        appEnCours?.terminate()
        appEnCours = nil
        // Gives the system time to deliver the quit request before returning: the request
        // leaves from here, but it is handled by the other process.
        usleep(300_000)
        sortir(130)
    }
    source.resume()
    return source
}
_ = sourcesSignal   // kept alive: releasing them would cancel the watch

// All the work runs off the main thread, which stays free for the run loop.
// NSWorkspace.openApplication calls its completion block back through that loop: blocking
// the main thread while waiting for it would deadlock.
DispatchQueue.global(qos: .userInitiated).async {
    runAll()
    if echecsEcriture > 0 {
        FileHandle.standardError.write(
            "⛔️ \(echecsEcriture) fiche(s) n'ont pas pu être écrites.\n".data(using: .utf8)!)
    }
    sortir(echecsEcriture > 0 ? 1 : 0)
}
RunLoop.main.run()
