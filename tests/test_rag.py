from src.rag.ingest import DOCUMENT_INDEX, RAGIngestor
from src.rag.search import RAGSearchEngine


def test_rag_text_ingest_and_search():
    DOCUMENT_INDEX.clear()
    result = RAGIngestor().ingest_text(
        "贵州茅台 批价 稳定 合同负债 增长",
        company="600519",
        doc_type="note",
        source="unit-test",
    )
    assert result.success
    assert result.chunk_count == 1

    matches = RAGSearchEngine(relevance_threshold=0.1).search(
        "批价 合同负债", company="600519"
    )
    assert matches
    assert matches[0].company == "600519"
