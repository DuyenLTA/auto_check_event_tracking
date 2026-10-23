@echo off
rem Cham event tracking KHONG can Claude. Chay tren may dang cam dien thoai (USB debugging).
rem   chay-khong-claude.bat <package> <link Confluence hoac ten chuc nang>
rem Tu chay lai case lai hut 1 lan; event van chua cham duoc ghi "Can nguoi xem".
rem Report HTML nam trong out\, Discord gui kem file report (neu co DISCORD_WEBHOOK_URL).
setlocal
cd /d "%~dp0"
if "%~2"=="" (
  echo Cach dung: chay-khong-claude.bat ^<package^> ^<link spec hoac ten chuc nang^>
  echo Link spec phai de trong ngoac kep: chay-khong-claude.bat com.x "https://...?pageId=123"
  exit /b 1
)
if not exist out mkdir out
".venv\Scripts\usv-check.exe" --khong-claude --package "%~1" --spec "%~2" > "out\lan-chay-cuoi.json"
set MA=%ERRORLEVEL%
if %MA%==0 (echo Xong. Ket qua JSON: out\lan-chay-cuoi.json - duong dan report o truong "report".)
exit /b %MA%
