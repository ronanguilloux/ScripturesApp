import Foundation

class ServerManager: ObservableObject {
    static let shared = ServerManager()
    
    // Keys for UserDefaults
    private let kServerPath = "BibleCLI_ServerPath"
    
    // Default fallback path (optional, or empty)
    private let defaultPath = "/Users/ronan/Documents/Gemini/antigravity/biblecli"
    
    var serverPath: String {
        get {
            UserDefaults.standard.string(forKey: kServerPath) ?? defaultPath
        }
        set {
            UserDefaults.standard.set(newValue, forKey: kServerPath)
        }
    }

    private var serverProcess: Process?
    
    func startServer() {
        guard serverProcess == nil else {
            print("Server already running (managed)")
            return
        }
        
        let path = serverPath
        var isDir: ObjCBool = false
        if !FileManager.default.fileExists(atPath: path, isDirectory: &isDir) || !isDir.boolValue {
            print("Invalid server path: \(path)")
            return
        }
        
        let task = Process()
        task.currentDirectoryPath = path
        task.executableURL = URL(fileURLWithPath: "/bin/zsh")
        
        // Command to start uvicorn
        // We use -c to run the full command string
        // Check if .venv exists, otherwise might need another way or assume standard layout
        let command = ".venv/bin/uvicorn api.main:app --app-dir src --port 8000"
        task.arguments = ["-c", command]
        
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe
        
        let outHandle = pipe.fileHandleForReading
        outHandle.readabilityHandler = { pipe in
            if let line = String(data: pipe.availableData, encoding: .utf8) {
                if !line.isEmpty {
                    print("[Server Log] \(line)")
                }
            }
        }
        
        do {
            try task.run()
            self.serverProcess = task
            print("Server started manually from: \(path)")
        } catch {
            print("Failed to start server: \(error)")
        }
    }
    
    func stopServer() {
        serverProcess?.terminate()
        serverProcess = nil
    }
    
    func killExistingServer() {
        // Kill uvicorn process by name (development only)
        let task = Process()
        task.launchPath = "/usr/bin/pkill"
        task.arguments = ["-f", "uvicorn"]
        try? task.run()
        task.waitUntilExit()
    }
    
    func restartServer() {
        print("Restarting server...")
        stopServer() // Stop managed
        killExistingServer() // Stop any legacy/zombie
        // Short delay to ensure port release?
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.startServer()
        }
    }
}
