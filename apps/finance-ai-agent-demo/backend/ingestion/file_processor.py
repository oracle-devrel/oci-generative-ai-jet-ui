"""Extract text content from various file types."""

from pathlib import Path


class FileProcessor:
    """Extract text from PDF, DOCX, TXT, CSV, JSON files."""

    SUPPORTED_TYPES = {".pdf", ".txt", ".md", ".csv", ".json", ".docx"}

    def extract(self, filepath):
        """Extract text from a file. Returns raw text string."""
        ext = Path(filepath).suffix.lower()

        if ext == ".pdf":
            return self._extract_pdf(filepath)
        elif ext in (".txt", ".md"):
            return self._extract_text(filepath)
        elif ext == ".csv":
            return self._extract_csv(filepath)
        elif ext == ".json":
            return self._extract_json(filepath)
        elif ext == ".docx":
            return self._extract_docx(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, filepath):
        import pdfplumber

        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)

    def _extract_text(self, filepath):
        with open(filepath, encoding="utf-8") as f:
            return f.read()

    def _extract_csv(self, filepath):
        import csv

        lines = []
        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                line = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                lines.append(line)
        return "\n".join(lines)

    def _extract_json(self, filepath):
        import json

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)

    def _extract_docx(self, filepath):
        from docx import Document

        doc = Document(filepath)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
