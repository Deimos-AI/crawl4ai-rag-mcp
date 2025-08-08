"""Embedding generation utilities using OpenAI."""

import os
import sys
import time
from typing import Any

import openai



from concurrent.futures import ThreadPoolExecutor

def _get_embedding_dimensions(model: str) -> int:
    """
    Get the embedding dimensions for a given OpenAI model.
    
    Args:
        model: The embedding model name
        
    Returns:
        Number of dimensions for the embedding
    """
    # OpenAI embedding model dimensions
    model_dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    # Default to 1536 for unknown models (most common)
    return model_dimensions.get(model, 1536)

def create_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Create embeddings for multiple texts in a single API call.

    Args:
        texts: List of texts to create embeddings for

    Returns:
        List of embeddings (each embedding is a list of floats)
    """
    from core.logging import logger
    
    if not texts:
        return []

    max_retries = 3
    retry_delay = 1.0  # Start with 1 second delay
    
    # Use the embedding model from environment or default
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    for retry in range(max_retries):
        try:
            # Create OpenAI client instance
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = client.embeddings.create(
                model=model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if retry < max_retries - 1:
                logger.error(
                    "Error creating batch embeddings (attempt %d/%d): %s",
                    retry + 1, max_retries, str(e)
                )
                logger.info("Retrying in %s seconds...", retry_delay)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(
                    "Failed to create batch embeddings after %d attempts: %s",
                    max_retries, str(e)
                )
                # Try creating embeddings one by one as fallback
                logger.info("Attempting to create embeddings individually...")
                embeddings = []
                successful_count = 0

                for i, text in enumerate(texts):
                    try:
                        individual_response = client.embeddings.create(
                            model=model, input=[text],
                        )
                        embeddings.append(individual_response.data[0].embedding)
                        successful_count += 1
                    except Exception as individual_error:
                        logger.error(
                            "Failed to create embedding for text %d: %s",
                            i, str(individual_error)
                        )
                        # Add zero embedding as fallback
                        dimensions = _get_embedding_dimensions(model)
                        embeddings.append([0.0] * dimensions)

                logger.info(
                    "Successfully created %d/%d embeddings individually",
                    successful_count, len(texts)
                )
                return embeddings


def create_embedding(text: str) -> list[float]:
    """
    Create an embedding for a single text using OpenAI's API.

    Args:
        text: Text to create an embedding for

    Returns:
        List of floats representing the embedding
    """
    from core.logging import logger
    
    try:
        embeddings = create_embeddings_batch([text])
        if embeddings:
            return embeddings[0]
        else:
            # Fallback with dynamic dimensions
            model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            dimensions = _get_embedding_dimensions(model)
            return [0.0] * dimensions
    except Exception as e:
        logger.error("Error creating embedding: %s", str(e))
        # Return empty embedding with dynamic dimensions
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        dimensions = _get_embedding_dimensions(model)
        return [0.0] * dimensions


def generate_contextual_embedding(
    chunk: str, full_document: str, chunk_index: int = 0, total_chunks: int = 1
) -> str:
    """
    Generate contextual information for a chunk within a document to improve retrieval.

    Args:
        chunk: The specific chunk of text to generate context for
        full_document: The complete document text
        chunk_index: Index of the current chunk (optional)
        total_chunks: Total number of chunks (optional)

    Returns:
        The contextual text that situates the chunk within the document
    """
    from core.logging import logger
    
    # Use environment variables for configuration with validation
    model_choice = os.getenv("CONTEXTUAL_EMBEDDING_MODEL", "gpt-4o-mini")
    
    # Validate and set max_tokens (1-4096 range)
    try:
        max_tokens = int(os.getenv("CONTEXTUAL_EMBEDDING_MAX_TOKENS", "200"))
        if not (1 <= max_tokens <= 4096):
            logger.warning(f"CONTEXTUAL_EMBEDDING_MAX_TOKENS ({max_tokens}) out of range 1-4096, using default 200")
            max_tokens = 200
    except ValueError:
        logger.warning("CONTEXTUAL_EMBEDDING_MAX_TOKENS must be an integer, using default 200")
        max_tokens = 200
    
    # Validate and set temperature (0.0-2.0 range)
    try:
        temperature = float(os.getenv("CONTEXTUAL_EMBEDDING_TEMPERATURE", "0.3"))
        if not (0.0 <= temperature <= 2.0):
            logger.warning(f"CONTEXTUAL_EMBEDDING_TEMPERATURE ({temperature}) out of range 0.0-2.0, using default 0.3")
            temperature = 0.3
    except ValueError:
        logger.warning("CONTEXTUAL_EMBEDDING_TEMPERATURE must be a number, using default 0.3")
        temperature = 0.3
    
    # Validate and set max_doc_chars (positive integer)
    try:
        max_doc_chars = int(os.getenv("CONTEXTUAL_EMBEDDING_MAX_DOC_CHARS", "25000"))
        if max_doc_chars <= 0:
            logger.warning(f"CONTEXTUAL_EMBEDDING_MAX_DOC_CHARS ({max_doc_chars}) must be positive, using default 25000")
            max_doc_chars = 25000
    except ValueError:
        logger.warning("CONTEXTUAL_EMBEDDING_MAX_DOC_CHARS must be a positive integer, using default 25000")
        max_doc_chars = 25000

    try:
        # Truncate full document if it's too long
        truncated_document = full_document[:max_doc_chars]
        
        # Create position info if available
        position_info = ""
        if chunk_index >= 0 and total_chunks > 1:
            position_info = f" (chunk {chunk_index + 1} of {total_chunks})"

        # Create the prompt for generating contextual information
        prompt = f"""<document>
{truncated_document}
</document>

