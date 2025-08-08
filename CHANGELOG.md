# Changelog

All notable changes to this project will be documented in this file.

## [2025-08-08] - Critical Source Filtering Bug Fix

### Fixed

- **Source filtering in RAG queries completely broken**:
  - Fixed relative import error in `src/utils/embeddings.py` that was using `from ..core.logging` instead of `from core.logging`
  - This error prevented `extract_domain_from_url` from being called, causing all source metadata to be stored as null
  - Source filtering now works correctly for RAG queries and code searches
  - Affected functions: `perform_rag_query`, `search_code_examples`, all search operations with source filters

## [2025-08-08] - Modular Utility Functions Restoration

### Added

- **New utility modules** for better code organization:
  - `src/utils/code_analysis.py` - Functions for extracting and analyzing code blocks from markdown
  - `src/utils/summarization.py` - AI-powered content summarization utilities
  
- **Restored missing functions** from pre-refactoring backup:
  - `extract_code_blocks()` - Extract code blocks with language detection from markdown
  - `generate_code_example_summary()` - Generate AI summaries of code examples with context
  - `extract_source_summary()` - Create summaries of crawled sources using OpenAI
  - `generate_contextual_embedding()` - Generate contextual representations for chunks
  - `process_chunk_with_context()` - Process chunks with context for embeddings
  - `process_code_example()` - Wrapper for concurrent code processing

### Fixed

- **Critical security issues**:
  - Replaced deprecated `openai.api_key` global assignment with secure client instantiation pattern
  - Fixed potential information disclosure in error messages by using structured logging
  - Removed hardcoded embedding dimensions (1536) - now dynamically determined by model
  
- **Code quality improvements**:
  - Eliminated function duplication between `text_processing.py` and `code_analysis.py`
  - Replaced all print statements with proper logging using centralized logger
  - Fixed stub implementations that were causing silent failures
  
- **Import structure**:
  - Updated `src/utils/__init__.py` to properly export all utility functions
  - Fixed circular import potential in module structure
  - Ensured backward compatibility for all existing imports

### Technical Details

- **OpenAI Integration**: All API calls now use the modern `openai.OpenAI()` client pattern
- **Error Handling**: Comprehensive retry logic with exponential backoff for API calls
- **Model Support**: Dynamic embedding dimensions for multiple models:
  - `text-embedding-3-small`: 1536 dimensions
  - `text-embedding-3-large`: 3072 dimensions
  - `text-embedding-ada-002`: 1536 dimensions
- **Logging**: Migrated from stderr prints to structured logging via `core.logging.logger`

### Impact

- Restores functionality lost during the monolithic `src/utils.py` refactoring
- Fixes 20+ test failures related to missing utility functions
- Improves security posture by eliminating deprecated API patterns
- Maintains clean modular architecture with single responsibility principle

## [2025-08-07] - QdrantAdapter Parameter Name Consistency Fix

### Fixed

- Fixed parameter name inconsistency in QdrantAdapter causing "unexpected keyword argument 'filter_metadata'" errors
  - **Root Cause**: QdrantAdapter methods used `metadata_filter` while VectorDatabase protocol defined `filter_metadata`
  - **Files Updated**:
    - `src/database/qdrant_adapter.py`:
      - Line 288: `search()` method parameter changed from `metadata_filter` to `filter_metadata`
      - Line 319: `hybrid_search()` method parameter changed from `metadata_filter` to `filter_metadata`
      - Line 338: Internal call in `hybrid_search()` updated to use `filter_metadata`
      - Line 541: `search_code_examples()` method parameter changed from `metadata_filter` to `filter_metadata`
    - `src/services/validated_search.py` (line 220): Updated call to use `filter_metadata` parameter
    - `src/database/rag_queries.py` (line 176): Updated call to use `filter_metadata` parameter
  - **Impact**: Resolves runtime errors in semantic search, hybrid search, and code example search operations
  - **Validation**: All database adapters now consistently implement the VectorDatabase protocol interface

## [2025-08-07] - Neo4j Aggregation Warning Suppression

### Fixed

- Eliminated Neo4j aggregation warnings about null values in repository metadata queries
  - Implemented driver-level warning suppression using `NotificationMinimumSeverity.OFF` for Neo4j driver 5.21.0+
  - Added fallback to logging suppression for older Neo4j driver versions
  - Updated all 5 Neo4j driver initialization points across the codebase:
    - `src/knowledge_graph/queries.py` (line 65)
    - `knowledge_graphs/parse_repo_into_neo4j.py` (line 427)
    - `src/services/validated_search.py` (line 85)
    - `knowledge_graphs/query_knowledge_graph.py` (line 37)
    - `knowledge_graphs/knowledge_graph_validator.py` (line 127)
  - Fixed exception handling to properly catch both `ImportError` and `AttributeError`
  - Updated aggregation query in `src/knowledge_graph/repository.py` (line 354) to filter null files

### Technical Details

- Warning suppression is configured at Neo4j driver initialization
- Backward compatible with Neo4j driver versions < 5.21.0 via logging configuration
- No performance impact - warnings are suppressed, not the underlying aggregation
- Maintains full data integrity and calculation accuracy

## [2025-08-07] - Validated Search Parameter Fix

### Fixed

- Fixed parameter name mismatch in `src/services/validated_search.py` causing "unexpected keyword argument 'filter_metadata'" error
  - Changed `filter_metadata` to `metadata_filter` when calling `QdrantAdapter.search_code_examples()` (line 207)
  - This resolves the error that was preventing validated code search from working with source filters

## [2025-08-06] - Hallucination Detection Volume Mounting Fix

### Added

- Created `analysis_scripts/` directory structure for script analysis
  - `user_scripts/` - For user Python scripts
  - `test_scripts/` - For test scripts  
  - `validation_results/` - For storing analysis results
- Added Docker volume mounts in `docker-compose.dev.yml`:
  - `./analysis_scripts:/app/analysis_scripts:rw` - Script directories
  - `/tmp:/app/tmp_scripts:ro` - Temporary scripts (read-only)
- New helper tool `get_script_analysis_info()` to provide setup information
- Comprehensive documentation in README.md and CLAUDE.md

### Changed

- Enhanced `validate_script_path()` in `src/utils/validation.py`:
  - Added automatic path translation from host to container paths
  - Improved error messages with helpful guidance
- Updated hallucination detection tools in `src/tools.py`:
  - `check_ai_script_hallucinations` now uses container paths
  - `check_ai_script_hallucinations_enhanced` now uses container paths
- Updated `.gitignore` to exclude analysis scripts while keeping directory structure

### Fixed

- Resolved "Script not found" errors in hallucination detection tools
- Fixed path accessibility issues between host and Docker container
- Tools can now access scripts placed in designated directories

### Technical Details

- Path mapping: Host paths automatically translate to container paths
- Security: /tmp mount is read-only to prevent container writing to host
- Convenience: Scripts can be referenced with simple relative paths
