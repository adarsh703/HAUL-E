import os
import zipfile

def create_katabump_zip():
    zip_filename = "katabump_deploy.zip"
    
    # Files/directories to exclude
    exclude_dirs = {'.git', 'venv', '__pycache__', '.idea', '.vscode'}
    exclude_files = {
        '.env',                   # Keep secrets out of ZIP; set them in Katabump dashboard
        'broker_bot.log',         # Don't include old logs
        'katabump_deploy.zip',
        'build_katabump_zip.py'
    }
    
    # Files that MUST be included, even if they match some generic exclusion (though we don't have generic exclusions here)
    required_files = ['main.py', 'requirements.txt']
    
    print(f"📦 Creating {zip_filename} for Katabump...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Modify dirs in-place to avoid walking into excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files:
                    continue
                if file.endswith('.pyc'):
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start='.')
                zipf.write(file_path, arcname)
                print(f"  + {arcname}")

    print(f"\n✅ Created {zip_filename} successfully!")
    print("\nNext steps for Katabump:")
    print("1. Log in to Katabump control panel")
    print("2. Go to your server -> Files")
    print(f"3. Upload '{zip_filename}' and Unarchive it")
    print("4. Go to 'Environment Variables' or 'Startup' and add:")
    print("   - DISCORD_TOKEN")
    print("   - ALLOWED_CHANNEL_ID")
    print("   - GMAIL_USER")
    print("   - GMAIL_APP_PASSWORD")
    print("   - GOOGLE_PROJECT_ID (e.g. haul-e-498411)")
    print("   - GEMINI_MODEL (optional)")
    print("   (Ensure google_credentials.json is uploaded alongside these files)")
    print("5. Start your server. Katabump will install requirements.txt and run main.py.")

if __name__ == "__main__":
    create_katabump_zip()
