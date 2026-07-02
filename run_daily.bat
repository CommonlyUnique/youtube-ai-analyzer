@echo off
cd /d %~dp0
if not exist logs mkdir logs
echo [%date% %time%] 데이터 수집 및 갱신 시작 >> logs\daily_collector.log
.venv\Scripts\python src\collector.py >> logs\daily_collector.log 2>&1
echo [%date% %time%] 수집 완료 >> logs\daily_collector.log
