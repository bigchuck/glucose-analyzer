"""
Spike Normalizer Module
Creates normalized spike profiles for shape-based comparison
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class NormalizedProfile:
    """Normalized spike profile for comparison"""
    timestamps_minutes: np.ndarray  # Minutes from spike start (absolute time)
    normalized_glucose: np.ndarray  # Normalized 0-1 scale (baseline to peak)
    original_baseline: float        # Original baseline glucose (mg/dL)
    original_peak: float           # Original peak glucose (mg/dL)
    original_magnitude: float      # Original magnitude (mg/dL)
    duration_minutes: float        # Total duration
    spike_start_time: str         # ISO timestamp of spike start
    meal_timestamp: Optional[str] = None  # Associated meal timestamp if available
    glycemic_load: Optional[float] = None  # GL value if available
    
    def __repr__(self):
        meal_info = f", meal={self.meal_timestamp}" if self.meal_timestamp else ""
        return (f"NormalizedProfile(duration={self.duration_minutes:.0f}min, "
                f"magnitude={self.original_magnitude:.0f}mg/dL{meal_info})")


class SpikeNormalizer:
    """Normalizes spike profiles for shape comparison"""
    
    def __init__(self):
        """Initialize spike normalizer"""
        pass
    
    def normalize_spike(self, spike, cgm_data, meal_info=None):
        """
        Create normalized profile from a spike
        
        Args:
            spike: Spike object from spike_detector
            cgm_data: DataFrame with CGM data
            meal_info: Optional dict with meal timestamp and GL
            
        Returns:
            NormalizedProfile object
        """
        # Extract glucose readings for this spike window
        spike_window = cgm_data[
            (cgm_data['timestamp'] >= spike.start_time) &
            (cgm_data['timestamp'] <= spike.end_time)
        ].copy()
        
        if len(spike_window) < 2:
            raise ValueError("Insufficient data for normalization")
        
        # Calculate minutes from spike start
        spike_window['minutes_from_start'] = (
            (spike_window['timestamp'] - spike.start_time).dt.total_seconds() / 60
        )
        
        timestamps = spike_window['minutes_from_start'].values
        glucose = spike_window['glucose'].values
        
        # Normalize glucose: 0 (baseline) to 1.0 (peak)
        baseline = spike.baseline
        peak = spike.peak_glucose
        
        if peak <= baseline:
            # Degenerate case - shouldn't happen but handle gracefully
            normalized = np.zeros_like(glucose)
        else:
            normalized = (glucose - baseline) / (peak - baseline)
            normalized = np.clip(normalized, 0, 1)  # Ensure 0-1 range
        
        # Extract meal info if provided
        meal_timestamp = None
        glycemic_load = None
        if meal_info:
            meal_timestamp = meal_info.get('timestamp')
            glycemic_load = meal_info.get('gl')
        
        return NormalizedProfile(
            timestamps_minutes=timestamps,
            normalized_glucose=normalized,
            original_baseline=baseline,
            original_peak=peak,
            original_magnitude=spike.magnitude,
            duration_minutes=spike.duration_minutes,
            spike_start_time=spike.start_time.isoformat(),
            meal_timestamp=meal_timestamp,
            glycemic_load=glycemic_load
        )
    
    def normalize_matches(self, matches, cgm_data):
        """
        Normalize all matched meal-spike pairs
        
        Args:
            matches: List of MealSpikeMatch objects
            cgm_data: DataFrame with CGM data
            
        Returns:
            List of NormalizedProfile objects
        """
        profiles = []
        
        for match in matches:
            meal_info = {
                'timestamp': match.meal['timestamp'],
                'gl': match.meal['gl']
            }
            
            try:
                profile = self.normalize_spike(match.spike, cgm_data, meal_info)
                profiles.append(profile)
            except ValueError as e:
                print(f"[WARNING] Could not normalize spike at {match.spike.start_time}: {e}")
                continue
        
        return profiles
    
    def compare_profiles(self, profiles: List[NormalizedProfile]) -> dict:
        """
        Compare multiple normalized profiles
        
        Args:
            profiles: List of NormalizedProfile objects
            
        Returns:
            dict: Comparison statistics
        """
        if not profiles:
            return {}
        
        stats = {
            'count': len(profiles),
            'avg_duration': np.mean([p.duration_minutes for p in profiles]),
            'std_duration': np.std([p.duration_minutes for p in profiles]),
            'min_duration': min([p.duration_minutes for p in profiles]),
            'max_duration': max([p.duration_minutes for p in profiles]),
            'avg_magnitude': np.mean([p.original_magnitude for p in profiles]),
            'std_magnitude': np.std([p.original_magnitude for p in profiles]),
        }
        
        # If GL values available, add GL stats
        profiles_with_gl = [p for p in profiles if p.glycemic_load is not None]
        if profiles_with_gl:
            stats['avg_gl'] = np.mean([p.glycemic_load for p in profiles_with_gl])
            stats['std_gl'] = np.std([p.glycemic_load for p in profiles_with_gl])
        
        return stats
    
    def align_profiles_by_duration(self, profiles: List[NormalizedProfile], 
                                   num_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        Align profiles to common time grid for averaging
        
        Args:
            profiles: List of NormalizedProfile objects
            num_points: Number of interpolation points
            
        Returns:
            Tuple of (common_time_grid, aligned_profiles_array)
        """
        if not profiles:
            return np.array([]), np.array([])
        
        # Find maximum duration for time grid
        max_duration = max([p.duration_minutes for p in profiles])
        common_time = np.linspace(0, max_duration, num_points)
        
        # Interpolate each profile onto common time grid
        aligned = np.zeros((len(profiles), num_points))
        
        for i, profile in enumerate(profiles):
            # Interpolate to common time grid
            # Use 0 for times beyond this profile's duration
            aligned[i, :] = np.interp(
                common_time, 
                profile.timestamps_minutes, 
                profile.normalized_glucose,
                left=0,  # Before spike
                right=0  # After spike ends
            )
        
        return common_time, aligned
    
    def calculate_average_profile(self, profiles: List[NormalizedProfile],
                                  num_points: int = 100) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate average normalized profile across multiple spikes
        
        Args:
            profiles: List of NormalizedProfile objects
            num_points: Number of interpolation points
            
        Returns:
            Tuple of (time_grid, mean_profile, std_profile)
        """
        if not profiles:
            return np.array([]), np.array([]), np.array([])
        
        common_time, aligned = self.align_profiles_by_duration(profiles, num_points)
        
        # Calculate mean and std
        mean_profile = np.mean(aligned, axis=0)
        std_profile = np.std(aligned, axis=0)
        
        return common_time, mean_profile, std_profile
    
    def calculate_shape_similarity(self, profile1: NormalizedProfile, 
                                   profile2: NormalizedProfile,
                                   num_points: int = 50) -> float:
        """
        Calculate similarity score between two normalized profiles
        Uses correlation coefficient of interpolated profiles
        
        Args:
            profile1: First NormalizedProfile
            profile2: Second NormalizedProfile
            num_points: Number of interpolation points
            
        Returns:
            float: Correlation coefficient (1 = identical shape, -1 = opposite)
        """
        # Use shorter duration for comparison
        max_time = min(profile1.duration_minutes, profile2.duration_minutes)
        common_time = np.linspace(0, max_time, num_points)
        
        # Interpolate both profiles
        interp1 = np.interp(common_time, profile1.timestamps_minutes, 
                           profile1.normalized_glucose)
        interp2 = np.interp(common_time, profile2.timestamps_minutes, 
                           profile2.normalized_glucose)
        
        # Calculate correlation
        correlation = np.corrcoef(interp1, interp2)[0, 1]
        
        return correlation
    
    def find_similar_spikes(self, target_profile: NormalizedProfile,
                           candidate_profiles: List[NormalizedProfile],
                           threshold: float = 0.8) -> List[Tuple[NormalizedProfile, float]]:
        """
        Find spikes with similar shapes to target
        
        Args:
            target_profile: Profile to match against
            candidate_profiles: List of profiles to search
            threshold: Minimum correlation coefficient
            
        Returns:
            List of (profile, similarity_score) tuples, sorted by similarity
        """
        similarities = []
        
        for candidate in candidate_profiles:
            if candidate.spike_start_time == target_profile.spike_start_time:
                continue  # Skip self
            
            similarity = self.calculate_shape_similarity(target_profile, candidate)
            if similarity >= threshold:
                similarities.append((candidate, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities
    
    def compare_groups(self, group1_profiles: List[NormalizedProfile],
                      group2_profiles: List[NormalizedProfile]) -> dict:
        """
        Compare normalized profiles between two groups
        
        Args:
            group1_profiles: First group of profiles
            group2_profiles: Second group of profiles
            
        Returns:
            dict: Comprehensive comparison statistics
        """
        comparison = {
            'group1': self.compare_profiles(group1_profiles),
            'group2': self.compare_profiles(group2_profiles)
        }
        
        # Calculate average profiles for each group
        if group1_profiles:
            time1, mean1, std1 = self.calculate_average_profile(group1_profiles)
            comparison['group1']['avg_profile_time'] = time1
            comparison['group1']['avg_profile_mean'] = mean1
            comparison['group1']['avg_profile_std'] = std1
        
        if group2_profiles:
            time2, mean2, std2 = self.calculate_average_profile(group2_profiles)
            comparison['group2']['avg_profile_time'] = time2
            comparison['group2']['avg_profile_mean'] = mean2
            comparison['group2']['avg_profile_std'] = std2
        
        # Calculate improvement metrics
        if group1_profiles and group2_profiles:
            g1_stats = comparison['group1']
            g2_stats = comparison['group2']
            
            comparison['improvement'] = {
                'duration_change_min': g2_stats['avg_duration'] - g1_stats['avg_duration'],
                'magnitude_change_mgdl': g2_stats['avg_magnitude'] - g1_stats['avg_magnitude'],
                'duration_pct_change': ((g2_stats['avg_duration'] - g1_stats['avg_duration']) 
                                       / g1_stats['avg_duration'] * 100) if g1_stats['avg_duration'] > 0 else 0,
                'magnitude_pct_change': ((g2_stats['avg_magnitude'] - g1_stats['avg_magnitude']) 
                                        / g1_stats['avg_magnitude'] * 100) if g1_stats['avg_magnitude'] > 0 else 0
            }
        
        return comparison
    
    def get_profile_summary(self, profile: NormalizedProfile) -> dict:
        """
        Get human-readable summary of a normalized profile
        
        Args:
            profile: NormalizedProfile object
            
        Returns:
            dict: Summary information
        """
        summary = {
            'spike_start': profile.spike_start_time,
            'duration_minutes': profile.duration_minutes,
            'baseline_mgdl': profile.original_baseline,
            'peak_mgdl': profile.original_peak,
            'magnitude_mgdl': profile.original_magnitude,
            'data_points': len(profile.timestamps_minutes)
        }
        
        if profile.meal_timestamp:
            summary['meal'] = profile.meal_timestamp
            summary['glycemic_load'] = profile.glycemic_load
        
        return summary


# Example usage
if __name__ == "__main__":
    print("Normalizer module - creates comparable spike profiles")
    print("Normalizes glucose from baseline (0) to peak (1.0)")
    print("Preserves absolute time duration for shape comparison")