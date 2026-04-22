#!/usr/bin/env python3
"""
Script: 3_parse.py
Purpose: Parse the .mat file into per-sequence segments using pseudotime_mapping.json.

For each sequence:
  - Extracts the 4 channels (RESP, RPIEZO, STIMTRIG, MRTRIG) for that time window
  - Saves the segment as a .mat file
  - Saves a 4-panel plot of the segment

Source file discovery (DATA_DIR):
  1. Uses the filename recorded in pseudotime_mapping.json ("reference_mat_file").
  2. If not found, falls back to any *.mat in DATA_DIR (excluding per-sequence bold.mat files).
  3. If still not found but a *.adicht exists, exits with an informative message —
     adi-reader only ships Windows DLLs and cannot be used on macOS/Linux.

Sequences with no matching dicominfo row are skipped and written to
parsed/unmatched_sequences.log instead of receiving a 120 s fallback.
"""

import glob
import json
import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR   = '/Users/mariomjr/Desktop/pseudotime/data'
OUTPUT_DIR = '/Users/mariomjr/Desktop/pseudotime/parsed'
JSON_FILE  = os.path.join(DATA_DIR, 'pseudotime_mapping.json')
TSV_FILE   = os.path.join(DATA_DIR, 'dicominfo_ses-01.tsv')
LOG_FILE   = os.path.join(OUTPUT_DIR, 'unmatched_sequences.log')

CHANNEL_NAMES  = ['RESP', 'RPIEZO', 'STIMTRIG', 'MRTRIG']
CHANNEL_COLORS = {'RESP': 'blue', 'RPIEZO': 'red', 'STIMTRIG': 'orange', 'MRTRIG': 'green'}
FS = 1000  # Hz


# ── Source file discovery ──────────────────────────────────────────────────────

def find_source_file(data_dir, mapping):
    """
    Return the path to the full-session .mat file, or exit with an error.

    Search order:
      1. The filename stored in mapping['reference_mat_file'].
      2. Any *.mat in data_dir that is NOT a per-sequence bold.mat.
      3. If only *.adicht files exist, exit with an explanation.
    """
    # 1. Try the filename recorded in the JSON
    ref = mapping.get('reference_mat_file', '')
    if ref:
        candidate = os.path.join(data_dir, ref)
        if os.path.exists(candidate):
            return candidate

    # 2. Glob for any .mat that isn't a BIDS bold file
    mats = [
        p for p in glob.glob(os.path.join(data_dir, '*.mat'))
        if 'bold' not in os.path.basename(p).lower()
    ]
    if mats:
        if len(mats) > 1:
            print(f"WARNING: multiple .mat files found; using {os.path.basename(mats[0])}")
        return mats[0]

    # 3. Check for .adicht and give an informative error
    adichts = glob.glob(os.path.join(data_dir, '*.adicht'))
    if adichts:
        names = [os.path.basename(p) for p in adichts]
        print(f"ERROR: Found {names} but no .mat file.")
        print("       adi-reader only ships Windows DLLs — .adicht cannot be read on macOS/Linux.")
        print("       Export the file to .mat from LabChart on Windows, then re-run.")
        sys.exit(1)

    print(f"ERROR: No .mat or .adicht file found in {data_dir}")
    sys.exit(1)


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_channels(mat_path):
    """Return dict {name: np.ndarray} for all 4 channels."""
    mat       = sio.loadmat(mat_path)
    data      = mat['data'].flatten()
    datastart = mat['datastart'].flatten().astype(int)
    dataend   = mat['dataend'].flatten().astype(int)

    channels = {}
    for i, name in enumerate(CHANNEL_NAMES):
        channels[name] = data[datastart[i] - 1 : dataend[i]]  # MATLAB 1-indexed
    return channels


def load_mapping(json_path):
    with open(json_path) as f:
        return json.load(f)


def load_durations(tsv_path, pseudotime_mapping):
    """
    Match each JSON sequence to a dicominfo row by AcquisitionTime and return
    its duration in seconds.

    Returns:
        durations : dict  { json_fname -> float }   (only matched sequences)
        unmatched : list  [ (json_fname, reason) ]
    """
    unmatched = []

    if not os.path.exists(tsv_path):
        reason = "dicominfo TSV not found"
        for fname in pseudotime_mapping:
            unmatched.append((fname, reason))
        return {}, unmatched

    with open(tsv_path) as f:
        lines = f.readlines()
    header = lines[0].strip().split('\t')

    series = []
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < len(header):
            continue
        row = dict(zip(header, parts))
        t = row.get('time', '')
        if t in ('None', ''):
            continue
        try:
            t_part, frac = (t.split('.') + ['0'])[:2]
            if len(t_part) == 6:
                hh, mm, ss = int(t_part[0:2]), int(t_part[2:4]), int(t_part[4:6])
                row['time_sec'] = hh * 3600 + mm * 60 + ss + float('0.' + frac)
                series.append(row)
        except Exception:
            pass

    def _duration(row):
        dim4 = int(row['dim4'])
        tr   = float(row['TR'])
        name = row.get('series_description', '')
        if dim4 > 1:
            return dim4 * tr
        tr_m  = re.search(r'TR(\d+)ms',  name, re.IGNORECASE)
        rep_m = re.search(r'(\d+)reps',  name, re.IGNORECASE)
        if tr_m and rep_m:
            return int(rep_m.group(1)) * int(tr_m.group(1)) / 1000.0
        dim3 = int(row['dim3'])
        return max(dim3, dim4) * tr

    def _acq_sec(time_str):
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)

    durations = {}
    for fname, info in pseudotime_mapping.items():
        try:
            acq = _acq_sec(info['acq_time'])
        except Exception:
            unmatched.append((fname, f"could not parse acq_time '{info.get('acq_time')}'"))
            continue

        if not series:
            unmatched.append((fname, "dicominfo has no parseable rows"))
            continue

        best = min(series, key=lambda r: abs(r['time_sec'] - acq))
        gap  = abs(best['time_sec'] - acq)
        if gap > 5:
            unmatched.append((fname, f"nearest dicominfo row is {gap:.1f} s away (>{5} s threshold)"))
        else:
            try:
                durations[fname] = _duration(best)
            except Exception as e:
                unmatched.append((fname, f"duration calculation failed: {e}"))

    return durations, unmatched


