"""
10k_reader.py

Reads a 10-K PDF, extracts key sections, generates AI summaries using
Anthropic's API, and produces a downloadable investment research PDF report.

Usage:
    python 10k_reader.py <path_to_10k.pdf> [company_name]

Output:
    <company_name>_10K_Report.pdf  (in same folder as input PDF, or cwd)
"""

import sys
import os
import textwrap
import re
import importlib.util
from collections import Counter
from datetime import datetime
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from pypdf import PdfReader

import importlib.util

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(project_root, ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

extract_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'extract_10k.py')
spec = importlib.util.spec_from_file_location("extract_10k", extract_path)

def _missing_extract(*args, **kwargs):
    raise RuntimeError("extract_10k could not be loaded.")

extract_10k_sections = _missing_extract
if spec and spec.loader:
    extract_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract_module)
    extract_10k_sections = extract_module.extract_10k_sections

# ── PDF report builder ────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


# ── Model setup ───────────────────────────────────────────────────────────────
anthropic_client = None
anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
fallback_models = [
    "claude-3-5-haiku-latest",
    "claude-3-5-sonnet-latest",
    "claude-3-haiku-20240307",
]
resolved_model = None


def _candidate_models() -> list[str]:
    ordered = [anthropic_model] + fallback_models
    deduped = []
    for model_name in ordered:
        if model_name and model_name not in deduped:
            deduped.append(model_name)
    return deduped


def _discover_available_models() -> list[str]:
    """Discover models available to the current Anthropic API key."""
    global anthropic_client
    if anthropic_client is None:
        return []

    try:
        models_page = anthropic_client.models.list()  # type: ignore[union-attr]
        discovered = []
        for model in models_page.data:
            model_id = getattr(model, "id", None)
            if model_id:
                discovered.append(model_id)
        return discovered
    except Exception as e:
        print(f"Could not discover Anthropic models: {e}")
        return []


def load_model():
    global anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    anthropic_client = Anthropic(api_key=api_key)
    print(f"Anthropic client initialized with model: {anthropic_model}")


def _run_inference(prompt: str, max_new_tokens: int = 170) -> str:
    global anthropic_client, resolved_model
    if anthropic_client is None:
        load_model()

    last_error = None
    # If we already found a working model, use it first.
    model_candidates = []
    if resolved_model:
        model_candidates.append(resolved_model)

    # User-configured and fallback candidates.
    model_candidates.extend(_candidate_models())

    # Dynamically discovered account-available models.
    model_candidates.extend(_discover_available_models())

    deduped_candidates = []
    for model_name in model_candidates:
        if model_name and model_name not in deduped_candidates:
            deduped_candidates.append(model_name)

    for model_name in deduped_candidates:
        try:
            continuation_rounds = int(os.getenv("ANTHROPIC_CONTINUATION_ROUNDS", "2"))
            messages = [{"role": "user", "content": prompt}]
            text_parts = []

            for _ in range(continuation_rounds + 1):
                response = anthropic_client.messages.create(  # type: ignore[union-attr]
                    model=model_name,
                    max_tokens=max_new_tokens,
                    messages=messages,  # type: ignore[arg-type]
                )

                chunk_parts = []
                for block in response.content:
                    block_text = getattr(block, "text", None)
                    if block_text:
                        chunk_parts.append(block_text)

                chunk = "\n".join(chunk_parts).strip()
                if chunk:
                    text_parts.append(chunk)

                stop_reason = getattr(response, "stop_reason", None)
                if stop_reason != "max_tokens":
                    break

                if not chunk:
                    break

                messages.append({"role": "assistant", "content": chunk})
                messages.append({
                    "role": "user",
                    "content": "Continue exactly where you left off. Do not restart, do not summarize what you already wrote, and do not repeat prior text.",
                })

            # Remember working model for subsequent calls in this process.
            resolved_model = model_name
            if model_name != anthropic_model:
                print(f"Anthropic model fallback in use: {model_name}")
            return "\n".join(text_parts).strip()
        except Exception as e:
            last_error = e
            error_text = str(e).lower()
            # Retry only for model-not-found style failures.
            if "not_found_error" in error_text or "model:" in error_text:
                continue
            raise

    raise RuntimeError(f"All configured Anthropic models failed. Last error: {last_error}")


