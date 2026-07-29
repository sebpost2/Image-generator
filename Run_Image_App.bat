@echo off
rem Double-click to open the Image-generator app (generate scene images from prompts/).
rem ComfyUI must be running (run_nvidia_gpu.bat) and listening on 127.0.0.1:8188.
cd /d "%~dp0"
python scripts\image_app.py
if errorlevel 1 pause
