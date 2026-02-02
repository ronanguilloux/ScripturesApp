```
                                                         
 Usage: cli.py [OPTIONS] [REFERENCE] [EXTRA_ARGS]...     
                                                         
 BibleCLI - Command-line interface for the Greek New     
 Testament & Hebrew Bible                                
                                                         
 DESCRIPTION                                             
     biblecli is a tool for reading and researching the  
 Bible in its original                                   
     languages and modern translations. It supports:     
     - Greek New Testament (Nestle 1904)                 
     - Hebrew Masoretic Text (BHSA - Biblia Hebraica     
 Stuttgartensia)                                         
     - Septuagint (LXX - Rahlfs 1935)                    
     - French Traduction Œcumenique de la Bible (TOB)    
     - Bible de Jérusalem (BJ)                           
     - New Arabic Version (NAV)                          
     - English Berean Interlinear Bible                  
                                                         
     It features smart lazy-loading of datasets,         
 verse-level cross-references,                           
     and a personal notebook for saving connections      
 between texts.                                          
                                                         
 COMMANDS                                                
     list books                                          
            List all available books in the N1904        
 dataset.                                                
                                                         
     add -c [COLLECTION] -s [SOURCE] -t [TARGET] --type  
 [TYPE] -n [NOTE]                                        
            Add a new cross-reference/note to a personal 
 collection.                                             
                                                         
            Arguments:                                   
            -c, --collection: Collection name (e.g.,     
 'notes').                                               
                              Automatically saved as     
 data/references_nt_.json                                
                              or                         
 data/references_ot_.json based on source book.          
            -s, --source:     Source verse (e.g., 'Mc    
 1:1')                                                   
            -t, --target:     Target verse or reference  
 note (e.g., 'Lc 1:1')                                   
            --type:           Relation type (parallel,   
 allusion, quotation, other).                            
                              Default: 'other'           
            -n, --note:       Text content of the note   
                                                         
     search [QUERY] (Coming soon)                        
            Search for specific terms in the texts.      
                                                         
 SHORTCUTS                                               
     tob [REFERENCE]                                     
            Equivalent to `biblecli [REFERENCE] -b tob`. 
            Focuses on the French TOB translation. Use   
 -f to view notes.                                       
                                                         
     bj [REFERENCE]                                      
            Equivalent to `biblecli [REFERENCE] -b bj`.  
            Focuses on the French BJ translation.        
                                                         
 REFERENCES                                              
     Flexible reference parsing supports English and     
 French abbreviations:                                   
     - Single verse:  "Jn 1:1", "Jean 1:1", "Gen 1:1"    
     - Verse range:   "Mt 5:1-10"                        
     - Whole chapter: "Mk 4"                             
     - Book aliases:  "Gn" = "Gen" = "Genesis", "Mt" =   
 "Matt", etc.: both French and English abbreviations     
 supported.                                              
                                                         
 DATA SOURCES                                            
     N1904 (Greek NT)                                    
            Nestle 1904 Greek New Testament. Structure   
 based on Tischendorf.                                   
            Source: github.com/CenterBLC/N1904           
                                                         
     LXX (Greek OT)                                      
            Septuaginta (Rahlfs 1935).                   
            Source: github.com/CenterBLC/LXX             
                                                         
     BHSA (Hebrew OT)                                    
            Biblia Hebraica Stuttgartensia               
 Amstellodamensis.                                       
            Source: github.com/ETCBC/bhsa                
                                                         
     TOB (French)                                        
            Traduction Œcumenique de la Bible.           
            Note: Requires manual setup due to           
 copyright. See ADD_SOURCES.md.                          
                                                         
     BJ (French)                                         
            Bible de Jérusalem.                          
            Note: Requires manual setup (EPUB            
 conversion). See ADD_SOURCES.md.                        
                                                         
     NAV (Arabic)                                        
            New Arabic Version (Ketab El Hayat).         
            Note: Requires manual setup (XML             
 conversion). See ADD_SOURCES.md.                        
                                                         
     OpenBible                                           
            Cross-reference data provided by             
 OpenBible.info,a modernized, evolution of the classic   
 Treasury of Scripture Knowledge (TSK)                   
                                                         
 EXAMPLES                                                
     biblecli "Jn 3:16" -t en fr gr                      
            Show John 3:16 in English, French, and       
 Greek.                                                  
                                                         
     biblecli "Gn 1:1" --tr hb gr                        
            Show Genesis 1:1 in Hebrew and Greek         
 Septuagint.                                             
                                                         
     tob "Mc 1:1" -f                                     
            Show Mark 1:1 in French with TOB notes and   
 parallels.                                              
                                                         
     biblecli list books                                 
            Show all supported book names.               
                                                         
     biblecli "Gen 1:1" --tr ar                          
            Show Genesis 1:1 in Arabic (NAV).            
                                                         
╭─ Arguments ───────────────────────────────────────────╮
│   reference       [REFERENCE]      Bible reference    │
│                                    (e.g. 'Gn 1:1')    │
│   extra_args      [EXTRA_ARGS]...  Extra translation  │
│                                    arguments for      │
│                                    compatibility      │
╰───────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────╮
│ --tr              -tr,-t      TEXT  Translations to   │
│                                     show (en, fr, gr, │
│                                     hb, ar)           │
│ --version         -v          TEXT  Primary version   │
│                                     for lookup        │
│                                     (N1904, LXX,      │
│                                     BHSA)             │
│                                     [default: N1904]  │
│ --bible           -b          TEXT  French version    │
│                                     (tob, bj)         │
│ --crossref        -c                Show cross        │
│                                     references        │
│ --crossref-full   -f                Display           │
│                                     cross-references  │
│                                     with text         │
│ --crossref-sour…  -s          TEXT  Filter            │
│                                     cross-references  │
│                                     by source         │
│ --compact         -k                Compact display   │
│                                     (vX. Text)        │
│ --very-compact    -K                Very compact      │
│                                     display (Text     │
│                                     only)             │
│ --install-compl…                    Install           │
│                                     completion for    │
│                                     the current       │
│                                     shell.            │
│ --show-completi…                    Show completion   │
│                                     for the current   │
│                                     shell, to copy it │
│                                     or customize the  │
│                                     installation.     │
│ --help            -h                Show this message │
│                                     and exit.         │
╰───────────────────────────────────────────────────────╯

```
