#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DShotDecoder - Logic Analyzer Dshot Signal Decoder
This script parses Dshot signal data exported from a logic analyzer.

Key Features:
1. Multi-rate Auto-detection: Identifies the Dshot speed (Dshot1200, Dshot600,
   Dshot300, or Dshot150) by analyzing the physical widths of the first few high-level pulses.
2. Dynamic Decision Boundary: Calculates T_bit and sets 0.6 * T_bit as the
   decision boundary between logic "0" and "1".
3. Adaptive CSV Loader:
   - Supports 2-column format: [Timestamp (s or ns), Pin state (0 or 1)]. Timestamps
     in seconds are automatically converted to nanoseconds.
   - Supports 1-column format: [Pin state (0 or 1)]. Relative timestamps are generated
     based on the sample rate (default 100MHz / 10ns period).
4. Frame Slicing: Uses inter-frame gap thresholding to group bits into 16-bit frames.
5. Standard CRC Verification: Performs Dshot 4-bit CRC checks on each frame.
"""

import csv
import sys
import argparse
import statistics

# Standard Dshot speed specifications in nanoseconds (ns)
DSHOT_SPECS = {
    "Dshot1200": {
        "bit_period": 833.0,
        "w0": 313.0,    # Nominal high width for logic '0'
        "w1": 625.0,    # Nominal high width for logic '1'
    },
    "Dshot600": {
        "bit_period": 1667.0,
        "w0": 625.0,
        "w1": 1250.0,
    },
    "Dshot300": {
        "bit_period": 3333.0,
        "w0": 1250.0,
        "w1": 2500.0,
    },
    "Dshot150": {
        "bit_period": 6667.0,
        "w0": 2500.0,
        "w1": 5000.0,
    }
}

class DShotDecoder:
    def __init__(self, filepath, sample_rate_hz=100e6):
        """
        Initialize the decoder.
        :param filepath: Path to the input CSV file.
        :param sample_rate_hz: Sample rate in Hz, used for single-column CSVs.
        """
        self.filepath = filepath
        self.sample_rate_hz = sample_rate_hz
        self.sample_period_ns = (1.0 / sample_rate_hz) * 1e9
        
        # Raw data: list of tuples (timestamp_ns, state)
        self.data = []
        # Detected edges: list of dicts {'type': 'rising'/'falling', 'time_ns': float, 'index': int}
        self.transitions = []
        # Extracted high-level pulses: list of dicts {'rising_time': float, 'falling_time': float, 'width_ns': float, 'low_duration_ns': float}
        self.pulses = []
        
        # Identified protocol attributes
        self.protocol = None
        self.bit_period_ns = 0.0
        self.threshold_ns = 0.0

    def load_data(self):
        """
        Load and parse the CSV file. Detects single vs multi-column formats.
        """
        print("[System] Loading data from file...")
        raw_rows = []
        
        with open(self.filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                first_row = next(reader)
            except StopIteration:
                print("[Error] CSV file is empty.")
                sys.exit(1)
            
            # Heuristic to check if first row is a header
            def is_header(row):
                for cell in row:
                    try:
                        float(cell.strip())
                    except ValueError:
                        return True
                return False
            
            header = None
            if is_header(first_row):
                header = first_row
                print(f"[System] Found CSV Header: {header}")
            else:
                raw_rows.append(first_row)
                
            for row in reader:
                if not row or all(cell.strip() == '' for cell in row):
                    continue
                raw_rows.append(row)
                
        if not raw_rows:
            print("[Error] No data rows found in CSV.")
            sys.exit(1)
            
        num_cols = len(raw_rows[0])
        has_timestamp = (num_cols >= 2)
        
        if has_timestamp:
            print(f"[System] Data contains {num_cols} columns. Using 1st column as timestamp, 2nd column as GPIO state.")
        else:
            print(f"[System] Data contains 1 column. Using implicit sample rate {self.sample_rate_hz / 1e6:.1f} MHz (period {self.sample_period_ns:.2f} ns).")
            
        timestamps = []
        states = []
        
        for idx, row in enumerate(raw_rows):
            try:
                if has_timestamp:
                    t_val = float(row[0].strip())
                    s_val = int(float(row[1].strip()))
                    timestamps.append(t_val)
                    states.append(s_val)
                else:
                    s_val = int(float(row[0].strip()))
                    states.append(s_val)
            except ValueError:
                # Ignore non-numeric rows or headers
                continue
                
        # Convert timestamps unit if they are in seconds
        if has_timestamp:
            max_t = max(timestamps)
            if max_t < 1.0:
                print("[System] Auto-converted timestamps from seconds to nanoseconds (multiplied by 1e9).")
                timestamps = [t * 1e9 for t in timestamps]
            self.data = list(zip(timestamps, states))
        else:
            # Single-column: generate relative timestamps
            timestamps = [i * self.sample_period_ns for i in range(len(states))]
            self.data = list(zip(timestamps, states))
            
        print(f"[System] Loaded {len(self.data)} samples.")

    def extract_transitions(self):
        """
        Identify rising and falling edges, computing high-pulse widths and low intervals.
        """
        print("[System] Analyzing signal transitions (edge detection)...")
        transitions = []
        
        # Scan for state changes
        for i in range(1, len(self.data)):
            prev_t, prev_s = self.data[i-1]
            curr_t, curr_s = self.data[i]
            if prev_s != curr_s:
                edge_type = "rising" if curr_s == 1 else "falling"
                transitions.append({
                    'type': edge_type,
                    'time_ns': curr_t,
                    'index': i,
                    'state': curr_s
                })
                
        # If the signal ends while high, append a virtual falling edge at the last sample
        if self.data and self.data[-1][1] == 1:
            transitions.append({
                'type': 'falling',
                'time_ns': self.data[-1][0],
                'index': len(self.data) - 1,
                'state': 0
            })

        self.transitions = transitions
        print(f"[System] Detected {len(transitions)} edge transitions (including virtual edges if any).")
        
        # Match rising and falling edges to measure high pulse widths and subsequent low periods
        pulses = []
        for i in range(len(transitions) - 1):
            curr = transitions[i]
            nxt = transitions[i+1]
            if curr['type'] == 'rising' and nxt['type'] == 'falling':
                rising_time = curr['time_ns']
                falling_time = nxt['time_ns']
                width_ns = falling_time - rising_time
                
                # Determine the low period duration following this pulse (until the next rising edge)
                low_duration_ns = float('inf')
                for j in range(i + 2, len(transitions)):
                    if transitions[j]['type'] == 'rising':
                        low_duration_ns = transitions[j]['time_ns'] - falling_time
                        break
                        
                pulses.append({
                    'rising_time': rising_time,
                    'falling_time': falling_time,
                    'width_ns': width_ns,
                    'low_duration_ns': low_duration_ns
                })
                
        self.pulses = pulses
        print(f"[System] Extracted {len(pulses)} high-level pulses.")

    def detect_protocol(self):
        """
        Identify the Dshot speed by mapping observed pulse widths to standard values
        using nearest-centroid classification. Sets the dynamic decision boundary.
        """
        print("[System] Analyzing signal headers...")
        if not self.pulses:
            print("[Error] No high-level pulses detected to perform rate auto-identification.")
            sys.exit(1)
            
        # Analyze first 5-10 high pulses
        sample_size = min(10, len(self.pulses))
        sample_pulses = self.pulses[:sample_size]
        sample_widths = [p['width_ns'] for p in sample_pulses]
        
        print(f"[System] Sample pulse widths (ns): {['{:.1f}'.format(w) for w in sample_widths]}")
        
        # Score each candidate protocol based on distance to nominal values
        scores = {}
        for proto_name, spec in DSHOT_SPECS.items():
            w0 = spec["w0"]
            w1 = spec["w1"]
            total_error = 0.0
            for w in sample_widths:
                # Find minimum distance to either the '0' or '1' expected width
                total_error += min(abs(w - w0), abs(w - w1))
            scores[proto_name] = total_error
            
        # Select the protocol with the lowest error
        self.protocol = min(scores, key=scores.get)
        spec = DSHOT_SPECS[self.protocol]
        self.bit_period_ns = spec["bit_period"]
        
        # Calculate dynamic threshold: 0.6 * T_bit
        # Widths less than threshold are classified as '0', others as '1'
        self.threshold_ns = 0.6 * self.bit_period_ns
        
        print(f"[System] Protocol detected: {self.protocol} (Bit period ~{self.bit_period_ns:.0f}ns)")
        print(f"[System] Dynamic decision boundary (T_threshold): {self.threshold_ns:.1f}ns")

    def decode_frames(self, use_user_crc=False):
        """
        Slice frames using inter-frame gap thresholds, decode bit values, and verify CRC.
        :param use_user_crc: If True, uses the simplified formula from the prompt instead of standard Dshot CRC.
        """
        print("[System] Slicing and decoding Dshot frames...")
        # Define inter-frame gap threshold as 2 * bit period
        gap_threshold_ns = 2.0 * self.bit_period_ns
        
        frames_pulses = []
        current_frame = []
        
        for idx, pulse in enumerate(self.pulses):
            current_frame.append(pulse)
            
            # If the subsequent low period exceeds the threshold, this ends the frame
            if pulse['low_duration_ns'] > gap_threshold_ns:
                if len(current_frame) == 16:
                    frames_pulses.append(current_frame)
                else:
                    print(f"[Warning] Skipped a frame-like packet with invalid bit length: {len(current_frame)} bits (expected 16) at start time {current_frame[0]['rising_time']:.1f}ns")
                current_frame = []
                
        # Append final frame if complete
        if current_frame:
            if len(current_frame) == 16:
                frames_pulses.append(current_frame)
            else:
                print(f"[Warning] Skipped trailing packet with invalid bit length: {len(current_frame)} bits at start time {current_frame[0]['rising_time']:.1f}ns")
                
        print(f"[System] Found {len(frames_pulses)} valid 16-bit Dshot frames.")
        
        # Decode frame values
        decoded_frames = []
        for f_idx, frame in enumerate(frames_pulses):
            bits = []
            for pulse in frame:
                if pulse['width_ns'] < self.threshold_ns:
                    bits.append(0)
                else:
                    bits.append(1)
                    
            # Reconstruct 16-bit integer
            val_16 = 0
            for bit in bits:
                val_16 = (val_16 << 1) | bit
                
            # Extract Dshot fields
            # Bits 15-5 (11 bits): Throttle
            throttle = (val_16 >> 5) & 0x07FF
            # Bit 4 (1 bit): Telemetry Request
            telemetry = (val_16 >> 4) & 0x01
            # Bits 3-0 (4 bits): CRC Checksum
            crc_received = val_16 & 0x0F
            
            # Standard Dshot CRC: XOR the three 4-bit nibbles of the 12-bit payload
            # val_12 = (Throttle << 1) | Telemetry
            val_12 = (throttle << 1) | telemetry
            crc_calculated_std = (val_12 ^ (val_12 >> 4) ^ (val_12 >> 8)) & 0x0F
            
            # User simplified CRC formula:
            # GND = (Throttle ^ (Throttle >> 4) ^ Telemetry) & 0x0F
            crc_calculated_user = (throttle ^ (throttle >> 4) ^ telemetry) & 0x0F
            
            # Determine which validation standard to use
            crc_expected = crc_calculated_user if use_user_crc else crc_calculated_std
            crc_ok = (crc_received == crc_expected)
            status_str = "CRC OK" if crc_ok else f"CRC FAIL (Expected: {crc_expected})"
            
            decoded_frames.append({
                'frame_index': f_idx + 1,
                'throttle': throttle,
                'telemetry': telemetry,
                'crc_received': crc_received,
                'crc_expected': crc_expected,
                'crc_ok': crc_ok,
                'status_str': status_str,
                'time_ns': frame[0]['rising_time']
            })
            
            print(f"Frame {f_idx + 1} -> Throttle: {throttle}, Telemetry: {telemetry}, CRC: {crc_received} [{status_str}]")
            
        return decoded_frames

def main():
    parser = argparse.ArgumentParser(description="Dshot Logic Analyzer Protocol Parser")
    parser.add_argument("file", help="Path to input CSV file")
    parser.add_argument("--rate", type=float, default=100e6,
                        help="Sample rate in Hz for single-column CSV (default: 100000000 / 100MHz)")
    parser.add_argument("--use-user-crc", action="store_true",
                        help="Use the simplified CRC formula (Throttle ^ Throttle>>4 ^ Telemetry) & 0x0F instead of standard Dshot CRC")
                        
    args = parser.parse_args()
    
    print("[System] Starting DShotDecoder...")
    decoder_obj = DShotDecoder(args.file, sample_rate_hz=args.rate)
    decoder_obj.load_data()
    decoder_obj.extract_transitions()
    decoder_obj.detect_protocol()
    decoder_obj.decode_frames(use_user_crc=args.use_user_crc)
    
if __name__ == "__main__":
    main()
