@echo off
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo Edit .env and add DISCORD_TOKEN, then run this file again.
python -m solana_bot
pause
