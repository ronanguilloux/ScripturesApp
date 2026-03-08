import os
import sys
import json
import subprocess
from typing import List, Dict, Any
from src.ports.nlp_provider import NLPProvider

class LocalNLPAdapter(NLPProvider):
    """
    Implementation of NLPProvider that invokes local Python workers via subprocess.
    """
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.workers_dir = os.path.join(self.project_root, "src", "application", "workers")
        
        # Determine the appropriate Python executable (venv-spacy or current)
        self.venv_python = os.path.join(self.project_root, ".venv-spacy", "bin", "python3")
        if not os.path.exists(self.venv_python):
             self.venv_python = sys.executable

    def find_words(self, query: str, limit: int, search_corpus: str, mode: str) -> Dict[str, Any]:
        if mode == "french":
            worker_script = os.path.join(self.workers_dir, "french_worker.py")
            cmd = [sys.executable, worker_script, query, "--bible", search_corpus, "--limit", str(limit)]
        else: # Greek
            worker_script = os.path.join(self.workers_dir, "find_worker.py")
            cmd = [self.venv_python, worker_script, query, "--limit", str(limit), "--corpus", search_corpus]

        return self._run_command(cmd)

    def find_septantisms(self, payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        worker_script = os.path.join(self.workers_dir, "septantism_worker.py")
        cmd = [self.venv_python, worker_script]
        return self._run_command_with_input(cmd, json.dumps(payload))

    def analyze_intertextuality(self, payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        worker_script = os.path.join(self.workers_dir, "intertext_worker.py")
        cmd = [self.venv_python, worker_script]
        return self._run_command_with_input(cmd, json.dumps(payload))

    def analyze_greek_word(self, word: str) -> List[Dict[str, Any]]:
        worker_script = os.path.join(self.workers_dir, "greek_worker.py")
        cmd = [self.venv_python, worker_script, word]
        return self._run_command(cmd)

    def _run_command(self, cmd: List[str]) -> Any:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            raise RuntimeError(f"Error running NLP worker: {e}")
            
        if result.returncode != 0:
            raise RuntimeError(f"NLP Worker failed: {result.stderr}")
            
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid output from NLP worker: {result.stdout}")

    def _run_command_with_input(self, cmd: List[str], input_data: str) -> Any:
        try:
            result = subprocess.run(cmd, input=input_data, capture_output=True, text=True)
        except Exception as e:
            raise RuntimeError(f"Error running NLP worker: {e}")
            
        if result.returncode != 0:
            raise RuntimeError(f"NLP Worker failed: {result.stderr}")
            
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid output from NLP worker: {result.stdout}")