Here is the chunk{position_info} we want to situate within the whole document:
<chunk>
{chunk}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        # Create OpenAI client instance
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Call the OpenAI API to generate contextual information
        response = client.chat.completions.create(
            model=model_choice,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise contextual information.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Extract the generated context
        context = response.choices[0].message.content.strip()

        # Combine the context with the original chunk
        contextual_text = f"{context}\n---\n{chunk}"

        return contextual_text

    except Exception as e:
        logger.error(
            "Error generating contextual embedding: %s. Using original chunk instead.",
            str(e)
        )
        return chunk


def process_chunk_with_context(args) -> tuple[str, list[float]]:
    """
    Process a single chunk with contextual embedding.
    This function is designed to be used with concurrent.futures.

    Args:
        args: Tuple containing (chunk, full_document, chunk_index, total_chunks)

    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - The embedding for the contextual text
    """
    chunk, full_document, chunk_index, total_chunks = args
    contextual_text = generate_contextual_embedding(chunk, full_document, chunk_index, total_chunks)
    embedding = create_embedding(contextual_text)
    return contextual_text, embedding


async def add_documents_to_database(
    database: Any,  # VectorDatabase instance
    urls: list[str],
    chunk_numbers: list[int],
    contents: list[str],
    metadatas: list[dict[str, Any]],
    url_to_full_document: dict[str, str] | None = None,
    batch_size: int = 20,
    source_ids: list[str] | None = None,
) -> None:
    """
    Add documents to the database with embeddings.
    
    This function generates embeddings, stores documents in the vector database,
    and automatically adds source entries for web scraped content.
    
    Args:
        database: VectorDatabase instance (the database adapter)
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        contents: List of document contents
        metadatas: List of document metadata
        url_to_full_document: Dictionary mapping URLs to their full document content (optional)
        batch_size: Size of each batch for insertion
        source_ids: Optional list of source IDs
    """
    from core.logging import logger
    from concurrent.futures import as_completed
    
    # Check if we should use contextual embeddings
    use_contextual_embeddings = (
        os.getenv("USE_CONTEXTUAL_EMBEDDINGS", "false").lower() == "true"
    )
    
    if use_contextual_embeddings and url_to_full_document:
        logger.info("Using contextual embeddings for enhanced retrieval")
        
        # Use ThreadPoolExecutor for parallel processing with individual error handling
        with ThreadPoolExecutor(max_workers=int(os.getenv("CONTEXTUAL_EMBEDDING_MAX_WORKERS", "10"))) as executor:
            # Submit tasks individually for better error handling
            future_to_index = {}
            total_chunks = len(contents)
            
            for i, (url, content) in enumerate(zip(urls, contents)):
                full_document = url_to_full_document.get(url, "")
                args = (content, full_document, i, total_chunks)
                future = executor.submit(process_chunk_with_context, args)
                future_to_index[future] = i
            
            # Process results as they complete, with individual error handling
            contextual_contents = contents.copy()  # Start with original contents
            embeddings = [None] * len(contents)  # Pre-allocate embeddings list
            successful_contextual_count = 0
            failed_contextual_count = 0
            
            try:
                for future in as_completed(future_to_index.keys()):
                    index = future_to_index[future]
                    try:
                        contextual_text, embedding = future.result()
                        contextual_contents[index] = contextual_text
                        embeddings[index] = embedding
                        successful_contextual_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to generate contextual embedding for chunk {index}: {e}. Using original content.")
                        # Keep original content and generate standard embedding
                        embedding = create_embedding(contents[index])
                        embeddings[index] = embedding
                        failed_contextual_count += 1
                
                # Update contents to use contextual versions where successful
                contents = contextual_contents
                
                # Add contextual embedding flag to metadata for successful ones
                for i, metadata in enumerate(metadatas):
                    metadata["contextual_embedding"] = (embeddings[i] is not None and i < successful_contextual_count)
                
                logger.info(f"Contextual embedding processing: {successful_contextual_count} successful, {failed_contextual_count} failed")
                
            except Exception as e:
                logger.error(f"Error during contextual embedding processing: {e}. Falling back to standard embeddings.")
                # Fall back to standard embedding generation for all
                embeddings = []
                for i in range(0, len(contents), batch_size):
                    batch_texts = contents[i:i + batch_size]
                    batch_embeddings = create_embeddings_batch(batch_texts)
                    embeddings.extend(batch_embeddings)
    else:
        # Generate embeddings for all contents in batches (standard approach)
        embeddings = []
        for i in range(0, len(contents), batch_size):
            batch_texts = contents[i:i + batch_size]
            batch_embeddings = create_embeddings_batch(batch_texts)
            embeddings.extend(batch_embeddings)
    
    # Store documents with embeddings using the provided database adapter
    await database.add_documents(
        urls=urls,
        chunk_numbers=chunk_numbers,
        contents=contents,
        metadatas=metadatas,
        embeddings=embeddings,
        source_ids=source_ids,
    )
    
    # Add source entries for web scraped content
    if source_ids and url_to_full_document:
        await _add_web_sources_to_database(
            database=database,
            urls=urls,
            source_ids=source_ids,
            url_to_full_document=url_to_full_document,
            contents=contents,
        )

async def search_documents(
    database: Any,  # VectorDatabase instance
    query: str,
    match_count: int = 10,
    filter_metadata: dict[str, Any] | None = None,
    source_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search for documents using vector similarity.
    
    Args:
        database: VectorDatabase instance (the database adapter)
        query: Search query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter
        source_filter: Optional source ID filter
    
    Returns:
        List of documents with similarity scores
    """
    # Generate embedding for the query
    query_embedding = create_embedding(query)
    
    # Search using the database adapter
    return await database.search_documents(
        query_embedding=query_embedding,
        match_count=match_count,
        filter_metadata=filter_metadata,
        source_filter=source_filter,
    )


async def add_code_examples_to_database(
    database: Any,  # VectorDatabase instance
    urls: list[str],
    chunk_numbers: list[int],
    code_examples: list[str],
    summaries: list[str],
    metadatas: list[dict[str, Any]],
    batch_size: int = 20,
) -> None:
    """
    Add code examples to the database with embeddings.
    
    Args:
        database: VectorDatabase instance (the database adapter)
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        code_examples: List of code examples
        summaries: List of summaries for the code examples
        metadatas: List of metadata dictionaries
        batch_size: Size of each batch for insertion
    """
    if not urls:
        return  # Early return for empty lists
    
    # Generate embeddings for summaries in batches
    embeddings = []
    for i in range(0, len(summaries), batch_size):
        batch_texts = summaries[i:i + batch_size]
        batch_embeddings = create_embeddings_batch(batch_texts)
        embeddings.extend(batch_embeddings)
    
    # Store code examples with embeddings using the database adapter
    await database.add_code_examples(
        urls=urls,
        chunk_numbers=chunk_numbers,
        code_examples=code_examples,
        summaries=summaries,
        metadatas=metadatas,
        embeddings=embeddings,
    )


async def search_code_examples(
    database: Any,  # VectorDatabase instance
    query: str,
    match_count: int = 5,
    source_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search for code examples using vector similarity with enhanced query.
    
    Args:
        database: VectorDatabase instance (the database adapter)
        query: Search query text
        match_count: Maximum number of results to return
        source_filter: Optional source ID filter
    
    Returns:
        List of code examples with similarity scores
    """
    # Enhance the query for code search
    enhanced_query = f"Code example for {query}"
    
    # Generate embedding for the enhanced query
    query_embedding = create_embedding(enhanced_query)
    
    # Search using the database adapter
    return await database.search_code_examples(
        query_embedding=query_embedding,
        match_count=match_count,
        source_filter=source_filter,
    )


async def _add_web_sources_to_database(
    database: Any,
    urls: list[str],
    source_ids: list[str],
    url_to_full_document: dict[str, str],
    contents: list[str],
) -> None:
    """
    Add web sources to the sources table for scraped content.
    
    Args:
        database: Database adapter
        urls: List of URLs
        source_ids: List of source IDs
        url_to_full_document: Map of URLs to full documents
        contents: List of chunk contents for counting
    """
    from core.logging import logger
    
    try:
        # Group by source_id to create source summaries
        source_data = {}
        
        for i, (url, source_id) in enumerate(zip(urls, source_ids)):
            if source_id and source_id not in source_data:
                # Get full document for this URL
                full_document = url_to_full_document.get(url, "")
                
                # Count chunks for this source
                chunk_count = sum(1 for sid in source_ids if sid == source_id)
                
                # Generate a simple summary from first 200 characters
                summary = full_document[:200].strip()
                if len(full_document) > 200:
                    summary += "..."
                
                # Word count estimation
                word_count = len(full_document.split())
                
                source_data[source_id] = {
                    "url": url,  # Use the first URL for this source
                    "title": source_id,  # Use source_id as title for web sources
                    "description": summary,
                    "word_count": word_count,
                    "metadata": {
                        "type": "web_scrape",
                        "chunk_count": chunk_count,
                        "total_content_length": len(full_document),
                    },
                }
        
        # Add each unique source to the database
        for source_id, data in source_data.items():
            try:
                # Check database adapter type and use appropriate method
                if hasattr(database, 'add_source'):
                    # Qdrant adapter - needs embedding
                    source_embedding = create_embeddings_batch([data["description"]])[0]
                    await database.add_source(
                        source_id=source_id,
                        url=data["url"],
                        title=data["title"],
                        description=data["description"],
                        metadata=data["metadata"],
                        embedding=source_embedding,
                    )
                    logger.info(f"Added web source to Qdrant: {source_id}")
                    
                elif hasattr(database, 'update_source_info'):
                    # Supabase adapter - simpler interface
                    await database.update_source_info(
                        source_id=source_id,
                        summary=data["description"],
                        word_count=data["word_count"],
                    )
                    logger.info(f"Added web source to Supabase: {source_id}")
                    
                else:
                    logger.warning(f"Database adapter does not support adding sources")
                    
            except Exception as e:
                logger.warning(f"Failed to add web source {source_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error adding web sources to database: {e}")