def _clean_output_text(text: str) -> str:
    """Normalize model output to plain readable text (remove markdown artifacts)."""
    if not text:
        return ""

    cleaned = text.replace("**", "").replace("`", "")
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def _ensure_complete_sentence(text: str, max_completion_tokens: int = 120) -> str:
    """If model output looks truncated, request a short continuation to finish cleanly."""
    cleaned = _clean_output_text(text)
    if not cleaned:
        return cleaned

    if cleaned.endswith((".", "!", "?", '"')):
        return cleaned

    try:
        continuation_prompt = f"""The text below appears truncated. Continue from the exact point where it ends and finish the final sentence.
Requirements:
- Return only the continuation text.
- Do not restart or repeat prior text.
- End with a complete sentence.

Current text:
{cleaned}

Continuation:"""
        continuation = _run_inference(continuation_prompt, max_new_tokens=max_completion_tokens)
        continuation = _clean_output_text(continuation.split("Continuation:")[-1])
        merged = f"{cleaned} {continuation}".strip()
        return _clean_output_text(merged)
    except Exception:
        return cleaned


def _read_text_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file_handle:
        return file_handle.read()


def extract_uploaded_document_text(file_path: str) -> str:
    """Extract text from a supported uploaded document."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".pdf":
        text_parts = []
        reader = PdfReader(file_path)
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if page_text.strip():
                text_parts.append(page_text)
        return "\n".join(text_parts).strip()

    if extension in {".txt", ".md", ".text"}:
        return _read_text_file(file_path).strip()

    raise ValueError(f"Unsupported analysis document type: {extension or 'unknown'}")


def _normalize_for_rag(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _tokenize_for_rag(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9%$,.\-/]*", _normalize_for_rag(text))
    return [token.strip("$,.\/-%)") for token in tokens if token.strip("$,.\/-%)")]


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 220) -> list[str]:
    """Split text into overlapping chunks for retrieval."""
    normalized = (text or "").strip()
    if not normalized:
        return []

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", normalized) if paragraph.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue

        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}"
            continue

        chunks.append(current.strip())
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        start = 0
        step = max(1, chunk_size - overlap)
        while start < len(paragraph):
            piece = paragraph[start:start + chunk_size].strip()
            if piece:
                chunks.append(piece)
            start += step
        current = ""

    if current.strip():
        chunks.append(current.strip())

    return chunks


def build_rag_corpus(documents: list[dict], chunk_size: int = 1200, overlap: int = 220) -> list[dict]:
    """Build a retrievable chunk corpus from named source documents."""
    corpus: list[dict] = []
    for document in documents:
        source_name = document.get("source", "source")
        text = (document.get("text") or "").strip()
        if not text:
            continue

        for index, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, overlap=overlap), start=1):
            cleaned = chunk.strip()
            if not cleaned:
                continue
            corpus.append({
                "source": f"{source_name}::chunk_{index}",
                "text": cleaned,
            })

    return corpus


def _score_relevance(query_tokens: list[str], chunk_tokens: list[str]) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0

    query_counter = Counter(query_tokens)
    chunk_counter = Counter(chunk_tokens)
    overlap_score = sum(min(count, chunk_counter.get(token, 0)) for token, count in query_counter.items())

    numeric_bonus = 0.0
    for token in query_counter:
        if any(character.isdigit() for character in token) and token in chunk_counter:
            numeric_bonus += 2.0

    return float(overlap_score + numeric_bonus)


def retrieve_relevant_chunks(query: str, corpus: list[dict], top_k: int = 4) -> list[dict]:
    """Return the most relevant chunks for a query using lexical overlap."""
    query_tokens = _tokenize_for_rag(query)
    ranked = []

    for chunk in corpus:
        chunk_text_value = chunk.get("text", "")
        score = _score_relevance(query_tokens, _tokenize_for_rag(chunk_text_value))
        if score <= 0:
            continue
        ranked.append({**chunk, "score": score})

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]


def _should_verify_claim(sentence: str) -> bool:
    lowered = sentence.lower()
    signal_words = [
        "revenue", "sales", "income", "profit", "loss", "margin", "cash flow", "debt",
        "guidance", "growth", "customer", "employee", "risk", "market", "assets", "liabilities",
        "operating", "quarter", "year", "fiscal", "million", "billion", "%",
    ]
    if any(word in lowered for word in signal_words):
        return True
    if re.search(r"\d", sentence):
        return True
    return len(sentence) >= 90


def _split_analysis_claims(text: str, max_claims: int = 12) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text or "") if paragraph.strip()]
    claims: list[str] = []

    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        for sentence in sentences:
            candidate = sentence.strip().strip("-•\t")
            if len(candidate) < 35:
                continue
            if _should_verify_claim(candidate) or len(candidate) >= 120:
                claims.append(candidate)
            if len(claims) >= max_claims:
                return claims

    if not claims and text.strip():
        claims.append(text.strip()[:500])

    return claims[:max_claims]


def _parse_verification_response(response_text: str) -> dict:
    verdict = "Unclear"
    reason = response_text.strip()
    evidence = ""

    verdict_match = re.search(r"VERDICT:\s*(Supported|Partially Supported|Unsupported|Unclear)", response_text, flags=re.IGNORECASE)
    if verdict_match:
        verdict = verdict_match.group(1).title()

    reason_match = re.search(r"REASON:\s*(.*?)(?:\nEVIDENCE:|$)", response_text, flags=re.IGNORECASE | re.DOTALL)
    if reason_match:
        reason = reason_match.group(1).strip()

    evidence_match = re.search(r"EVIDENCE:\s*(.*)$", response_text, flags=re.IGNORECASE | re.DOTALL)
    if evidence_match:
        evidence = evidence_match.group(1).strip()

    return {
        "verdict": verdict,
        "reason": reason,
        "evidence": evidence,
    }


def verify_analysis_document(document_name: str, document_text: str, corpus: list[dict], company_name: str = "the company") -> dict:
    """Verify the factual claims in an uploaded analysis document against the 10-K corpus."""
    claims = _split_analysis_claims(document_text)
    findings: list[dict] = []

    for claim in claims:
        retrieved = retrieve_relevant_chunks(claim, corpus, top_k=4)
        context_block = "\n\n".join(
            f"[{chunk['source']}]\n{chunk['text']}" for chunk in retrieved
        )
        if not context_block.strip():
            findings.append({
                "claim": claim,
                "verdict": "Unclear",
                "reason": "No relevant 10-K evidence was retrieved for this claim.",
                "evidence": "",
                "sources": [],
            })
            continue

        prompt = f"""You are checking whether a user's analysis statement is supported by the 10-K source excerpts.
