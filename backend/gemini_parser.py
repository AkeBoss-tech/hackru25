"""
JSON response parser for Gemini API responses.
Handles parsing, validation, and formatting of Gemini analysis results.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
import re
from datetime import datetime


class GeminiResponseParser:
    """
    Parser for Gemini API responses with JSON validation and formatting.
    
    Features:
    - JSON extraction from mixed responses
    - Response validation
    - Error handling and recovery
    - Result formatting and standardization
    """
    
    def __init__(self):
        """Initialize the response parser."""
        self.logger = logging.getLogger(__name__)
        
        # Expected schema for different analysis types
        self.schemas = {
            'comprehensive': {
                'required_fields': ['image_description', 'subjects', 'objects', 'activities', 'scene_analysis'],
                'optional_fields': ['timestamp_estimate', 'location_context', 'technical_quality']
            },
            'objects': {
                'required_fields': ['detected_items'],
                'optional_fields': ['object_counts']
            },
            'activities': {
                'required_fields': ['activities'],
                'optional_fields': ['behaviors']
            },
            'description': {
                'required_fields': ['scene_description'],
                'optional_fields': ['key_elements', 'environment', 'time_context', 'notable_details']
            }
        }
    
    def parse_response(
        self,
        raw_response: str,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Parse raw Gemini response into structured JSON.
        
        Args:
            raw_response: Raw text response from Gemini
            analysis_type: Type of analysis performed
            
        Returns:
            Parsed and validated response dictionary
        """
        try:
            # Extract JSON from response
            json_content = self._extract_json(raw_response)
            if not json_content:
                return self._create_error_response("No valid JSON found in response", raw_response)
            
            # Parse JSON
            try:
                parsed_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                return self._create_error_response(f"JSON decode error: {e}", raw_response)
            
            # Validate response
            validation_result = self._validate_response(parsed_data, analysis_type)
            if not validation_result['valid']:
                parsed_data['_validation_errors'] = validation_result['errors']
            
            # Add metadata
            parsed_data['_parser_metadata'] = {
                'analysis_type': analysis_type,
                'parsed_at': datetime.now().isoformat(),
                'validation_status': 'valid' if validation_result['valid'] else 'warnings'
            }
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing Gemini response: {e}")
            return self._create_error_response(f"Parser error: {e}", raw_response)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON content from mixed text response.
        
        Args:
            text: Raw response text
            
        Returns:
            Extracted JSON string or None
        """
        try:
            # Remove markdown code blocks
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
            text = text.strip()
            
            # Try to find JSON object boundaries
            json_start = text.find('{')
            json_end = text.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_content = text[json_start:json_end + 1]
                
                # Basic validation - check if it looks like JSON
                if json_content.startswith('{') and json_content.endswith('}'):
                    return json_content
            
            # If no clear JSON boundaries, try the whole text
            if text.startswith('{') and text.endswith('}'):
                return text
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting JSON: {e}")
            return None
    
    def _validate_response(self, data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """
        Validate response against expected schema.
        
        Args:
            data: Parsed response data
            analysis_type: Type of analysis
            
        Returns:
            Validation result with status and errors
        """
        schema = self.schemas.get(analysis_type, {})
        required_fields = schema.get('required_fields', [])
        optional_fields = schema.get('optional_fields', [])
        
        errors = []
        warnings = []
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif data[field] is None:
                warnings.append(f"Required field is null: {field}")
        
        # Validate field types and content
        self._validate_field_types(data, analysis_type, errors, warnings)
        
        # Validate specific analysis type content
        if analysis_type == 'comprehensive':
            self._validate_comprehensive_response(data, errors, warnings)
        elif analysis_type == 'objects':
            self._validate_objects_response(data, errors, warnings)
        elif analysis_type == 'activities':
            self._validate_activities_response(data, errors, warnings)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_field_types(self, data: Dict[str, Any], analysis_type: str, errors: List[str], warnings: List[str]):
        """Validate field types for different analysis types."""
        try:
            # Validate subjects field (if present)
            if 'subjects' in data:
                subjects = data['subjects']
                if not isinstance(subjects, list):
                    errors.append("'subjects' must be a list")
                else:
                    for i, subject in enumerate(subjects):
                        if not isinstance(subject, dict):
                            errors.append(f"Subject {i} must be a dictionary")
                        else:
                            required_subject_fields = ['id', 'type', 'description']
                            for field in required_subject_fields:
                                if field not in subject:
                                    warnings.append(f"Subject {i} missing field: {field}")
            
            # Validate objects field (if present)
            if 'objects' in data:
                objects = data['objects']
                if not isinstance(objects, list):
                    errors.append("'objects' must be a list")
                else:
                    for i, obj in enumerate(objects):
                        if not isinstance(obj, dict):
                            errors.append(f"Object {i} must be a dictionary")
            
            # Validate activities field (if present)
            if 'activities' in data:
                activities = data['activities']
                if not isinstance(activities, list):
                    errors.append("'activities' must be a list")
                else:
                    for i, activity in enumerate(activities):
                        if not isinstance(activity, dict):
                            errors.append(f"Activity {i} must be a dictionary")
            
            # Validate scene_analysis field (if present)
            if 'scene_analysis' in data:
                scene_analysis = data['scene_analysis']
                if not isinstance(scene_analysis, dict):
                    errors.append("'scene_analysis' must be a dictionary")
            
        except Exception as e:
            errors.append(f"Field type validation error: {e}")
    
    def _validate_comprehensive_response(self, data: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate comprehensive analysis response."""
        try:
            # Validate scene_analysis structure
            if 'scene_analysis' in data and isinstance(data['scene_analysis'], dict):
                scene_analysis = data['scene_analysis']
                expected_fields = ['overall_mood', 'safety_assessment']
                for field in expected_fields:
                    if field not in scene_analysis:
                        warnings.append(f"scene_analysis missing field: {field}")
            
            # Validate technical_quality structure
            if 'technical_quality' in data and isinstance(data['technical_quality'], dict):
                tech_quality = data['technical_quality']
                expected_fields = ['image_clarity', 'lighting_conditions']
                for field in expected_fields:
                    if field not in tech_quality:
                        warnings.append(f"technical_quality missing field: {field}")
            
        except Exception as e:
            warnings.append(f"Comprehensive validation warning: {e}")
    
    def _validate_objects_response(self, data: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate objects analysis response."""
        try:
            if 'object_counts' in data and isinstance(data['object_counts'], dict):
                counts = data['object_counts']
                expected_count_fields = ['people', 'vehicles', 'objects']
                for field in expected_count_fields:
                    if field not in counts:
                        warnings.append(f"object_counts missing field: {field}")
                    elif not isinstance(counts[field], int):
                        warnings.append(f"object_counts.{field} must be an integer")
            
        except Exception as e:
            warnings.append(f"Objects validation warning: {e}")
    
    def _validate_activities_response(self, data: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate activities analysis response."""
        try:
            if 'behaviors' in data and isinstance(data['behaviors'], list):
                for i, behavior in enumerate(data['behaviors']):
                    if not isinstance(behavior, dict):
                        warnings.append(f"Behavior {i} must be a dictionary")
                    else:
                        expected_fields = ['subject', 'behavior', 'assessment']
                        for field in expected_fields:
                            if field not in behavior:
                                warnings.append(f"Behavior {i} missing field: {field}")
            
        except Exception as e:
            warnings.append(f"Activities validation warning: {e}")
    
    def _create_error_response(self, error_message: str, raw_response: str) -> Dict[str, Any]:
        """Create error response structure."""
        return {
            'error': True,
            'error_message': error_message,
            'raw_response': raw_response,
            '_parser_metadata': {
                'parsed_at': datetime.now().isoformat(),
                'validation_status': 'error'
            }
        }
    
    def format_analysis_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of analysis results.
        
        Args:
            analysis_result: Full analysis result
            
        Returns:
            Formatted summary
        """
        try:
            summary = {
                'analysis_type': analysis_result.get('_parser_metadata', {}).get('analysis_type', 'unknown'),
                'timestamp': analysis_result.get('_parser_metadata', {}).get('parsed_at'),
                'validation_status': analysis_result.get('_parser_metadata', {}).get('validation_status', 'unknown')
            }
            
            # Extract key information based on analysis type
            if 'image_description' in analysis_result:
                summary['description'] = analysis_result['image_description'][:200] + "..." if len(analysis_result['image_description']) > 200 else analysis_result['image_description']
            
            if 'subjects' in analysis_result:
                subjects = analysis_result['subjects']
                summary['subject_count'] = len(subjects)
                summary['subject_types'] = list(set(subject.get('type', 'unknown') for subject in subjects))
            
            if 'objects' in analysis_result:
                objects = analysis_result['objects']
                summary['object_count'] = len(objects)
                summary['object_types'] = list(set(obj.get('type', 'unknown') for obj in objects))
            
            if 'activities' in analysis_result:
                activities = analysis_result['activities']
                summary['activity_count'] = len(activities)
                summary['notable_activities'] = [act.get('description', '') for act in activities[:3]]  # First 3 activities
            
            if 'scene_analysis' in analysis_result:
                scene = analysis_result['scene_analysis']
                summary['safety_assessment'] = scene.get('safety_assessment', 'unknown')
                summary['overall_mood'] = scene.get('overall_mood', 'unknown')
            
            # Add validation info if present
            if '_validation_errors' in analysis_result:
                summary['validation_errors'] = analysis_result['_validation_errors']
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating analysis summary: {e}")
            return {
                'error': True,
                'error_message': f"Summary creation failed: {e}",
                'analysis_type': 'unknown'
            }
    
    def extract_key_insights(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        Extract key insights from analysis result.
        
        Args:
            analysis_result: Analysis result dictionary
            
        Returns:
            List of key insights
        """
        insights = []
        
        try:
            # Extract insights from scene analysis
            if 'scene_analysis' in analysis_result:
                scene = analysis_result['scene_analysis']
                
                if scene.get('safety_assessment') in ['potential_concern', 'requires_attention']:
                    insights.append(f"Safety concern detected: {scene.get('safety_assessment')}")
                
                if scene.get('overall_mood') == 'concerning':
                    insights.append("Scene mood assessed as concerning")
                
                if scene.get('notable_events'):
                    insights.extend([f"Notable event: {event}" for event in scene['notable_events'][:3]])
            
            # Extract insights from activities
            if 'activities' in analysis_result:
                for activity in analysis_result['activities']:
                    if activity.get('significance') in ['suspicious', 'concerning']:
                        insights.append(f"Suspicious activity: {activity.get('description', 'Unknown')}")
            
            # Extract insights from subjects
            if 'subjects' in analysis_result:
                for subject in analysis_result['subjects']:
                    if subject.get('actions') and 'running' in subject['actions'].lower():
                        insights.append(f"Person running detected: {subject.get('description', 'Unknown')}")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error extracting insights: {e}")
            return [f"Error extracting insights: {e}"]
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get parser validation statistics."""
        return {
            'supported_analysis_types': list(self.schemas.keys()),
            'parser_version': '1.0.0',
            'features': [
                'JSON extraction',
                'Schema validation',
                'Error recovery',
                'Summary formatting',
                'Insight extraction'
            ]
        }
