@echo off
title Scribd Mini Downloader
cd /d "%~dp0"
python mini_app.py
if errorlevel 1 (
    echo.
    echo Da co loi xay ra!
    pause
)
