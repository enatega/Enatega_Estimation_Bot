import os
import json
from typing import Dict, List
from app.utils.document_extractor import DocumentExtractor
from app.services.vector_store import VectorStore
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """Manage knowledge base from extracted documents with Qdrant vector store"""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = data_dir
        self.extractor = DocumentExtractor(data_dir)
        self.documents: Dict[str, str] = {}
        self.chatgpt_examples: str = ""
        self.features: List[Dict] = []
        self.vector_store: VectorStore = None
        self._load_documents()
        self._init_vector_store()
    
    def _load_documents(self):
        """Load all documents into memory - only called once at initialization"""
        try:
            logger.info("Loading documents (one-time operation)...")
            self.documents = self.extractor.extract_all_documents()
            self.chatgpt_examples = self.extractor.get_chatgpt_examples(self.documents)
            logger.info(f"Loaded {len(self.documents)} documents - documents cached in memory")
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
    
    def _init_vector_store(self):
        """Initialize Qdrant vector store"""
        try:
            logger.info("Initializing Qdrant vector store...")
            collection_name = settings.QDRANT_COLLECTION_NAME
            self.vector_store = VectorStore(collection_name=collection_name)
            # Add documents to vector store
            if self.documents:
                self.vector_store.add_documents(self.documents)
            logger.info(f"Vector store initialized with collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Vector store initialization failed (will use fallback): {e}")
            self.vector_store = None
    
    def get_all_text(self) -> str:
        """Get all extracted text combined"""
        return "\n\n".join(self.documents.values())
    
    def get_chatgpt_examples(self) -> str:
        """Get ChatGPT conversation examples"""
        return self.chatgpt_examples
    
    def get_context_for_query(self, query: str, max_length: int = 6000) -> str:
        """Get comprehensive relevant context for a query using semantic search"""
        if self.vector_store:
            try:
                # Use vector search - get extensive context
                context = self.vector_store.get_relevant_context(query, max_length)
                if context:
                    logger.debug(f"Retrieved {len(context)} chars from vector store")
                    return context
            except Exception as e:
                logger.warning(f"Vector search failed, using fallback: {e}")
        
        # Fallback: search in cached documents (no reload)
        # Use comprehensive keyword matching on all documents
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]
        relevant_parts = []
        
        # Score all documents by relevance
        doc_scores = []
        for doc_id, text in self.documents.items():
            text_lower = text.lower()
            # Count matches and check for important terms
            matches = sum(1 for word in query_words if word in text_lower)
            # Boost score for important keywords
            if "team" in query_lower and "team" in text_lower:
                matches += 2
            if "developer" in query_lower and "developer" in text_lower:
                matches += 2
            if "estimate" in query_lower and "estimate" in text_lower:
                matches += 2
            
            if matches > 0:
                doc_scores.append((matches, doc_id, text))
        
        # Sort by match count (most relevant first)
        doc_scores.sort(reverse=True, key=lambda x: x[0])
        
        # Get top matching documents with more content
        for _, doc_id, text in doc_scores[:8]:  # Get top 8 matching documents
            relevant_parts.append(f"=== From {doc_id} ===\n{text[:3000]}")  # More text from each doc
            if len('\n\n'.join(relevant_parts)) > max_length:
                break
        
        if relevant_parts:
            return '\n\n'.join(relevant_parts)[:max_length]
        
        # Last resort: return ChatGPT examples (always cached)
        return self.chatgpt_examples[:max_length] if self.chatgpt_examples else ""
    
    def extract_features(self) -> List[Dict]:
        """Extract features from documents only - no hardcoded features"""
        # All features must come from documents
        # Return empty list - features should be extracted via AI from query + documents
        self.features = []
        return []
