import SwiftUI
import AppKit

/// Single source of truth for the popover size, shared by the SwiftUI frame and
/// the NSPopover contentSize so the two can never disagree.
enum PopoverSize {
    static let minimum = CGSize(width: 320, height: 300)
    static let fallback = CGSize(width: 600, height: 500)

    static func clamp(_ size: CGSize) -> CGSize {
        let visible = NSScreen.main?.visibleFrame.size ?? CGSize(width: 1000, height: 700)
        return CGSize(
            width: min(max(size.width, minimum.width), visible.width - 40),
            height: min(max(size.height, minimum.height), visible.height - 40)
        )
    }

    /// Persisted size (same keys as ContentView's @AppStorage), clamped to the screen.
    static var stored: CGSize {
        let defaults = UserDefaults.standard
        return clamp(CGSize(
            width: defaults.object(forKey: "windowWidth_v2") as? Double ?? fallback.width,
            height: defaults.object(forKey: "windowHeight_v2") as? Double ?? fallback.height
        ))
    }
}

struct ContentView: View {
    @State private var selectedTab = 0
    @AppStorage("windowWidth_v2") private var windowWidth: Double = 600
    @AppStorage("windowHeight_v2") private var windowHeight: Double = 500
    @State private var dragStartSize: CGSize?

    private var clampedSize: CGSize {
        PopoverSize.clamp(CGSize(width: windowWidth, height: windowHeight))
    }

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            TabView(selection: $selectedTab) {
                ReadView()
                    .tabItem {
                        Label("Read", systemImage: "book")
                    }
                    .tag(0)
                
                FindView()
                    .tabItem {
                        Label("Find", systemImage: "character.book.closed")
                    }
                    .tag(1)
            }
            .frame(width: clampedSize.width, height: clampedSize.height)
            // .padding(.bottom, 20) // Only if needed for resize handle
            
            // Resize Handle
            Image(systemName: "arrow.down.forward")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.secondary.opacity(0.5))
                .frame(width: 20, height: 20)
                .contentShape(Rectangle())
                .padding(2) // Bottom right padding
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            if dragStartSize == nil {
                                dragStartSize = CGSize(width: windowWidth, height: windowHeight)
                            }
                            guard let start = dragStartSize else { return }
                            
                            let clamped = PopoverSize.clamp(CGSize(
                                width: start.width + value.translation.width,
                                height: start.height + value.translation.height
                            ))
                            windowWidth = clamped.width
                            windowHeight = clamped.height
                        }
                        .onEnded { _ in
                            dragStartSize = nil
                        }
                )
            
            // Restart Button (Top Right)
            VStack {
                HStack {
                    Spacer()
                    Button(action: restartApp) {
                        Image(systemName: "arrow.clockwise.circle.fill")
                            .font(.system(size: 20))
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                    .padding(8)
                    .help("Restart App & Server")
                }
                Spacer()
            }
        }
    }
    
    func restartApp() {
        let task = Process()
        task.launchPath = "/bin/bash"
        // We need to find biblecli. 
        // Assuming it's in the project bin logic or installed in path.
        // Let's try matching the behavior of the python script:
        // The app is likely running from derived data or .build
        // Getting the project root is tricky from sandbox/build.
        // But for this user env, `biblecli` command should be available if they sourced it?
        // Or we can try to find absolute path.
        // Let's assume `biblecli` is in the path or use a hardcoded path for this user context since we know it.
        // User's biblecli is at /Users/ronan/Documents/Gemini/antigravity/ScripturesApp/bin/biblecli
        
        let cliPath = "/Users/ronan/Documents/Gemini/antigravity/ScripturesApp/bin/biblecli"
        
        task.arguments = ["-c", "\(cliPath) restart --detach"]
        
        do {
            try task.run()
            // We don't need to exit explicitly, the restart command will kill us.
            // But to be sure we don't block the restart:
            // Actually `biblecli restart` kills the app process.
        } catch {
            print("Failed to restart: \(error)")
        }
    }
}
