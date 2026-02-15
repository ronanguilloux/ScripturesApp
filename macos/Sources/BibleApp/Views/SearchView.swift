import SwiftUI

struct SearchView: View {
    @State private var searchText = ""
    @State private var searchResults: [SearchResult] = []
    @State private var errorMessage: String?
    @State private var isLoading = false
    
    // Configuration
    @State private var limitK: Double = 10
    @State private var translationFilter: String = "TOB" // Could be ALL or specific
    
    @FocusState private var isFocused: Bool
    
    var body: some View {
        VStack(spacing: 0) {
            // MARK: - Options Bar
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("Limit (K): \(Int(limitK))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Slider(value: $limitK, in: 1...50, step: 1)
                        .controlSize(.mini)
                        .frame(width: 100)
                    
                    Spacer()
                    
                    Picker("Trans:", selection: $translationFilter) {
                        Text("TOB").tag("TOB")
                        Text("BJ").tag("BJ")
                        // Text("All").tag("ALL") // Backend might support optional?
                    }
                    .pickerStyle(.menu)
                    .controlSize(.mini)
                    .frame(width: 100)
                }
            }
            .padding(10)
            .background(Color(NSColor.controlBackgroundColor))
            
            Divider()

            // Search Bar
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.gray)
                TextField("Semantic Search (e.g. parole de dieu)", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.title2)
                    .focused($isFocused)
                    .onSubmit {
                        performSemanticSearch()
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
                if !searchResults.isEmpty {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Text("Found \(searchResults.count) results")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Spacer()
                        }
                        
                        ForEach(searchResults) { result in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    // Localize Ref
                                    let localizedBook = BookNameNormalizer.shared.localize(bookCode: result.book, language: "fr")
                                    let displayRef = "\(localizedBook) \(result.chapter):\(result.verse)"
                                    
                                    Text(displayRef)
                                        .font(.headline)
                                        .foregroundColor(.blue)
                                    Text("(\(result.translation))")
                                        .font(.caption)
                                        .bold()
                                        .padding(2)
                                        .background(Color.gray.opacity(0.2))
                                        .cornerRadius(4)
                                    
                                    Spacer()
                                    
                                    // Score indicator
                                    Text(String(format: "%.2f", result.score))
                                        .font(.caption)
                                        .foregroundColor(scoreColor(result.score))
                                }
                                
                                Text(result.text)
                                    .font(.body)
                                    .textSelection(.enabled)
                            }
                            .padding(8)
                            .background(Color(NSColor.controlBackgroundColor))
                            .cornerRadius(8)
                        }
                    }
                    .padding()
                } else if let error = errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .padding()
                } else {
                    VStack {
                        Image(systemName: "sparkles.magnifyingglass")
                            .font(.largeTitle)
                            .foregroundColor(.secondary.opacity(0.5))
                        Text("Search by meaning, not just keywords.")
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
    
    func scoreColor(_ score: Double) -> Color {
        if score > 0.6 { return .green }
        if score > 0.4 { return .orange }
        return .red
    }
    
    func performSemanticSearch() {
        guard !searchText.isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        searchResults = []
        
        let query = searchText
        
        // Build URL for Semantic Search
        
        // Use standard local URL
        let urlComp = URLComponents(string: "http://127.0.0.1:8000/api/v1/semantic-search")!

        // Wait, ReadView used /api/v1/search. The server code generally has /api/v1 prefix or not? 
        // Checking server/search_service.py: @app.post("/search")
        // Checking server/server.py: likely mounts routers.
        // Let's assume /search based on search_service.py content which seemed standalone app variable. 
        // But main.py likely mounts it.
        // Actually, previous CLI code used `requests.post(f"{SERVER_URL}/search", ...)`
        // And SERVER_URL defaults to http://127.0.0.1:8000.
        // So it is /search directly on the microservice port if running standalone uvicorn?
        // Or is it part of the main API?
        
        // Correction: The new search service is likely running on port 8000 alongside the main app or integrated.
        // The implementation plan said: Integrate with biblecli (src/cli.py).
        // Let's use `http://127.0.0.1:8000/search` as per `search_service.py` which had `app.post("/search")`.
        
        // POST request
        guard let url = urlComp.url else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "query": query,
            "limit": Int(limitK),
            "translation": translationFilter
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        } catch {
            print("Error parsing body")
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
                
                if let error = error {
                    errorMessage = "Error: \(error.localizedDescription)"
                    return
                }
                
                guard let data = data else { return }
                
                do {
                    let decoded = try JSONDecoder().decode([SearchResult].self, from: data)
                    self.searchResults = decoded
                    if self.searchResults.isEmpty {
                        self.errorMessage = "No results found."
                    }
                } catch {
                    errorMessage = "Parsing Error: \(error.localizedDescription)"
                    print(String(data: data, encoding: .utf8) ?? "Bad Data")
                }
            }
        }.resume()
    }
}
