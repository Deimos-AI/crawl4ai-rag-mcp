"""Utility functions for the Crawl4AI MCP server."""

from .reranking import rerank_results
from .text_processing import (
    extract_section_info,
    smart_chunk_markdown,
)
from .url_helpers import extract_domain_from_url, is_sitemap, is_txt, normalize_url, parse_sitemap
from .validation import (
    validate_github_url,
    validate_neo4j_connection,
    validate_script_path,
)

# Import embedding functions from local embeddings module
from .embeddings import (
    add_documents_to_database,
    create_embedding,
    create_embeddings_batch,
    generate_contextual_embedding,
    process_chunk_with_context,
)

# Import code analysis functions
from .code_analysis import (
    extract_code_blocks,
    generate_code_example_summary,
)

# Import summarization functions
from .summarization import extract_source_summary


__all__ = [
    # Database and embedding functions
    "add_documents_to_database",
    "create_embedding",
    "create_embeddings_batch",
    "generate_contextual_embedding",
    "process_chunk_with_context",
    # Code analysis functions
    "extract_code_blocks",
    "generate_code_example_summary",
    "process_code_example",
    # Text processing functions
    "extract_section_info",
    "smart_chunk_markdown",
    # Summarization functions
    "extract_source_summary",
    # URL helpers
    "extract_domain_from_url",
    "is_sitemap",
    "is_txt",
    "normalize_url",
    "parse_sitemap",
    # Reranking
    "rerank_results",
    # Validation
    "validate_github_url",
    "validate_neo4j_connection",
    "validate_script_path",
]
