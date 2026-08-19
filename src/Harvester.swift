// Moissonneur de raccourcis de menu macOS.
//
// Pourquoi ce binaire existe : les raccourcis d'une app ne sont écrits nulle part sur
// le disque. Ils ne vivent que dans la barre de menu construite en mémoire au lancement.
// Le seul moyen de les lire est l'API d'accessibilité (AX), qui exige une autorisation
// explicite — d'où un binaire dédié plutôt qu'un script : l'autorisation ne concerne
// que lui, et pas le terminal entier.
//
// Il émet du JSON brut (caractère, masque de modificateurs, glyphe). Le rendu lisible
// (⌘⇧K) est fait côté Python, où vivent les tables extraites de macOS.

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
    var force = false              // refaire les apps déjà moissonnées
    var reglages = "out/reglages-scan.json"   // exclusions posées à la main
    var onlyRunning = false        // ne relire que les apps déjà ouvertes
    var includeGames = false       // les jeux sont écartés par défaut
    var dryRun = false             // lister les cibles sans rien lancer
    var verdict: String?           // où écrire le résultat de --check
    var keymap = false             // exporter la correspondance code de touche -> caractère
    var catalogue = false          // exporter la liste des apps installées, sans rien lancer
    var keepRunning = false        // ne pas quitter les apps qu'on a lancées
}

func parseArgs() -> Options {
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
        case "--keymap": o.keymap = true
        case "--catalogue": o.catalogue = true
        case "--bundle-ids": o.bundleIDs = (it.next() ?? "").split(separator: ",").map(String.init)
        case "--out": o.outDir = it.next() ?? o.outDir
        case "--timeout": o.timeout = Double(it.next() ?? "") ?? o.timeout
        default:
            FileHandle.standardError.write("Option inconnue : \(arg)\n".data(using: .utf8)!)
            exit(2)
        }
    }
    return o
}

// MARK: - Accessibilité

enum AX {
    static func isTrusted() -> Bool {
        AXIsProcessTrustedWithOptions(
            [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: false] as CFDictionary)
    }

