import os
import shutil
import threading
from typing import List, Set

# Track files being cleaned to prevent concurrent access
_cleaning_lock = threading.Lock()
_files_being_cleaned: Set[str] = set()

def cleanup_files():
    """Clean all generated files and directories from the documentation scraper project."""
    global _files_being_cleaned
    
    # Directories to clean
    directories_to_clean = [
        'documentation',  # Web scraper output
        'chunks',        # Text processor output
        'summaries',     # GPT summarizer output
    ]
    
    # Individual files to clean
    files_to_clean = [
        'combined_summary.txt',
        'optimized_combined_summary.txt'
    ]
    
    cleaned = False
    
    with _cleaning_lock:
        try:
            # Clean directories
            for directory in directories_to_clean:
                if os.path.exists(directory) and directory not in _files_being_cleaned:
                    try:
                        _files_being_cleaned.add(directory)
                        shutil.rmtree(directory)
                        print(f"✓ Cleaned {directory}/")
                        cleaned = True
                    except Exception as e:
                        print(f"✗ Error cleaning {directory}/: {str(e)}")
                    finally:
                        _files_being_cleaned.discard(directory)
            
            # Clean individual files
            for file_path in files_to_clean:
                if os.path.exists(file_path) and file_path not in _files_being_cleaned:
                    try:
                        _files_being_cleaned.add(file_path)
                        os.remove(file_path)
                        print(f"✓ Cleaned {file_path}")
                        cleaned = True
                    except Exception as e:
                        print(f"✗ Error cleaning {file_path}: {str(e)}")
                    finally:
                        _files_being_cleaned.discard(file_path)
            
            if not cleaned:
                print("No generated files found to clean.")
            else:
                print("\nAll generated files have been cleaned successfully.")
                
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
        finally:
            _files_being_cleaned.clear()

if __name__ == "__main__":
    # Add a confirmation prompt
    response = input("This will remove all generated files. Are you sure? (y/N): ")
    if response.lower() == 'y':
        cleanup_files()
    else:
        print("Operation cancelled.") 