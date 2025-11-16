"""Data persistence manager for meals, groups, and bypassed spikes"""

import json
import os


class DataManager:
    """Manages meals.json persistence"""
    
    def __init__(self, filepath):
        """
        Initialize data manager
        
        Args:
            filepath: Path to JSON data file
        """
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
        """
        Add a meal entry
        
        Args:
            timestamp: Meal timestamp string (YYYY-MM-DD:HH:MM)
            gl: Glycemic load value
            
        Returns:
            dict: The created meal entry
        """
        meal = {
            "timestamp": timestamp,
            "gl": gl
        }
        self.data["meals"].append(meal)
        self.save()
        return meal
    
    def start_group(self, start_time, description):
        """
        Start a new analysis group
        
        Args:
            start_time: Group start timestamp
            description: Group description
            
        Returns:
            dict: The created group entry
        """
        group = {
            "start": start_time,
            "end": None,
            "description": description
        }
        self.data["groups"].append(group)
        self.save()
        return group
    
    def end_group(self, end_time):
        """
        End the current open group
        
        Args:
            end_time: Group end timestamp
            
        Returns:
            dict: The closed group, or None if no open group
        """
        for group in reversed(self.data["groups"]):
            if group["end"] is None:
                group["end"] = end_time
                self.save()
                return group
        return None
    
    def add_bypass(self, timestamp, reason):
        """
        Mark a spike as bypassed
        
        Args:
            timestamp: Spike timestamp
            reason: Reason for bypass
            
        Returns:
            dict: The created bypass entry
        """
        bypass = {
            "timestamp": timestamp,
            "reason": reason
        }
        self.data["bypassed_spikes"].append(bypass)
        self.save()
        return bypass
    
    def get_meals(self, start=None, end=None):
        """
        Get meals in date range
        
        Args:
            start: Optional start timestamp filter
            end: Optional end timestamp filter
            
        Returns:
            list: Filtered and sorted meals
        """
        meals = self.data["meals"]
        if start:
            meals = [m for m in meals if m["timestamp"] >= start]
        if end:
            meals = [m for m in meals if m["timestamp"] <= end]
        return sorted(meals, key=lambda m: m["timestamp"])
    
    def get_open_group(self):
        """
        Get currently open group, if any
        
        Returns:
            dict: Open group or None
        """
        for group in reversed(self.data["groups"]):
            if group["end"] is None:
                return group
        return None
