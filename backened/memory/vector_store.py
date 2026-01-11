import faiss
import numpy as np
import os
import pickle
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from datetime import datetime
import threading

class VectorMemory:
    """
    Vector-based memory store using FAISS for semantic search.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: str = "vector.index",
        data_path: str = "vector_data.pkl",
        dimension: int = 384
    ):
        """
        Initialize vector memory store.
        
        Args:
            model_name: Name of the sentence transformer model
            index_path: Path to save/load FAISS index
            data_path: Path to save/load metadata
            dimension: Embedding dimension
        """
        self.model_name = model_name
        self.index_path = index_path
        self.data_path = data_path
        self.dimension = dimension
        self._lock = threading.Lock()  # Thread safety
        
        # Lazy load model (load only when needed)
        self._model = None
        
        # Load or create index and data
        self._load_or_create()
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def _load_or_create(self) -> None:
        """Load existing index and data or create new ones."""
        if os.path.exists(self.index_path) and os.path.exists(self.data_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.data_path, "rb") as f:
                    self.data = pickle.load(f)
                print(f"Loaded {len(self.data)} memories from disk")
            except Exception as e:
                print(f"Error loading index/data: {e}. Creating new ones.")
                self._create_new()
        else:
            self._create_new()
    
    def _create_new(self) -> None:
        """Create new index and data structures."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.data = []
    
    def _save(self) -> None:
        """Save index and data to disk."""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.data_path, "wb") as f:
                pickle.dump(self.data, f)
        except Exception as e:
            print(f"Error saving index/data: {e}")
    
    def store_memory(
        self, 
        user_id: str, 
        text: str, 
        metadata: Optional[Dict] = None,
        auto_save: bool = True
    ) -> bool:
        """
        Store a memory with its embedding.
        
        Args:
            user_id: User identifier
            text: Text to store
            metadata: Optional additional metadata
            auto_save: Whether to save immediately to disk
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            print("Warning: Cannot store empty text")
            return False
        
        try:
            with self._lock:
                # Generate embedding
                embedding = self.model.encode([text.strip()], convert_to_numpy=True)
                
                # Add to index
                self.index.add(embedding.astype('float32'))
                
                # Store metadata
                memory_data = {
                    "user_id": user_id,
                    "text": text.strip(),
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata or {}
                }
                self.data.append(memory_data)
                
                # Save to disk
                if auto_save:
                    self._save()
                
                return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def store_batch(
        self, 
        user_id: str, 
        texts: List[str], 
        metadata_list: Optional[List[Dict]] = None
    ) -> int:
        """
        Store multiple memories at once (more efficient).
        
        Args:
            user_id: User identifier
            texts: List of texts to store
            metadata_list: Optional list of metadata dicts
            
        Returns:
            Number of successfully stored memories
        """
        if not texts:
            return 0
        
        texts = [t.strip() for t in texts if t and t.strip()]
        if not texts:
            return 0
        
        try:
            with self._lock:
                # Generate embeddings in batch
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                
                # Add to index
                self.index.add(embeddings.astype('float32'))
                
                # Store metadata
                metadata_list = metadata_list or [{}] * len(texts)
                for i, text in enumerate(texts):
                    memory_data = {
                        "user_id": user_id,
                        "text": text,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": metadata_list[i] if i < len(metadata_list) else {}
                    }
                    self.data.append(memory_data)
                
                # Save once at the end
                self._save()
                
                return len(texts)
        except Exception as e:
            print(f"Error storing batch: {e}")
            return 0
    
    def retrieve_memories(
        self, 
        user_id: str, 
        query: str, 
        k: int = 3,
        min_similarity: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieve most relevant memories for a query.
        
        Args:
            user_id: User identifier
            query: Search query
            k: Number of results to return
            min_similarity: Optional minimum similarity threshold (lower distance = higher similarity)
            
        Returns:
            List of memory dictionaries with relevance scores
        """
        if not self.data or not query.strip():
            return []
        
        try:
            with self._lock:
                # Generate query embedding
                query_embedding = self.model.encode([query.strip()], convert_to_numpy=True)
                
                # Search in index (get more results to filter by user_id)
                search_k = min(len(self.data), k * 10)  # Get 10x more to filter
                distances, indices = self.index.search(
                    query_embedding.astype('float32'), 
                    search_k
                )
                
                # Filter by user_id and compile results
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < len(self.data):
                        memory = self.data[idx]
                        
                        # Filter by user_id
                        if memory["user_id"] != user_id:
                            continue
                        
                        # Filter by similarity threshold if provided
                        if min_similarity is not None and dist > min_similarity:
                            continue
                        
                        result = {
                            **memory,
                            "distance": float(dist),
                            "similarity": 1 / (1 + float(dist))  # Convert distance to similarity score
                        }
                        results.append(result)
                        
                        # Stop when we have enough results
                        if len(results) >= k:
                            break
                
                return results
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []
    
    def retrieve_memories_text_only(
        self, 
        user_id: str, 
        query: str, 
        k: int = 3
    ) -> List[str]:
        """
        Retrieve only the text of relevant memories (backward compatible).
        
        Args:
            user_id: User identifier
            query: Search query
            k: Number of results to return
            
        Returns:
            List of memory texts
        """
        memories = self.retrieve_memories(user_id, query, k)
        return [m["text"] for m in memories]
    
    def get_user_memories(
        self, 
        user_id: str, 
        limit: Optional[int] = None,
        sort_by_time: bool = True
    ) -> List[Dict]:
        """
        Get all memories for a specific user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of memories to return
            sort_by_time: Sort by timestamp (newest first)
            
        Returns:
            List of memory dictionaries
        """
        with self._lock:
            user_memories = [m for m in self.data if m["user_id"] == user_id]
            
            if sort_by_time:
                user_memories.sort(key=lambda x: x["timestamp"], reverse=True)
            
            if limit:
                user_memories = user_memories[:limit]
            
            return user_memories
    
    def delete_user_memories(self, user_id: str) -> int:
        """
        Delete all memories for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of deleted memories
        """
        with self._lock:
            # Find indices to keep
            indices_to_keep = [i for i, m in enumerate(self.data) if m["user_id"] != user_id]
            deleted_count = len(self.data) - len(indices_to_keep)
            
            if deleted_count == 0:
                return 0
            
            # Rebuild index with remaining embeddings
            new_index = faiss.IndexFlatL2(self.dimension)
            new_data = []
            
            for idx in indices_to_keep:
                # Re-encode and add to new index
                text = self.data[idx]["text"]
                embedding = self.model.encode([text], convert_to_numpy=True)
                new_index.add(embedding.astype('float32'))
                new_data.append(self.data[idx])
            
            self.index = new_index
            self.data = new_data
            self._save()
            
            return deleted_count
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the memory store.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            user_counts = {}
            for memory in self.data:
                user_id = memory["user_id"]
                user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            return {
                "total_memories": len(self.data),
                "unique_users": len(user_counts),
                "user_memory_counts": user_counts,
                "index_size": self.index.ntotal,
                "model": self.model_name,
                "dimension": self.dimension
            }
    
    def clear_all(self) -> None:
        """Clear all memories and reset index."""
        with self._lock:
            self._create_new()
            self._save()
    
    def __len__(self) -> int:
        """Return total number of memories."""
        return len(self.data)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"VectorMemory(memories={len(self.data)}, model={self.model_name})"


# Convenience functions for backward compatibility
_global_memory = None

def _get_memory() -> VectorMemory:
    """Get or create global memory instance."""
    global _global_memory
    if _global_memory is None:
        _global_memory = VectorMemory()
    return _global_memory

def store_memory(user_id: str, text: str) -> bool:
    """Store a memory (backward compatible)."""
    return _get_memory().store_memory(user_id, text)

def retrieve_memories(user_id: str, query: str, k: int = 3) -> List[str]:
    """Retrieve memories (backward compatible)."""
    return _get_memory().retrieve_memories_text_only(user_id, query, k)