"""
Timeline Visualization Module
Generates 24-hour glucose charts with meals and spikes
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os


class TimelineVisualizer:
    """Creates 24-hour timeline visualizations of glucose, meals, and spikes"""
    
    def __init__(self, config):
        """
        Initialize visualizer with configuration
        
        Args:
            config: Config object
        """
        self.config = config
        self.output_dir = config.get('output', 'charts_dir')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def plot_day_timeline(self, date, cgm_data, meals, matches, unmatched_spikes):
        """
        Create a 24-hour timeline chart for a specific date
        
        Args:
            date: Date string (YYYY-MM-DD) or datetime object
            cgm_data: List of dicts with 'timestamp' and 'glucose' (full dataset)
            meals: List of all meal dicts with 'timestamp' and 'gl'
            matches: List of MealSpikeMatch objects
            unmatched_spikes: List of SpikeEvent objects without meals
            
        Returns:
            str: Path to saved chart file
        """
        # Convert date to datetime if string
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        # Define the 24-hour window
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Filter DataFrame by date range
        day_cgm = cgm_data[
            cgm_data['timestamp'].dt.date == day_start.date()
        ]
        
        if day_cgm.empty:
            print(f"No CGM data found for {date.strftime('%Y-%m-%d')}")
            return None
        
        # Filter meals for this day
        day_meals = []
        for meal in meals:
            meal_dt = datetime.strptime(meal['timestamp'], "%Y-%m-%d:%H:%M")
            if day_start <= meal_dt < day_end:
                day_meals.append({**meal, 'datetime': meal_dt})
        
        # Filter matches for this day
        day_matches = []
        for match in matches:
            # Handle both object and dict format
            if isinstance(match, dict):
                spike_time = datetime.strptime(match['spike']['start_time'], '%Y-%m-%d %H:%M:%S')
            else:
                spike_time = match.spike.start_time
            
            if day_start <= spike_time < day_end:
                day_matches.append(match)
        
        # Filter unmatched spikes for this day
        day_unmatched = [
            s for s in unmatched_spikes
            if day_start <= s.start_time < day_end
        ]
        
        # Create the plot
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Extract CGM times and glucose values
        times = day_cgm['timestamp'].tolist()
        glucose = day_cgm['glucose'].tolist()
        
        # Plot glucose trace
        ax.plot(times, glucose, 'b-', linewidth=2, label='Glucose', zorder=1)
        
        # Add meal markers
        if day_meals:
            meal_times = [m['datetime'] for m in day_meals]
            meal_gls = [m['gl'] for m in day_meals]
            
            # Scale GL to fit nicely on chart (map to glucose range)
            glucose_range = max(glucose) - min(glucose)
            gl_max = max(meal_gls) if meal_gls else 1
            
            # Draw vertical lines for meals
            for meal_time, gl in zip(meal_times, meal_gls):
                # Line height proportional to GL
                line_height = min(glucose) + (gl / gl_max) * (glucose_range * 0.3)
                ax.plot([meal_time, meal_time], [min(glucose), line_height], 
                       'g--', linewidth=2, alpha=0.7, zorder=2)
                # Add GL label at top of line
                ax.text(meal_time, line_height + glucose_range * 0.02, 
                       f'GL={gl}', ha='center', va='bottom', fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7))
        
        # Shade spike regions
        for match in day_matches:
            spike = match.spike
            # Different colors for single vs multi-meal
            if match.meal_count == 1:
                color = 'lightblue'
                alpha = 0.3
                label_prefix = 'Single meal'
            else:
                color = 'lightblue'
                alpha = 0.3
                label_prefix = f'{match.meal_count} meals'
            
            ax.axvspan(spike.start_time, spike.end_time, 
                      color=color, alpha=alpha, zorder=0)
            
            # Add spike label
            mid_time = spike.start_time + (spike.end_time - spike.start_time) / 2
            label_y = spike.peak_glucose + glucose_range * 0.05
            ax.text(mid_time, label_y, f'{label_prefix}\nGL={match.total_gl}',
                   ha='center', va='bottom', fontsize=8,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # Shade unexplained spike regions
        for spike in day_unmatched:
            ax.axvspan(spike.start_time, spike.end_time, 
                      color='red', alpha=0.2, zorder=0)
            
            # Add label
            mid_time = spike.start_time + (spike.end_time - spike.start_time) / 2
            label_y = spike.peak_glucose + glucose_range * 0.05
            ax.text(mid_time, label_y, 'Unexplained',
                   ha='center', va='bottom', fontsize=8,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7))
        
        # Formatting
        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Glucose (mg/dL)', fontsize=12, fontweight='bold')
        ax.set_title(f'24-Hour Glucose Timeline - {date.strftime("%Y-%m-%d")}', 
                    fontsize=14, fontweight='bold', loc='left')
        
        # Format x-axis to show hours
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.xticks(rotation=45)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add legend for spike types
        from matplotlib.patches import Patch
        legend_elements = [
            plt.Line2D([0], [0], color='b', linewidth=2, label='Glucose'),
            plt.Line2D([0], [0], color='g', linestyle='--', linewidth=2, label='Meal (GL)'),
            Patch(facecolor='lightblue', alpha=0.3, label='Spike'),
            Patch(facecolor='red', alpha=0.3, label='Unexplained spike')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        # Tight layout
        plt.tight_layout()
        
        # Save figure
        filename = f"timeline_{date.strftime('%Y-%m-%d')}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def plot_date_range(self, start_date, end_date, cgm_data, meals, matches, unmatched_spikes):
        """
        Create timeline charts for each day in a date range
        
        Args:
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            cgm_data: Full CGM dataset
            meals: All meals
            matches: All matches
            unmatched_spikes: All unmatched spikes
            
        Returns:
            list: Paths to all generated chart files
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        chart_files = []
        current = start
        
        while current <= end:
            filepath = self.plot_day_timeline(
                current, cgm_data, meals, matches, unmatched_spikes
            )
            if filepath:
                chart_files.append(filepath)
            current += timedelta(days=1)
        
        return chart_files
    
    def plot_multi_day_overview(self, start_date, end_date, cgm_data, meals, matches):
        """
        Create a multi-day overview chart (condensed view)
        Shows glucose trace with meal markers over multiple days
        
        Args:
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            cgm_data: Full CGM dataset
            meals: All meals
            matches: All matches
            
        Returns:
            str: Path to saved chart file
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        # Filter data for date range
        range_cgm = cgm_data[(cgm_data['timestamp'].dt.date >= start.date()) & 
                    (cgm_data['timestamp'].dt.date < end.date())]
        
        if range_cgm.empty:
            print(f"No CGM data found for range {start_date} to {end_date}")
            return None
        
        # Filter meals
        range_meals = []
        for meal in meals:
            meal_dt = datetime.strptime(meal['timestamp'], "%Y-%m-%d:%H:%M")
            if start <= meal_dt < end:
                range_meals.append({**meal, 'datetime': meal_dt})
        
        # Create plot
        fig, ax = plt.subplots(figsize=(20, 6))
        
        # Plot glucose
        times = range_cgm['timestamp'].tolist()
        glucose = range_cgm['glucose'].tolist()
        ax.plot(times, glucose, 'b-', linewidth=1, label='Glucose')
        
        # Add meal markers (simpler for multi-day)
        if range_meals:
            meal_times = [m['datetime'] for m in range_meals]
            meal_glucose = [min(glucose)] * len(meal_times)  # Place at bottom
            ax.scatter(meal_times, meal_glucose, color='green', marker='^', 
                      s=100, label='Meals', zorder=3, alpha=0.6)
        
        # Formatting
        ax.set_xlabel('Date/Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Glucose (mg/dL)', fontsize=12, fontweight='bold')
        ax.set_title(f'Multi-Day Glucose Overview - {start_date} to {end_date}', 
                    fontsize=14, fontweight='bold', loc='left')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        plt.xticks(rotation=45)
        
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        # Save
        filename = f"overview_{start_date}_to_{end_date}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath