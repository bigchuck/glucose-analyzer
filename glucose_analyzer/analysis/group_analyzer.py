"""
Group Analyzer Module
Performs temporal comparisons of glucose responses across analysis groups
"""

import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class GroupStats:
    """Statistical summary for a group of matched events"""
    
    def __init__(self, group_info: dict, matches: list):
        """
        Initialize group statistics
        
        Args:
            group_info: Dict with group metadata (start, end, description)
            matches: List of MealSpikeMatch objects in this group
        """
        self.group_info = group_info
        self.matches = matches
        self.count = len(matches)
        
        # Calculate statistics for each metric
        self.auc_relative = self._calc_stats([m.spike.auc_relative for m in matches])
        self.normalized_auc = self._calc_stats([m.spike.normalized_auc for m in matches])
        self.recovery_time = self._calc_stats([m.spike.recovery_time for m in matches if m.spike.recovery_time])
        self.magnitude = self._calc_stats([m.spike.magnitude for m in matches])
        self.time_to_peak = self._calc_stats([m.spike.time_to_peak_minutes for m in matches])
        # Use first meal's delay (primary meal) for delay statistics
        self.delay_minutes = self._calc_stats([m.meal_delays[0] if m.meal_delays else 0 for m in matches])
        
        # Additional metrics
        # Use total GL from all contributing meals
        self.gl = self._calc_stats([m.total_gl for m in matches])
        self.duration = self._calc_stats([m.spike.duration_minutes for m in matches])
        self.peak_glucose = self._calc_stats([m.spike.peak_glucose for m in matches])
        
        # Counts for context
        self.complex_events = sum(1 for m in matches if m.is_complex)
    
    def _calc_stats(self, values: list) -> dict:
        """
        Calculate descriptive statistics
        
        Args:
            values: List of numeric values
            
        Returns:
            dict: Statistics (mean, median, std, min, max, count)
        """
        if not values:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }
        
        values_array = np.array(values)
        return {
            'mean': float(np.mean(values_array)),
            'median': float(np.median(values_array)),
            'std': float(np.std(values_array)),
            'min': float(np.min(values_array)),
            'max': float(np.max(values_array)),
            'count': len(values)
        }
    
    def get_metric(self, metric_name: str) -> dict:
        """
        Get statistics for a specific metric
        
        Args:
            metric_name: Name of metric to retrieve
            
        Returns:
            dict: Statistics for that metric
        """
        return getattr(self, metric_name, None)


class GroupComparison:
    """Comparison between two groups"""
    
    def __init__(self, group1_stats: GroupStats, group2_stats: GroupStats):
        """
        Initialize group comparison
        
        Args:
            group1_stats: Statistics for first group (baseline)
            group2_stats: Statistics for second group (comparison)
        """
        self.group1 = group1_stats
        self.group2 = group2_stats
        
        # Core metrics in priority order
        self.metrics = [
            ('auc_relative', 'AUC-relative', 'mg/dL*min', 'lower'),
            ('normalized_auc', 'Normalized AUC', '', 'lower'),
            ('recovery_time', 'Recovery time', 'min', 'lower'),
            ('magnitude', 'Magnitude', 'mg/dL', 'lower'),
            ('time_to_peak', 'Time to peak', 'min', 'either'),
            ('delay_minutes', 'Delay', 'min', 'either')
        ]
        
        # Calculate changes for each metric
        self.changes = {}
        for metric_key, _, _, _ in self.metrics:
            self.changes[metric_key] = self._calc_change(metric_key)
    
    def _calc_change(self, metric_name: str) -> dict:
        """
        Calculate change between groups for a metric
        
        Args:
            metric_name: Name of metric
            
        Returns:
            dict: Change statistics
        """
        g1_stats = self.group1.get_metric(metric_name)
        g2_stats = self.group2.get_metric(metric_name)
        
        if not g1_stats or not g2_stats or g1_stats['count'] == 0 or g2_stats['count'] == 0:
            return {
                'absolute': 0.0,
                'percent': 0.0,
                'is_improvement': False,
                'available': False
            }
        
        g1_mean = g1_stats['mean']
        g2_mean = g2_stats['mean']
        
        absolute_change = g2_mean - g1_mean
        
        if g1_mean != 0:
            percent_change = (absolute_change / g1_mean) * 100
        else:
            percent_change = 0.0
        
        return {
            'absolute': absolute_change,
            'percent': percent_change,
            'is_improvement': absolute_change < 0,  # Negative change is improvement for our metrics
            'available': True
        }


