import logging
from pathlib import Path
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

DOCUMENT_INDEX: list[dict] = []

@dataclass
class IngestResult:
    file_name: str
    company: str
    doc_type: str
    chunk_count: int
    success: bool
    error: str = ""

class RAGIngestor:
    """Ingest PDFs/documents into vector store for evidence retrieval."""

    def __init__(self, embedding_model: str = "BAAI/bge-m3"):
        self._embedding_model = embedding_model
        self._initialized = False
        logger.info(f"RAGIngestor created with model: {embedding_model}")

    def _ensure_initialized(self):
        """Lazy init to avoid import errors when dependencies missing."""
        if self._initialized:
            return
        try:
            # These will be connected when full dependencies are available
            self._initialized = True
        except ImportError as e:
            logger.warning(f"RAG dependencies not fully installed: {e}")

    def ingest_pdf(self, file_path: str | Path, company: str, doc_type: str = "annual_report") -> IngestResult:
        """Ingest a PDF document.

        Args:
            file_path: Path to PDF file
            company: Company ticker this document belongs to
            doc_type: Type (annual_report, earnings_call, research_report, announcement)

        Returns:
            IngestResult with chunk count and status.
        """
        path = Path(file_path)
        if not path.exists():
            return IngestResult(file_name=path.name, company=company, doc_type=doc_type,
                              chunk_count=0, success=False, error=f"File not found: {path}")

        logger.info(f"Ingesting {path.name} for {company} ({doc_type})")

        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return IngestResult(
                file_name=path.name,
                company=company,
                doc_type=doc_type,
                chunk_count=0,
                success=False,
                error="pypdf is required for PDF ingestion",
            )
        except Exception as exc:
            return IngestResult(
                file_name=path.name,
                company=company,
                doc_type=doc_type,
                chunk_count=0,
                success=False,
                error=str(exc),
            )
        return self.ingest_text(text, company, doc_type, source=str(path))

    def _chunk_text(self, text: str, max_chars: int = 1200) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= max_chars:
                current = f"{current}\n{paragraph}".strip()
            else:
                if current:
                    chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks or [text[:max_chars]]
        return IngestResult(
            file_name=path.name, company=company, doc_type=doc_type,
            chunk_count=0, success=True,
            error="Placeholder: full LlamaIndex pipeline pending dependency setup"
        )

    def ingest_text(self, text: str, company: str, doc_type: str, source: str = "") -> IngestResult:
        """Ingest raw text content."""
        if not text.strip():
            return IngestResult(file_name=source, company=company, doc_type=doc_type,
                              chunk_count=0, success=False, error="Empty text")

        logger.info(f"Ingesting text ({len(text)} chars) for {company}")
        chunks = self._chunk_text(text)
        for idx, chunk in enumerate(chunks):
            DOCUMENT_INDEX.append(
                {
                    "content": chunk,
                    "company": company,
                    "doc_type": doc_type,
                    "source": source,
                    "chunk_id": idx,
                    "embedding_model": self._embedding_model,
                }
            )
        return IngestResult(
            file_name=source, company=company, doc_type=doc_type,
            chunk_count=len(chunks), success=True,
        )
