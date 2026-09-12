"""
InvoiceIQ — Core Module: Document Field Extractor
Extracts structured fields from invoice/receipt images and PDFs.

Pipeline (in order):
1. Native PDF text (PyMuPDF) when available
2. Ollama vision model (if installed)
3. Florence-2 OCR (if loaded)
4. Tesseract OCR on images
5. Demo schema only as last resort when no text can be read

DEMO_MODE no longer skips real extraction — it only enables the final fallback.
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

try:
    import ollama

    USE_OLLAMA = True
except ImportError:
    USE_OLLAMA = False

try:
    from transformers import AutoModelForCausalLM, AutoProcessor

    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


@dataclass
class ExtractedField:
    field_name: str
    value: str
    confidence: float
    category: str


@dataclass
class ExtractionResult:
    document_type: str
    fields: List[ExtractedField]
    line_items: List[Dict]
    raw_text: str
    total_amount: Optional[float]
    mode: str = "live"


EXTRACTION_PROMPT = """You are an invoice data extractor. Analyze this invoice image and extract ALL of the following fields in JSON format:

{
  "document_type": "invoice" or "receipt" or "purchase_order",
  "vendor_name": "",
  "vendor_address": "",
  "invoice_number": "",
  "invoice_date": "",
  "due_date": "",
  "bill_to": "",
  "subtotal": 0.00,
  "tax": 0.00,
  "total_amount": 0.00,
  "currency": "USD",
  "payment_terms": "",
  "line_items": [
    {"description": "", "quantity": 0, "unit_price": 0.00, "amount": 0.00}
  ]
}

