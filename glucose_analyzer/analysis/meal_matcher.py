"""
Meal Matching Module
Associates detected glucose spikes with logged meals
"""

from datetime import datetime, timedelta


class MealSpikeMatch:
    """Represents a matched meal and spike event"""
    
    def __init__(self):
        self.meal = None  # Dict with meal data
        self.spike = None  # SpikeEvent object
        self.delay_minutes = None  # Time from meal to spike start
        self.is_complex = False  # Multiple meals within proximity
        self.nearby_meals = []  # Other meals near this one
    
    def __repr__(self):
        if self.meal and self.spike:
            return (f"MealSpikeMatch(meal={self.meal['timestamp']}, GL={self.meal['gl']}, "
                    f"spike_start={self.spike.start_time}, delay={self.delay_minutes}min)")
        return "MealSpikeMatch(unmatched)"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'meal': self.meal,
            'spike': self.spike.to_dict() if self.spike else None,
            'delay_minutes': float(self.delay_minutes) if self.delay_minutes else None,
            'is_complex': self.is_complex,
            'nearby_meals': self.nearby_meals
        }


class MealMatcher:
    """Matches meals to glucose spikes"""
    
    def __init__(self, config):
        """
        Initialize meal matcher with configuration
        
        Args:
            config: Config object with matching parameters
        """
        self.config = config
        self.search_window_minutes = config.get('spike_detection', 'search_window_minutes')
        self.proximity_threshold_minutes = config.get('spike_detection', 'proximity_threshold_minutes')
    
    def match_meals_to_spikes(self, meals, spikes):
        """
        Match meals to detected spikes
        
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
        unmatched_spikes = list(spikes)
        
        # Convert meal timestamps to datetime objects
        meals_with_dt = []
        for meal in meals:
            meal_copy = meal.copy()
            meal_copy['datetime'] = datetime.strptime(meal['timestamp'], "%Y-%m-%d:%H:%M")
            meals_with_dt.append(meal_copy)
        
        # Sort meals by time
        meals_with_dt.sort(key=lambda m: m['datetime'])
        
        # Track which meals got matched
        matched_meal_timestamps = set()
        
        # For each meal, look for matching spike
        for meal in meals_with_dt:
            match = self._find_spike_for_meal(meal, spikes)
            
            if match:
                matched.append(match)
                matched_meal_timestamps.add(meal['timestamp'])
                if match.spike in unmatched_spikes:
                    unmatched_spikes.remove(match.spike)
        
        # Create unmatched meals list (meals that didn't get matched)
        unmatched_meals = [m for m in meals if m['timestamp'] not in matched_meal_timestamps]
        
        # Check for complex events (meals in proximity)
        self._flag_complex_events(matched, meals_with_dt)
        
        return {
            'matched': matched,
            'unmatched_spikes': unmatched_spikes,
            'unmatched_meals': unmatched_meals
        }
    
    def _find_spike_for_meal(self, meal, spikes):
        """
        Find the spike that matches this meal
        
        Args:
            meal: Meal dict with 'datetime' key
            spikes: List of SpikeEvent objects
            
        Returns:
            MealSpikeMatch object or None if no match
        """
        meal_time = meal['datetime']
        search_end = meal_time + timedelta(minutes=self.search_window_minutes)
        
        # Look for spikes that start within the search window
        candidates = []
        for spike in spikes:
            # Spike must start after meal and within search window
            if meal_time <= spike.start_time <= search_end:
                delay = (spike.start_time - meal_time).total_seconds() / 60
                candidates.append((spike, delay))
        
        if not candidates:
            return None
        
        # If multiple candidates, choose the closest one to the meal
        candidates.sort(key=lambda x: x[1])
        best_spike, delay = candidates[0]
        
        # Create match
        match = MealSpikeMatch()
        match.meal = meal
        match.spike = best_spike
        match.delay_minutes = delay
        
        return match
    
    def _flag_complex_events(self, matches, all_meals):
        """
        Flag matches where multiple meals are close together
        
        Args:
            matches: List of MealSpikeMatch objects
            all_meals: List of all meals with datetime
        """
        for match in matches:
            if not match.meal:
                continue
            
            meal_time = match.meal['datetime']
            nearby = []
            
            # Look for other meals within proximity threshold
            for other_meal in all_meals:
                if other_meal['timestamp'] == match.meal['timestamp']:
                    continue  # Skip self
                
                other_time = other_meal['datetime']
                time_diff = abs((other_time - meal_time).total_seconds() / 60)
                
                if time_diff <= self.proximity_threshold_minutes:
                    nearby.append({
                        'timestamp': other_meal['timestamp'],
                        'gl': other_meal['gl'],
                        'minutes_apart': time_diff
                    })
            
            if nearby:
                match.is_complex = True
                match.nearby_meals = nearby
    
    def get_stats(self, match_results):
        """
        Get statistics about meal-spike matching
        
        Args:
            match_results: Dict from match_meals_to_spikes()
            
        Returns:
            dict: Statistics about matching
        """
        matched = match_results['matched']
        unmatched_spikes = match_results['unmatched_spikes']
        unmatched_meals = match_results['unmatched_meals']
        
        stats = {
            'total_meals': len(matched) + len(unmatched_meals),
            'total_spikes': len(matched) + len(unmatched_spikes),
            'matched_count': len(matched),
            'unmatched_spikes': len(unmatched_spikes),
            'unmatched_meals': len(unmatched_meals),
            'complex_events': sum(1 for m in matched if m.is_complex)
        }
        
        if matched:
            stats['avg_delay'] = sum(m.delay_minutes for m in matched) / len(matched)
            stats['min_delay'] = min(m.delay_minutes for m in matched)
            stats['max_delay'] = max(m.delay_minutes for m in matched)
            
            # GL statistics for matched meals
            gls = [m.meal['gl'] for m in matched]
            stats['avg_gl'] = sum(gls) / len(gls)
            stats['min_gl'] = min(gls)
            stats['max_gl'] = max(gls)
            
            # Spike magnitude for matched spikes
            magnitudes = [m.spike.magnitude for m in matched]
            stats['avg_magnitude'] = sum(magnitudes) / len(magnitudes)
        else:
            stats['avg_delay'] = 0
            stats['min_delay'] = 0
            stats['max_delay'] = 0
            stats['avg_gl'] = 0
            stats['min_gl'] = 0
            stats['max_gl'] = 0
            stats['avg_magnitude'] = 0
        
        return stats
    
    def get_unmatched_spike_summary(self, unmatched_spikes):
        """
        Get summary of unmatched spikes (potential unexplained events)
        
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
            matches: List of MealSpikeMatch objects
            start_date: Optional start datetime string (YYYY-MM-DD:HH:MM)
            end_date: Optional end datetime string (YYYY-MM-DD:HH:MM)
            
        Returns:
            list: Filtered matches
        """
        if not start_date and not end_date:
            return matches
        
        filtered = []
        for match in matches:
            meal_time_str = match.meal['timestamp']
            
            if start_date and meal_time_str < start_date:
                continue
            if end_date and meal_time_str > end_date:
                continue
            
            filtered.append(match)
        
        return filtered
