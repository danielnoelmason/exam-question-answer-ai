import pandas as pd
import re

# Load your CSV
file_path = "Practice Questions - exam-certified-data-engineer-professional.csv"
df = pd.read_csv(file_path)

# Safely add [View Question](url) at the start of the QUESTION
def prepend_link(row):
    question = row.get("QUESTION", "")
    if isinstance(question, str):
        url_match = re.search(r'(https?://[^\s]+)', question)
        if url_match:
            url = url_match.group(1)
            return f"[View Question]({url})\n\n{question}"
    return question  # Return original or empty string if invalid

df['QUESTION'] = df.apply(prepend_link, axis=1)

# Save it back
df.to_csv(file_path, index=False)
print(f"✅ Updated file: {file_path}")
