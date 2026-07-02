import os
import sqlite3
from datetime import datetime

def get_db_connection(db_path=None):
    """
    SQLite 데이터베이스 연결 객체를 생성하여 반환합니다.
    Streamlit Cloud의 st.secrets와 로컬 .env 파일을 모두 지원합니다.
    """
    if db_path is None:
        # 1순위: Streamlit Cloud secrets
        try:
            import streamlit as st
            db_path = st.secrets.get("DATABASE_PATH", None)
        except Exception:
            db_path = None
        
        # 2순위: 로컬 .env 파일
        if not db_path:
            from dotenv import load_dotenv
            load_dotenv()
            db_path = os.getenv("DATABASE_PATH", "data/youtube_analyzer.db")
    
    # 데이터베이스 저장 디렉토리 자동 생성
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 데이터 접근이 가능하도록 설정
    return conn

def init_db(db_path=None):
    """
    시스템에 필요한 테이블들을 생성하고 데이터베이스를 초기화합니다.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 1. channels 테이블 (채널 메타데이터)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        published_at TEXT,
        country TEXT,
        language TEXT,
        custom_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. channel_stats_daily 테이블 (일별 채널 통계)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channel_stats_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT NOT NULL,
        view_count INTEGER,
        subscriber_count INTEGER,
        video_count INTEGER,
        record_date TEXT NOT NULL,
        FOREIGN KEY(channel_id) REFERENCES channels(channel_id),
        UNIQUE(channel_id, record_date)
    )
    ''')
    
    # 3. videos 테이블 (비디오 메타데이터)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        channel_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        published_at TEXT,
        duration TEXT,       -- ISO 8601 형식 (예: PT3M45S)
        tags TEXT,           -- 쉼표(,) 혹은 JSON 문자열로 저장
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
    )
    ''')
    
    # 4. video_stats_daily 테이블 (일별 비디오 통계)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_stats_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL,
        view_count INTEGER,
        like_count INTEGER,
        comment_count INTEGER,
        record_date TEXT NOT NULL,
        FOREIGN KEY(video_id) REFERENCES videos(video_id),
        UNIQUE(video_id, record_date)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
