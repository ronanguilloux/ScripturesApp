import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @AppStorage("windowWidth_v2") private var windowWidth: Double = 600
    @AppStorage("windowHeight_v2") private var windowHeight: Double = 500
    @State private var dragStartSize: CGSize?

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
            .frame(width: windowWidth, height: windowHeight)
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
                            
                            windowWidth = max(320, start.width + value.translation.width)
                            windowHeight = max(300, start.height + value.translation.height)
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
