# Qdrant Vector Database Setup

## Overview

The Estimation Bot uses **Qdrant** as its vector database for semantic search through documents. This enables the bot to find relevant context from your PDF/DOCX files when generating estimates.

## How It Works

1. **Document Embedding**: When documents are loaded, they're converted to vector embeddings using Sentence Transformers
2. **Vector Storage**: Embeddings are stored in Qdrant with document metadata
3. **Semantic Search**: When a query comes in, it's converted to an embedding and Qdrant finds the most similar documents
4. **Context Retrieval**: Relevant document chunks are retrieved and used to enhance AI responses

## Configuration Options

### Option 1: In-Memory Qdrant (Default - Railway Compatible)

**No setup required!** The system uses in-memory Qdrant by default, which is perfect for Railway deployments.

- ✅ No external service needed
- ✅ Works immediately
- ✅ Good for most use cases
- ⚠️ Data is lost on restart (documents are re-indexed on startup)

### Option 2: Qdrant Cloud (Recommended for Production)

For persistent storage and better performance:

1. **Sign up** at https://cloud.qdrant.io
2. **Create a cluster**
3. **Get your credentials**:
   - QDRANT_URL: Your cluster URL
   - QDRANT_API_KEY: Your API key

4. **Set environment variables in Railway**:
   ```bash
   QDRANT_URL=https://your-cluster.qdrant.io
   QDRANT_API_KEY=your_api_key_here
   ```

## Benefits of Qdrant

- 🚀 **Fast Semantic Search**: Find relevant documents instantly
- 📊 **Better Context**: AI gets more relevant information
- 🎯 **Accurate Estimates**: Based on actual document content
- 💾 **Scalable**: Can handle large document collections
- 🔍 **Similarity Search**: Uses cosine similarity for best results

## Current Implementation

The system automatically:
- ✅ Creates embeddings for all PDF/DOCX documents
- ✅ Stores them in Qdrant on startup
- ✅ Uses semantic search for query context
- ✅ Falls back to simple text search if Qdrant fails

## Vector Model

Using **all-MiniLM-L6-v2** from Sentence Transformers:
- 384-dimensional vectors
- Fast and efficient
- Good quality embeddings
- Small model size

## Monitoring

Check logs for:
- `"Using in-memory Qdrant"` - In-memory mode
- `"Using Qdrant Cloud"` - Cloud mode
- `"Added X documents to vector store"` - Indexing success
- `"Vector search failed, using fallback"` - Fallback mode

## Troubleshooting

### Vector Store Not Working?

The system has automatic fallback - if Qdrant fails, it uses simple text search. Check logs for errors.

### Want Better Performance?

Use Qdrant Cloud for:
- Persistent storage
- Better performance
- Multi-instance support
- Production reliability

### Documents Not Being Indexed?

- Check that PDF/DOCX files exist in project root
- Verify document extraction is working (check logs)
- Ensure documents have sufficient text content

## No Vector Database Needed?

While Qdrant enhances the system, it's **optional**. The bot works without it using:
- Simple text search
- AI feature extraction
- Fallback mechanisms

However, Qdrant provides:
- Better context retrieval
- More accurate estimates
- Faster search
- Scalability
