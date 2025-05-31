"""
Utility script to verify static files during deployment.
Run this with: python verify_static.py
"""

import os
import sys
import glob
import shutil
from pathlib import Path

def check_static_files():
    # Initialize counters
    found_files = 0
    copied_files = 0
    
    print("=" * 80)
    print("STATIC FILES VERIFICATION SCRIPT")
    print("=" * 80)
    
    # Get current directory
    base_dir = Path(__file__).resolve().parent
    print(f"Base directory: {base_dir}")
    
    # Identify potential static file locations
    possible_static_dirs = [
        base_dir / "core" / "static",
        base_dir / "staticfiles",
        Path("/opt/render/project/src/staticfiles"),
        Path("/var/data/staticfiles"),
    ]
    
    # Check each directory
    for static_dir in possible_static_dirs:
        if static_dir.exists():
            print(f"\nFound static directory: {static_dir}")
            
            # Count all files
            static_files = list(static_dir.glob('**/*.*'))
            count = len(static_files)
            found_files += count
            print(f"Contains {count} files")
            
            # List some files as examples
            if count > 0:
                print("Sample files:")
                for file in static_files[:5]:  # Show at most 5 files
                    print(f"  - {file.relative_to(static_dir)}")
                if count > 5:
                    print(f"  - ... and {count - 5} more files")
        else:
            print(f"\nDirectory not found: {static_dir}")
    
    # Check if we need to perform emergency file copy
    src_dir = base_dir / "core" / "static"
    dest_dir = base_dir / "staticfiles"
    
    if src_dir.exists() and dest_dir.exists():
        src_files = list(src_dir.glob('**/*.*'))
        dest_files = list(dest_dir.glob('**/*.*'))
        
        if len(src_files) > 0 and len(dest_files) == 0:
            print("\nEMERGENCY COPY: Source has files but destination is empty!")
            
            # Copy all files
            for src_file in src_files:
                # Get relative path
                rel_path = src_file.relative_to(src_dir)
                # Create destination path
                dest_file = dest_dir / rel_path
                
                # Create parent directories if needed
                os.makedirs(dest_file.parent, exist_ok=True)
                
                # Copy the file
                shutil.copy2(src_file, dest_file)
                print(f"Copied: {rel_path}")
                copied_files += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {found_files} static files, copied {copied_files} files")
    print("=" * 80)

if __name__ == "__main__":
    check_static_files() 