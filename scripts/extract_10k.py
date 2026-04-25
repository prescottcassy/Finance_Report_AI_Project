"""
extract_10k.py

Extracts text and financial tables from SEC 10-K PDF filings.
- Accepts a PDF path directly (no hardcoded data/ folder)
- Saves extracted sections as text files to output_folder
- Integrates structured financial model extraction (financial_model_extractor.py)
- Returns extracted sections dict for use by 10k_reader.py
"""

import pypdf
import re
import os
import csv
import pdfplumber
import tempfile
from glob import glob


def _find_best_item_span(full_text, item_num, next_item_candidates, required_keywords=None):
    """Find the best ITEM span, preferring full-body sections over TOC snippets."""
    required_keywords = required_keywords or []
    start_pattern = re.compile(rf"\bITEM\s+{re.escape(item_num)}\b[\.:\-–—]?", re.IGNORECASE)
    next_patterns = [
        re.compile(rf"\bITEM\s+{re.escape(next_item)}\b[\.:\-–—]?", re.IGNORECASE)
        for next_item in next_item_candidates
    ]

    starts = list(start_pattern.finditer(full_text))
    if not starts:
        return ""

    best_text = ""
    best_score = -1
    text_len = len(full_text)

    for start_match in starts:
        start_idx = start_match.start()
        end_idx = text_len

        for next_pattern in next_patterns:
            next_match = next_pattern.search(full_text, start_match.end())
            if next_match:
                end_idx = min(end_idx, next_match.start())

        if end_idx <= start_idx:
            continue

        candidate = full_text[start_idx:end_idx].strip()
        if not candidate:
            continue

        score = len(candidate)
        lowered = candidate.lower()
        score += sum(3000 for kw in required_keywords if kw.lower() in lowered)
        if start_idx < int(0.08 * text_len):
            score -= 5000

        if score > best_score:
            best_score = score
            best_text = candidate

    return best_text


def extract_full_text(pdf_path):
    print(f"Extracting text from PDF: {pdf_path}")
    if not os.path.exists(pdf_path):
        print("ERROR: PDF path does not exist.")
        return ""

    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)
            print(f"Total pages: {total_pages}")
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception:
                    pass
                if (i + 1) % 50 == 0:
                    print(f"  Extracted {i + 1}/{total_pages} pages...")
        print(f"✓ Total extracted: {len(text)} characters")
    except Exception as e:
        print(f"Error: {e}")
    return text


def split_into_items(full_text):
    pattern = r"(ITEM[\s\u00A0]+[\d]+[A-Z]?(?:[\.\:\-–—])?[\s\u00A0]*)"
    parts = re.split(pattern, full_text, flags=re.IGNORECASE)

    sections = {}
    current = None

    for part in parts:
        if re.match(pattern, part, flags=re.IGNORECASE):
            current = part.strip().upper()
            sections[current] = ""
        elif current:
            sections[current] += part

    print(f"Found {len(sections)} ITEM sections:")
    for key in sorted(sections.keys()):
        size = len(sections[key].strip())
        print(f"  - {key}: {size} characters")

    return sections


def extract_table_name(page_text):
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


def find_item_position(text, item_num):
    text_upper = text.upper()
    patterns = [
        f"ITEM {item_num}.", f"ITEM {item_num}:", f"ITEM {item_num}",
        f"Item {item_num}.", f"Item {item_num}:", f"Item {item_num}",
    ]
    for pattern in patterns:
        pos = text_upper.find(pattern)
        if pos != -1:
            return pos
    return -1


