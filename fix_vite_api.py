import os
import glob
import re

files = glob.glob('tms/src/**/*.tsx', recursive=True) + glob.glob('tms/src/**/*.ts', recursive=True)

for file in files:
    with open(file, 'r') as f:
        content = f.read()
        
    # Replace `${import.meta.env.VITE_API_URL}/api/...` with `/api/...`
    new_content = content.replace("`${import.meta.env.VITE_API_URL}/api", "`/api")
    new_content = new_content.replace("${import.meta.env.VITE_API_URL}/api", "/api")
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"Updated {file}")
