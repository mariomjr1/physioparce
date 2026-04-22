#!/usr/bin/env python3
"""
Script: 2_plot_pseudotime_quality.py
Purpose: Visualize the original .mat file with pseudotime acquisition periods labeled

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
    """Load physiological data from .mat file"""
    try:
        mat_data = sio.loadmat(mat_path)

        if 'data' in mat_data and 'datastart' in mat_data and 'dataend' in mat_data:
            data = mat_data['data'].flatten()
            datastart = mat_data['datastart'].flatten().astype(int)
            dataend = mat_data['dataend'].flatten().astype(int)

            # Extract all 4 channels
            channels = {}
            channel_names = ['RESP', 'RPIEZO', 'STIMTRIG', 'MRTRIG']

            for i, name in enumerate(channel_names):
                if i < len(datastart) and i < len(dataend):
                    channels[name] = data[datastart[i]-1:dataend[i]]  # MATLAB 1-indexed

            # Time vector in seconds
            max_length = max(len(ch) for ch in channels.values())
            time_vector = np.arange(max_length) / sampling_rate

            return channels, time_vector, mat_data
        else:
            print("ERROR: Required data not found in .mat file")
            return None, None, None

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

def load_dicominfo_durations(dicominfo_path, pseudotime_mapping):
    """
    For each JSON sequence, find its matching series in dicominfo by AcquisitionTime,
    then compute duration:
      - Multi-volume BOLD (dim4 > 1): dim4 * TR
      - Single-slice 2D (e.g. FreeBreath/PaceBreath): parse n_reps and TR_ms from
        the series_description name (e.g. "TR1210ms_250reps"), because the DICOM
        TR field reflects per-slice readout time, not the volume repetition period.
    Returns dict: json_file -> duration_sec
    """
    if not os.path.exists(dicominfo_path):
        print(f"WARNING: dicominfo not found at {dicominfo_path} — using 120s fallback")
        return {k: 120.0 for k in pseudotime_mapping}

    series = []
    with open(dicominfo_path) as f:
        lines = f.readlines()
    header = lines[0].strip().split('\t')

    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < len(header):
            continue
        row = dict(zip(header, parts))
        t = row.get('time', 'None')
        if t in ('None', ''):
            continue
        try:
            t_part, frac = (t.split('.') + ['0'])[:2]
            if len(t_part) == 6:
                hh, mm, ss = int(t_part[0:2]), int(t_part[2:4]), int(t_part[4:6])
                row['time_sec'] = hh * 3600 + mm * 60 + ss + float('0.' + frac)
                series.append(row)
        except:
            pass

    def series_duration(row):
        try:
            dim4 = int(row['dim4'])
            tr   = float(row['TR'])
            name = row.get('series_description', '')
            if dim4 > 1:
                return dim4 * tr
            # Single-slice: extract actual TR and rep count from series name
            tr_m  = re.search(r'TR(\d+)ms',  name, re.IGNORECASE)
            rep_m = re.search(r'(\d+)reps',  name, re.IGNORECASE)
            if tr_m and rep_m:
                return int(rep_m.group(1)) * int(tr_m.group(1)) / 1000.0
            # Fallback: use dim3 or dim4 whichever is larger
            dim3 = int(row['dim3'])
            return max(dim3, dim4) * tr
        except:
            return 120.0

    durations = {}
    for fname, info in pseudotime_mapping.items():
        acq_sec = time_to_seconds(info['acq_time'])
        if acq_sec is None or not series:
            durations[fname] = 120.0
            continue
        best = min(series, key=lambda r: abs(r['time_sec'] - acq_sec))
        if abs(best['time_sec'] - acq_sec) > 5:
            print(f"  WARNING: no close dicominfo match for {fname} (nearest gap "
                  f"{abs(best['time_sec'] - acq_sec):.1f}s) — using 120s fallback")
            durations[fname] = 120.0
        else:
            durations[fname] = series_duration(best)

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
    dicominfo_path = os.path.join(os.path.dirname(os.path.abspath(json_path)),
                                  'dicominfo_ses-01.tsv')
    durations = load_dicominfo_durations(dicominfo_path, mapping['pseudotime_mapping'])

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
