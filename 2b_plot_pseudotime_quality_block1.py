#!/usr/bin/env python3
"""
Script: 2b_plot_pseudotime_quality_block1.py
Purpose: Visualize the original .mat file (block1 format) with pseudotime acquisition periods labeled.

Block1 format: data_block1 is a (4, N) array.
  Row 0: RESP  |  Row 1: RPIEZO  |  Row 2: STIMTRIG  |  Row 3: MRTRIG

Creates a plot showing:
1. The physiological signals from the original .mat file
2. A timeline bar showing when each sequence was acquired
3. Colored regions for each sequence type
"""

import json
import re
import sys
import os
import scipy.io as sio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from datetime import datetime

def time_to_seconds(time_str):
    """HH:MM:SS.ffffff → total seconds"""
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except:
        return None

def load_mat_data(mat_path, sampling_rate=1000):
    """Load physiological data from a block1-format .mat file."""
    try:
        mat_data = sio.loadmat(mat_path)

        if 'data_block1' not in mat_data:
            print("ERROR: 'data_block1' key not found in this .mat file.")
            print("       This file appears to be in the classic format.")
            print("       Use 2_plot_pseudotime_quality.py instead.")
            return None, None, None

        data_block = mat_data['data_block1']   # shape (4, N)
        channel_names = ['RESP', 'RPIEZO', 'STIMTRIG', 'MRTRIG']
        channels = {name: data_block[i].flatten()
                    for i, name in enumerate(channel_names)}

        n_samples   = data_block.shape[1]
        time_vector = np.arange(n_samples) / sampling_rate

        return channels, time_vector, mat_data

    except Exception as e:
        print(f"ERROR loading .mat file: {e}")
        return None, None, None

def load_pseudotime_mapping(json_path):
    """Load pseudotime mapping from JSON"""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading pseudotime mapping: {e}")
        return None

# ── series_description → BIDS task name ───────────────────────────────────────
_TASK_PATTERNS = [
    (re.compile(r'REST_ep2d',      re.IGNORECASE), 'rest'),
    (re.compile(r'ContinuousStim', re.IGNORECASE), 'ContinuousStim'),
    (re.compile(r'BlockStim',      re.IGNORECASE), 'BlockStim'),
    (re.compile(r'TOPUP_AP',       re.IGNORECASE), 'AP'),
    (re.compile(r'TOPUP_PA',       re.IGNORECASE), 'PA'),
    (re.compile(r'FreeBreathe',    re.IGNORECASE), 'FreeBreath'),
    (re.compile(r'PaceBreathe',    re.IGNORECASE), 'PaceBreath'),
    (re.compile(r'BEAT_1p6',       re.IGNORECASE), 'BEAT'),
]

def _series_desc_to_task(series_desc):
    for pattern, task in _TASK_PATTERNS:
        if pattern.search(series_desc):
            return task
    return None


def _tr_from_json(fname, data_dir):
    """Read RepetitionTime from the BIDS JSON sidecar for this sequence."""
    if not data_dir:
        return None
    path = os.path.join(data_dir, fname)
    try:
        with open(path) as f:
            return json.load(f).get('RepetitionTime')
    except Exception:
        return None


