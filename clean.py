import os
import shutil
import threading
import time
from typing import List, Set
from contextlib import contextmanager

# Track files being cleaned to prevent concurrent access
_cleaning_lock = threading.Lock()
_files_being_cleaned: Set[str] = set()

@contextmanager
def file_lock(path: str):
    """Context manager for file locking."""
    with _cleaning_lock:
        if path in _files_being_cleaned:
            raise RuntimeError(f"File {path} is already being cleaned")
        _files_being_cleaned.add(path)
    try:
        yield
    finally:
        with _cleaning_lock:
            _files_being_cleaned.discard(path)

def retry_delete(path: str, max_attempts: int = 3, delay: float = 0.5) -> bool:
    """Retry deletion of a file or directory with multiple attempts."""
    for attempt in range(max_attempts):
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            return True
        except (PermissionError, OSError) as e:
            if attempt == max_attempts - 1:
                print(f"Failed to delete {path} after {max_attempts} attempts: {str(e)}")
                return False
            time.sleep(delay)
    return False

def cleanup_files():
    """Clean all generated files and directories from the documentation scraper project."""
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
    
    try:
        # Clean directories
        for directory in directories_to_clean:
            if os.path.exists(directory) and directory not in _files_being_cleaned:
                try:
                    with file_lock(directory):
                        if retry_delete(directory):
                            print(f"✓ Cleaned {directory}/")
                            cleaned = True
                except Exception as e:
                    print(f"✗ Error cleaning {directory}/: {str(e)}")
        
        # Clean individual files
        for file_path in files_to_clean:
            if os.path.exists(file_path) and file_path not in _files_being_cleaned:
                try:
                    with file_lock(file_path):
                        if retry_delete(file_path):
                            print(f"✓ Cleaned {file_path}")
                            cleaned = True
                except Exception as e:
                    print(f"✗ Error cleaning {file_path}: {str(e)}")
        
        if not cleaned:
            print("No generated files found to clean.")
        else:
            print("\nAll generated files have been cleaned successfully.")
            
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
    finally:
        # Ensure we clear the cleaning set
        with _cleaning_lock:
            _files_being_cleaned.clear()

if __name__ == "__main__":
    # Add a confirmation prompt
    response = input("This will remove all generated files. Are you sure? (y/N): ")
    if response.lower() == 'y':
        cleanup_files()
    else:
        print("Operation cancelled.") 