Use only the excerpts below. If the claim is partially right, say what is right and what is not.

Return plain text in exactly this format:
VERDICT: Supported | Partially Supported | Unsupported | Unclear
REASON: brief explanation
EVIDENCE: one or two short quotes or paraphrases from the excerpts

Company: {company_name}

Source excerpts:
{context_block}

Analysis statement:
{claim}"""

        verification_text = _run_inference(prompt, max_new_tokens=260)
        parsed = _parse_verification_response(verification_text)
        findings.append({
            "claim": claim,
            "verdict": parsed["verdict"],
            "reason": parsed["reason"],
            "evidence": parsed["evidence"],
            "sources": [chunk["source"] for chunk in retrieved],
        })

    verdicts = {finding["verdict"] for finding in findings}
    if "Unsupported" in verdicts:
        overall_status = "needs_review"
    elif "Partially Supported" in verdicts or "Unclear" in verdicts:
        overall_status = "review"
    else:
        overall_status = "verified"

    return {
        "file_name": document_name,
        "overall_status": overall_status,
        "findings": findings,
    }


def summarize_verification_results(results: list[dict]) -> str:
    """Create a compact plain-text summary of verification results for the report."""
    if not results:
        return "No analysis documents were uploaded for verification."

    lines = []
    for result in results:
        lines.append(f"{result.get('file_name', 'analysis document')}: {result.get('overall_status', 'review')}")
        for finding in result.get("findings", [])[:5]:
            lines.append(
                f"- {finding.get('verdict', 'Unclear')}: {finding.get('claim', '')}"
            )
            reason = finding.get("reason", "")
            if reason:
                lines.append(f"  {reason}")
    return "\n".join(lines).strip()


# ── AI generation functions ───────────────────────────────────────────────────

def build_summary_prompt(text: str, section_name: str) -> tuple[str, int]:
    """Build the exact summary prompt and token budget used for inference."""
    # Long-form limits so total report is approximately five pages.
    section_max_tokens = int(os.getenv("SECTION_SUMMARY_MAX_TOKENS", "700"))
    regular_context_chars = int(os.getenv("SECTION_SUMMARY_CONTEXT_CHARS", "2800"))
    financial_context_chars = int(os.getenv("FINANCIAL_SUMMARY_CONTEXT_CHARS", "5000"))
    regular_target_words = int(os.getenv("SECTION_SUMMARY_TARGET_WORDS", "420"))
    financial_target_words = int(os.getenv("FINANCIAL_SUMMARY_TARGET_WORDS", "520"))

    if "financial" in section_name.lower() or "income" in section_name.lower():
        prompt = f"""You are a fun financial storyteller. Analyze this {section_name} section from a 10-K filing and turn it into a engaging story for someone who knows nothing about finance. Write it like you're explaining it to a curious friend over coffee, no jargon, no boring tables. If you use any financial word, explain it immediately in simple terms.  