def load_dicominfo_durations(dicominfo_path, pseudotime_mapping, data_dir=None):
    """
    Compute duration for each sequence by matching JSON filenames
    (task + run number) to dicominfo rows via series_description.

    Matching rules:
      - series_description prefix → BIDS task name  (see _TASK_PATTERNS)
      - first occurrence of a task in TSV row order → run-01, second → run-02, …

    Duration priority:
      1. dim4 × TR          — when heudiconv correctly populated both fields
      2. reps × TR_ms/1000  — single-slice sequences with explicit name encoding
      3. series_files × TR  — TR read from BIDS JSON sidecar (handles dim4=1 / TR=-1)

    Returns dict: json_file -> duration_sec
    """
    if not os.path.exists(dicominfo_path):
        print(f"WARNING: dicominfo not found at {dicominfo_path} — using 120s fallback")
        return {k: 120.0 for k in pseudotime_mapping}

    with open(dicominfo_path) as f:
        lines = f.readlines()
    header = lines[0].strip().split('\t')

    # Build (task, run_number) → row, using TSV row order for run numbering
    task_run_rows    = {}
    task_run_counter = {}
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < len(header):
            continue
        row  = dict(zip(header, parts))
        task = _series_desc_to_task(row.get('series_description', ''))
        if task is None:
            continue
        run = task_run_counter.get(task, 0) + 1
        task_run_counter[task] = run
        task_run_rows[(task, run)] = row

    def _duration(row, fname):
        dim4 = int(row['dim4'])
        tr   = float(row['TR'])
        name = row.get('series_description', '')

        # 1. heudiconv gave valid dim4 and TR
        if dim4 > 1 and tr > 0:
            return dim4 * tr

        # 2. single-slice sequence with TR and reps encoded in series name
        tr_m  = re.search(r'TR(\d+)ms',  name, re.IGNORECASE)
        rep_m = re.search(r'(\d+)reps',  name, re.IGNORECASE)
        if tr_m and rep_m:
            return int(rep_m.group(1)) * int(tr_m.group(1)) / 1000.0

        # 3. series_files × TR from BIDS JSON sidecar
        try:
            n_vols = int(row.get('series_files', 0))
        except (ValueError, TypeError):
            n_vols = 0
        tr_json = _tr_from_json(fname, data_dir)
        if n_vols > 0 and tr_json and tr_json > 0:
            return n_vols * tr_json

        raise ValueError(
            f"cannot determine duration — "
            f"dim4={dim4}, TR={tr}, series_files={row.get('series_files')}, "
            f"TR_json={tr_json}")

    durations = {}
    for fname in pseudotime_mapping:
        m = re.search(r'task-(\w+)_run-(\d+)', fname)
        if not m:
            durations[fname] = 120.0
            continue
        task = m.group(1)
        run  = int(m.group(2))
        row  = task_run_rows.get((task, run))
        if row is None:
            print(f"  WARNING: no dicominfo row for task-{task} run-{run:02d} — using 120s fallback")
            durations[fname] = 120.0
        else:
            try:
                durations[fname] = _duration(row, fname)
            except Exception as e:
                print(f"  WARNING: duration failed for {fname}: {e} — using 120s fallback")
                durations[fname] = 120.0

    return durations

def group_sequences(pseudotime_mapping):
    """Group sequences by task type and get start/end times"""
    sequences = {}

    for json_file, timing_info in pseudotime_mapping['pseudotime_mapping'].items():
        # Extract task name
        if 'task-' in json_file:
            task = json_file.split('task-')[1].split('_run')[0]
            run = json_file.split('_run-')[1].split('_')[0] if '_run-' in json_file else '01'

            if task not in sequences:
                sequences[task] = []

            sequences[task].append({
                'run': run,
                'pseudotime': timing_info['pseudotime_sec'],
                'acq_time': timing_info['acq_time'],
                'json': json_file
            })

    # Sort by pseudotime within each task
    for task in sequences:
        sequences[task].sort(key=lambda x: x['pseudotime'])

    return sequences

