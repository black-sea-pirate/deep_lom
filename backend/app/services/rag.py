"""
RAG Service

Retrieval-Augmented Generation service for document processing.
Uses ChromaDB HTTP API for vector storage and OpenAI embeddings.

This version uses direct HTTP calls to ChromaDB server instead of the SDK,
which avoids the need for compiling chroma-hnswlib on Windows.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
import httpx

from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaHTTPClient:
    """
    Simple HTTP client for ChromaDB server.
    
    Uses the ChromaDB REST API directly without requiring the chromadb SDK.
    This is useful on Windows where chroma-hnswlib compilation fails.
    """
    
    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"
        self.client = httpx.Client(timeout=120.0)
        self._tenant = "default_tenant"
        self._database = "default_database"
        logger.info(f"ChromaDB HTTP client initialized: {self.base_url}")
    
    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make HTTP request to ChromaDB."""
        url = f"{self.base_url}{path}"
        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            if response.content:
                return response.json()
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"ChromaDB HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"ChromaDB request error: {e}")
            raise
    
    def heartbeat(self) -> dict:
        """Check server is alive."""
        return self._request("GET", "/api/v1/heartbeat")
    
    def list_collections(self) -> List[dict]:
        """List all collections."""
        return self._request("GET", "/api/v1/collections")
    
    def create_collection(self, name: str, metadata: Optional[dict] = None) -> dict:
        """Create or get a collection."""
        try:
            # Try get_or_create endpoint first
            return self._request("POST", "/api/v1/collections", 
                json={
                    "name": name,
                    "metadata": metadata or {},
                    "get_or_create": True,
                })
        except httpx.HTTPStatusError as e:
            # If collection exists (409) or endpoint not found, try to get it
            if e.response.status_code in (409, 404):
                return self.get_collection(name)
            raise
    
    def get_collection(self, name: str) -> dict:
        """Get collection by name."""
        return self._request("GET", f"/api/v1/collections/{name}")
    
    def delete_collection(self, name: str) -> None:
        """Delete collection."""
        try:
            self._request("DELETE", f"/api/v1/collections/{name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
    
    def add_to_collection(
        self,
        collection_id: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
    ) -> None:
        """Add documents to collection."""
        self._request("POST", f"/api/v1/collections/{collection_id}/add", json={
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas or [{}] * len(ids),
        })
    
    def query_collection(
        self,
        collection_id: str,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[dict] = None,
        include: Optional[List[str]] = None,
    ) -> dict:
        """Query collection for similar vectors."""
        body = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
            "include": include or ["documents", "metadatas", "distances"],
        }
        if where:
            body["where"] = where
        return self._request("POST", f"/api/v1/collections/{collection_id}/query", json=body)
    
    def get_from_collection(
        self,
        collection_id: str,
        where: Optional[dict] = None,
        include: Optional[List[str]] = None,
    ) -> dict:
        """Get documents from collection by filter."""
        body = {
            "include": include or ["documents", "metadatas"],
        }
        if where:
            body["where"] = where
        return self._request("POST", f"/api/v1/collections/{collection_id}/get", json=body)
    
    def delete_from_collection(self, collection_id: str, ids: List[str]) -> None:
        """Delete documents from collection by IDs."""
        self._request("POST", f"/api/v1/collections/{collection_id}/delete", json={
            "ids": ids,
        })


