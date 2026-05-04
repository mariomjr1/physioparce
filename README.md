# Pseudotime Pipeline

A physiological data processing pipeline for MRI research sessions.
Aligns a continuous LabChart recording (RESP, RPIEZO, STIMTRIG, MRTRIG) to individual MRI sequences using MR-trigger–anchored pseudotime.

---

## Pipeline overview

Each step has two variants — one per LabChart export format. Select the correct format in the GUI before running.

| Step | Classic script | Block1 script | What it does |
|------|---------------|---------------|-------------|
| 1 | `1_times_acquisition.sh` | `1b_times_acquisition_block1.sh` | Detects MR triggers, computes pseudotime for each sequence, saves `pseudotime_mapping.json` |
| 2 | `2_plot_pseudotime_quality.py` | `2b_plot_pseudotime_quality_block1.py` | Visualises all 4 channels with colour-coded acquisition bars |
| 3 | `3_parse.py` | `3b_parse_block1.py` | Cuts the recording into per-sequence `.mat` files and plots |

Run all steps through the graphical interface: `bash gui/run.sh [conda_env_name]`

---

## MAT file formats

LabChart exports `.mat` files in two layouts depending on the software version:

| Format | Key in `.mat` | Layout |
|--------|--------------|--------|
| **Classic** | `data`, `datastart`, `dataend` | 1-D flattened array; channel boundaries given by `datastart`/`dataend` |
| **Block1** | `data_block1` | 2-D array `(4, N)` — each row is a channel directly |

Channel order is the same in both formats:

| Row / index | Channel |
|-------------|---------|
| 0 | RESP — respiration belt |
| 1 | RPIEZO — respiratory piezo |
| 2 | STIMTRIG — stimulus trigger |
| 3 | MRTRIG — MR scanner trigger |

The GUI exposes a **MAT file format** radio selector on every step panel. Choose *Classic* or *Block1* before clicking Run.

---

## Quick start

```bash
# 1. Launch the GUI (replace MyEnv with your conda environment name)
bash gui/run.sh MyEnv

# 2. In the Quick Setup banner, browse to your data folder — all fields fill automatically.
# 3. Select the MAT file format (Classic or Block1) on each step tab.
# 4. Run Step 1 → Step 2 → Step 3 in order.
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
├── 1_times_acquisition.sh            ← Step 1 — classic format
├── 1b_times_acquisition_block1.sh    ← Step 1 — block1 format
├── 2_plot_pseudotime_quality.py      ← Step 2 — classic format
├── 2b_plot_pseudotime_quality_block1.py  ← Step 2 — block1 format
├── 3_parse.py                        ← Step 3 — classic format
├── 3b_parse_block1.py                ← Step 3 — block1 format
├── gui/
│   ├── app.py        ← main GUI window (format selector on every step)
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
