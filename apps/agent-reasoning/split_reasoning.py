
import re
import os

INPUT_FILE = "data/meaning_of_life_reasoning.txt"
OUTPUT_DIR = "data"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"File {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # The file has sections separated by "="*80 or headers. 
    # Let's split by the "Using model:" line or just the separator.
    # Pattern: "Using model: gemma3:latest+strategy"
    
    # We can regex specifically for the block start
    # Block starts with:
    # Query: ...
    # Using model: ...
    
    # Let's find all chunks
    sections = content.split("="*80)
    
    for section in sections:
        if not section.strip():
            continue
            
        # Find strategy
        match = re.search(r"Using model: .*?\+([a-z_]+)", section)
        if match:
            strategy = match.group(1)
            filename = f"meaning_of_life_{strategy}.txt"
            path = os.path.join(OUTPUT_DIR, filename)
            
            with open(path, "w", encoding="utf-8") as out:
                out.write(section.strip() + "\n")
            
            print(f"Created {filename}")
        else:
            # Maybe standard which might default? 
            # Or headers differ.
            # Let's check for standard header manually if regex fails
            if "standard" in section.lower() and "Using model" in section: # manual check
                 # Try to grab strategy from header line if regex failed due to formatting
                 pass

if __name__ == "__main__":
    main()
