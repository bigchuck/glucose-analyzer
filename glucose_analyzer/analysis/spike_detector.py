"""
Spike Detection Module
Identifies significant glucose spike events in CGM data
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from dataclasses import dataclass
from typing import Optional

# Import AUC calculator
import sys
sys.path.insert(0, '/home/claude')
from glucose_analyzer.analysis.auc_calculator import SpikeData, analyze_spike, AUCResults


@dataclass
class Spike:
    """Represents a detected glucose spike event"""
    start_time: pd.Timestamp
    start_glucose: float
    peak_time: pd.Timestamp
    peak_glucose: float
    end_time: pd.Timestamp
    end_glucose: float
    duration_minutes: float
    time_to_peak_minutes: float
    magnitude: float
    end_reason: str
    
    # AUC metrics from auc_calculator
    auc_0: float = 0.0
    auc_70: float = 0.0
    auc_relative: float = 0.0
    normalized_auc: float = 0.0
    baseline: float = 0.0
    recovery_time: Optional[float] = None  # Minutes from meal to return to baseline
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'start_time': self.start_time.isoformat(),
            'start_glucose': float(self.start_glucose),
            'peak_time': self.peak_time.isoformat(),
            'peak_glucose': float(self.peak_glucose),
            'end_time': self.end_time.isoformat(),
            'end_glucose': float(self.end_glucose),
            'duration_minutes': float(self.duration_minutes),
            'time_to_peak_minutes': float(self.time_to_peak_minutes),
            'magnitude': float(self.magnitude),
            'end_reason': self.end_reason,
            'auc_0': float(self.auc_0),
            'auc_70': float(self.auc_70),
            'auc_relative': float(self.auc_relative),
            'normalized_auc': float(self.normalized_auc),
            'baseline': float(self.baseline),
            'recovery_time': float(self.recovery_time) if self.recovery_time else None
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

        # Load parameters
        self.min_spike_magnitude = config.get('spike_detection', 'min_spike_magnitude')
        self.min_spike_threshold = config.get('spike_detection', 'min_spike_threshold')
        self.end_return_threshold = config.get('spike_detection', 'end_criteria', 'return_tolerance')
        self.end_rate_threshold = config.get('spike_detection', 'end_criteria', 'flat_rate_threshold')
        self.end_timeout_minutes = config.get('spike_detection', 'end_criteria', 'max_duration_minutes')
    
    def detect_spikes(self, cgm_data):
        """
        Detect all glucose spikes in CGM data
        
        Args:
            cgm_data: DataFrame with columns ['timestamp', 'glucose']
        
        Returns:
            list: List of Spike objects
        """
        if cgm_data.empty:
            return []
        
        spikes = []
        i = 0
        
        while i < len(cgm_data) - 1:
            spike = self._detect_single_spike(cgm_data, i)
            if spike:
                # Calculate comprehensive AUC metrics
                spike = self._calculate_spike_auc(spike, cgm_data)
                spikes.append(spike)
                # Skip past this spike
                i = cgm_data[cgm_data['timestamp'] >= spike.end_time].index[0]
            else:
                i += 1
        
        return spikes
    
    def _detect_single_spike(self, cgm_data, start_idx):
        """
        Detect a single spike starting from given index
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Index to start searching from
        
        Returns:
            Spike object or None if no spike detected
        """
        start_time = cgm_data.iloc[start_idx]['timestamp']
        start_glucose = cgm_data.iloc[start_idx]['glucose']
        
        # Look for peak
        peak_idx = start_idx
        peak_glucose = start_glucose
        
        for i in range(start_idx + 1, len(cgm_data)):
            current_glucose = cgm_data.iloc[i]['glucose']
            
            # Track peak
            if current_glucose > peak_glucose:
                peak_idx = i
                peak_glucose = current_glucose
            
            # Check if we've found a spike (sufficient rise)
            magnitude = peak_glucose - start_glucose
            
            if magnitude >= self.min_spike_magnitude or peak_glucose >= self.min_spike_threshold:
                # Found significant rise, now look for end
                end_idx, end_reason = self._find_spike_end(cgm_data, start_idx, peak_idx)
                
                if end_idx:
                    peak_time = cgm_data.iloc[peak_idx]['timestamp']
                    end_time = cgm_data.iloc[end_idx]['timestamp']
                    end_glucose = cgm_data.iloc[end_idx]['glucose']
                    
                    duration = (end_time - start_time).total_seconds() / 60
                    time_to_peak = (peak_time - start_time).total_seconds() / 60
                    
                    return Spike(
                        start_time=start_time,
                        start_glucose=start_glucose,
                        peak_time=peak_time,
                        peak_glucose=peak_glucose,
                        end_time=end_time,
                        end_glucose=end_glucose,
                        duration_minutes=duration,
                        time_to_peak_minutes=time_to_peak,
                        magnitude=magnitude,
                        end_reason=end_reason,
                        baseline=start_glucose  # Initial baseline
                    )
        
        return None
    
    def _find_spike_end(self, cgm_data, start_idx, peak_idx):
        """
        Find where the spike ends after reaching peak
        
        Args:
            cgm_data: DataFrame with CGM data
            start_idx: Index where spike started
            peak_idx: Index of peak glucose
        
        Returns:
            tuple: (end_index, end_reason) or (None, None)
        """
        start_glucose = cgm_data.iloc[start_idx]['glucose']
        peak_glucose = cgm_data.iloc[peak_idx]['glucose']
        peak_time = cgm_data.iloc[peak_idx]['timestamp']
        
        # Search for end after peak
        for i in range(peak_idx + 1, len(cgm_data)):
            current_glucose = cgm_data.iloc[i]['glucose']
            current_time = cgm_data.iloc[i]['timestamp']
            
            # End criterion 1: Return to baseline
            if abs(current_glucose - start_glucose) <= self.end_return_threshold:
                return i, "returned_to_baseline"
            
            # End criterion 2: Rate flattened (check change over last 3 readings)
            if i >= peak_idx + 3:
                recent_values = cgm_data.iloc[i-2:i+1]['glucose'].values
                rate_of_change = abs(recent_values[-1] - recent_values[0]) / 10  # per minute
                if rate_of_change <= self.end_rate_threshold:
                    return i, "rate_flattened"
            
            # End criterion 3: Timeout
            elapsed = (current_time - peak_time).total_seconds() / 60
            if elapsed >= self.end_timeout_minutes:
                return i, "timeout"
        
        # If we reach end of data, use last point
        return len(cgm_data) - 1, "end_of_data"
    
    def _calculate_spike_auc(self, spike, cgm_data):
        """
        Calculate comprehensive AUC metrics for a spike
        
        Args:
            spike: Spike object with basic info
            cgm_data: DataFrame with CGM data
        
        Returns:
            Spike object with AUC fields populated
        """
        # Extract glucose readings for this spike window
        spike_window = cgm_data[
            (cgm_data['timestamp'] >= spike.start_time) &
            (cgm_data['timestamp'] <= spike.end_time)
        ].copy()
        
        if len(spike_window) < 2:
            # Not enough data for AUC
            return spike
        
        # Convert timestamps to minutes from start
        spike_window['minutes_from_start'] = (
            (spike_window['timestamp'] - spike.start_time).dt.total_seconds() / 60
        )
        
        # Create SpikeData object for auc_calculator
        spike_data = SpikeData(
            timestamps=spike_window['minutes_from_start'].tolist(),
            glucose=spike_window['glucose'].tolist(),
            baseline=spike.baseline,
            peak=spike.peak_glucose,
            meal_time=spike.start_time.isoformat(),
            glycemic_load=0  # Not known at spike detection time
        )
        
        # Calculate comprehensive AUC metrics
        auc_results = analyze_spike(spike_data)
        
        # Update spike with AUC results
        spike.auc_0 = auc_results.auc_0
        spike.auc_70 = auc_results.auc_70
        spike.auc_relative = auc_results.auc_relative
        spike.normalized_auc = auc_results.normalized_auc
        spike.recovery_time = auc_results.recovery_time
        
        return spike
    
    def get_stats(self, spikes):
        """
        Calculate statistics across all spikes
        
        Args:
            spikes: List of Spike objects
        
        Returns:
            dict: Statistics summary
        """
        if not spikes:
            return {
                'count': 0,
                'avg_magnitude': 0,
                'avg_duration': 0,
                'avg_time_to_peak': 0,
                'avg_auc_70': 0,
                'avg_auc_relative': 0,
                'avg_normalized_auc': 0
            }
        
        return {
            'count': len(spikes),
            'avg_magnitude': np.mean([s.magnitude for s in spikes]),
            'max_magnitude': max([s.magnitude for s in spikes]),
            'avg_duration': np.mean([s.duration_minutes for s in spikes]),
            'avg_time_to_peak': np.mean([s.time_to_peak_minutes for s in spikes]),
            'avg_auc_70': np.mean([s.auc_70 for s in spikes]),
            'avg_auc_relative': np.mean([s.auc_relative for s in spikes]),
            'avg_normalized_auc': np.mean([s.normalized_auc for s in spikes]),
            'avg_recovery_time': np.mean([s.recovery_time for s in spikes if s.recovery_time])
        }