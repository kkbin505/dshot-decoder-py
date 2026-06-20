# DShot Decoder Test Results

This document summarizes the decoding results of all captured Dshot CSV files using `DShotDecoder.py` at the default sample rate of **100 MHz (100,000,000 Hz)**.

## Test Summary

| Capture Filename | Identified Protocol | Status | Decoded Values | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **sample_Dshot150_caputre_48.csv** | Dshot150 | **SUCCESS** | Throttle: 48, Telemetry: 0, CRC: 6 | `[CRC OK]` (Recovered via virtual falling edge) |
| **sample_Dshot150_caputre_2047.csv** | Dshot150 | **SUCCESS** | Throttle: 2047, Telemetry: 0, CRC: 14 | `[CRC OK]` (Recovered via virtual falling edge) |
| **sample_Dshot300_caputre_466.csv** | Dshot300 | **SUCCESS** | Throttle: 466, Telemetry: 0, CRC: 13 | `[CRC OK]` |
| **sample_Dshot300_caputre_1003.csv** | Dshot300 | **SUCCESS** | Throttle: 1003, Telemetry: 0, CRC: 12 | `[CRC OK]` |
| **sample_Dshot300_caputre_1506.csv** | Dshot300 | **SUCCESS** | Throttle: 1506, Telemetry: 0, CRC: 3 | `[CRC OK]` |
| **sample_Dshot600_caputre_48.csv** | Dshot600 | **SUCCESS** | Throttle: 48, Telemetry: 0, CRC: 6 | `[CRC OK]` |
| **sample_Dshot600_caputre_500.csv** | Dshot600 | **SUCCESS** | Throttle: 500, Telemetry: 0, CRC: 5 | `[CRC OK]` |
| **sample_Dshot600_caputre_1071.csv** | Dshot600 | **SUCCESS** | Throttle: 1071, Telemetry: 0, CRC: 3 | `[CRC OK]` |
| **sample_Dshot600_caputre_2047.csv** | Dshot600 | **SUCCESS** | Throttle: 2047, Telemetry: 0, CRC: 14 | `[CRC OK]` |
| *sample_Dshot150_caputre_1092.csv* | Dshot300 | **FAILED** | - | **Incomplete Capture**: Contains only 3 high pulses on disk. |
| *sample_Dshot600_caputre_1622.csv* | Dshot600 | **FAILED** | - | **Truncated Capture**: Contains 7 bits of previous frame & 15 bits of next frame. |

---

## Detailed File Analysis

### 1. Dshot150 Captures with Virtual Edge Correction

Dshot150 signals have a longer bit period ($6667\text{ ns}$). Since the capture logs end at 11,024 samples ($110.24\text{ us}$), the 16th high pulse is cut off right at the end of the file. By appending a virtual falling edge dynamically when the file ends while high, `DShotDecoder.py` successfully recovers the final bit.

#### sample_Dshot150_caputre_48.csv
- **Detected Protocol**: Dshot150 (Bit period ~6667ns, Decision boundary: 4000.2ns)
- **Decoded Bits**: `0000011000000110`
- **Output**: `Frame 1 -> Throttle: 48, Telemetry: 0, CRC: 6 [CRC OK]`

#### sample_Dshot150_caputre_2047.csv
- **Detected Protocol**: Dshot150 (Bit period ~6667ns, Decision boundary: 4000.2ns)
- **Decoded Bits**: `1111111111101110`
- **Output**: `Frame 1 -> Throttle: 2047, Telemetry: 0, CRC: 14 [CRC OK]`

---

### 2. Dshot300 Captures

All Dshot300 captures have a bit period of $3333\text{ ns}$ (100 samples per bit at 100 MHz).

#### sample_Dshot300_caputre_466.csv
- **Detected Protocol**: Dshot300 (Bit period ~3333ns, Decision boundary: 1999.8ns)
- **Output**: `Frame 1 -> Throttle: 466, Telemetry: 0, CRC: 13 [CRC OK]`

#### sample_Dshot300_caputre_1003.csv
- **Detected Protocol**: Dshot300 (Bit period ~3333ns, Decision boundary: 1999.8ns)
- **Output**: `Frame 1 -> Throttle: 1003, Telemetry: 0, CRC: 12 [CRC OK]`

#### sample_Dshot300_caputre_1506.csv
- **Detected Protocol**: Dshot300 (Bit period ~3333ns, Decision boundary: 1999.8ns)
- **Output**: `Frame 1 -> Throttle: 1506, Telemetry: 0, CRC: 3 [CRC OK]`

---

### 3. Dshot600 Captures

All Dshot600 captures have a bit period of $1667\text{ ns}$ (50 samples per bit at 100 MHz).

#### sample_Dshot600_caputre_48.csv
- **Detected Protocol**: Dshot600 (Bit period ~1667ns, Decision boundary: 1000.2ns)
- **Output**: `Frame 1 -> Throttle: 48, Telemetry: 0, CRC: 6 [CRC OK]`

#### sample_Dshot600_caputre_500.csv
- **Detected Protocol**: Dshot600 (Bit period ~1667ns, Decision boundary: 1000.2ns)
- **Output**: `Frame 1 -> Throttle: 500, Telemetry: 0, CRC: 5 [CRC OK]`

#### sample_Dshot600_caputre_1071.csv
- **Detected Protocol**: Dshot600 (Bit period ~1667ns, Decision boundary: 1000.2ns)
- **Output**: `Frame 1 -> Throttle: 1071, Telemetry: 0, CRC: 3 [CRC OK]`

#### sample_Dshot600_caputre_2047.csv
- **Detected Protocol**: Dshot600 (Bit period ~1667ns, Decision boundary: 1000.2ns)
- **Output**: `Frame 1 -> Throttle: 2047, Telemetry: 0, CRC: 14 [CRC OK]`

---

### 4. Physically Truncated Captures (Unresolved)

These captures contain incomplete frames due to logic analyzer logging issues and cannot be decoded into 16-bit frames.

#### sample_Dshot150_caputre_1092.csv
- **Analysis**: Contains only **3 high-level pulses** (from index 1024 to 2599) and stays at logic `0` for the remaining $84,250\text{ ns}$ of the capture.
- **Output**: `[Warning] Skipped a frame-like packet with invalid bit length: 3 bits (expected 16)`

#### sample_Dshot600_caputre_1622.csv
- **Analysis**: Contains 22 pulses in total. 
  - Group 1 (Indices 1023 to 2008) has only 7 pulses (the end of a previous frame).
  - Group 2 (Indices 8608 to 11008) has 15 pulses, and the capture ended before the 16th pulse started.
- **Output**: `[Warning] Skipped a frame-like packet with invalid bit length: 7 bits` and `[Warning] Skipped a frame-like packet with invalid bit length: 15 bits`
