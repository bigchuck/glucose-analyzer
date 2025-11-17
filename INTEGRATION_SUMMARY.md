# Normalizer Integration - Quick Start

## Files Available for Download

**[normalizer.py](computer:///mnt/user-data/outputs/normalizer.py)** (14KB)
- Place at: `glucose_analyzer/analysis/normalizer.py`
- New module - just copy to your project

**[CLI_CHANGES.md](computer:///mnt/user-data/outputs/CLI_CHANGES.md)** (detailed guide)
- Shows exactly what to add to `glucose_analyzer/cli.py`
- 3 new command methods + 2 small edits
- ~180 lines to add

**[ANALYZER_CHANGES.md](computer:///mnt/user-data/outputs/ANALYZER_CHANGES.md)** (detailed guide)
- Shows exactly what to add to `glucose_analyzer/analyzer.py`
- 1 import + 2 lines in __init__() + 5 lines in run_analysis()
- ~8 lines total

## Quick Integration Steps

### 1. Copy New File
```bash
# Copy normalizer.py to your project
cp normalizer.py glucose-analyzer/glucose_analyzer/analysis/
```

### 2. Update analyzer.py (3 edits)

**Line 7 - Add import:**
```python
from glucose_analyzer.analysis.normalizer import SpikeNormalizer
```

**Line 25 - Add to __init__():**
```python
self.normalizer = SpikeNormalizer()
self.normalized_profiles = []
```

**Line 110 - Add to run_analysis() after meal matching:**
```python
# Normalize matched profiles
if match_stats['matched_count'] > 0:
    print(f"\nCreating normalized profiles...")
    self.normalized_profiles = self.normalizer.normalize_matches(
        self.match_results['matched'], 
        self.cgm_data
    )
    print(f"[OK] Normalized {len(self.normalized_profiles)} spike profiles")
```

### 3. Update cli.py (5 edits)

**Add 3 new command methods:**
- `cmd_list_profiles()` - List normalized profiles
- `cmd_compare_groups()` - Compare two groups
- `cmd_find_similar()` - Find similar spike shapes

**Update process_command():**
```python
elif subcommand == "profiles":
    self.cmd_list_profiles(args[1:])
```

```python
elif cmd == "compare":
    self.cmd_compare_groups(args)
elif cmd == "similar":
    self.cmd_find_similar(args)
```

**Update cmd_help():**
Add new commands to help text.

See CLI_CHANGES.md for complete code.

## Test It Works

```bash
$ python glucose_analyzer.py
> analyze

Analyzing glucose data for spikes...
[OK] Spike detection complete
Found 2 spike events

Matching 2 meals to spikes...
[OK] Meal matching complete

Creating normalized profiles...
[OK] Normalized 2 spike profiles    ← YOU SHOULD SEE THIS

> list profiles

Normalized Spike Profiles (2 total):
Profile 1:
  Spike: 2025-11-14T06:15:00
  Meal: 2025-11-14:06:00 (GL=25.0)
  Duration: 105 minutes
  Baseline: 82 mg/dL
  Peak: 168 mg/dL
  Magnitude: 86 mg/dL
```

## New Commands

```bash
list profiles [start] [end]       # Show all normalized profiles
compare "group1" "group2"          # Compare temporal groups
similar <index> [threshold]        # Find similar spike shapes
```

## What You Get

- **Shape-based comparison** - Compare spikes independent of magnitude
- **Similarity detection** - Find meals producing similar responses
- **Group comparison** - Track improvement over time
- **Quantitative metrics** - Statistical analysis of spike shapes

## Need Help?

Check the detailed guides:
- **CLI_CHANGES.md** - Complete CLI code with explanations
- **ANALYZER_CHANGES.md** - Complete analyzer changes with context

Both files show exactly what to add and where!
