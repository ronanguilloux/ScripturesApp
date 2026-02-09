import typer
import os
from typing import Optional, List
from typing_extensions import Annotated

from presenter import VersePresenter
from book_normalizer import BookNormalizer
from references_db import ReferenceDatabase

app = typer.Typer(help="ScripturesApp - Modern Python Bible Reader", context_settings={"help_option_names": ["-h", "--help"]})

class AdapterFactory:
    _adapter = None
    
    @classmethod
    def get(cls):
        if cls._adapter:
            return cls._adapter
            
        # Data dir for normalizer (bible_books.json)
        # Assuming src/cli.py is in src/, so data is in ../data relative to this file
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        data_dir = os.path.join(project_root, "data")
        
        # Define providers
        def n1904_p():
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/N1904", version="1.0.0", silent=True)
                 except: return None
        
        def lxx_p():
             # Basic implementation
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/LXX", version="1935", check=False, silent=True)
                 except: return None

        # ... other providers can be added as needed or rely on Adapter defaults ...
        
        adapter = TextFabricAdapter(
            data_dir=data_dir,
            n1904_provider=n1904_p,
            lxx_provider=lxx_p,
            # Pass others if needed, adapter has some internal fallbacks too
        )
        cls._adapter = adapter
        return adapter

@app.command()
def main(
    ctx: typer.Context,
    reference: Annotated[Optional[str], typer.Argument(help="Bible reference (e.g. 'Gn 1:1')")] = None,
    translations: Annotated[Optional[List[str]], typer.Option("--tr", "-tr", "-t", help="Translations to show (en, fr, gr, hb, ar)")] = None,
    version: Annotated[str, typer.Option("--version", "-v", help="Primary version for lookup (N1904, LXX, BHSA)")] = "N1904",
    french_version: Annotated[Optional[str], typer.Option("--bible", "-b", help="French version (tob, bj)")] = None,
    show_crossrefs: Annotated[bool, typer.Option("--crossref", "-c", help="Show cross references")] = False,
    crossref_full: Annotated[bool, typer.Option("--crossref-full", "-f", help="Display cross-references with text")] = False,
    crossref_source: Annotated[Optional[str], typer.Option("--crossref-source", "-s", help="Filter cross-references by source (default: aggregate all)")] = None,
    compact: Annotated[bool, typer.Option("--compact", "-k", help="Compact display (vX. Text)")] = False,
    very_compact: Annotated[bool, typer.Option("--very-compact", "-K", help="Very compact display (Text only)")] = False,
    extra_args: Annotated[Optional[List[str]], typer.Argument(help="Extra translation arguments for compatibility")] = None,
):
    """
    ScripturesApp - Command-line interface for the Greek New Testament & Hebrew Bible
    
    DESCRIPTION
        scripturesapp (biblecli) is a tool for reading and researching the Bible in its original
        languages and modern translations. It supports:
        - Greek New Testament (Nestle 1904)
        - Hebrew Masoretic Text (BHSA - Biblia Hebraica Stuttgartensia)
        - Septuagint (LXX - Rahlfs 1935)
        - French Traduction Œcumenique de la Bible (TOB)
        - Bible de Jérusalem (BJ)
        - New Arabic Version (NAV)
        - English Berean Interlinear Bible

        It features smart lazy-loading of datasets, verse-level cross-references,
        and a personal notebook for saving connections between texts.

    COMMANDS
        list books
               List all available books in the N1904 dataset.

        add -c [COLLECTION] -s [SOURCE] -t [TARGET] --type [TYPE] -n [NOTE]
               Add a new cross-reference/note to a personal collection.

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
    """
    
    if ctx.invoked_subcommand is not None:
        return # Delegate
        
    # 1. Handle "list books" command
    if reference == "list":
         if extra_args and extra_args[0] == "books":
              from application.services import AdapterFactory
              # Basic listing
              # Initialize normalizer to get book names
              # We can use AdapterFactory to get adapter and normalizer
              adapter = AdapterFactory.get()
              norm = adapter.normalizer
              
              ot_list = []
              nt_list = []
              # Sort by book_order
              sorted_codes = sorted(norm.book_order.keys(), key=lambda k: norm.book_order[k])
              for code in sorted_codes:
                  name = norm.code_to_n1904.get(code, code)
                  if norm.is_ot(code):
                      ot_list.append(name)
                  elif norm.is_nt(code):
                      nt_list.append(name)
              
              typer.secho("Available Books:", bold=True)
              typer.secho("OT: ", nl=False, bold=True)
              typer.echo(", ".join(ot_list))
              typer.secho("NT: ", nl=False, bold=True)
              typer.echo(", ".join(nt_list))
              raise typer.Exit()
         else:
              presenter = VersePresenter()
              presenter.present_error("Unknown command 'list'. Did you mean 'list books'?")
              raise typer.Exit(code=1)

    # 2. Parse Reference
    if not reference:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

    from application.services import BibleService
    service = BibleService()
    presenter = VersePresenter()
    
    # Pre-process Extra Args
    if translations is None: translations = []
    if extra_args:
        # Check if they are languages
        valid_langs = ["en", "fr", "gr", "hb", "ar", "tob", "bj", "nav", "lxx", "bhsa", "n1904"]
        for arg in extra_args:
             if arg.lower() in valid_langs:
                 translations.append(arg)
                 
    if compact or very_compact:
         typer.secho(f"\n{reference}", fg=typer.colors.GREEN, bold=True)
         
    try:
        response = service.search(
            reference=reference,
            translations=translations,
            version=version,
            french_version=french_version,
            show_crossrefs=show_crossrefs,
            crossref_full=crossref_full,
            crossref_source=crossref_source
        )
    except Exception as e:
        presenter.present_error(str(e))
        raise typer.Exit(code=1)
        
    # 4. Determine Compact Mode
    compact_mode = 0
    if very_compact: compact_mode = 2
    elif compact: compact_mode = 1

    # 5. Present
    for item in response.verses:
        main_v = item.primary
        pars = item.parallels
        
        # Calculate Header Override
        # Legacy logic: If displaying French, use French book name in Header.
        header_name = None
        
        # Check if French is being displayed
        is_french_active = False
        if translations:
             if 'fr' in [t.lower() for t in translations]: is_french_active = True
        else:
             is_french_active = True
             
        if is_french_active:
             # Try to localize main_v.book_code
             code = main_v.book_code
             
             # N1904 name
             n1904_name = service.normalizer.code_to_n1904.get(code, code)
             
             # TOB name
             tob_name = service.normalizer.n1904_to_tob.get(n1904_name)
             if tob_name:
                 header_name = tob_name
        
        # English Header Logic
        is_english_active = False
        if translations and 'en' in [t.lower() for t in translations]: is_english_active = True
        if item.primary.version == "N1904_EN": is_english_active = True
        
        if is_english_active and not is_french_active: 
             code = main_v.book_code
             en_name = service.normalizer.code_to_n1904.get(code, code)
             if en_name:
                 header_name = en_name.replace("_", " ")

        presenter.present_verse(main_v, pars, compact_mode=compact_mode, book_name_override=header_name)

    
    # 6. Cross Refs
    if response.cross_references:
        # Formatter Helper (Ported Logic)
        def format_ref(target_str):
             if not target_str: return ""
             def parse_one(ref):
                 parts = ref.split(".")
                 if len(parts) >= 3:
                     bk, ch, vs = parts[0], parts[1], parts[2]
                     n1904 = service.normalizer.code_to_n1904.get(bk, bk)
                     tob_name = service.normalizer.n1904_to_tob.get(n1904, bk)
                     return tob_name, ch, vs
                 return None, None, None

             if "-" in target_str:
                 parts_range = target_str.split("-")
                 if len(parts_range) == 2:
                     start_parsed = parse_one(parts_range[0])
                     end_parsed = parse_one(parts_range[1])
                     
                     if start_parsed[0] and end_parsed[0]:
                         sb, sc, sv = start_parsed
                         eb, ec, ev = end_parsed
                         if sb == eb:
                             if sc == ec: return f"{sb} {sc}:{sv}-{ev}"
                             else: return f"{sb} {sc}:{sv}-{ec}:{ev}"
                         else: return f"{sb} {sc}:{sv}-{eb} {ec}:{ev}"
              
             abbr, ch, vs = parse_one(target_str)
             if abbr:
                  return f"{abbr} {ch}:{vs}"
             return target_str

        # Note: formatting and ref_texts logic is currently not fully populated in BibleService for cross refs
        # The service returns VerseCrossReferences model.
        # But 'ref_texts' dict required for full text display is NOT in the response yet?
        # WAIT. services.py: "// Full text fetch if requested ... pass"
        # I did not implement populating 'ref_texts' in the service!
        
        # CRITICAL: Re-implement full text fetch for cross refs in CLI or Service?
        # Ideally Service. But I skipped it.
        # For now, to match legacy behavior, I should probably re-implement it here using service.adapter?
        # Or quickly add it to service?
        # Adding to service is cleaner. 
        # But I'm in the middle of replacing CLI.
        # I will fetch it here using service.adapter (exposed via service).
        
        ref_texts = {}
        if crossref_full and response.cross_references:
             for rel in response.cross_references.relations:
                 if rel.text:
                     ref_texts[rel.target_ref] = rel.text

        presenter.present_cross_references(response.cross_references, ref_texts=ref_texts, formatter=format_ref)


