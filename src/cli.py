import typer
import os
import contextlib
from typing import Optional, List
from typing_extensions import Annotated
from enum import Enum

from adapters.text_fabric_adapter import TextFabricAdapter
from domain.models import Language
from domain.models import Language, VerseCrossReferences, CrossReferenceRelation
from presenter import VersePresenter
from references_db import ReferenceDatabase
from book_normalizer import BookNormalizer

# Lazy load helpers (duplicated from main/adapter logic to ensure independence)
# ideally commonly shared utils, but keeping self-contained in factories for now.
from tf.app import use
from tf.fabric import Fabric

app = typer.Typer(help="BibleCLI - Modern Python Bible Reader")

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
    crossref_source: Annotated[Optional[str], typer.Option("--crossref-source", "-s", help="Filter cross-references by source")] = None,
    compact: Annotated[bool, typer.Option("--compact", "-k", help="Compact display (vX. Text)")] = False,
    very_compact: Annotated[bool, typer.Option("--very-compact", "-K", help="Very compact display (Text only)")] = False,
    extra_args: Annotated[Optional[List[str]], typer.Argument(help="Extra translation arguments for compatibility")] = None,
):
    """
    BibleCLI - Modern Python Bible Reader
    """
    # If a subcommand (like search) is called, 'reference' might be None, and strictly likely should be ignored here
    # But Typer callback runs BEFORE command.
    # If invoke_without_command=True, this runs if NO subcommand is used.
    # BUT if a subcommand IS used, this ALSO runs (as parent).
    # We need to detect if we are running as the main action.
    
    if ctx.invoked_subcommand is not None:
        return # Delegate
    # 1. Handle "list books" command
    if reference == "list":
         if extra_args and extra_args[0] == "books":
              # Basic listing
              # Initialize normalizer to get book names
              src_dir = os.path.dirname(os.path.abspath(__file__))
              project_root = os.path.dirname(src_dir)
              data_dir = os.path.join(project_root, "data")
              norm = BookNormalizer(data_dir)
              
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
              presenter.present_error("Unknown command 'list'. Did you mean 'list books'?")
              raise typer.Exit(code=1)

    # 2. Parse Reference
    if not reference:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

    presenter = VersePresenter()
    adapter = AdapterFactory.get()
    
    # 1. Normalize
    # Handle Legacy Range Parsing logic logic is partly in adapter.normalize_reference?
    # No, adapter.normalize_reference returns (book, chapter, verse).
    # Does normalizer handle ranges?
    # We need to be careful. The Adapter 'normalize_reference' assumes single verse.
    # We might need to handle the "1:2-5" splitting here or in adapter.
    
    # For now, let's try the existing normalizer. If it fails on range, we need to fix it.
    # The error "Full chapter reading not yet implemented" suggests it parsed verse=0 or failed.
    
    # Let's rely on adapter for simpler cases first, then check range logic.
    norm = adapter.normalize_reference(reference)

    if compact or very_compact:
         typer.secho(f"\n{reference}", fg=typer.colors.GREEN, bold=True)
    
    if not norm:
         # It might be a Range that normalizer didn't handle nicely returning None
         # Or it might be invalid.
         # The legacy ReferenceHandler handled ranges. Adapter should too.
         # I will delegate range handling to the Adapter's 'get_verses' method eventually.
         # But for strict check:
         presenter.present_error(f"Invalid reference '{reference}'")
         raise typer.Exit(code=1)
    
    book_code, chapter, verse = norm
    
    # 2b. Determine Primary Version (Early)
    # 2b. Determine Primary Version (Early)
    # Refined Logic: Select primary based on requested translations to ensure Main Verse is one of them.
    # Hierarchy matching Legacy Printer: Hebrew > Greek > English > French > Arabic
    is_nt = adapter.normalizer.is_nt(book_code)
    primary_v = version # Default
    
    if translations:
        # Map requested languages to versions
        candidates = []
        for t in translations:
            t = t.lower()
            if t == 'hb': candidates.append('BHSA')
            elif t == 'gr': candidates.append('N1904' if is_nt else 'LXX')
            elif t == 'en': candidates.append('N1904_EN') # English Gloss 
                                                        # Actually N1904 is Greek. Legacy English usually assumes N1904?
            elif t == 'fr': candidates.append((french_version or 'tob').upper())
            elif t == 'ar': candidates.append('NAV')
            elif t in ['tob', 'bj', 'nav', 'lxx', 'bhsa', 'n1904']: candidates.append(t.upper())
            
        # Select best candidate
        # Rank: BHSA, LXX/N1904, TOB/BJ, NAV
        best = None
        # Ranking logic
        if not is_nt and 'BHSA' in candidates: best = 'BHSA'
        elif (is_nt and 'N1904' in candidates) or (not is_nt and 'LXX' in candidates): 
             best = 'N1904' if is_nt else 'LXX'
        elif is_nt and 'N1904_EN' in candidates: 
             best = 'N1904_EN'
        elif 'N1904' in candidates: best = 'N1904' # English maps to N1904
        
        if not best:
             # Try French
             for c in candidates:
                 if c in ['TOB', 'BJ']: 
                     best = c
                     break
        if not best:
             # Try Arabic
             if 'NAV' in candidates: best = 'NAV'
             
        if best:
             primary_v = best
    else:
        # Default defaults
        if version == "N1904": 
            if not is_nt:
                primary_v = "LXX"
    
    verses_to_fetch = []
    
    # Range Handling Logic
    parsed_range = False
    if "-" in reference and ":" in reference:
        last_colon = reference.rfind(":")
        if last_colon != -1:
             part_Right = reference[last_colon+1:]
             if "-" in part_Right:
                 try:
                     start_s, end_s = part_Right.split("-")
                     start_v = int(start_s)
                     end_v = int(end_s)
                     
                     for v in range(start_v, end_v + 1):
                         verses_to_fetch.append((book_code, chapter, v))
                     parsed_range = True
                 except ValueError:
                     pass

    # 3. Determine Verses to Fetch
    results = [] # Results for Chapter Mode

    if not parsed_range:
        if verse == 0:
             # Chapter Mode
             try:
                 chapter_verses = adapter.get_chapter(book_code, chapter, primary_v)
                 if not chapter_verses:
                      presenter.present_error(f"No verses found for {book_code} {chapter}")
                      raise typer.Exit(code=1)
                 
                 for v_obj in chapter_verses:
                      v_num = v_obj.verse
                      parallels = []
                      
                      if translations:
                           for tr in translations:
                                tr = tr.lower()
                                v_code = None
                                # Logic duplicated from below loop? 
                                if tr == 'en': v_code = 'N1904_EN'
                                elif tr == 'fr': v_code = (french_version or "tob").upper()
                                elif tr == 'gr': v_code = 'N1904' if is_nt else 'LXX'
                                elif tr == 'hb': v_code = 'BHSA'
                                elif tr == 'ar': v_code = 'NAV'
                                
                                if v_code and v_code != primary_v:
                                     # Efficiency: lazy fetch 1 by 1
                                     p_v = adapter.get_verse(book_code, chapter, v_num, version=v_code)
                                     parallels.append(p_v)
                           
                      results.append((v_obj, parallels))
                      
             except Exception as e:
                 presenter.present_error(f"Chapter fetch failed: {e}")
                 raise typer.Exit(code=1)
        else:
             # Single Verse
             verses_to_fetch.append((book_code, chapter, verse))

    # 4. Fetch Loop (if results not already populated)
    if not results:
                
        # 3. Fetch Loop
        # Merge extra args into translations for greedy support
        if translations is None: translations = []
        
        if extra_args:
            # Check if they are languages
            valid_langs = ["en", "fr", "gr", "hb", "ar", "tob", "bj", "nav", "lxx", "bhsa", "n1904"]
            for arg in extra_args:
                 if arg.lower() in valid_langs:
                     translations.append(arg)
                 # If not, maybe it's part of the reference if reference was split?
                 # E.g. biblecli "Dt" "1:1"
                 # But Typer usually grabs positional args into reference. 
                 # If reference="Dt", extra_args=["1:1"].
                 # We should join them if reference looks incomplete?
                 # Or just handle languages.
                 pass

        results = []
        for (b, c, v) in verses_to_fetch:
            try:
                 v_obj = adapter.get_verse(b, c, v, version=primary_v)
                 if v_obj:
                     parallels = []
                     if translations:
                        for tr in translations:
                            tr = tr.lower()
                            v_code = None
                            if tr == 'en': v_code = 'N1904_EN'
                            elif tr == 'fr': v_code = (french_version or "tob").upper()
                            elif tr == 'gr': v_code = 'N1904' if is_nt else 'LXX'
                            elif tr == 'hb': v_code = 'BHSA'
                            elif tr == 'ar': v_code = 'NAV'
                            
                            if v_code and v_code != primary_v:
                                sec_verse = adapter.get_verse(b, c, v, version=v_code)
                                parallels.append(sec_verse)
                     else:
                        # Smart Defaults: Greek, Hebrew (OT), French
                        # 1. Greek
                        greek_code = 'N1904' if is_nt else 'LXX'
                        if primary_v != greek_code:
                            gr_verse = adapter.get_verse(b, c, v, version=greek_code)
                            parallels.append(gr_verse)
                        
                        # 2. Hebrew (OT only)
                        if not is_nt and primary_v != 'BHSA':
                             hb_verse = adapter.get_verse(b, c, v, version='BHSA')
                             parallels.append(hb_verse)
                             
                        # 3. French
                        if primary_v != (french_version or "tob").upper():
                             fr_verse = adapter.get_verse(b, c, v, version=(french_version or "tob").upper())
                             parallels.append(fr_verse)
                     
                     results.append((v_obj, parallels))
            except Exception:
                 pass

    # 4. Determine Compact Mode
    compact_mode = 0
    if very_compact: compact_mode = 2
    elif compact: compact_mode = 1

    # 5. Present
    for main_v, pars in results:
        # Calculate Header Override
        # Legacy logic: If displaying French, use French book name in Header.
        # Otherwise use English/N1904 name.
        header_name = None
        
        # Check if French is being displayed
        is_french_active = False
        if translations:
             if 'fr' in [t.lower() for t in translations]: is_french_active = True
        else:
             # Default logic: if no translation overrides, and we are showing french (usually yes by default)?
             # The CLI defaults to Greeks + Hebrew (OT) + French (TOB/BJ).
             # So yes.
             is_french_active = True
             
        if is_french_active:
             # Try to localize main_v.book_code
             code = main_v.book_code
             
             # N1904 name from code
             # normalizer.code_to_n1904 usually exists
             n1904_name = adapter.normalizer.code_to_n1904.get(code, code)
             
             # TOB name
             tob_name = adapter.normalizer.n1904_to_tob.get(n1904_name)
             if tob_name:
                 header_name = tob_name
        
        # English Header Logic
        is_english_active = False
        if translations and 'en' in [t.lower() for t in translations]: is_english_active = True
        if primary_v == "N1904_EN": is_english_active = True
        
        if is_english_active and not is_french_active: # French takes precedence? Legacy output with French is French.
             # Legacy English output uses English Header
             code = main_v.book_code
             en_name = adapter.normalizer.code_to_n1904.get(code, code)
             if en_name:
                 header_name = en_name.replace("_", " ")

        presenter.present_verse(main_v, pars, compact_mode=compact_mode, book_name_override=header_name)

    
    # 6. Cross Refs
    if show_crossrefs or crossref_full:
        # Initialize dependencies relative to this script
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        data_dir = os.path.join(project_root, "data")
        
        norm = BookNormalizer(data_dir)
        ref_db = ReferenceDatabase(data_dir, norm)
        
        # Determine Source Filter
        s_filter = crossref_source
        if not s_filter and french_version:
             # If no explicit source filter, use -b/--french as hint if it looks like a source?
             # Legacy logic: "Smart default: if no -s provided, but -b provided, use -b as source hint"
             s_filter = french_version

        # Determine Scope
        scope = 'all'
        if adapter.normalizer.is_nt(book_code): scope = 'nt'
        elif adapter.normalizer.is_ot(book_code): scope = 'ot'
        
        ref_db.load_all(source_filter=s_filter, scope=scope)
        
        # Retrieve refs for this specific verse
        # Legacy used 'book_key' resolution. 
        # Here we have 'book_code' (GEN), 'chapter', 'verse'.
        # We need the key string e.g. "GEN.1.1"
        key = f"{book_code}.{chapter}.{verse}"
        
        key = f"{book_code}.{chapter}.{verse}"
        
        refs_dict = ref_db.in_memory_refs.get(key)
        
        refs_model = None
        if refs_dict:
             # Convert to Pydantic Model
             # legacy data "type" -> model "rel_type"
             relations = []
             for r in refs_dict.get("relations", []):
                  relations.append(CrossReferenceRelation(
                      target_ref=r["target"],
                      rel_type=r["type"],
                      note=r.get("note")
                  ))
             
             refs_model = VerseCrossReferences(
                 notes=refs_dict.get("notes", []),
                 relations=relations
             )
        
        if refs_model:
            # If full text requested, fetch target verses
            ref_texts = {}
            if crossref_full:
                 for rel in refs_model.relations:
                     target = rel.target_ref
                     # Parse target ref
                     target = rel.target_ref
                     parsed = None
                     
                     # Try Manual Parsing for TF/OpenBible style "BOOK.C.V"
                     if "." in target and not " " in target:
                         parts = target.split(".")
                         if len(parts) >= 3:
                             # Basic range "BOOK.C.V-BOOK.C.V" handled?
                             # OpenBible usually "BOOK.C.V"
                             # But ranges exist "BOOK.C.V-C.V" ??
                             # Handle verse ranges "29-30" or "1a" (if unnormalized?)
                             # OpenBible usually pure numbers but ranges happen.
                             v_str = parts[2]
                             if "-" in v_str:
                                 v_str = v_str.split("-")[0]
                             
                             # Clean potential suffixes? "14a"? TF usually handles ints.
                             # Assuming integers for now as per adapter.
                             if v_str.isdigit():
                                  parsed = (parts[0], int(parts[1]), int(v_str))
                             else:
                                  parsed = None
                     
                     if not parsed:
                         # Try standard normalizer
                         parsed = norm.normalize_reference(target)
                         
                     if parsed:
                         tb, tc, tv = parsed
                         
                         # Determine version for lookup
                         is_target_nt = norm.is_nt(tb)
                         target_v = primary_v
                         if target_v == "N1904" and not is_target_nt: target_v = "LXX"
                         if target_v == "BHSA" and is_target_nt: target_v = "N1904"
                         if target_v == "TOB" or target_v == "BJ":
                              # Keep French if requested as primary? 
                              # Legacy usually showed text in Default (LXX/BHSA/N1904)??
                              # Step 176 of Legacy printer output showed French text?
                              # "Quand vous venez..." (French).
                              # So if Primary is French (TOB default), crossrefs are French.
                              pass

                         # Helper to fetch
                         try:
                             v_obj = adapter.get_verse(tb, tc, tv, version=target_v)
                             if v_obj:
                                 ref_texts[target] = v_obj.text
                         except: 
                             pass

            # Formatter Helper
            def format_ref(target_str):
                 # Ported from verse_printer.py format_ref_fr
                 if not target_str: return ""
                 def parse_one(ref):
                     parts = ref.split(".")
                     if len(parts) >= 3:
                         bk, ch, vs = parts[0], parts[1], parts[2]
                         # Try French Abbr
                         # We need code_to_fr_abbr? Not available on norm?
                         # norm has code_to_n1904. n1904_to_tob.
                         # Logic: Code -> N1904 -> TOB (French Name) -> Abbr?
                         # Or just Code -> N1904 -> TOB Name.
                         # Legacy used 'code_to_fr_abbr'. BookNormalizer has it?
                         # Let's check BookNormalizer members in memory or file?
                         # Assuming norm.data_dir loaded bible_books.json which has "abbreviations".
                         # But 'code_to_fr_abbr' might be property?
                         # Let's fallback to TOB Name or Code.
                         
                         n1904 = norm.code_to_n1904.get(bk, bk)
                         tob_name = norm.n1904_to_tob.get(n1904, bk)
                         return tob_name, ch, vs
                     return None, None, None

                 if "-" in target_str:
                      pass # Simplified for now, just return raw if range complex
                 
                 abbr, ch, vs = parse_one(target_str)
                 if abbr:
                      return f"{abbr} {ch}:{vs}"
                 return target_str

            presenter.present_cross_references(refs_model, ref_texts=ref_texts, formatter=format_ref)


# Search command removed to ensure Single Command App behavior for legacy compatibility
# @app.command()
# def search(query: str): ...


if __name__ == "__main__":
    app()
