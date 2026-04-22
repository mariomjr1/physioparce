# Step 3 — Parse Segments

**Script:** `3_parse.py`  
**Language:** Python  
**Run time:** Several minutes (loads the full 156 MB recording, then writes N output files)

---

## What it does

Step 3 is the final output step. It takes the continuous physiological recording and **cuts it into individual segments**, one per MRI sequence. Each segment contains only the portion of the recording that corresponds to that sequence — from when the first MRI trigger of the sequence occurred until the sequence ended.

For each sequence it produces two output files:

1. A `.mat` file containing the four channel segments
2. A `.png` plot showing the four channels for that segment

---

## Inputs

| Input | Where it comes from |
|-------|-------------------|
| Data folder | Specified in the GUI or command line — must contain `pseudotime_mapping.json`, the `.mat` file, and `dicominfo_ses-01.tsv` |
| Output folder | Where to save all results (created automatically if it doesn't exist) |

The script finds the `.mat` file automatically: it first checks the filename stored in `pseudotime_mapping.json` (the `reference_mat_file` field), then scans the data folder for any `.mat` file that doesn't have "bold" in its name.

---

## Outputs

Everything is saved inside the output folder (default: `parsed/`):

```
parsed/
├── task-rest_run-01.mat
├── task-rest_run-02.mat
├── task-AP_run-01.mat
├── task-PA_run-01.mat
├── task-BlockStim_run-01.mat
├── task-ContinuousStim_run-01.mat
├── task-FreeBreath_run-01.mat
│   ... (one .mat per matched sequence)
│
├── plots/
│   ├── task-rest_run-01.png
│   ├── task-rest_run-02.png
│   │   ... (one .png per matched sequence)
│
└── unmatched_sequences.log      ← only created if some sequences had no duration match
```

---

## How to run it

### Via the GUI

Go to the **"3 · Parse Segments"** tab, fill in the Data folder and Output folder fields, and click **▶ Run Step 3**.

### From the terminal

```bash
python 3_parse.py /path/to/data /path/to/parsed
```

The first argument is the data folder. The second is the output folder. If the output folder doesn't exist it will be created.

---

## What is inside each output `.mat` file

Each segment `.mat` file contains these variables:

| Variable | Type | Description |
|----------|------|-------------|
| `RESP` | array | Respiration signal for this sequence |
| `RPIEZO` | array | Heart rate signal for this sequence |
| `STIMTRIG` | array | Stimulus trigger signal for this sequence |
| `MRTRIG` | array | MRI trigger signal for this sequence |
| `pseudotime_sec` | float | When this segment starts in the full recording (seconds) |
| `pseudotime_sample` | int | The sample index of the start in the full recording |
| `duration_sec` | float | How many seconds long this segment is |
| `sampling_rate` | int | Always 1000 Hz |

To load one of these files in MATLAB or Python:

**MATLAB:**
```matlab
d = load('task-rest_run-01.mat');
plot(d.MRTRIG)
```

**Python:**
```python
import scipy.io as sio
d = sio.loadmat('task-rest_run-01.mat')
import matplotlib.pyplot as plt
plt.plot(d['MRTRIG'].flatten())
```

---

## What each segment plot shows

Each `.png` in `parsed/plots/` has four panels stacked vertically, one per channel:

- **RESP** (blue) — respiration during the sequence
- **RPIEZO** (red) — heartbeat during the sequence
- **STIMTRIG** (orange) — stimulus triggers during the sequence (flat for rest/field maps)
- **MRTRIG** (green) — MRI triggers during the sequence (regular pulses, one per TR)

The horizontal axis is **time within the segment** in seconds (starting at 0, ending at the sequence duration). This is different from pseudotime — it always starts at 0 for each segment.

The title of each plot shows the sequence name, pseudotime start, and duration.

---

## How it works internally

### 1. Load everything

The script loads the full `.mat` recording into memory (all four channels), loads `pseudotime_mapping.json`, and loads `dicominfo_ses-01.tsv`.

### 2. Match sequences to durations

For each sequence in the mapping, the script searches `dicominfo_ses-01.tsv` for a row whose `time` field matches the sequence's `acq_time` within 5 seconds. If a match is found, the duration is computed from `dim4 × TR` (or the `TR × reps` formula for single-slice sequences).

**If no match is found:** The sequence is added to the unmatched log and skipped entirely. No `.mat` or `.png` is created for it. The log entry explains why the match failed (e.g., "nearest dicominfo row is 8.3 s away (>5 s threshold)").

### 3. Extract each segment

For a matched sequence:
```
start_sample = pseudotime_sample  (from pseudotime_mapping.json)
end_sample   = start_sample + int(duration_sec × 1000)
segment[channel] = channel_data[start_sample : end_sample]
```

The `min(end_sample, len(channel))` guard prevents an out-of-bounds error if a sequence runs close to the end of the recording.

### 4. Save the `.mat` file

The four channel arrays and the metadata fields are saved to a new `.mat` file using `scipy.io.savemat`.

### 5. Save the plot

A 4-panel matplotlib figure is created, saved to PNG at 120 DPI, and closed immediately to free memory. The figure is never displayed on screen.

### 6. Name the output files

The output filename is derived from the BIDS JSON filename by removing the subject/session prefix and the `_bold.json` suffix:

```
sub-7T1911CI071223_ses-01_task-rest_run-01_bold.json
                              ↓
                 task-rest_run-01
```

---

## The unmatched sequences log

If any sequences could not be matched to the dicominfo TSV, a file called `unmatched_sequences.log` is created in the output folder. Example:

```
Sequences skipped (no dicominfo match)
============================================================
sub-7T1911CI071223_ses-01_task-FreeBreath_run-01_bold.json
  reason: nearest dicominfo row is 12.4 s away (>5 s threshold)

sub-7T1911CI071223_ses-01_task-FreeBreath_run-02_bold.json
  reason: nearest dicominfo row is 12.4 s away (>5 s threshold)
```

**Why sequences might be skipped:**
- The `dicominfo_ses-01.tsv` was generated from a different session
- Some sequences share the same `AcquisitionTime` (e.g., multiple runs acquired simultaneously or with the same timestamp) — only the first match is used
- The tolerance of 5 seconds is too tight for sequences with acquisition time delays

---

## What can go wrong

| Problem | Symptom | Cause |
|---------|---------|-------|
| All sequences skipped | Every entry in the log, empty `parsed/` folder | `dicominfo_ses-01.tsv` is missing or from a different session |
| `.mat` file not found | "No .mat or .adicht file found" error | The data folder doesn't contain the physiological recording |
| Short or empty segments | Arrays in the output `.mat` are shorter than expected | The sequence's pseudotime is near the end of the recording |
| Slow run | Normal behavior | Loading 156 MB into RAM and writing 19 output files takes time |
