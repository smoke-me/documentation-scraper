import os
import shutil

def clean_directories():
    """Clean all generated files and directories from the documentation scraper project."""
    directories_to_clean = [
        'documentation',  # Web scraper output
        'chunks',        # Text processor output
        'summaries'      # GPT summarizer output
    ]
    
    cleaned = False
    for directory in directories_to_clean:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                print(f"✓ Cleaned {directory}/")
                cleaned = True
            except Exception as e:
                print(f"✗ Error cleaning {directory}/: {str(e)}")
    
    if not cleaned:
        print("No generated files found to clean.")
    else:
        print("\nAll generated files have been cleaned successfully.")

if __name__ == "__main__":
    # Add a confirmation prompt
    response = input("This will remove all generated files. Are you sure? (y/N): ")
    if response.lower() == 'y':
        clean_directories()
    else:
        print("Operation cancelled.") 