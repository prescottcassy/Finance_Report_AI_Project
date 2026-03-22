import pdfplumber
import re
import os

# 1. Extract full text from a PDF file
def extract_full_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# 2. Split text into sections
def split_into_items(full_text):
    # regex to match ITEM headings
    pattern = r"(ITEM\s+\d+[A]?\.)"
    parts = re.split(pattern, full_text)

    sections = {}
    current = None

    for part in parts:
        if re.match(pattern, part):
            current = part.strip()
            sections[current] = ""
        elif current:
            sections[current] += part
    return sections

# 3. Save important sections
def save_target_sections(sections, output_folder):
    targets = {
        "ITEM 1.": "businessOverview.txt",
        "ITEM 1A.": "riskFactors.txt",
        "ITEM 7.": "managementDiscussion.txt",
        "ITEM 8.": "incomeStatements.txt"
    }

    os.makedirs(output_folder, exist_ok=True)
    
    for item, filename in targets.items():
        for section_title in sections:
            if section_title.startswith(item):
                path = os.path.join(output_folder, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(sections[section_title])
                print(f"Saved: {filename}")

# 4. Main function to run the extraction
def extract_10k_sections(pdf_path, output_folder):
    print("Extracting full text from PDF...")
    full_text = extract_full_text(pdf_path)

    print("Splitting text into sections...")
    sections = split_into_items(full_text)

    print("Saving target sections...")
    save_target_sections(sections, output_folder)

    print("Extraction completed.")

# 5. Run the script    
if __name__ == "__main__":
    pdf_path = "../data/Qualcomm/10K.pdf"
    output_folder = "../data/Qualcomm/extracted"
