from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Optional
from app.core.config import settings
import logging
import os
import hashlib

logger = logging.getLogger(__name__)

# Lazy import for sentence_transformers
_sentence_transformer = None

def get_encoder():
    """Lazy load sentence transformer"""
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer loaded")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {e}")
            raise
    return _sentence_transformer

class VectorStore:
    """Qdrant vector store for semantic search"""
    
    def __init__(self, collection_name: str = "Enatega-Estimator"):
        self.collection_name = collection_name
        # Initialize Qdrant client (in-memory for Railway, or use Qdrant Cloud)
        self.client = self._init_client()
        self.encoder = None  # Will be loaded lazily
        self._ensure_collection()
    
    def _init_client(self) -> QdrantClient:
        """Initialize Qdrant client"""
        # Try to use Qdrant Cloud if URL is provided, otherwise use in-memory
        qdrant_url = settings.QDRANT_URL or os.getenv("QDRANT_URL")
        qdrant_api_key = settings.QDRANT_API_KEY or os.getenv("QDRANT_API_KEY")
        
        if qdrant_url and qdrant_api_key:
            logger.info(f"Using Qdrant Cloud: {qdrant_url}")
            # QdrantClient expects URL without protocol prefix for cloud instances
            # Format: https://cluster-id.region.cloud.qdrant.io
            clean_url = qdrant_url.replace("https://", "").replace("http://", "")
            # Remove port if present (Qdrant Cloud uses default ports)
            if ":6333" in clean_url:
                clean_url = clean_url.split(":")[0]
            
            return QdrantClient(
                url=f"https://{clean_url}",
                api_key=qdrant_api_key,
                port=6333  # Qdrant Cloud uses port 6333
            )
        else:
            # Use in-memory Qdrant (good for Railway)
            logger.info("Using in-memory Qdrant")
            return QdrantClient(":memory:")
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 produces 384-dim vectors
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
    
    def add_documents(self, documents: Dict[str, str]):
        """Add documents to vector store"""
        try:
            # Lazy load encoder
            if self.encoder is None:
                self.encoder = get_encoder()
            
            points = []
            for doc_id, text in documents.items():
                if not text or len(text.strip()) < 10:
                    continue
                
                # Create embedding
                embedding = self.encoder.encode(text).tolist()
                
                # Create point ID from document name
                point_id = int(hashlib.md5(doc_id.encode()).hexdigest()[:8], 16)
                
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": text[:5000],  # Limit payload size
                        "doc_id": doc_id
                    }
                ))
            
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Added {len(points)} documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
    
    def search(self, query: str, top_k: int = 8) -> List[Dict]:
        """Search for similar documents"""
        try:
            # Lazy load encoder
            if self.encoder is None:
                self.encoder = get_encoder()
            
            # Create query embedding
            query_embedding = self.encoder.encode(query).tolist()
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result.payload.get("text", ""),
                    "doc_id": result.payload.get("doc_id", ""),
                    "score": result.score
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []
    
    def get_relevant_context(self, query: str, max_length: int = 6000) -> str:
        """Get comprehensive relevant context for a query"""
        # Get more results for comprehensive coverage
        results = self.search(query, top_k=8)
        
        if not results:
            return ""
        
        # Combine top results, prioritizing higher scores
        context_parts = []
        current_length = 0
        
        for result in results:
            text = result["text"]
            score = result.get("score", 0)
            doc_id = result.get("doc_id", "unknown")
            
            # Prioritize higher scoring results but include all relevant content
            if current_length + len(text) <= max_length:
                context_parts.append(f"[Doc: {doc_id} | Relevance: {score:.2f}]\n{text}")
                current_length += len(text)
            else:
                remaining = max_length - current_length
                if remaining > 300:  # Increased threshold to get more complete context
                    context_parts.append(f"[Doc: {doc_id} | Relevance: {score:.2f}]\n{text[:remaining]}")
                break
        
        return "\n\n---\n\n".join(context_parts)
