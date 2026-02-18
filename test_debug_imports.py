
import sys
import os

print("Starting debug...")
sys.path.append(os.getcwd())

try:
    print("Importing typer...")
    import typer
    print("Typer imported.")
except ImportError as e:
    print(f"Failed to import typer: {e}")

try:
    print("Importing src.book_normalizer...")
    from src import book_normalizer
    print("Normalizer imported.")
except ImportError as e:
    print(f"Failed to import normalizer: {e}")
except Exception as e:
    print(f"Error importing normalizer: {e}")

try:
    print("Importing src.cli...")
    from src import cli
    print("CLI imported.")
except Exception as e:
    print(f"Error importing CLI: {e}")

print("Done.")
