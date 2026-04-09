#!/bin/bash
echo "FastAPI 서버 시작..."
cd /Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260409_scaleup_biso
source /Users/skku_aws2_14/miniconda3/etc/profile.d/conda.sh
conda activate drug4-kg
uvicorn chat.api_server:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
echo "서버 PID: $SERVER_PID"

sleep 3
echo "ngrok 터널 시작..."
ngrok http 8000
