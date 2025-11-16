"""
AUC (Area Under Curve) Calculator for Glucose Spike Analysis

Provides multiple AUC calculation methods for analyzing glucose responses
to meals from CGM data.
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SpikeData:
    """Container for glucose spike data"""
    timestamps: List[float]  # Minutes from meal time
    glucose: List[float]     # mg/dL
    baseline: float          # Baseline glucose level (mg/dL)
    peak: float             # Peak glucose level (mg/dL)
    meal_time: str          # ISO format timestamp
    glycemic_load: float    # Glycemic load of the meal


@dataclass
class AUCResults:
    """Container for AUC calculation results"""
    auc_0: float           # Total area above 0
    auc_70: float          # Area above 70 mg/dL threshold
    auc_relative: float    # Area above baseline
    normalized_auc: float  # Normalized 0-1 scale
    duration: float        # Duration of spike in minutes
    peak_time: float       # Time to peak in minutes
    recovery_time: Optional[float]  # Time to return to baseline (if applicable)


def calculate_auc_trapezoidal(x: np.ndarray, y: np.ndarray, baseline: float = 0.0) -> float:
    """
    Calculate area under curve using trapezoidal rule.
    
    Args:
        x: Time points (minutes)
        y: Glucose values (mg/dL)
        baseline: Baseline value to subtract (default 0)
    
    Returns:
        AUC value (mg/dL * minutes)
    """
    # Subtract baseline from glucose values
    y_adjusted = np.maximum(y - baseline, 0)  # Only positive areas
    
    # Calculate AUC using trapezoidal rule
    auc = np.trapezoid(y_adjusted, x)
    
    return auc


def find_baseline(glucose: np.ndarray, pre_meal_window: int = 3) -> float:
    """
    Determine baseline glucose from pre-meal readings.
    
    Args:
        glucose: Array of glucose values
        pre_meal_window: Number of readings before meal to average
    
    Returns:
        Baseline glucose level (mg/dL)
    """
    if len(glucose) < pre_meal_window:
        return glucose[0]
    
    return np.mean(glucose[:pre_meal_window])


def find_peak_info(timestamps: np.ndarray, glucose: np.ndarray) -> Tuple[float, float]:
    """
    Find peak glucose and time to peak.
    
    Args:
        timestamps: Time points (minutes from meal)
        glucose: Glucose values
    
    Returns:
        Tuple of (peak_glucose, time_to_peak)
    """
    peak_idx = np.argmax(glucose)
    peak_glucose = glucose[peak_idx]
    time_to_peak = timestamps[peak_idx]
    
    return peak_glucose, time_to_peak


def find_recovery_time(timestamps: np.ndarray, glucose: np.ndarray, 
                       baseline: float, tolerance: float = 5.0) -> Optional[float]:
    """
    Find time when glucose returns to baseline.
    
    Args:
        timestamps: Time points (minutes from meal)
        glucose: Glucose values
        baseline: Baseline glucose level
        tolerance: Tolerance for considering "returned to baseline" (mg/dL)
    
    Returns:
        Recovery time in minutes, or None if not recovered within window
    """
    # Find peak first
    peak_idx = np.argmax(glucose)
    
    # Search after peak for return to baseline
    for i in range(peak_idx + 1, len(glucose)):
        if glucose[i] <= baseline + tolerance:
            return timestamps[i]
    
    return None


def calculate_normalized_auc(timestamps: np.ndarray, glucose: np.ndarray, 
                             baseline: float, peak: float) -> float:
    """
    Calculate normalized AUC where baseline=0 and peak=1.
    
    This allows comparison of spike shapes independent of magnitude.
    
    Args:
        timestamps: Time points
        glucose: Glucose values
        baseline: Baseline glucose
        peak: Peak glucose
    
    Returns:
        Normalized AUC (dimensionless)
    """
    if peak <= baseline:
        return 0.0
    
    # Normalize glucose to 0-1 scale
    glucose_normalized = (glucose - baseline) / (peak - baseline)
    glucose_normalized = np.clip(glucose_normalized, 0, 1)
    
    # Calculate AUC of normalized curve
    auc = np.trapezoid(glucose_normalized, timestamps)
    
    return auc


def analyze_spike(spike_data: SpikeData) -> AUCResults:
    """
    Perform complete AUC analysis on a glucose spike.
    
    Args:
        spike_data: SpikeData object containing glucose readings
    
    Returns:
        AUCResults object with all calculated metrics
    """
    timestamps = np.array(spike_data.timestamps)
    glucose = np.array(spike_data.glucose)
    baseline = spike_data.baseline
    peak = spike_data.peak
    
    # Calculate different AUC methods
    auc_0 = calculate_auc_trapezoidal(timestamps, glucose, baseline=0)
    auc_70 = calculate_auc_trapezoidal(timestamps, glucose, baseline=70)
    auc_relative = calculate_auc_trapezoidal(timestamps, glucose, baseline=baseline)
    
    # Calculate normalized AUC for shape comparison
    normalized_auc = calculate_normalized_auc(timestamps, glucose, baseline, peak)
    
    # Find temporal metrics
    peak_glucose, peak_time = find_peak_info(timestamps, glucose)
    recovery_time = find_recovery_time(timestamps, glucose, baseline)
    duration = timestamps[-1] - timestamps[0]
    
    return AUCResults(
        auc_0=auc_0,
        auc_70=auc_70,
        auc_relative=auc_relative,
        normalized_auc=normalized_auc,
        duration=duration,
        peak_time=peak_time,
        recovery_time=recovery_time
    )


def compare_spike_groups(group1_spikes: List[AUCResults], 
                        group2_spikes: List[AUCResults]) -> dict:
    """
    Compare AUC metrics between two groups of spikes.
    
    Args:
        group1_spikes: List of AUCResults from first time period
        group2_spikes: List of AUCResults from second time period
    
    Returns:
        Dictionary with comparison metrics
    """
    def get_stats(spikes: List[AUCResults], metric: str) -> dict:
        values = [getattr(s, metric) for s in spikes]
        return {
            'mean': np.mean(values),
            'median': np.median(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'count': len(values)
        }
    
    metrics = ['auc_relative', 'normalized_auc', 'peak_time', 'recovery_time']
    comparison = {}
    
    for metric in metrics:
        comparison[metric] = {
            'group1': get_stats(group1_spikes, metric),
            'group2': get_stats(group2_spikes, metric),
        }
        
        # Calculate improvement percentage (lower is better for AUC)
        g1_mean = comparison[metric]['group1']['mean']
        g2_mean = comparison[metric]['group2']['mean']
        
        if g1_mean != 0:
            pct_change = ((g2_mean - g1_mean) / g1_mean) * 100
            comparison[metric]['percent_change'] = pct_change
            comparison[metric]['improvement'] = -pct_change  # Negative = improvement
        
    return comparison


# Example usage
if __name__ == "__main__":
    # Example spike data
    example_spike = SpikeData(
        timestamps=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90],
        glucose=[95, 98, 105, 118, 135, 148, 152, 150, 142, 130, 120, 110, 105, 100, 98, 96, 95, 94, 95],
        baseline=95,
        peak=152,
        meal_time="2025-11-14T18:00:00",
        glycemic_load=33
    )
    
    results = analyze_spike(example_spike)
    
    print("AUC Analysis Results:")
    print(f"  AUC-0: {results.auc_0:.1f} mg/dL*min")
    print(f"  AUC-70: {results.auc_70:.1f} mg/dL*min")
    print(f"  AUC-relative: {results.auc_relative:.1f} mg/dL*min")
    print(f"  Normalized AUC: {results.normalized_auc:.3f}")
    print(f"  Peak time: {results.peak_time:.1f} min")
    print(f"  Recovery time: {results.recovery_time:.1f} min" if results.recovery_time else "  Recovery time: Not recovered")
    print(f"  Duration: {results.duration:.1f} min")