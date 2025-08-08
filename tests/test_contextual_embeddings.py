"""Comprehensive tests for contextual embeddings feature."""

import os
import pytest
from unittest.mock import patch, MagicMock, call
from concurrent.futures import Future, TimeoutError
import asyncio

from src.utils.embeddings import (
    generate_contextual_embedding,
    process_chunk_with_context,
    add_documents_to_database,
)


class TestGenerateContextualEmbedding:
    """Test the generate_contextual_embedding function."""

    @patch.dict(os.environ, {
        "CONTEXTUAL_EMBEDDING_MODEL": "gpt-4o-mini",
        "CONTEXTUAL_EMBEDDING_MAX_TOKENS": "200",
        "CONTEXTUAL_EMBEDDING_TEMPERATURE": "0.3",
        "CONTEXTUAL_EMBEDDING_MAX_DOC_CHARS": "25000"
    })
    @patch("src.utils.embeddings.openai.OpenAI")
    def test_basic_functionality(self, mock_openai_class):
        """Test basic contextual embedding generation."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This chunk discusses testing"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test
        chunk = "Testing is important"
        full_doc = "This is a full document about testing in Python"
        result = generate_contextual_embedding(chunk, full_doc, 0, 1)

        # Verify
        assert "This chunk discusses testing" in result
        assert chunk in result
        assert "---" in result  # Separator between context and chunk
        mock_client.chat.completions.create.assert_called_once()

    @patch.dict(os.environ, {
        "CONTEXTUAL_EMBEDDING_MAX_TOKENS": "5000",  # Out of range
        "CONTEXTUAL_EMBEDDING_TEMPERATURE": "3.0",  # Out of range
        "CONTEXTUAL_EMBEDDING_MAX_DOC_CHARS": "-100"  # Invalid
    })
    @patch("src.utils.embeddings.openai.OpenAI")
    def test_config_validation(self, mock_openai_class):
        """Test configuration validation with invalid values."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Context"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test - should use defaults when invalid values provided
        chunk = "Test chunk"
        full_doc = "Test document"
        result = generate_contextual_embedding(chunk, full_doc, 0, 1)

        # Verify defaults were used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 200  # Default
        assert call_kwargs["temperature"] == 0.3  # Default

    @patch("src.utils.embeddings.openai.OpenAI")
    def test_document_truncation(self, mock_openai_class):
        """Test that very long documents are truncated."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Context for long doc"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test with very long document
        chunk = "Test chunk"
        full_doc = "A" * 30000  # Longer than default max
        result = generate_contextual_embedding(chunk, full_doc, 0, 1)

        # Verify truncation happened
        call_args = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
        assert len(call_args) < 30000  # Document was truncated

    @patch("src.utils.embeddings.openai.OpenAI")
    def test_chunk_position_info(self, mock_openai_class):
        """Test that chunk position information is included."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Context"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test with position info
        chunk = "Test chunk"
        full_doc = "Test document"
        result = generate_contextual_embedding(chunk, full_doc, 2, 5)

        # Verify position info in prompt
        call_args = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
        assert "chunk 3 of 5" in call_args  # 0-indexed becomes 1-indexed

    @patch("src.utils.embeddings.openai.OpenAI")
    def test_error_handling(self, mock_openai_class):
        """Test error handling returns original chunk."""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        # Test
        chunk = "Test chunk"
        full_doc = "Test document"
        result = generate_contextual_embedding(chunk, full_doc, 0, 1)

        # Verify fallback to original chunk
        assert result == chunk


class TestProcessChunkWithContext:
    """Test the process_chunk_with_context function."""

    @patch("src.utils.embeddings.create_embedding")
    @patch("src.utils.embeddings.generate_contextual_embedding")
    def test_basic_processing(self, mock_generate, mock_create_embedding):
        """Test basic chunk processing with context."""
        # Setup mocks
        mock_generate.return_value = "Contextual text"
        mock_create_embedding.return_value = [0.1, 0.2, 0.3]

        # Test
        args = ("chunk", "full_doc", 0, 1)
        contextual_text, embedding = process_chunk_with_context(args)

        # Verify
        assert contextual_text == "Contextual text"
        assert embedding == [0.1, 0.2, 0.3]
        mock_generate.assert_called_once_with("chunk", "full_doc", 0, 1)
        mock_create_embedding.assert_called_once_with("Contextual text")

    @patch("src.utils.embeddings.create_embedding")
    @patch("src.utils.embeddings.generate_contextual_embedding")
    def test_error_propagation(self, mock_generate, mock_create_embedding):
        """Test that errors are propagated."""
        # Setup mock to raise error
        mock_generate.side_effect = Exception("Generation failed")

        # Test - should raise exception
        args = ("chunk", "full_doc", 0, 1)
        with pytest.raises(Exception) as exc_info:
            process_chunk_with_context(args)
        
        assert "Generation failed" in str(exc_info.value)


