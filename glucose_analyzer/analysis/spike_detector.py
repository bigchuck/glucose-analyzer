"""
Spike Detection Module
Identifies significant glucose spike events in CGM data
"""

import pandas as pd
from datetime import timedelta


class SpikeEvent:
    """Represents a detected glucose spike event"""
    
    def __init__(self):
        self.start_time = None
        self.start_glucose = None
        self.peak_time = None
        self.peak_glucose = None
        self.end_time = None
        self.end_glucose = None
        self.duration_minutes = None
        self.time_to_peak_minutes = None
        self.magnitude = None  # Peak - start
        self.end_reason = None  # Why the spike ended
    
    def __repr__(self):
        return (f"SpikeEvent(start={self.start_time}, peak={self.peak_glucose}mg/dL "
                f"at {self.peak_time}, end={self.end_time}, magnitude={self.magnitude}mg/dL)")
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'start_glucose': float(self.start_glucose) if self.start_glucose else None,
            'peak_time': self.peak_time.isoformat() if self.peak_time else None,
            'peak_glucose': float(self.peak_glucose) if self.peak_glucose else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'end_glucose': float(self.end_glucose) if self.end_glucose else None,
            'duration_minutes': float(self.duration_minutes) if self.duration_minutes else None,
            'time_to_peak_minutes': float(self.time_to_peak_minutes) if self.time_to_peak_minutes else None,
            'magnitude': float(self.magnitude) if self.magnitude else None,
            'end_reason': self.end_reason
        }


