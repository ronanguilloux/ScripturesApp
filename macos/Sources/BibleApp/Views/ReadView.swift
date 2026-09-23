import SwiftUI

// Display Modes matching CLI -k/-K
enum DisplayMode: String, CaseIterable, Identifiable {
    case classic = "Classic"
    case compact = "Compact"
    case textOnly = "Text Only"
    var id: String { self.rawValue }
}

struct ReadView: View {

    @State private var searchText = "Mc 7:8"
    @State private var verseResponse: VerseResponse?
    @State private var errorMessage: String?
    @State private var isLoading = false
    
    // Options State
    @State private var selectedLanguages: Set<String> = ["fr", "gr"] // Defaults
    @State private var frenchVersion: String = "tob" // Default to TOB
    @State private var showCrossRefs = false
    @State private var showFullCrossRefs = false
    @State private var crossRefSource: String = "tob"
    @State private var displayMode: DisplayMode = .classic
    @State private var showSettings = false // For Settings Sheet

    /// Target verse texts fetched on hover, keyed by target_ref.
    @State private var previewCache: [String: String] = [:]

    /// Browser-style stack: one entry per reference the reader asked for.
    /// Option changes (language, cross-ref source) re-run performSearch() on the same
    /// reference, so nothing is pushed there -- only at the two points that carry an
    /// intent to move: submitting the field, and clicking a reference.
    @State private var history: [String] = []
    @State private var historyIndex = -1

    /// ContentView owns and persists the popover width; the gutter only needs to read it.
    @AppStorage("windowWidth_v2") private var windowWidth: Double = 600

    /// A BJ margin is a narrow outer column. Below this the text would be strangled,
    /// so the references fall back to a line above the verse.
    private var showGutter: Bool { windowWidth >= 460 }
    private let gutterWidth: CGFloat = 78

    @FocusState private var isFocused: Bool
    
    var body: some View {
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
                    
                    // Display Mode
                    Picker("", selection: $displayMode) {
                        ForEach(DisplayMode.allCases) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .controlSize(.mini)
                    .frame(width: 150)
                }
                .toggleStyle(.button)
                .controlSize(.mini)
                .onChange(of: selectedLanguages) { _ in performSearch() }
                
                HStack {
                    Spacer()
                    
                    // Cross Refs
                    Toggle(isOn: $showCrossRefs) {
                        Image(systemName: "link")
                    }
                    .toggleStyle(.button)
                    .controlSize(.mini)
                    .help("Renvois en marge (-c)")
                    .onChange(of: showCrossRefs) { _ in performSearch() }
                    
                    if showCrossRefs {
                        // TOB is curated at BJ density (1-3 per verse); openbible can
                        // carry 30+ on one verse and is capped server-side.
                        Picker("", selection: $crossRefSource) {
                            Text("TOB").tag("tob")
                            Text("OpenBible").tag("openbible")
                            Text("Toutes").tag("all")
                        }
                        .pickerStyle(.menu)
                        .controlSize(.mini)
                        .frame(width: 95)
                        .help("Source des renvois")
                        .onChange(of: crossRefSource) { _ in performSearch() }

                        Toggle(isOn: $showFullCrossRefs) {
                            Image(systemName: "text.alignleft")
                        }
                        .toggleStyle(.button)
                        .controlSize(.mini)
                        .help("Liste détaillée sous le passage (-f)")
                        .onChange(of: showFullCrossRefs) { _ in performSearch() }
                    }
                }
            }
            .padding(10)
            .background(Color(NSColor.controlBackgroundColor))
            
            Divider()

