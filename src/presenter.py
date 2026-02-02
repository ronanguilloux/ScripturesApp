import typer
from typing import List, Optional
from domain.models import Verse, VerseCrossReferences, Language

class VersePresenter:
    def present_verse(self, verse: Verse, additional_versions: List[Verse] = None, compact_mode: int = 0, book_name_override: Optional[str] = None):
        """
        Present a primary verse and optional additional versions (parallel).
        """
        header_color = typer.colors.GREEN
        text_color = typer.colors.RESET
        
        # Header Logic
        # Use override if provided (e.g. French name), else book_code
        book_label = book_name_override if book_name_override else verse.book_code

        # Compact Mode Logic
        if compact_mode == 1:
            # vX. Text
            header_str = f"v{verse.verse}. "
            typer.secho(f"{header_str}", nl=False, fg=header_color, bold=True)
            typer.secho(f"{verse.text}", fg=text_color)
        elif compact_mode == 2:
            # Very Compact: Text only
            typer.secho(f"{verse.text}", fg=text_color)
        else:
            # Classic Mode
            # Header: "Book Chapter:Verse"
            header_str = f"{book_label} {verse.chapter}:{verse.verse}"
            typer.secho(f"\n{header_str}", fg=header_color, bold=True)
            typer.secho(f"{verse.text}", fg=text_color)
        
        if additional_versions:
            for v in additional_versions:
                if v:
                    # Legacy matching: No prefixes for TOB/BJ/NAV/BHSA/LXX.
                    # Just distinct lines.
                    typer.secho(f"{v.text}", fg=text_color)

    def present_cross_references(self, refs: VerseCrossReferences, ref_texts: dict = None, formatter=None):
        if not refs or (not refs.relations and not refs.notes):
            return

        typer.secho("\n  ––––––––––", dim=True)
        
        if refs.notes:
            typer.secho("  Notes:", bold=True)
            for note in refs.notes:
                typer.secho(f"    • {note}")

        if refs.relations:
            # Group by type
            by_type = {}
            for r in refs.relations:
                t = r.rel_type.value.capitalize()
                if t not in by_type: by_type[t] = []
                by_type[t].append(r)
            
            for t, rels in by_type.items():
                 typer.secho(f"  {t}:", bold=True, fg=typer.colors.MAGENTA)
                 for r in rels:
                     note_str = f" ({r.note})" if r.note else ""
                     
                     target_label = formatter(r.target_ref) if formatter else r.target_ref
                     
                     # Check indent style parity with Legacy
                     # Legacy: "        Is 1:12" (8 spaces?)
                     # New: "    -> ISA.1.12" (4 spaces + arrow)
                     # Let's drop arrow if formatted? Or keep arrow for style? 
                     # Legacy didn't use arrow.
                     # Let's match legacy: indent 4, no arrow?
                     # "    Is 1:12"
                     
                     typer.echo(f"    {target_label}{note_str}")
                     
                     if ref_texts and r.target_ref in ref_texts:
                         # Print text indented
                         # Legacy style: italic? or just text.
                         text = ref_texts[r.target_ref]
                         if text:
                             typer.secho(f"       {text}", dim=True, italic=True)

    def present_error(self, message: str):
        typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
