""" This script extracts text and financial  tables from SEC 10‑K PDF filings by identifying ITEM sections using a flexible, format‑agnostic regex. It saves key sections—Business
Overview, Risk Factors, MD&A, and Item 8 financial statements; into organized text files and consolidates all detected financial tables into CSVs. The tool is designed to handle 
inconsistent 10‑K formatting  across companies, ensuring reliable extraction for downstream analysis and modeling. 
"""

import pdfplumber
import re
import os
import csv

# 1. Extract full text from a PDF file
def extract_full_text(pdf_path):
    print(f"Opening PDF at: {pdf_path}")
    if not os.path.exists(pdf_path):
        print("ERROR: PDF path does not exist.")
        return ""

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
    pattern = r"(Item\s+1A?\.?\s*|Item\s+7\.?\s*|Item\s+8\.?\s*)"
    parts = re.split(pattern, full_text)

    sections = {}
    current = None

    for part in parts:
        if re.match(pattern, part, flags=re.IGNORECASE):
            current = part.strip().upper()
            sections[current] = ""
        elif current:
            sections[current] += part
    return sections

# 3. Helper function to extract table name from page
def extract_table_name(page_text):
    """Extract table title from page text and convert to filename"""
    # Common table titles to look for
    table_patterns = [
        ("CONSOLIDATED BALANCE SHEET", "consolidated_balance_sheet"),
        ("BALANCE SHEET", "balance_sheet"),
        ("CONSOLIDATED STATEMENT OF INCOME", "consolidated_income_statement"),
        ("CONSOLIDATED INCOME STATEMENT", "consolidated_income_statement"),
        ("INCOME STATEMENT", "income_statement"),
        ("CONSOLIDATED STATEMENT OF CASH FLOWS", "consolidated_cash_flows"),
        ("CASH FLOWS", "cash_flows"),
        ("STATEMENT OF STOCKHOLDERS", "stockholders_equity"),
        ("STOCKHOLDERS EQUITY", "stockholders_equity"),
    ]
    
    page_upper = page_text.upper()
    
    for pattern, filename in table_patterns:
        if pattern in page_upper:
            return filename
    
    return None

# 4. Helper function to find Item position with flexible formatting
def find_item_position(text, item_num):
    """Find position of Item X in text (case-insensitive, flexible formatting)"""
    text_upper = text.upper()
    
    # Try different formats
    patterns = [
        f"ITEM {item_num}.",      # "ITEM 8."
        f"ITEM {item_num}:",      # "ITEM 8:"
        f"ITEM {item_num}",       # "ITEM 8" (general match)
        f"Item {item_num}.",      # "Item 8."
        f"Item {item_num}:",      # "Item 8:"
        f"Item {item_num}",       # "Item 8" (general match)
    ]
    
    for pattern in patterns:
        pos = text_upper.find(pattern)
        if pos != -1:
            return pos
    
    return -1

# 5. Extract tables from Item 8 pages
def extract_item8_tables(pdf_path, full_text, output_folder):
    # Identify where Item 8 starts and ends using flexible search
    item8_start = find_item_position(full_text, "8")
    item9_start = find_item_position(full_text, "9")


    if item8_start == -1:
        print("Could not find Item 8 in text.")
        return

    if item9_start == -1:
        item9_start = len(full_text)

    # Extract the text of Item 8
    item8_text = full_text[item8_start:item9_start]

    # Dictionary to collect tables by type
    tables_by_type = {}

    # Open PDF to find pages containing Item 8 text
    with pdfplumber.open(pdf_path) as pdf:
        tables_found = 0
        pages_with_keywords = 0
        
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""

            # Print progress every 10 pages
            if i % 10 == 0:
                print(f"Checking page {i+1}/{len(pdf.pages)}")

            # Skip early pages (covers, TOC, etc.) - financial statements start around page 50+
            if i < 50:
                continue

            # Check for financial statement keywords
            has_keywords = any(keyword in page_text.upper() for keyword in 
                             ["CONSOLIDATED", "BALANCE SHEET", "INCOME", "OPERATIONS", "CASH FLOW"])
            
            if has_keywords:
                pages_with_keywords += 1
                
                # Extract the table title/name from page text
                table_name = extract_table_name(page_text)
                
                tables = page.extract_tables()
                
                if tables is None: 
                    continue

                for t_index, table in enumerate(tables):
                    if table is None or len(table) == 0:
                        continue
                    
                    
                    # Group tables by type
                    if table_name:
                        if table_name not in tables_by_type:
                            tables_by_type[table_name] = []
                        tables_by_type[table_name].append((table, i+1))
                    
                    tables_found += 1
        
        # Write consolidated files - one per table type
        for table_name, table_list in tables_by_type.items():
            csv_path = os.path.join(output_folder, f"{table_name}.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                for idx, (table, page_num) in enumerate(table_list):
                    # Add separator between different occurrences of same table type
                    if idx > 0:
                        writer.writerow([f"--- Table from page {page_num} ---"])
                        writer.writerow([])
                    else:
                        # Add header for first occurrence
                        writer.writerow([f"Table from page {page_num}"])
                        writer.writerow([])
                    
                    for row in table:
                        writer.writerow(row)
                    
                    writer.writerow([])  # Blank row between tables
            
            print(f"Saved consolidated table: {table_name}.csv ({len(table_list)} occurrences)")
        
# 6. Save important sections
def save_target_sections(sections, output_folder):
    targets = {
        "Item 1.": "businessOverview.txt",
        "Item 1A.": "riskFactors.txt",
        "Item 7.": "managementDiscussion.txt",
        "Item 8.": "incomeStatements.txt"
    }

    os.makedirs(output_folder, exist_ok=True)
    
    for item, filename in targets.items():
        for section_title in sections:
            if section_title.startswith(item):
                path = os.path.join(output_folder, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(sections[section_title])
                print(f"Saved: {filename}")

# 7. Main function to run the extraction
def extract_10k_sections(pdf_path, output_folder):
    print("Extracting full text from PDF...")
    full_text = extract_full_text(pdf_path)

    print("Splitting text into sections...")
    sections = split_into_items(full_text)

    print("Saving target sections...")
    save_target_sections(sections, output_folder)

    print("Extracting tables from Item 8...")
    extract_item8_tables(pdf_path, full_text, output_folder)

    print("Extraction completed.")

# 8. Run the script    
if __name__ == "__main__":
    pdf_path = "data/Qualcomm/10K.pdf"
    output_folder = "data/Qualcomm/extracted"
    text = extract_10k_sections(pdf_path, output_folder)
    print(text)
