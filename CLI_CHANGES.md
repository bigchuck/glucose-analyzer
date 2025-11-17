# CLI Changes for Normalizer Integration

## Three New Command Methods to Add

### 1. cmd_list_profiles()

Add this method to the CLI class (around line 250, near other list commands):

```python
def cmd_list_profiles(self, args):
    """List normalized profiles: list profiles [start] [end]"""
    if not self.analyzer.normalized_profiles:
        print("No normalized profiles yet. Run 'analyze' first.")
        return
    
    start_filter = args[0] if len(args) > 0 else None
    end_filter = args[1] if len(args) > 1 else None
    
    profiles = self.analyzer.normalized_profiles
    
    # Filter by date range if provided
    if start_filter or end_filter:
        filtered = []
        for profile in profiles:
            if start_filter and profile.spike_start_time < start_filter:
                continue
            if end_filter and profile.spike_start_time > end_filter:
                continue
            filtered.append(profile)
        profiles = filtered
    
    if not profiles:
        print("No profiles found in specified range")
        return
    
    print(f"\nNormalized Spike Profiles ({len(profiles)} total):")
    print("=" * 80)
    for i, profile in enumerate(profiles):
        print(f"\nProfile {i+1}:")
        print(f"  Spike: {profile.spike_start_time}")
        if profile.meal_timestamp:
            print(f"  Meal: {profile.meal_timestamp} (GL={profile.glycemic_load})")
        print(f"  Duration: {profile.duration_minutes:.0f} minutes")
        print(f"  Baseline: {profile.original_baseline:.0f} mg/dL")
        print(f"  Peak: {profile.original_peak:.0f} mg/dL")
        print(f"  Magnitude: {profile.original_magnitude:.0f} mg/dL")
        print(f"  Data points: {len(profile.timestamps_minutes)}")
```

### 2. cmd_compare_groups()

Add this method:

```python
def cmd_compare_groups(self, args):
    """Compare normalized profiles between groups: compare "group1" "group2" """
    if len(args) < 2:
        print("[ERROR] Usage: compare \"group1 description\" \"group2 description\"")
        print("Example: compare \"baseline\" \"after medication\"")
        return
    
    # Parse group descriptions - simple approach: split args in half
    # Better approach: user passes quoted strings
    group1_desc = args[0].strip('"')
    group2_desc = args[1].strip('"')
    
    if not self.analyzer.normalized_profiles:
        print("[ERROR] No normalized profiles available. Run 'analyze' first.")
        return
    
    # Get all groups
    groups = self.analyzer.data_manager.data["groups"]
    
    # Find the two groups
    group1 = None
    group2 = None
    
    for g in groups:
        if g['description'] == group1_desc:
            group1 = g
        if g['description'] == group2_desc:
            group2 = g
    
    if not group1 or not group2:
        print(f"[ERROR] Could not find one or both groups")
        print(f"Available groups:")
        for g in groups:
            print(f"  - \"{g['description']}\"")
        return
    
    # Filter profiles by group date ranges
    group1_profiles = [p for p in self.analyzer.normalized_profiles
                      if group1['start'] <= p.spike_start_time <= (group1['end'] or '9999-12-31')]
    group2_profiles = [p for p in self.analyzer.normalized_profiles
                      if group2['start'] <= p.spike_start_time <= (group2['end'] or '9999-12-31')]
    
    if not group1_profiles or not group2_profiles:
        print(f"[ERROR] One or both groups have no normalized profiles")
        print(f"Group 1 \"{group1_desc}\": {len(group1_profiles)} profiles")
        print(f"Group 2 \"{group2_desc}\": {len(group2_profiles)} profiles")
        return
    
    # Perform comparison using normalizer
    comparison = self.analyzer.normalizer.compare_groups(group1_profiles, group2_profiles)
    
    # Display results
    print(f"\nGroup Comparison:")
    print("=" * 80)
    
    print(f"\nGroup 1: \"{group1_desc}\"")
    print(f"  Date range: {group1['start']} to {group1['end']}")
    print(f"  Count: {comparison['group1']['count']} spikes")
    print(f"  Avg duration: {comparison['group1']['avg_duration']:.0f} ± {comparison['group1']['std_duration']:.0f} min")
    print(f"  Avg magnitude: {comparison['group1']['avg_magnitude']:.0f} ± {comparison['group1']['std_magnitude']:.0f} mg/dL")
    if 'avg_gl' in comparison['group1']:
        print(f"  Avg GL: {comparison['group1']['avg_gl']:.1f} ± {comparison['group1']['std_gl']:.1f}")
    
    print(f"\nGroup 2: \"{group2_desc}\"")
    print(f"  Date range: {group2['start']} to {group2['end']}")
    print(f"  Count: {comparison['group2']['count']} spikes")
    print(f"  Avg duration: {comparison['group2']['avg_duration']:.0f} ± {comparison['group2']['std_duration']:.0f} min")
    print(f"  Avg magnitude: {comparison['group2']['avg_magnitude']:.0f} ± {comparison['group2']['std_magnitude']:.0f} mg/dL")
    if 'avg_gl' in comparison['group2']:
        print(f"  Avg GL: {comparison['group2']['avg_gl']:.1f} ± {comparison['group2']['std_gl']:.1f}")
    
    if 'improvement' in comparison:
        print(f"\nChange (Group 2 vs Group 1):")
        print(f"  Duration: {comparison['improvement']['duration_change_min']:+.0f} min "
              f"({comparison['improvement']['duration_pct_change']:+.1f}%)")
        print(f"  Magnitude: {comparison['improvement']['magnitude_change_mgdl']:+.0f} mg/dL "
              f"({comparison['improvement']['magnitude_pct_change']:+.1f}%)")
        
        # Interpret results
        if comparison['improvement']['duration_pct_change'] < -5:
            print(f"\n  ✓ Improved: Shorter spike duration")
        elif comparison['improvement']['duration_pct_change'] > 5:
            print(f"\n  ⚠ Longer: Spike duration increased")
        
        if comparison['improvement']['magnitude_pct_change'] < -5:
            print(f"  ✓ Improved: Lower spike magnitude")
        elif comparison['improvement']['magnitude_pct_change'] > 5:
            print(f"  ⚠ Higher: Spike magnitude increased")
```

