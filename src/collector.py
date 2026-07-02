import os
import sqlite3
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection

load_dotenv()

# Streamlit Cloud secrets 우선, 없으면 .env 파일 사용
def _get_secret(key, default=None):
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, default)

API_KEY = _get_secret("YOUTUBE_API_KEY")
DB_PATH = _get_secret("DATABASE_PATH", "data/youtube_analyzer.db")

def get_youtube_client():
    if not API_KEY or API_KEY == "YOUR_YOUTUBE_API_KEY_HERE":
        return None
    try:
        return build('youtube', 'v3', developerKey=API_KEY)
    except Exception as e:
        print(f"YouTube Client 빌드 실패: {e}")
        return None

def search_channels_by_keywords(youtube, keywords=["AI lofi", "AI playlist", "AI cover music"]):
    """
    키워드 검색을 통해 AI 음원 관련 채널 ID들을 발굴합니다.
    (API 쿼터를 절약하기 위해 비디오 검색 결과에서 채널 ID를 추출합니다.)
    """
    channel_ids = set()
    for kw in keywords:
        try:
            print(f"키워드 검색 중: '{kw}'...")
            request = youtube.search().list(
                q=kw,
                part="snippet",
                type="video",
                maxResults=25,
                order="relevance"
            )
            response = request.execute()
            for item in response.get("items", []):
                channel_id = item["snippet"]["channelId"]
                channel_ids.add(channel_id)
        except HttpError as e:
            print(f"키워드 '{kw}' 검색 오류: {e}")
            break
    return list(channel_ids)

def save_channel_metadata(conn, channel_data):
    """
    채널 기본 메타데이터를 저장하거나 갱신합니다.
    """
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO channels (
        channel_id, title, description, published_at, country, language, custom_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        channel_data['channel_id'],
        channel_data['title'],
        channel_data['description'],
        channel_data['published_at'],
        channel_data['country'],
        channel_data['language'],
        channel_data['custom_url']
    ))
    conn.commit()

def save_channel_daily_stats(conn, channel_id, stats, record_date):
    """
    일별 채널 통계치를 적재합니다. (동일 날짜 데이터는 중복 방지)
    """
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO channel_stats_daily (
        channel_id, view_count, subscriber_count, video_count, record_date
    ) VALUES (?, ?, ?, ?, ?)
    ''', (
        channel_id,
        stats.get('view_count'),
        stats.get('subscriber_count'),
        stats.get('video_count'),
        record_date
    ))
    conn.commit()

def save_video_metadata(conn, video_data):
    """
    비디오 기본 메타데이터를 저장하거나 갱신합니다.
    """
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO videos (
        video_id, channel_id, title, description, published_at, duration, tags
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        video_data['video_id'],
        video_data['channel_id'],
        video_data['title'],
        video_data['description'],
        video_data['published_at'],
        video_data['duration'],
        ",".join(video_data['tags']) if video_data['tags'] else ""
    ))
    conn.commit()

def save_video_daily_stats(conn, video_id, stats, record_date):
    """
    일별 비디오 통계치를 적재합니다. (동일 날짜 데이터는 중복 방지)
    """
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO video_stats_daily (
        video_id, view_count, like_count, comment_count, record_date
    ) VALUES (?, ?, ?, ?, ?)
    ''', (
        video_id,
        stats.get('view_count'),
        stats.get('like_count'),
        stats.get('comment_count'),
        record_date
    ))
    conn.commit()

