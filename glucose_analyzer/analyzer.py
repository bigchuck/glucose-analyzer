"""Main analyzer class for glucose spike analysis"""

import os
from pathlib import Path

from glucose_analyzer.utils.config import Config
from glucose_analyzer.utils.data_manager import DataManager
from glucose_analyzer.parsers.csv_parser import LibreViewParser
from glucose_analyzer.analysis.spike_detector import SpikeDetector
from glucose_analyzer.analysis.meal_matcher import MealMatcher
from glucose_analyzer.analysis.normalizer import SpikeNormalizer
from glucose_analyzer.analysis.group_analyzer import GroupAnalyzer
from glucose_analyzer.visualization.charts import ChartGenerator

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
        self.normalizer = SpikeNormalizer()
        self.normalized_profiles = []
        self.group_analyzer = GroupAnalyzer()
        self.chart_generator = ChartGenerator(self.config)
        
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

                # Normalize matched profiles
                if match_stats['matched_count'] > 0:
                    print(f"\nCreating normalized profiles...")
                    self.normalized_profiles = self.normalizer.normalize_matches(
                        self.match_results['matched'], 
                        self.cgm_data
                    )
                    print(f"[OK] Normalized {len(self.normalized_profiles)} spike profiles")

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
            chart_type: Type of chart to generate ('spike', 'group', 'compare', 'scatter')
            *args: Additional arguments for chart generation
        """
        try:
            if chart_type == 'spike':
                return self._chart_spike(*args)
            elif chart_type == 'group':
                return self._chart_group(*args)
            elif chart_type == 'compare':
                return self._chart_compare(*args)
            elif chart_type == 'scatter':
                return self._chart_scatter(*args)
            else:
                print(f"[ERROR] Unknown chart type: {chart_type}")
                return None
        except Exception as e:
            print(f"[ERROR] Failed to generate chart: {e}")
            return None
    
    def _chart_spike(self, spike_index, normalize=False):
        """Generate chart for a single spike"""
        if not self.detected_spikes:
            print("[ERROR] No spikes detected. Run 'analyze' first.")
            return None
        
        if spike_index < 0 or spike_index >= len(self.detected_spikes):
            print(f"[ERROR] Spike index {spike_index} out of range (0-{len(self.detected_spikes)-1})")
            return None
        
        spike = self.detected_spikes[spike_index]
        
        if self.cgm_data is None:
            print("[ERROR] CGM data not available")
            return None
        
        filepath = self.chart_generator.chart_spike(spike, spike_index, self.cgm_data, normalize)
        print(f"[OK] Chart saved: {filepath}")
        return filepath
    
    def _chart_group(self, group_index, normalize=False):
        """Generate overlay chart for a group"""
        if not self.match_results:
            print("[ERROR] No analysis results. Run 'analyze' first.")
            return None
        
        # Analyze the group
        analysis = self.analyze_group(group_index)
        if not analysis:
            return None
        
        filepath = self.chart_generator.chart_group(analysis, normalize)
        print(f"[OK] Chart saved: {filepath}")
        return filepath
    
    def _chart_compare(self, group1_index, group2_index, normalize=False):
        """Generate comparison chart for two groups"""
        if not self.match_results:
            print("[ERROR] No analysis results. Run 'analyze' first.")
            return None
        
        # Analyze both groups
        analysis1 = self.analyze_group(group1_index)
        analysis2 = self.analyze_group(group2_index)
        
        if not analysis1 or not analysis2:
            return None
        
        # Get comparison
        comparison = self.group_analyzer.compare_groups(analysis1, analysis2)
        
        if not comparison:
            print("[ERROR] Failed to compare groups")
            return None
        
        filepath = self.chart_generator.chart_compare(comparison, analysis1, analysis2, normalize)
        print(f"[OK] Chart saved: {filepath}")
        return filepath
    
    def _chart_scatter(self, group_index):
        """Generate GL vs AUC scatter plot for a group"""
        if not self.match_results:
            print("[ERROR] No analysis results. Run 'analyze' first.")
            return None
        
        # Analyze the group
        analysis = self.analyze_group(group_index)
        if not analysis:
            return None
        
        filepath = self.chart_generator.chart_scatter(analysis)
        print(f"[OK] Chart saved: {filepath}")
        return filepath

    def compare_normalized_groups(self, group1_desc, group2_desc):
        """
        Compare normalized profiles between two groups
        
        Args:
            group1_desc: Description of first group
            group2_desc: Description of second group
            
        Returns:
            dict: Comparison results or None if groups not found
        """
        groups = self.data_manager.data["groups"]
        
        # Find groups by description
        group1 = None
        group2 = None
        
        for g in groups:
            if g['description'] == group1_desc:
                group1 = g
            if g['description'] == group2_desc:
                group2 = g
        
        if not group1 or not group2:
            print("[ERROR] Could not find one or both groups")
            return None
        
        if not self.normalized_profiles:
            print("[ERROR] No normalized profiles available. Run 'analyze' first.")
            return None
        
        # Filter profiles by group dates
        group1_profiles = [p for p in self.normalized_profiles
                        if group1['start'] <= p.spike_start_time <= (group1['end'] or '9999-12-31')]
        group2_profiles = [p for p in self.normalized_profiles
                        if group2['start'] <= p.spike_start_time <= (group2['end'] or '9999-12-31')]
        
        if not group1_profiles or not group2_profiles:
            print("[ERROR] One or both groups have no normalized profiles")
            return None
        
        # Perform comparison
        comparison = self.normalizer.compare_groups(group1_profiles, group2_profiles)
        
        return comparison
    
    def analyze_group(self, group_index, gl_range=None):
        """
        Analyze a specific group
        
        Args:
            group_index: Index of group to analyze
            gl_range: Optional tuple (min_gl, max_gl) to filter by GL
            
        Returns:
            dict: Analysis results or None if error
        """
        if not self.match_results:
            print("[ERROR] No analysis results. Run 'analyze' first.")
            return None
        
        groups = self.data_manager.data["groups"]
        if group_index < 0 or group_index >= len(groups):
            print(f"[ERROR] Group index {group_index} out of range (0-{len(groups)-1})")
            return None
        
        group_info = groups[group_index]
        
        # Filter matches by group
        group_matches = self.group_analyzer.filter_matches_by_group(
            self.match_results['matched'], 
            group_info
        )
        
        # Apply GL filter if specified
        if gl_range:
            min_gl, max_gl = gl_range
            group_matches = self.group_analyzer.filter_by_gl_range(group_matches, min_gl, max_gl)
        
        # Filter unmatched items by group
        unmatched_spikes = self.group_analyzer.filter_unmatched_by_group(
            self.match_results['unmatched_spikes'],
            group_info
        )
        
        unmatched_meals = self.group_analyzer.filter_unmatched_by_group(
            self.match_results['unmatched_meals'],
            group_info
        )
        
        # Analyze the group
        analysis = self.group_analyzer.analyze_group(
            group_info, 
            group_matches, 
            unmatched_spikes, 
            unmatched_meals
        )
        
        return analysis

    def compare_groups(self, group1_index, group2_index, gl_range=None):
        """
        Compare two groups
        
        Args:
            group1_index: Index of first group
            group2_index: Index of second group
            gl_range: Optional tuple (min_gl, max_gl) to filter by GL
            
        Returns:
            GroupComparison object or None if error
        """
        # Analyze both groups
        analysis1 = self.analyze_group(group1_index, gl_range)
        analysis2 = self.analyze_group(group2_index, gl_range)
        
        if not analysis1 or not analysis2:
            return None
        
        # Compare them
        comparison = self.group_analyzer.compare_groups(analysis1, analysis2)
        
        return comparison