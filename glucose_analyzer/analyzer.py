"""Main analyzer class for glucose spike analysis"""

import os
from pathlib import Path

from glucose_analyzer.utils.config import Config
from glucose_analyzer.utils.data_manager import DataManager
from glucose_analyzer.parsers.csv_parser import LibreViewParser
from glucose_analyzer.analysis.spike_detector import SpikeDetector


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
        self.spike_detector = SpikeDetector(self.config)
        self.detected_spikes = []
        
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
        if self.cgm_data is None:
            print("[ERROR] No CGM data loaded. Cannot run analysis.")
            return False
        
        print("Analyzing glucose data for spikes...")
        
        # Detect spikes
        self.detected_spikes = self.spike_detector.detect_spikes(self.cgm_data)
        
        # Get statistics
        stats = self.spike_detector.get_stats(self.detected_spikes)
        
        # Display results
        print(f"\n[OK] Spike detection complete")
        print(f"Found {stats['count']} spike events\n")
        
        if stats['count'] > 0:
            print("Spike Statistics:")
            print("=" * 60)
            print(f"Average magnitude: {stats['avg_magnitude']:.1f} mg/dL")
            print(f"Maximum magnitude: {stats['max_magnitude']:.1f} mg/dL")
            print(f"Average peak glucose: {stats['avg_peak']:.1f} mg/dL")
            print(f"Maximum peak glucose: {stats['max_peak']:.1f} mg/dL")
            print(f"Average duration: {stats['avg_duration']:.1f} minutes")
            print(f"Average time to peak: {stats['avg_time_to_peak']:.1f} minutes")
            print(f"\nSpike end reasons:")
            for reason, count in stats['end_reasons'].items():
                print(f"  {reason}: {count}")
            
            # Show first few spikes as examples
            print(f"\nFirst {min(5, len(self.detected_spikes))} spike events:")
            print("-" * 60)
            for i, spike in enumerate(self.detected_spikes[:5]):
                print(f"\nSpike {i+1}:")
                print(f"  Start: {spike.start_time.strftime('%Y-%m-%d %H:%M')} at {spike.start_glucose:.0f} mg/dL")
                print(f"  Peak:  {spike.peak_time.strftime('%Y-%m-%d %H:%M')} at {spike.peak_glucose:.0f} mg/dL")
                print(f"  End:   {spike.end_time.strftime('%Y-%m-%d %H:%M')} at {spike.end_glucose:.0f} mg/dL")
                print(f"  Magnitude: {spike.magnitude:.0f} mg/dL")
                print(f"  Duration: {spike.duration_minutes:.0f} minutes")
        
        return True
    
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
