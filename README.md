# Chess Game

Production-ready desktop chess game built with PyQt6, python-chess, and Stockfish.

## Features

- Full legal chess rules (castling, en passant, promotion, check/checkmate/stalemate)
- Drag-and-drop board interaction
- Right-click arrows (default yellow, Shift=green, Ctrl=red)
- Optional premove queue
- AI difficulty levels: 300 / 500 / 1000 / 1500 / 2000 Elo
- Real-time evaluation bar with centipawn and mate display
- Move history panel with clickable navigation
- PGN export to file
- Settings panel with immediate apply behavior
- Board flip support

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Stockfish setup and troubleshooting

The project depends on the Python `stockfish` package (`stockfish>=16.0.0`) and also supports a manual binary path.

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. If Stockfish is not auto-detected, install Stockfish manually:
   - Linux: `sudo apt install stockfish`
   - macOS: `brew install stockfish`
   - Windows: download from official Stockfish releases and extract binary
3. Set manual path (all platforms):
   ```bash
   export STOCKFISH_PATH=/absolute/path/to/stockfish
   ```

If initialization fails, the app shows a warning dialog with recovery guidance.

## Keyboard / mouse shortcuts

- Left click + drag: move piece
- Right click drag: draw arrow
- Shift + right drag: green arrow
- Ctrl + right drag: red arrow
- View menu: show/hide Settings panel
- Edit menu: Undo Move, Flip Board

## Screenshot / demo

Launch `python main.py` to view the chessboard UI with board, evaluation bar, move history, and settings dock.

## Dependencies

- PyQt6>=6.6.0
- python-chess>=1.10.0
- stockfish>=16.0.0
- Pillow>=10.0.0
- PyQt6-sip>=13.6.0

## Troubleshooting

- **`Stockfish binary was not found`**
  - Install the `stockfish` package and/or system binary
  - Set `STOCKFISH_PATH` to the binary executable
- **GUI does not open**
  - Confirm PyQt6 installed in active environment
- **No AI move generated**
  - Verify Stockfish executable permissions and path
