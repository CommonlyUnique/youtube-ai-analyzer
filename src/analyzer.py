import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 패키지 검색 경로에 현재 디렉토리 추가 (임포트 오류 방지)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection

def classify_genre(title, tags_str, custom_genres=None):
    """
    비디오 제목 및 태그를 가공하여 20가지 세부 장르 및 사용자가 추가한 커스텀 장르로 정밀 분류하는 룰베이스 분류기입니다.
    """
    text = f"{title} {tags_str}".lower()
    
    # 1. AI Cover (가장 특수한 형태)
    if any(k in text for k in ['cover', '커버', 'voice change']):
        return 'AI Cover'
    # 2. K-pop
    elif any(k in text for k in ['kpop', 'k-pop', '아이돌', 'idol', 'bts', 'blackpink']):
        return 'K-pop'
    # 3. J-pop
    elif any(k in text for k in ['jpop', 'j-pop', '제이팝', 'utaite', 'vocals']):
        return 'J-pop'
    # 4. Lofi/Chill
    elif any(k in text for k in ['lofi', 'chill', '로파이', 'chillhop']):
        return 'Lofi/Chill'
    # 5. Jazz/Bossa Nova
    elif any(k in text for k in ['jazz', '재즈', 'bossa', 'bossa nova']):
        return 'Jazz/Bossa Nova'
    # 6. Anime Beats
    elif any(k in text for k in ['anime', '애니', 'animix', 'ghibli', '지브리']):
        return 'Anime Beats'
    # 7. Synthwave/Retro
    elif any(k in text for k in ['synthwave', 'retrowave', 'synth', '레트로', 'retro', '80s']):
        return 'Synthwave/Retro'
    # 8. Cyberpunk/Industrial
    elif any(k in text for k in ['cyberpunk', 'industrial', 'techno', '사이버펑크', '테크노', 'dystopia']):
        return 'Cyberpunk/Industrial'
    # 9. Fantasy/Medieval
    elif any(k in text for k in ['fantasy', 'medieval', 'bard', 'rpg', '판타지', '중세풍']):
        return 'Fantasy/Medieval'
    # 10. Sleep/Deep Relax
    elif any(k in text for k in ['sleep', '수면', '꿀잠', '잠', 'deep relax', 'meditation', '명상']):
        return 'Sleep/Deep Relax'
    # 11. Classical/Study
    elif any(k in text for k in ['classical', 'study', '공부', '집중', 'focus', '클래식']):
        return 'Classical/Study'
    # 12. Café/BGM
    elif any(k in text for k in ['cafe', 'bgm', '카페', '배경음악', 'coffee', 'tea']):
        return 'Café/BGM'
    # 13. ASMR/Ambient
    elif any(k in text for k in ['asmr', 'soundscape', 'rain', '빗소리', '소리', '백색소음', 'ambient', 'healing', '힐링']):
        return 'ASMR/Ambient'
    # 14. Acoustic/Folk
    elif any(k in text for k in ['acoustic', 'folk', '어쿠스틱', '포크', '통기타', 'guitar']):
        return 'Acoustic/Folk'
    # 15. Gaming/EDM
    elif any(k in text for k in ['gaming', 'edm', 'electro', 'dance', '댄스', '클럽']):
        return 'Gaming/EDM'
    # 16. R&B/Soul
    elif any(k in text for k in ['rnb', 'r&b', 'soul', '소울', '알앤비']):
        return 'R&B/Soul'
    # 17. Hip-hop/Rap
    elif any(k in text for k in ['hiphop', 'hip-hop', 'rap', '힙합', '랩', 'boombap', 'trap']):
        return 'Hip-hop/Rap'
    # 18. Rock/Metal
    elif any(k in text for k in ['rock', 'metal', '락', '메탈', 'heavy metal', 'guitar solo']):
        return 'Rock/Metal'
    # 19. Cinematic/Epic
    elif any(k in text for k in ['cinematic', 'epic', 'orchestral', '오케스트라', '시네마틱', 'film score']):
        return 'Cinematic/Epic'
    # 20. Pop/Mainstream
    elif any(k in text for k in ['pop', 'mainstream', '빌보드', 'billboard', '팝']):
        return 'Pop/Mainstream'
    else:
        # 커스텀 동적 장르 키워드 매칭
        if custom_genres:
            base_genres = [
                'AI Cover', 'K-pop', 'J-pop', 'Lofi/Chill', 'Jazz/Bossa Nova',
                'Anime Beats', 'Synthwave/Retro', 'Cyberpunk/Industrial', 'Fantasy/Medieval',
                'Sleep/Deep Relax', 'Classical/Study', 'Café/BGM', 'ASMR/Ambient',
                'Acoustic/Folk', 'Gaming/EDM', 'R&B/Soul', 'Hip-hop/Rap', 'Rock/Metal',
                'Cinematic/Epic', 'Pop/Mainstream'
            ]
            for cg in custom_genres:
                if cg not in base_genres:
                    if cg.lower() in text:
                        return cg
        return 'Others'

