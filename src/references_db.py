import json
import os
import glob
from collections import defaultdict

class ReferenceDatabase:
    def __init__(self, data_dir, normalizer):
        self.data_dir = data_dir
        self.normalizer = normalizer
        # Structure: source_key -> {"notes": [], "relations": []}
        self.in_memory_refs = defaultdict(lambda: {"notes": [], "relations": []})
        self.loaded_files = [] # Track which files contributed to in-memory state

    def load_all(self, source_filter=None):
        """
        Loads references similar to the legacy load_cross_references function.
        """
        self.in_memory_refs.clear()
        
        # Determine files to load based on logic from main.py
        files_to_load = []
        
        # If source_filter is 'tob', only load TOB. 
        # Note: The legacy logic split OT/NT based on book_code but here we load ALL 
        # consistent with a database view, or we can filter later.
        # To maintain exact same behavior for the 'view' command, the view command 
        # might need to call this with specific file lists, OR we load everything and filter by book later.
        # Loading everything is safer for a unified DB.
        
        if source_filter == 'tob':
            files_to_load = ["references_nt_tob.json"] # And OT if it existed
        else:
            # Logic: load all references_nt_*.json
            pattern = os.path.join(self.data_dir, "references_nt_*.json")
            globbed = glob.glob(pattern)
            files_to_load = [os.path.basename(p) for p in globbed]
            
            # Also load OT if present (openbible default)
            files_to_load.append("references_ot_openbible.json")

            if not globbed and "references_nt_openbible.json" not in files_to_load:
                 files_to_load.append("references_nt_openbible.json")

        for filename in files_to_load:
            self._load_file(filename)

    def _load_file(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            # Fallback check
            if "openbible" in filename:
                fb = os.path.join(self.data_dir, "references_openbible.json")
                if os.path.exists(fb):
                    path = fb
                else:
                    return
            else:
                return

        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            for entry in data.get("cross_references", []):
                src = entry["source"]
                # Structure merge
                if src not in self.in_memory_refs:
                    self.in_memory_refs[src] = {"notes": [], "relations": []}
                
                tgt = self.in_memory_refs[src]
                
                if "notes" in entry and entry["notes"]:
                    if entry["notes"] not in tgt["notes"]:
                        tgt["notes"].append(entry["notes"])
                
                if "relations" in entry:
                    tgt["relations"].extend(entry["relations"])
                    
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")

    def get_references(self, book_code):
        """
        Returns the subset of references for a specific book code.
        Used by the viewer to filter relevant refs.
        """
        # The keys are like "GEN.1.1". We verify the prefix.
        filtered = {}
        idx = f"{book_code}."
        for k, v in self.in_memory_refs.items():
            if k.startswith(idx):
                filtered[k] = v
        return filtered

    def add_relation(self, collection_name, source_ref, target_ref, rel_type="other", note=""):
        """
        Adds a relation to a specific collection file.
        This reads the specific file, modifies it, and saves it, 
        independent of the unified in-memory load state.
        """
        filename = f"references_{collection_name}.json"
        path = os.path.join(self.data_dir, filename)
        
        # Load specific file or init new
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"version": "1.0", "cross_references": []}
        else:
            data = {"version": "1.0", "description": f"References for {collection_name}", "cross_references": []}

        # Normalize source and target
        norm_source = self.normalizer.normalize_reference(source_ref)
        norm_target = self.normalizer.normalize_reference(target_ref)
        
        if not norm_source:
            raise ValueError(f"Invalid source reference: {source_ref}")
        if not norm_target:
            raise ValueError(f"Invalid target reference: {target_ref}")
            
        src_str = norm_source[3]
        tgt_str = norm_target[3]
        
        # Find existing source entry or create new
        source_entry = None
        for entry in data["cross_references"]:
            if entry["source"] == src_str:
                source_entry = entry
                break
        
        if not source_entry:
            source_entry = {"source": src_str, "relations": []}
            data["cross_references"].append(source_entry)
            
        if "relations" not in source_entry:
            source_entry["relations"] = []
            
        # Append new relation (allow duplicates as per spec)
        new_rel = {
            "target": tgt_str,
            "type": rel_type,
            "note": note
        }
        # filter empty keys if any (e.g. if note is empty, keep it? spec says "note is then the note added")
        # Usually cleaner to keep keys even if empty string for consistency, or omit. 
        # Sample shows "note" field exists.
        
        source_entry["relations"].append(new_rel)
        
        # Write back
        with open(path, "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        return True
