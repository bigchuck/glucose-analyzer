#!/usr/bin/env python3
"""
Glucose Spike Analyzer
Analyzes FreeStyle Libre 3 CGM data from LibreView CSV exports
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path


class Config:
    """Application configuration manager"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.data = json.load(f)
    
    def get(self, *keys):
        """Get nested config value"""
        value = self.data
        for key in keys:
            value = value[key]
        return value


class DataManager:
    """Manages meals.json persistence"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self):
        """Load data from JSON file"""
        if not os.path.exists(self.filepath):
            return {"meals": [], "groups": [], "bypassed_spikes": []}
        
        with open(self.filepath, 'r') as f:
            return json.load(f)
    
    def save(self):
        """Save data to JSON file"""
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def add_meal(self, timestamp, gl):
        """Add a meal entry"""
        meal = {
            "timestamp": timestamp,
            "gl": gl
        }
        self.data["meals"].append(meal)
        self.save()
        return meal
    
    def start_group(self, start_time, description):
        """Start a new analysis group"""
        group = {
            "start": start_time,
            "end": None,
            "description": description
        }
        self.data["groups"].append(group)
        self.save()
        return group
    
    def end_group(self, end_time):
        """End the current open group"""
        for group in reversed(self.data["groups"]):
            if group["end"] is None:
                group["end"] = end_time
                self.save()
                return group
        return None
    
    def add_bypass(self, timestamp, reason):
        """Mark a spike as bypassed"""
        bypass = {
            "timestamp": timestamp,
            "reason": reason
        }
        self.data["bypassed_spikes"].append(bypass)
        self.save()
        return bypass
    
    def get_meals(self, start=None, end=None):
        """Get meals in date range"""
        meals = self.data["meals"]
        if start:
            meals = [m for m in meals if m["timestamp"] >= start]
        if end:
            meals = [m for m in meals if m["timestamp"] <= end]
        return sorted(meals, key=lambda m: m["timestamp"])
    
    def get_open_group(self):
        """Get currently open group, if any"""
        for group in reversed(self.data["groups"]):
            if group["end"] is None:
                return group
        return None


class GlucoseAnalyzer:
    """Main analyzer application"""
    
    def __init__(self):
        self.config = Config()
        self.data_manager = DataManager(self.config.get('data_files', 'meals_json'))
        self.cgm_data = None
        
        # Create charts directory if it doesn't exist
        charts_dir = self.config.get('output', 'charts_directory')
        Path(charts_dir).mkdir(exist_ok=True)
    
    def load_cgm_data(self):
        """Load LibreView CSV data"""
        # TODO: Implement CSV parsing
        csv_path = self.config.get('data_files', 'libreview_csv')
        print(f"[INFO] Loading CGM data from {csv_path}...")
        # Placeholder for now
        pass
    
    def run_analysis(self):
        """Run full spike analysis"""
        print("Analyzing glucose data...")
        # TODO: Implement analysis
        print("[INFO] Analysis not yet implemented")
    
    def generate_chart(self, chart_type, *args):
        """Generate visualization chart"""
        print(f"Generating {chart_type} chart...")
        # TODO: Implement charting
        print("[INFO] Charting not yet implemented")


class CLI:
    """Command-line interface shell"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.running = True
    
    def parse_timestamp(self, ts_str):
        """Parse timestamp string to datetime"""
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
        """Run analysis"""
        self.analyzer.run_analysis()
    
    def cmd_chart(self, args):
        """Generate chart: chart group <name> OR chart meal <timestamp>"""
        if len(args) < 2:
            print("[ERROR] Usage: chart group <name> OR chart meal <timestamp>")
            return
        
        chart_type = args[0]
        self.analyzer.generate_chart(chart_type, *args[1:])
    
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
    
    def cmd_help(self, args):
        """Show help"""
        print("""
Commands:
  addmeal <timestamp> <gl>           Add meal entry
  group start <timestamp> <desc>     Start new analysis group
  group end <timestamp>              Close current group
  bypass <timestamp> <reason>        Mark spike as bypassed
  analyze                            Run full analysis
  chart group <name>                 Generate group charts
  chart meal <timestamp>             Generate single meal chart
  list meals [start] [end]           List meals in date range
  list groups                        Show all groups
  help                               Show this help
  quit                               Exit program

Timestamp format: YYYY-MM-DD:HH:MM (24-hour)
Example: addmeal 2025-11-14:18:00 33
        """)
    
    def cmd_quit(self, args):
        """Exit program"""
        self.running = False
        print("Goodbye!")
    
    def process_command(self, line):
        """Parse and execute command"""
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
            else:
                print("[ERROR] Unknown list command. Use 'list meals' or 'list groups'")
        elif cmd == "addmeal":
            self.cmd_addmeal(args)
        elif cmd == "bypass":
            self.cmd_bypass(args)
        elif cmd == "analyze":
            self.cmd_analyze(args)
        elif cmd == "chart":
            self.cmd_chart(args)
        elif cmd == "help":
            self.cmd_help(args)
        elif cmd == "quit" or cmd == "exit":
            self.cmd_quit(args)
        else:
            print(f"[ERROR] Unknown command: {cmd}. Type 'help' for commands.")
    
    def run(self):
        """Main CLI loop"""
        print("Glucose Spike Analyzer v1.0")
        
        # Load stats
        meals_count = len(self.analyzer.data_manager.data["meals"])
        groups_count = len(self.analyzer.data_manager.data["groups"])
        bypassed_count = len(self.analyzer.data_manager.data["bypassed_spikes"])
        
        print(f"Loaded {meals_count} meals, {groups_count} groups, {bypassed_count} bypassed spikes")
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
