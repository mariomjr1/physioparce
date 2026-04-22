# The Graphical Interface (GUI)

The GUI is a desktop application that lets you run all three pipeline steps without touching the terminal. It provides file pickers for every input, a live console showing script output, and a status bar at the bottom.

---

## How to launch the GUI

Open a terminal, navigate to the `gui/` folder, and run:

```bash
bash run.sh
```

Or from anywhere on your computer:

```bash
bash /path/to/pseudotime/gui/run.sh
```

The launcher will find the Neuroimaging conda environment automatically and open the window.

---

## Window layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Pseudotime Pipeline                  Scripts root: [...] [Change]│
├─────────────────────────────────────────────────────────────────┤
│ ┌─ Quick Setup ──────────────────────────────────────────────┐  │
│ │ Data folder: [_________________________________] [Browse…]  │  │
│ │ Picks the .mat, pseudotime_mapping.json, and output folder  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌─ 1 · Compute Pseudotime ─┐ ┌─ 2 · Plot Quality ─┐ ┌─ 3 ... ┐│
│ │                           │ │                     │ │        ││
│ │ [Step 1 form fields]      │ │                     │ │        ││
│ │                           │ │                     │ │        ││
│ └───────────────────────────┘ └─────────────────────┘ └────────┘│
│                                                                   │
│ ┌─ Console Output ──────────────────────────────────────────────┐│
│ │ (dark terminal area showing script output)                    ││
│ │                                                               ││
│ │                                                         [Clear]│
│ └───────────────────────────────────────────────────────────────┘│
│ Ready                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Each part of the window explained

### Scripts root (top right)

Shows the folder where the three pipeline scripts (`1_times_acquisition.sh`, etc.) are located. This is detected automatically when the GUI opens — it is the parent folder of the `gui/` folder.

**When to change it:** Only if you have moved the scripts to a different location. Click `Change…` and select the folder that contains the three scripts. The GUI will look for scripts in this folder whenever you press a Run button.

---

### Quick Setup banner

The most important part of the GUI for first-time use. You only need to set **one path** here — the data folder — and the GUI will automatically fill in all the fields in all three tabs.

**What it auto-fills:**
- The `.mat` file (first non-bold `.mat` found in the folder)
- The `pseudotime_mapping.json` (if it already exists from a previous Step 1 run)
- The output image path for Step 2 (set to `../pseudotime_plot.png` relative to the data folder)
- The output folder for Step 3 (set to `../parsed/` relative to the data folder)

**Typical workflow:** Set this once and then just click Run on each tab in order.

---

### Tab: 1 · Compute Pseudotime

**What runs:** `bash 1_times_acquisition.sh <data_folder> <mat_filename>`

| Field | What to put here |
|-------|-----------------|
| Data folder | The folder containing your `.mat` file and all BIDS `.json` files. Browse to select it, or it will be filled automatically by Quick Setup. |
| MAT file | The full path to the physiological `.mat` file. If you set the Data folder first and the MAT field was empty, it is filled automatically. |

**When you click Run Step 1:**
1. The button becomes disabled (grayed out) to prevent double-clicking
2. A progress bar starts animating (back and forth — this shows the script is running, not a percentage)
3. The console shows the script's output in real time
4. When finished, the button is re-enabled and the status bar shows "Step 1 complete ✓" or an error

**After Step 1 finishes:** `pseudotime_mapping.json` is saved into your data folder. You can now run Step 2 and Step 3.

---

### Tab: 2 · Plot Quality

**What runs:** `python 2_plot_pseudotime_quality.py <mat_file> <json_file> <output_image>`

| Field | What to put here |
|-------|-----------------|
| MAT file | Same `.mat` file as Step 1 |
| Pseudotime JSON | The `pseudotime_mapping.json` created by Step 1. Browse to it, or it will be filled automatically by Quick Setup. |
| Output image | Where to save the plot. Browse and type a filename ending in `.png`, or accept the default path filled by Quick Setup. |

**Note:** Step 2 can take 1–3 minutes because it loads the entire 156 MB recording into memory and renders plots with millions of data points. The console will be quiet during loading — this is normal.

**After Step 2 finishes:** Two image files are saved:
- The path you specified → main 5-panel visualization
- Same path with `_stats` added → summary statistics figure

---

### Tab: 3 · Parse Segments

**What runs:** `python 3_parse.py <data_folder> <output_folder>`

