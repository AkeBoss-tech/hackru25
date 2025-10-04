"""
Vector Database for Timeline Events and Gemini Reports
Provides semantic search and similarity matching for surveillance data.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
import threading
import time


class VectorDatabase:
    """
    Vector database for storing and searching timeline events with semantic meaning.
    
    Features:
    - Semantic search of Gemini reports
    - Similarity matching for events
    - Automatic embedding generation
    - Persistent storage
    - Real-time indexing
    """
    
    def __init__(self, persist_directory: str = "vector_db", collection_name: str = "timeline_events"):
        """
        Initialize Vector Database.
        
        Args:
            persist_directory: Directory to store vector database
            collection_name: Name of the collection to store events
        """
        self.logger = logging.getLogger(__name__)
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        
        # Create persist directory
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize embedding model (lightweight, fast model)
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.logger.info("Embedding model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise
        
        # Initialize ChromaDB client
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Timeline events with semantic embeddings"}
            )
            
            self.logger.info(f"Vector database initialized: {collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
        
        # Statistics
        self.stats = {
            'total_vectors': 0,
            'total_searches': 0,
            'last_index_time': None,
            'embedding_model': 'all-MiniLM-L6-v2'
        }
        
        # Thread safety
        self.lock = threading.Lock()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using sentence transformer.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return []
    
    def _create_searchable_text(self, event_data: Dict, gemini_report: Optional[Dict] = None) -> str:
        """
        Create searchable text from event data and Gemini report.
        
        Args:
            event_data: Timeline event data
            gemini_report: Optional Gemini AI report
            
        Returns:
            Combined searchable text
        """
        text_parts = []
        
        # Add Gemini report content if available
        if gemini_report:
            if 'summary' in gemini_report:
                text_parts.append(f"Summary: {gemini_report['summary']}")
            if 'activity' in gemini_report:
                text_parts.append(f"Activity: {gemini_report['activity']}")
            if 'objects_detected' in gemini_report:
                objects = ', '.join(gemini_report['objects_detected'])
                text_parts.append(f"Objects: {objects}")
        
        # Add timeline event metadata
        if 'objects' in event_data:
            for obj in event_data['objects']:
                if 'class_name' in obj:
                    text_parts.append(f"Detected: {obj['class_name']}")
                if 'track_id' in obj and obj['track_id'] is not None:
                    text_parts.append(f"Object ID: {obj['track_id']}")
        
        # Add video source
        if 'video_source' in event_data:
            text_parts.append(f"Source: {event_data['video_source']}")
        
        # Add timestamp context
        if 'timestamp' in event_data:
            try:
                dt = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
                time_str = dt.strftime("%A %B %d, %Y at %I:%M %p")
                text_parts.append(f"Time: {time_str}")
            except:
                text_parts.append(f"Time: {event_data['timestamp']}")
        
        return " | ".join(text_parts)
    
    def add_event(self, event_id: str, event_data: Dict, gemini_report: Optional[Dict] = None):
        """
        Add a timeline event to the vector database.
        
        Args:
            event_id: Unique event identifier
            event_data: Timeline event data
            gemini_report: Optional Gemini AI report
        """
        try:
            with self.lock:
                # Create searchable text
                searchable_text = self._create_searchable_text(event_data, gemini_report)
                
                if not searchable_text:
                    self.logger.warning(f"No searchable text for event {event_id}")
                    return
                
                # Generate embedding
                embedding = self._generate_embedding(searchable_text)
                if not embedding:
                    self.logger.error(f"Failed to generate embedding for event {event_id}")
                    return
                
                # Prepare metadata
                metadata = {
                    'event_id': event_id,
                    'timestamp': event_data.get('timestamp', ''),
                    'video_source': event_data.get('video_source', ''),
                    'object_count': len(event_data.get('objects', [])),
                    'has_gemini_report': gemini_report is not None,
                    'snapshot_path': event_data.get('snapshot_path', ''),
                    'frame_number': event_data.get('frame_number', 0)
                }
                
                # Add Gemini report metadata if available
                if gemini_report:
                    metadata.update({
                        'gemini_summary': gemini_report.get('summary', ''),
                        'gemini_confidence': gemini_report.get('confidence', ''),
                        'objects_detected': ', '.join(gemini_report.get('objects_detected', [])),
                        'object_ids': ', '.join(gemini_report.get('object_ids', []))
                    })
                
                # Add to collection
                self.collection.add(
                    ids=[event_id],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    documents=[searchable_text]
                )
                
                # Update stats
                self.stats['total_vectors'] = self.collection.count()
                self.stats['last_index_time'] = datetime.now().isoformat()
                
                self.logger.debug(f"Added event to vector database: {event_id}")
                
        except Exception as e:
            self.logger.error(f"Error adding event {event_id} to vector database: {e}")
    
    def search_similar_events(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.7,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for events similar to the query.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of similar events with scores
        """
        try:
            with self.lock:
                # Generate embedding for query
                query_embedding = self._generate_embedding(query)
                if not query_embedding:
                    self.logger.error("Failed to generate embedding for search query")
                    return []
                
                # Build where clause for filtering
                where_clause = None
                if filter_metadata:
                    where_clause = filter_metadata
                
                # Search collection
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where_clause
                )
                
                # Process results
                similar_events = []
                if results['ids'] and results['ids'][0]:
                    for i, event_id in enumerate(results['ids'][0]):
                        similarity = 1 - results['distances'][0][i]  # Convert distance to similarity
                        
                        if similarity >= min_similarity:
                            similar_events.append({
                                'event_id': event_id,
                                'similarity': similarity,
                                'metadata': results['metadatas'][0][i],
                                'document': results['documents'][0][i]
                            })
                
                # Update stats
                self.stats['total_searches'] += 1
                
                self.logger.debug(f"Found {len(similar_events)} similar events for query: {query}")
                return similar_events
                
        except Exception as e:
            self.logger.error(f"Error searching vector database: {e}")
            return []
    
    def search_by_gemini_report(self, gemini_report: Dict, limit: int = 10) -> List[Dict]:
        """
        Search for events similar to a Gemini report.
        
        Args:
            gemini_report: Gemini AI report to search for
            limit: Maximum number of results
            
        Returns:
            List of similar events
        """
        # Create search query from Gemini report
        query_parts = []
        if 'summary' in gemini_report:
            query_parts.append(gemini_report['summary'])
        if 'activity' in gemini_report:
            query_parts.append(gemini_report['activity'])
        if 'objects_detected' in gemini_report:
            query_parts.append(' '.join(gemini_report['objects_detected']))
        
        query = ' '.join(query_parts)
        return self.search_similar_events(query, limit)
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """
        Get a specific event by ID.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Event data or None if not found
        """
        try:
            results = self.collection.get(ids=[event_id])
            if results['ids']:
                return {
                    'event_id': results['ids'][0],
                    'metadata': results['metadatas'][0],
                    'document': results['documents'][0]
                }
        except Exception as e:
            self.logger.error(f"Error getting event {event_id}: {e}")
        
        return None
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """
        Get recent events from the database.
        
        Args:
            limit: Maximum number of events
            
        Returns:
            List of recent events
        """
        try:
            results = self.collection.get(limit=limit)
            events = []
            
            for i, event_id in enumerate(results['ids']):
                events.append({
                    'event_id': event_id,
                    'metadata': results['metadatas'][i],
                    'document': results['documents'][i]
                })
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting recent events: {e}")
            return []
    
    def update_event(self, event_id: str, event_data: Dict, gemini_report: Optional[Dict] = None):
        """
        Update an existing event in the vector database.
        
        Args:
            event_id: Event identifier
            event_data: Updated event data
            gemini_report: Updated Gemini report
        """
        try:
            # Remove existing event
            self.delete_event(event_id)
            
            # Add updated event
            self.add_event(event_id, event_data, gemini_report)
            
        except Exception as e:
            self.logger.error(f"Error updating event {event_id}: {e}")
    
    def delete_event(self, event_id: str):
        """
        Delete an event from the vector database.
        
        Args:
            event_id: Event identifier
        """
        try:
            with self.lock:
                self.collection.delete(ids=[event_id])
                self.stats['total_vectors'] = self.collection.count()
                
        except Exception as e:
            self.logger.error(f"Error deleting event {event_id}: {e}")
    
    def clear_database(self):
        """Clear all events from the database."""
        try:
            with self.lock:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Timeline events with semantic embeddings"}
                )
                self.stats['total_vectors'] = 0
                self.stats['total_searches'] = 0
                
        except Exception as e:
            self.logger.error(f"Error clearing database: {e}")
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            with self.lock:
                self.stats['total_vectors'] = self.collection.count()
                return self.stats.copy()
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return self.stats.copy()


# Global instance
_vector_db = None

def get_vector_database() -> VectorDatabase:
    """Get global vector database instance."""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDatabase()
    return _vector_db

def initialize_vector_database(persist_directory: str = "vector_db", collection_name: str = "timeline_events"):
    """Initialize vector database with custom settings."""
    global _vector_db
    _vector_db = VectorDatabase(persist_directory, collection_name)
    return _vector_db