    static func app(_ pid: pid_t, timeout: Float) -> AXUIElement {
        let element = AXUIElementCreateApplication(pid)
        // Sans plafond, une app bloquée sur une boîte de dialogue fige la lecture.
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

// MARK: - Parcours des menus

struct Shortcut: Encodable {
    let chemin: String        // "Fichier > Enregistrer sous…"
    let menu: String          // menu de premier niveau
    let caractere: String?    // AXMenuItemCmdChar
    let glyphe: Int?          // AXMenuItemCmdGlyph (touches non imprimables)
    let modificateurs: Int    // AXMenuItemCmdModifiers, format AX
    let source: String        // "menubar" ou "extras"
}

let maxDepth = 12  // les menus réels plafonnent vers 5 ; au-delà, l'arbre est suspect

func walk(_ items: [AXUIElement], path: [String], menu: String, source: String,
          depth: Int, limite: Date, into found: inout [Shortcut], tronque: inout Bool) {
    guard depth < maxDepth else { return }
    for item in items {
        // Le délai borne aussi le parcours de l'arbre, pas seulement l'attente de la
        // barre de menu. Sans cela, le seul plafond est le délai **par message**
        // d'accessibilité, appliqué à chacune des centaines de requêtes : un serveur
        // lent répond à chaque fois dans les temps tout en immobilisant la passe bien
        // au-delà du délai annoncé.
        if Date() >= limite { tronque = true; return }
        let title = AX.string(item, kAXTitleAttribute as String) ?? ""
        let subPath = title.isEmpty ? path : path + [title]

        let char = AX.string(item, "AXMenuItemCmdChar")
        let glyph = AX.int(item, "AXMenuItemCmdGlyph")
        // Un raccourci existe si un caractère OU un glyphe est présent. HotkeyClash
        // n'exploite que le caractère ; pour un inventaire il faut aussi les glyphes,
        // sinon toutes les flèches et touches F disparaissent silencieusement.
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

/// Délai laissé à une app fraîchement lancée pour construire sa barre de menu, avant
/// de conclure qu'elle n'en a pas.
let delaiDeGrace: Double = 4

/// Attend que la barre de menu soit lisible.
///
/// Trois issues, et la distinction compte : une app d'arrière-plan n'expose aucune
/// barre de menu et le savoir en quatre secondes évite d'attendre le délai complet
/// pour chacune. Confondre les deux cas coûtait plusieurs minutes par passe et
/// donnait un diagnostic faux.
func waitForMenuBar(pid: pid_t, deadline: Date, timeout: Double) -> EtatMenu {
    let finDeGrace = Date().addingTimeInterval(delaiDeGrace)
    var barreVue = false

    while Date() < deadline {
        let app = AX.app(pid, timeout: Float(min(timeout, 5)))
        if let bar = AX.element(app, kAXMenuBarAttribute as String) {
            barreVue = true
            let menus = AX.children(bar).count
            // Plus d'un menu = barre construite. Un seul menu peut être un état
            // transitoire au lancement : on ne l'accepte qu'une fois le délai de
            // grâce passé, faute de quoi une app à menu unique expirerait.
            if menus > 1 || (menus >= 1 && Date() > finDeGrace) { return .pret }
        }
        // Les apps d'arrière-plan n'ont pas de barre de menu classique : leurs
        // raccourcis vivent dans le menu de leur icône de statut.
        if let extras = AX.element(app, kAXExtrasMenuBarAttribute as String) {
            barreVue = true
            if !AX.children(extras).isEmpty { return .pret }
        }
        if !barreVue && Date() > finDeGrace { return .sansMenu }
        Thread.sleep(forTimeInterval: 0.3)
    }
    return .expire
}

// MARK: - Résultat par app

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

    // Les apps publiées par Parallels sont des passerelles vers un Windows en machine
    // virtuelle : les ouvrir démarrerait la VM. Hors périmètre, et jamais lancées,
    // même si un identifiant de bundle y mène.
    if url.path.contains("Applications (Parallels)") {
        return result("hors_perimetre", "App Windows publiée par Parallels",
                      [], running: false, launched: false)
    }

    var running = workspace.runningApplications.first { $0.bundleIdentifier == bundleID }
    let wasRunning = running != nil
    var launchedByUs = false

    if running == nil {
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = false        // ne pas voler le focus à l'utilisateur
        configuration.hides = true             // masquer les fenêtres qui s'ouvrent
        configuration.addsToRecentItems = false
        let semaphore = DispatchSemaphore(value: 0)
        var launchError: Error?
        workspace.openApplication(at: url, configuration: configuration) { app, error in
            running = app
            launchError = error
            semaphore.signal()
        }
        if semaphore.wait(timeout: .now() + options.timeout) == .timedOut {
            // L'ouverture a bien été demandée : si l'app finit par s'ouvrir, elle
            // resterait ouverte alors que nous seuls l'avons lancée. On la referme
            // quand le système nous répond enfin, et la fiche dit la vérité —
            // « lancée par nous », et non « jamais lancée ».
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

    // Le délai repart d'ici : le lancement a déjà consommé son propre budget, et le
    // décompter deux fois classerait « expirée » une app lente à ouvrir mais saine.
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

    // On ne quitte que ce qu'on a lancé, et jamais de force : un forceTerminate peut
    // faire perdre du travail non enregistré.
    if launchedByUs && !options.keepRunning {
        process.terminate()
    }

    let statut: String
    let detail: String?
    switch etat {
    case .pret:
        // Une lecture écourtée reste utilisable, mais elle est incomplète : le dire
        // vaut mieux que laisser croire à un inventaire exhaustif.
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
        detail = "Barre de menu non peuplée avant expiration du délai"
    }
    return result(statut, detail, shortcuts, running: wasRunning, launched: launchedByUs)
}

// MARK: - Entrée

let options = parseArgs()

// Correspondance code de touche -> caractère, pour la disposition clavier active.
//
// Indispensable pour comparer des raccourcis venus de sources différentes : les menus
// exposent un caractère ("V"), les outils tiers un code de touche brut (9). Traduire
// l'un en l'autre avec une table ANSI donnerait des résultats faux sur un clavier
// AZERTY — le code 41 y produit « m », pas « ; ». On demande donc la réponse au
// système, pour la disposition réellement en service.
func dumpKeymap() {
    guard let source = TISCopyCurrentKeyboardLayoutInputSource()?.takeRetainedValue(),
          let pointer = TISGetInputSourceProperty(source, kTISPropertyUnicodeKeyLayoutData)
    else {
        FileHandle.standardError.write("Disposition clavier illisible\n".data(using: .utf8)!)
        exit(1)
    }
    // La disposition conditionne toutes les combinaisons affichées : son nom fait
    // partie du résultat, pas d'un commentaire.
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
            // UCKeyTranslate attend l'état des modificateurs décalé de 8 bits.
            let modifierState = shifted ? UInt32(shiftKey >> 8) : 0
            let status = UCKeyTranslate(
                layout, code, UInt16(kUCKeyActionDown), modifierState, UInt32(LMGetKbdType()),
                UInt32(kUCKeyTranslateNoDeadKeysMask), &deadKeyState,
                characters.count, &length, &characters)
            guard status == noErr, length > 0 else { return nil }
            let text = String(utf16CodeUnits: characters, count: length)
            // Les caractères de contrôle (retour, tabulation) ne sont pas affichables :
            // leur libellé vient de la table des glyphes, pas d'ici.
            guard text.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) })
            else { return nil }
            return echapper(text)
        }

        for code in UInt16(0)...127 {
            guard let plain = translate(code, shifted: false) else { continue }
            // Les deux niveaux sont nécessaires : sur AZERTY la touche du « 4 » produit
            // « ' » sans Maj. Apple affiche pourtant ⇧⌘4 — c'est le caractère décalé
            // qui sert de libellé dès que Maj fait partie de la combinaison.
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
    exit(0)
}

if options.keymap { dumpKeymap() }

/// Refuse de continuer sans l'autorisation d'accessibilité.
///
/// N'est appelé que par les modes qui lisent réellement une barre de menu. Recenser
/// les apps installées ou exporter la disposition clavier ne demande rien : exiger
/// l'autorisation pour ces modes rendrait la page impossible à régénérer après une
/// recompilation, alors qu'aucune application n'y est ouverte.
func exigerAutorisation() {
    guard AX.isTrusted() else {
        FileHandle.standardError.write("""
        ⛔️ Autorisation d'accessibilité absente.

        Ouvre Réglages Système → Confidentialité et sécurité → Accessibilité,
        ajoute ce binaire, et relance :
          \(Bundle.main.bundleURL.path)

        """.data(using: .utf8)!)
        exit(1)
    }
}

if let chemin = options.verdict {
    try? (AX.isTrusted() ? "accordee" : "absente")
        .write(toFile: chemin, atomically: true, encoding: .utf8)
    if options.checkOnly { exit(AX.isTrusted() ? 0 : 1) }
}

if options.checkOnly {
    exigerAutorisation()
    print("✅ Autorisation d'accessibilité accordée.")
    exit(0)
}

struct Installee: Encodable {
    let nom: String
    let bundleID: String
    let chemin: String
    let version: String?
    let categorie: String?
    let exclu: Bool
    let raison: String?
    // Verrouillée : exclusion que l'utilisateur ne peut pas lever depuis la page.
    // Ces apps déclenchent une action lourde ou destructrice au simple lancement.
    let verrou: Bool
}

/// Recense les apps installées dans les dossiers balayés, en indiquant pour chacune
/// Exclusions posées à la main depuis la page. Le fichier est écrit par l'utilisateur,
/// pas par le programme : son absence est le cas normal, pas une erreur.
func reglagesManuels(_ chemin: String) -> (exclues: Set<String>, incluses: Set<String>) {
    guard let data = FileManager.default.contents(atPath: chemin),
          let objet = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    else { return ([], []) }
    return (Set(objet["exclues"] as? [String] ?? []),
            Set(objet["incluses"] as? [String] ?? []))
}

/// si la passe l'écarte et pourquoi. Rien n'est lancé ici.
func recenser(includeGames: Bool,
              exclues: Set<String> = [], incluses: Set<String> = []) -> [Installee] {
    // Chemins explicites, sans récursion. Deux dossiers du dossier de départ sont
    // volontairement absents :
    //   ~/Applications              bibliothèque Steam (23 jeux sur 25 apps)
    //   ~/Applications (Parallels)  passerelles vers un Windows en machine virtuelle
    // Les ouvrir coûterait plusieurs gigaoctets de chargement pour une barre de menu
    // vide, voire démarrerait une VM.
    var directories = ["/Applications", "/Applications/Utilities",
                       "/System/Applications", "/System/Applications/Utilities"]
    directories.append(NSHomeDirectory() + "/Applications")

    // Les installeurs rangent couramment leurs apps dans un sous-dossier à leur nom
    // (/Applications/Arturia, /Applications/Antidote, /Applications/WhatsApp.localized),
    // parfois sur deux niveaux (/Applications/Native Instruments/Controller Editor/).
    // Sans cette descente elles sont invisibles du recensement, donc absentes de la
    // page et impossibles à cocher.
    //
    // Un dossier dont le nom porte une extension est un **paquet**, pas un rangement :
    // y descendre remonterait des exécutables internes qu'aucun utilisateur ne lance,
    // tel l'installeur de pilote logé dans un .bundle.
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

    // Lanceurs de jeux : pas de catégorie déclarée, mais même coût de lancement.
    let gameLaunchers: Set<String> = ["com.valvesoftware.steam"]

    // Apps qu'on ne lance jamais automatiquement : les ouvrir déclenche une action
    // lourde ou destructrice, sans rapport avec la lecture d'une barre de menu.
    let neverLaunch: [String: String] = [
        "com.apple.MigrateAssistant": "ferme toutes les apps et déconnecte la session",
        "com.apple.bootcampassistant": "assistant de partitionnement de disque",
        "com.apple.backup.launcher": "ouvre l'interface de restauration en plein écran",
        // Déclencheurs de fonctions système : ils n'ont pas de barre de menu, et deux
        // passes (25 s puis 45 s) l'ont confirmé. Rien n'est perdu — leurs raccourcis
        // sont inventoriés côté système, via les tables du panneau Clavier de macOS.
        "com.apple.exposelauncher": "déclencheur système, aucune barre de menu",
        // Observé : elle déclenche une capture dès l'ouverture et s'empare de l'écran.
        "com.apple.screenshot.launcher": "déclenche une capture dès le lancement",
        "com.apple.siri.launcher": "déclencheur système, aucune barre de menu",
        "com.apple.apps.launcher": "déclencheur système, aucune barre de menu",
        "com.apple.ScreenContinuity": "déclencheur système, aucune barre de menu",
    ]

    // Les désinstalleurs se reconnaissent à leur nom, quel que soit l'éditeur : une
    // règle générale vaut mieux qu'une liste d'identifiants relevés sur une machine.
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
            // Deux apps peuvent partager un identifiant (digikam et showfoto par
            // exemple) : le lancement se faisant par identifiant, la seconde est
            // inatteignable. On garde la première et on le dit plutôt que de la
            // laisser disparaître en silence.
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
                // Choix explicite de l'utilisateur : il prime sur les règles du
                // programme, sauf sur les exclusions verrouillées ci-dessus.
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
    exit(0)
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
    exit(2)
}

// Sortie avant toute écriture et tout lancement : --dry-run doit rester inoffensif.
if options.dryRun {
    for (index, bundleID) in targets.enumerated() {
        print("[\(index + 1)/\(targets.count)] \(bundleID)")
    }
    exit(0)
}

exigerAutorisation()

try? FileManager.default.createDirectory(atPath: options.outDir,
                                         withIntermediateDirectories: true)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]

func runAll() {
    for (index, bundleID) in targets.enumerated() {
        // Un identifiant de bundle sert ici de nom de fichier. Il est lu sur le disque,
        // donc il n'est pas de confiance : un « / » y ferait écrire hors du dossier de
        // sortie. Les caractères admis sont ceux qu'Apple recommande pour un identifiant.
        guard !bundleID.isEmpty,
              bundleID.allSatisfy({ $0.isLetter || $0.isNumber || ".-_ ".contains($0) })
        else {
            FileHandle.standardError.write(
                "⛔️ Identifiant refusé, caractères inattendus : \(bundleID)\n"
                    .data(using: .utf8)!)
            continue
        }
        let file = "\(options.outDir)/\(bundleID).json"
        // Reprise : une passe interrompue ne recommence pas ce qui est déjà sur le disque.
        if !options.force && FileManager.default.fileExists(atPath: file) {
            print("[\(index + 1)/\(targets.count)] \(bundleID) — déjà fait, ignoré")
            continue
        }
        // Relecture sans ouverture. Ouvrir une app est la seule chose vraiment gênante
        // d'une passe : elle surgit pendant qu'on travaille. Se limiter aux apps déjà
        // lancées permet de rafraîchir des fiches périmées sans que rien ne bouge.
        if options.onlyRunning,
           !NSWorkspace.shared.runningApplications.contains(
                where: { $0.bundleIdentifier == bundleID }) {
            print("[\(index + 1)/\(targets.count)] \(bundleID) — non lancée, inchangée")
            continue
        }
        let outcome = process(bundleID: bundleID, options: options)
        // Une relecture automatique ne doit jamais appauvrir l'inventaire. Une app
        // ouverte sans document expose moins de commandes : écraser une fiche pleine
        // par une fiche vide perdrait des raccourcis sans que personne le demande.
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

// Tout le travail tourne hors du thread principal, qui reste libre pour la boucle
// d'exécution. NSWorkspace.openApplication rappelle son bloc de complétion via
// cette boucle : bloquer le thread principal en l'attendant provoquerait un interblocage.
DispatchQueue.global(qos: .userInitiated).async {
    runAll()
    exit(0)
}
RunLoop.main.run()
