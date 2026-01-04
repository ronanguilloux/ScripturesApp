class CLIHelp:
    def __init__(self):
        pass

    def print_usage(self):
        help_text = """
BIBLECLI(1)                      Bible CLI Manual                      BIBLECLI(1)

NAME
       biblecli - Command-line interface for the Greek New Testament & Hebrew Bible
       tob      - Shortcut for displaying French TOB translation
       bj       - Shortcut for displaying French BJ translation

SYNOPSIS
       biblecli [COMMAND | REFERENCE] [ARGS...] [OPTIONS]
       tob      [REFERENCE] [OPTIONS]
       bj       [REFERENCE] [OPTIONS]

DESCRIPTION
       biblecli is a tool for reading and researching the Bible in its original
       languages and modern translations. It supports:
       - Greek New Testament (Nestle 1904)
       - Hebrew Masoretic Text (BHSA - Biblia Hebraica Stuttgartensia)
       - Septuagint (LXX - Rahlfs 1935)
       - French Traduction Œcumenique de la Bible (TOB)
       - Bible de Jérusalem (BJ)
       - English Berean Interlinear Bible

       It features smart lazy-loading of datasets, verse-level cross-references,
       and a personal notebook for saving connections between texts.

COMMANDS
       list books
              List all available books in the N1904 dataset.

       add -c [COLLECTION] -s [SOURCE] -t [TARGET] --type [TYPE] -n [NOTE]
              Add a new cross-reference/note to a personal collection.
              
              Arguments:
              -c, --collection: Collection name (e.g., 'notes'). 
                                Automatically saved as data/references_nt_[name].json 
                                or data/references_ot_[name].json based on source book.
              -s, --source:     Source verse (e.g., 'Mc 1:1')
              -t, --target:     Target verse or reference note (e.g., 'Lc 1:1')
              --type:           Relation type (parallel, allusion, quotation, other). 
                                Default: 'other'
              -n, --note:       Text content of the note

       search [QUERY] (Coming soon)
              Search for specific terms in the texts.

SHORTCUTS
       tob [REFERENCE]
              Equivalent to `biblecli [REFERENCE] -b tob`. 
              Focuses on the French TOB translation. Use -f to view notes.

       bj [REFERENCE]
              Equivalent to `biblecli [REFERENCE] -b bj`.
              Focuses on the French BJ translation.

REFERENCES
       Flexible reference parsing supports English and French abbreviations:
       - Single verse:  "Jn 1:1", "Jean 1:1", "Gen 1:1"
       - Verse range:   "Mt 5:1-10"
       - Whole chapter: "Mk 4"
       - Book aliases:  "Gn" = "Gen" = "Genesis", "Mt" = "Matt", etc.: both French and English abbreviations supported.

OPTIONS
       -h, --help
              Show this help message and exit.

       -t, --tr [en|fr|gr|hb]
              Specify translations to display. Multiple values allowed.
              Codes:
              - en: English (Berean)
              - fr: French (TOB by default. Use -b bj for Bible de Jérusalem)
              - gr: Greek (N1904 for NT, LXX for OT)
              - hb: Hebrew (BHSA)

       -b, --bible [tob|bj]
              Select the French text version (Translation) to display.
              Options: 'tob' (default), 'bj'.

       -c, --crossref
              Display list of cross-references for the verse.

       -f, --crossref-full
              Display cross-references with their full verse text.

       -s, --crossref-source [SOURCE]
              Filter cross-references by source id (e.g. 'tob' for TOB notes, 'all' for all valid sources).
              If omitted, and -b is provided, the bible version is used as the default source.

       -k, --compact
              Compact display: each verse on a new line prefixed with 'vX.', no blank lines.
       
       -K, --very-compact
              Very compact display: each verse on a new line with no prefix (text only), no blank lines.

DATA SOURCES
       N1904 (Greek NT)
              Nestle 1904 Greek New Testament. Structure based on Tischendorf.
              Source: github.com/CenterBLC/N1904

       LXX (Greek OT)
              Septuaginta (Rahlfs 1935).
              Source: github.com/CenterBLC/LXX

       BHSA (Hebrew OT)
              Biblia Hebraica Stuttgartensia Amstellodamensis.
              Source: github.com/ETCBC/bhsa

       TOB (French)
              Traduction Œcumenique de la Bible.
              Note: Requires manual setup due to copyright. See ADD_SOURCES.md.

       BJ (French)
              Bible de Jérusalem.
              Note: Requires manual setup (EPUB conversion). See ADD_SOURCES.md.

       OpenBible
              Cross-reference data provided by OpenBible.info,a modernized, evolution of the classic Treasury of Scripture Knowledge (TSK)

EXAMPLES
       biblecli "Jn 3:16" -t en fr gr
              Show John 3:16 in English, French, and Greek.

       biblecli "Gn 1:1" --tr hb gr
              Show Genesis 1:1 in Hebrew and Greek Septuagint.

       tob "Mc 1:1" -f
              Show Mark 1:1 in French with TOB notes and parallels.

       biblecli list books
              Show all supported book names.
"""
        print(help_text)
