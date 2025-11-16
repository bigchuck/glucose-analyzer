# Glucose Spike Analyzer

Analysis tool for FreeStyle Libre 3 continuous glucose monitor (CGM) data from LibreView CSV exports.

## Purpose

Track glucose spike recovery improvement over time by calculating area under the curve (AUC) for post-meal glucose responses. Particularly useful for measuring the impact of medication adjustments or lifestyle interventions on glucose control.

## Features

- Parse LibreView CSV exports (Type 0 automatic readings)
- Manual meal logging with glycemic load (GL)
- Spike detection with configurable parameters
- Multiple AUC calculations (AUC-0, AUC-70, AUC-relative)
- Normalized spike profiles for shape comparison
- Group-based temporal analysis
- Visual charts (matplotlib PNG output)

## Installation

```bash
pip install -r requirements.txt --break-system-packages
```

## Usage

```bash
python glucose_analyzer.py
```

### Interactive Commands

- `addmeal <timestamp> <gl>` - Add meal entry (e.g., `addmeal 2025-11-14:18:00 33`)
- `group start <timestamp> <description>` - Start new analysis group
- `group end <timestamp>` - Close current group
- `bypass <timestamp> <reason>` - Mark unexplained spike
- `analyze` - Run full analysis
- `chart group <name>` - Generate group visualizations
- `chart meal <timestamp>` - Chart individual meal spike
- `list meals [start] [end]` - List meals in date range
- `list groups` - Show all analysis groups
- `quit` - Exit program

## Configuration

Edit `config.json` to adjust:
- Search window (default: 90 minutes after meal)
- Proximity threshold (default: 180 minutes between meals)
- Spike detection thresholds
- Input/output file paths

## Data Files

- `libreview_data.csv` - LibreView export (configure path in config.json)
- `meals.json` - Meal log, groups, and bypassed spikes
- `charts/` - Generated visualization output

## Project Status

In development - initial implementation phase.
