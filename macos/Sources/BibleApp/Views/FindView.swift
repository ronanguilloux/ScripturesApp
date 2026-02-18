import SwiftUI

struct FindView: View {
    @State private var searchText = ""
    @State private var limitText = "20"
    @State private var findResponse: FindResponse?
    @State private var errorMessage: String?
    @State private var isLoading = false
    
    // Options
    @State private var selectedVersion = "NT" // Greek Corpus: NT, LXX, ALL
    @State private var selectedBible = "TOB" // French Version: TOB, BJ
    @State private var selectedTranslations: Set<String> = [] // EN, FR, GR, HB
    
    @FocusState private var isFocused: Bool
    
    let availableTranslations = ["EN", "FR", "GR", "HB"]
    
    var body: some View {
        VStack(spacing: 0) {
            // MARK: - Options & Search Bar (Compact)
            VStack(spacing: 8) {
                // Top Row: Options + Toggle
                HStack(spacing: 12) {
                    // Corpus Picker
                    Picker("", selection: $selectedVersion) {
                        Text("NT").tag("NT")
                        Text("LXX").tag("LXX")
                        Text("All").tag("ALL")
                    }
                    .pickerStyle(.menu)
                    .frame(width: 70)
                    .controlSize(.small)
                    
                    // Bible Version Picker
                    Picker("", selection: $selectedBible) {
                        Text("TOB").tag("TOB")
                        Text("BJ").tag("BJ")
                    }
                    .pickerStyle(.menu)
                    .frame(width: 70)
                    .controlSize(.small)
                    
                    // Translations Toggles
                    HStack(spacing: 2) {
                        ForEach(availableTranslations, id: \.self) { code in
                            Toggle(code, isOn: Binding(
                                get: { selectedTranslations.contains(code) },
                                set: { isOn in
                                    if isOn { selectedTranslations.insert(code) }
                                    else { selectedTranslations.remove(code) }
                                }
                            ))
                            .toggleStyle(.button)
                            .controlSize(.mini)
                        }
                    }
                    
                    Spacer()
                }
                
                // Bottom Row: Search Input + Limit
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.gray)
                    
                    TextField("Greek word (e.g. ἀγαπάω) or French expression", text: $searchText)
                        .textFieldStyle(.plain)
                        .font(.body)
                        .focused($isFocused)
                        .onSubmit {
                            performFind()
                        }
                        .frame(maxWidth: .infinity)
                    
                    // Limit field
                    HStack(spacing: 4) {
                        Text("Limit:")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        TextField("20", text: $limitText)
                            .textFieldStyle(.roundedBorder)
                            .font(.caption)
                            .frame(width: 40)
                            .controlSize(.small)
                            .onSubmit {
                                performFind()
                            }
                    }
                    
                    if isLoading {
                        ProgressView()
                            .controlSize(.mini)
                    }
                }
                .padding(6)
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(6)
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                )
            }
            .padding(10)
            .background(Color(NSColor.windowBackgroundColor)) // Slightly different bg for header area?
            
            Divider()
            
            // MARK: - Results
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
                                
                                // Main Text (Greek or French) with highlighting
                                HighlightedText(text: result.text, highlights: result.highlights)
                                    .font(.body)
                                    .textSelection(.enabled)
                                
                                // Translations
                                if !result.translations.isEmpty {
                                    VStack(alignment: .leading, spacing: 2) {
                                        ForEach(result.translations.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                                            HStack(alignment: .top) {
                                                Text(key)
                                                    .font(.caption)
                                                    .bold()
                                                    .foregroundColor(.secondary)
                                                    .frame(width: 30, alignment: .leading)
                                                
                                                Text(value)
                                                    .font(.body)
                                                    .foregroundColor(.secondary)
                                            }
                                        }
                                    }
                                    .padding(.leading, 8)
                                }
                                
                                Divider()
                                    .background(Color.gray.opacity(0.3))
                            }
                        }
                        
                        // Footer
                        if response.total > response.results.count {
                            Text("... and \(response.total - response.results.count) more.")
                                .font(.body)
                                .foregroundColor(.secondary)
                                .padding(.vertical, 4)
                        }
                        
                        // Summary
                        VStack(alignment: .leading, spacing: 4) {
                            Divider()
                                .background(Color.gray)
                                .padding(.vertical, 8)
                            
                            // Lemma info
                            HStack {
                                Text("Lemma: \(response.lemma)")
                                    .font(.headline)
                                    .foregroundColor(.cyan)
                                
                                if !response.lemmaGloss.isEmpty {
                                    Text("(\(response.lemmaGloss))")
                                        .font(.headline)
                                        .foregroundColor(.secondary)
                                }
                            }
                            
                            if response.original != response.lemma {
                                Text("Original: \(response.original)")
                                    .font(.caption)
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
                        Text("Find occurrences of a word or expression")
                            .foregroundColor(.secondary)
                        Text("Auto-detects Greek or French mode")
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
        
        let query = searchText
        let limit = Int(limitText) ?? 20
        
        // Build URL
        var components = URLComponents(string: "http://127.0.0.1:8000/api/v1/find")!
        var queryItems = [
            URLQueryItem(name: "q", value: query),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "v", value: selectedVersion.lowercased()),
            URLQueryItem(name: "bible", value: selectedBible.lowercased())
        ]
        
        // Add translations (multiple 'tr' params)
        for tr in selectedTranslations {
            queryItems.append(URLQueryItem(name: "tr", value: tr.lowercased()))
        }
        
        components.queryItems = queryItems
        
        guard let url = components.url else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
                
                if let error = error {
                    errorMessage = "Error: \(error.localizedDescription)"
                    return
                }
                
                guard let data = data else { return }
                
                // Debug: Print raw response if needed
                // print(String(data: data, encoding: .utf8) ?? "nil")
                
                do {
                    let result = try JSONDecoder().decode(FindResponse.self, from: data)
                    self.findResponse = result
                    if result.total == 0 {
                        self.errorMessage = "No occurrences found for '\(query)'."
                    }
                } catch {
                    errorMessage = "Parsing error: \(error.localizedDescription)"
                    print("Raw data: \(String(data: data, encoding: .utf8) ?? "Bad data")")
                }
            }
        }.resume()
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