| Field | What to put here |
|-------|-----------------|
| Data folder | Same data folder as Step 1. Must contain `pseudotime_mapping.json` and `dicominfo_ses-01.tsv`. |
| Output folder | Where to save the segment `.mat` files and plots. Will be created if it doesn't exist. The default from Quick Setup is `parsed/` next to the data folder. |

**After Step 3 finishes:** The output folder will contain one `.mat` and one `.png` per matched sequence, plus a `plots/` subfolder with all the PNG files. If any sequences were skipped (no duration found in dicominfo), a `unmatched_sequences.log` file explains which ones and why.

---

### Console Output

The dark terminal area at the bottom shows everything the running script prints — the same output you would see if you ran the script manually in a terminal.

**Color coding:**
- Blue text — step headers and divider lines
- Teal/green text — success messages (✓, "done", "saved", "complete")
- Yellow text — warnings (things that were skipped or couldn't be matched)
- Red text — errors (the script failed or something is wrong)
- White/light gray — normal informational output

The console scrolls automatically to always show the latest line. Click **Clear** to erase all previous output.

---

### Status bar (bottom edge)

A one-line summary of the current state:

| Status text | Meaning |
|------------|---------|
| `Ready` | No script has been run yet |
| `Step N running…` | A script is currently executing |
| `Step N complete ✓` | The last script finished successfully |
| `Step N failed (exit 1)` | The script exited with an error — check the console for details |

---

## Complete step-by-step walkthrough

This assumes you are starting from scratch with a new dataset.

### 1. Prepare your data folder

Place these files in a single folder:
- The full physiological `.mat` recording
- All BIDS `.json` sidecar files (one per MRI sequence)
- The `dicominfo_ses-01.tsv` file

### 2. Launch the GUI

```bash
bash /path/to/pseudotime/gui/run.sh
```

### 3. Set the data folder (Quick Setup)

In the "Quick Setup" banner at the top, click **Browse…** next to "Data folder" and select the folder you just prepared. The GUI will automatically find the `.mat` file, check for an existing `pseudotime_mapping.json`, and fill in all three step tabs.

### 4. Run Step 1

Click the **"1 · Compute Pseudotime"** tab. Verify the Data folder and MAT file look correct, then click **▶ Run Step 1**. Watch the console output. The script prints the acquisition times of all sequences, the trigger count, and the computed pseudotimes. It ends with "Pseudotime mapping saved" and the green success message.

### 5. Run Step 2

Click the **"2 · Plot Quality"** tab. The fields should already be filled. Click **▶ Run Step 2**. Wait 1–3 minutes. When done, open the output images and verify that the MRTRIG pulses (green panel) line up with the colored timeline bars in panel 5.

### 6. Run Step 3

Click the **"3 · Parse Segments"** tab. The fields should already be filled. Click **▶ Run Step 3**. The console will print each sequence as it is processed. When done, check the output folder for the `.mat` files and the `plots/` folder for the PNG images.

---

## Technical details (for developers)

The GUI is built with Python's built-in `tkinter` library (no installation required). The code is split into two files:

### `gui/app.py` — the interface

Contains these classes:

| Class | What it is |
|-------|-----------|
| `PathRow` | A reusable widget: label + text entry + Browse button |
| `Console` | The dark scrollable text area with color-coded output |
| `Step1Panel` | The content of the Step 1 tab |
| `Step2Panel` | The content of the Step 2 tab |
| `Step3Panel` | The content of the Step 3 tab |
| `ConfigBanner` | The Quick Setup banner that auto-fills all three tabs |
| `App` | The main window that assembles everything |

### `gui/runner.py` — the subprocess engine

Handles running scripts without freezing the GUI. The key problem: if you run a slow script directly on the interface's thread, the window freezes until it finishes. The solution:

1. The script is launched in a **background thread** (a parallel execution track)
2. Output lines are put into a **queue** (a thread-safe message buffer)
3. Every 50 milliseconds, the GUI's main thread checks the queue and prints any new lines to the Console

This way the window stays responsive (you can scroll, resize, etc.) while the script runs.

### `gui/run.sh` — the launcher

Finds the Neuroimaging conda environment by looking for the Python executable at a direct filesystem path (`~/anaconda3/envs/Neuroimaging/bin/python`). This is more reliable than `conda activate`, which requires the shell to have been specially initialized. Falls back to system `python3` with a warning if the conda env is not found.