class RAGService:
    """
    RAG Service for document vectorization and retrieval.
    
    Uses ChromaDB as vector database and OpenAI embeddings.
    This ensures AI-generated questions are grounded in actual document content.
    
    Each project has its own ChromaDB collection for isolation.
    """
    
    def __init__(self):
        """Initialize RAG service with ChromaDB and OpenAI clients."""
        # Initialize OpenAI client
        self.openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Initialize ChromaDB HTTP client
        self.chroma = ChromaHTTPClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        
        # Cache for collection IDs (name -> UUID)
        self._collection_ids: Dict[str, str] = {}
        
        logger.info("RAG Service initialized")
    
    def get_or_create_collection(self, collection_name: str) -> str:
        """
        Get or create a ChromaDB collection for a project.
        
        Args:
            collection_name: Collection name (usually project_{project_id})
            
        Returns:
            Collection UUID
        """
        if collection_name not in self._collection_ids:
            result = self.chroma.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._collection_ids[collection_name] = result["id"]
            logger.info(f"Created/got collection: {collection_name} -> {result['id']}")
        return self._collection_ids[collection_name]
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a ChromaDB collection.
        
        Args:
            collection_name: Collection name to delete
        """
        try:
            self.chroma.delete_collection(name=collection_name)
            if collection_name in self._collection_ids:
                del self._collection_ids[collection_name]
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Failed to delete collection {collection_name}: {e}")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for texts using OpenAI.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        # Filter out empty texts
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            return []
        
        response = self.openai.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=non_empty_texts,
        )
        
        logger.debug(f"Generated {len(response.data)} embeddings")
        return [item.embedding for item in response.data]
    
    def add_document(
        self,
        collection_id: str,
        document_id: str,
        chunks: List[str],
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Add document chunks to a project's vector collection.
        
        Args:
            collection_id: ChromaDB collection name (project_{project_id})
            document_id: Unique document identifier (material_id)
            chunks: List of text chunks from document
            metadata: Optional metadata for chunks
        """
        if not chunks:
            logger.warning(f"No chunks to add for document {document_id}")
            return
        
        # Filter empty chunks
        valid_chunks = [c for c in chunks if c and c.strip()]
        if not valid_chunks:
            logger.warning(f"No valid chunks after filtering for document {document_id}")
            return
        
        logger.info(f"Adding {len(valid_chunks)} chunks for document {document_id}")
        
        # Get collection UUID
        chroma_collection_id = self.get_or_create_collection(collection_id)
        
        # Generate embeddings
        embeddings = self.get_embeddings(valid_chunks)
        
        if not embeddings:
            logger.warning(f"No embeddings generated for document {document_id}")
            return
        
        # Prepare IDs and metadata
        ids = [f"{document_id}_chunk_{i}" for i in range(len(valid_chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "chunk_index": i,
                **(metadata or {}),
            }
            for i in range(len(valid_chunks))
        ]
        
        # Add to ChromaDB
        self.chroma.add_to_collection(
            collection_id=chroma_collection_id,
            ids=ids,
            embeddings=embeddings,
            documents=valid_chunks,
            metadatas=metadatas,
        )
        
        logger.info(f"Successfully added {len(ids)} chunks for document {document_id}")
    
    def delete_document(self, collection_id: str, document_id: str) -> None:
        """
        Delete all chunks for a document from vector database.
        
        Args:
            collection_id: ChromaDB collection name
            document_id: Document identifier to delete
        """
        try:
            chroma_collection_id = self.get_or_create_collection(collection_id)
            
            # Get all chunk IDs for this document
            results = self.chroma.get_from_collection(
                collection_id=chroma_collection_id,
                where={"document_id": document_id},
            )
            
            if results.get("ids"):
                self.chroma.delete_from_collection(
                    collection_id=chroma_collection_id,
                    ids=results["ids"],
                )
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
        except Exception as e:
            logger.warning(f"Failed to delete document {document_id}: {e}")
    
    def query(
        self,
        collection_id: str,
        query_text: str,
        n_results: int = 10,
        document_ids: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Query vector database for relevant chunks.
        
        Args:
            collection_id: ChromaDB collection name (project_{project_id})
            query_text: Query text to search for
            n_results: Number of results to return
            document_ids: Optional list of document IDs to filter by
            
        Returns:
            List of matching chunks with metadata
        """
        chroma_collection_id = self.get_or_create_collection(collection_id)
        
        # Generate query embedding
        query_embedding = self.get_embeddings([query_text])[0]
        
        # Build where filter
        where_filter = None
        if document_ids:
            where_filter = {"document_id": {"$in": document_ids}}
        
        # Query ChromaDB
        results = self.chroma.query_collection(
            collection_id=chroma_collection_id,
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
        
        # Format results
        chunks = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                chunks.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })
        
        logger.debug(f"Query returned {len(chunks)} chunks")
        return chunks
    
    def get_context_for_generation(
        self,
        collection_id: str,
        topic: str,
        max_chunks: int = 20,
    ) -> str:
        """
        Get relevant context for test generation from project's collection.
        
        Args:
            collection_id: ChromaDB collection name (project_{project_id})
            topic: Topic or subject to generate questions about
            max_chunks: Maximum number of chunks to include
            
        Returns:
            Concatenated context string
        """
        # Query for relevant chunks
        chunks = self.query(
            collection_id=collection_id,
            query_text=topic,
            n_results=max_chunks,
        )
        
        # Concatenate chunks with separators
        context_parts = []
        for chunk in chunks:
            context_parts.append(chunk["text"])
        
        context = "\n\n---\n\n".join(context_parts)
        logger.info(f"Generated context with {len(chunks)} chunks, {len(context)} chars")
        return context


# Global RAG service instance
rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service instance."""
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