def fetch_and_save_channels(youtube, conn, channel_ids):
    """
    채널 ID 리스트의 상세 정보 및 일별 통계를 유튜브 API로부터 가져와 DB에 적재합니다.
    """
    if not channel_ids:
        return
    
    # 50개 단위로 묶어서 API 요청 (API 효율화)
    chunk_size = 50
    record_date = datetime.now().strftime("%Y-%m-%d")
    
    for i in range(0, len(channel_ids), chunk_size):
        chunk = channel_ids[i:i+chunk_size]
        ids_str = ",".join(chunk)
        
        try:
            request = youtube.channels().list(
                part="snippet,statistics,contentDetails",
                id=ids_str
            )
            response = request.execute()
            
            for item in response.get("items", []):
                channel_id = item["id"]
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                
                # 메타데이터 구조화
                # country 필드가 없는 채널의 경우, 언어 정보나 기본 국가를 None 처리
                country = snippet.get("country")
                
                # 설명과 제목에서 대략적인 주 사용 언어 추정 (임시 룰)
                description = snippet.get("description", "")
                title = snippet.get("title", "")
                language = "ko" if re.search("[ㄱ-ㅎㅏ-ㅣ가-힣]", title + description) else "en"
                if not country and language == "ko":
                    country = "KR"
                
                channel_data = {
                    "channel_id": channel_id,
                    "title": title,
                    "description": description,
                    "published_at": snippet.get("publishedAt"),
                    "country": country or "US",  # 누락 시 기본값 US
                    "language": language,
                    "custom_url": snippet.get("customUrl")
                }
                
                # 채널 기본 정보 저장
                save_channel_metadata(conn, channel_data)
                
                # 채널 일별 통계
                stats = {
                    "view_count": int(statistics.get("viewCount", 0)) if statistics.get("viewCount") else None,
                    "subscriber_count": int(statistics.get("subscriberCount", 0)) if statistics.get("subscriberCount") else None,
                    "video_count": int(statistics.get("videoCount", 0)) if statistics.get("videoCount") else None
                }
                save_channel_daily_stats(conn, channel_id, stats, record_date)
                
                # 최근 업로드 비디오 수집을 위한 Uploads Playlist ID 추출
                uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads")
                if uploads_playlist_id:
                    fetch_and_save_channel_videos(youtube, conn, channel_id, uploads_playlist_id)
                    
        except HttpError as e:
            print(f"채널 상세 정보 수집 오류: {e}")

def fetch_and_save_channel_videos(youtube, conn, channel_id, uploads_playlist_id, max_videos=15):
    """
    특정 채널의 Uploads 플레이리스트에서 최근 영상들을 가져와 DB에 적재합니다.
    """
    record_date = datetime.now().strftime("%Y-%m-%d")
    try:
        # 1. 최근 비디오 ID 목록 조회
        playlist_request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=max_videos
        )
        playlist_response = playlist_request.execute()
        
        video_ids = [item["contentDetails"]["videoId"] for item in playlist_response.get("items", [])]
        if not video_ids:
            return
            
        # 2. 비디오 상세 정보 조회
        video_request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(video_ids)
        )
        video_response = video_request.execute()
        
        for item in video_response.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            statistics = item.get("statistics", {})
            
            video_data = {
                "video_id": video_id,
                "channel_id": channel_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"),
                "duration": content_details.get("duration", ""),
                "tags": snippet.get("tags", [])
            }
            # 비디오 메타데이터 저장
            save_video_metadata(conn, video_data)
            
            # 비디오 일별 통계
            stats = {
                "view_count": int(statistics.get("viewCount", 0)) if statistics.get("viewCount") else None,
                "like_count": int(statistics.get("likeCount", 0)) if statistics.get("likeCount") else None,
                "comment_count": int(statistics.get("commentCount", 0)) if statistics.get("commentCount") else None
            }
            save_video_daily_stats(conn, video_id, stats, record_date)
            
    except HttpError as e:
        print(f"채널 {channel_id}의 비디오 수집 오류: {e}")

def run_collector():
    """
    수집기 메인 실행 함수
    """
    youtube = get_youtube_client()
    conn = get_db_connection()
    
    if youtube is None:
        print("YouTube API Key가 설정되지 않았거나 올바르지 않습니다.")
        print("시뮬레이션 및 테스트를 위해 Mock 데이터를 생성합니다...")
        generate_mock_data(conn)
        conn.close()
        return

    print("수집기 작동을 시작합니다...")
    # 1. 키워드 검색을 통해 대상 채널 수집
    keywords = ["AI lofi playlist", "AI cover song", "AI BGM playlist", "Lofi Chill AI", "AI 커버 플레이리스트"]
    channel_ids = search_channels_by_keywords(youtube, keywords)
    
    # 기 등록된 기존 채널 ID도 리스트에 통합
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    existing_ids = [row[0] for row in cursor.fetchall()]
    all_channel_ids = list(set(channel_ids + existing_ids))
    
    print(f"총 {len(all_channel_ids)}개 채널 분석 및 갱신 시작...")
    # 2. 채널별 상세 정보 및 비디오 적재
    fetch_and_save_channels(youtube, conn, all_channel_ids)
    
    conn.close()
    print("수집이 완료되었습니다.")

