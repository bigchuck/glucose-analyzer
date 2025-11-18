"""
Meal Matching Module
Associates detected glucose spikes with logged meals
Supports multiple meals per spike
"""

from datetime import datetime, timedelta


class MealSpikeMatch:
    """Represents a spike event with associated meals"""
    
    def __init__(self):
        self.meals = []  # List of meal dicts that contributed to this spike
        self.spike = None  # SpikeEvent object
        self.total_gl = 0  # Sum of GL from all associated meals
        self.meal_count = 0  # Number of meals
        self.meal_delays = []  # Time from each meal to spike start (minutes)
        self.is_complex = False  # DEPRECATED: All multi-meal spikes are complex
    
    def __repr__(self):
        if self.meals and self.spike:
            meal_times = [m['timestamp'] for m in self.meals]
            return (f"MealSpikeMatch(meals={meal_times}, total_GL={self.total_gl}, "
                    f"spike_start={self.spike.start_time})")
        return "MealSpikeMatch(unmatched)"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'meals': self.meals,
            'spike': self.spike.to_dict() if self.spike else None,
            'total_gl': self.total_gl,
            'meal_count': self.meal_count,
            'meal_delays': self.meal_delays,
            'is_complex': self.is_complex
        }


class MealMatcher:
    """Matches meals to glucose spikes with multi-meal support"""
    
    def __init__(self, config):
        """
        Initialize meal matcher with configuration
        
        Args:
            config: Config object with matching parameters
        """
        self.config = config
        self.pre_spike_meal_window = config.get('spike_detection', 'pre_spike_meal_window')
    
    def match_meals_to_spikes(self, meals, spikes):
        """
        Match meals to detected spikes
        Finds ALL meals that contribute to each spike
        
        Args:
            meals: List of meal dicts with 'timestamp' and 'gl'
            spikes: List of SpikeEvent objects
            
        Returns:
            dict: {
                'matched': list of MealSpikeMatch objects,
                'unmatched_spikes': list of SpikeEvent objects,
                'unmatched_meals': list of meal dicts
            }
        """
        matched = []
        unmatched_spikes = []
        
        # Convert meal timestamps to datetime objects
        meals_with_dt = []
        for meal in meals:
            meal_copy = meal.copy()
            meal_copy['datetime'] = datetime.strptime(meal['timestamp'], "%Y-%m-%d:%H:%M")
            meals_with_dt.append(meal_copy)
        
        # Sort meals by time
        meals_with_dt.sort(key=lambda m: m['datetime'])
        
        # Track which meals got matched to at least one spike
        matched_meal_timestamps = set()
        
        # For each spike, find ALL contributing meals
        for spike in spikes:
            contributing_meals = self._find_meals_for_spike(spike, meals_with_dt)
            
            if contributing_meals:
                # Create match with multiple meals
                match = MealSpikeMatch()
                match.spike = spike
                match.meals = contributing_meals
                match.meal_count = len(contributing_meals)
                match.total_gl = sum(m['gl'] for m in contributing_meals)
                match.is_complex = len(contributing_meals) > 1
                
                # Calculate delays for each meal
                match.meal_delays = []
                for meal in contributing_meals:
                    delay = (spike.start_time - meal['datetime']).total_seconds() / 60
                    match.meal_delays.append(delay)
                    matched_meal_timestamps.add(meal['timestamp'])
                
                matched.append(match)
            else:
                # Spike with no associated meals
                unmatched_spikes.append(spike)
        
        # Create unmatched meals list
        unmatched_meals = [m for m in meals if m['timestamp'] not in matched_meal_timestamps]
        
        return {
            'matched': matched,
            'unmatched_spikes': unmatched_spikes,
            'unmatched_meals': unmatched_meals
        }
    
    def _find_meals_for_spike(self, spike, meals_with_dt):
        """
        Find ALL meals that contribute to this spike
        
        A meal contributes if it occurs:
        - Within pre_spike_meal_window before spike start, OR
        - During the rise phase (between spike start and peak)
        
        Meals during plateau or decline are excluded.
        
        Args:
            spike: SpikeEvent object
            meals_with_dt: List of meals with 'datetime' key
            
        Returns:
            List of meal dicts that contribute to this spike
        """
        contributing = []
        
        # Define the time window for contributing meals
        window_start = spike.start_time - timedelta(minutes=self.pre_spike_meal_window)
        rise_end = spike.peak_time  # Only meals before peak
        
        for meal in meals_with_dt:
            meal_time = meal['datetime']
            
            # Check if meal is within the contributing window
            if window_start <= meal_time <= rise_end:
                contributing.append(meal)
        
        # Sort by time (earliest first)
        contributing.sort(key=lambda m: m['datetime'])
        
        return contributing
    
    def get_stats(self, matched):
        """
        Get statistics about matches
        
        Args:
            matched: List of MealSpikeMatch objects or dicts
            
        Returns:
            dict: Statistics
        """
        if not matched:
            return {
                'total_matches': 0,
                'single_meal_spikes': 0,
                'multi_meal_spikes': 0,
                'avg_meals_per_spike': 0,
                'avg_total_gl': 0,
                'avg_magnitude': 0,
                'avg_earliest_delay': 0
            }
        
        # Helper function to safely get attribute from object or dict
        def get_val(item, attr):
            if isinstance(item, dict):
                return item.get(attr)
            return getattr(item, attr, None)
        
        # Count single vs multi-meal spikes
        single_meal = sum(1 for m in matched if get_val(m, 'meal_count') == 1)
        multi_meal = sum(1 for m in matched if get_val(m, 'meal_count') > 1)
        
        # Extract values
        total_gl_values = [get_val(m, 'total_gl') for m in matched]
        
        # Handle magnitude - might be in spike object or dict
        magnitudes = []
        for m in matched:
            spike = get_val(m, 'spike')
            if spike:
                if isinstance(spike, dict):
                    magnitudes.append(spike.get('magnitude', 0))
                else:
                    magnitudes.append(getattr(spike, 'magnitude', 0))
        
        # Get earliest meal delay for each spike
        earliest_delays = []
        for m in matched:
            delays = get_val(m, 'meal_delays')
            if delays:
                earliest_delays.append(min(delays))
        
        stats = {
            'total_matches': len(matched),
            'single_meal_spikes': single_meal,
            'multi_meal_spikes': multi_meal,
            'avg_meals_per_spike': sum(get_val(m, 'meal_count') or 0 for m in matched) / len(matched),
            'avg_total_gl': sum(total_gl_values) / len(total_gl_values) if total_gl_values else 0,
            'min_gl': min(total_gl_values) if total_gl_values else 0,
            'max_gl': max(total_gl_values) if total_gl_values else 0,
            'avg_magnitude': sum(magnitudes) / len(magnitudes) if magnitudes else 0,
            'avg_earliest_delay': sum(earliest_delays) / len(earliest_delays) if earliest_delays else 0,
            'min_delay': min(earliest_delays) if earliest_delays else 0,
            'max_delay': max(earliest_delays) if earliest_delays else 0
        }
        
        return stats
    
    def get_unmatched_spike_summary(self, unmatched_spikes):
        """
        Get summary of unmatched spikes (unexplained events)
        
        Args:
            unmatched_spikes: List of SpikeEvent objects without meals
            
        Returns:
            list: List of dicts with spike info
        """
        summary = []
        for spike in unmatched_spikes:
            summary.append({
                'time': spike.start_time.strftime('%Y-%m-%d %H:%M'),
                'start_glucose': spike.start_glucose,
                'peak_glucose': spike.peak_glucose,
                'magnitude': spike.magnitude,
                'duration': spike.duration_minutes
            })
        return summary
    
    def filter_matches_by_date(self, matches, start_date=None, end_date=None):
        """
        Filter matches by date range
        
        Args:
            matches: List of MealSpikeMatch objects or dicts
            start_date: Optional start datetime string (YYYY-MM-DD:HH:MM)
            end_date: Optional end datetime string (YYYY-MM-DD:HH:MM)
            
        Returns:
            list: Filtered matches
        """
        if not start_date and not end_date:
            return matches
        
        filtered = []
        for match in matches:
            # Handle both object and dict
            if isinstance(match, dict):
                spike = match.get('spike')
                if isinstance(spike, dict):
                    spike_time_str = spike.get('start_time', '')
                else:
                    spike_time_str = spike.start_time.strftime('%Y-%m-%d:%H:%M') if spike else ''
            else:
                spike_time_str = match.spike.start_time.strftime('%Y-%m-%d:%H:%M') if match.spike else ''
            
            if start_date and spike_time_str < start_date:
                continue
            if end_date and spike_time_str > end_date:
                continue
            
            filtered.append(match)
        
        return filtered