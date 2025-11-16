"""Command-line interface for Glucose Analyzer"""

from datetime import datetime

from glucose_analyzer.analyzer import GlucoseAnalyzer


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
        """Run analysis"""
        self.analyzer.run_analysis()
    
    def cmd_chart(self, args):
        """Generate chart: chart group <n> OR chart meal <timestamp>"""
        if len(args) < 2:
            print("[ERROR] Usage: chart group <n> OR chart meal <timestamp>")
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
  stats                              Show CGM data statistics
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
        elif cmd == "stats":
            self.cmd_stats(args)
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