class SpikeDetector:
    """Detects glucose spike events in CGM data"""
    
    def __init__(self, config):
        """
        Initialize spike detector with configuration
        
        Args:
            config: Config object with spike detection parameters
        """
        self.config = config
        
        # Load parameters from config
        self.min_spike_magnitude = config.get('spike_detection', 'min_spike_magnitude')
        self.min_spike_threshold = config.get('spike_detection', 'min_spike_threshold')
        
        # End criteria
        end_criteria = config.get('spike_detection', 'end_criteria')
        self.return_tolerance = end_criteria['return_tolerance']
        self.flat_rate_threshold = end_criteria['flat_rate_threshold']
        self.flat_duration_minutes = end_criteria['flat_duration_minutes']
        self.max_duration_minutes = end_criteria['max_duration_minutes']
    
    def detect_spikes(self, cgm_data):
        """
        Detect all spike events in CGM data
        
        Args:
            cgm_data: DataFrame with 'timestamp' and 'glucose' columns
            
        Returns:
            list: List of SpikeEvent objects
        """
        if cgm_data is None or len(cgm_data) == 0:
            return []
        
        spikes = []
        i = 0
        
        while i < len(cgm_data):
            # Look for spike start
            spike_start_idx = self._find_spike_start(cgm_data, i)
            
            if spike_start_idx is None:
                break  # No more spikes found
            
            # Found a spike start, now find its peak and end
            spike = self._analyze_spike(cgm_data, spike_start_idx)
            
            if spike:
                spikes.append(spike)
                # Continue searching after this spike ends
                i = cgm_data[cgm_data['timestamp'] == spike.end_time].index[0] + 1
            else:
                # Failed to complete spike analysis, move forward
                i = spike_start_idx + 1
        
        return spikes
    
    def _find_spike_start(self, cgm_data, start_idx):
        """
        Find the start of a spike from given index
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Index to start searching from
            
        Returns:
            int: Index of spike start, or None if not found
        """
        # Look for a local minimum followed by significant rise
        for i in range(start_idx, len(cgm_data) - 1):
            current_glucose = cgm_data.iloc[i]['glucose']
            
            # Check if this could be a valley (local minimum)
            is_valley = self._is_local_valley(cgm_data, i)
            
            if not is_valley:
                continue
            
            # From this potential valley, look ahead for significant rise
            rise_found = self._check_for_rise(cgm_data, i)
            
            if rise_found:
                return i
        
        return None
    
    def _is_local_valley(self, cgm_data, idx, window=2):
        """
        Check if index is a local minimum (valley)
        
        Args:
            cgm_data: DataFrame with CGM data
            idx: Index to check
            window: Number of points to check on each side
            
        Returns:
            bool: True if this is a local valley
        """
        if idx < window or idx >= len(cgm_data) - window:
            return False
        
        current = cgm_data.iloc[idx]['glucose']
        
        # Check points before
        for i in range(max(0, idx - window), idx):
            if cgm_data.iloc[i]['glucose'] < current:
                return False
        
        # Check points after
        for i in range(idx + 1, min(len(cgm_data), idx + window + 1)):
            if cgm_data.iloc[i]['glucose'] < current:
                return False
        
        return True
    
    def _check_for_rise(self, cgm_data, start_idx, lookforward_minutes=90):
        """
        Check if there's a significant rise after start index
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Starting index
            lookforward_minutes: How far ahead to look
            
        Returns:
            bool: True if significant rise detected
        """
        start_time = cgm_data.iloc[start_idx]['timestamp']
        start_glucose = cgm_data.iloc[start_idx]['glucose']
        end_time = start_time + timedelta(minutes=lookforward_minutes)
        
        # Get data in the lookforward window
        window_data = cgm_data[
            (cgm_data['timestamp'] > start_time) & 
            (cgm_data['timestamp'] <= end_time)
        ]
        
        if len(window_data) == 0:
            return False
        
        max_glucose = window_data['glucose'].max()
        rise = max_glucose - start_glucose
        
        # Check if rise meets magnitude threshold OR absolute threshold
        meets_magnitude = rise >= self.min_spike_magnitude
        meets_threshold = max_glucose >= self.min_spike_threshold
        
        return meets_magnitude or meets_threshold
    
    def _analyze_spike(self, cgm_data, start_idx):
        """
        Analyze a complete spike: find peak and end
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Index where spike starts
            
        Returns:
            SpikeEvent: Complete spike event, or None if analysis fails
        """
        spike = SpikeEvent()
        
        # Set start
        spike.start_time = cgm_data.iloc[start_idx]['timestamp']
        spike.start_glucose = cgm_data.iloc[start_idx]['glucose']
        
        # Find peak
        peak_idx = self._find_peak(cgm_data, start_idx)
        if peak_idx is None:
            return None
        
        spike.peak_time = cgm_data.iloc[peak_idx]['timestamp']
        spike.peak_glucose = cgm_data.iloc[peak_idx]['glucose']
        spike.magnitude = spike.peak_glucose - spike.start_glucose
        
        # Calculate time to peak
        spike.time_to_peak_minutes = (spike.peak_time - spike.start_time).total_seconds() / 60
        
        # Find end
        end_idx, end_reason = self._find_spike_end(cgm_data, start_idx, peak_idx)
        if end_idx is None:
            return None
        
        spike.end_time = cgm_data.iloc[end_idx]['timestamp']
        spike.end_glucose = cgm_data.iloc[end_idx]['glucose']
        spike.end_reason = end_reason
        
        # Calculate total duration
        spike.duration_minutes = (spike.end_time - spike.start_time).total_seconds() / 60
        
        return spike
    
    def _find_peak(self, cgm_data, start_idx):
        """
        Find the peak glucose value after spike start
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Index where spike starts
            
        Returns:
            int: Index of peak, or None if not found
        """
        start_time = cgm_data.iloc[start_idx]['timestamp']
        max_time = start_time + timedelta(minutes=self.max_duration_minutes)
        
        # Get data from start to max duration
        window_data = cgm_data[
            (cgm_data['timestamp'] >= start_time) & 
            (cgm_data['timestamp'] <= max_time)
        ]
        
        if len(window_data) == 0:
            return None
        
        # Find highest glucose value
        peak_idx = window_data['glucose'].idxmax()
        
        return peak_idx
    
    def _find_spike_end(self, cgm_data, start_idx, peak_idx):
        """
        Find where the spike ends based on multiple criteria
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Index where spike starts
            peak_idx: Index of peak glucose
            
        Returns:
            tuple: (end_idx, end_reason) or (None, None) if not found
        """
        start_glucose = cgm_data.iloc[start_idx]['glucose']
        peak_time = cgm_data.iloc[peak_idx]['timestamp']
        max_time = cgm_data.iloc[start_idx]['timestamp'] + timedelta(minutes=self.max_duration_minutes)
        
        # Start looking after the peak
        search_data = cgm_data[
            (cgm_data['timestamp'] > peak_time) & 
            (cgm_data['timestamp'] <= max_time)
        ]
        
        if len(search_data) == 0:
            # Spike extends beyond our data or max duration
            return peak_idx, "max_duration"
        
        # Check each point after peak for end criteria
        for i, row in search_data.iterrows():
            current_glucose = row['glucose']
            
            # Criterion 1: Return to near start level
            if abs(current_glucose - start_glucose) <= self.return_tolerance:
                return i, "returned_to_baseline"
            
            # Criterion 2: Sustained flat rate (plateau)
            if self._check_sustained_flat(cgm_data, i):
                return i, "plateau"
        
        # If we get here, spike didn't end within max duration
        last_idx = search_data.index[-1]
        return last_idx, "max_duration"
    
    def _check_sustained_flat(self, cgm_data, idx):
        """
        Check if glucose is flat (not changing much) for sustained period
        
        Args:
            cgm_data: DataFrame with CGM data
            idx: Current index
            
        Returns:
            bool: True if sustained flat rate detected
        """
        # Need enough data points after this index
        points_needed = self.flat_duration_minutes // 5  # 5-minute intervals
        
        if idx + points_needed >= len(cgm_data):
            return False
        
        # Get the next N points
        window = cgm_data.iloc[idx:idx + points_needed + 1]
        
        # Check rate of change for each consecutive pair
        for i in range(len(window) - 1):
            glucose_1 = window.iloc[i]['glucose']
            glucose_2 = window.iloc[i + 1]['glucose']
            rate = abs(glucose_2 - glucose_1)
            
            if rate > self.flat_rate_threshold:
                return False
        
        return True
    
    def get_stats(self, spikes):
        """
        Get summary statistics about detected spikes
        
        Args:
            spikes: List of SpikeEvent objects
            
        Returns:
            dict: Statistics about spikes
        """
        if not spikes:
            return {
                'count': 0,
                'avg_magnitude': 0,
                'avg_peak': 0,
                'avg_duration': 0,
                'avg_time_to_peak': 0
            }
        
        return {
            'count': len(spikes),
            'avg_magnitude': sum(s.magnitude for s in spikes) / len(spikes),
            'max_magnitude': max(s.magnitude for s in spikes),
            'avg_peak': sum(s.peak_glucose for s in spikes) / len(spikes),
            'max_peak': max(s.peak_glucose for s in spikes),
            'avg_duration': sum(s.duration_minutes for s in spikes) / len(spikes),
            'avg_time_to_peak': sum(s.time_to_peak_minutes for s in spikes) / len(spikes),
            'end_reasons': {
                'returned_to_baseline': sum(1 for s in spikes if s.end_reason == 'returned_to_baseline'),
                'plateau': sum(1 for s in spikes if s.end_reason == 'plateau'),
                'max_duration': sum(1 for s in spikes if s.end_reason == 'max_duration')
            }
        }
