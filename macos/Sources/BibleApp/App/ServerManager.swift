import Foundation

class ServerManager: ObservableObject {
    static let shared = ServerManager()
    
    // Keys for UserDefaults
    // Keys for Settings
    private let kServerPath = "ScripturesApp_ServerPath"
    
    // Dynamic determination of project root
    private var defaultPath: String {
        let current = FileManager.default.currentDirectoryPath
        // If running from 'macos' subdir (e.g. swift run)
        if current.hasSuffix("/macos") {
            let parent = URL(fileURLWithPath: current).deletingLastPathComponent().path
            return parent
        }
        return current
    }
    
    var serverPath: String {
        get {
            // Priority:
            // 1. User setting (if valid)
            // 2. Dynamic default
            if let saved = UserDefaults.standard.string(forKey: kServerPath), !saved.isEmpty {
                 var isDir: ObjCBool = false
                 if FileManager.default.fileExists(atPath: saved, isDirectory: &isDir) && isDir.boolValue {
                     return saved
                 } else {
                     UserDefaults.standard.removeObject(forKey: kServerPath)
                 }
            }
            return defaultPath
        }
        set {
            UserDefaults.standard.set(newValue, forKey: kServerPath)
        }
    }

    private var serverProcess: Process?
    
    // Check if server is managed externally (e.g. by biblecli start)
    private var isManaged: Bool {
        return ProcessInfo.processInfo.environment["BIBLE_APP_SERVER_MANAGED"] == "true"
    }
    
    func startServer() {
        if isManaged {
            print("Server is managed externally. Skipping start.")
            return
        }
        
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
        
        // Command to start uvicorn (using module path without --app-dir)
        let command = ".venv/bin/uvicorn src.api.main:app --port 8000"
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
        if isManaged {
            print("Server is managed externally. Skipping stop.")
            return
        }
        serverProcess?.terminate()
        serverProcess = nil
    }
    
    func killExistingServer() {
        if isManaged {
            print("Server is managed externally. Skipping kill.")
            return
        }
        // Kill uvicorn process by name (development only)
        let task = Process()
        task.launchPath = "/usr/bin/pkill"
        task.arguments = ["-f", "uvicorn"]
        try? task.run()
        task.waitUntilExit()
    }
    
    func restartServer() {
        if isManaged {
            print("Server is managed externally. Skipping restart.")
            return
        }
        print("Restarting server...")
        stopServer() // Stop managed
        killExistingServer() // Stop any legacy/zombie
        // Short delay to ensure port release?
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.startServer()
        }
    }
}
