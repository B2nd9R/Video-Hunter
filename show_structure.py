# ملف لعرض هيكلة المشروع بواسطة python

import os
from pathlib import Path

def print_structure(startpath, ignore=None):
    if ignore is None:
        ignore = {'__pycache__', 'venv', 'node_modules', '.git'}
    
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in ignore]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f not in ignore:
                print(f"{subindent}{f}")

print("هيكلة المشروع:")
print_structure('.')