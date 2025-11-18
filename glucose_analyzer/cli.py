"""Command-line interface for Glucose Analyzer"""

from datetime import datetime
from pathlib import Path
import json

from glucose_analyzer.analyzer import GlucoseAnalyzer
from glucose_analyzer.analysis.spike_manual import add_spike_interactive


class CLI:
    """Command-line interface shell"""
    
    def __init__(self, analyzer):
        """
        Initialize CLI
        
        Args:
            analyzer: GlucoseAnalyzer instance
        """
        self.analyzer = analyzer
        self.running = True
    
    def parse_timestamp(self, ts_str):
        """
        Parse timestamp string to datetime
        
        Args:
            ts_str: Timestamp string in YYYY-MM-DD:HH:MM format
            
        Returns:
            datetime object or None if invalid
        """
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d:%H:%M")
        except ValueError:
            print("[ERROR] Invalid timestamp format. Use: YYYY-MM-DD:HH:MM")
            return None
    
    def cmd_addmeal(self, args):
        """Add meal entry: addmeal YYYY-MM-DD:HH:MM GL"""
        if len(args) != 2:
            print("[ERROR] Usage: addmeal <timestamp> <gl>")
            return
        
        timestamp_str = args[0]
        try:
            gl = float(args[1])
        except ValueError:
            print("[ERROR] GL must be a number")
            return
        
        # Validate timestamp
        if not self.parse_timestamp(timestamp_str):
            return
        
        self.analyzer.data_manager.add_meal(timestamp_str, gl)
        print(f"[OK] Meal added: {timestamp_str}, GL={gl}")
    
    def cmd_group_start(self, args):
        """Start new group: group start YYYY-MM-DD:HH:MM "description" """
        if len(args) < 2:
            print("[ERROR] Usage: group start <timestamp> <description>")
            return
        
        timestamp_str = args[0]
        description = ' '.join(args[1:]).strip('"')
        
        # Validate timestamp
        if not self.parse_timestamp(timestamp_str):
            return
        
        # Check if there's an open group
        open_group = self.analyzer.data_manager.get_open_group()
        if open_group:
            print(f"[ERROR] Group '{open_group['description']}' is still open. Use 'group end' first.")
            return
        
        self.analyzer.data_manager.start_group(timestamp_str, description)
        print(f"[OK] New group started: {description}")
    
    def cmd_group_end(self, args):
        """End current group: group end YYYY-MM-DD:HH:MM"""
        if len(args) != 1:
            print("[ERROR] Usage: group end <timestamp>")
            return
        
        timestamp_str = args[0]
        
        # Validate timestamp
        if not self.parse_timestamp(timestamp_str):
            return
        
        group = self.analyzer.data_manager.end_group(timestamp_str)
        if group:
            print(f"[OK] Group '{group['description']}' closed at {timestamp_str}")
        else:
            print("[ERROR] No open group to close")
    
    def cmd_bypass(self, args):
        """Bypass spike: bypass YYYY-MM-DD:HH:MM "reason" """
        if len(args) < 2:
            print("[ERROR] Usage: bypass <timestamp> <reason>")
            return
        
        timestamp_str = args[0]
        reason = ' '.join(args[1:]).strip('"')
        
        # Validate timestamp
        if not self.parse_timestamp(timestamp_str):
            return
        
        self.analyzer.data_manager.add_bypass(timestamp_str, reason)
        print(f"[OK] Spike at {timestamp_str} bypassed: {reason}")
    
    def cmd_analyze(self, args):
        """Run analysis: analyze [--auto]"""
        # Check for --auto flag
        auto_mode = '--auto' in args
        
        if auto_mode:
            print("[INFO] Running AUTO spike detection (legacy mode)...")
        else:
            print("[INFO] Using manual spikes from spikes_manual.json...")
        
        success = self.analyzer.run_analysis(auto=auto_mode)
        
        if not success and not auto_mode:
            print("\n[TIP] Define spikes with: addspike YYYY-MM-DD")
            print("[TIP] Or use auto-detection: analyze --auto")
    
    def cmd_chart_spike(self, args):
        """Chart a spike: chart spike <n> [--normalize]"""
        if len(args) < 1:
            print("[ERROR] Usage: chart spike <n> [--normalize]")
            return
        
        try:
            user_spike_num = int(args[0])  # User enters 1-based
        except ValueError:
            print("[ERROR] Spike number must be a number")
            return
        
        # Convert to 0-based index for internal use
        spike_index = user_spike_num - 1
        
        if spike_index < 0:
            print("[ERROR] Spike number must be >= 1")
            return
        
        # Check for normalize flag
        normalize = '--normalize' in args
        
        self.analyzer.generate_chart('spike', spike_index, normalize)    

    def cmd_chart_group(self, args):
        """Chart a group: chart group <n> [--normalize]"""
        if len(args) < 1:
            print("[ERROR] Usage: chart group <n> [--normalize]")
            return
        
        try:
            group_index = int(args[0])
        except ValueError:
            print("[ERROR] Group index must be a number")
            return
        
        # Check for normalize flag
        normalize = '--normalize' in args
        
        self.analyzer.generate_chart('group', group_index, normalize)
    
    def cmd_chart_compare(self, args):
        """Chart comparison: chart compare <n1> <n2> [--normalize]"""
        if len(args) < 2:
            print("[ERROR] Usage: chart compare <n1> <n2> [--normalize]")
            return
        
        try:
            group1_index = int(args[0])
            group2_index = int(args[1])
        except ValueError:
            print("[ERROR] Group indices must be numbers")
            return
        
        # Check for normalize flag
        normalize = '--normalize' in args
        
        self.analyzer.generate_chart('compare', group1_index, group2_index, normalize)
    
    def cmd_chart_scatter(self, args):
        """Chart scatter plot: chart scatter <n>"""
        if len(args) < 1:
            print("[ERROR] Usage: chart scatter <n>")
            return
        
        try:
            group_index = int(args[0])
        except ValueError:
            print("[ERROR] Group index must be a number")
            return
        
        self.analyzer.generate_chart('scatter', group_index)
    
    def cmd_list_meals(self, args):
        """List meals: list meals [start] [end]"""
        start = args[0] if len(args) > 0 else None
        end = args[1] if len(args) > 1 else None
        
        meals = self.analyzer.data_manager.get_meals(start, end)
        if not meals:
            print("No meals found")
            return
        
        print(f"\nMeals ({len(meals)} total):")
        print("-" * 50)
        for meal in meals:
            print(f"  {meal['timestamp']}  GL={meal['gl']}")
    
    def cmd_list_groups(self, args):
        """List all groups"""
        groups = self.analyzer.data_manager.data["groups"]
        if not groups:
            print("No groups defined")
            return
        
        print(f"\nAnalysis Groups ({len(groups)} total):")
        print("-" * 70)
        for i, group in enumerate(groups):
            end_str = group['end'] if group['end'] else "OPEN"
            print(f"  {i}: {group['start']} to {end_str}")
            print(f"     {group['description']}")
    
    def cmd_list_spikes(self, args):
        """List manually defined spikes"""
        json_path = Path(self.analyzer.config.get('data_files', 'spikes_manual_json'))
        
        if not json_path.exists():
            print("[INFO] No manual spikes defined yet.")
            print("[TIP] Use 'addspike YYYY-MM-DD' to add spikes interactively.")
            return
        
        try:
            with open(json_path, 'r') as f:
                spikes = json.load(f)
            
            if not spikes:
                print("[INFO] No manual spikes defined yet.")
                return
            
            # Parse date range if provided
            start_filter = None
            end_filter = None
            if len(args) >= 1:
                try:
                    start_filter = datetime.strptime(args[0], '%Y-%m-%d')
                except ValueError:
                    print("[ERROR] Invalid start date format. Use YYYY-MM-DD")
                    return
            if len(args) >= 2:
                try:
                    end_filter = datetime.strptime(args[1], '%Y-%m-%d')
                except ValueError:
                    print("[ERROR] Invalid end date format. Use YYYY-MM-DD")
                    return
            
            # Filter spikes by date range
            filtered_spikes = []
            for spike in spikes:
                start_time = datetime.fromisoformat(spike['start'])
                if start_filter and start_time < start_filter:
                    continue
                if end_filter and start_time > end_filter:
                    continue
                filtered_spikes.append(spike)
            
            if not filtered_spikes:
                print("[INFO] No spikes found in specified date range.")
                return
            
            print(f"\nManually Defined Spikes ({len(filtered_spikes)} total):")
            print("=" * 80)
            
            for i, spike in enumerate(filtered_spikes, 1):
                start = datetime.fromisoformat(spike['start'])
                end = datetime.fromisoformat(spike['end'])
                duration = (end - start).total_seconds() / 60
                
                print(f"\nSpike {i}: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%H:%M')}")
                print(f"  Duration: {duration:.0f} minutes")
        
        except Exception as e:
            print(f"[ERROR] Failed to load manual spikes: {e}")
    
    def cmd_list_matches(self, args):
        """List meal-spike matches: list matches [start] [end]"""
        if not self.analyzer.match_results:
            print("No matches yet. Run 'analyze' first.")
            return
        
        start_filter = args[0] if len(args) > 0 else None
        end_filter = args[1] if len(args) > 1 else None
        
        matches = self.analyzer.match_results['matched']
        
        # Filter by date range if provided
        if start_filter or end_filter:
            matches = self.analyzer.meal_matcher.filter_matches_by_date(
                matches, start_filter, end_filter
            )
        
        if not matches:
            print("No matched events found")
            return
        
        print(f"\nMeal-Spike Matches ({len(matches)} total):")
        print("=" * 80)
        for i, match in enumerate(matches):
            print(f"\nMatch {i+1}:")
            print(f"  Meal:  {match.meal['timestamp']} (GL={match.meal['gl']})")
            print(f"  Spike: {match.spike.start_time.strftime('%Y-%m-%d %H:%M')} "
                  f"(+{match.delay_minutes:.0f} min delay)")
            print(f"  Peak:  {match.spike.peak_time.strftime('%H:%M')} at {match.spike.peak_glucose:.0f} mg/dL "
                  f"(+{match.spike.magnitude:.0f} mg/dL)")
            print(f"  Peak:  {match.spike.peak_time.strftime('%H:%M')} at {match.spike.peak_glucose:.0f} mg/dL "
                  f"(+{match.spike.magnitude:.0f} mg/dL)")
            print(f"  AUC-relative: {match.spike.auc_relative:.0f} mg/dL*min, Normalized: {match.spike.normalized_auc:.3f}")
            if match.spike.recovery_time:
                print(f"  Recovery: {match.spike.recovery_time:.0f} minutes")
            print(f"  End:   {match.spike.end_time.strftime('%H:%M')} at {match.spike.end_glucose:.0f} mg/dL")
            print(f"  End:   {match.spike.end_time.strftime('%H:%M')} at {match.spike.end_glucose:.0f} mg/dL")
            print(f"  Duration: {match.spike.duration_minutes:.0f} minutes")
            if match.is_complex:
                print(f"  [COMPLEX] {len(match.nearby_meals)} nearby meal(s):")
                for nearby in match.nearby_meals:
                    print(f"    - {nearby['timestamp']} (GL={nearby['gl']}, "
                          f"{nearby['minutes_apart']:.0f} min apart)")
    
    def cmd_list_unmatched(self, args):
        """List unmatched spikes and meals"""
        if not self.analyzer.match_results:
            print("No analysis results yet. Run 'analyze' first.")
            return
        
        unmatched_spikes = self.analyzer.match_results['unmatched_spikes']
        unmatched_meals = self.analyzer.match_results['unmatched_meals']
        
        if unmatched_spikes:
            print(f"\nUnmatched Spikes ({len(unmatched_spikes)} total):")
            print("=" * 80)
            print("These spikes have no associated meal - possible unexplained events")
            print()
            for i, spike in enumerate(unmatched_spikes):
                print(f"{i+1}. {spike.start_time.strftime('%Y-%m-%d %H:%M')} - "
                      f"Peak: {spike.peak_glucose:.0f} mg/dL (+{spike.magnitude:.0f} mg/dL), "
                      f"Duration: {spike.duration_minutes:.0f} min")
        else:
            print("\n[OK] No unmatched spikes - all spikes have associated meals")
        
        if unmatched_meals:
            print(f"\nUnmatched Meals ({len(unmatched_meals)} total):")
            print("=" * 80)
            print("These meals did not trigger detectable spikes")
            print()
            for i, meal in enumerate(unmatched_meals):
                print(f"{i+1}. {meal['timestamp']} - GL={meal['gl']}")
        else:
            print("\n[OK] No unmatched meals - all meals have associated spikes")
    
    def cmd_stats(self, args):
        """Show CGM data statistics"""
        if self.analyzer.cgm_data is None:
            print("[ERROR] No CGM data loaded")
            csv_path = self.analyzer.config.get('data_files', 'libreview_csv')
            print(f"[INFO] Place LibreView CSV at: {csv_path}")
            return
        
        stats = self.analyzer.cgm_parser.get_stats()
        
        print("\nCGM Data Statistics:")
        print("=" * 60)
        print(f"Date range: {stats['start_date']} to {stats['end_date']}")
        print(f"Duration: {stats['days_of_data']} days")
        print(f"\nRecord counts:")
        print(f"  Total records: {stats['total_records']}")
        print(f"  Type 0 (automatic): {stats['type_0_count']}")
        print(f"  Type 1 (scan): {stats['type_1_count']}")
        print(f"  Type 6 (events): {stats['type_6_count']}")
        print(f"\nGlucose statistics:")
        print(f"  Mean: {stats['mean_glucose']:.1f} mg/dL")
        print(f"  Min: {stats['min_glucose']:.0f} mg/dL")
        print(f"  Max: {stats['max_glucose']:.0f} mg/dL")
        print(f"  Range: {stats['max_glucose'] - stats['min_glucose']:.0f} mg/dL")
    
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


    def cmd_help(self, args):
        """Show help"""
        print("""
  addmeal <timestamp> <gl>           Add meal entry
  addspike <yyyy-mm-dd>              Add spike interactively (click start/end on chart)
  group start <timestamp> <desc>     Start new analysis group
  group end <timestamp>              Close current group
  bypass <timestamp> <reason>        Mark spike as bypassed
  analyze                            Analyze using manual spikes (default)
  analyze --auto                     Analyze using auto spike detection (legacy)
  analyze group <n>                  Analyze single group
  analyze group <n> --gl-range X-Y   Analyze group with GL filter
  compare groups <n1> <n2>           Compare two groups
  compare groups <n1> <n2> --gl-range X-Y   Compare with GL filter
  list meals [start] [end]           List meals in date range
  list groups                        Show all groups
  list spikes [start] [end]          List manually defined spikes
  list matches [start] [end]         List meal-spike matches
  list unmatched                     Show unmatched spikes and meals
  list profiles [start] [end]        List normalized spike profiles
  compare "group1" "group2"          Compare normalized profiles between groups
  similar <spike_idx> [threshold]    Find spikes with similar shapes (threshold: 0.0-1.0)
  stats                              Show CGM data statistics
  chart spike <n> [--normalize]      Chart individual spike
  chart group <n> [--normalize]      Chart group overlay
  chart compare <n1> <n2> [--normalize]  Chart group comparison
  chart scatter <n>                  Chart GL vs AUC scatter
  help                               Show this help
  quit                               Exit program

Timestamp format: YYYY-MM-DD:HH:MM (24-hour)
Examples:
  addspike 2025-11-05
  addmeal 2025-11-14:18:00 33
  analyze
  analyze --auto
  list spikes
  chart spike 1              
Examples:
  addmeal 2025-11-14:18:00 33
  compare "baseline" "after medication"
  similar 3 0.8
Examples:
  addmeal 2025-11-14:18:00 33
  analyze group 0                    
  compare groups 0 1 --gl-range 25-35  
  chart spike 0
  chart group 0 --normalize
  chart compare 0 1
  chart scatter 0
        """)
    
    def cmd_quit(self, args):
        """Exit program"""
        self.running = False
        print("Goodbye!")
    
    def process_command(self, line):
        """
        Parse and execute command
        
        Args:
            line: Command line string
        """
        parts = line.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Handle multi-word commands
        if cmd == "group" and len(args) > 0:
            subcommand = args[0].lower()
            if subcommand == "start":
                self.cmd_group_start(args[1:])
            elif subcommand == "end":
                self.cmd_group_end(args[1:])
            else:
                print("[ERROR] Unknown group command. Use 'group start' or 'group end'")
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
        elif cmd == "addmeal":
            self.cmd_addmeal(args)
        elif cmd == "addspike":
            self.cmd_addspike_interactive(args)
        elif cmd == "bypass":
            self.cmd_bypass(args)
        elif cmd == "analyze":
            self.cmd_analyze(args)
        elif cmd == "chart" and len(args) > 0:
            subcommand = args[0].lower()
            if subcommand == "spike":
                self.cmd_chart_spike(args[1:])
            elif subcommand == "group":
                self.cmd_chart_group(args[1:])
            elif subcommand == "compare":
                self.cmd_chart_compare(args[1:])
            elif subcommand == "scatter":
                self.cmd_chart_scatter(args[1:])
            else:
                print("[ERROR] Unknown chart command. Use 'chart spike', 'chart group', 'chart compare', or 'chart scatter'")
        elif cmd == "stats":
            self.cmd_stats(args)
        elif cmd == "help":
            self.cmd_help(args)
        elif cmd == "quit" or cmd == "exit" or cmd == "q":
            self.cmd_quit(args)
        elif cmd == "compare":
            self.cmd_compare_groups(args)
        elif cmd == "similar":
            self.cmd_find_similar(args)
        elif cmd == "analyze":
            if len(args) > 0 and args[0].lower() == "group":
                self.cmd_analyze_group(args[1:])  # NEW
            else:
                self.cmd_analyze(args)
        elif cmd == "compare" and len(args) > 0 and args[0].lower() == "groups":
            self.cmd_compare_groups(args[1:])  # NEW
        else:
            print(f"[ERROR] Unknown command: {cmd}. Type 'help' for commands.")

    def cmd_analyze_group(self, args):
        """Analyze a group: analyze group <n> [--gl-range min-max]"""
        if len(args) < 1:
            print("[ERROR] Usage: analyze group <n> [--gl-range min-max]")
            return
        
        try:
            group_index = int(args[0])
        except ValueError:
            print("[ERROR] Group index must be a number")
            return
        
        # Check for GL range filter
        gl_range = None
        if len(args) >= 3 and args[1] == '--gl-range':
            try:
                parts = args[2].split('-')
                if len(parts) != 2:
                    print("[ERROR] GL range format: min-max (e.g., 25-35)")
                    return
                min_gl = float(parts[0])
                max_gl = float(parts[1])
                gl_range = (min_gl, max_gl)
            except ValueError:
                print("[ERROR] Invalid GL range values")
                return
        
        # Analyze the group
        analysis = self.analyzer.analyze_group(group_index, gl_range)
        
        if analysis:
            output = self.analyzer.group_analyzer.format_group_analysis(analysis)
            print(output)

    def cmd_compare_groups(self, args):
        """Compare groups: compare groups <n1> <n2> [--gl-range min-max]"""
        if len(args) < 2:
            print("[ERROR] Usage: compare groups <n1> <n2> [--gl-range min-max]")
            return
        
        try:
            group1_index = int(args[0])
            group2_index = int(args[1])
        except ValueError:
            print("[ERROR] Group indices must be numbers")
            return
        
        # Check for GL range filter
        gl_range = None
        if len(args) >= 4 and args[2] == '--gl-range':
            try:
                parts = args[3].split('-')
                if len(parts) != 2:
                    print("[ERROR] GL range format: min-max (e.g., 25-35)")
                    return
                min_gl = float(parts[0])
                max_gl = float(parts[1])
                gl_range = (min_gl, max_gl)
            except ValueError:
                print("[ERROR] Invalid GL range values")
                return
        
        # Compare the groups
        comparison = self.analyzer.compare_groups(group1_index, group2_index, gl_range)
        
        if comparison:
            output = self.analyzer.group_analyzer.format_comparison(comparison)
            print(output)
            
            if gl_range:
                print(f"\nNote: Comparison limited to meals with GL {gl_range[0]}-{gl_range[1]}")

    def cmd_addspike_interactive(self, args):
        """Add spike interactively: addspike YYYY-MM-DD"""
        if len(args) < 1:
            print("[ERROR] Usage: addspike YYYY-MM-DD")
            return
        
        date_str = args[0]
        
        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print("[ERROR] Invalid date format. Use YYYY-MM-DD")
            return
        
        csv_path = Path(self.analyzer.config.get('data_files', 'libreview_csv'))
        json_path = Path(self.analyzer.config.get('data_files', 'spikes_manual_json'))
        
        if not csv_path.exists():
            print(f"[ERROR] CGM data file not found: {csv_path}")
            return
        
        try:
            add_spike_interactive(date_str, csv_path, json_path)
        except Exception as e:
            print(f"[ERROR] Failed to add spike: {e}")

    def run(self):
        """Main CLI loop"""
        print("Glucose Spike Analyzer v1.0")
        
        # Load stats
        meals_count = len(self.analyzer.data_manager.data["meals"])
        groups_count = len(self.analyzer.data_manager.data["groups"])
        bypassed_count = len(self.analyzer.data_manager.data["bypassed_spikes"])
        
        print(f"Loaded {meals_count} meals, {groups_count} groups, {bypassed_count} bypassed spikes")
        
        # Show CGM data status
        if self.analyzer.cgm_data is not None:
            cgm_count = len(self.analyzer.cgm_data)
            print(f"CGM data: {cgm_count} readings loaded")
        else:
            csv_path = self.analyzer.config.get('data_files', 'libreview_csv')
            print(f"[WARNING] No CGM data loaded. Place LibreView CSV at: {csv_path}")
        
        print("Type 'help' for commands\n")
        
        while self.running:
            try:
                line = input("> ")
                self.process_command(line)
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                break


def main():
    """Application entry point"""
    analyzer = GlucoseAnalyzer()
    cli = CLI(analyzer)
    cli.run()


if __name__ == "__main__":
    main()
