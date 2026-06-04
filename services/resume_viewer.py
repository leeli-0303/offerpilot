"""Resume file text extraction for preview.

Supports TXT, PDF (via PyPDF2), and DOCX (via python-docx).
All extractors degrade gracefully when optional dependencies are missing.
"""

from pathlib import Path


def get_file_type(file_path: str) -> str:
    """Return the lowercase file extension without the dot.

    Returns:
        One of ``"txt"``, ``"pdf"``, ``"docx"``, or ``"unknown"``.
    """
    ext = Path(file_path).suffix.lower().lstrip(".")
    if ext in ("txt", "pdf", "docx"):
        return ext
    return "unknown"


def extract_text(file_path: str) -> str | None:
    """Extract readable text from a resume file.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        Extracted text as a string, or ``None`` if extraction is not
        supported / the file cannot be read.
    """
    fpath = Path(file_path)
    if not fpath.exists():
        return None

    file_type = get_file_type(file_path)

    if file_type == "txt":
        return _extract_txt(fpath)
    elif file_type == "pdf":
        return _extract_pdf(fpath)
    elif file_type == "docx":
        return _extract_docx(fpath)
    else:
        return None


# ── TXT ─────────────────────────────────────────────────────────────────

def _extract_txt(fpath: Path) -> str | None:
    try:
        return fpath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return fpath.read_text(encoding="gbk")
        except Exception:
            return None
    except Exception:
        return None


# ── PDF ─────────────────────────────────────────────────────────────────

def _extract_pdf(fpath: Path) -> str | None:
    """Extract text from a PDF using PyPDF2 (primary) or pdfplumber (fallback)."""
    text = _try_pypdf2(fpath)
    if text is not None:
        return text
    text = _try_pdfplumber(fpath)
    if text is not None:
        return text
    return None


def _try_pypdf2(fpath: Path) -> str | None:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(str(fpath))
        parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
        return "\n\n".join(parts) if parts else None
    except Exception:
        return None


def _try_pdfplumber(fpath: Path) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        parts: list[str] = []
        with pdfplumber.open(str(fpath)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    parts.append(page_text)
        return "\n\n".join(parts) if parts else None
    except Exception:
        return None


# ── DOCX ────────────────────────────────────────────────────────────────

def _extract_docx(fpath: Path) -> str | None:
    try:
        from docx import Document
    except ImportError:
        return None
    try:
        doc = Document(str(fpath))
        parts: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        return "\n".join(parts) if parts else None
    except Exception:
        return None


def preview_status(file_path: str) -> dict:
    """Return a status dict describing whether preview is available.

    Returns:
        ``{"ok": bool, "text": str | None, "reason": str}``
        - *ok*: ``True`` when text was successfully extracted.
        - *text*: the extracted text (may be ``None`` when *ok* is ``False``).
        - *reason*: human-readable explanation when *ok* is ``False``.
    """
    fpath = Path(file_path)
    if not fpath.exists():
        return {"ok": False, "text": None, "reason": "文件不存在或已移动"}

    file_type = get_file_type(file_path)
    if file_type == "unknown":
        return {"ok": False, "text": None,
                "reason": f"暂不支持 {fpath.suffix} 格式的在线预览"}

    # Check dependency availability before attempting extraction
    if file_type == "pdf":
        has_pypdf = _library_available("PyPDF2")
        has_plumber = _library_available("pdfplumber")
        if not has_pypdf and not has_plumber:
            return {
                "ok": False, "text": None,
                "reason": "PDF 预览需要安装 PyPDF2 或 pdfplumber。"
                          "请在终端执行：pip install PyPDF2",
            }
    elif file_type == "docx":
        if not _library_available("docx"):
            return {
                "ok": False, "text": None,
                "reason": "DOCX 预览需要安装 python-docx。"
                          "请在终端执行：pip install python-docx",
            }

    text = extract_text(str(fpath))
    if text is None:
        return {
            "ok": False, "text": None,
            "reason": "无法从文件中提取文本，文件可能已损坏或为扫描版 PDF。"
                      "请下载后在本地查看。",
        }
    return {"ok": True, "text": text, "reason": ""}


def _library_available(import_name: str) -> bool:
    """Check whether a Python library can be imported."""
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False
