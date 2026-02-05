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
    let relations: [CrossReferenceRelation]
}

// MARK: - CrossReferenceRelation
struct CrossReferenceRelation: Codable, Identifiable {
    var id: String { targetRef }
    let targetRef: String
    let targetRefLocalized: String?
    let relType: String
    let note: String?
    let text: String?
    
    enum CodingKeys: String, CodingKey {
        case targetRef = "target_ref"
        case targetRefLocalized = "target_ref_localized"
        case relType = "rel_type"
        case note
        case text
    }
}
