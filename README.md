# Glucose Spike Analyzer

Analysis tool for FreeStyle Libre 3 continuous glucose monitor (CGM) data from LibreView CSV exports.

## Purpose

Track glucose spike recovery improvement over time by calculating area under the curve (AUC) for post-meal glucose responses. Particularly useful for measuring the impact of medication adjustments or lifestyle interventions on glucose control.

## Project Structure

```
glucose-analyzer/
├── glucose_analyzer/              # Main package
│   ├── parsers/                  # Data input modules
│   │   └── csv_parser.py        # LibreView CSV parser ✓
│   ├── analysis/                 # Analysis modules
│   │   ├── spike_detector.py    # Spike detection ✓
│   │   ├── meal_matcher.py      # TODO
│   │   ├── auc_calculator.py    # TODO
│   │   └── normalizer.py        # TODO
│   ├── visualization/            # Chart generation
│   │   └── charts.py            # TODO
│   ├── utils/                    # Utilities
│   │   ├── config.py            # Config manager ✓
│   │   └── data_manager.py      # JSON persistence ✓
│   ├── analyzer.py              # Main analyzer class ✓
│   └── cli.py                   # CLI interface ✓
├── tests/                        # Test files
│   └── test_data.csv            # Sample CGM data
├── data/                         # User data (gitignored)
│   ├── libreview_data.csv       # Your CGM export (place here)
│   └── meals.json               # Meal log storage
├── charts/                       # Generated charts (gitignored)
├── config.json                   # Configuration
├── requirements.txt              # Python dependencies
└── glucose_analyzer.py          # Entry point script
```

## Features

**Completed (✓):**
- Parse LibreView CSV exports (Type 0 automatic readings)
- Manual meal logging with glycemic load (GL)
- **Spike detection with configurable parameters**
- Group-based temporal analysis
- CLI interface with interactive commands
- Configuration system
- Data persistence (JSON)

**In Development:**
- Meal-to-spike matching
- Multiple AUC calculations (AUC-0, AUC-70, AUC-relative)
- Normalized spike profiles for shape comparison
- Visual charts (matplotlib PNG output)

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Setup
1. Export your LibreView data as CSV
2. Place the CSV file at `data/libreview_data.csv`
3. Run the application: `python glucose_analyzer.py`

### Interactive Commands

```
> addmeal 2025-11-14:18:00 33      # Add meal with GL=33
> group start 2025-11-01:00:00 "baseline period"
> group end 2025-11-30:23:59
> stats                            # Show CGM statistics
> analyze                          # Detect glucose spikes
> list spikes                      # Show detected spikes
> chart group 0                    # Generate charts (TODO)
> list meals
> list groups
> help
> quit
```

### Command Reference

- `addmeal <timestamp> <gl>` - Add meal entry
- `group start <timestamp> <desc>` - Start new analysis group
- `group end <timestamp>` - Close current group
- `bypass <timestamp> <reason>` - Mark unexplained spike
- `stats` - Show CGM data statistics
- `analyze` - Detect glucose spikes in CGM data
- `list spikes [start] [end]` - Show detected spikes (optionally filtered)
- `chart group <n>` - Generate group visualizations (TODO)
- `chart meal <timestamp>` - Chart individual meal spike (TODO)
- `list meals [start] [end]` - List meals in date range
- `list groups` - Show all analysis groups
- `help` - Show command help
- `quit` - Exit program

Timestamp format: `YYYY-MM-DD:HH:MM` (24-hour)

## Configuration

Edit `config.json` to adjust:
- **Search window:** Minutes after meal to look for spike (default: 90)
- **Proximity threshold:** Minutes between meals for complex event flagging (default: 180)
- **Spike detection:** Magnitude thresholds and end criteria
- **File paths:** Input CSV and output locations
- **Chart settings:** DPI, auto-open behavior

## Development

The codebase is organized into clear modules:
- **parsers/**: Data input (CSV parsing)
- **analysis/**: Core algorithms (spike detection, AUC calculation)
- **visualization/**: Chart generation
- **utils/**: Configuration and data management
- **cli.py**: Interactive command interface
- **analyzer.py**: Main orchestration class

Next implementation priority: Spike detection algorithm

## License

Personal project for glucose data analysis.
