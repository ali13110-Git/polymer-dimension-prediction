from pypdf import PdfReader
import re

# Use the one Keyence PDF you have locally
FILE_PATH = "data/raw/your_report.pdf" 

def debug_pdf():
    reader = PdfReader(FILE_PATH)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    print("--- RAW TEXT START ---")
    print(text) # Look at this to see how Keyence labels its data
    print("--- RAW TEXT END ---")

    # This is where your trial and error happens
    # We will adjust this regex until it hits your dimensions perfectly
    dimensions = re.findall(r"(\d+\.\d{3})", text) 
    print(f"Found Dimensions: {dimensions}")

if __name__ == "__main__":
    debug_pdf()