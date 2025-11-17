# Glucose Analyzer - Group Module Package

## 📦 Package Contents

This package contains the **Group Analyzer** module for temporal glucose response comparisons.

### What's New
**Group Analyzer v1.1.0** - Complete temporal comparison system with 400+ lines of production code

### Downloads
- **glucose-analyzer-group-module.zip** (28 KB) - For Windows users
- **glucose-analyzer-group-module.tar.gz** (20 KB) - For macOS/Linux users

## 📄 Files Included

### New Module (Core Feature)
```
glucose_analyzer/analysis/group_analyzer.py (400+ lines)
├── GroupStats - Single group statistics
├── GroupComparison - Two-group comparison
└── GroupAnalyzer - Main analysis engine
```

### Updated Core Files
```
glucose_analyzer/analyzer.py - Integrated group analyzer
glucose_analyzer/cli.py - Added 4 new commands
glucose_analyzer/utils/config.py - Configuration manager
glucose_analyzer/utils/data_manager.py - Data persistence
```

### Documentation
```
GROUP_ANALYZER.md - Complete feature documentation (30+ sections)
QUICKSTART.md - 10-minute getting started guide
README.md - Updated project overview
RELEASE_NOTES.md - Version 1.1.0 changelog
INSTALL.md - Integration instructions
```

### Supporting Files
```
config.json - Configuration template
requirements.txt - Python dependencies
glucose_analyzer.py - Entry point script
data/meals.json - Data storage template
tests/test_data.csv - Sample CGM data
```

## 🚀 Quick Start

### 1. Extract Package
```bash
# Windows
unzip glucose-analyzer-group-module.zip

# macOS/Linux
tar -xzf glucose-analyzer-group-module.tar.gz
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Add Your Data
Place your LibreView CSV at: `data/libreview_data.csv`

### 4. Run Application
```bash
python glucose_analyzer.py
```

## ✨ New Features

### Commands Added
| Command | Purpose |
|---------|---------|
| `analyze group <n>` | Analyze single group with full statistics |
| `analyze group <n> --gl-range X-Y` | GL-filtered group analysis |
| `compare groups <n1> <n2>` | Side-by-side comparison of two groups |
| `compare groups <n1> <n2> --gl-range X-Y` | GL-stratified comparison |

### Capabilities
✅ Temporal comparisons across time periods  
✅ Six core metrics in priority order  
✅ GL-stratified analysis (compare similar meals)  
✅ Side-by-side statistics with percent changes  
✅ Improvement indicators (✓/✗)  
✅ Unmatched spike tracking per group  
✅ Mean, median, std, min, max for all metrics

## 📊 Usage Example

```bash
# Create two groups
> group start 2025-11-01:00:00 "baseline"
> group end 2025-11-30:23:59
> group start 2025-12-01:00:00 "after medication"
> group end 2025-12-31:23:59

# Log meals
> addmeal 2025-11-15:18:00 33
> addmeal 2025-12-15:18:00 33

# Run analysis
> analyze

# Compare groups
> compare groups 0 1

Group Comparison
==========================================================================================================
Metric               Group 1              Group 2              Change                   
----------------------------------------------------------------------------------------------------------
AUC-relative         2840.0 ± 450.0       2150.0 ± 380.0       -24.3% ✓
Normalized AUC       0.485 ± 0.065        0.425 ± 0.058        -12.4% ✓
Recovery time        98.0 ± 15.0 min      82.0 ± 12.0 min      -16.3% ✓
Magnitude            82.0 ± 12.0 mg/dL    75.0 ± 10.0 mg/dL    -8.5% ✓

Improvement in 4/4 key metrics
```

## 🎯 Core Metrics (Priority Order)

1. **AUC-relative** - Total glucose exposure above baseline (mg/dL*min)
2. **Normalized AUC** - Recovery speed, scaled 0-1  
3. **Recovery time** - Minutes to return to baseline
4. **Magnitude** - Peak rise from baseline (mg/dL)
5. **Time to peak** - Minutes from meal to peak
6. **Delay** - Minutes from meal to spike start

**Lower is better** for metrics 1-4 (improvement indicators show ✓)

## 📖 Documentation

### Start Here
1. **QUICKSTART.md** - 10-minute setup and first analysis
2. **GROUP_ANALYZER.md** - Complete feature documentation with examples

### Reference
3. **README.md** - Full project overview
4. **RELEASE_NOTES.md** - Version 1.1.0 changelog
5. **INSTALL.md** - Integration instructions

### In-Code
All modules have comprehensive docstrings and type hints

## 🔧 Integration

### Fresh Installation
1. Extract package
2. Install dependencies: `pip install -r requirements.txt`
3. Copy missing modules from original project (csv_parser, spike_detector, etc.)
4. Place CGM data
5. Run application

### Update Existing Installation
1. Copy `group_analyzer.py` to your `glucose_analyzer/analysis/` directory
2. Replace `analyzer.py` and `cli.py` (or merge changes)
3. Add documentation files
4. Update README

## ✅ Module Status

**Included in Package:**
- ✅ group_analyzer.py (NEW! 400+ lines)
- ✅ analyzer.py (updated)
- ✅ cli.py (updated)
- ✅ config.py
- ✅ data_manager.py
- ✅ Complete documentation

**Requires from Original Project:**
- ○ parsers/csv_parser.py
- ○ analysis/spike_detector.py
- ○ analysis/meal_matcher.py
- ○ analysis/auc_calculator.py

## 🧪 Testing

Includes sample test data (tests/test_data.csv) with 48 CGM readings showing 2 glucose spikes.

Test the module:
```bash
> analyze
> analyze group 0
> compare groups 0 1
```

All commands should execute without errors.

## 📋 Requirements

- Python 3.8+
- pandas >= 2.0.0
- numpy >= 1.24.0
- matplotlib >= 3.7.0
- python-dateutil >= 2.8.2

## 🚦 Next Steps

1. **Extract** the package
2. **Review** QUICKSTART.md
3. **Install** dependencies
4. **Integrate** with your project
5. **Test** with sample data
6. **Analyze** your glucose data!

## 📌 Key Features Summary

| Feature | Description | Benefit |
|---------|-------------|---------|
| Temporal Comparison | Compare across time periods | Track improvement quantitatively |
| GL Stratification | Filter by meal size | Fair comparisons |
| Six Core Metrics | Prioritized tracking | Focus on what matters |
| Side-by-Side Tables | Clear visualization | Easy interpretation |
| Improvement Indicators | ✓/✗ markers | Instant feedback |
| Unmatched Tracking | Monitor unexplained events | Identify patterns |

## 💡 Use Cases

- **Track medication effectiveness** - Before/after comparisons
- **Monitor lifestyle changes** - Exercise, diet modifications
- **Identify problem foods** - High-response meals
- **Measure recovery improvement** - Faster return to baseline
- **Compare time periods** - Any two date ranges

## 🎓 Learning Path

1. **Day 1:** Extract package, review QUICKSTART.md
2. **Day 2:** Create test groups, run first comparison
3. **Day 3:** Read GROUP_ANALYZER.md, try GL stratification
4. **Week 2:** Analyze your data, track first improvements
5. **Month 1:** Regular monitoring, measure intervention effects

## 📞 Support

- **GROUP_ANALYZER.md** - Detailed usage examples
- **Code comments** - Inline documentation
- **config.json** - Adjustable parameters

## ⚖️ License

Personal project for glucose data analysis.

---

**Version:** 1.1.0  
**Module:** Group Analyzer  
**Status:** Production Ready  
**Lines:** 400+  
**Release:** November 2025

**Ready to track your glucose control improvement!** 📊✨