# ── Segment extractor ─────────────────────────────────────────────────────────

def extract_segment(channels, start_sample, duration_sec):
    """Slice each channel from start_sample for duration_sec seconds."""
    n_samples = int(duration_sec * FS)
    segment = {}
    for name, data in channels.items():
        end = min(start_sample + n_samples, len(data))
        segment[name] = data[start_sample:end]
    return segment


# ── Plot ──────────────────────────────────────────────────────────────────────

def plot_segment(segment, title, plot_path):
    fig, axes = plt.subplots(4, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(title, fontsize=13, fontweight='bold')

    for ax, name in zip(axes, CHANNEL_NAMES):
        sig = segment.get(name, np.array([]))
        t   = np.arange(len(sig)) / FS
        ax.plot(t, sig, linewidth=0.6, color=CHANNEL_COLORS[name])
        ax.set_ylabel(name, fontsize=9, fontweight='bold')
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Time within segment (s)', fontsize=10)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=120, bbox_inches='tight')
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Allow overriding paths via CLI: python 3_parse.py <data_dir> <output_dir>
    data_dir   = sys.argv[1] if len(sys.argv) > 1 else DATA_DIR
    output_dir = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_DIR
    json_file  = os.path.join(data_dir, 'pseudotime_mapping.json')
    tsv_file   = os.path.join(data_dir, 'dicominfo_ses-01.tsv')
    log_file   = os.path.join(output_dir, 'unmatched_sequences.log')

    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)

    print("Loading pseudotime mapping …")
    mapping   = load_mapping(json_file)
    pseud_map = mapping['pseudotime_mapping']

    mat_file = find_source_file(data_dir, mapping)
    print(f"Loading {os.path.basename(mat_file)} …")
    channels = load_channels(mat_file)
    for name, ch in channels.items():
        print(f"  {name}: {len(ch)} samples ({len(ch)/FS:.1f} s)")
    print()

    print("Matching sequences to dicominfo …")
    durations, unmatched = load_durations(tsv_file, pseud_map)

    # Write unmatched log
    if unmatched:
        with open(log_file, 'w') as log:
            log.write("Sequences skipped (no dicominfo match)\n")
            log.write("=" * 60 + "\n")
            for fname, reason in unmatched:
                log.write(f"{fname}\n  reason: {reason}\n\n")
        print(f"  {len(unmatched)} sequence(s) unmatched — see {log_file}")

    matched = {k: v for k, v in pseud_map.items() if k in durations}
    print(f"  {len(matched)} / {len(pseud_map)} sequences matched\n")

    print(f"Parsing {len(matched)} sequences …\n")

    for json_fname, info in sorted(matched.items(), key=lambda x: x[1]['pseudotime_sec']):
        start_sample = info['pseudotime_sample']
        duration_sec = durations[json_fname]

        # Short output stem: drop subject/session prefix and _bold.json suffix
        stem = (json_fname
                .replace('_bold.json', '')
                .replace('sub-7T1911CI071223_ses-01_', ''))

        print(f"  {stem}")
        print(f"    pseudotime: {info['pseudotime_sec']:.3f} s  |  "
              f"start sample: {start_sample}  |  duration: {duration_sec:.1f} s")

        segment = extract_segment(channels, start_sample, duration_sec)

        # Save .mat
        mat_out   = os.path.join(output_dir, f'{stem}.mat')
        save_dict = {name: seg for name, seg in segment.items()}
        save_dict['pseudotime_sec']    = info['pseudotime_sec']
        save_dict['pseudotime_sample'] = start_sample
        save_dict['duration_sec']      = duration_sec
        save_dict['sampling_rate']     = FS
        sio.savemat(mat_out, save_dict)

        # Save plot
        title     = f"{stem}  |  pseudotime {info['pseudotime_sec']:.1f} s  |  dur {duration_sec:.1f} s"
        plot_path = os.path.join(plots_dir, f'{stem}.png')
        plot_segment(segment, title, plot_path)

        print(f"    saved → {os.path.basename(mat_out)}  +  plots/{os.path.basename(plot_path)}")

    print(f"\nDone. {len(matched)} segments saved to {output_dir}/")
    if unmatched:
        print(f"       {len(unmatched)} skipped — see {log_file}")


if __name__ == '__main__':
    main()