Return ONLY valid JSON, no other text."""


def _demo_flag() -> bool:
    return DEMO_MODE or os.getenv("FORCE_DEMO", "0") == "1"


class InvoiceExtractor:
    """Extract structured data from invoice images/PDFs."""

    def __init__(self, model_name: str = "microsoft/Florence-2-base"):
        self.model = None
        self.processor = None
        self.model_name = model_name
        # demo flag only controls last-resort fallback, not skipping OCR
        self.demo = _demo_flag()
        self.tesseract_ok = self._probe_tesseract()

        if HF_AVAILABLE and os.getenv("LOAD_FLORENCE", "0") == "1":
            try:
                import torch
                from PIL import Image  # noqa: F401

                self.processor = AutoProcessor.from_pretrained(
                    model_name, trust_remote_code=True
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float16
                    if torch.cuda.is_available()
                    else torch.float32,
                )
                if torch.cuda.is_available():
                    self.model = self.model.cuda()
                self.model.eval()
            except Exception as exc:  # noqa: BLE001
                print(f"[InvoiceIQ] HF model load failed: {exc}")

    @staticmethod
    def _probe_tesseract() -> bool:
        try:
            import pytesseract
            from PIL import Image

            pytesseract.get_tesseract_version()
            return True
        except Exception:  # noqa: BLE001
            return False

    def _image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def _extract_with_ollama(self, image_path: str) -> dict:
        if not USE_OLLAMA:
            return {}
        resp = ollama.chat(
            model=os.getenv("OLLAMA_VISION_MODEL", "llava:7b"),
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [image_path],
                }
            ],
        )
        text = resp["message"]["content"]
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}

    def _extract_with_florence(self, image_path: str) -> dict:
        if self.model is None or self.processor is None:
            return {}
        import torch
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(text="<OCR>", images=image, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            ids = self.model.generate(
                **inputs, max_new_tokens=1024, num_beams=3, early_stopping=True
            )

        ocr_text = self.processor.batch_decode(ids, skip_special_tokens=True)[0]
        return self._parse_ocr_to_fields(ocr_text)

    def _extract_pdf_text(self, pdf_path: str) -> dict:
        """Extract selectable text from a PDF (no OCR needed)."""
        try:
            import fitz

            doc = fitz.open(pdf_path)
            parts = []
            for page in doc:
                parts.append(page.get_text("text"))
            text = "\n".join(parts).strip()
            if len(text) < 20:
                return {}
            return self._parse_ocr_to_fields(text)
        except Exception as exc:  # noqa: BLE001
            print(f"[InvoiceIQ] PDF text extract failed: {exc}")
            return {}

    def _extract_with_ocr_fallback(self, image_path: str) -> dict:
        text = self._ocr_image(image_path)
        if not text.strip():
            return {}
        return self._parse_ocr_to_fields(text)

    def _ocr_image(self, image_path: str) -> str:
        try:
            import pytesseract
            from PIL import Image, ImageOps, ImageFilter

            image = Image.open(image_path).convert("RGB")
            # Light preprocessing improves OCR on UI-generated / scanned invoices
            gray = ImageOps.grayscale(image)
            gray = ImageOps.autocontrast(gray)
            gray = gray.filter(ImageFilter.SHARPEN)
            # Upscale small images
            if min(gray.size) < 900:
                scale = 2
                gray = gray.resize((gray.width * scale, gray.height * scale))

            config = "--psm 6"
            text = pytesseract.image_to_string(gray, config=config)
            if len(text.strip()) < 20:
                text = pytesseract.image_to_string(image, config="--psm 4")
            return text or ""
        except Exception as exc:  # noqa: BLE001
            print(f"[InvoiceIQ] OCR failed: {exc}")
            return ""

    def _demo_extract(self, image_path: str) -> dict:
        """Last-resort synthetic result when no text could be read."""
        name = os.path.basename(image_path)
        return {
            "document_type": "invoice",
            "vendor_name": "Extraction unavailable",
            "vendor_address": "",
            "invoice_number": "",
            "invoice_date": "",
            "due_date": "",
            "bill_to": "",
            "subtotal": "",
            "tax": "",
            "total_amount": "",
            "currency": "",
            "payment_terms": "",
            "line_items": [],
            "raw_text": (
                f"[FALLBACK] Could not read text from {name}. "
                "Install Tesseract OCR (`brew install tesseract`) or use a text-based PDF. "
                f"tesseract_ok={self.tesseract_ok}"
            ),
        }

    def _parse_amount(self, value: str) -> Optional[float]:
        try:
            cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def _parse_ocr_to_fields(self, text: str) -> dict:
        fields: dict = {
            "raw_text": text,
            "document_type": "invoice",
            "line_items": [],
        }
        if not text or len(text.strip()) < 10:
            return {}

        # Normalize currency glyphs for matching
        norm = (
            text.replace("₹", "INR ")
            .replace("Rs.", "INR ")
            .replace("Rs ", "INR ")
            .replace("$", "USD ")
            .replace("€", "EUR ")
            .replace("£", "GBP ")
        )

        patterns = {
            # Prefer INV-#### first; any other invoice id must include a digit
            # (avoids capturing labels like "Vendor" from nearby lines)
            "invoice_number": [
                r"\b(INV[- ]?\d{3,})\b",
                r"(?:invoice\s*(?:number|no\.?|#))\s*[:.#-]?\s*((?=.*\d)[A-Z0-9][A-Z0-9/-]{2,})",
                r"(?:inv\.?\s*(?:no\.?|#)?)\s*[:.#-]?\s*((?=.*\d)[A-Z0-9][A-Z0-9/-]{2,})",
            ],
            "invoice_date": [
                r"(?:invoice\s*)?date\s*[:\-]?\s*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})",
                r"(?:invoice\s*)?date\s*[:\-]?\s*(\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2})",
                r"(?:invoice\s*)?date\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})",
            ],
            "due_date": [
                r"(?:due\s*date|payment\s*due|due\s*on)\s*[:\-]?\s*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})",
                r"(?:due\s*date|payment\s*due)\s*[:\-]?\s*(\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2})",
                r"(?:due\s*date|payment\s*due)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})",
            ],
            "total_amount": [
                r"(?:grand\s*total|amount\s*due|total\s*amount|total\s*due|^total)\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*([\d,]+\.\d{2})",
                r"(?:grand\s*total|amount\s*due|total\s*amount|total)\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*([\d,]+)",
            ],
            "subtotal": [
                r"(?:sub\s*total|subtotal)\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*([\d,]+\.?\d*)",
            ],
            "tax": [
                r"(?:gst|vat|tax|cgst|sgst|igst)(?:\s*\([^)]*\))?\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*([\d,]+\.?\d*)",
            ],
            "payment_terms": [
                r"(?:payment\s*terms|terms)\s*[:\-]?\s*(Net\s*\d+|Due\s*on\s*receipt|[A-Za-z0-9 ]{3,40})",
            ],
            "currency": [
                r"\b(INR|USD|EUR|GBP|CAD|AUD)\b",
            ],
            "bill_to": [
                r"(?:bill\s*to|billed\s*to|customer|client)\s*[:\-]?\s*(.+)",
            ],
            "vendor_name": [
                r"(?:vendor|from|seller|supplier|company)\s*[:\-]?\s*(.+)",
            ],
            "vendor_address": [
                r"(?:address|vendor\s*address)\s*[:\-]?\s*(.+)",
            ],
        }

        banned_inv = {
            "INVOICE",
            "DATE",
            "NUMBER",
            "NO",
            "VENDOR",
            "ADDRESS",
            "TOTAL",
            "AMOUNT",
            "BILL",
            "DUE",
        }

        for field, pats in patterns.items():
            for pattern in pats:
                match = re.search(pattern, norm, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    if field == "invoice_number" and value.upper() in banned_inv:
                        continue
                    if field == "invoice_number" and not re.search(
                        r"\d", value
                    ):  # must contain a digit
                        continue
                    fields[field] = value[:120]
                    break

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Prefer a real company-looking first line if vendor missing
        if "vendor_name" not in fields and lines:
            for line in lines[:8]:
                if re.search(r"invoice", line, re.I):
                    continue
                if len(line) >= 3:
                    fields["vendor_name"] = line[:120]
                    break

        # Currency inference from symbols in original text
        if "currency" not in fields:
            if "₹" in text or re.search(r"\bINR\b", text, re.I):
                fields["currency"] = "INR"
            elif "$" in text or re.search(r"\bUSD\b", text, re.I):
                fields["currency"] = "USD"

        # Line items: description + trailing amount
        item_re = re.compile(
            r"^(.{8,80}?)\s+(\d+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$"
        )
        alt_item_re = re.compile(r"^(.{8,80}?)\s+([\d,]+\.\d{2})$")
        skip = re.compile(
            r"^(description|qty|quantity|unit|amount|subtotal|total|tax|gst|invoice|date|due|vendor|bill)",
            re.I,
        )
        for line in lines:
            if skip.search(line):
                continue
            m = item_re.match(line)
            if m:
                fields["line_items"].append(
                    {
                        "description": m.group(1).strip(),
                        "quantity": float(m.group(2)),
                        "unit_price": float(m.group(3).replace(",", "")),
                        "amount": float(m.group(4).replace(",", "")),
                    }
                )
                continue
            m2 = alt_item_re.match(line)
            if m2 and not re.search(r"total|tax|subtotal|gst|due", m2.group(1), re.I):
                amt = float(m2.group(2).replace(",", ""))
                if amt >= 1:
                    fields["line_items"].append(
                        {
                            "description": m2.group(1).strip(),
                            "quantity": 1,
                            "unit_price": amt,
                            "amount": amt,
                        }
                    )

        return fields

    def _field_count(self, raw: dict) -> int:
        keys = [
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "due_date",
            "total_amount",
            "subtotal",
            "tax",
            "bill_to",
        ]
        return sum(1 for k in keys if raw.get(k) not in (None, "", []))

    def _to_result(self, raw_data: dict, mode: str) -> ExtractionResult:
        fields: List[ExtractedField] = []
        field_mapping = {
            "vendor_name": ("Vendor Name", "header"),
            "vendor_address": ("Vendor Address", "header"),
            "invoice_number": ("Invoice Number", "header"),
            "invoice_date": ("Invoice Date", "header"),
            "due_date": ("Due Date", "header"),
            "bill_to": ("Bill To", "header"),
            "subtotal": ("Subtotal", "financial"),
            "tax": ("Tax", "financial"),
            "total_amount": ("Total Amount", "financial"),
            "currency": ("Currency", "metadata"),
            "payment_terms": ("Payment Terms", "metadata"),
        }

        conf_base = 0.7 if mode == "ocr" else (0.55 if mode == "fallback" else 0.85)

        for key, (display_name, category) in field_mapping.items():
            value = raw_data.get(key, "")
            if value != "" and value is not None:
                fields.append(
                    ExtractedField(
                        field_name=display_name,
                        value=str(value),
                        confidence=round(conf_base, 2),
                        category=category,
                    )
                )

        # Surface OCR text snippet for debugging in UI
        raw_text = raw_data.get("raw_text", "") or ""
        if raw_text and mode in {"ocr", "pdf", "fallback"}:
            preview = raw_text.strip().replace("\n", " ")[:240]
            if preview:
                fields.append(
                    ExtractedField(
                        field_name="OCR Preview",
                        value=preview,
                        confidence=0.5,
                        category="metadata",
                    )
                )

        line_items = raw_data.get("line_items", []) or []
        total = None
        try:
            total = float(str(raw_data.get("total_amount", "")).replace(",", ""))
        except (ValueError, TypeError):
            total = self._parse_amount(str(raw_data.get("total_amount", "")))

        return ExtractionResult(
            document_type=raw_data.get("document_type", "invoice"),
            fields=fields,
            line_items=line_items,
            raw_text=raw_text,
            total_amount=total,
            mode=mode,
        )

    def extract(self, image_path: str, pdf_path: Optional[str] = None) -> ExtractionResult:
        """
        Extract fields from an image path, optionally using original PDF text first.
        """
        candidates: List[Tuple[str, dict]] = []

        # 1) Native PDF text
        if pdf_path and pdf_path.lower().endswith(".pdf"):
            pdf_data = self._extract_pdf_text(pdf_path)
            if self._field_count(pdf_data) >= 2:
                return self._to_result(pdf_data, mode="pdf")
            if pdf_data:
                candidates.append(("pdf", pdf_data))

        # 2) Ollama vision
        if USE_OLLAMA:
            try:
                ollama_data = self._extract_with_ollama(image_path)
                if self._field_count(ollama_data) >= 2:
                    return self._to_result(ollama_data, mode="vlm")
                if ollama_data:
                    candidates.append(("vlm", ollama_data))
            except Exception as exc:  # noqa: BLE001
                print(f"[InvoiceIQ] Ollama extract failed: {exc}")

        # 3) Florence
        if self.model is not None:
            try:
                flor = self._extract_with_florence(image_path)
                if self._field_count(flor) >= 2:
                    return self._to_result(flor, mode="vlm")
                if flor:
                    candidates.append(("vlm", flor))
            except Exception as exc:  # noqa: BLE001
                print(f"[InvoiceIQ] Florence extract failed: {exc}")

        # 4) Tesseract OCR
        ocr_data = self._extract_with_ocr_fallback(image_path)
        if self._field_count(ocr_data) >= 1:
            return self._to_result(ocr_data, mode="ocr")
        if ocr_data:
            candidates.append(("ocr", ocr_data))

        # Prefer best partial candidate over fake demo numbers
        if candidates:
            best = max(candidates, key=lambda c: self._field_count(c[1]))
            return self._to_result(best[1], mode=best[0])

        # 5) Explicit fallback (empty-ish) — only when nothing readable
        return self._to_result(self._demo_extract(image_path), mode="fallback")