def create_visualization(mat_path, json_path, output_path):
    """Create the visualization"""

    print("Loading data...")
    channels, time_vector, mat_info = load_mat_data(mat_path)
    if channels is None:
        return False

    mapping = load_pseudotime_mapping(json_path)
    if mapping is None:
        return False

    sequences = group_sequences(mapping)
    data_dir       = os.path.dirname(os.path.abspath(json_path))
    dicominfo_path = os.path.join(data_dir, 'dicominfo_ses-01.tsv')
    durations = load_dicominfo_durations(dicominfo_path, mapping['pseudotime_mapping'], data_dir)

    print(f"\nLoaded {len(channels)} physiological channels")
    print(f"Total recording duration: {len(time_vector)/60:.1f} minutes ({len(time_vector):.0f} seconds)")
    print(f"Found {sum(len(runs) for runs in sequences.values())} sequences across {len(sequences)} tasks")

    # Create figure with multiple subplots
    fig = plt.figure(figsize=(18, 15))

    # Main signal plot
    ax1 = plt.subplot(5, 1, 1)
    ax2 = plt.subplot(5, 1, 2)
    ax3 = plt.subplot(5, 1, 3)
    ax4 = plt.subplot(5, 1, 4)
    ax_timeline = plt.subplot(5, 1, 5)

    # Plot physiological signals
    print("\nPlotting physiological signals...")

    # RESP channel
    if 'RESP' in channels:
        resp = channels['RESP']
        resp_time = np.arange(len(resp)) / 1000
        ax1.plot(resp_time, resp, linewidth=0.5, color='blue', alpha=0.7)
        ax1.set_ylabel('RESP', fontsize=10, fontweight='bold')
        ax1.set_xlim(0, len(time_vector) / 1000)
        ax1.grid(True, alpha=0.3)
        ax1.set_title('Physiological Recording Timeline with Sequence Acquisitions', fontsize=14, fontweight='bold')

    # RPIEZO (heart rate) channel
    if 'RPIEZO' in channels:
        piezo = channels['RPIEZO']
        piezo_time = np.arange(len(piezo)) / 1000
        ax2.plot(piezo_time, piezo, linewidth=0.5, color='red', alpha=0.7)
        ax2.set_ylabel('RPIEZO\n(Heart Rate)', fontsize=10, fontweight='bold')
        ax2.set_xlim(0, len(time_vector) / 1000)
        ax2.grid(True, alpha=0.3)

    # STIMTRIG channel
    if 'STIMTRIG' in channels:
        stimtrig = channels['STIMTRIG']
        stimtrig_time = np.arange(len(stimtrig)) / 1000
        ax3.plot(stimtrig_time, stimtrig, linewidth=0.5, color='orange', alpha=0.7)
        ax3.set_ylabel('STIMTRIG\n(Stimulus)', fontsize=10, fontweight='bold')
        ax3.set_xlim(0, len(time_vector) / 1000)
        ax3.grid(True, alpha=0.3)

    # MRTRIG channel
    if 'MRTRIG' in channels:
        mrtrig = channels['MRTRIG']
        mrtrig_time = np.arange(len(mrtrig)) / 1000
        ax4.plot(mrtrig_time, mrtrig, linewidth=0.5, color='green', alpha=0.7)
        ax4.set_ylabel('MRTRIG\n(MRI Trigger)', fontsize=10, fontweight='bold')
        ax4.set_xlim(0, len(time_vector) / 1000)
        ax4.grid(True, alpha=0.3)

    # Timeline with acquisition periods
    print("Plotting acquisition timeline...")

    # Color map for different task types
    colors = {
        'rest': '#1f77b4',          # blue
        'BlockStim': '#ff7f0e',     # orange
        'ContinuousStim': '#2ca02c', # green
        'AP': '#d62728',            # red
        'PA': '#9467bd',            # purple
        'FreeBreath': '#8c564b',    # brown
        'PaceBreath': '#e377c2'     # pink
    }

    # Plot timeline bars
    y_pos = 0
    task_positions = {}
    max_pseudotime = max(max(seq['pseudotime'] for seq in runs)
                         for runs in sequences.values())

    for task in sorted(sequences.keys()):
        task_positions[task] = y_pos
        color = colors.get(task, '#999999')

        for seq in sequences[task]:
            duration = durations.get(seq['json'], 120)

            rect = Rectangle((seq['pseudotime'], y_pos - 0.3),
                            duration, 0.6,
                            linewidth=1, edgecolor='black',
                            facecolor=color, alpha=0.7)
            ax_timeline.add_patch(rect)

            # Add label
            label = f"{task} (run-{seq['run']})"
            ax_timeline.text(seq['pseudotime'] + duration/2, y_pos, label,
                           ha='center', va='center', fontsize=8, fontweight='bold')

        y_pos += 1

    max_end = max(
        seq['pseudotime'] + durations.get(seq['json'], 120)
        for runs in sequences.values() for seq in runs
    )
    ax_timeline.set_xlim(0, max_end + 60)
    ax_timeline.set_ylim(-0.5, y_pos + 0.5)
    ax_timeline.set_xlabel('Pseudotime (seconds)', fontsize=11, fontweight='bold')
    ax_timeline.set_ylabel('Sequence', fontsize=10, fontweight='bold')
    ax_timeline.set_yticks(list(task_positions.values()))
    ax_timeline.set_yticklabels(list(task_positions.keys()))
    ax_timeline.grid(True, alpha=0.3, axis='x')
    ax_timeline.set_title('Acquisition Timeline (Relative to First BOLD)', fontsize=11, fontweight='bold')

    # Add legend
    legend_patches = [mpatches.Patch(color=color, label=task, alpha=0.7)
                     for task, color in colors.items() if task in sequences]
    ax_timeline.legend(handles=legend_patches, loc='upper right', fontsize=9)

    # Connect time axes for reference
    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_xlabel('')
    ax4.set_xlabel('Time in Recording (seconds)', fontsize=11, fontweight='bold')

    plt.tight_layout()

    # Save figure
    print(f"\nSaving visualization to: {output_path}")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print("✓ Visualization saved!")

    # Create a summary statistics figure
    fig2, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig2.suptitle('Acquisition Summary Statistics', fontsize=14, fontweight='bold')

    # Plot 1: Sequence count by task
    ax = axes[0, 0]
    task_counts = {task: len(runs) for task, runs in sequences.items()}
    tasks = list(task_counts.keys())
    counts = list(task_counts.values())
    colors_list = [colors.get(task, '#999999') for task in tasks]
    ax.bar(tasks, counts, color=colors_list, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Number of Runs', fontsize=10, fontweight='bold')
    ax.set_title('Sequences per Task', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, (task, count) in enumerate(zip(tasks, counts)):
        ax.text(i, count + 0.1, str(count), ha='center', fontweight='bold')

    # Plot 2: Timeline distribution
    ax = axes[0, 1]
    pseudo_times = []
    pseudo_labels = []
    for task in sorted(sequences.keys()):
        for seq in sequences[task]:
            pseudo_times.append(seq['pseudotime'])
            pseudo_labels.append(f"{task}\n(run-{seq['run']})")

    colors_timeline = [colors.get(label.split('\n')[0], '#999999') for label in pseudo_labels]
    ax.scatter(pseudo_times, range(len(pseudo_times)), c=colors_timeline, s=100, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Pseudotime (seconds)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Sequence Index', fontsize=10, fontweight='bold')
    ax.set_title('Temporal Distribution of Acquisitions', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Plot 3: Signal overview (raw counts)
    ax = axes[1, 0]
    channel_lengths = [(name, len(ch)) for name, ch in channels.items()]
    ch_names = [name for name, _ in channel_lengths]
    ch_lengths = [length/1000 for _, length in channel_lengths]  # Convert to seconds
    ax.barh(ch_names, ch_lengths, color=['blue', 'red', 'orange', 'green'], alpha=0.7, edgecolor='black')
    ax.set_xlabel('Duration (seconds)', fontsize=10, fontweight='bold')
    ax.set_title('Physiological Channel Durations', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    for i, (name, duration) in enumerate(zip(ch_names, ch_lengths)):
        ax.text(duration + 50, i, f'{duration:.0f}s', va='center', fontweight='bold')

    # Plot 4: Pseudotime statistics
    ax = axes[1, 1]
    ax.axis('off')

    anchor       = mapping.get('anchor', {})
    anchor_time  = anchor.get('real_time', 'N/A')
    anchor_ptime = anchor.get('first_trigger_pseudotime_sec', 'N/A')
    n_triggers   = mapping.get('total_triggers', 'N/A')

    stats_text = f"""
    PSEUDOTIME STATISTICS

    Anchor: task-rest_run-01
      Real time:      {anchor_time}
      Pseudotime:     {anchor_ptime:.3f} s

    Total Sequences: {len(pseudo_times)}
    Total Tasks: {len(sequences)}

    Pseudotime Range:
      Min: {min(pseudo_times):.1f} s
      Max: {max(pseudo_times):.1f} s
      Range: {max(pseudo_times) - min(pseudo_times):.1f} s

    Physiological Recording:
      Duration: {len(time_vector)/60:.1f} minutes
      Sampling Rate: 1000 Hz
      Total Triggers: {n_triggers}
    """

    ax.text(0.1, 0.9, stats_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save statistics figure
    stats_path = output_path.replace('.png', '_stats.png')
    print(f"Saving statistics to: {stats_path}")
    plt.savefig(stats_path, dpi=150, bbox_inches='tight')
    print("✓ Statistics figure saved!")

    return True

DATA_DIR   = '/Users/mariomjr/Desktop/pseudotime/data'
OUTPUT_DIR = '/Users/mariomjr/Desktop/pseudotime/data/qc_images'

def main():
    if len(sys.argv) >= 4:
        mat_file    = sys.argv[1]
        json_file   = sys.argv[2]
        output_file = sys.argv[3]
    else:
        mat_file    = os.path.join(DATA_DIR,   'subject_sample.mat')
        json_file   = os.path.join(DATA_DIR,   'pseudotime_mapping.json')
        output_file = os.path.join(OUTPUT_DIR, 'pseudotime_plot.png')
        print(f"No arguments supplied — using defaults:")
        print(f"  MAT:    {mat_file}")
        print(f"  JSON:   {json_file}")
        print(f"  Output: {output_file}")
        print()

    # Verify files exist
    if not os.path.exists(mat_file):
        print(f"ERROR: MAT file not found: {mat_file}")
        sys.exit(1)

    if not os.path.exists(json_file):
        print(f"ERROR: JSON mapping not found: {json_file}")
        sys.exit(1)

    print("="*60)
    print("Pseudotime Quality Visualization")
    print("="*60)

    success = create_visualization(mat_file, json_file, output_file)

    if success:
        print("\n" + "="*60)
        print("✓ Visualization complete!")
        print("="*60)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()