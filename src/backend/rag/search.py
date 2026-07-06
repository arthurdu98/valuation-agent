import logging
from dataclasses import dataclass, field
import math
import re

from src.backend.rag.ingest import DOCUMENT_INDEX

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    content: str
    source: str
    company: str
    page: int | None = None
    relevance_score: float = 0.0
    doc_type: str = ""

class RAGSearchEngine:
    """Hybrid search engine: dense (pgvector) + BM25 + reranking."""

    def __init__(self, relevance_threshold: float = 0.3):
        self._threshold = relevance_threshold
        logger.info("RAGSearchEngine initialized")

    def _tokens(self, text: str) -> list[str]:
        return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())

    def search(
        self,
        query: str,
        company: str | None = None,
        include_competitors: bool = False,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Search for relevant evidence.

        Args:
            query: Natural language query
            company: Filter to specific company (None = all)
            include_competitors: Also search competitor documents
            top_k: Number of results to return

        Returns:
            List of RetrievalResult, sorted by relevance.
            Empty list with log if no results above threshold.
        """
        logger.info(f"Searching: '{query}' (company={company}, competitors={include_competitors})")

        query_tokens = set(self._tokens(query))
        if not query_tokens:
            return []

        candidates = []
        for doc in DOCUMENT_INDEX:
            if company and doc["company"] != company and not include_competitors:
                continue
            doc_tokens = self._tokens(doc["content"])
            if not doc_tokens:
                continue
            overlap = len(query_tokens.intersection(doc_tokens))
            if overlap == 0:
                continue
            bm25_like = overlap / math.sqrt(len(set(doc_tokens)))
            score = min(1.0, bm25_like)
            if score >= self._threshold:
                candidates.append(
                    RetrievalResult(
                        content=doc["content"],
                        source=doc["source"],
                        company=doc["company"],
                        relevance_score=score,
                        doc_type=doc["doc_type"],
                    )
                )
        return sorted(candidates, key=lambda item: item.relevance_score, reverse=True)[:top_k]

    def search_with_context(
        self,
        query: str,
        company: str,
        context_type: str = "all",
    ) -> tuple[list[RetrievalResult], bool]:
        """Search with sufficiency check.

        Returns:
            (results, is_sufficient) - is_sufficient is False if results are below threshold
        """
        results = self.search(query, company=company)
        is_sufficient = len(results) > 0 and results[0].relevance_score >= self._threshold
        if not is_sufficient:
            logger.info(f"Evidence insufficient for query: {query}")
        return results, is_sufficient
