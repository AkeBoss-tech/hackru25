"""
Gemini API service for image analysis and description generation.
Provides AI-powered analysis of snapshots captured by the timeline manager.
"""

import os
import json
import base64
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import io


class GeminiImageAnalyzer:
    """
    Service for analyzing images using Google's Gemini 2.5 Flash model.
    
    Features:
    - Image description generation
    - Object and subject tracking
    - Activity analysis
    - JSON-formatted responses
    - Batch processing capabilities
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini Image Analyzer.
        
        Args:
            api_key: Google AI API key (if None, will try to load from environment)
            model_name: Gemini model to use
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        
        # Get API key
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        try:
            self.model = genai.GenerativeModel(model_name)
            self.logger.info(f"Gemini Image Analyzer initialized with model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini model: {e}")
            raise
    
    def _encode_image_to_base64(self, image_path: Union[str, Path]) -> Optional[str]:
        """
        Encode image to base64 string for API transmission.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string or None if error
        """
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error encoding image {image_path}: {e}")
            return None
    
    def _load_image(self, image_path: Union[str, Path]) -> Optional[Image.Image]:
        """
        Load image from file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            PIL Image object or None if error
        """
        try:
            return Image.open(image_path)
        except Exception as e:
            self.logger.error(f"Error loading image {image_path}: {e}")
            return None
    
    def _create_analysis_prompt(self, analysis_type: str = "comprehensive") -> str:
        """
        Create prompt for image analysis based on type.
        
        Args:
            analysis_type: Type of analysis ("comprehensive", "objects", "activities", "description")
            
        Returns:
            Formatted prompt string
        """
        prompts = {
            "comprehensive": """
            Analyze this surveillance/security camera image and provide a detailed JSON response with the following structure:
            
            {
                "image_description": "Detailed description of the scene",
                "timestamp_estimate": "Estimated time of day if visible",
                "location_context": "Inferred location type (indoor/outdoor, specific setting)",
                "subjects": [
                    {
                        "id": "unique_identifier",
                        "type": "person/vehicle/object",
                        "description": "Detailed description",
                        "position": "location_in_frame",
                        "actions": "what_they_are_doing",
                        "attributes": ["key", "characteristics"],
                        "confidence": 0.0-1.0
                    }
                ],
                "objects": [
                    {
                        "id": "unique_identifier", 
                        "type": "object_category",
                        "description": "Detailed description",
                        "position": "location_in_frame",
                        "purpose": "likely_use_or_function",
                        "confidence": 0.0-1.0
                    }
                ],
                "activities": [
                    {
                        "description": "Activity description",
                        "participants": ["subject_ids"],
                        "objects_involved": ["object_ids"],
                        "significance": "normal/suspicious/concerning",
                        "confidence": 0.0-1.0
                    }
                ],
                "scene_analysis": {
                    "overall_mood": "calm/active/concerning",
                    "safety_assessment": "safe/potential_concern/requires_attention",
                    "notable_events": ["list", "of", "notable", "things"],
                    "recommendations": ["any", "recommended", "actions"]
                },
                "technical_quality": {
                    "image_clarity": "excellent/good/fair/poor",
                    "lighting_conditions": "optimal/good/adequate/poor",
                    "visibility_issues": ["any", "issues", "affecting", "analysis"]
                }
            }
            
            Be thorough and specific. If you cannot determine something, use null or "unknown" rather than guessing.
            """,
            
            "objects": """
            Analyze this image and identify all objects, people, and vehicles. Return a JSON response:
            
            {
                "detected_items": [
                    {
                        "id": "unique_id",
                        "type": "person/vehicle/object",
                        "class": "specific_classification",
                        "description": "detailed_description",
                        "position": "approximate_location",
                        "size": "relative_size",
                        "confidence": 0.0-1.0
                    }
                ],
                "object_counts": {
                    "people": 0,
                    "vehicles": 0,
                    "objects": 0
                }
            }
            """,
            
            "activities": """
            Analyze this image for activities and behaviors. Return a JSON response:
            
            {
                "activities": [
                    {
                        "description": "what_is_happening",
                        "participants": ["who_is_involved"],
                        "location": "where_in_frame",
                        "significance": "normal/suspicious/notable",
                        "confidence": 0.0-1.0
                    }
                ],
                "behaviors": [
                    {
                        "subject": "who",
                        "behavior": "what_they_are_doing", 
                        "context": "why_or_how",
                        "assessment": "normal/concerning/notable"
                    }
                ]
            }
            """,
            
            "description": """
            Provide a detailed description of this image. Return a JSON response:
            
            {
                "scene_description": "comprehensive_description_of_what_you_see",
                "key_elements": ["list", "of", "main", "elements"],
                "environment": "setting_description",
                "time_context": "time_of_day_if_visible",
                "notable_details": ["any", "specific", "notable", "details"]
            }
            """
        }
        
        return prompts.get(analysis_type, prompts["comprehensive"])
    
    def analyze_image(
        self,
        image_path: Union[str, Path],
        analysis_type: str = "comprehensive",
        custom_prompt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single image using Gemini.
        
        Args:
            image_path: Path to image file
            analysis_type: Type of analysis ("comprehensive", "objects", "activities", "description")
            custom_prompt: Custom prompt to override default
            
        Returns:
            Dictionary with analysis results or None if error
        """
        try:
            # Load image
            image = self._load_image(image_path)
            if not image:
                return None
            
            # Get prompt
            prompt = custom_prompt or self._create_analysis_prompt(analysis_type)
            
            # Generate content
            self.logger.info(f"Analyzing image: {image_path}")
            response = self.model.generate_content([prompt, image])
            
            if not response.text:
                self.logger.error("Empty response from Gemini")
                return None
            
            # Parse JSON response
            try:
                # Clean the response text to extract JSON
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                analysis_result = json.loads(response_text)
                
                # Add metadata
                analysis_result['_metadata'] = {
                    'image_path': str(image_path),
                    'analysis_type': analysis_type,
                    'model_used': self.model_name,
                    'timestamp': self._get_current_timestamp()
                }
                
                self.logger.info(f"Successfully analyzed image: {image_path}")
                return analysis_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                self.logger.error(f"Raw response: {response.text}")
                return {
                    'error': 'JSON parsing failed',
                    'raw_response': response.text,
                    '_metadata': {
                        'image_path': str(image_path),
                        'analysis_type': analysis_type,
                        'model_used': self.model_name,
                        'timestamp': self._get_current_timestamp()
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing image {image_path}: {e}")
            return None
    
    def analyze_snapshot_pair(
        self,
        raw_image_path: Union[str, Path],
        annotated_image_path: Union[str, Path],
        analysis_type: str = "comprehensive"
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze both raw and annotated versions of a snapshot.
        
        Args:
            raw_image_path: Path to raw snapshot
            annotated_image_path: Path to annotated snapshot
            analysis_type: Type of analysis
            
        Returns:
            Combined analysis results
        """
        try:
            # Analyze raw image
            raw_analysis = self.analyze_image(raw_image_path, analysis_type)
            if not raw_analysis:
                return None
            
            # Analyze annotated image
            annotated_analysis = self.analyze_image(annotated_image_path, analysis_type)
            if not annotated_analysis:
                return raw_analysis
            
            # Combine results
            combined_result = {
                'raw_image_analysis': raw_analysis,
                'annotated_image_analysis': annotated_analysis,
                'comparison': self._compare_analyses(raw_analysis, annotated_analysis),
                '_metadata': {
                    'raw_image_path': str(raw_image_path),
                    'annotated_image_path': str(annotated_image_path),
                    'analysis_type': analysis_type,
                    'model_used': self.model_name,
                    'timestamp': self._get_current_timestamp()
                }
            }
            
            return combined_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing snapshot pair: {e}")
            return None
    
    def batch_analyze_images(
        self,
        image_paths: List[Union[str, Path]],
        analysis_type: str = "comprehensive",
        max_workers: int = 3
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Analyze multiple images in batch.
        
        Args:
            image_paths: List of image file paths
            analysis_type: Type of analysis
            max_workers: Maximum concurrent workers (Gemini has rate limits)
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i, image_path in enumerate(image_paths):
            self.logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
            
            try:
                result = self.analyze_image(image_path, analysis_type)
                results.append(result)
                
                # Add small delay to respect rate limits
                if i < len(image_paths) - 1:
                    import time
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.error(f"Error in batch processing {image_path}: {e}")
                results.append(None)
        
        return results
    
    def _compare_analyses(self, analysis1: Dict, analysis2: Dict) -> Dict[str, Any]:
        """Compare two analysis results."""
        comparison = {
            'differences_noted': [],
            'consistency_score': 0.0,
            'additional_detections': [],
            'missed_detections': []
        }
        
        try:
            # Simple comparison logic - can be enhanced
            subjects1 = analysis1.get('subjects', [])
            subjects2 = analysis2.get('subjects', [])
            
            if len(subjects1) != len(subjects2):
                comparison['differences_noted'].append(f"Subject count differs: {len(subjects1)} vs {len(subjects2)}")
            
            # Calculate basic consistency score
            if subjects1 and subjects2:
                comparison['consistency_score'] = 0.8  # Placeholder logic
            
        except Exception as e:
            self.logger.error(f"Error comparing analyses: {e}")
        
        return comparison
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        output_path: Union[str, Path]
    ) -> bool:
        """
        Save analysis result to JSON file.
        
        Args:
            analysis_result: Analysis result dictionary
            output_path: Path to save JSON file
            
        Returns:
            True if successful
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(analysis_result, f, indent=2)
            
            self.logger.info(f"Analysis result saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving analysis result: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            'model_name': self.model_name,
            'api_key_configured': bool(self.api_key),
            'api_key_preview': f"{self.api_key[:8]}..." if self.api_key else None
        }


class GeminiTimelineAnalyzer:
    """
    Specialized analyzer for timeline events and snapshots.
    Integrates with TimelineManager to provide AI analysis of captured events.
    """
    
    def __init__(self, timeline_manager, gemini_analyzer: Optional[GeminiImageAnalyzer] = None):
        """
        Initialize Gemini Timeline Analyzer.
        
        Args:
            timeline_manager: TimelineManager instance
            gemini_analyzer: GeminiImageAnalyzer instance (will create new if None)
        """
        self.timeline_manager = timeline_manager
        self.gemini_analyzer = gemini_analyzer or GeminiImageAnalyzer()
        self.logger = logging.getLogger(__name__)
        
        # Analysis results storage
        self.analysis_results: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Gemini Timeline Analyzer initialized")
    
    def analyze_event(
        self,
        event_id: str,
        analysis_type: str = "comprehensive"
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a specific timeline event.
        
        Args:
            event_id: Timeline event ID
            analysis_type: Type of analysis
            
        Returns:
            Analysis result or None if error
        """
        try:
            # Get event from timeline manager
            event = self.timeline_manager.get_event_by_id(event_id)
            if not event:
                self.logger.error(f"Event not found: {event_id}")
                return None
            
            snapshot_path = event.get('snapshot_path')
            if not snapshot_path or not os.path.exists(snapshot_path):
                self.logger.error(f"Snapshot not found for event {event_id}: {snapshot_path}")
                return None
            
            # Get raw snapshot path if available
            raw_snapshot_path = self.timeline_manager.get_raw_snapshot_path(snapshot_path)
            
            # Perform analysis
            if raw_snapshot_path and os.path.exists(raw_snapshot_path):
                # Analyze both raw and annotated
                analysis_result = self.gemini_analyzer.analyze_snapshot_pair(
                    raw_snapshot_path, snapshot_path, analysis_type
                )
            else:
                # Analyze only annotated
                analysis_result = self.gemini_analyzer.analyze_image(
                    snapshot_path, analysis_type
                )
            
            if analysis_result:
                # Store result
                self.analysis_results[event_id] = analysis_result
                
                # Add timeline event metadata
                analysis_result['_timeline_event'] = event
                
                self.logger.info(f"Analyzed timeline event: {event_id}")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing timeline event {event_id}: {e}")
            return None
    
    def analyze_recent_events(
        self,
        limit: int = 10,
        analysis_type: str = "comprehensive"
    ) -> List[Dict[str, Any]]:
        """
        Analyze recent timeline events.
        
        Args:
            limit: Maximum number of events to analyze
            analysis_type: Type of analysis
            
        Returns:
            List of analysis results
        """
        try:
            # Get recent events
            recent_events = self.timeline_manager.get_events(limit=limit)
            
            analysis_results = []
            for event in recent_events:
                event_id = event['event_id']
                result = self.analyze_event(event_id, analysis_type)
                if result:
                    analysis_results.append(result)
            
            self.logger.info(f"Analyzed {len(analysis_results)} recent events")
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error analyzing recent events: {e}")
            return []
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of all analysis results."""
        return {
            'total_analyses': len(self.analysis_results),
            'analysis_types': list(set(
                result.get('_metadata', {}).get('analysis_type', 'unknown')
                for result in self.analysis_results.values()
            )),
            'recent_analyses': list(self.analysis_results.keys())[-5:],
            'model_info': self.gemini_analyzer.get_model_info()
        }
    
    def clear_analysis_results(self):
        """Clear all stored analysis results."""
        self.analysis_results.clear()
        self.logger.info("Analysis results cleared")
