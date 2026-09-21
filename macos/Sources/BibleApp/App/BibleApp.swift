import SwiftUI
import AppKit

@main
struct BibleApp: App {
    // We use a custom AppDelegate to handle Menu Bar logic
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        // No window for a background app
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var menuBarManager: MenuBarManager?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide dock icon
        NSApp.setActivationPolicy(.accessory)
        
        // An .accessory app has no main menu, so AppKit never dispatches the standard
        // key equivalents (Cmd+Q, Cmd+A/C/V/X/Z) to the responder chain. The menu is not
        // displayed; it exists purely so the shortcuts reach the focused text field.
        NSApp.mainMenu = Self.makeMainMenu()

        // Initialize menu bar manager
        menuBarManager = MenuBarManager()
        
        // Ensure server is running (Development Convenience)
        ServerManager.shared.restartServer()
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cmd+Q would otherwise orphan the server process we spawned.
        ServerManager.shared.stopServer()
    }

    /// Minimal main menu holding the standard shortcuts. Every action targets nil so it
    /// travels the responder chain to whatever text field currently has focus.
    static func makeMainMenu() -> NSMenu {
        let app = NSMenu()
        let quit = NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        quit.keyEquivalentModifierMask = .command
        app.addItem(quit)

        let edit = NSMenu(title: "Edit")
        let entries: [(String, Selector, String, NSEvent.ModifierFlags)] = [
            ("Undo", Selector(("undo:")), "z", .command),
            ("Redo", Selector(("redo:")), "z", [.command, .shift]),
            ("Cut", #selector(NSText.cut(_:)), "x", .command),
            ("Copy", #selector(NSText.copy(_:)), "c", .command),
            ("Paste", #selector(NSText.paste(_:)), "v", .command),
            ("Select All", #selector(NSText.selectAll(_:)), "a", .command),
        ]
        for (title, action, key, modifiers) in entries {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
            item.keyEquivalentModifierMask = modifiers
            edit.addItem(item)
        }

        let appItem = NSMenuItem()
        appItem.submenu = app

        let editItem = NSMenuItem()
        editItem.submenu = edit

        let main = NSMenu()
        main.addItem(appItem)   // first item is the application menu
        main.addItem(editItem)
        return main
    }
}
