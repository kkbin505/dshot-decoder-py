# DShot Decoder (dshot-decoder-py)

A lightweight Python script to parse and decode Dshot signals exported from logic analyzers. 

## Features
- **Multi-rate Auto-detection**: Automatically identifies the signal rate (Dshot1200, Dshot600, Dshot300, or Dshot150) from the first few pulses and adjusts its timing thresholds dynamically.
- **Dynamic Decision Boundary**: Computes the bit decision boundary dynamically ($0.6 \times T_{\text{bit}}$) for error-tolerant logic `0`/`1` classification.
- **Adaptive CSV Loader**: Supports single-column (states only, using default/custom sample rate) and dual-column (timestamp and state, auto-converting seconds to nanoseconds) CSV formats.
- **Standard CRC Verification**: Performs full Dshot 4-bit CRC checks on each packet.

## Usage

Place the `DShotDecoder.py` script in your working directory and execute it via the terminal.

### 1. Basic Usage (Default 100 MHz sample rate)
For single-column CSV logs (like logic level captures), it defaults to a sample rate of `100,000,000 Hz` (100 MHz):
```bash
python DShotDecoder.py Dshot_caputre_1003.csv
```

### 2. Specifying a Custom Sample Rate
If your logic analyzer captured data at a different sample rate (e.g., 200 MHz):
```bash
python DShotDecoder.py Dshot_caputre_1003.csv --rate 200e6
```

### 3. Using Alternate CRC Mode
If your Dshot packet uses a custom/simplified CRC logic `(Throttle ^ Throttle>>4 ^ Telemetry) & 0x0F` instead of standard Dshot CRC, use the `--use-user-crc` flag:
```bash
python DShotDecoder.py Dshot_caputre_1003.csv --use-user-crc
```

## Output
```text
[System] Slicing and decoding Dshot frames...
[System] Found 1 valid 16-bit Dshot frames.
Frame 1 -> Throttle: 1003, Telemetry: 0, CRC: 12 [CRC OK]
```

## Reference:

I use this logic analyzer to capture the Dshot signal, all you need is a pico:
https://github.com/gusmanb/logicanalyzer
