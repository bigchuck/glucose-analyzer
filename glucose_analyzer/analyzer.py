"""Main analyzer class for glucose spike analysis"""

import os
from pathlib import Path

from glucose_analyzer.utils.config import Config
from glucose_analyzer.utils.data_manager import DataManager
from glucose_analyzer.parsers.csv_parser import LibreViewParser
from glucose_analyzer.analysis.spike_detector import SpikeDetector
from glucose_analyzer.analysis.meal_matcher import MealMatcher


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
        self.meal_matcher = MealMatcher(self.config)
        self.detected_spikes = []
        self.match_results = None
        
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
        spike_stats = self.spike_detector.get_stats(self.detected_spikes)
        
        # Display spike results
        print(f"\n[OK] Spike detection complete")
        print(f"Found {spike_stats['count']} spike events")
        
        # Match meals to spikes
        meals = self.data_manager.get_meals()
        if meals:
            print(f"\nMatching {len(meals)} meals to spikes...")
            self.match_results = self.meal_matcher.match_meals_to_spikes(meals, self.detected_spikes)
            match_stats = self.meal_matcher.get_stats(self.match_results)
            
            print(f"\n[OK] Meal matching complete")
            print(f"Matched: {match_stats['matched_count']} meal-spike pairs")
            print(f"Unmatched spikes: {match_stats['unmatched_spikes']}")
            print(f"Unmatched meals: {match_stats['unmatched_meals']}")
            if match_stats['complex_events'] > 0:
                print(f"Complex events (multiple meals nearby): {match_stats['complex_events']}")
            
            if match_stats['matched_count'] > 0:
                print(f"\nMatched Event Statistics:")
                print("=" * 60)
                print(f"Average delay (meal to spike): {match_stats['avg_delay']:.1f} minutes")
                print(f"Delay range: {match_stats['min_delay']:.0f} - {match_stats['max_delay']:.0f} minutes")
                print(f"Average GL: {match_stats['avg_gl']:.1f}")
                print(f"Average spike magnitude: {match_stats['avg_magnitude']:.1f} mg/dL")
                if spike_stats['count'] > 0:
                    print(f"Average magnitude: {spike_stats['avg_magnitude']:.1f} mg/dL")
                    print(f"Average AUC-70: {spike_stats['avg_auc_70']:.0f} mg/dL*min")
                    print(f"Average AUC-relative: {spike_stats['avg_auc_relative']:.0f} mg/dL*min")
                    print(f"Average normalized AUC: {spike_stats['avg_normalized_auc']:.3f}")
                    if spike_stats.get('avg_recovery_time', 0) > 0:
                        print(f"Average recovery time: {spike_stats['avg_recovery_time']:.0f} minutes")
                # Show first few matches
                print(f"\nFirst {min(3, len(self.match_results['matched']))} matched events:")
                print("-" * 60)
                for i, match in enumerate(self.match_results['matched'][:3]):
                    print(f"\nMatch {i+1}:")
                    print(f"  Meal: {match.meal['timestamp']} (GL={match.meal['gl']})")
                    print(f"  Spike: {match.spike.start_time.strftime('%Y-%m-%d %H:%M')} "
                          f"to {match.spike.end_time.strftime('%H:%M')}")
                    print(f"  Delay: {match.delay_minutes:.0f} minutes")
                    print(f"  Peak: {match.spike.peak_glucose:.0f} mg/dL (+{match.spike.magnitude:.0f})")
                    if match.is_complex:
                        print(f"  [COMPLEX] {len(match.nearby_meals)} nearby meal(s)")
                    print(f"  AUC-relative: {match.spike.auc_relative:.0f} mg/dL*min, Normalized: {match.spike.normalized_auc:.3f}")
                    if match.spike.recovery_time:
                        print(f"  Recovery: {match.spike.recovery_time:.0f} minutes")
            
            # Show unmatched spikes if any
            if match_stats['unmatched_spikes'] > 0:
                print(f"\n[WARNING] {match_stats['unmatched_spikes']} unexplained spike(s):")
                for spike in self.match_results['unmatched_spikes'][:3]:
                    print(f"  {spike.start_time.strftime('%Y-%m-%d %H:%M')} - "
                          f"Peak: {spike.peak_glucose:.0f} mg/dL (+{spike.magnitude:.0f})")
        else:
            print("\n[INFO] No meals logged. Add meals with 'addmeal' to enable matching.")
            print("[INFO] Spike detection complete without meal matching.")
        
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
