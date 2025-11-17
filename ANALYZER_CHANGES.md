# Analyzer Changes for Normalizer Integration

## Changes to glucose_analyzer/analyzer.py

### 1. Add Import (Line ~7)

**FIND:**
```python
from glucose_analyzer.parsers.csv_parser import LibreViewParser
from glucose_analyzer.analysis.spike_detector import SpikeDetector
from glucose_analyzer.analysis.meal_matcher import MealMatcher
```

**CHANGE TO:**
```python
from glucose_analyzer.parsers.csv_parser import LibreViewParser
from glucose_analyzer.analysis.spike_detector import SpikeDetector
from glucose_analyzer.analysis.meal_matcher import MealMatcher
from glucose_analyzer.analysis.normalizer import SpikeNormalizer
```

### 2. Initialize Normalizer in __init__() (Line ~25)

**FIND:**
```python
self.spike_detector = SpikeDetector(self.config)
self.meal_matcher = MealMatcher(self.config)
self.detected_spikes = []
self.match_results = None
```

**CHANGE TO:**
```python
self.spike_detector = SpikeDetector(self.config)
self.meal_matcher = MealMatcher(self.config)
self.normalizer = SpikeNormalizer()
self.detected_spikes = []
self.match_results = None
self.normalized_profiles = []
```

### 3. Add Normalization to run_analysis() (Line ~110)

**FIND THIS SECTION (after meal matching completes):**
```python
            if match_stats['matched_count'] > 0:
                print(f"\nMatched Event Statistics:")
                print("=" * 60)
                print(f"Average delay (meal to spike): {match_stats['avg_delay']:.1f} minutes")
                # ... more statistics ...
```

**ADD BEFORE THE STATISTICS PRINTING:**
```python
            if match_stats['matched_count'] > 0:
                # Normalize matched profiles
                print(f"\nCreating normalized profiles...")
                self.normalized_profiles = self.normalizer.normalize_matches(
                    self.match_results['matched'], 
                    self.cgm_data
                )
                print(f"[OK] Normalized {len(self.normalized_profiles)} spike profiles")
                
                print(f"\nMatched Event Statistics:")
                print("=" * 60)
                print(f"Average delay (meal to spike): {match_stats['avg_delay']:.1f} minutes")
                # ... rest of statistics ...
```

### Complete Modified run_analysis() Section

Here's the complete section with normalization added:

```python
            # Normalize matched profiles
            if match_stats['matched_count'] > 0:
                print(f"\nCreating normalized profiles...")
                self.normalized_profiles = self.normalizer.normalize_matches(
                    self.match_results['matched'], 
                    self.cgm_data
                )
                print(f"[OK] Normalized {len(self.normalized_profiles)} spike profiles")
                
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
```

### 4. Optional: Add Group Comparison Method (End of Class)

This is optional but useful. Add at the end of the GlucoseAnalyzer class:

```python
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
```

## Summary of Changes

**Total changes: 3 main edits + 1 optional method**

1. **Import statement** - Add normalizer import (1 line)
2. **Initialization** - Add normalizer and profiles list (2 lines)
3. **run_analysis()** - Add normalization step (5 lines)
4. **Optional** - Add group comparison method (35 lines)

**Total lines added:** ~8 lines required, +35 optional

All changes are additive - no existing code needs to be removed!

## Testing After Changes

```bash
$ python glucose_analyzer.py
> analyze

... spike detection ...
... meal matching ...
Creating normalized profiles...
[OK] Normalized 5 spike profiles

> list profiles
Normalized Spike Profiles (5 total):
...
```

If you see "Creating normalized profiles..." message, integration is successful!
