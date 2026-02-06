import SwiftUI

struct SettingsView: View {
    @AppStorage("BibleCLI_ServerPath") private var serverPath: String = "/Users/ronan/Documents/Gemini/antigravity/biblecli"
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Settings")
                .font(.headline)
            
            VStack(alignment: .leading) {
                Text("BibleCLI Project Path:")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                HStack {
                    TextField("Path", text: $serverPath)
                        .textFieldStyle(.roundedBorder)
                    
                    Button("Browse") {
                        let panel = NSOpenPanel()
                        panel.allowsMultipleSelection = false
                        panel.canChooseDirectories = true
                        panel.canChooseFiles = false
                        panel.prompt = "Select"
                        
                        if panel.runModal() == .OK {
                            if let url = panel.url {
                                serverPath = url.path
                            }
                        }
                    }
                }
                
                Text("This path is used to start the Python server (uvicorn).")
                    .font(.caption2)
                    .foregroundColor(.gray)
            }
            .padding()
            
            Divider()
            
            HStack {
                Spacer()
                Button("Done") {
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding()
        .frame(width: 450)
    }
}
