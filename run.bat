@echo off
title Hitter All-in-One Runner
echo 🚀 Starting Hitter Project...

:: 1. Check/Install Dependencies
echo [1/4] Installing dependencies...
pip install python-dotenv pyTelegramBotAPI requests flask playwright playwright-stealth

echo 🌐 Setting up Chromium Browser (One time)...
playwright install chromium

echo 🚀 Starting Auto Hitter Bot...
echo [2/4] Starting Telegram Bot in a new window...
start "Hitter Bot" cmd /k python "auto hitter code EG.py"

:: 3. Start Dashboard Server
echo [3/4] Starting Dashboard Server in a new window...
start "Dashboard Server" cmd /k python "server.py"

:: 4. Start SSH Tunnel (Public URL)
echo [4/4] Establishing STATIC Public URL (Serveo)...

:: Check for SSH Key (Required for static subdomains on Serveo)
if not exist "%USERPROFILE%\.ssh\id_rsa" (
    echo 🔧 Generating local SSH Key for static URL...
    if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"
    ssh-keygen -q -t rsa -N "" -f "%USERPROFILE%\.ssh\id_rsa"
)

echo 🔗 Your fixed Mini App URL: https://hitter8766583877.serveo.net
echo ⚠️  If asked "yes/no", type: yes  (only the first time)
ssh -o ServerAliveInterval=60 -R hitter8766583877:80:localhost:5000 serveo.net

pause
