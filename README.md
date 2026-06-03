# Chess Game (PyQt6 + Stockfish)

A professional desktop chess game application built with **Python 3.10+**, **PyQt6**, **python-chess**, and **Stockfish** integration.

## Features

- Complete chess rules via python-chess (castling, en passant, promotion, legal move validation)
- Check/checkmate/stalemate detection and FEN support
- Interactive PyQt6 board with:
  - Drag-and-drop/click move interaction
  - Legal move indicators
  - Arrow drawing (right-click drag toggles arrows)
  - Board flip
  - Last-move and selected-square highlighting
- Premove queue support
- Move history with SAN notation and PGN save/load
- Undo/redo and game reset controls
- Stockfish integration with 5 difficulties:
  - 300 Elo
  - 500 Elo
  - 1000 Elo
  - 1500 Elo
  - 2000 Elo
- Live evaluation bar + numeric centipawn display
- Settings panel:
  - Legal move indicators toggle
  - Premove toggle
  - AI difficulty selector
  - Evaluation bar toggle
  - Board and piece theme selectors
  - Sound toggle

## Project Structure

- `main.py` – application entrypoint
- `chess_game/engine.py` – Stockfish engine wrapper
- `chess_game/board.py` – chess state, move validation, undo/redo, PGN handling
- `chess_game/gui/main_window.py` – main application window and game loop
- `chess_game/gui/board_widget.py` – board rendering and interaction
- `chess_game/gui/settings_panel.py` – settings controls
- `chess_game/gui/evaluation_bar.py` – position evaluation bar
- `chess_game/gui/move_history.py` – SAN move list display
- `chess_game/utils/constants.py` / `helpers.py` – constants and helpers
- `chess_game/resources/styles.qss` – stylesheet

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### Stockfish binary

The app tries to auto-detect Stockfish from common paths (`stockfish`, `/usr/games/stockfish`, `/usr/local/bin/stockfish`).

If Stockfish is not found, the game still runs in local-play mode and AI/evaluation features remain unavailable.

## Run

```bash
python main.py
```

## Packaging (PyInstaller)

```bash
pyinstaller --name chess-game --onefile --windowed main.py
```
