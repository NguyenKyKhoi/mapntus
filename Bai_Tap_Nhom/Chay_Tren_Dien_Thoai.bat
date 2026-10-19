@echo off
chcp 65001 >nul
title May Chu WebGIS NTU Cho Dien Thoai
echo Dang khoi chay may chu, vui long doi giay lat...
cd /d "%~dp0"
python server_mobile.py
pause