            // Search Bar
            HStack {
                Button { go(-1) } label: { Image(systemName: "chevron.left") }
                    .buttonStyle(.plain)
                    .disabled(!canGoBack)
                    .keyboardShortcut("[", modifiers: .command)
                    .help("Retour")
                Button { go(1) } label: { Image(systemName: "chevron.right") }
                    .buttonStyle(.plain)
                    .disabled(!canGoForward)
                    .keyboardShortcut("]", modifiers: .command)
                    .help("Suivant")

                Image(systemName: "book") // Different icon for Read
                    .foregroundColor(.gray)
                TextField("Reference (e.g. Mc 7:8)", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.title2)
                    .focused($isFocused)
                    .onSubmit {
                        pushHistory(searchText)
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
            // ScrollViewReader so a footnote call can jump to its note.
            ScrollViewReader { proxy in
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
                        
                        let letters = noteLetters(response)

                        ForEach(response.verses) { item in
                            // .firstTextBaseline sits the top reference on the baseline of
                            // the verse block's first line -- the BJ anchor, for free.
                            HStack(alignment: .firstTextBaseline, spacing: 10) {
                                if showCrossRefs && showGutter {
                                    marginGutter(for: item)
                                        .frame(width: gutterWidth, alignment: .trailing)
                                }

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

                                    if showCrossRefs && !showGutter {
                                        inlineRefs(for: item)
                                    }

                                    // Primary Text, with the footnote call at the end of the
                                    // verse: TOB notes carry a verse_ref, never a word offset,
                                    // so the BJ's mid-sentence placement is not reconstructible.
                                    Text(verseText(item, letter: letters[item.ref]))
                                        .font(.body)
                                        .textSelection(.enabled)

                                    // Parallels
                                    ForEach(item.parallels, id: \.version) { p in
                                        Text(p.text)
                                            .font(.body)
                                            .foregroundColor(.secondary)
                                            .textSelection(.enabled)
                                    }
                                }
                            }
                            .padding(.bottom, 8)
                        }

                        // Footnotes, lettered in the order the verses appear
                        if !letters.isEmpty {
                            Divider()
                            VStack(alignment: .leading, spacing: 6) {
                                ForEach(response.verses) { item in
                                    if let letter = letters[item.ref],
                                       let notes = item.crossReferences?.notes, !notes.isEmpty {
                                        HStack(alignment: .firstTextBaseline, spacing: 6) {
                                            Text(letter)
                                                .font(.caption2)
                                                .bold()
                                                .foregroundColor(.accentColor)
                                            Text(notes.joined(separator: " "))
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                                .textSelection(.enabled)
                                        }
                                        .id("note-\(letter)")
                                    }
                                }
                            }
                        }

                        Divider()
                        
                        // Cross References -- the detailed list is now the "full" mode only;
                        // plain -c puts the references in the margin instead.
                        if showFullCrossRefs, let refs = response.crossReferences, !refs.relations.isEmpty {
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
                            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                                performSearch()
                            }
                        }
                    }
                } else {
                    Text("Type a reference to read")
                        .foregroundColor(.secondary)
                        .padding(.top, 40)
                }
            }
            .environment(\.openURL, OpenURLAction { url in
                guard url.scheme == "scriptures", url.host == "note" else { return .systemAction }
                let letter = url.lastPathComponent
                withAnimation { proxy.scrollTo("note-\(letter)", anchor: .center) }
                return .handled
            })
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
        .onAppear {
            isFocused = true
        }
    }
    
    // MARK: - BJ-style margin

    /// The outer column: one reference per line, right-aligned against the text,
    /// stacked in the order the server sorted them.
    @ViewBuilder
    private func marginGutter(for item: VerseItem) -> some View {
        VStack(alignment: .trailing, spacing: 1) {
            ForEach(item.crossReferences?.relations ?? []) { rel in
                refLabel(rel)
            }
        }
    }

    /// Narrow-window fallback: the same references, laid out above the verse.
    @ViewBuilder
    private func inlineRefs(for item: VerseItem) -> some View {
        let rels = item.crossReferences?.relations ?? []
        if !rels.isEmpty {
            HStack(spacing: 8) {
                ForEach(rels) { rel in
                    refLabel(rel)
                }
                Spacer(minLength: 0)
            }
        }
    }

    private func refLabel(_ rel: CrossReferenceRelation) -> some View {
        Text(rel.marginLabel)
            .font(.caption2)
            .foregroundColor(.secondary)
            .lineLimit(1)
            .help(previewText(for: rel))
            .onHover { inside in
                if inside { fetchPreview(rel) }
            }
            .onTapGesture { navigate(to: rel) }
    }

    /// Clicking a reference reads it. The margin label may be elided ("2:33"),
    /// which the parser cannot resolve -- navigate with the full localized form.
    private func navigate(to rel: CrossReferenceRelation) {
        searchText = rel.targetRefLocalized ?? rel.targetRef
        pushHistory(searchText)
        performSearch()
    }

    // MARK: - History

    private var canGoBack: Bool { historyIndex > 0 }
    private var canGoForward: Bool { historyIndex >= 0 && historyIndex < history.count - 1 }

    private func pushHistory(_ ref: String) {
        guard historyIndex < 0 || history[historyIndex] != ref else { return }
        // Branching off mid-stack drops what was ahead, as a browser does.
        if historyIndex < history.count - 1 {
            history.removeSubrange((historyIndex + 1)...)
        }
        history.append(ref)
        historyIndex = history.count - 1
    }

    /// Replays an entry without recording it -- otherwise going back would
    /// itself become a step forward.
    private func go(_ delta: Int) {
        let i = historyIndex + delta
        guard history.indices.contains(i) else { return }
        historyIndex = i
        searchText = history[i]
        performSearch()
    }

    private func previewText(for rel: CrossReferenceRelation) -> String {
        if let cached = previewCache[rel.targetRef] { return cached }
        if let t = rel.text, !t.isEmpty { return t }
        return rel.targetRefLocalized ?? rel.targetRef
    }

    /// Hovering a reference fetches the target verse once, through the same
    /// endpoint the view already uses. No preloading: a chapter can carry
    /// dozens of references nobody will ever point at.
    private func fetchPreview(_ rel: CrossReferenceRelation) {
        let key = rel.targetRef
        guard previewCache[key] == nil else { return }
        previewCache[key] = (rel.targetRefLocalized ?? key) + "…"

        var comp = URLComponents(string: "http://127.0.0.1:8000/api/v1/search")!
        comp.queryItems = [
            URLQueryItem(name: "q", value: rel.targetRefLocalized ?? key),
            URLQueryItem(name: "tr", value: "fr"),
            URLQueryItem(name: "bible", value: frenchVersion)
        ]
        guard let url = comp.url else { return }

        URLSession.shared.dataTask(with: url) { data, _, _ in
            guard let data = data,
                  let decoded = try? JSONDecoder().decode(VerseResponse.self, from: data)
            else { return }
            let body = decoded.verses.map { $0.primary.text }.joined(separator: " ")
            let label = rel.targetRefLocalized ?? key
            DispatchQueue.main.async {
                previewCache[key] = body.isEmpty ? label : "\(label) — \(body)"
            }
        }.resume()
    }

    /// One letter per annotated verse, in reading order, as the BJ letters its
    /// footnotes down the page.
    private func noteLetters(_ response: VerseResponse) -> [String: String] {
        let alphabet = Array("abcdefghijklmnopqrstuvwxyz")
        var out: [String: String] = [:]
        var index = 0
        for item in response.verses {
            guard let notes = item.crossReferences?.notes, !notes.isEmpty else { continue }
            out[item.ref] = String(alphabet[index % alphabet.count])
            index += 1
        }
        return out
    }

    private func verseText(_ item: VerseItem, letter: String?) -> AttributedString {
        var full = AttributedString(item.primary.text)
        guard let letter = letter else { return full }

        var mark = AttributedString(letter)
        mark.font = .caption2
        mark.baselineOffset = 5
        mark.foregroundColor = .accentColor
        mark.link = URL(string: "scriptures://note/\(letter)")

        full += AttributedString(" ")
        full += mark
        return full
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
    
    // API Fetch Logic
    func performSearch() {
        guard !searchText.isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        verseResponse = nil
        previewCache.removeAll()
        
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
        if showCrossRefs && crossRefSource != "all" {
            queryItems.append(URLQueryItem(name: "crossref_source", value: crossRefSource))
        }
        
        urlComp.queryItems = queryItems
        
        guard let url = urlComp.url else { return }
        
        URLSession.shared.dataTask(with: url) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
                
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
        output += "\(response.reference)\n"
        for item in response.verses {
            output += "v\(item.primary.verse). \(item.primary.text)\n"
            for p in item.parallels {
                output += "\(p.text)\n"
            }
        }
        copyToClipboard(output)
    }
    
    private func copyCrossRefs(_ refs: VerseCrossReferences) {
        var output = "Cross References:\n"
        for rel in refs.relations {
            let refName = rel.targetRefLocalized ?? rel.targetRef
            output += "\(refName)\n"
            if let text = rel.text {
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
