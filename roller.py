#!/usr/bin/env python3
import os
import stat
import base64
import sys

# Directories and files to ignore to avoid self-inclusion, massive virtual environments, caches, and git directories.
IGNORE_NAMES = {
    '.git',
    '.venv',
    'venv',
    'env',
    '__pycache__',
    '.pytest_cache',
    '.DS_Store',
    'chroma_store',
    'roller.py',
    'unroller.py',
    'unroller.py.txt',
    'project_bundle.txt'
}

def get_repo_files(root_dir):
    files_to_roll = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in place to skip ignored directories entirely
        dirnames[:] = [d for d in dirnames if d not in IGNORE_NAMES]
        for filename in filenames:
            if filename in IGNORE_NAMES:
                continue
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_dir)
            files_to_roll.append(rel_path)
    return sorted(files_to_roll)

def find_safe_delimiter(root_dir, files):
    base_delimiter = "__ROLLUP_BOUNDARY_MARKER_9f8c7d6e5a4b3c2d1e0f"
    suffix = ""
    attempt = 0
    while True:
        delimiter = f"{base_delimiter}{suffix}__"
        # Check if the delimiter is in any of the files
        found_in_any = False
        for rel_path in files:
            full_path = os.path.join(root_dir, rel_path)
            try:
                with open(full_path, 'rb') as f:
                    content = f.read()
                    if delimiter.encode('utf-8') in content:
                        found_in_any = True
                        break
            except Exception:
                # Ignore read failures (e.g. broken symlinks or special files)
                pass
        if not found_in_any:
            return delimiter
        attempt += 1
        suffix = f"_{attempt}"

def write_bundle(root_dir, files, delimiter, output_path):
    print(f"Writing bundle to {output_path}...")
    with open(output_path, 'w', encoding='utf-8', newline='\n') as out:
        # Write delimiter metadata as the very first line
        out.write(f"DELIMITER: {delimiter}\n")
        
        for rel_path in files:
            full_path = os.path.join(root_dir, rel_path)
            try:
                st = os.stat(full_path)
                mode = oct(stat.S_IMODE(st.st_mode))
                
                with open(full_path, 'rb') as f:
                    content_bytes = f.read()
                
                # Base64 encode the file content
                b64_content = base64.b64encode(content_bytes).decode('ascii')
                
                # Write file metadata block
                out.write(f"{delimiter}\n")
                out.write(f"PATH: {rel_path}\n")
                out.write(f"MODE: {mode}\n")
                out.write(f"ENCODING: base64\n")
                out.write(f"{delimiter}\n")
                
                # Write base64 content
                out.write(f"{b64_content}\n")
                
                print(f"  Packed: {rel_path} ({len(content_bytes)} bytes)")
            except Exception as e:
                print(f"  Error packing {rel_path}: {e}", file=sys.stderr)
        
        # Write final delimiter to close the last file block
        out.write(f"{delimiter}\n")

def main():
    root_dir = os.path.abspath(os.path.dirname(__file__))
    output_path = os.path.join(root_dir, "project_bundle.txt")
    
    print("Scanning repository files...")
    files = get_repo_files(root_dir)
    print(f"Found {len(files)} files to roll up.")
    
    print("Determining a safe boundary delimiter...")
    delimiter = find_safe_delimiter(root_dir, files)
    print(f"Using delimiter: {delimiter}")
    
    write_bundle(root_dir, files, delimiter, output_path)
    print("\nRollup complete! All files bundled successfully.")

if __name__ == '__main__':
    main()
