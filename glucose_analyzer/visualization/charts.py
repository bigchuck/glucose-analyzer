"""
Visualization Module
Generates charts for glucose spike analysis
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from datetime import datetime
import os


class ChartGenerator:
    """Generates charts for glucose analysis"""
    
    def __init__(self, config):
        """
        Initialize chart generator
        
        Args:
            config: Config object with output settings
        """
        self.config = config
        self.output_dir = Path(config.get('output', 'charts_directory'))
        self.dpi = config.get('output', 'chart_dpi')
        self.auto_open = config.get('output', 'auto_open_charts')
        
        # Create output directory if needed
        self.output_dir.mkdir(exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Color scheme (colorblind-safe)
        self.colors = {
            'group1': '#1f77b4',  # Blue
            'group2': '#ff7f0e',  # Orange
            'baseline': '#7f7f7f',  # Gray
            'auc_fill': '#1f77b4',  # Light blue
            'peak': '#d62728',  # Red
            'recovery': '#2ca02c'  # Green
        }
    
    def chart_spike(self, spike, spike_index, cgm_data, normalize=False):
        """
        Generate chart for a single spike
        
        Args:
            spike: Spike object
            spike_index: 0-based internal index
            cgm_data: DataFrame with CGM data
            normalize: If True, normalize glucose to 0-1 scale

        Returns:
            str: Path to saved chart file
        """
        # Extract spike window data
        spike_window = cgm_data[
            (cgm_data['timestamp'] >= spike.start_time) &
            (cgm_data['timestamp'] <= spike.end_time)
        ].copy()
        
        if len(spike_window) < 2:
            raise ValueError("Insufficient data for spike chart")
        
        # Calculate minutes from spike start
        spike_window['minutes'] = (
            (spike_window['timestamp'] - spike.start_time).dt.total_seconds() / 60
        )
        
        minutes = spike_window['minutes'].values
        glucose = spike_window['glucose'].values
        
        # Normalize if requested
        if normalize:
            glucose_plot = (glucose - spike.baseline) / (spike.peak_glucose - spike.baseline)
            ylabel = 'Normalized Glucose (0=baseline, 1=peak)'
            baseline_y = 0
            peak_y = 1
            title_suffix = ' (Normalized)'
        else:
            glucose_plot = glucose
            ylabel = 'Glucose (mg/dL)'
            baseline_y = spike.baseline
            peak_y = spike.peak_glucose
            title_suffix = ''
        
        # Display as 1-based for user
        user_spike_num = spike_index + 1

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6), dpi=self.dpi)
        
        # Plot glucose curve
        ax.plot(minutes, glucose_plot, 'o-', color=self.colors['group1'], 
                linewidth=2, markersize=4, label='Glucose')
        
        # Plot baseline
        ax.axhline(y=baseline_y, color=self.colors['baseline'], 
                   linestyle='--', linewidth=1, alpha=0.7, label='Baseline')
        
        # Fill AUC area (above baseline)
        if normalize:
            ax.fill_between(minutes, baseline_y, glucose_plot, 
                           where=(glucose_plot >= baseline_y),
                           alpha=0.3, color=self.colors['auc_fill'], 
                           label='AUC-relative')
        else:
            ax.fill_between(minutes, baseline_y, glucose_plot,
                           where=(glucose >= spike.baseline),
                           alpha=0.3, color=self.colors['auc_fill'],
                           label='AUC-relative')
        
        # Mark peak
        peak_minute = (spike.peak_time - spike.start_time).total_seconds() / 60
        ax.plot(peak_minute, peak_y, 'o', color=self.colors['peak'], 
                markersize=10, label='Peak', zorder=5)
        
        # Mark recovery if available
        if spike.recovery_time:
            if normalize:
                recovery_y = baseline_y
            else:
                recovery_y = spike.baseline
            ax.plot(spike.recovery_time, recovery_y, 'o', 
                   color=self.colors['recovery'], markersize=10, 
                   label='Recovery', zorder=5)
        
        # Formatting
        ax.set_xlabel('Minutes from Spike Start', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(f'Spike {user_spike_num}: {spike.start_time.strftime("%Y-%m-%d %H:%M")}{title_suffix}',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Add text box with metrics
        if normalize:
            textstr = '\n'.join([
                f'Magnitude: {spike.magnitude:.0f} mg/dL',
                f'Duration: {spike.duration_minutes:.0f} min',
                f'Time to peak: {spike.time_to_peak_minutes:.0f} min',
                f'Normalized AUC: {spike.normalized_auc:.3f}',
                f'Recovery: {spike.recovery_time:.0f} min' if spike.recovery_time else 'Recovery: N/A'
            ])
        else:
            textstr = '\n'.join([
                f'Baseline: {spike.baseline:.0f} mg/dL',
                f'Peak: {spike.peak_glucose:.0f} mg/dL',
                f'Magnitude: {spike.magnitude:.0f} mg/dL',
                f'Duration: {spike.duration_minutes:.0f} min',
                f'AUC-relative: {spike.auc_relative:.0f} mg/dL*min',
                f'Recovery: {spike.recovery_time:.0f} min' if spike.recovery_time else 'Recovery: N/A'
            ])
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Save figure
        timestamp_str = spike.start_time.strftime('%Y-%m-%d_%H%M')
        norm_suffix = '_normalized' if normalize else ''
        filename = f'spike_{user_spike_num}_{timestamp_str}{norm_suffix}.png'
        filepath = self.output_dir / filename
        
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        
        if self.auto_open:
            self._open_file(filepath)
        
        plt.close()
        
        return str(filepath)
    
    def chart_group(self, group_analysis, normalize=False):
        """
        Generate overlay chart for all spikes in a group
        
        Args:
            group_analysis: Dict from GroupAnalyzer.analyze_group()
            normalize: If True, normalize all spikes to 0-1 scale
            
        Returns:
            str: Path to saved chart file
        """
        if not group_analysis['stats']:
            raise ValueError("Group has no matched events to chart")
        
        matches = group_analysis['stats'].matches
        group_info = group_analysis['group_info']
        
        if len(matches) == 0:
            raise ValueError("No spikes in group to chart")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6), dpi=self.dpi)
        
        # Collect all spike curves
        all_curves = []
        max_duration = 0
        
        for match in matches:
            spike = match.spike
            
            # Get spike window from match
            duration = spike.duration_minutes
            num_points = int(duration / 5) + 1  # Approximate 5-min intervals
            minutes = np.linspace(0, duration, num_points)
            
            if normalize:
                # Normalize to 0-1 scale
                glucose = np.linspace(0, 1, num_points)  # Simplified for demo
                # In reality, we'd need the actual glucose data points
                baseline = 0
                peak = 1
            else:
                # Use actual glucose values
                # For this we'd need access to CGM data - simplified here
                baseline = spike.baseline
                peak = spike.peak_glucose
            
            all_curves.append({
                'minutes': minutes,
                'duration': duration,
                'baseline': baseline,
                'peak': peak
            })
            
            max_duration = max(max_duration, duration)
        
        # Plot all individual spikes (thin, transparent)
        for i, match in enumerate(matches):
            spike = match.spike
            duration = spike.duration_minutes
            
            # Create interpolated curve (simplified)
            minutes = np.linspace(0, duration, 50)
            
            if normalize:
                # Normalized curve: 0 to 1 and back
                peak_idx = int(len(minutes) * (spike.time_to_peak_minutes / duration))
                glucose = np.concatenate([
                    np.linspace(0, 1, peak_idx),
                    np.linspace(1, 0, len(minutes) - peak_idx)
                ])
            else:
                # Actual glucose curve (simplified approximation)
                peak_idx = int(len(minutes) * (spike.time_to_peak_minutes / duration))
                glucose = np.concatenate([
                    np.linspace(spike.baseline, spike.peak_glucose, peak_idx),
                    np.linspace(spike.peak_glucose, spike.end_glucose, len(minutes) - peak_idx)
                ])
            
            ax.plot(minutes, glucose, color=self.colors['group1'], 
                   alpha=0.2, linewidth=1)
        
        # Calculate and plot mean curve
        # Simplified: just show the range
        if normalize:
            ax.axhline(y=0, color=self.colors['baseline'], linestyle='--', 
                      linewidth=1, alpha=0.7, label='Baseline (normalized)')
            ylabel = 'Normalized Glucose (0=baseline, 1=peak)'
            title_suffix = ' (Normalized)'
        else:
            avg_baseline = np.mean([m.spike.baseline for m in matches])
            ax.axhline(y=avg_baseline, color=self.colors['baseline'], 
                      linestyle='--', linewidth=1, alpha=0.7, label='Avg Baseline')
            ylabel = 'Glucose (mg/dL)'
            title_suffix = ''
        
        # Formatting
        ax.set_xlabel('Minutes from Spike Start', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(f'Group: {group_info["description"]}{title_suffix}',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Add statistics text box
        stats = group_analysis['stats']
        if normalize:
            textstr = '\n'.join([
                f'Spikes: {len(matches)}',
                f'Avg magnitude: {stats.magnitude["mean"]:.0f} ± {stats.magnitude["std"]:.0f} mg/dL',
                f'Avg duration: {stats.duration["mean"]:.0f} ± {stats.duration["std"]:.0f} min',
                f'Avg normalized AUC: {stats.normalized_auc["mean"]:.3f} ± {stats.normalized_auc["std"]:.3f}'
            ])
        else:
            textstr = '\n'.join([
                f'Spikes: {len(matches)}',
                f'Avg AUC-relative: {stats.auc_relative["mean"]:.0f} ± {stats.auc_relative["std"]:.0f}',
                f'Avg magnitude: {stats.magnitude["mean"]:.0f} ± {stats.magnitude["std"]:.0f} mg/dL',
                f'Avg duration: {stats.duration["mean"]:.0f} ± {stats.duration["std"]:.0f} min'
            ])
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Save figure
        group_desc = group_info['description'].replace(' ', '-').lower()
        norm_suffix = '_normalized' if normalize else ''
        filename = f'group_{group_desc}_overlay{norm_suffix}.png'
        filepath = self.output_dir / filename
        
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        
        if self.auto_open:
            self._open_file(filepath)
        
        plt.close()
        
        return str(filepath)
    
    def chart_compare(self, comparison, group1_analysis, group2_analysis, normalize=False):
        """
        Generate comparison chart for two groups
        
        Args:
            comparison: GroupComparison object
            group1_analysis: Analysis dict for group 1
            group2_analysis: Analysis dict for group 2
            normalize: If True, show normalized spikes
            
        Returns:
            str: Path to saved chart file
        """
        if not comparison:
            raise ValueError("Invalid comparison object")
        
        group1_info = group1_analysis['group_info']
        group2_info = group2_analysis['group_info']
        
        matches1 = group1_analysis['stats'].matches
        matches2 = group2_analysis['stats'].matches
        
        if len(matches1) == 0 or len(matches2) == 0:
            raise ValueError("One or both groups have no spikes to chart")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6), dpi=self.dpi)
        
        # Plot Group 1 spikes
        for match in matches1:
            spike = match.spike
            duration = spike.duration_minutes
            minutes = np.linspace(0, duration, 50)
            
            if normalize:
                peak_idx = int(len(minutes) * (spike.time_to_peak_minutes / duration))
                glucose = np.concatenate([
                    np.linspace(0, 1, peak_idx),
                    np.linspace(1, 0, len(minutes) - peak_idx)
                ])
            else:
                peak_idx = int(len(minutes) * (spike.time_to_peak_minutes / duration))
                glucose = np.concatenate([
                    np.linspace(spike.baseline, spike.peak_glucose, peak_idx),
                    np.linspace(spike.peak_glucose, spike.end_glucose, len(minutes) - peak_idx)
                ])
            
            ax.plot(minutes, glucose, color=self.colors['group1'], 
                   alpha=0.15, linewidth=1)
        
        # Plot Group 2 spikes
        for match in matches2:
            spike = match.spike
            duration = spike.duration_minutes
            minutes = np.linspace(0, duration, 50)
            
            if normalize:
                peak_idx = int(len(minutes) * (spike.time_to_peak_minutes / duration))
                glucose = np.concatenate([
                    np.linspace(0, 1, peak_idx),
                    np.linspace(1, 0, len(minutes) - peak_idx)
                ])
            else:
                peak_idx = int(len(minutes) * (spike.time_to_peak_minutes / duration))
                glucose = np.concatenate([
                    np.linspace(spike.baseline, spike.peak_glucose, peak_idx),
                    np.linspace(spike.peak_glucose, spike.end_glucose, len(minutes) - peak_idx)
                ])
            
            ax.plot(minutes, glucose, color=self.colors['group2'], 
                   alpha=0.15, linewidth=1)
        
        # Add legend patches for groups
        group1_patch = mpatches.Patch(color=self.colors['group1'], 
                                     label=f'Group 1: {group1_info["description"]} (n={len(matches1)})')
        group2_patch = mpatches.Patch(color=self.colors['group2'], 
                                     label=f'Group 2: {group2_info["description"]} (n={len(matches2)})')
        
        ax.legend(handles=[group1_patch, group2_patch], loc='upper right', fontsize=10)
        
        # Formatting
        ax.set_xlabel('Minutes from Spike Start', fontsize=12)
        if normalize:
            ax.set_ylabel('Normalized Glucose (0=baseline, 1=peak)', fontsize=12)
            ax.axhline(y=0, color=self.colors['baseline'], linestyle='--', 
                      linewidth=1, alpha=0.7)
            title_suffix = ' (Normalized)'
        else:
            ax.set_ylabel('Glucose (mg/dL)', fontsize=12)
            title_suffix = ''
        
        ax.set_title(f'Group Comparison{title_suffix}', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add comparison statistics
        if normalize:
            textstr = '\n'.join([
                'Group 1:',
                f'  Normalized AUC: {comparison.group1.normalized_auc["mean"]:.3f}',
                f'  Duration: {comparison.group1.duration["mean"]:.0f} min',
                'Group 2:',
                f'  Normalized AUC: {comparison.group2.normalized_auc["mean"]:.3f}',
                f'  Duration: {comparison.group2.duration["mean"]:.0f} min',
                'Change:',
                f'  {comparison.changes["normalized_auc"]["percent"]:+.1f}%'
            ])
        else:
            textstr = '\n'.join([
                'Group 1:',
                f'  AUC-relative: {comparison.group1.auc_relative["mean"]:.0f}',
                f'  Magnitude: {comparison.group1.magnitude["mean"]:.0f} mg/dL',
                'Group 2:',
                f'  AUC-relative: {comparison.group2.auc_relative["mean"]:.0f}',
                f'  Magnitude: {comparison.group2.magnitude["mean"]:.0f} mg/dL',
                'Change:',
                f'  {comparison.changes["auc_relative"]["percent"]:+.1f}%'
            ])
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Save figure
        norm_suffix = '_normalized' if normalize else ''
        filename = f'compare_groups{norm_suffix}.png'
        filepath = self.output_dir / filename
        
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        
        if self.auto_open:
            self._open_file(filepath)
        
        plt.close()
        
        return str(filepath)
    
    def chart_scatter(self, group_analysis):
        """
        Generate scatter plot of GL vs AUC for a group
        
        Args:
            group_analysis: Dict from GroupAnalyzer.analyze_group()
            
        Returns:
            str: Path to saved chart file
        """
        if not group_analysis['stats']:
            raise ValueError("Group has no matched events to chart")
        
        matches = group_analysis['stats'].matches
        group_info = group_analysis['group_info']
        
        if len(matches) == 0:
            raise ValueError("No spikes in group to chart")
        
        # Extract data
        gl_values = [m.meal['gl'] for m in matches]
        auc_values = [m.spike.auc_relative for m in matches]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 8), dpi=self.dpi)
        
        # Scatter plot
        ax.scatter(gl_values, auc_values, s=100, alpha=0.6, 
                  color=self.colors['group1'], edgecolors='black', linewidth=1)
        
        # Add trendline
        if len(gl_values) > 1:
            z = np.polyfit(gl_values, auc_values, 1)
            p = np.poly1d(z)
            gl_range = np.linspace(min(gl_values), max(gl_values), 100)
            ax.plot(gl_range, p(gl_range), "--", color=self.colors['group2'], 
                   linewidth=2, alpha=0.8, label=f'Trend: y={z[0]:.1f}x+{z[1]:.0f}')
            
            # Calculate R²
            correlation_matrix = np.corrcoef(gl_values, auc_values)
            correlation = correlation_matrix[0, 1]
            r_squared = correlation ** 2
            
            ax.text(0.05, 0.95, f'R² = {r_squared:.3f}', 
                   transform=ax.transAxes, fontsize=12,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Formatting
        ax.set_xlabel('Glycemic Load (GL)', fontsize=12)
        ax.set_ylabel('AUC-relative (mg/dL*min)', fontsize=12)
        ax.set_title(f'GL vs AUC: {group_info["description"]}', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        if len(gl_values) > 1:
            ax.legend(loc='lower right', fontsize=10)
        
        # Add statistics
        textstr = '\n'.join([
            f'Data points: {len(matches)}',
            f'Avg GL: {np.mean(gl_values):.1f}',
            f'Avg AUC: {np.mean(auc_values):.0f}',
            f'GL range: {min(gl_values):.0f}-{max(gl_values):.0f}'
        ])
        
        props = dict(boxstyle='round', facecolor='lightblue', alpha=0.5)
        ax.text(0.95, 0.05, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='bottom', horizontalalignment='right', bbox=props)
        
        plt.tight_layout()
        
        # Save figure
        group_desc = group_info['description'].replace(' ', '-').lower()
        filename = f'scatter_{group_desc}_gl-vs-auc.png'
        filepath = self.output_dir / filename
        
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        
        if self.auto_open:
            self._open_file(filepath)
        
        plt.close()
        
        return str(filepath)
    
    def _open_file(self, filepath):
        """
        Open file with default system viewer
        
        Args:
            filepath: Path to file to open
        """
        import platform
        import subprocess
        
        system = platform.system()
        
        try:
            if system == 'Darwin':  # macOS
                subprocess.run(['open', str(filepath)], check=True)
            elif system == 'Windows':
                os.startfile(str(filepath))
            else:  # Linux and others
                subprocess.run(['xdg-open', str(filepath)], check=True)
        except Exception as e:
            # Silently fail if can't open
            pass