Requirements:
- Quote specific numeric figures when available.
- Include at least 5 concrete figures (e.g., revenue, operating income, net income, cash flow, assets/liabilities) if present.
- Explain year-over-year changes and operational drivers.
- Highlight profitability, liquidity, and cash-flow implications.
- If exact values are unavailable, say what is missing and still inferable.
- Do not use placeholders like [Company Name].
- Keep the response complete and detailed; do not end mid-sentence.
- Target length: approximately {financial_target_words} words.
- Return plain text only. Do not use markdown formatting, headings, hashtags, or asterisks.

Content:
{text[:financial_context_chars]}

Financial Analysis:"""
    else:
        prompt = f"""You are a fun financial storyteller. Analyze this {section_name} section from a 10-K filing and turn it into a engaging story for someone who knows nothing about finance. Write it like you're explaining it to a curious friend over coffee, no jargon, no boring tables. If you use any financial word, explain it immediately in simple terms.
Requirements:
- Include concrete facts from the text.
- Prioritize implications for revenue, margins, growth, and risk.
- Do not use placeholders like [Company Name].
- Keep the response complete and detailed; do not end mid-sentence.
- Target length: approximately {regular_target_words} words.
- Return plain text only. Do not use markdown formatting, headings, hashtags, or asterisks.

Content:
{text[:regular_context_chars]}

Summary:"""

    return prompt, section_max_tokens

def build_bluf_prompt(all_summaries: str, company_name: str = "the company") -> tuple[str, int]:
    """Build the exact BLUF prompt and token budget used for inference."""
    prompt = f"""Based on this 10-K analysis for {company_name}, provide a direct investment bottom line using plain language that also answers the following question: : "Why should I care about this?" Write it from 3 perspectives — an employee, a customer, and a small investor.
Requirements:
- Mention the company name: {company_name}
- Include one key supporting reason.
- Do not use placeholders.
- Return plain text only. Do not use markdown formatting, headings, hashtags, or asterisks.

Key Sections:
{all_summaries[:1200]}

