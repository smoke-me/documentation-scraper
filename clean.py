import os
import shutil

def cleanup_files():
    """Clean all generated files and directories from the documentation scraper project."""
    # Directories to clean
    directories_to_clean = [
        'documentation',  # Web scraper output
        'chunks',        # Text processor output
        'summaries',     # GPT summarizer output
        'optimized'      # Optimized summaries
    ]
    
    # Individual files to clean
    files_to_clean = [
        'combined_summary.txt',
        os.path.join('optimized', 'combined_summary.txt')
    ]
    
    cleaned = False
    
    # Clean directories
    for directory in directories_to_clean:
        if os.path.exists(directory):
            try:
                shutil.rmtree(directory)
                print(f"✓ Cleaned {directory}/")
                cleaned = True
            except Exception as e:
                print(f"✗ Error cleaning {directory}/: {str(e)}")
    
    # Clean individual files
    for file_path in files_to_clean:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✓ Cleaned {file_path}")
                cleaned = True
            except Exception as e:
                print(f"✗ Error cleaning {file_path}: {str(e)}")
    
    if not cleaned:
        print("No generated files found to clean.")
    else:
        print("\nAll generated files have been cleaned successfully.")

if __name__ == "__main__":
    # Add a confirmation prompt
    response = input("This will remove all generated files. Are you sure? (y/N): ")
    if response.lower() == 'y':
        cleanup_files()
    else:
        print("Operation cancelled.") 