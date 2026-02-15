import Foundation

class BookNameNormalizer {
    static let shared = BookNameNormalizer()
    
    private var data: BookData?
    
    struct BookData: Codable {
        let books: [String: BookDetails]
    }
    
    struct BookDetails: Codable {
        let fr: FrenchDetails?
    }
    
    struct FrenchDetails: Codable {
        let abbreviations: [String]?
    }
    
    init() {
        loadData()
    }
    
    private func loadData() {
        // Correct way to load resource from Bundle.module
        guard let url = Bundle.module.url(forResource: "bible_books", withExtension: "json") else {
            print("Error: bible_books.json not found in bundle.")
            return
        }
        
        do {
            let jsonData = try Data(contentsOf: url)
            self.data = try JSONDecoder().decode(BookData.self, from: jsonData)
        } catch {
            print("Error decoding bible_books.json: \(error)")
        }
    }
    
    func localize(bookCode: String, language: String = "fr") -> String {
        guard let data = data,
              let details = data.books[bookCode] else {
            return bookCode // Fallback to code
        }
        
        if language == "fr" {
            // Prefer first abbreviation (e.g. "Gn", "Ex", "Lc")
            if let fr = details.fr, let abbrs = fr.abbreviations, !abbrs.isEmpty {
                return abbrs[0]
            }
        }
        
        return bookCode
    }
}

