import sys
import os
sys.path.append(os.getcwd())
print(f"Python: {sys.executable}")
try:
    print("Importing src.cli...")
    from src import cli
    print("Imported successfully.")
    print("Running cli.find with -tr...")
    # Mock sys.argv
    # Find known word 'λόγος' in NT, show French translation
    sys.argv = ["biblecli", "find", "λόγος", "-b", "nt", "--limit", "2", "-tr", "fr"]
    cli.app()
except Exception as e:
    print(f"Error: {e}")
except SystemExit as e:
    print(f"SystemExit: {e}")
