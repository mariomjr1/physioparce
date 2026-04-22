# Pseudotime Pipeline — Documentation

## What is this project?

This project is a **physiological data processing pipeline** for MRI research sessions. During an MRI scan, a recording device (ADInstruments LabChart) continuously records four physiological signals from the subject: breathing, heart rate, stimulus triggers, and MRI scanner triggers. All saved into a single `.mat` file.

The problem this pipeline solves: **the physiological recording runs continuously across the entire session, but the MRI data is split into separate sequences** (rest, stimulation, breathing tasks, etc.) that were acquired at different times. To analyze the physiology of each MRI sequence separately, you need to know exactly where each sequence starts and ends inside the continuous physiological recording.

This is what **pseudotime** means: a unified time axis, anchored to the first MRI trigger detected in the recording, that allows every sequence to be located precisely within the physiological data.

---

## What does the pipeline do?

The pipeline has three sequential steps:

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `1_times_acquisition.sh` | Reads the MRI triggers from the recording, finds when each sequence started, and saves a timing map |
| 2 | `2_plot_pseudotime_quality.py` | Creates a visual overview of all 4 channels and marks when each sequence was running |
| 3 | `3_parse.py` | Cuts the continuous recording into individual per-sequence `.mat` files, one per MRI sequence |

All three steps can be run through a graphical interface (the GUI) or directly from the terminal.

---

## Project folder structure

```
pseudotime/
│
├── 1_times_acquisition.sh          ← Step 1 script
├── 2_plot_pseudotime_quality.py    ← Step 2 script
├── 3_parse.py                      ← Step 3 script
│
├── data/                           ← YOUR INPUT DATA GOES HERE
│   ├── subject.mat                 ← full physiological recording
│   ├── pseudotime_mapping.json     ← created by Step 1
│   ├── dicominfo_ses-01.tsv        ← DICOM scan information
│   └── sub-..._bold.json           ← one per MRI sequence (BIDS format)
│
├── parsed/                         ← OUTPUT from Step 3
│   ├── task-rest_run-01.mat
│   ├── task-rest_run-01.png
│   └── plots/
│
├── gui/                            ← Graphical interface
│   ├── app.py
│   ├── runner.py
│   └── run.sh
│
├── pseudotime_plot.png             ← Output from Step 2
├── pseudotime_plot_stats.png       ← Output from Step 2
│
└── documentation/                  ← You are here
    ├── README.md
    ├── concepts.md
    ├── installation.md
    ├── data_folder.md
    ├── step1.md
    ├── step2.md
    ├── step3.md
    └── gui.md
```

---

## Quick start (first time)

1. Read [installation.md](installation.md) to set up your Python environment
2. Read [data_folder.md](data_folder.md) to understand what files you need and where to put them
3. Read [concepts.md](concepts.md) if you want to understand what pseudotime means before running anything
4. Launch the GUI: open a terminal, go to the `gui/` folder, and run `bash run.sh`
5. Follow the step-by-step walkthrough in [gui.md](gui.md)

---

## Documentation index

| File | What it covers |
|------|---------------|
| [concepts.md](concepts.md) | Background — pseudotime, physiological channels, MRI triggers |
| [installation.md](installation.md) | Setting up the Python environment |
| [data_folder.md](data_folder.md) | What files are needed and what they contain |
| [step1.md](step1.md) | `1_times_acquisition.sh` — computing pseudotime |
| [step2.md](step2.md) | `2_plot_pseudotime_quality.py` — quality visualization |
| [step3.md](step3.md) | `3_parse.py` — parsing segments |
| [gui.md](gui.md) | The graphical interface — how to use it |