def get_channel_analysis(country_filter=None):
    """
    각 채널의 일별 통계를 가공하여 최근 7일 성장성 및 효율성 지수를 산출합니다.
    """
    conn = get_db_connection()
    
    # 1. 채널 메타데이터 조회
    query_channels = "SELECT * FROM channels"
    if country_filter and country_filter != "전체":
        # SQLite 특성상 대소문자 매칭을 위해 LIKE 혹은 UPPER 사용
        query_channels += f" WHERE UPPER(country) = '{country_filter.upper()}'"
        
    df_ch = pd.read_sql_query(query_channels, conn)
    
    if df_ch.empty:
        conn.close()
        return pd.DataFrame()
        
    # 2. 일별 채널 통계 조회
    df_stats = pd.read_sql_query("SELECT * FROM channel_stats_daily ORDER BY record_date ASC", conn)
    conn.close()
    
    analysis_results = []
    
    for _, ch in df_ch.iterrows():
        ch_id = ch['channel_id']
        ch_stats = df_stats[df_stats['channel_id'] == ch_id].copy()
        
        if len(ch_stats) < 2:
            # 일일 통계 히스토리가 부족한 경우 스킵
            continue
            
        latest_row = ch_stats.iloc[-1]
        latest_subs = latest_row['subscriber_count'] or 0
        latest_views = latest_row['view_count'] or 0
        latest_video_count = latest_row['video_count'] or 0
        
        # 시계열 분석 (최근 7일 대비 이전 7일 비교)
        row_count = len(ch_stats)
        
        # 최근 7일 시점 (인덱스 -8, 데이터 부족 시 0번째 인덱스)
        row_idx_7d = max(0, row_count - 8)
        row_7d = ch_stats.iloc[row_idx_7d]
        
        views_7d_diff = latest_views - (row_7d['view_count'] or 0)
        subs_7d_diff = latest_subs - (row_7d['subscriber_count'] or 0)
        
        # 이전 7일 시점 (인덱스 -15, 데이터 부족 시 0번째 인덱스)
        row_idx_14d = max(0, row_count - 15)
        row_14d = ch_stats.iloc[row_idx_14d]
        
        views_prev_7d_diff = (row_7d['view_count'] or 0) - (row_14d['view_count'] or 0)
        
        # 1. 성장 속도 (Growth Velocity)
        # 이전 7일 조회수 증가량 대비 최근 7일 조회수 증가량의 변화량
        if views_prev_7d_diff > 0:
            growth_velocity = ((views_7d_diff - views_prev_7d_diff) / views_prev_7d_diff) * 100
        else:
            # 이전 성장이 없었다면 신규 상승이므로 높은 초기 속도 부여 혹은 0%
            growth_velocity = 100.0 if views_7d_diff > 0 else 0.0
            
        # 2. 채널 효율성 지수 (Efficiency Index)
        # 최근 7일 조회수 증가량 / 최신 구독자 수 (구독자 수 대비 폭발력 측정)
        # 구독자가 0인 신생 채널 분모 0 방지
        efficiency_index = views_7d_diff / max(1, latest_subs)
        
        analysis_results.append({
            "channel_id": ch_id,
            "title": ch['title'],
            "description": ch['description'],
            "country": ch['country'],
            "language": ch['language'],
            "custom_url": ch['custom_url'],
            "subscribers": latest_subs,
            "total_views": latest_views,
            "video_count": latest_video_count,
            "views_growth_7d": views_7d_diff,
            "subs_growth_7d": subs_7d_diff,
            "growth_velocity": round(growth_velocity, 1),
            "efficiency_index": round(efficiency_index, 2)
        })
        
    df_res = pd.DataFrame(analysis_results)
    if not df_res.empty:
        # 효율성 지수 순으로 기본 정렬
        df_res = df_res.sort_values(by="efficiency_index", ascending=False).reset_index(drop=True)
    return df_res

