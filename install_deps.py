#!/usr/bin/env python3
"""
Simple dependency installer for Morning Digest
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a single package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("Installing Morning Digest dependencies...")
    
    # Core dependencies needed for the orchestration system
    core_deps = [
        "anthropic>=0.7.0",
        "aiohttp>=3.8.0", 
        "feedparser>=6.0.0",
        "tiktoken>=0.5.0",
        "python-dateutil>=2.8.0",
        "pyyaml>=6.0",
        "jinja2>=3.1.0"
    ]
    
    failed = []
    
    for dep in core_deps:
        print(f"Installing {dep}...")
        if install_package(dep):
            print(f"  OK: {dep}")
        else:
            print(f"  FAILED: {dep}")
            failed.append(dep)
    
    if failed:
        print(f"\nFailed to install: {failed}")
        print("You may need to install these manually:")
        for dep in failed:
            print(f"  pip install {dep}")
    else:
        print("\nAll dependencies installed successfully!")
        print("You can now run: python -m src.main health")

if __name__ == "__main__":
    main()