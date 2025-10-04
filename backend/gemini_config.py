"""
Configuration management for Gemini API integration.
Handles environment variables and settings for Gemini services.
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv


class GeminiConfig:
    """Configuration class for Gemini API integration."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize Gemini configuration.
        
        Args:
            env_file: Path to .env file (optional)
        """
        # Load environment variables
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
        else:
            # Try to load from common locations
            possible_env_files = [
                '.env',
                'backend/.env',
                'gemini.env',
                'backend/gemini.env'
            ]
            
            for env_file_path in possible_env_files:
                if os.path.exists(env_file_path):
                    load_dotenv(env_file_path)
                    break
        
        # API Configuration
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash-exp')
        
        # Analysis Settings
        self.analysis_type = os.getenv('GEMINI_ANALYSIS_TYPE', 'comprehensive')
        self.batch_size = int(os.getenv('GEMINI_BATCH_SIZE', '3'))
        self.rate_limit_delay = float(os.getenv('GEMINI_RATE_LIMIT_DELAY', '0.5'))
        
        # Output Settings
        self.save_results = os.getenv('GEMINI_SAVE_RESULTS', 'true').lower() == 'true'
        self.output_dir = Path(os.getenv('GEMINI_OUTPUT_DIR', 'analysis_results'))
        
        # Logging
        self.log_level = getattr(logging, os.getenv('GEMINI_LOG_LEVEL', 'INFO').upper())
        
        # Validation
        self._validate_config()
        
        # Setup output directory
        if self.save_results:
            self.output_dir.mkdir(exist_ok=True)
    
    def _validate_config(self) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Check required settings
        if not self.api_key:
            errors.append("GEMINI_API_KEY is required")
        
        # Validate model name
        valid_models = [
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-1.0-pro'
        ]
        if self.model_name not in valid_models:
            errors.append(f"Invalid model name: {self.model_name}. Must be one of: {valid_models}")
        
        # Validate analysis type
        valid_analysis_types = ['comprehensive', 'objects', 'activities', 'description']
        if self.analysis_type not in valid_analysis_types:
            errors.append(f"Invalid analysis type: {self.analysis_type}. Must be one of: {valid_analysis_types}")
        
        # Validate numeric values
        if self.batch_size <= 0:
            errors.append(f"Batch size must be positive, got: {self.batch_size}")
        
        if self.rate_limit_delay < 0:
            errors.append(f"Rate limit delay must be non-negative, got: {self.rate_limit_delay}")
        
        # Report errors
        if errors:
            for error in errors:
                logging.error(f"Gemini config error: {error}")
            return False
        
        return True
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model-related configuration."""
        return {
            'api_key': self.api_key,
            'model_name': self.model_name,
            'analysis_type': self.analysis_type
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing-related configuration."""
        return {
            'batch_size': self.batch_size,
            'rate_limit_delay': self.rate_limit_delay,
            'save_results': self.save_results,
            'output_dir': str(self.output_dir)
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            'log_level': self.log_level
        }
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return bool(self.api_key) and self._validate_config()
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"GeminiConfig(model={self.model_name}, analysis_type={self.analysis_type}, valid={self.is_valid()})"


# Global configuration instance
gemini_config = GeminiConfig()
