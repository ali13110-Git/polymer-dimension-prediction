import pypdf
import pandas as pd
import os

print("✅ Libraries loaded successfully!")

# Let's check your folder structure
raw_folder = os.path.join("data", "raw")
if os.path.exists(raw_folder):
    files = os.listdir(raw_folder)
    print(f"📂 Folder found! Files inside: {files}")
else:
    print("❌ 'data/raw' folder not found. Please create it!")