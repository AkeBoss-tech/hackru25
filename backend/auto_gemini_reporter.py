"""
Auto-Gemini Reporter for Timeline Snapshots
Automatically generates brief AI reports for each captured snapshot.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import time
import threading
from queue import Queue

# Import Gemini modules
from .gemini_service import GeminiImageAnalyzer
from .gemini_config import GeminiConfig

class AutoGeminiReporter:
    """
    Automatically generates brief AI reports for timeline snapshots.
    Designed to be cost-effective with minimal token usage.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Auto Gemini Reporter.
        
        Args:
            api_key: Google AI API key (if None, will try to load from environment)
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize config
        self.config = GeminiConfig()
        
        # Get API key from environment
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            self.logger.warning("No Gemini API key found in environment. Auto-reporting disabled.")
            self.logger.info("Please add GEMINI_API_KEY to your .env file")
            self.enabled = False
            return
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        try:
            # Use the model name from config
            model_name = self.config.model_name
            self.model = genai.GenerativeModel(model_name)
            self.enabled = True
            self.logger.info(f"Auto Gemini Reporter initialized successfully with model: {model_name}")
        except Exception as e:
            model_name = self.config.model_name if hasattr(self, 'config') else 'unknown'
            self.logger.error(f"Failed to initialize Gemini model {model_name}: {e}")
            self.enabled = False
            return
        
        # Report storage
        self.reports = {}
        self.report_queue = Queue()
        
        # Start background processor
        self.processor_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processor_thread.start()
        
        # Statistics
        self.stats = {
            'total_reports': 0,
            'successful_reports': 0,
            'failed_reports': 0,
            'total_cost_estimate': 0.0,
            'last_report_time': None
        }
    
    def _create_brief_prompt(self, event_data: Dict) -> str:
        """
        Create a cost-effective, brief prompt for snapshot analysis.
        
        Args:
            event_data: Timeline event data
            
        Returns:
            Optimized prompt string
        """
        # Extract object IDs from detection data
        object_ids = []
        object_types = []
        
        for obj in event_data.get('objects', []):
            if 'track_id' in obj and obj['track_id'] is not None:
                object_ids.append(str(obj['track_id']))
            if 'class_name' in obj:
                object_types.append(obj['class_name'])
        
        # Very brief, token-efficient prompt
        prompt = f"""Analyze this surveillance image. Provide a brief report in JSON format:

{{
  "summary": "Brief 1-sentence description",
  "objects_detected": {object_types},
  "object_ids": {object_ids},
  "activity": "Brief activity description",
  "confidence": "high/medium/low"
}}

Keep response under 100 words. Focus on relevant objects and activities."""

        return prompt
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for Gemini API call.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        # Gemini 1.5 Flash pricing (as of 2024)
        input_cost_per_1k = 0.000075  # $0.075 per 1M tokens
        output_cost_per_1k = 0.0003   # $0.30 per 1M tokens
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost
    
    def _process_queue(self):
        """Background thread to process report queue."""
        while True:
            try:
                if not self.report_queue.empty():
                    event_data, snapshot_path = self.report_queue.get(timeout=1)
                    self._generate_report(event_data, snapshot_path)
                    self.report_queue.task_done()
                else:
                    time.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                self.logger.error(f"Error in report processor: {e}")
                time.sleep(1)
    
    def _generate_report(self, event_data: Dict, snapshot_path: str):
        """
        Generate AI report for a snapshot.
        
        Args:
            event_data: Timeline event data
            snapshot_path: Path to snapshot image
        """
        if not self.enabled:
            return
        
        try:
            # Load image
            image = Image.open(snapshot_path)
            
            # Create brief prompt
            prompt = self._create_brief_prompt(event_data)
            
            # Generate content
            response = self.model.generate_content([prompt, image])
            
            if not response.text:
                self.logger.error("Empty response from Gemini")
                self.stats['failed_reports'] += 1
                return
            
            # Parse response
            try:
                # Clean response text
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                report_data = json.loads(response_text)
                
                # Add metadata
                event_id = event_data.get('event_id', 'unknown')
                report_data['_metadata'] = {
                    'event_id': event_id,
                    'snapshot_path': snapshot_path,
                    'timestamp': datetime.now().isoformat(),
                    'model_used': self.config.model_name
                }
                
                # Store report
                self.reports[event_id] = report_data
                
                # Add to vector database
                try:
                    from .vector_database import get_vector_database
                    vector_db = get_vector_database()
                    vector_db.add_event(event_id, event_data, report_data)
                    self.logger.debug(f"Added event {event_id} to vector database")
                except Exception as e:
                    self.logger.debug(f"Vector database not available: {e}")
                
                # Update stats
                self.stats['total_reports'] += 1
                self.stats['successful_reports'] += 1
                self.stats['last_report_time'] = datetime.now().isoformat()
                
                # Estimate cost (rough calculation)
                estimated_tokens = len(prompt.split()) + len(response.text.split())
                cost_estimate = self._estimate_cost(estimated_tokens, estimated_tokens // 2)
                self.stats['total_cost_estimate'] += cost_estimate
                
                self.logger.info(f"Generated report for event {event_id}")
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse Gemini response: {e}")
                self.stats['failed_reports'] += 1
                
        except Exception as e:
            self.logger.error(f"Error generating report for {snapshot_path}: {e}")
            self.stats['failed_reports'] += 1
    
    def queue_report(self, event_data: Dict, snapshot_path: str):
        """
        Queue a snapshot for AI report generation.
        
        Args:
            event_data: Timeline event data
            snapshot_path: Path to snapshot image
        """
        if not self.enabled:
            self.logger.debug("Gemini reporting disabled, skipping report generation")
            return
        
        if not os.path.exists(snapshot_path):
            self.logger.error(f"Snapshot not found: {snapshot_path}")
            return
        
        # Add to queue for background processing
        self.report_queue.put((event_data, snapshot_path))
        self.logger.debug(f"Queued report for event {event_data.get('event_id', 'unknown')}")
    
    def get_report(self, event_id: str) -> Optional[Dict]:
        """
        Get AI report for a specific event.
        
        Args:
            event_id: Timeline event ID
            
        Returns:
            Report data or None if not found
        """
        return self.reports.get(event_id)
    
    def get_recent_reports(self, limit: int = 10) -> List[Dict]:
        """
        Get recent AI reports.
        
        Args:
            limit: Maximum number of reports to return
            
        Returns:
            List of recent reports
        """
        sorted_reports = sorted(
            self.reports.items(),
            key=lambda x: x[1].get('_metadata', {}).get('timestamp', ''),
            reverse=True
        )
        
        return [report for _, report in sorted_reports[:limit]]
    
    def get_stats(self) -> Dict:
        """Get reporter statistics."""
        return {
            **self.stats,
            'enabled': self.enabled,
            'queue_size': self.report_queue.qsize(),
            'reports_stored': len(self.reports)
        }
    
    def clear_reports(self):
        """Clear all stored reports."""
        self.reports.clear()
        self.stats['total_reports'] = 0
        self.stats['successful_reports'] = 0
        self.stats['failed_reports'] = 0
        self.stats['total_cost_estimate'] = 0.0
        self.logger.info("Cleared all AI reports")


# Global instance
_auto_reporter = None

def get_auto_reporter() -> AutoGeminiReporter:
    """Get global auto reporter instance."""
    global _auto_reporter
    if _auto_reporter is None:
        _auto_reporter = AutoGeminiReporter()
    return _auto_reporter

def enable_auto_reporting(api_key: Optional[str] = None):
    """Enable auto-reporting with API key."""
    global _auto_reporter
    _auto_reporter = AutoGeminiReporter(api_key)
    return _auto_reporter

def disable_auto_reporting():
    """Disable auto-reporting."""
    global _auto_reporter
    _auto_reporter = None
