import SwiftUI
import AppKit

class MenuBarManager: NSObject, NSPopoverDelegate {
    var statusItem: NSStatusItem?
    var popover: NSPopover?
    var eventMonitor: EventMonitor?
    
    override init() {
        super.init()
        setupMenuBar()
        setupPopover()
        setupEventMonitor()
    }
    
    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem?.button {
            // "bolt" or "bolt.fill"
            button.image = NSImage(systemSymbolName: "fish.fill", accessibilityDescription: "Bible Lookup")
            button.action = #selector(togglePopover)
            button.target = self
        }
    }
    
    private func setupPopover() {
        let popover = NSPopover()
        // popover.contentSize = NSSize(width: 400, height: 600) // Let SwiftUI View dictate size
        popover.behavior = .transient // Closes on click outside (mostly)
        
        // Inject ContentView
        let contentView = ContentView()
        popover.contentViewController = NSHostingController(rootView: contentView)
        popover.delegate = self
        
        self.popover = popover
    }
    
    private func setupEventMonitor() {
        // Monitor global clicks to close popover if needed (behavior .transient handles most)
        eventMonitor = EventMonitor(mask: [.leftMouseDown, .rightMouseDown]) { [weak self] event in
            if let strongSelf = self, let popover = strongSelf.popover {
                if popover.isShown {
                    strongSelf.closePopover(sender: event)
                }
            }
        }
    }
    
    @objc func togglePopover(_ sender: AnyObject?) {
        if let popover = popover {
            if popover.isShown {
                closePopover(sender: sender)
            } else {
                showPopover(sender: sender)
            }
        }
    }
    
    func showPopover(sender: AnyObject?) {
        if let button = statusItem?.button {
            popover?.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            eventMonitor?.start()
            // Force focus
            NSApp.activate(ignoringOtherApps: true)
        }
    }
    
    func closePopover(sender: AnyObject?) {
        popover?.performClose(sender)
        eventMonitor?.stop()
    }
}