Investment Decision:"""
    return prompt, 220


def build_narrative_prompt(all_summaries: str, company_name: str = "the company") -> tuple[str, int]:
    """Build the exact narrative prompt and token budget used for inference."""
    narrative_target_words = int(os.getenv("NARRATIVE_TARGET_WORDS", "700"))
    narrative_max_tokens = int(os.getenv("NARRATIVE_MAX_TOKENS", "950"))
    prompt = f"""Write a comprehensive investor narrative for {company_name} based on its 10-K filing for a complete beginner that doesn't use jargon. Write it like you're explaining it to a curious friend over coffee, no jargon, no boring tables. If you use any financial word, explain it immediately in simple terms. Structure it like this: first, how the company makes money → then where it spent money → then what was left over → then one fun takeaway at the end. Compare big numbers to everyday. 
Requirements:
- Mention the company name: {company_name}
- Connect strategy, risks, and financial trajectory.
- Include at least one specific figure or clearly state if figures are unavailable.
- Do not use placeholders.
- Target length: approximately {narrative_target_words} words.
- Return plain text only. Do not use markdown formatting, headings, hashtags, or asterisks.

Key Sections Summary:
{all_summaries[:4500]}

The Story:"""
    return prompt, narrative_max_tokens

def generate_summary(text: str, section_name: str) -> str:
    if not text or len(text.strip()) < 100:
        return f"[{section_name} section not found or too short to analyze]"
    prompt, section_max_tokens = build_summary_prompt(text, section_name)

    try:
        result = _run_inference(prompt, max_new_tokens=section_max_tokens)
        for delimiter in ["Financial Analysis:", "Summary:"]:
            if delimiter in result:
                parsed = _clean_output_text(result.split(delimiter)[-1])
                return _ensure_complete_sentence(parsed, max_completion_tokens=180)
        return _ensure_complete_sentence(_clean_output_text(result), max_completion_tokens=180)
    except Exception as e:
        print(f"Error generating summary for {section_name}: {e}")
        return f"[Error generating summary: {str(e)[:100]}]"


def generate_bluf(all_summaries: str, company_name: str = "the company") -> str:
    if not all_summaries or len(all_summaries.strip()) < 50:
        return "[Insufficient data for BLUF generation]"
    prompt, bluf_max_tokens = build_bluf_prompt(all_summaries, company_name)
    try:
        result = _run_inference(prompt, max_new_tokens=bluf_max_tokens)
        bluf_text = _clean_output_text(result.split("Investment Decision:")[-1])
        return _ensure_complete_sentence(bluf_text, max_completion_tokens=220)
    except Exception as e:
        print(f"Error generating BLUF: {e}")
        return f"[Error generating BLUF: {str(e)[:100]}]"


def generate_narrative(all_summaries: str, company_name: str = "the company") -> str:
    if not all_summaries or len(all_summaries.strip()) < 50:
        return "[Insufficient data for narrative generation]"
    prompt, narrative_max_tokens = build_narrative_prompt(all_summaries, company_name)
    try:
        result = _run_inference(prompt, max_new_tokens=narrative_max_tokens)
        parsed = _clean_output_text(result.split("The Story:")[-1])
        return _ensure_complete_sentence(parsed, max_completion_tokens=220)
    except Exception as e:
        print(f"Error generating narrative: {e}")
        return f"[Error generating narrative: {str(e)[:100]}]"


# ── PDF report builder ────────────────────────────────────────────────────────

def _build_styles():
    base   = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=28, leading=34, textColor=colors.HexColor("#1F3864"),
        spaceAfter=6, alignment=TA_CENTER,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=13, leading=18, textColor=colors.HexColor("#444444"),
        spaceAfter=4, alignment=TA_CENTER,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", parent=base["Normal"],
        fontSize=10, textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading", parent=base["Heading1"],
        fontSize=14, leading=18, textColor=colors.white,
        backColor=colors.HexColor("#1F3864"),
        spaceBefore=14, spaceAfter=8,
        leftIndent=-6, rightIndent=-6,
        borderPad=6,
    )
    styles["sub_heading"] = ParagraphStyle(
        "sub_heading", parent=base["Heading2"],
        fontSize=11, leading=14, textColor=colors.HexColor("#1F3864"),
        spaceBefore=10, spaceAfter=4,
        borderWidth=0, borderColor=colors.HexColor("#1F3864"),
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=9.5, leading=14, textColor=colors.HexColor("#222222"),
        spaceAfter=6, alignment=TA_JUSTIFY,
    )
    styles["bluf_box"] = ParagraphStyle(
        "bluf_box", parent=base["Normal"],
        fontSize=11, leading=16, textColor=colors.HexColor("#1F3864"),
        backColor=colors.HexColor("#D6E4F0"),
        spaceBefore=6, spaceAfter=10,
        leftIndent=12, rightIndent=12,
        borderPad=10,
        borderWidth=1, borderColor=colors.HexColor("#1F3864"),
    )
    styles["footer"] = ParagraphStyle(
        "footer", parent=base["Normal"],
        fontSize=7.5, textColor=colors.HexColor("#AAAAAA"),
        alignment=TA_CENTER,
    )
    return styles


def _wrap_text(text: str, width: int = 90) -> str:
    """Wrap long AI-generated text to avoid overflow."""
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            lines.append(textwrap.fill(paragraph.strip(), width=width))
        else:
            lines.append("")
    return "\n".join(lines)


def _safe_para(text: str, style) -> Paragraph:
    """Create a Paragraph, escaping problematic XML characters."""
    safe = (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
    return Paragraph(safe, style)


def build_pdf_report(
    company_name: str,
    bluf: str,
    narrative: str,
    summaries: dict,           # {section_label: summary_text}
    financial_table_rows: list,# list of [label, val1, val2, ...] rows for key metrics
    output_path: str,
    periods: Optional[list] = None,
):
    """
    Build the PDF investment report.

    Args:
        company_name:         Company name string
        bluf:                 Bottom-Line-Up-Front sentence(s)
        narrative:            Investor narrative paragraph
        summaries:            Dict of section_label → AI summary text
        financial_table_rows: List of rows for the key metrics table
        output_path:          Where to write the PDF
        periods:              List of fiscal year period labels e.g. ["FY2023","FY2022"]
    """
    doc    = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.9*inch,   bottomMargin=0.9*inch,
    )
    styles = _build_styles()
    story  = []
    now    = datetime.now().strftime("%B %d, %Y")

    # ── Cover page ────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2 * inch))
    story.append(_safe_para(f"{company_name}", styles["cover_title"]))
    story.append(_safe_para("10-K Investment Research Report", styles["cover_sub"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor("#1F3864"),
                              hAlign="CENTER"))
    story.append(Spacer(1, 0.2 * inch))
    story.append(_safe_para(f"Generated: {now}", styles["cover_meta"]))
    story.append(_safe_para("Source: SEC 10-K Filing  |  AI Analysis: Anthropic API",
                             styles["cover_meta"]))
    story.append(Spacer(1, 0.5 * inch))
    story.append(_safe_para(
        "DISCLAIMER: This report is generated by an AI system for informational purposes only. "
        "It does not constitute investment advice. Always consult a qualified financial advisor "
        "before making investment decisions.",
        ParagraphStyle("disc", parent=styles["footer"], fontSize=8,
                       textColor=colors.HexColor("#888888"), alignment=TA_CENTER)
    ))
    story.append(PageBreak())

    # ── BLUF box ──────────────────────────────────────────────────────────
    story.append(_safe_para("⚡ Bottom Line", styles["section_heading"]))
    story.append(Spacer(1, 4))
    story.append(_safe_para(_wrap_text(bluf), styles["bluf_box"]))
    story.append(Spacer(1, 10))

    # ── Investment Narrative ──────────────────────────────────────────────
    story.append(_safe_para("The Investment Story", styles["section_heading"]))
    story.append(Spacer(1, 4))
    story.append(_safe_para(_wrap_text(narrative), styles["body"]))
    story.append(Spacer(1, 10))

    # ── Key Financial Metrics table ───────────────────────────────────────
    if financial_table_rows:
        story.append(_safe_para("Key Financial Metrics", styles["section_heading"]))
        story.append(Spacer(1, 4))

        period_headers = periods or []
        col_headers = ["Metric"] + period_headers
        table_data  = [col_headers] + financial_table_rows

        col_count  = len(col_headers)
        label_w    = 2.5 * inch
        val_w      = (6.3 * inch - label_w) / max(col_count - 1, 1)
        col_widths = [label_w] + [val_w] * (col_count - 1)

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#1F3864")),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0),  9),
            ("ALIGN",       (1, 0), (-1, 0),  "RIGHT"),
            ("ALIGN",       (0, 0), (0, 0),   "LEFT"),
            ("BOTTOMPADDING",(0,0), (-1, 0),  6),
            ("TOPPADDING",  (0, 0), (-1, 0),  6),
            # Data rows
            ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 1), (-1, -1), 9),
            ("ALIGN",       (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN",       (0, 1), (0, -1),  "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F0F5FB")]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("TOPPADDING",  (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING",(0,1), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 14))

    # ── Section summaries ─────────────────────────────────────────────────
    section_labels = {
        "businessOverview.txt":    "Business Overview (Item 1)",
        "riskFactors.txt":         "Risk Factors (Item 1A)",
        "managementDiscussion.txt":"Management Discussion & Analysis (Item 7)",
        "incomeStatements.txt":    "Financial Statements (Item 8)",
    }

    for filename, label in section_labels.items():
        summary = summaries.get(filename, "")
        if not summary or summary.startswith("["):
            continue
        story.append(_safe_para(label, styles["section_heading"]))
        story.append(Spacer(1, 4))
        story.append(_safe_para(_wrap_text(summary), styles["body"]))
        story.append(Spacer(1, 10))

    # ── Footer note ───────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 6))
    story.append(_safe_para(
        f"Report generated on {now} using Anthropic API. "
        "Content is derived from SEC 10-K filings and is for informational purposes only.",
        styles["footer"]
    ))

    doc.build(story)
    print(f"✓ PDF report saved: {output_path}")
    return output_path


# ── Financial table helper ────────────────────────────────────────────────────

def _format_value(val, is_pct=False):
    """Format a float for display in the PDF table."""
    if val is None:
        return "—"
    if is_pct:
        return f"{val * 100:.1f}%"
    # Values are stored as full dollars; display in millions
    millions = val / 1_000_000
    if abs(millions) >= 1000:
        return f"${millions/1000:,.1f}B"
    return f"${millions:,.0f}M"


def _build_financial_table_rows(model) -> tuple[list, list]:
    """
    Extract key metrics from the FinancialModel into table rows and period headers.
    Returns (rows, periods).
    """
    IS = model.income_statement
    CF = model.cash_flow
    BS = model.balance_sheet

    periods = IS.periods or CF.periods or BS.periods or []

    def get_is(name):  return IS.line_items.get(name, [])
    def get_cf(name):  return CF.line_items.get(name, [])
    def get_bs(name):  return BS.line_items.get(name, [])

    def row(label, values, is_pct=False):
        formatted = [_format_value(v, is_pct) for v in (values or [])]
        return [label] + formatted

    metrics = [
        # Income Statement
        ("── Income Statement", None, False),
        row("Revenue",            get_is("Revenue")),
        row("Gross Profit",       get_is("Gross Profit")),
        row("Gross Margin %",     get_is("Gross Margin %"),    True),
        row("EBITDA",             get_is("EBITDA")),
        row("EBITDA Margin %",    get_is("EBITDA Margin %"),   True),
        row("Operating Income",   get_is("Operating Income")),
        row("Operating Margin %", get_is("Operating Margin %"),True),
        row("Net Income",         get_is("Net Income")),
        row("Net Margin %",       get_is("Net Margin %"),      True),
        row("EPS (Diluted)",      get_is("EPS (Diluted)")),
        # Cash Flow
        ("── Cash Flow", None, False),
        row("Operating Cash Flow",get_cf("Operating Cash Flow")),
        row("Capex",              get_cf("Capex")),
        row("Free Cash Flow",     get_cf("Free Cash Flow")),
        row("FCF Margin %",       get_cf("FCF Margin %"),      True),
        # Balance Sheet
        ("── Balance Sheet", None, False),
        row("Cash & Equivalents", get_bs("Cash & Equivalents")),
        row("Total Assets",       get_bs("Total Assets")),
        row("Total Debt",         get_bs("Long-Term Debt")),
        row("Total Equity",       get_bs("Total Equity")),
    ]

    # Filter: keep rows with at least one real value; keep section headers
    rows = []
    for item in metrics:
        if isinstance(item, tuple) and item[1] is None:
            # Section header row
            label = item[0]
            rows.append([label] + [""] * len(periods))
        else:
            # Data row — only include if at least one value populated
            if any(v != "—" for v in item[1:]):
                rows.append(list(item))

    return rows, periods


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(pdf_path: str, company_name: str = "", output_path: str = ""):
    """
    Full pipeline: extract → summarize → build PDF report.

    Args:
        pdf_path:     Path to the 10-K PDF
        company_name: Optional override; derived from filename if blank
        output_path:  Where to save the report PDF.
                      Defaults to same directory as input PDF.
    """
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    # ── Step 1: Extract sections ──────────────────────────────────────────
    result       = extract_10k_sections(pdf_path, company_name=company_name)
    sections     = result["sections"]       # {filename: text}
    company_name = result["company_name"]
    output_folder= result["output_folder"]

    # ── Step 2: Load financial model (if extractor ran) ───────────────────
    financial_table_rows = []
    periods              = []
    helper_path = os.path.join(os.path.dirname(__file__), "financial_model_extractor.py")
    if os.path.exists(helper_path):
        try:
            helper_spec = importlib.util.spec_from_file_location("financial_model_extractor", helper_path)
            if helper_spec and helper_spec.loader:
                helper_module = importlib.util.module_from_spec(helper_spec)
                helper_spec.loader.exec_module(helper_module)
                fin_model = helper_module.extract_financial_tables_structured(pdf_path)
                helper_module._compute_derived_metrics(fin_model)
                financial_table_rows, periods = _build_financial_table_rows(fin_model)
        except Exception as e:
            print(f"⚠ Could not load financial model for PDF table: {e}")

    # ── Step 3: Generate AI summaries ─────────────────────────────────────
    section_labels = {
        "businessOverview.txt":    "Business Overview",
        "riskFactors.txt":         "Risk Factors",
        "managementDiscussion.txt":"MD&A",
        "incomeStatements.txt":    "Financial Statements",
    }

    print("\nGenerating AI summaries...")
    summaries = {}
    for filename, label in section_labels.items():
        text = sections.get(filename, "")
        print(f"  Summarizing: {label}...")
        summaries[filename] = generate_summary(text, label)

    # ── Step 4: Generate BLUF and narrative ───────────────────────────────
    combined = "\n\n".join(
        f"=== {label} ===\n{summaries.get(filename, '')}"
        for filename, label in section_labels.items()
    )
    print("  Generating BLUF...")
    bluf      = generate_bluf(combined, company_name)
    print("  Generating narrative...")
    narrative = generate_narrative(combined, company_name)

    # ── Step 5: Build PDF report ──────────────────────────────────────────
    if not output_path:
        pdf_dir     = os.path.dirname(os.path.abspath(pdf_path))
        safe_name   = re.sub(r"[^\w\-]", "_", company_name)
        output_path = os.path.join(pdf_dir, f"{safe_name}_10K_Report.pdf")

    print(f"\nBuilding PDF report → {output_path}")
    build_pdf_report(
        company_name         = company_name,
        bluf                 = bluf,
        narrative            = narrative,
        summaries            = summaries,
        financial_table_rows = financial_table_rows,
        output_path          = output_path,
        periods              = periods,
    )

    print(f"\n{'='*60}")
    print(f"✓ Done!  Report: {output_path}")
    print(f"{'='*60}")
    return output_path


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 10k_reader.py <path_to_10k.pdf> [company_name] [output_report.pdf]")
        sys.exit(1)

    pdf_path     = sys.argv[1]
    company_name = sys.argv[2] if len(sys.argv) > 2 else ""
    output_path  = sys.argv[3] if len(sys.argv) > 3 else ""

    run(pdf_path, company_name, output_path)
