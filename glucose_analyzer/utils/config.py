"""Configuration management for Glucose Analyzer"""

import json


class Config:
    """Application configuration manager"""
    
    def __init__(self, config_path='config.json'):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config.json file
        """
        with open(config_path, 'r') as f:
            self.data = json.load(f)
    
    def get(self, *keys):
        """
        Get nested config value
        
        Args:
            *keys: Sequence of keys to traverse nested dict
            
        Returns:
            Configuration value at specified path
            
        Example:
            config.get('data_files', 'libreview_csv')
        """
        value = self.data
        for key in keys:
            value = value[key]
        return value
