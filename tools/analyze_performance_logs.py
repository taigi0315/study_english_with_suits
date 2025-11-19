#!/usr/bin/env python3
"""
Analyze performance from LangFlix logs to find bottlenecks.

Usage:
    python tools/analyze_performance_logs.py < logfile.txt
    # Or from clipboard/terminal output
"""

import re
import sys
from datetime import datetime
from collections import defaultdict

def parse_timestamp(log_line):
    """Extract timestamp from log line."""
    match = re.match(r'^(\d{2}:\d{2}:\d{2})', log_line)
    if match:
        time_str = match.group(1)
        return datetime.strptime(time_str, "%H:%M:%S")
    return None

def analyze_logs(lines):
    """Analyze logs and find time spent in each operation."""

    events = []
    current_operation = None

    for line in lines:
        timestamp = parse_timestamp(line)
        if not timestamp:
            continue

        # Look for key operations
        if "Extracting context clip" in line:
            events.append(("start", timestamp, "Context extraction"))
        elif "Extracted context segment" in line:
            events.append(("end", timestamp, "Context extraction"))
        elif "Extracting expression clip" in line:
            events.append(("start", timestamp, "Expression extraction"))
        elif "Expression clip extracted" in line:
            events.append(("end", timestamp, "Expression extraction"))
        elif "Repeating expression clip" in line:
            events.append(("start", timestamp, "Expression repeat"))
        elif "Encoding video" in line and "preset" in line:
            if current_operation != "Concatenating":
                events.append(("encode", timestamp, "FFmpeg encoding pass"))
        elif "Concatenating context + transition" in line or "Concatenating context + expression" in line:
            events.append(("start", timestamp, "Concatenating"))
        elif "Context + expression duration" in line:
            events.append(("end", timestamp, "Concatenating"))
        elif "Creating educational slide" in line:
            events.append(("start", timestamp, "Create slide"))
        elif "Successfully created slide" in line or "Educational slide created" in line:
            events.append(("end", timestamp, "Create slide"))
        elif "Concatenating context+expression → slide" in line:
            events.append(("start", timestamp, "Final concatenation"))
        elif "Adding logo" in line:
            events.append(("end", timestamp, "Final concatenation"))
            events.append(("start", timestamp, "Logo overlay"))
        elif "Failed to add logo" in line or "Applying final audio gain" in line:
            events.append(("end", timestamp, "Logo overlay"))
        elif "Long-form video created:" in line:
            events.append(("end", timestamp, "Total pipeline"))

    # Calculate durations
    operation_times = defaultdict(list)
    encoding_passes = []
    stack = {}

    for event_type, timestamp, operation in events:
        if event_type == "start":
            stack[operation] = timestamp
        elif event_type == "end" and operation in stack:
            start_time = stack.pop(operation)
            duration = (timestamp - start_time).total_seconds()
            operation_times[operation].append(duration)
        elif event_type == "encode":
            encoding_passes.append(timestamp)

    return operation_times, encoding_passes

def print_analysis(operation_times, encoding_passes):
    """Print analysis results."""

    print("\n" + "="*80)
    print(" " * 25 + "PERFORMANCE BOTTLENECK ANALYSIS")
    print("="*80)
    print()

    # Sort by total time spent
    items = []
    total_time = 0

    for operation, durations in operation_times.items():
        total_duration = sum(durations)
        avg_duration = total_duration / len(durations)
        count = len(durations)
        items.append((operation, total_duration, avg_duration, count))
        if operation != "Total pipeline":
            total_time += total_duration

    items.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Operation':<35} {'Total Time':<15} {'Avg Time':<15} {'Count':<10} {'% of Total':<10}")
    print("-" * 90)

    for operation, total_dur, avg_dur, count in items:
        if total_time > 0:
            percentage = (total_dur / total_time) * 100
        else:
            percentage = 0
        print(f"{operation:<35} {total_dur:>6.1f}s {avg_dur:>12.1f}s {count:>8}x {percentage:>8.1f}%")

    print()
    print(f"{'TOTAL (excluding full pipeline)':<35} {total_time:>6.1f}s")

    if encoding_passes:
        print()
        print(f"⚠️  FFmpeg Encoding Passes Detected: {len(encoding_passes)}")
        print("   (Each pass re-encodes the entire video - major performance cost)")

    print()
    print("="*80)
    print()

    # Recommendations
    print("🎯 OPTIMIZATION RECOMMENDATIONS:")
    print()

    for operation, total_dur, avg_dur, count in items[:3]:
        percentage = (total_dur / total_time) * 100 if total_time > 0 else 0
        if percentage > 20:
            print(f"🔴 HIGH PRIORITY: {operation}")
            print(f"   Takes {total_dur:.1f}s ({percentage:.0f}% of total time)")

            if "Concatenat" in operation:
                print(f"   → Use concat demuxer instead of filter concat")
                print(f"   → Potential savings: 50-70% ({total_dur * 0.6:.1f}s)")
            elif "extraction" in operation.lower():
                print(f"   → Enable stream copy mode (no re-encoding)")
                print(f"   → Potential savings: 80-90% ({total_dur * 0.8:.1f}s)")
            elif "slide" in operation.lower():
                print(f"   → Consider caching slides or using lower quality")
            print()

    if len(encoding_passes) > 5:
        print(f"🔴 TOO MANY ENCODING PASSES: {len(encoding_passes)} detected")
        print(f"   Each pass re-encodes the video - very expensive!")
        print(f"   Expected: 4-6 passes | Actual: {len(encoding_passes)} passes")
        print(f"   → Enable concat demuxer to reduce passes")
        print(f"   → Use stream copy when possible")
        print()

def main():
    """Main entry point."""
    if sys.stdin.isatty():
        print("Usage: python analyze_performance_logs.py < logfile.txt")
        print("   Or: paste log content and press Ctrl+D")
        return

    lines = sys.stdin.readlines()

    operation_times, encoding_passes = analyze_logs(lines)

    if not operation_times:
        print("❌ No performance data found in logs")
        print("   Make sure logs contain timestamps and operation messages")
        return

    print_analysis(operation_times, encoding_passes)

if __name__ == "__main__":
    main()