class GroupAnalyzer:
    """Analyzes and compares glucose responses across groups"""
    
    def __init__(self):
        """Initialize group analyzer"""
        pass
    
    def analyze_group(self, group_info: dict, matches: list, 
                     unmatched_spikes: list, unmatched_meals: list) -> dict:
        """
        Analyze matches within a single group
        
        Args:
            group_info: Dict with group metadata
            matches: List of MealSpikeMatch objects
            unmatched_spikes: List of unmatched spike objects in group
            unmatched_meals: List of unmatched meals in group
            
        Returns:
            dict: Analysis results
        """
        if not matches:
            return {
                'group_info': group_info,
                'stats': None,
                'match_count': 0,
                'unmatched_spikes_count': len(unmatched_spikes),
                'unmatched_meals_count': len(unmatched_meals),
                'message': 'No matched events in this group'
            }
        
        stats = GroupStats(group_info, matches)
        
        return {
            'group_info': group_info,
            'stats': stats,
            'match_count': len(matches),
            'unmatched_spikes_count': len(unmatched_spikes),
            'unmatched_meals_count': len(unmatched_meals)
        }
    
    def filter_matches_by_group(self, matches: list, group_info: dict) -> list:
        """
        Filter matches that belong to a group (based on meal timestamp)
        
        Args:
            matches: List of MealSpikeMatch objects
            group_info: Dict with 'start' and 'end' timestamps
            
        Returns:
            list: Filtered matches
        """
        start_dt = datetime.strptime(group_info['start'], "%Y-%m-%d:%H:%M")
                
        # Handle OPEN groups (no end date yet) - use far future date
        if group_info['end'] is None:
            end_dt = datetime(9999, 12, 31, 23, 59)
        else:
            end_dt = datetime.strptime(group_info['end'], "%Y-%m-%d:%H:%M")

        filtered = []
        for match in matches:
            # Use first meal's timestamp (earliest contributing meal)
            if match.meals:
                meal_dt = datetime.strptime(match.meals[0]['timestamp'], "%Y-%m-%d:%H:%M")
                if start_dt <= meal_dt <= end_dt:
                    filtered.append(match)
 
        return filtered
    
    def filter_by_gl_range(self, matches: list, min_gl: float, max_gl: float) -> list:
        """
        Filter matches by glycemic load range
        
        Args:
            matches: List of MealSpikeMatch objects
            min_gl: Minimum GL value
            max_gl: Maximum GL value
            
        Returns:
            list: Filtered matches
        """
        return [m for m in matches if min_gl <= m.total_gl <= max_gl]
    
    def filter_unmatched_by_group(self, items: list, group_info: dict, 
                                  timestamp_key: str = 'timestamp') -> list:
        """
        Filter unmatched items (spikes or meals) by group
        
        Args:
            items: List of unmatched spike or meal objects
            group_info: Dict with group date range
            timestamp_key: Key name for timestamp in item dict
            
        Returns:
            list: Filtered items
        """
        start_dt = datetime.strptime(group_info['start'], "%Y-%m-%d:%H:%M")
        
        # Handle OPEN groups (no end date yet) - use far future date
        if group_info['end'] is None:
            end_dt = datetime(9999, 12, 31, 23, 59)
        else:
            end_dt = datetime.strptime(group_info['end'], "%Y-%m-%d:%H:%M")
        
        filtered = []
        for item in items:
            # For spikes, use start_time; for meals, use timestamp
            if hasattr(item, 'start_time'):
                item_dt = item.start_time
            else:
                item_dt = datetime.strptime(item[timestamp_key], "%Y-%m-%d:%H:%M")
            
            if start_dt <= item_dt <= end_dt:
                filtered.append(item)
        
        return filtered
    
    def compare_groups(self, group1_analysis: dict, group2_analysis: dict) -> GroupComparison:
        """
        Compare two groups
        
        Args:
            group1_analysis: Analysis results from analyze_group() for first group
            group2_analysis: Analysis results from analyze_group() for second group
            
        Returns:
            GroupComparison object
        """
        if not group1_analysis['stats'] or not group2_analysis['stats']:
            return None
        
        return GroupComparison(group1_analysis['stats'], group2_analysis['stats'])
    
    def format_group_analysis(self, analysis: dict) -> str:
        """
        Format single group analysis for display
        
        Args:
            analysis: Results from analyze_group()
            
        Returns:
            str: Formatted output
        """
        lines = []
        
        group = analysis['group_info']
        lines.append(f"\nGroup: {group['description']}")
        lines.append(f"Period: {group['start']} to {group['end']}")
        lines.append("=" * 80)
        
        if not analysis['stats']:
            lines.append(analysis['message'])
            return '\n'.join(lines)
        
        stats = analysis['stats']
        
        lines.append(f"\nMatched events: {analysis['match_count']}")
        lines.append(f"Unmatched spikes: {analysis['unmatched_spikes_count']}")
        lines.append(f"Unmatched meals: {analysis['unmatched_meals_count']}")
        lines.append(f"Complex events: {stats.complex_events}")
        
        lines.append(f"\nKey Metrics (mean ± std):")
        lines.append("-" * 80)
        
        # Primary metrics
        lines.append(f"AUC-relative:    {stats.auc_relative['mean']:>8.0f} ± {stats.auc_relative['std']:>6.0f} mg/dL*min")
        lines.append(f"Normalized AUC:  {stats.normalized_auc['mean']:>8.3f} ± {stats.normalized_auc['std']:>6.3f}")
        
        if stats.recovery_time['count'] > 0:
            lines.append(f"Recovery time:   {stats.recovery_time['mean']:>8.0f} ± {stats.recovery_time['std']:>6.0f} min "
                        f"(n={stats.recovery_time['count']})")
        else:
            lines.append(f"Recovery time:   Not available")
        
        lines.append(f"Magnitude:       {stats.magnitude['mean']:>8.0f} ± {stats.magnitude['std']:>6.0f} mg/dL")
        lines.append(f"Time to peak:    {stats.time_to_peak['mean']:>8.0f} ± {stats.time_to_peak['std']:>6.0f} min")
        lines.append(f"Delay:           {stats.delay_minutes['mean']:>8.0f} ± {stats.delay_minutes['std']:>6.0f} min")
        
        lines.append(f"\nAdditional Info:")
        lines.append("-" * 80)
        lines.append(f"Average GL:      {stats.gl['mean']:>8.1f} ± {stats.gl['std']:>6.1f}")
        lines.append(f"Peak glucose:    {stats.peak_glucose['mean']:>8.0f} ± {stats.peak_glucose['std']:>6.0f} mg/dL")
        lines.append(f"Duration:        {stats.duration['mean']:>8.0f} ± {stats.duration['std']:>6.0f} min")
        
        return '\n'.join(lines)
    
    def format_comparison(self, comparison: GroupComparison) -> str:
        """
        Format group comparison for display
        
        Args:
            comparison: GroupComparison object
            
        Returns:
            str: Formatted comparison table
        """
        if not comparison:
            return "Cannot compare groups - insufficient data"
        
        lines = []
        
        g1 = comparison.group1
        g2 = comparison.group2
        
        lines.append("\nGroup Comparison")
        lines.append("=" * 100)
        lines.append(f"Group 1: {g1.group_info['description']}")
        lines.append(f"         {g1.group_info['start']} to {g1.group_info['end']} (n={g1.count})")
        lines.append(f"Group 2: {g2.group_info['description']}")
        lines.append(f"         {g2.group_info['start']} to {g2.group_info['end']} (n={g2.count})")
        lines.append("")
        
        # Table header
        lines.append(f"{'Metric':<20} {'Group 1':<20} {'Group 2':<20} {'Change':<25}")
        lines.append("-" * 100)
        
        # Display each metric
        for metric_key, metric_name, unit, direction in comparison.metrics:
            g1_stats = g1.get_metric(metric_key)
            g2_stats = g2.get_metric(metric_key)
            change = comparison.changes[metric_key]
            
            if not change['available']:
                lines.append(f"{metric_name:<20} {'N/A':<20} {'N/A':<20} {'N/A':<25}")
                continue
            
            # Format values with units
            if unit:
                g1_str = f"{g1_stats['mean']:.1f} ± {g1_stats['std']:.1f} {unit}"
                g2_str = f"{g2_stats['mean']:.1f} ± {g2_stats['std']:.1f} {unit}"
            else:
                g1_str = f"{g1_stats['mean']:.3f} ± {g1_stats['std']:.3f}"
                g2_str = f"{g2_stats['mean']:.3f} ± {g2_stats['std']:.3f}"
            
            # Format change with improvement indicator
            change_str = f"{change['percent']:+.1f}%"
            if direction == 'lower' and change['is_improvement']:
                change_str += " ✓"
            elif direction == 'lower' and not change['is_improvement']:
                change_str += " ✗"
            
            lines.append(f"{metric_name:<20} {g1_str:<20} {g2_str:<20} {change_str:<25}")
        
        # Summary statistics
        lines.append("")
        lines.append("Additional Statistics:")
        lines.append("-" * 100)
        lines.append(f"{'Unmatched spikes':<20} {g1.count - g1.count + len([]):<20} "
                    f"{g2.count - g2.count + len([]):<20}")
        lines.append(f"{'Complex events':<20} {g1.complex_events:<20} {g2.complex_events:<20}")
        
        # Improvement summary
        lines.append("")
        improvements = sum(1 for k, _, _, d in comparison.metrics 
                          if d == 'lower' and comparison.changes[k]['available'] 
                          and comparison.changes[k]['is_improvement'])
        total_metrics = sum(1 for k, _, _, d in comparison.metrics 
                           if d == 'lower' and comparison.changes[k]['available'])
        
        if total_metrics > 0:
            lines.append(f"Improvement in {improvements}/{total_metrics} key metrics")
        
        return '\n'.join(lines)
