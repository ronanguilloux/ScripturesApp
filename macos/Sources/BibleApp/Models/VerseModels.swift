import Foundation

// MARK: - VerseResponse
struct VerseResponse: Codable {
    let reference: String
    let verses: [VerseItem]
    let crossReferences: VerseCrossReferences?
    
    enum CodingKeys: String, CodingKey {
        case reference
        case verses
        case crossReferences = "cross_references"
    }
}

// MARK: - VerseItem
struct VerseItem: Codable, Identifiable {
    var id: String { ref }
    let ref: String
    let primary: VerseContent
    let parallels: [VerseContent]
    /// Cross-references belonging to THIS verse, already capped for margin display.
    /// VerseResponse.crossReferences keeps the uncapped aggregate for the passage.
    let crossReferences: VerseCrossReferences?

    enum CodingKeys: String, CodingKey {
        case ref, primary, parallels
        case crossReferences = "cross_references"
    }
}

// MARK: - VerseContent
struct VerseContent: Codable {
    let book: String
    let chapter: Int
    let verse: Int
    let text: String
    let version: String
    let bookName: String?
    
    enum CodingKeys: String, CodingKey {
        case book = "book_code"
        case bookName = "book_name"
        case chapter
        case verse
        case text
        case version
    }
}

// MARK: - VerseCrossReferences
struct VerseCrossReferences: Codable {
    let notes: [String]
    let relations: [CrossReferenceRelation]

    // The API always sends both keys, but a decode failure here blanks the whole
    // passage, so treat either as optional rather than trust the contract.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        notes = try c.decodeIfPresent([String].self, forKey: .notes) ?? []
        relations = try c.decodeIfPresent([CrossReferenceRelation].self, forKey: .relations) ?? []
    }
}

// MARK: - CrossReferenceRelation
struct CrossReferenceRelation: Codable, Identifiable {
    // The server dedupes on (target, type, note), so targetRef alone collides and
    // makes ForEach drop rows. Key on the same triple it deduped with.
    var id: String { "\(targetRef)|\(relType)|\(note ?? "")" }
    let targetRef: String
    let targetRefLocalized: String?
    let relType: String
    let note: String?
    let text: String?
    /// Short BJ-style label: book dropped when it repeats the book being read or
    /// the reference above it, '+' kept when the reference carries a note.
    let targetRefMargin: String?

    /// What the margin column prints, falling back as the data thins out.
    var marginLabel: String { targetRefMargin ?? targetRefLocalized ?? targetRef }

    enum CodingKeys: String, CodingKey {
        case targetRef = "target_ref"
        case targetRefLocalized = "target_ref_localized"
        case relType = "rel_type"
        case note
        case text
        case targetRefMargin = "target_ref_margin"
    }
}

// MARK: - SearchResult
struct SearchResult: Codable, Identifiable {
    var id: String { ref + translation + String(score) } // Unique combo
    let ref: String
    let text: String
    let translation: String
    let score: Double
    let book: String
    let chapter: Int
    let verse: Int
}

// MARK: - FindResponse
struct FindResponse: Codable {
    let lemma: String
    let original: String
    let lemmaGloss: String
    let total: Int
    let results: [FindResultItem]
    
    enum CodingKeys: String, CodingKey {
        case lemma, original, total, results
        case lemmaGloss = "lemma_gloss"
    }
}

// MARK: - FindResultItem
// MARK: - FindResultItem
struct FindResultItem: Codable, Identifiable {
    var id: String { ref }
    let ref: String
    let book_code: String
    let chapter: Int
    let verse: Int
    let text: String
    let translations: [String: String]
    let highlights: [String]
}
