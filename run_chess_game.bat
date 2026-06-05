@echo off
set "STOCKFISH_PATH=C:\Users\apgif\AppData\Local\Microsoft\WinGet\Packages\Stockfish.Stockfish_Microsoft.Winget.Source_8wekyb3d8bbwe\stockfish\stockfish-windows-x86-64-avx2.exe"
cd /d "%~dp0"
".venv\Scripts\python.exe" main.py
