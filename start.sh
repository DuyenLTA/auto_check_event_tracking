#!/usr/bin/env bash
# UI Spec Verifier - khoi dong tren macOS va Linux.
#
#   ./start.sh                    -> http://127.0.0.1:8000
#   PORT=9000 ./start.sh          -> doi cong
#   USV_NO_BROWSER=1 ./start.sh   -> khong tu mo trinh duyet
#
# Lan dau chay se tu tao moi truong ao va cai thu vien (~30 giay).
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ENV_DIR=".venv"
PORT="${PORT:-8000}"

die() {
  echo "" >&2
  echo "LOI: $*" >&2
  exit 1
}

# --- 1. Tim Python 3.12+ ------------------------------------------------------
PY=""
for candidate in python3.14 python3.13 python3.12 python3 python; do
  command -v "$candidate" >/dev/null 2>&1 || continue
  if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
    PY="$candidate"; break
  fi
done
[ -n "$PY" ] || die "Can Python 3.12 tro len.
  macOS : brew install python@3.13
  Ubuntu: sudo apt install python3 python3-venv"

# --- 2. Moi truong ao ---------------------------------------------------------
# BAT BUOC dung moi truong ao: Python he thong tren Ubuntu/Debian va Homebrew
# chan 'pip install' voi loi externally-managed-environment (PEP 668).
if [ ! -x "$ENV_DIR/bin/python" ]; then
  echo "Lan dau chay - dang tao moi truong ao..."
  "$PY" -m venv "$ENV_DIR" || die "Khong tao duoc moi truong ao.
  Ubuntu/Debian can them goi: sudo apt install python3-venv"
fi
VPY="$ENV_DIR/bin/python"

# Cai lai khi thieu thu vien HOAC khi pyproject.toml moi hon lan cai truoc
STAMP="$ENV_DIR/.usv-installed"
NEEDS_INSTALL=0
"$VPY" -c "import usv, fastapi, yaml, openpyxl" >/dev/null 2>&1 || NEEDS_INSTALL=1
[ -f "$STAMP" ] && [ pyproject.toml -nt "$STAMP" ] && NEEDS_INSTALL=1

# `usv` phai tro vao CHINH repo nay. Doi ten thu muc du an lam file .pth cua
# editable install tro vao duong dan cu -> uvicorn nap MOT PACKAGE KHAC ma
# pytest khong he bao loi, vi pytest lay src qua `pythonpath` trong pyproject.
# Da gap that: server serve nguyen mot tool khac, moi route tra 404.
HERE_SRC="$(cd "$(dirname "$0")" && pwd)/src"
LOADED="$("$VPY" -c "import usv,os;print(os.path.dirname(os.path.dirname(usv.__file__)))" 2>/dev/null || true)"
if [ -n "$LOADED" ] && [ "$LOADED" != "$HERE_SRC" ]; then
  echo "usv dang tro vao $LOADED thay vi $HERE_SRC - cai lai..."
  NEEDS_INSTALL=1
fi
if [ "$NEEDS_INSTALL" = "1" ]; then
  echo "Dang cai thu vien..."
  "$VPY" -m pip install -q --upgrade pip >/dev/null 2>&1
  "$VPY" -m pip install -q -e . || die "Cai thu vien that bai.
  Thu chay tay de xem chi tiet: $VPY -m pip install -e ."
  touch "$STAMP"

  AFTER="$("$VPY" -c "import usv,os;print(os.path.dirname(os.path.dirname(usv.__file__)))" 2>/dev/null || true)"
  if [ -n "$AFTER" ] && [ "$AFTER" != "$HERE_SRC" ]; then
    die "Cai xong ma usv van tro vao $AFTER.
  Thuong la con mot ban editable cu cua du an khac cung dung package 'usv'.
  Xem: $VPY -m pip list | grep -i usv
  Bo di:  $VPY -m pip uninstall -y usv"
  fi
fi

# --- 3. Tim adb (canh bao thoi, khong chan) -----------------------------------
if [ -z "${ADB_PATH:-}" ] && ! command -v adb >/dev/null 2>&1; then
  for guess in \
    "$HOME/Android/Sdk/platform-tools/adb" \
    "$HOME/Library/Android/sdk/platform-tools/adb" \
    "/usr/local/bin/adb" "/opt/android-sdk/platform-tools/adb"; do
    [ -x "$guess" ] && { export ADB_PATH="$guess"; break; }
  done
fi
if [ -z "${ADB_PATH:-}" ] && ! command -v adb >/dev/null 2>&1; then
  echo "CANH BAO: khong tim thay adb. Cai Android platform-tools, hoac dat:"
  echo "          export ADB_PATH=/duong/dan/toi/adb"
else
  echo "adb : ${ADB_PATH:-$(command -v adb)}"
fi

# --- 4. Chon cong con trong ---------------------------------------------------
FREE_PORT=$("$VPY" scripts/find-free-port.py "$PORT")
[ "$FREE_PORT" = "0" ] && die "Khong con cong trong tu $PORT den $((PORT + 19))."
[ "$FREE_PORT" != "$PORT" ] && echo "Cong $PORT dang ban - dung cong $FREE_PORT."

URL="http://127.0.0.1:${FREE_PORT}"
echo "Mo $URL  (Ctrl+C de dung)"

if [ "${USV_NO_BROWSER:-0}" != "1" ]; then
  (
    sleep 2
    if command -v open >/dev/null 2>&1; then open "$URL"
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
    fi
  ) >/dev/null 2>&1 &
fi

# Chi bind 127.0.0.1: cong cu noi bo, khong co auth, dieu khien duoc adb ->
# KHONG duoc expose ra LAN. main.py con co middleware chan thu hai.
"$VPY" -m uvicorn usv.main:app --host 127.0.0.1 --port "$FREE_PORT"
