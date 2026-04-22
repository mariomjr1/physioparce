# Pseudotime Pipeline

A physiological data processing pipeline for MRI research sessions.
Aligns a continuous LabChart recording (RESP, RPIEZO, STIMTRIG, MRTRIG) to individual MRI sequences using MR-trigger–anchored pseudotime.

---

## Pipeline overview

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `1_times_acquisition.sh` | Detects MR triggers, computes pseudotime for each sequence, saves `pseudotime_mapping.json` |
| 2 | `2_plot_pseudotime_quality.py` | Visualises all 4 channels with colour-coded acquisition bars |
| 3 | `3_parse.py` | Cuts the recording into per-sequence `.mat` files and plots |

Run all steps through the graphical interface: `bash gui/run.sh [conda_env_name]`

---

## Quick start

```bash
# 1. Launch the GUI (replace MyEnv with your conda environment name)
bash gui/run.sh MyEnv

# 2. In the Quick Setup banner, browse to your data folder — all fields fill automatically.
# 3. Run Step 1 → Step 2 → Step 3 in order.
```

See the full walkthrough in [documentation/gui.md](documentation/gui.md).

---

## Documentation

| File | Contents |
|------|----------|
| [documentation/concepts.md](documentation/concepts.md) | Pseudotime, the 4 channels, MRI triggers, file formats |
| [documentation/installation.md](documentation/installation.md) | Python environment setup and troubleshooting |
| [documentation/data_folder.md](documentation/data_folder.md) | Every required file explained |
| [documentation/step1.md](documentation/step1.md) | `1_times_acquisition.sh` — how it works |
| [documentation/step2.md](documentation/step2.md) | `2_plot_pseudotime_quality.py` — reading the plots |
| [documentation/step3.md](documentation/step3.md) | `3_parse.py` — output files and the unmatched log |
| [documentation/gui.md](documentation/gui.md) | GUI walkthrough, every field explained |

---

## Repository layout

```
pseudotime/
├── 1_times_acquisition.sh
├── 2_plot_pseudotime_quality.py
├── 3_parse.py
├── gui/
│   ├── app.py        ← main GUI window
│   ├── runner.py     ← thread-safe subprocess runner
│   └── run.sh        ← launcher (pass conda env name as argument)
└── documentation/
    ├── concepts.md
    ├── installation.md
    ├── data_folder.md
    ├── step1.md
    ├── step2.md
    ├── step3.md
    └── gui.md
```

> `data/` and `parsed/` are excluded from version control (see `.gitignore`).
