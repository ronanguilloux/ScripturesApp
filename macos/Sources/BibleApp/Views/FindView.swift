import SwiftUI

struct FindView: View {
    @State private var searchText = ""
    @State private var limitText = "20"
    @State private var findResponse: FindResponse?
    @State private var errorMessage: String?
    @State private var isLoading = false
    
    @FocusState private var isFocused: Bool
    
    var body: some View {
        VStack(spacing: 0) {
            // Input Bar
            HStack(spacing: 12) {
                // Greek word field
                HStack {
                    Image(systemName: "character.book.closed")
                        .foregroundColor(.gray)
                    TextField("Greek word (e.g. ἀγαπάω)", text: $searchText)
                        .textFieldStyle(.plain)
                        .font(.title2)
                        .focused($isFocused)
                        .onSubmit {
                            performFind()
                        }
                }
                .frame(maxWidth: .infinity)
                
                // Limit field
                HStack {
                    Text("Limit:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    TextField("20", text: $limitText)
                        .textFieldStyle(.roundedBorder)
                        .font(.body)
                        .frame(width: 60)
                        .onSubmit {
                            performFind()
                        }
                }
                
                if isLoading {
                    ProgressView()
                        .scaleEffect(0.5)
                }
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            
            Divider()
            
            // Results
            ScrollView {
                if let response = findResponse {
                    VStack(alignment: .leading, spacing: 12) {
                        // Results list
                        ForEach(response.results) { result in
                            VStack(alignment: .leading, spacing: 4) {
                                // Reference
                                Text(result.ref)
                                    .font(.headline)
                                    .foregroundColor(.green)
                                
                                // Greek text with highlighting
                                HighlightedText(text: result.greek, highlights: result.highlights)
                                    .font(.body)
                                    .textSelection(.enabled)
                                
                                // French translation
                                if !result.french.isEmpty {
                                    Text("(TOB) \(result.french)")
                                        .font(.body)
                                        .foregroundColor(.cyan)
                                        .textSelection(.enabled)
                                }
                                
                                Divider()
                                    .background(Color.gray.opacity(0.3))
                            }
                        }
                        
                        // "... and X more" message
                        if response.total > response.results.count {
                            Text("... and \(response.total - response.results.count) more.")
                                .font(.body)
                                .foregroundColor(.secondary)
                                .padding(.vertical, 4)
                        }
                        
                        // Summary footer
                        VStack(alignment: .leading, spacing: 4) {
                            Divider()
                                .background(Color.gray)
                                .padding(.vertical, 8)
                            
                            // Lemma transformation
                            if response.original != response.lemma {
                                if !response.lemmaGloss.isEmpty {
                                    Text("Lemma: \(response.original) → \(response.lemma) (\(response.lemmaGloss))")
                                        .font(.headline)
                                        .foregroundColor(.cyan)
                                } else {
                                    Text("Lemma: \(response.original) → \(response.lemma)")
                                        .font(.headline)
                                        .foregroundColor(.cyan)
                                }
                            } else {
                                if !response.lemmaGloss.isEmpty {
                                    Text("Lemma: \(response.lemma) (\(response.lemmaGloss))")
                                        .font(.headline)
                                        .foregroundColor(.cyan)
                                } else {
                                    Text("Lemma: \(response.lemma)")
                                        .font(.headline)
                                        .foregroundColor(.cyan)
                                }
                            }
                            
                            Text("Total occurrences: \(response.total)")
                                .font(.headline)
                                .foregroundColor(.green)
                        }
                        .padding(.top, 8)
                    }
                    .padding()
                } else if let error = errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .padding()
                } else {
                    VStack {
                        Image(systemName: "character.book.closed")
                            .font(.largeTitle)
                            .foregroundColor(.secondary.opacity(0.5))
                        Text("Find all occurrences of a Greek word")
                            .foregroundColor(.secondary)
                        Text("Supports lemmatization with OdyCy")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.top, 60)
                }
            }
        }
        .onAppear {
            isFocused = true
        }
    }
    
    func performFind() {
        guard !searchText.isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        findResponse = nil
        
        let word = searchText
        let limit = Int(limitText) ?? 20
        
        // Get project root from ServerManager
        let projectRoot = ServerManager.shared.serverPath
        let venvPython = "\(projectRoot)/.venv-spacy/bin/python3"
        let workerScript = "\(projectRoot)/src/application/workers/find_worker.py"
        
        DispatchQueue.global(qos: .userInitiated).async {
            let task = Process()
            task.executableURL = URL(fileURLWithPath: venvPython)
            task.arguments = [workerScript, word, "--limit", "\(limit)"]
            task.currentDirectoryPath = projectRoot
            
            let pipe = Pipe()
            task.standardOutput = pipe
            task.standardError = pipe
            
            do {
                try task.run()
                task.waitUntilExit()
                
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                
                DispatchQueue.main.async {
                    isLoading = false
                    
                    if task.terminationStatus != 0 {
                        let errorText = String(data: data, encoding: .utf8) ?? "Unknown error"
                        errorMessage = "Worker failed: \(errorText)"
                        return
                    }
                    
                    do {
                        let result = try JSONDecoder().decode(FindResponse.self, from: data)
                        self.findResponse = result
                        if result.total == 0 {
                            self.errorMessage = "No occurrences found for '\(word)'."
                        }
                    } catch {
                        errorMessage = "Parsing error: \(error.localizedDescription)"
                        print("Raw data: \(String(data: data, encoding: .utf8) ?? "Bad data")")
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    isLoading = false
                    errorMessage = "Failed to run worker: \(error.localizedDescription)"
                }
            }
        }
    }
}

// Helper view for highlighting Greek text
struct HighlightedText: View {
    let text: String
    let highlights: [String]
    
    var body: some View {
        // Simple approach: split by highlights and colorize
        // For better highlighting, we could use AttributedString
        if highlights.isEmpty {
            Text(text)
        } else {
            // Create attributed string with highlights
            Text(attributedText())
        }
    }
    
    private func attributedText() -> AttributedString {
        var attrString = AttributedString(text)
        
        for highlight in highlights {
            // Find all ranges of this highlight
            var searchRange = attrString.startIndex..<attrString.endIndex
            
            while let range = attrString[searchRange].range(of: highlight) {
                attrString[range].foregroundColor = .red
                attrString[range].font = .body.bold()
                
                // Continue searching after this range
                if range.upperBound < attrString.endIndex {
                    searchRange = range.upperBound..<attrString.endIndex
                } else {
                    break
                }
            }
        }
        
        return attrString
    }
}
