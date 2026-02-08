import SwiftUI

// Display Modes matching CLI -k/-K
enum DisplayMode: String, CaseIterable, Identifiable {
    case classic = "Classic"
    case compact = "Compact"
    case textOnly = "Text Only"
    var id: String { self.rawValue }
}

struct ContentView: View {
    @State private var searchText = "Mc 7:8"
    @State private var verseResponse: VerseResponse?
    @State private var errorMessage: String?
    @State private var isLoading = false
    
    // Options State
    @State private var selectedLanguages: Set<String> = ["fr", "gr"] // Defaults
    @State private var frenchVersion: String = "tob" // Default to TOB
    @State private var showCrossRefs = false
    @State private var showFullCrossRefs = false
    @State private var displayMode: DisplayMode = .classic
    @State private var showSettings = false // For Settings Sheet

    
    @AppStorage("windowWidth") private var windowWidth: Double = 400
    @AppStorage("windowHeight") private var windowHeight: Double = 600
    @State private var dragStartSize: CGSize?

    // Focus management
    @FocusState private var isFocused: Bool
    
    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            VStack(spacing: 0) {
                // MARK: - Options Bar
                VStack(alignment: .leading, spacing: 10) {
                    // Languages
                    HStack {
                        Text("Lang:")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        HStack(spacing: 2) {
                            Toggle("FR", isOn: binding(for: "fr"))
                            // French Version Selector (Only if FR matches)
                            if selectedLanguages.contains("fr") {
                                Picker("", selection: $frenchVersion) {
                                    Text("TOB").tag("tob")
                                    Text("BJ").tag("bj")
                                }
                                .pickerStyle(.menu)
                                .controlSize(.mini)
                                .frame(width: 60)
                                .onChange(of: frenchVersion) { _ in performSearch() }
                            }
                        }
                        Toggle("GR", isOn: binding(for: "gr"))
                        Toggle("EN", isOn: binding(for: "en"))
                        Toggle("AR", isOn: binding(for: "ar"))
                        Toggle("HB", isOn: binding(for: "hb"))
                        
                        Spacer()
                        
                        Button(action: {
                            ServerManager.shared.stopServer()
                            NSApplication.shared.terminate(nil)
                        }) {
                            Image(systemName: "power")
                        }
                        .help("Quit")
                        .keyboardShortcut("q")
                        .controlSize(.small)
                        // .buttonStyle(.borderless)
                    }
                    .toggleStyle(.button)
                    .controlSize(.mini)
                    .onChange(of: selectedLanguages) { _ in performSearch() }
                    
                    HStack {
                        // Display Mode
                        Picker("", selection: $displayMode) {
                            ForEach(DisplayMode.allCases) { mode in
                                Text(mode.rawValue).tag(mode)
                            }
                        }
                        .pickerStyle(.segmented)
                        .controlSize(.mini)
                        .frame(width: 150)
                        
                        Spacer()
                        
                        // Cross Refs
                        Toggle(isOn: $showCrossRefs) {
                            Image(systemName: "link")
                        }
                        .toggleStyle(.button)
                        .controlSize(.mini)
                        .help("Show Cross-References (-c)")
                        .onChange(of: showCrossRefs) { _ in performSearch() }
                        
                        if showCrossRefs {
                            Toggle(isOn: $showFullCrossRefs) {
                                Image(systemName: "text.alignleft")
                            }
                            .toggleStyle(.button)
                            .controlSize(.mini)
                            .help("Show Full Text (-f)")
                            .onChange(of: showFullCrossRefs) { _ in performSearch() }
                        }
                    }
                }
                .padding(10)
                .background(Color(NSColor.controlBackgroundColor))
                
                Divider()

                // Search Bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.gray)
                    TextField("Search (e.g. Mc 7:8)", text: $searchText)
                        .textFieldStyle(.plain)
                        .font(.title2)
                        .focused($isFocused)
                        .onSubmit {
                            performSearch()
                        }
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.5)
                    }
                }
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                
                Divider()
                
                // Results OR Prompt
                ScrollView {
                    if let response = verseResponse {
                        VStack(alignment: .leading, spacing: 20) {
                            // Main Verses Header
                            HStack {
                                Text("Verses")
                                    .font(.headline)
                                    .foregroundColor(.secondary)
                                Spacer()
                                Button(action: {
                                    copyVerses(response)
                                }) {
                                    Image(systemName: "doc.on.doc")
                                    Text("Copy")
                                }
                                .controlSize(.small)
                            }
                            
                            ForEach(response.verses) { item in
                                VStack(alignment: .leading, spacing: 4) {
                                    // Header (Classic & Compact Only)
                                    if displayMode != .textOnly {
                                        if displayMode == .compact {
                                             // vX.
                                             Text("v\(item.primary.verse).")
                                                .font(.headline)
                                                .foregroundColor(.green)
                                        } else {
                                             // Classic: Book Chapter:Verse
                                             Text("\(item.primary.bookName ?? item.primary.book) \(item.primary.chapter):\(item.primary.verse)")
                                                .font(.headline)
                                                .foregroundColor(.green)
                                        }
                                    }
                                    
                                    // Primary Text
                                    Text(item.primary.text)
                                        .font(.body)
                                        .textSelection(.enabled)
                                    
                                    // Parallels (Not in text-only mode strictly? CLI says Text Only is "Text only". 
                                    // But usually means hiding header metadata. 
                                    // Let's show parallels but without their own headers if logical.)
                                    ForEach(item.parallels, id: \.version) { p in
                                        Text(p.text)
                                            .font(.body)
                                            .foregroundColor(.secondary)
                                            .textSelection(.enabled)
                                    }
                                }
                                .padding(.bottom, 8)
                            }
                            
                            Divider()
                            
                            // Cross References
                            if let refs = response.crossReferences, !refs.relations.isEmpty {
                                HStack {
                                    Text("Cross References")
                                        .font(.subheadline)
                                        .bold()
                                        .foregroundColor(.secondary)
                                    Spacer()
                                    Button(action: {
                                        copyCrossRefs(refs)
                                    }) {
                                        Image(systemName: "doc.on.doc")
                                        Text("Copy")
                                    }
                                    .controlSize(.small)
                                }
                                
                                ForEach(refs.relations) { rel in
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack {
                                            // Indentation style from CLI
                                            Text("    \(rel.targetRefLocalized ?? rel.targetRef)")
                                                .font(.caption)
                                                .bold()
                                            Spacer()
                                        }
                                        if let text = rel.text {
                                            Text(text)
                                                .font(.caption)
                                                .foregroundColor(.gray)
                                                .padding(.leading, 20) // Indent text
                                                .lineLimit(nil)
                                        }
                                    }
                                    .padding(.vertical, 2)
                                }
                            }
                        }
                        .padding()
                    } else if let error = errorMessage {
                        VStack(spacing: 8) {
                            Text(error)
                                .foregroundColor(.red)
                                .multilineTextAlignment(.center)
                                .padding()
                            
                            Button("Start Server") {
                                ServerManager.shared.startServer()
                                // Retry after delay?
                                DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                                    performSearch()
                                }
                            }
                        }
                    } else {
                        Text("Type a reference to search")
                            .foregroundColor(.secondary)
                            .padding(.top, 40)
                    }
                }
                
                Divider()
                
                // Footer
                HStack {
                    Button(action: {
                        showSettings = true
                    }) {
                        Image(systemName: "gearshape")
                    }
                    .controlSize(.small)
                    .help("Settings")
                    .sheet(isPresented: $showSettings) {
                        SettingsView()
                    }
                    
                    Spacer()
                }
                .padding(8)
                .background(Color(NSColor.controlBackgroundColor))
            }
            .frame(width: windowWidth, height: windowHeight)
            
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
        }
        .onAppear {
            isFocused = true
        }
    }
    
    // Helper for Set binding
    private func binding(for lang: String) -> Binding<Bool> {
        Binding(
            get: { selectedLanguages.contains(lang) },
            set: { isOn in
                if isOn { selectedLanguages.insert(lang) }
                else { selectedLanguages.remove(lang) }
            }
        )
    }
    
    // API Fetch Logic (Inline for simplicity or move to ViewModel)
    func performSearch() {
        guard !searchText.isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        verseResponse = nil
        
        // let query = searchText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        // URLQueryItem handles encoding automatically
        let query = searchText
        
        // Build URL
        var urlComp = URLComponents(string: "http://127.0.0.1:8000/api/v1/search")!
        var queryItems = [URLQueryItem(name: "q", value: query)]
        
        // Add Translations
        for lang in selectedLanguages {
            queryItems.append(URLQueryItem(name: "tr", value: lang))
        }
        
        // Add French Version
        if selectedLanguages.contains("fr") {
             queryItems.append(URLQueryItem(name: "bible", value: frenchVersion))
        }
        
        // Add Cross Refs
        if showCrossRefs {
            queryItems.append(URLQueryItem(name: "crossref", value: "true"))
        }
        if showFullCrossRefs {
            queryItems.append(URLQueryItem(name: "crossref_full", value: "true"))
        }
        
        urlComp.queryItems = queryItems
        
        guard let url = urlComp.url else { return }
        print("DEBUG REQUEST: \(url.absoluteString)")
        
        URLSession.shared.dataTask(with: url) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
         
                // ... (Keep existing response handling)
                
                if let error = error {
                    errorMessage = "Network error: \(error.localizedDescription)\nMake sure server is running."
                    return
                }
                
                guard let data = data else { return }
                
                do {
                    let decoded = try JSONDecoder().decode(VerseResponse.self, from: data)
                    self.verseResponse = decoded
                } catch {
                    errorMessage = "Parsing Error: \(error.localizedDescription)"
                    print(String(data: data, encoding: .utf8) ?? "Bad Data")
                }
            }
        }.resume()
    }
    
    // MARK: - Clipboard Helpers
    private func copyVerses(_ response: VerseResponse) {
        var output = ""
        
        // Header: Reference (Match CLI "Mc 7:8-9")
        output += "\(response.reference)\n"
        
        for item in response.verses {
            // Verse Number + Primary Text
            // CLI Format: "v8. <Text>"
            output += "v\(item.primary.verse). \(item.primary.text)\n"
            
            // Parallels
            // CLI Format: Indented text? Or just text?
            // User example: "Vous laissez..." (No indent shown in example, but purely new line)
            // And NO [Version] prefix.
            for p in item.parallels {
                output += "\(p.text)\n"
            }
        }
        
        copyToClipboard(output)
    }
    
    private func copyCrossRefs(_ refs: VerseCrossReferences) {
        var output = "Cross References:\n"
        for rel in refs.relations {
            // Use localized reference (e.g. "Marc 7:3")
            // Fallback to targetRef if localized not available
            let refName = rel.targetRefLocalized ?? rel.targetRef
            output += "\(refName)\n"
            
            if let text = rel.text {
                // Indent text by 2 spaces
                // If text is multi-line (e.g. multiple versions), we might need to indent lines?
                // For now, assume simple text block.
                output += "  \(text)\n"
            }
        }
        copyToClipboard(output)
    }
    
    private func copyToClipboard(_ text: String) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
    }
}
