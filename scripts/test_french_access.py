import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.text_fabric_adapter import TextFabricAdapter

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    adapter = TextFabricAdapter(data_dir=data_dir)
    
    print("Testing TOB access...")
    try:
        tob_verse = adapter.get_verse("Matthew", 1, 1, "TOB")
        if tob_verse:
             print(f"TOB Mt 1:1: {tob_verse.text}")
        else:
             print("TOB Mt 1:1 NOT FOUND (might need TF data)")
    except Exception as e:
        print(f"TOB Error: {e}")

    print("\nTesting BJ access...")
    try:
        bj_verse = adapter.get_verse("Matthew", 1, 1, "BJ")
        if bj_verse:
             print(f"BJ Mt 1:1: {bj_verse.text}")
        else:
             print("BJ Mt 1:1 NOT FOUND (might need TF data)")
    except Exception as e:
        print(f"BJ Error: {e}")

if __name__ == "__main__":
    main()