class TestAddDocumentsToDatabase:
    """Test the add_documents_to_database function with contextual embeddings."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    @patch("src.utils.embeddings.create_embedding")
    @patch("src.utils.embeddings.process_chunk_with_context")
    async def test_contextual_embeddings_enabled(self, mock_process, mock_create_embedding):
        """Test with contextual embeddings enabled."""
        # Setup mocks
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)
        
        mock_process.side_effect = [
            ("Context 1", [0.1, 0.2]),
            ("Context 2", [0.3, 0.4]),
        ]

        # Test data
        urls = ["url1", "url2"]
        chunk_numbers = [0, 1]
        contents = ["chunk1", "chunk2"]
        metadatas = [{}, {}]
        url_to_full_document = {
            "url1": "Full document 1",
            "url2": "Full document 2",
        }

        # Test
        await add_documents_to_database(
            database=mock_database,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )

        # Verify
        assert mock_process.call_count == 2
        mock_database.add_documents.assert_called_once()
        
        # Check that contextual embeddings were used
        call_args = mock_database.add_documents.call_args[1]
        assert call_args["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]
        assert call_args["contents"] == ["Context 1", "Context 2"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    @patch("src.utils.embeddings.create_embedding")
    @patch("src.utils.embeddings.process_chunk_with_context")
    async def test_partial_failure_handling(self, mock_process, mock_create_embedding):
        """Test handling of partial failures in contextual embedding generation."""
        # Setup mocks
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)
        
        # First succeeds, second fails
        def side_effect(args):
            if args[0] == "chunk1":
                return ("Context 1", [0.1, 0.2])
            else:
                raise Exception("Processing failed")
        
        mock_process.side_effect = side_effect
        mock_create_embedding.return_value = [0.5, 0.6]  # Fallback embedding

        # Test data
        urls = ["url1", "url2"]
        chunk_numbers = [0, 1]
        contents = ["chunk1", "chunk2"]
        metadatas = [{}, {}]
        url_to_full_document = {
            "url1": "Full document 1",
            "url2": "Full document 2",
        }

        # Test
        await add_documents_to_database(
            database=mock_database,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )

        # Verify partial success
        call_args = mock_database.add_documents.call_args[1]
        assert call_args["contents"][0] == "Context 1"  # Successful contextual
        assert call_args["contents"][1] == "chunk2"  # Failed, kept original
        assert call_args["embeddings"][0] == [0.1, 0.2]  # Contextual embedding
        assert call_args["embeddings"][1] == [0.5, 0.6]  # Fallback embedding

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "false"})
    @patch("src.utils.embeddings.create_embeddings_batch")
    async def test_contextual_embeddings_disabled(self, mock_create_batch):
        """Test with contextual embeddings disabled."""
        # Setup mocks
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)
        
        mock_create_batch.return_value = [[0.7, 0.8], [0.9, 1.0]]

        # Test data
        urls = ["url1", "url2"]
        chunk_numbers = [0, 1]
        contents = ["chunk1", "chunk2"]
        metadatas = [{}, {}]

        # Test
        await add_documents_to_database(
            database=mock_database,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
        )

        # Verify standard embeddings were used
        mock_create_batch.assert_called_once_with(["chunk1", "chunk2"])
        call_args = mock_database.add_documents.call_args[1]
        assert call_args["embeddings"] == [[0.7, 0.8], [0.9, 1.0]]
        assert call_args["contents"] == ["chunk1", "chunk2"]  # Original contents

    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        "USE_CONTEXTUAL_EMBEDDINGS": "true",
        "CONTEXTUAL_EMBEDDING_MAX_WORKERS": "5"
    })
    @patch("src.utils.embeddings.ThreadPoolExecutor")
    async def test_max_workers_configuration(self, mock_executor_class):
        """Test that max_workers is configurable."""
        # Setup mocks
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor_class.return_value.__exit__ = MagicMock()
        
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)

        # Test
        await add_documents_to_database(
            database=mock_database,
            urls=["url1"],
            chunk_numbers=[0],
            contents=["chunk1"],
            metadatas=[{}],
            url_to_full_document={"url1": "doc1"},
        )

        # Verify max_workers was set from environment
        mock_executor_class.assert_called_once_with(max_workers=5)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("src.utils.embeddings.openai.OpenAI")
    def test_empty_chunk(self, mock_openai_class):
        """Test handling of empty chunk."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Context for empty"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test
        result = generate_contextual_embedding("", "Full document", 0, 1)
        
        # Should still work
        assert "Context for empty" in result

    @patch("src.utils.embeddings.openai.OpenAI")
    def test_empty_document(self, mock_openai_class):
        """Test handling of empty document."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Context"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test
        result = generate_contextual_embedding("chunk", "", 0, 1)
        
        # Should still work
        assert "Context" in result

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    async def test_no_url_to_full_document(self):
        """Test when url_to_full_document is not provided."""
        # Setup mocks
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)

        # Test without url_to_full_document
        with patch("src.utils.embeddings.create_embeddings_batch") as mock_batch:
            mock_batch.return_value = [[0.1, 0.2]]
            
            await add_documents_to_database(
                database=mock_database,
                urls=["url1"],
                chunk_numbers=[0],
                contents=["chunk1"],
                metadatas=[{}],
                url_to_full_document=None,  # Not provided
            )

            # Should fall back to standard embeddings
            mock_batch.assert_called_once()


class TestIntegration:
    """Integration tests for the full contextual embeddings pipeline."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        "USE_CONTEXTUAL_EMBEDDINGS": "true",
        "CONTEXTUAL_EMBEDDING_MODEL": "gpt-4o-mini",
        "CONTEXTUAL_EMBEDDING_MAX_TOKENS": "150",
        "CONTEXTUAL_EMBEDDING_TEMPERATURE": "0.5",
        "CONTEXTUAL_EMBEDDING_MAX_DOC_CHARS": "10000",
        "CONTEXTUAL_EMBEDDING_MAX_WORKERS": "3"
    })
    @patch("src.utils.embeddings.openai.OpenAI")
    @patch("src.utils.embeddings.create_embedding")
    async def test_full_pipeline(self, mock_create_embedding, mock_openai_class):
        """Test the full contextual embeddings pipeline end-to-end."""
        # Setup OpenAI mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock different contexts for different chunks
        contexts = ["Context for chunk 1", "Context for chunk 2", "Context for chunk 3"]
        responses = []
        for context in contexts:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content=context))
            ]
            responses.append(mock_response)
        
        mock_client.chat.completions.create.side_effect = responses
        
        # Mock embeddings
        mock_create_embedding.side_effect = [
            [0.1, 0.2], [0.3, 0.4], [0.5, 0.6]
        ]
        
        # Setup database mock
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)
        
        # Test data
        urls = ["url1", "url1", "url2"]
        chunk_numbers = [0, 1, 0]
        contents = ["chunk1", "chunk2", "chunk3"]
        metadatas = [{}, {}, {}]
        url_to_full_document = {
            "url1": "This is the full document for URL 1 with multiple chunks",
            "url2": "This is the full document for URL 2",
        }
        
        # Run the pipeline
        await add_documents_to_database(
            database=mock_database,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )
        
        # Verify results
        assert mock_client.chat.completions.create.call_count == 3
        assert mock_create_embedding.call_count == 3
        
        # Check database was called with contextual content
        call_args = mock_database.add_documents.call_args[1]
        for i, content in enumerate(call_args["contents"]):
            assert f"Context for chunk {i+1}" in content
            assert f"chunk{i+1}" in content
        
        # Check embeddings
        assert call_args["embeddings"] == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        
        # Check metadata was updated
        for metadata in call_args["metadatas"]:
            assert "contextual_embedding" in metadata


class TestPerformance:
    """Test performance-related aspects."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    @patch("src.utils.embeddings.process_chunk_with_context")
    async def test_large_batch_processing(self, mock_process):
        """Test processing of large batches."""
        # Setup mocks
        mock_database = MagicMock()
        mock_database.add_documents = MagicMock(return_value=asyncio.Future())
        mock_database.add_documents.return_value.set_result(None)
        
        # Mock processing for 100 chunks
        mock_process.side_effect = [
            (f"Context {i}", [0.1 * i, 0.2 * i]) for i in range(100)
        ]
        
        # Create test data for 100 chunks
        urls = [f"url{i}" for i in range(100)]
        chunk_numbers = list(range(100))
        contents = [f"chunk{i}" for i in range(100)]
        metadatas = [{} for _ in range(100)]
        url_to_full_document = {
            f"url{i}": f"Document {i}" for i in range(100)
        }
        
        # Test
        await add_documents_to_database(
            database=mock_database,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )
        
        # Verify all were processed
        assert mock_process.call_count == 100
        call_args = mock_database.add_documents.call_args[1]
        assert len(call_args["contents"]) == 100
        assert len(call_args["embeddings"]) == 100