"""Manual spike definition using interactive matplotlib charts"""

import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np


class SpikeEditor:
    """Interactive spike definition using matplotlib click events"""
    
    def __init__(self, date_str: str, csv_path: Path, json_path: Path):
        self.date_str = date_str
        self.csv_path = csv_path
        self.json_path = json_path
        
        # State management
        self.state = 'waiting_for_start'
        self.temp_start = None
        self.temp_start_line = None
        self.existing_spikes = []
        self.new_spikes = []
        
        # Data
        self.timestamps = []
        self.glucose_values = []
        
        # Load existing spikes
        self._load_spikes()
        
    def _load_spikes(self):
        """Load existing spikes from JSON, filter to this day"""
        if self.json_path.exists():
            with open(self.json_path, 'r') as f:
                all_spikes = json.load(f)
                target_date = datetime.strptime(self.date_str, '%Y-%m-%d').date()
                for spike in all_spikes:
                    start_dt = datetime.fromisoformat(spike['start'])
                    if start_dt.date() == target_date:
                        self.existing_spikes.append(spike)
    
    def _load_day_data(self):
        """Load glucose data for the specified day"""
        from glucose_analyzer.parsers.csv_parser import LibreViewParser        
        parser = LibreViewParser(str(self.csv_path))
        parser.parse()
        cgm_data = parser.get_auto_readings()
        
        target_date = datetime.strptime(self.date_str, '%Y-%m-%d').date()

        for _, row in cgm_data.iterrows():
            if row['timestamp'].date() == target_date and row['glucose'] is not None:
                self.timestamps.append(row['timestamp'])
                self.glucose_values.append(row['glucose'])
    
        if not self.timestamps:
            raise ValueError(f"No data found for {self.date_str}")

    def _snap_to_nearest(self, click_time: datetime) -> datetime:
        """Snap clicked time to nearest actual data point"""
        if not self.timestamps:
            return click_time
        
        deltas = [abs((ts - click_time).total_seconds()) for ts in self.timestamps]
        nearest_idx = np.argmin(deltas)
        return self.timestamps[nearest_idx]
    
    def _check_overlap(self, start: datetime, end: datetime) -> Optional[Dict]:
        """Check if new spike overlaps with any existing spike"""
        for spike in self.existing_spikes + self.new_spikes:
            spike_start = datetime.fromisoformat(spike['start'])
            spike_end = datetime.fromisoformat(spike['end'])
            
            # Check for any overlap or touching boundaries
            if start < spike_end and end > spike_start:
                return spike
        return None
    
    def _on_click(self, event):
        """Handle matplotlib click events"""
        if event.inaxes is None:
            return

        # Convert matplotlib date number to datetime
        from matplotlib.dates import num2date
        click_time = num2date(event.xdata).replace(tzinfo=None)  # Remove timezone info
        snapped_time = self._snap_to_nearest(click_time)

        if self.state == 'waiting_for_start':
            self.temp_start = snapped_time
            time_str = snapped_time.strftime('%H:%M')
            
            # Draw temporary start line
            if self.temp_start_line:
                self.temp_start_line.remove()
            self.temp_start_line = self.ax.axvline(
                snapped_time, color='orange', linestyle='--', linewidth=2, 
                label=f'Start: {time_str}'
            )
            self.ax.legend()
            self.ax.set_title(f'Click END time for spike starting at {time_str}')
            self.fig.canvas.draw()
            
            self.state = 'waiting_for_end'
        
        elif self.state == 'waiting_for_end':
            end_time = snapped_time
            
            if end_time <= self.temp_start:
                self.ax.set_title('ERROR: End must be after start. Click END time again.')
                self.fig.canvas.draw()
                return
            
            # Check for overlaps
            overlap = self._check_overlap(self.temp_start, end_time)
            if overlap:
                overlap_start = datetime.fromisoformat(overlap['start']).strftime('%H:%M')
                overlap_end = datetime.fromisoformat(overlap['end']).strftime('%H:%M')
                self.ax.set_title(
                    f'OVERLAP with spike [{overlap_start}-{overlap_end}]. '
                    f'Click START for new spike.'
                )
                if self.temp_start_line:
                    self.temp_start_line.remove()
                    self.temp_start_line = None
                self.fig.canvas.draw()
                self.state = 'waiting_for_start'
                return
            
            # Valid spike - add it
            new_spike = {
                'start': self.temp_start.isoformat(),
                'end': end_time.isoformat()
            }
            self.new_spikes.append(new_spike)
            
            # Draw shaded region
            start_str = self.temp_start.strftime('%H:%M')
            end_str = end_time.strftime('%H:%M')
            self.ax.axvspan(
                self.temp_start, end_time, alpha=0.3, color='green',
                label=f'New: {start_str}-{end_str}'
            )
            
            # Remove temporary start line
            if self.temp_start_line:
                self.temp_start_line.remove()
                self.temp_start_line = None
            
            self.ax.legend()
            self.ax.set_title(
                f'Spike added: {start_str} to {end_str}. '
                f'Close window OR click START for another spike'
            )
            self.fig.canvas.draw()
            
            # Reset for next spike
            self.temp_start = None
            self.state = 'waiting_for_start'
    
    def _draw_existing_spikes(self):
        """Draw existing spikes as shaded regions"""
        for spike in self.existing_spikes:
            start = datetime.fromisoformat(spike['start'])
            end = datetime.fromisoformat(spike['end'])
            start_str = start.strftime('%H:%M')
            end_str = end.strftime('%H:%M')
            self.ax.axvspan(
                start, end, alpha=0.2, color='blue',
                label=f'Existing: {start_str}-{end_str}'
            )
    
    def _save_spikes(self):
        """Save all spikes sorted by start time"""
        # Load all existing spikes from file
        all_spikes = []
        if self.json_path.exists():
            with open(self.json_path, 'r') as f:
                all_spikes = json.load(f)
        
        # Add new spikes
        all_spikes.extend(self.new_spikes)
        
        # Sort by start time
        all_spikes.sort(key=lambda s: s['start'])
        
        # Save
        with open(self.json_path, 'w') as f:
            json.dump(all_spikes, f, indent=2)
        
        return len(self.new_spikes)
    
    def run(self):
        """Start interactive spike editor"""
        self._load_day_data()
        
        # Create figure
        self.fig, self.ax = plt.subplots(figsize=(14, 6))
        
        # Plot glucose data
        self.ax.plot(self.timestamps, self.glucose_values, 'o-', 
                    linewidth=2, markersize=4)
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Glucose (mg/dL)')
        self.ax.set_title(f'Click START time for new spike - {self.date_str}')
        self.ax.grid(True, alpha=0.3)
        
        # Draw existing spikes
        self._draw_existing_spikes()
        
        if self.existing_spikes:
            self.ax.legend()
        
        # Connect click event
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        
        # Show plot
        plt.tight_layout()
        plt.show()
        
        # Save when window closes
        if self.new_spikes:
            count = self._save_spikes()
            print(f"\n{count} spike(s) saved for {self.date_str}")
        else:
            print(f"\nNo new spikes added for {self.date_str}")


def add_spike_interactive(date_str: str, csv_path: Path, json_path: Path):
    """Entry point for adding spikes interactively"""
    editor = SpikeEditor(date_str, csv_path, json_path)
    editor.run()