### 3. cmd_find_similar()

Add this method:

```python
def cmd_find_similar(self, args):
    """Find spikes with similar shapes: similar <spike_index> [threshold]"""
    if len(args) < 1:
        print("[ERROR] Usage: similar <spike_index> [threshold]")
        print("Example: similar 3 0.8")
        print("  spike_index: Number from 'list profiles' (1-based)")
        print("  threshold: Similarity score 0.0-1.0 (default 0.8)")
        return
    
    try:
        spike_idx = int(args[0]) - 1  # Convert to 0-indexed
        threshold = float(args[1]) if len(args) > 1 else 0.8
    except (ValueError, IndexError):
        print("[ERROR] Invalid spike index or threshold")
        return
    
    if not self.analyzer.normalized_profiles:
        print("No normalized profiles yet. Run 'analyze' first.")
        return
    
    if spike_idx < 0 or spike_idx >= len(self.analyzer.normalized_profiles):
        print(f"[ERROR] Spike index out of range (1-{len(self.analyzer.normalized_profiles)})")
        return
    
    if threshold < 0 or threshold > 1:
        print("[ERROR] Threshold must be between 0.0 and 1.0")
        return
    
    target = self.analyzer.normalized_profiles[spike_idx]
    similar = self.analyzer.normalizer.find_similar_spikes(
        target, 
        self.analyzer.normalized_profiles,
        threshold
    )
    
    print(f"\nTarget Spike (Profile {spike_idx + 1}):")
    print(f"  Time: {target.spike_start_time}")
    if target.meal_timestamp:
        print(f"  Meal: {target.meal_timestamp} (GL={target.glycemic_load})")
    print(f"  Duration: {target.duration_minutes:.0f} minutes")
    print(f"  Magnitude: {target.original_magnitude:.0f} mg/dL")
    
    if not similar:
        print(f"\n[INFO] No similar spikes found (threshold={threshold:.2f})")
        print(f"Try lowering threshold, e.g.: similar {spike_idx + 1} 0.7")
        return
    
    print(f"\nSimilar Spikes ({len(similar)} found, threshold={threshold:.2f}):")
    print("=" * 80)
    for i, (profile, similarity) in enumerate(similar):
        # Find index in original list
        profile_idx = self.analyzer.normalized_profiles.index(profile) + 1
        
        print(f"\n{i+1}. Profile #{profile_idx} - Similarity: {similarity:.3f}")
        print(f"   Time: {profile.spike_start_time}")
        if profile.meal_timestamp:
            print(f"   Meal: {profile.meal_timestamp} (GL={profile.glycemic_load})")
        print(f"   Duration: {profile.duration_minutes:.0f} min")
        print(f"   Magnitude: {profile.original_magnitude:.0f} mg/dL")
```

## Update process_command() Method

Find the section handling "list" commands (around line 350) and update it:

**FIND THIS:**
```python
elif cmd == "list" and len(args) > 0:
    subcommand = args[0].lower()
    if subcommand == "meals":
        self.cmd_list_meals(args[1:])
    elif subcommand == "groups":
        self.cmd_list_groups(args[1:])
    elif subcommand == "spikes":
        self.cmd_list_spikes(args[1:])
    elif subcommand == "matches":
        self.cmd_list_matches(args[1:])
    elif subcommand == "unmatched":
        self.cmd_list_unmatched(args[1:])
    else:
        print("[ERROR] Unknown list command. Use 'list meals', 'list groups', 'list spikes', 'list matches', or 'list unmatched'")
```

**CHANGE TO:**
```python
elif cmd == "list" and len(args) > 0:
    subcommand = args[0].lower()
    if subcommand == "meals":
        self.cmd_list_meals(args[1:])
    elif subcommand == "groups":
        self.cmd_list_groups(args[1:])
    elif subcommand == "spikes":
        self.cmd_list_spikes(args[1:])
    elif subcommand == "matches":
        self.cmd_list_matches(args[1:])
    elif subcommand == "unmatched":
        self.cmd_list_unmatched(args[1:])
    elif subcommand == "profiles":
        self.cmd_list_profiles(args[1:])
    else:
        print("[ERROR] Unknown list command. Use 'list meals', 'list groups', 'list spikes', 'list matches', 'list unmatched', or 'list profiles'")
```

## Add New Commands to process_command()

Add these lines after the "list" command handler (around line 375):

```python
elif cmd == "compare":
    self.cmd_compare_groups(args)
elif cmd == "similar":
    self.cmd_find_similar(args)
```

## Update cmd_help() Method

Find the cmd_help() method (around line 300) and update the help text:

**FIND THIS:**
```python
def cmd_help(self, args):
    """Show help"""
    print("""
Commands:
  addmeal <timestamp> <gl>           Add meal entry
  group start <timestamp> <desc>     Start new analysis group
  group end <timestamp>              Close current group
  bypass <timestamp> <reason>        Mark spike as bypassed
  analyze                            Run full analysis
  chart group <n>                    Generate group charts
  chart meal <timestamp>             Generate single meal chart
  list meals [start] [end]           List meals in date range
  list groups                        Show all groups
  list spikes [start] [end]          List detected spikes
  list matches [start] [end]         List meal-spike matches
  list unmatched                     Show unmatched spikes and meals
  stats                              Show CGM data statistics
  help                               Show this help
  quit                               Exit program

Timestamp format: YYYY-MM-DD:HH:MM (24-hour)
Example: addmeal 2025-11-14:18:00 33
    """)
```

**CHANGE TO:**
```python
def cmd_help(self, args):
    """Show help"""
    print("""
Commands:
  addmeal <timestamp> <gl>           Add meal entry
  group start <timestamp> <desc>     Start new analysis group
  group end <timestamp>              Close current group
  bypass <timestamp> <reason>        Mark spike as bypassed
  analyze                            Run full analysis
  list meals [start] [end]           List meals in date range
  list groups                        Show all groups
  list spikes [start] [end]          List detected spikes
  list matches [start] [end]         List meal-spike matches
  list unmatched                     Show unmatched spikes and meals
  list profiles [start] [end]        List normalized spike profiles
  compare "group1" "group2"          Compare normalized profiles between groups
  similar <spike_idx> [threshold]    Find spikes with similar shapes (threshold: 0.0-1.0)
  stats                              Show CGM data statistics
  chart group <n>                    Generate group charts (TODO)
  chart meal <timestamp>             Generate single meal chart (TODO)
  help                               Show this help
  quit                               Exit program

Timestamp format: YYYY-MM-DD:HH:MM (24-hour)
Examples:
  addmeal 2025-11-14:18:00 33
  compare "baseline" "after medication"
  similar 3 0.8
    """)
```

## Summary of Changes

**3 new command methods:**
1. `cmd_list_profiles()` - Show normalized profiles
2. `cmd_compare_groups()` - Compare temporal groups
3. `cmd_find_similar()` - Find similar spike shapes

**2 modifications to existing methods:**
1. `process_command()` - Add routing for new commands
2. `cmd_help()` - Update help text

**Total lines added:** ~180 lines

All changes are additive - no existing code needs to be removed!