def get_niche_market_analysis(countries=None, sub_ranges=None, custom_genres=None):
    """
    장르별 수요(평균 조회수) 및 공급(채널 수, 비디오 개수)을 분석하여 니치 스코어를 산출합니다.
    다중 국가 필터(countries), 구독자 수 범위 필터(sub_ranges), 그리고 커스텀 장르(custom_genres)를 지원합니다.
    """
    conn = get_db_connection()
    
    # 각 비디오의 메타데이터와 최신 조회수, 그리고 채널의 최신 구독자 수를 Join하여 로드합니다.
    query = """
        SELECT v.video_id, v.channel_id, v.title, v.tags, c.country, vs.view_count as latest_view_count,
               cs.subscriber_count as latest_subscriber_count
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        LEFT JOIN video_stats_daily vs ON v.video_id = vs.video_id
        LEFT JOIN (
            SELECT channel_id, subscriber_count
            FROM channel_stats_daily
            WHERE record_date = (SELECT MAX(record_date) FROM channel_stats_daily)
        ) cs ON v.channel_id = cs.channel_id
        WHERE vs.record_date = (
            SELECT MAX(record_date) 
            FROM video_stats_daily 
            WHERE video_id = v.video_id
        )
    """
    
    df_v = pd.read_sql_query(query, conn)
    conn.close()
    
    if df_v.empty:
        return pd.DataFrame()
        
    # 1. 국가 필터링 적용 (다중 선택 대응)
    if countries:
        df_v = df_v[df_v['country'].str.upper().isin([c.upper() for c in countries])]
        
    # 2. 구독자 수 필터링 적용 (다중 선택 대응)
    if sub_ranges and not df_v.empty:
        cond = pd.Series([False] * len(df_v), index=df_v.index)
        for low, high in sub_ranges:
            if high is None:
                cond = cond | (df_v['latest_subscriber_count'] >= low)
            else:
                cond = cond | ((df_v['latest_subscriber_count'] >= low) & (df_v['latest_subscriber_count'] < high))
        df_v = df_v[cond]
        
    if df_v.empty:
        return pd.DataFrame()
        
    # 장르 분류 (커스텀 장르 리스트 전달)
    df_v['genre'] = df_v.apply(lambda row: classify_genre(row['title'], row['tags'] or '', custom_genres=custom_genres), axis=1)
    
    genre_stats = []
    
    # 장르별 그룹화 분석
    for genre, group in df_v.groupby('genre'):
        num_videos = len(group)
        num_channels = group['channel_id'].nunique()
        avg_views = group['latest_view_count'].mean() if not group['latest_view_count'].isnull().all() else 0
        total_views = group['latest_view_count'].sum()
        
        # 니치 스코어 (Niche Score)
        niche_score = avg_views / (num_channels + 1)
        
        genre_stats.append({
            "genre": genre,
            "video_count": num_videos,
            "channel_count": num_channels,
            "avg_views": round(avg_views, 1),
            "total_views": int(total_views),
            "niche_score": round(niche_score, 2)
        })
        
    df_genre = pd.DataFrame(genre_stats)
    if not df_genre.empty:
        # 니치 스코어 순 정렬
        df_genre = df_genre.sort_values(by="niche_score", ascending=False).reset_index(drop=True)
        
    return df_genre

if __name__ == "__main__":
    import sys
    # 윈도우 환경에서 UTF-8 출력을 강제하여 인코딩 오류 방지
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    print("=== 분석기 테스트 ===")
    print("1. 전체 국가 기준 급성장 채널:")
    df_channels = get_channel_analysis()
    if not df_channels.empty:
        print(df_channels[['title', 'country', 'subscribers', 'views_growth_7d', 'growth_velocity', 'efficiency_index']].head(5).to_string())
    else:
        print("분석 가능한 채널 데이터 없음")
        
    print("\n2. 전체 국가 기준 장르별 니치마켓:")
    df_niche = get_niche_market_analysis()
    if not df_niche.empty:
        print(df_niche.to_string())
    else:
        print("분석 가능한 장르 데이터 없음")
        
    print("\n3. 한국(KR) 국가 필터 적용 시 채널 분석:")
    df_kr = get_channel_analysis("KR")
    if not df_kr.empty:
        print(df_kr[['title', 'country', 'subscribers', 'views_growth_7d', 'efficiency_index']].to_string())
