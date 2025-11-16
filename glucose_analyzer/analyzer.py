"""Main analyzer class for glucose spike analysis"""

import os
from pathlib import Path

from glucose_analyzer.utils.config import Config
from glucose_analyzer.utils.data_manager import DataManager
from glucose_analyzer.parsers.csv_parser import LibreViewParser


class GlucoseAnalyzer:
    """Main analyzer application"""
    
    def __init__(self, config_path='config.json'):
        """
        Initialize the analyzer
        
        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        self.data_manager = DataManager(self.config.get('data_files', 'meals_json'))
        self.cgm_data = None
        self.cgm_parser = None
        
        # Create charts directory if it doesn't exist
        charts_dir = self.config.get('output', 'charts_directory')
        Path(charts_dir).mkdir(exist_ok=True)
        
        # Try to load CGM data on startup
        self.load_cgm_data()
    
    def load_cgm_data(self):
        """
        Load LibreView CSV data
        
        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        csv_path = self.config.get('data_files', 'libreview_csv')
        
        if not os.path.exists(csv_path):
            # CSV file doesn't exist yet - not an error, just skip loading
            return False
        
        try:
            print(f"[INFO] Loading CGM data from {csv_path}...")
            self.cgm_parser = LibreViewParser(csv_path)
            self.cgm_parser.parse()
            self.cgm_data = self.cgm_parser.get_auto_readings()
            
            stats = self.cgm_parser.get_stats()
            print(f"[OK] Loaded {stats['type_0_count']} CGM readings")
            print(f"[INFO] Data range: {stats['start_date']} to {stats['end_date']}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load CGM data: {e}")
            return False
    
    def run_analysis(self):
        """Run full spike analysis"""
        print("Analyzing glucose data...")
        # TODO: Implement analysis
        print("[INFO] Analysis not yet implemented")
    
    def generate_chart(self, chart_type, *args):
        """
        Generate visualization chart
        
        Args:
            chart_type: Type of chart to generate
            *args: Additional arguments for chart generation
        """
        print(f"Generating {chart_type} chart...")
        # TODO: Implement charting
        print("[INFO] Charting not yet implemented")