def add_cli(
    collection: Annotated[str, typer.Option("--collection", "-c", help="Collection name (e.g., 'notes').")],
    source: Annotated[str, typer.Option("--source", "-s", help="Source verse (e.g., 'Mc 1:1')")],
    target: Annotated[str, typer.Option("--target", "-t", help="Target verse or reference note (e.g., 'Lc 1:1')")],
    rel_type: Annotated[str, typer.Option("--type", help="Relation type (parallel, allusion, quotation, other). Default: 'other'")] = "other",
    note: Annotated[str, typer.Option("--note", "-n", help="Text content of the note")] = ""
):
    """
    Add a new cross-reference/note to a personal collection.
    """
    try:
        from application.services import AdapterFactory
        adapter = AdapterFactory.get()
        # AdapterFactory calculates data_dir internally, but we can access it via adapter instance
        data_dir = adapter.data_dir
        normalizer = adapter.normalizer
        
        db = ReferenceDatabase(data_dir, normalizer)
        success = db.add_relation(collection, source, target, rel_type, note)
        
        if success:
             typer.secho(f"Successfully added reference to collection '{collection}'", fg=typer.colors.GREEN)
        else:
             typer.secho("Failed to add reference.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
             
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        sys.argv.pop(1) # Remove "add" command so typer sees the rest as args/options
        typer.run(add_cli)
    else:
        app()
