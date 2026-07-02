# 🎵 유튜브 AI 음원 플레이리스트 채널 분석기 (YouTube AI Music Analyzer)

본 프로젝트는 유튜브의 **AI 음원 및 플레이리스트 채널** 데이터를 매일 수집 및 분석하여, 
성장성이 높은 '알짜 채널'을 발굴하고 장르별 수요-공급 포지셔닝을 통해 **니치마켓(블루오션 장르)을 분석**하는 시스템입니다.

---

## 🛠️ 기술 스택
- **언어**: Python 3.11+
- **데이터베이스**: SQLite (내장 라이브러리)
- **UI 및 시각화**: Streamlit, Plotly
- **주요 라이브러리**: Pandas, Google API Client (YouTube Data API v3), Python-dotenv

---

## 🚀 빠른 시작 (Quick Start)

### 1. 가상환경 활성화 및 패키지 설치
프로젝트 루트 폴더에서 가상환경을 활성화하고 필요한 패키지를 설치합니다.
```bash
# 가상환경 활성화 (Windows CMD)
.venv\Scripts\activate

# 의존성 패키지 설치 (필요시)
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (`.env`)
프로젝트 루트에 있는 `.env` 파일을 메모장 등으로 열어 사용자의 **YouTube API 키**를 입력합니다.
```env
# 구글 클라우드 콘솔에서 발급받은 API 키 입력
YOUTUBE_API_KEY=발급받은_API_키_입력

# SQLite 데이터베이스 경로 (기본값 제공됨)
DATABASE_PATH=data/youtube_analyzer.db
```
> **Note**: API 키가 입력되지 않았거나 유효하지 않은 경우, 분석기 대시보드를 시현해볼 수 있도록 **모의 데이터(Mock Data)**가 자동으로 데이터베이스에 적재됩니다.

### 3. Streamlit 대시보드 구동
대시보드를 실행하여 브라우저에서 분석 결과를 확인합니다.
```bash
streamlit run src/app.py --browser.gatherUsageStats=false
```
실행이 완료되면 브라우저에서 `http://localhost:8501`로 대시보드가 열립니다.

---

## 📂 프로젝트 구조
- `src/db.py`: SQLite 테이블 생성 및 DB 연결 관리 모듈
- `src/collector.py`: YouTube Data API v3를 활용해 일별 데이터 적재 및 Mock 데이터 생성 모듈
- `src/analyzer.py`: 데이터 가공, 급상승 지표 산출, 장르 분류 및 니치 스코어 연산 모듈
- `src/app.py`: Streamlit 기반 프론트엔드 대시보드 소스코드
- `run_daily.bat`: 윈도우 작업 스케줄러 연동용 배치 파일
- `data/youtube_analyzer.db`: 데이터베이스 파일 (수집 실행 후 생성됨)

---

## 📊 핵심 지표 정의

### 1. 채널 효율성 지수 (Efficiency Index)
$$\text{Efficiency Index} = \frac{\text{최근 7일 조회수 증가량}}{\text{구독자 수}}$$
* 구독자 수에 비해 실제로 유튜브 추천 알고리즘의 혜택을 받아 높은 유입을 얻고 있는 **알짜 채널**을 찾는 지표입니다. 
* 신규 채널 개설 시 벤치마킹하기 매우 유용한 모델을 식별하는 데 사용됩니다.

### 2. 성장 속도 (Growth Velocity)
* 이전 7일 대비 최근 7일 동안의 조회수 증가량의 성장폭을 비교하여 상승세가 얼마나 가파른지 퍼센트(%) 단위로 보여줍니다.

### 3. 니치 스코어 (Niche Score)
$$\text{Niche Score} = \frac{\text{장르 평균 조회수 (수요)}}{\text{해당 장르 경쟁 채널 수 + 1 (공급)}}$$
* 특정 음악 장르의 수요 대비 경쟁 강도를 분석하여 진입 매력도를 점수화한 지표입니다. 니치 스코어가 높을수록 경쟁자가 적고 조회수 효율이 높은 **블루오션 장르**임을 뜻합니다.

---

## ⏰ 매일 자동 실행 설정 (Windows)

매일 특정 시간에 백그라운드에서 유튜브 데이터를 수집하도록 설정하여 트렌드를 계속 추적할 수 있습니다.

1. `윈도우 시작` 버튼을 누르고 **작업 스케줄러 (Task Scheduler)**를 실행합니다.
2. 우측 메뉴에서 **기본 작업 만들기 (Create Basic Task)**를 클릭합니다.
3. 작업 이름(예: `YouTube_AI_Analyzer`)을 설정하고 **매일 (Daily)** 실행을 선택합니다.
4. 실행 원하는 시간(예: 새벽 4시)을 지정합니다.
5. 동작 단계에서 **프로그램 시작 (Start a program)**을 선택합니다.
6. 프로그램/스크립트 입력창에 **찾아보기**를 눌러 프로젝트 디렉토리 안의 `run_daily.bat`을 선택합니다.
7. **시작 위치(옵션)** 입력란에 프로젝트의 절대 경로 (예: `D:\Antigravity\FOLDER`)를 입력합니다. (매우 중요)
8. **마침**을 누르면 매일 지정된 시간에 데이터를 자동 수집하고 로그가 `logs/daily_collector.log`에 기록됩니다.