def generate_mock_data(conn):
    import random
    cursor = conn.cursor()
    mock_channels = [
        # (channel_id, title, description, published_at, country, language, custom_url)
        ("CH_LOFI_01", "Lofi AI Dreamer", "Chill Lofi beats created by advanced AI. Relax, study, sleep.", "2025-01-10T12:00:00Z", "US", "en", "@lofi_ai_dreamer"),
        ("CH_LOFI_02", "로파이 연구소 AI", "인공지능이 생성한 감성적인 로파이 비트입니다. 공부할 때 듣기 좋은 음악.", "2025-03-15T05:00:00Z", "KR", "ko", "@lofi_lab_ai"),
        ("CH_COVER_01", "AI Cover Universe", "K-Pop and J-Pop tracks reimagined with AI voice conversions.", "2025-04-20T08:00:00Z", "JP", "ja", "@ai_cover_uni"),
        ("CH_JAZZ_01", "Midnight AI Café", "Smooth jazz & bossa nova playlists created by AI.", "2024-11-01T15:00:00Z", "US", "en", "@midnight_ai_cafe"),
        ("CH_ASMR_01", "Acoustic AI Healing", "Cozy ASMR ambient soundscapes and acoustic guitar playlist.", "2025-05-02T10:00:00Z", "KR", "ko", "@acoustic_ai_healing"),
        ("CH_SYNTH_01", "CyberSynth AI", "Synthwave and cyberpunk music produced by AI tools.", "2025-02-18T14:00:00Z", "US", "en", "@cybersynth_ai"),
        ("CH_ANIME_01", "NeoAnime Beats", "AI Remixed Anime Soundtracks. Perfect for gaming.", "2025-03-30T11:00:00Z", "JP", "ja", "@neoanime_beats"),
        ("CH_KPOP_01", "AI K-Pop Star", "AI generated K-pop styles & virtual idols playlist.", "2025-05-12T09:00:00Z", "KR", "ko", "@ai_kpop_star"),
        
        # 신규 국가 및 구독자 수 구간별 세분화 채널
        ("CH_IND_01", "Bollywood AI Lounge", "Indian classical and R&B beats remixed by AI.", "2026-01-05T09:00:00Z", "IN", "en", "@bollywood_ai_lounge"), # ~500명 미만 (구독자 450명)
        ("CH_BR_01", "Samba Wave AI", "Brazilian Samba & Electro/EDM beats generated by AI.", "2026-05-20T10:00:00Z", "BR", "pt", "@samba_wave_ai"), # 100명 미만 (구독자 85명)
        ("CH_GB_01", "Royal Cinematic AI", "Epic orchestral and cinematic soundtracks by AI.", "2024-05-15T08:00:00Z", "GB", "en", "@royal_cinematic_ai"), # 1만명 이상 (구독자 12000명)
        ("CH_FR_01", "Café de Paris AI", "Accordion tunes, French Pop, and Cafe BGM by AI.", "2025-11-20T11:00:00Z", "FR", "fr", "@cafe_de_paris_ai"), # ~1천명 미만 (구독자 950명)
        ("CH_IT_01", "Classical Guitar AI", "Acoustic folk and classical guitar masterworks by AI.", "2025-07-04T12:00:00Z", "IT", "it", "@classical_guitar_ai"), # ~1만명 미만 (구독자 6500명)
        ("CH_CN_01", "Guzheng Ambient AI", "Traditional Chinese Guzheng mixed with Deep Relax Sleep music.", "2026-02-12T13:00:00Z", "CN", "zh", "@guzheng_ambient_ai"), # ~500명 미만 (구독자 280명)
        ("CH_RAP_01", "AI BoomBap Beats", "90s style Hip-hop & Rap instrumental beats by AI.", "2025-09-01T15:00:00Z", "US", "en", "@ai_boombap_beats"), # ~1만명 미만 (구독자 3200명)
        ("CH_ROCK_01", "Cyber Metal AI", "Heavy rock & metal generated by artificial neural networks.", "2025-04-18T16:00:00Z", "GB", "en", "@cyber_metal_ai"), # ~1만명 미만 (구독자 9800명)
        ("CH_CYBER_01", "Neo Tokyo Industrial", "Heavy industrial & cyberpunk beats by AI.", "2025-12-01T17:00:00Z", "JP", "ja", "@neo_tokyo_industrial"), # ~1천명 미만 (구독자 850명)
        ("CH_FANT_01", "Bardic Fantasy AI", "Medieval folk and fantasy ambient soundscapes by AI.", "2026-06-01T18:00:00Z", "FR", "fr", "@bardic_fantasy_ai"), # 100명 미만 (구독자 75명)
    ]
    
    for ch in mock_channels:
        cursor.execute('''
        INSERT OR REPLACE INTO channels (channel_id, title, description, published_at, country, language, custom_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ch)
    
    # 2. 채널별 일일 통계 시뮬레이션 (최근 15일치 데이터 축적)
    today = datetime.now()
    for channel_id, title, _, _, country, _, _ in mock_channels:
        # 가상 구독자 범위 타겟 설정
        if title == "로파이 연구소 AI":
            base_subs, base_views = 1500, 200000
            daily_sub_grow = lambda d: int(500 * (1.15 ** d))
            daily_view_grow = lambda d: int(10000 * (1.2 ** d))
        elif title == "AI K-Pop Star":
            base_subs, base_views = 800, 50000
            daily_sub_grow = lambda d: int(300 * (1.2 ** d))
            daily_view_grow = lambda d: int(8000 * (1.25 ** d))
        elif title == "Lofi AI Dreamer":
            base_subs, base_views = 85000, 12000000
            daily_sub_grow = lambda d: int(200 * d)
            daily_view_grow = lambda d: int(50000 * d)
        elif title == "Royal Cinematic AI":
            base_subs, base_views = 11500, 1500000
            daily_sub_grow = lambda d: int(40 * d)
            daily_view_grow = lambda d: int(15000 * d)
        elif title == "Samba Wave AI": # 100명 미만
            base_subs, base_views = 70, 500
            daily_sub_grow = lambda d: int(1.1 * d)
            daily_view_grow = lambda d: int(40 * d)
        elif title == "Bardic Fantasy AI": # 100명 미만
            base_subs, base_views = 60, 300
            daily_sub_grow = lambda d: int(1 * d)
            daily_view_grow = lambda d: int(20 * d)
        elif title == "Bollywood AI Lounge": # ~500명 미만
            base_subs, base_views = 400, 8000
            daily_sub_grow = lambda d: int(3.5 * d)
            daily_view_grow = lambda d: int(400 * d)
        elif title == "Guzheng Ambient AI": # ~500명 미만
            base_subs, base_views = 240, 5000
            daily_sub_grow = lambda d: int(2.8 * d)
            daily_view_grow = lambda d: int(300 * d)
        elif title == "Café de Paris AI": # ~1천명 미만
            base_subs, base_views = 900, 25000
            daily_sub_grow = lambda d: int(4 * d)
            daily_view_grow = lambda d: int(1200 * d)
        elif title == "Neo Tokyo Industrial": # ~1천명 미만
            base_subs, base_views = 800, 20000
            daily_sub_grow = lambda d: int(3.6 * d)
            daily_view_grow = lambda d: int(1000 * d)
        elif title == "Classical Guitar AI": # ~1만명 미만
            base_subs, base_views = 6200, 150000
            daily_sub_grow = lambda d: int(22 * d)
            daily_view_grow = lambda d: int(5500 * d)
        elif title == "AI BoomBap Beats":
            base_subs, base_views = 3000, 75000
            daily_sub_grow = lambda d: int(15 * d)
            daily_view_grow = lambda d: int(3500 * d)
        elif title == "Cyber Metal AI":
            base_subs, base_views = 9400, 380000
            daily_sub_grow = lambda d: int(28 * d)
            daily_view_grow = lambda d: int(8000 * d)
        else:
            base_subs = random.randint(3000, 15000)
            base_views = random.randint(100000, 800000)
            daily_sub_grow = lambda d: int(50 * d)
            daily_view_grow = lambda d: int(3000 * d)

        for d in range(15):
            date_str = (today - timedelta(days=(14 - d))).strftime("%Y-%m-%d")
            subs = base_subs + daily_sub_grow(d)
            views = base_views + daily_view_grow(d)
            video_count = 10 + (d // 3)
            
            cursor.execute('''
            INSERT OR REPLACE INTO channel_stats_daily (channel_id, view_count, subscriber_count, video_count, record_date)
            VALUES (?, ?, ?, ?, ?)
            ''', (channel_id, views, subs, video_count, date_str))
            
    # 3. 비디오 데이터 및 통계 시뮬레이션 (20개 세부 장르 커버)
    genres_pool = {
        "CH_LOFI_01": ("Lofi Study Beat", "chill, study, lofi, relaxing beats", "PT2H15M"),
        "CH_LOFI_02": ("공부할 때 듣는 감성 코딩 음악", "로파이, 코딩, 공부, lofi, sleep", "PT3H20M"),
        "CH_COVER_01": ("Famous K-pop hit but Sung by AI V", "cover, ai cover, kpop, bts", "PT3M45S"),
        "CH_JAZZ_01": ("Midnight Bossa Nova Playlist", "jazz, cafe, bossanova, ai music", "PT4H10M"),
        "CH_ASMR_01": ("Cozy Cabin Rain Sounds & Guitar", "asmr, rain, acoustic, sleep, ambient", "PT1H30M"),
        "CH_SYNTH_01": ("Retro Neon Ride: Synthwave Mix", "synthwave, cyberpunk, retrowave, gaming", "PT45M12S"),
        "CH_ANIME_01": ("Chill Anime AI Covers to Study", "anime, lofi, cover, beats", "PT1H15M"),
        "CH_KPOP_01": ("Next-gen Virtual Idol K-Pop Playlist", "kpop, virtual idol, ai pop, future", "PT25M10S"),
        
        # 신규 국가 채널 비디오 풀
        "CH_IND_01": ("Bollywood Chill R&B Night Mix", "bollywood, rnb, soul, indian classic, ai lounge", "PT1H05M"),
        "CH_BR_01": ("Rio Electro Samba Session", "samba, gaming, edm, pop, electro, dance", "PT55M30S"),
        "CH_GB_01": ("Epic Orchestral Cinematic Soundscapes", "cinematic, epic, orchestral, film score, battle", "PT2H30M"),
        "CH_FR_01": ("Romantic Accordion Café Parisienne BGM", "cafe, bgm, accordion, french pop, instrumental", "PT3H05M"),
        "CH_IT_01": ("Classical Guitar Masterworks for Focus", "classical, study, acoustic, folk, guitar", "PT1H45M"),
        "CH_CN_01": ("Sleep Deep Relax: Traditional Guzheng & Flute", "sleep, relax, guzheng, traditional, flute, ambient", "PT4H00M"),
        "CH_RAP_01": ("BoomBap Instrumental Hip-hop & Rap Beats", "hiphop, rap, boombap, instrumental, beats", "PT1H20M"),
        "CH_ROCK_01": ("Cyber Metal Symphonic Rock Mix", "rock, metal, symphonic, cyber, heavy, guitar", "PT50M15S"),
        "CH_CYBER_01": ("Neo Tokyo Industrial Cyberpunk Sound", "cyberpunk, industrial, electronic, techno, dystopia", "PT1H10M"),
        "CH_FANT_01": ("Medieval Folk Bardic Fantasy Ambient", "fantasy, medieval, folk, bard, dungeon, rpg", "PT2H10M"),
    }
    
    for channel_id, (vid_title, tag_str, duration) in genres_pool.items():
        # 각 채널마다 3개씩 비디오 등록
        for idx in range(3):
            video_id = f"VID_{channel_id}_{idx}"
            full_title = f"{vid_title} #{idx+1}"
            published_time = (today - timedelta(days=(10 - idx))).strftime("%Y-%m-%dT12:00:00Z")
            tags = tag_str.split(", ")
            
            cursor.execute('''
            INSERT OR REPLACE INTO videos (video_id, channel_id, title, description, published_at, duration, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (video_id, channel_id, full_title, f"This is a mock video for {full_title}", published_time, duration, ",".join(tags)))
            
            # 비디오 조회수 히스토리
            base_vid_views = random.randint(5000, 50000)
            for d in range(15):
                date_str = (today - timedelta(days=(14 - d))).strftime("%Y-%m-%d")
                vid_pub_date = (today - timedelta(days=(10 - idx))).strftime("%Y-%m-%d")
                if date_str >= vid_pub_date:
                    days_active = (datetime.strptime(date_str, "%Y-%m-%d") - datetime.strptime(vid_pub_date, "%Y-%m-%d")).days + 1
                    # 급성장 채널은 비디오 조회수 성장도 가파름
                    multiplier = 4.0 if channel_id in ["CH_LOFI_02", "CH_KPOP_01"] else 1.2
                    views = int(base_vid_views * (days_active ** multiplier) * 0.1)
                    likes = int(views * 0.05)
                    comments = int(views * 0.005)
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO video_stats_daily (video_id, view_count, like_count, comment_count, record_date)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (video_id, views, likes, comments, date_str))
                    
    conn.commit()
    print("Mock 데이터가 성공적으로 생성되었습니다.")

if __name__ == "__main__":
    run_collector()