def extract_item8_tables(pdf_path, full_text, output_folder):
    item8_start = find_item_position(full_text, "8")
    item9_start = find_item_position(full_text, "9")

    if item8_start == -1:
        print("Could not find Item 8 in text.")
        return

    if item9_start == -1:
        item9_start = len(full_text)

    tables_by_type = {}

    with pdfplumber.open(pdf_path) as pdf:
        tables_found = 0
        pages_with_keywords = 0

        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            print(f"Checking page {i+1}/{len(pdf.pages)}")

            has_keywords = any(keyword in page_text.upper() for keyword in
                               ["CONSOLIDATED", "BALANCE SHEET", "INCOME", "OPERATIONS",
                                "CASH FLOW", "REVENUES", "EXPENSES"])

            if has_keywords:
                pages_with_keywords += 1
                table_name = extract_table_name(page_text)
                all_tables = []

                for settings in [{}, {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
                                  {"vertical_strategy": "edges", "horizontal_strategy": "edges"}]:
                    try:
                        tables = page.extract_tables(settings) if settings else page.extract_tables()
                        if tables:
                            all_tables.extend(tables)
                    except Exception:
                        pass

                seen = set()
                for table in all_tables:
                    if table is None or len(table) < 2:
                        continue
                    table_key = str(table[:2])
                    if table_key not in seen:
                        seen.add(table_key)
                        if table_name:
                            if table_name not in tables_by_type:
                                tables_by_type[table_name] = []
                            tables_by_type[table_name].append((table, i + 1))
                            tables_found += 1
                            print(f"  → Found table: {table_name} ({len(table)} rows)")

        print(f"\nSummary: {pages_with_keywords} pages with financial keywords, {tables_found} table entries")

        for table_name, table_list in tables_by_type.items():
            csv_path = os.path.join(output_folder, f"{table_name}.csv")
            total_rows = sum(len(t[0]) for t in table_list)

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([f"{table_name.upper().replace('_', ' ')} - Multiple Years"])
                writer.writerow([f"Total occurrences: {len(table_list)}, Total rows: {total_rows}"])
                writer.writerow([])

                for idx, (table, page_num) in enumerate(table_list):
                    if idx > 0:
                        writer.writerow([])
                        writer.writerow([f"--- Occurrence {idx+1} from page {page_num} ---"])
                        writer.writerow([])
                    for row in table:
                        writer.writerow(row)
                    writer.writerow([])

            print(f"✓ Saved: {table_name}.csv ({len(table_list)} occurrences, {total_rows} total rows)")


def append_financial_tables_to_text(output_folder):
    income_path = os.path.join(output_folder, "incomeStatements.txt")
    if not os.path.exists(income_path):
        return

    csv_files = []
    for pattern in ["*income*.csv", "*balance*.csv", "*cash_flow*.csv", "*cash_flows*.csv"]:
        csv_files.extend(glob(os.path.join(output_folder, pattern)))

    if not csv_files:
        return

    snippets = []
    for csv_file in sorted(set(csv_files)):
        try:
            with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            if lines:
                header = os.path.basename(csv_file)
                sample = "\n".join(lines[:60])
                snippets.append(f"\n\n--- {header} ---\n{sample}")
        except Exception as e:
            print(f"⚠ Could not read {csv_file}: {e}")

    if snippets:
        with open(income_path, "a", encoding="utf-8") as f:
            f.write("\n\n[EXTRACTED FINANCIAL TABLES]\n")
            f.write("\n".join(snippets))
        print(f"✓ Appended financial table snippets to incomeStatements.txt ({len(snippets)} files)")


def save_target_sections(sections, output_folder, full_text=""):
    targets = {
        "ITEM 1.":  "businessOverview.txt",
        "ITEM 1A.": "riskFactors.txt",
        "ITEM 7.":  "managementDiscussion.txt",
        "ITEM 8.":  "incomeStatements.txt",
    }

    fallback_patterns = {
        "businessOverview.txt":    ["ITEM 1A", "ITEM 1", "BUSINESS", "ITEM 1."],
        "riskFactors.txt":         ["ITEM 1A", "ITEM 1A.", "RISK FACTORS", "RISK"],
        "managementDiscussion.txt":["ITEM 7", "ITEM 7.", "MD&A", "MANAGEMENT", "DISCUSSION"],
        "incomeStatements.txt":    ["ITEM 8", "ITEM 8.", "FINANCIAL STATEMENTS", "ITEM 9", "ITEM 9."],
    }

    direct_item_config = {
        "businessOverview.txt":    {"item": "1",  "next": ["1A", "1B", "2"],   "keywords": ["business", "operations", "segments"]},
        "riskFactors.txt":         {"item": "1A", "next": ["1B", "2"],          "keywords": ["risk", "adverse", "uncertainties"]},
        "managementDiscussion.txt":{"item": "7",  "next": ["7A", "8"],          "keywords": ["management", "discussion", "analysis", "results of operations"]},
        "incomeStatements.txt":    {"item": "8",  "next": ["9", "9A", "10"],    "keywords": ["financial statements", "balance sheets", "income", "cash flows"]},
    }

    os.makedirs(output_folder, exist_ok=True)
    extracted = {}

    for item_key, filename in targets.items():
        saved = False
        content = ""
        matched_section = None

        for section_title in sections:
            if section_title.startswith(item_key):
                content = sections[section_title].strip()
                matched_section = section_title
                saved = True
                break

        if not saved and filename in fallback_patterns:
            for pattern in fallback_patterns[filename]:
                if saved:
                    break
                for section_title in sections:
                    section_upper = section_title.upper()
                    if section_upper.startswith(pattern.upper()):
                        content = sections[section_title].strip()
                        matched_section = section_title
                        saved = True
                        break

        if filename == "incomeStatements.txt" and (not saved or len(content) < 300):
            for section_title in sections:
                if "ITEM 8" in section_title.upper():
                    item8_content = sections[section_title].strip()
                    if len(item8_content) > len(content):
                        content = item8_content
                        matched_section = section_title
                        saved = True
                        break

        if (not saved or len(content) < 1200) and full_text and filename in direct_item_config:
            cfg = direct_item_config[filename]
            direct_content = _find_best_item_span(full_text, cfg["item"], cfg["next"], cfg["keywords"])
            if direct_content and len(direct_content) > len(content):
                content = direct_content
                matched_section = f"Direct ITEM {cfg['item']} span"
                saved = True

        path = os.path.join(output_folder, filename)
        if saved and content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ Saved: {filename} (from {matched_section}) - {len(content)} chars")
            extracted[filename] = content
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write("[Section not found in this 10-K]")
            print(f"⚠ No content found for {filename} - created placeholder")
            extracted[filename] = ""

    return extracted


def extract_10k_sections(pdf_path, output_folder=None, company_name=""):
    """
    Main extraction function.

    Args:
        pdf_path:      Path to the 10-K PDF file (required)
        output_folder: Where to save intermediate text/CSV files.
                       If None, a temp folder is used automatically.
        company_name:  Optional company name for labeling outputs.

    Returns:
        dict with keys:
          "sections"     → {filename: text_content} for the 4 key ITEM sections
          "full_text"    → full extracted PDF text
          "output_folder"→ path where files were saved
          "company_name" → resolved company name
    """
    # If no output folder specified, use a temp directory
    if output_folder is None:
        output_folder = tempfile.mkdtemp(prefix="10k_extract_")
        print(f"Using temp folder: {output_folder}")

    if not company_name:
        # Derive from PDF filename: "AAPL_10K.pdf" → "AAPL"
        company_name = os.path.splitext(os.path.basename(pdf_path))[0].split("_")[0]

    try:
        print("=" * 60)
        print(f"Extracting 10-K sections — {company_name}")
        print("=" * 60)

        print("Step 1: Extracting full text from PDF...")
        full_text = extract_full_text(pdf_path)

        if not full_text or len(full_text.strip()) < 100:
            print("⚠ WARNING: Very little text extracted — PDF may be image-based.")

        print(f"Step 2: Extracted {len(full_text)} characters")

        print("Step 3: Splitting into ITEM sections...")
        sections = split_into_items(full_text)

        print(f"Step 4: Saving extracted sections to {output_folder}...")
        extracted_sections = save_target_sections(sections, output_folder, full_text)

        print("Step 5: Extracting financial statement tables...")
        try:
            extract_item8_tables(pdf_path, full_text, output_folder)
        except Exception as e:
            print(f"⚠ Table extraction skipped: {e}")

        print("Step 6: Merging financial table snippets...")
        append_financial_tables_to_text(output_folder)

        print("Step 7: Building structured financial model...")
        try:
            from financial_model_extractor import extract_financial_model # pyright: ignore[reportMissingImports]
            extract_financial_model(pdf_path, output_folder, company_name)
        except ImportError:
            print("⚠ financial_model_extractor.py not found — skipping Excel model")
        except Exception as e:
            print(f"⚠ Financial model extraction failed: {e}")

        print("=" * 60)
        print("✓ Extraction complete!")
        print("=" * 60)

        return {
            "sections": extracted_sections,
            "full_text": full_text,
            "output_folder": output_folder,
            "company_name": company_name,
        }

    except Exception as e:
        print(f"✗ ERROR during extraction: {e}")
        import traceback
        traceback.print_exc()
        return {
            "sections": {},
            "full_text": "",
            "output_folder": output_folder,
            "company_name": company_name,
        }


# ── Run standalone ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_10k.py <path_to_10k.pdf> [output_folder] [company_name]")
        sys.exit(1)

    pdf_path      = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    company_name  = sys.argv[3] if len(sys.argv) > 3 else ""

    result = extract_10k_sections(pdf_path, output_folder, company_name)
    print(f"\nOutput saved to: {result['output_folder']}")