import SwiftUI

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
        
        // Initialize menu bar manager
        menuBarManager = MenuBarManager()
        
        // Ensure server is running (Development Convenience)
        ServerManager.shared.restartServer()
    }
}
