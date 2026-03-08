import pandas as pd
import re

# This is the text you just pasted
raw_text = """
1 (Sample 1, Cav 1) 0,505 4,609
2 (Sample 2, Cav 1) 0,505 4,608
... (etc) ...
"""

def clean_keyence_data(text):
    # Regex to find: [ID] (Sample X, Cav Y) [Val1] [Val2]
    # We replace the comma with a dot for Python math
    pattern = r"(\d+)\s\(Sample\s\d+,\sCav\s(\d+)\)\s(\d+,\d+)\s(\d+,\d+)"
    matches = re.findall(pattern, text)
    
    data = []
    for m in matches:
        data.append({
            "Sample_ID": int(m[0]),
            "Cavity": int(m[1]),
            "Dimension_1": float(m[2].replace(',', '.')),
            "Dimension_2": float(m[3].replace(',', '.'))
        })
    
    return pd.DataFrame(data)

# Test it
df = clean_keyence_data(raw_text)
print(df.head())