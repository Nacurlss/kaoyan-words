#!/bin/bash
# 考研单词频率筛选 — 一键启动脚本
# Usage: ./start.sh

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  考研单词频率筛选 v2"
echo "========================================"

# ── Check Python ──
PYTHON=""
for py in python3.11 python3.10 python3 python; do
    if command -v "$py" &>/dev/null; then
        if "$py" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            PYTHON="$py"
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python 3.10+，请先安装 Python 3.10 或更高版本"
    exit 1
fi

# ── Check/setup backend deps ──
echo ""
echo "📦 检查 Python 依赖..."
if ! "$PYTHON" -c "import fastapi, nltk, pdfplumber, openpyxl" 2>/dev/null; then
    echo "   安装缺失的依赖..."
    "$PYTHON" -m pip install fastapi uvicorn python-multipart python-docx pdfplumber openpyxl httpx nltk --quiet
fi

# NLTK data
echo "📦 检查 NLTK 数据..."
"$PYTHON" -c "
import nltk, ssl, signal
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except: pass

def _timeout(*_):
    raise TimeoutError('NLTK download timed out')

for r in ['punkt_tab', 'averaged_perceptron_tagger_eng', 'wordnet']:
    try:
        loc = 'tokenizers' if 'punkt' in r else 'taggers' if 'tagger' in r else 'corpora'
        nltk.data.find(f'{loc}/{r}')
    except LookupError:
        try:
            signal.signal(signal.SIGALRM, _timeout)
            signal.alarm(8)
            ok = nltk.download(r, quiet=True)
            signal.alarm(0)
            if not ok:
                print(f'   ⚠ NLTK 数据 {r} 下载失败，先继续启动')
        except Exception as e:
            signal.alarm(0)
            print(f'   ⚠ NLTK 数据 {r} 不可用：{e}，先继续启动')
"

# ── Check/setup frontend deps ──
echo "📦 检查前端依赖..."
if [ ! -d "src/frontend/node_modules" ]; then
    echo "   安装前端依赖 (npm install)..."
    cd src/frontend && npm install --silent && cd ../..
fi

# ── Start servers ──
echo ""
echo "🚀 启动服务..."

# Backend
"$PYTHON" -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000 &
BPID=$!
echo "   后端: http://localhost:8000 (PID=$BPID)"

# Frontend
cd src/frontend
npx vite --host 127.0.0.1 --port 5173 &
FPID=$!
cd ../..
echo "   前端: http://localhost:5173 (PID=$FPID)"

# Cleanup on exit
trap "echo ''; echo '🛑 停止服务...'; kill $BPID $FPID 2>/dev/null; echo '已停止'" EXIT INT TERM

echo ""
echo "========================================"
echo "  ✅ 服务已启动"
echo "  浏览器打开: http://localhost:5173"
echo "  按 Ctrl+C 停止所有服务"
echo "========================================"

wait
