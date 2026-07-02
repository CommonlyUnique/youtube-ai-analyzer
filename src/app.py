import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from datetime import datetime

# 임포트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db import get_db_connection
from analyzer import get_channel_analysis, get_niche_market_analysis

# 1. Streamlit 앱 설정 및 프리미엄 테마 적용 (CSS)
st.set_page_config(
    page_title="유튜브 AI 음원 및 플레이리스트 트렌드 분석기",
    page_icon="🎵",
    layout="wide"
)

# 다크 모드에 어울리는 고품격 그래디언트 및 그림자 효과 추가
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF4B4B 0%, #8522f0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .card {
        background: linear-gradient(145deg, #1e222b, #15181e);
        border: 1px solid #2d323f;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        border-color: #8522f0;
    }
    
    .card-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 8px;
    }
    
    .card-url {
        font-size: 0.9rem;
        color: #ff4b4b;
        text-decoration: none;
        font-weight: 600;
        margin-bottom: 12px;
        display: inline-block;
    }
    
    .card-url:hover {
        text-decoration: underline;
    }
    
    .metric-container {
        display: flex;
        justify-content: space-between;
        margin-top: 15px;
        padding-top: 15px;
        border-top: 1px solid #2d323f;
    }
    
    .metric-box {
        text-align: center;
        flex: 1;
    }
    
    .metric-value {
        font-size: 1.2rem;
        font-weight: 800;
        color: #ffffff;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #888e9b;
        margin-top: 4px;
    }
    
    .badge {
        background-color: rgba(133, 34, 240, 0.2);
        color: #a78bfa;
        border: 1px solid rgba(133, 34, 240, 0.4);
        padding: 4px 8px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 5px;
    }
    
    .badge-efficiency {
        background-color: rgba(255, 75, 75, 0.2);
        color: #fca5a5;
        border: 1px solid rgba(255, 75, 75, 0.4);
    }
    
    /* 사이드바 마진 및 여백 좁히기 (미니멀 스타일) */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, 
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        margin-bottom: 2px !important;
        margin-top: 4px !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stSidebar"] div.row-widget.stCheckbox {
        margin-bottom: -15px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    [data-testid="stSidebar"] div.stButton button {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
        margin-top: 5px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stExpander"] {
        margin-top: -5px !important;
        margin-bottom: -5px !important;
    }
    [data-testid="stSidebar"] div.stTextInput {
        margin-top: -10px !important;
        margin-bottom: -5px !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎵 YouTube AI Music Trend Analyzer</div>', unsafe_allow_html=True)

# 2. 세션 상태 초기화 및 관리
if "custom_countries" not in st.session_state:
    st.session_state.custom_countries = ["KR", "US", "JP", "IN", "CN", "GB", "FR", "IT", "BR"]

if "custom_genres" not in st.session_state:
    st.session_state.custom_genres = [
        'Lofi/Chill', 'Jazz/Bossa Nova', 'ASMR/Ambient', 'AI Cover', 'Synthwave/Retro',
        'Anime Beats', 'K-pop', 'J-pop', 'Classical/Study', 'Acoustic/Folk',
        'Gaming/EDM', 'Sleep/Deep Relax', 'Café/BGM', 'R&B/Soul', 'Hip-hop/Rap',
        'Pop/Mainstream', 'Rock/Metal', 'Cinematic/Epic', 'Cyberpunk/Industrial', 'Fantasy/Medieval'
    ]

# 국가 코드 매핑 사전
country_mapping = {
    "KR": "한국", "US": "미국", "JP": "일본", "IN": "인도", "CN": "중국",
    "GB": "영국", "FR": "프랑스", "IT": "이탈리아", "BR": "브라질"
}

# 개별 체크박스 상태값 기본값 설정
for c in st.session_state.custom_countries:
    if f"chk_country_{c}" not in st.session_state:
        st.session_state[f"chk_country_{c}"] = True

for g in st.session_state.custom_genres:
    if f"chk_genre_{g}" not in st.session_state:
        st.session_state[f"chk_genre_{g}"] = True

# 토글 콜백 함수
def on_country_toggle():
    val = st.session_state.toggle_all_countries
    for c in st.session_state.custom_countries:
        st.session_state[f"chk_country_{c}"] = val

def on_genre_toggle():
    val = st.session_state.toggle_all_genres
    for g in st.session_state.custom_genres:
        st.session_state[f"chk_genre_{g}"] = val

# 사이드바 영역 콤팩트 렌더링
with st.sidebar:
    st.markdown("### 🔍 분석 설정")
    
    # 2-1. 국가 다중 선택 (토글 헤더 + expander)
    col_c_title, col_c_toggle = st.columns([3, 1])
    with col_c_title:
        st.markdown("**🌍 국가 필터**")
    with col_c_toggle:
        st.checkbox("전체", key="toggle_all_countries", value=True, on_change=on_country_toggle)
        
    with st.expander("상세 국가 목록", expanded=True):
        selected_countries = []
        for c in st.session_state.custom_countries:
            label = f"{country_mapping.get(c, c)} ({c})"
            if st.checkbox(label, key=f"chk_country_{c}"):
                selected_countries.append(c)
                
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        new_country = st.text_input("새 국가 추가 (예: CA)", key="input_new_country").strip().upper()
        if st.button("국가 추가", key="btn_add_country"):
            if new_country and new_country not in st.session_state.custom_countries:
                st.session_state.custom_countries.append(new_country)
                st.session_state[f"chk_country_{new_country}"] = True
                st.rerun()

    st.markdown("---")
    
    # 2-2. 구독자 수 범위 선택 (가로 슬라이더 바 스크롤 적용)
    st.markdown("**👥 구독자 수 범위**")
    sub_options = ["0", "100", "500", "1K", "10K", "100K+"]
    sub_range_selected = st.select_slider(
        "범위 슬라이더",
        options=sub_options,
        value=("0", "100K+"),
        label_visibility="collapsed"
    )
    
    sub_mapping = {
        "0": 0, "100": 100, "500": 500, "1K": 1000, "10K": 10000, "100K+": 999999999
    }
    low_str, high_str = sub_range_selected
    low_val = sub_mapping[low_str]
    high_val = sub_mapping[high_str]
    if high_str == "100K+":
        selected_sub_ranges = [(low_val, None)]
    else:
        selected_sub_ranges = [(low_val, high_val)]

    st.markdown("---")

    # 2-3. 장르 선택 (토글 헤더 + expander)
    col_g_title, col_g_toggle = st.columns([3, 1])
    with col_g_title:
        st.markdown("**🎵 장르 필터**")
    with col_g_toggle:
        st.checkbox("전체", key="toggle_all_genres", value=True, on_change=on_genre_toggle)
        
    with st.expander("상세 장르 목록", expanded=False):
        selected_genres = []
        for g in st.session_state.custom_genres:
            if st.checkbox(g, key=f"chk_genre_{g}"):
                selected_genres.append(g)
                
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        new_genre = st.text_input("새 장르 추가 (예: Lofi Trap)", key="input_new_genre").strip()
        if st.button("장르 추가", key="btn_add_genre"):
            if new_genre and new_genre not in st.session_state.custom_genres:
                st.session_state.custom_genres.append(new_genre)
                st.session_state[f"chk_genre_{new_genre}"] = True
                st.rerun()

    # 만약 아무것도 선택 안했을 경우, UX 차원에서 전체 선택으로 간주
    if not selected_countries:
        selected_countries = st.session_state.custom_countries
    if not selected_genres:
        selected_genres = st.session_state.custom_genres

    st.markdown("---")
    st.subheader("데이터 업데이트")
    if st.button("🔄 유튜브 최신 데이터 수집 및 갱신"):
        with st.spinner("유튜브 데이터를 가져오고 있습니다... (약 1분 소요)"):
            # collector.py 실행
            import subprocess
            result = subprocess.run([sys.executable, "src/collector.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.success("데이터 갱신 완료!")
                st.rerun()
            else:
                st.error("데이터 갱신 실패. 터미널 로그를 확인해 주세요.")

# 3. 데이터 로딩 및 다중 필터 적용
# 3-1. 채널 데이터 로드 후 필터링
df_channels_all = get_channel_analysis(None)

if not df_channels_all.empty:
    # 국가 필터 적용
    df_channels = df_channels_all[df_channels_all['country'].str.upper().isin([c.upper() for c in selected_countries])]
    # 구독자 수 필터 적용
    if not df_channels.empty:
        cond = pd.Series([False] * len(df_channels), index=df_channels.index)
        for low, high in selected_sub_ranges:
            if high is None:
                cond = cond | (df_channels['subscribers'] >= low)
            else:
                cond = cond | ((df_channels['subscribers'] >= low) & (df_channels['subscribers'] < high))
        df_channels = df_channels[cond]
else:
    df_channels = pd.DataFrame()

# 3-2. 니치마켓 데이터 (집계 전 국가 및 구독자 필터 적용을 위해 인자로 전달, custom_genres 포함)
df_niche_all = get_niche_market_analysis(
    countries=selected_countries, 
    sub_ranges=selected_sub_ranges,
    custom_genres=selected_genres
)

# 장르 필터 적용
if not df_niche_all.empty:
    df_niche = df_niche_all[df_niche_all['genre'].isin(selected_genres)]
else:
    df_niche = pd.DataFrame()

# 4. 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["🔥 급상승 채널 Top 20", "💎 블루오션 니치마켓 분석", "📈 채널 성장 트렌드 상세", "🔍 레퍼런스 채널 진단"])

# --- TAB 1: 급성장 채널 Top 10 ---
with tab1:
    st.subheader("🚀 구독자 대비 조회수 폭발 알짜 채널")
    st.write("채널 효율성 지수(최근 7일 조회수 증가 / 구독자 수)가 높은 상위 채널들입니다. 신생 채널의 니치마켓 진입 전략 수립에 좋은 벤치마킹 대상이 됩니다.")
    
    if df_channels.empty:
        st.warning("분석할 채널 데이터가 존재하지 않습니다.")
    else:
        # 상위 20개 추출
        top_20 = df_channels.head(20)
        
        # 카드를 2열 레이아웃으로 출력
        cols = st.columns(2)
        for idx, row in enumerate(top_20.itertuples(index=False)):
            col_idx = idx % 2
            with cols[col_idx]:
                custom_url = getattr(row, 'custom_url', None)
                channel_id = getattr(row, 'channel_id', '')
                channel_url = f"https://www.youtube.com/{custom_url}" if custom_url else f"https://www.youtube.com/channel/{channel_id}"
                subscribers = getattr(row, 'subscribers', 0)
                views_growth = getattr(row, 'views_growth_7d', 0)
                velocity = getattr(row, 'growth_velocity', 0)
                desc = getattr(row, 'description', '') or '설명이 없는 채널입니다.'
                desc_short = desc[:150] + '...' if len(desc) > 150 else desc
                eff = getattr(row, 'efficiency_index', 0)
                country = getattr(row, 'country', '')
                title = getattr(row, 'title', '')
                vel_color = '#4ade80' if velocity >= 0 else '#f87171'
                
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <span class="card-title">🏆 {idx+1}. {title}</span>
                        <div>
                            <span class="badge badge-efficiency">효율성: {eff}</span>
                            <span class="badge">{country}</span>
                        </div>
                    </div>
                    <a href="{channel_url}" target="_blank" class="card-url">🔗 유튜브 채널 바로가기 {custom_url or ''}</a>
                    <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; min-height: 50px;">
                        {desc_short}
                    </p>
                    <div class="metric-container">
                        <div class="metric-box">
                            <div class="metric-value">{subscribers:,}</div>
                            <div class="metric-label">구독자 수</div>
                        </div>
                        <div class="metric-box" style="border-left: 1px solid #2d323f; border-right: 1px solid #2d323f;">
                            <div class="metric-value">+{views_growth:,}</div>
                            <div class="metric-label">7일 조회수 증가</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-value" style="color: {vel_color}">
                                {velocity}%
                            </div>
                            <div class="metric-label">성장 속도</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- TAB 2: 블루오션 니치마켓 분석 ---
with tab2:
    st.subheader("📊 장르별 수요-공급 포지셔닝 맵")
    st.write("유튜브 비디오의 제목 및 태그 데이터를 바탕으로 공급(업로드된 비디오 수) 대비 수요(평균 조회수)를 평가하여 블루오션 영역을 식별합니다.")
    
    if df_niche.empty:
        st.warning("분석할 장르 데이터가 존재하지 않습니다.")
    else:
        # 1. 니치마켓 Scatter Plot 작성
        avg_video_count = df_niche['video_count'].mean()
        avg_avg_views = df_niche['avg_views'].mean()
        
        fig = px.scatter(
            df_niche,
            x="video_count",
            y="avg_views",
            size="niche_score",
            color="genre",
            hover_name="genre",
            text="genre",
            labels={
                "video_count": "공급량 (활성 비디오 수)",
                "avg_views": "수요량 (비디오당 평균 조회수)",
                "niche_score": "니치 스코어 (진입 매력도)"
            },
            title="음악 장르별 수요 vs 공급 (원 크기는 니치 매력도를 나타냄)"
        )
        
        # 4분면 가이드라인 라인 추가 (중앙값/평균 기준)
        fig.add_vline(x=avg_video_count, line_width=1, line_dash="dash", line_color="gray")
        fig.add_hline(y=avg_avg_views, line_width=1, line_dash="dash", line_color="gray")
        
        # 디자인 개선
        fig.update_layout(
            plot_bgcolor="rgba(30, 34, 43, 0.4)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(showgrid=True, gridcolor='#2d323f'),
            yaxis=dict(showgrid=True, gridcolor='#2d323f')
        )
        fig.update_traces(textposition='top center')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. 블루오션 매트릭스 설명 가이드
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("""
            ### 🧭 4분면 해석 가이드
            * **좌상단 (블루오션 - Blue Ocean) ⭐**:
              - 공급(비디오 개수)은 적은데, 수요(평균 조회수)는 월등히 높은 장르입니다. **신규 채널 개설 시 가장 추천하는 영역입니다.**
            * **우상단 (레드오션 - Red Ocean)**:
              - 수요와 공급 모두 높은 주류 시장입니다. 대기업이나 기성 대형 채널이 점유하고 있어 경쟁이 매우 치열합니다.
            * **좌하단 (니치마켓 - Niche/Emerging)**:
              - 아직 수요와 공급 모두 미미한 장르이지만 향후 성장할 가능성이 있는 대안 마켓입니다.
            * **우하단 (과잉경쟁 - High Competition)**:
              - 수요에 비해 공급이 너무 많아 진입 시 조회수 확보가 어려운 시장입니다.
            """)
        with col2:
            st.markdown("### 💎 니치 매력도 순위 (Niche Score)")
            # 표 렌더링
            st.dataframe(
                df_niche[['genre', 'video_count', 'channel_count', 'avg_views', 'niche_score']],
                use_container_width=True,
                column_config={
                    "genre": "장르",
                    "video_count": "비디오 개수 (공급)",
                    "channel_count": "경쟁 채널 수",
                    "avg_views": "평균 조회수 (수요)",
                    "niche_score": "니치 매력도 점수"
                }
            )

# --- TAB 3: 채널 성장 트렌드 상세 ---
with tab3:
    st.subheader("📈 채널 성장 상세 시계열 추이")
    
    if df_channels.empty:
        st.warning("분석할 채널이 없습니다.")
    else:
        # 분석 대상 채널 선택 셀렉트박스
        selected_ch_title = st.selectbox("분석 대상 채널을 선택하세요", df_channels['title'].unique())
        selected_ch_id = df_channels[df_channels['title'] == selected_ch_title]['channel_id'].values[0]
        
        # 데이터베이스에서 해당 채널의 일별 데이터 로딩
        conn = get_db_connection()
        df_daily = pd.read_sql_query(
            f"SELECT record_date, subscriber_count, view_count FROM channel_stats_daily WHERE channel_id = '{selected_ch_id}' ORDER BY record_date ASC", 
            conn
        )
        conn.close()
        
        if df_daily.empty:
            st.info("해당 채널의 시계열 데이터가 존재하지 않습니다.")
        else:
            # 조회수 및 구독자 증가율 차트 작성
            fig_trend = go.Figure()
            
            # 구독자 수 (Y1축)
            fig_trend.add_trace(go.Scatter(
                x=df_daily['record_date'],
                y=df_daily['subscriber_count'],
                name="구독자 수 (명)",
                line=dict(color="#FF4B4B", width=3)
            ))
            
            # 누적 조회수 (Y2축)
            fig_trend.add_trace(go.Scatter(
                x=df_daily['record_date'],
                y=df_daily['view_count'],
                name="누적 조회수 (회)",
                yaxis="y2",
                line=dict(color="#8522f0", width=3)
            ))
            
            # 이중 축 레이아웃 구성
            fig_trend.update_layout(
                title=f"{selected_ch_title} 채널 성장 지표 (구독자 & 조회수)",
                xaxis=dict(title="날짜", gridcolor='#2d323f'),
                yaxis=dict(title=dict(text="구독자 수 (명)", font=dict(color="#FF4B4B")), tickfont=dict(color="#FF4B4B"), gridcolor='#2d323f'),
                yaxis2=dict(
                    title=dict(text="누적 조회수 (회)", font=dict(color="#8522f0")),
                    tickfont=dict(color="#8522f0"),
                    overlaying="y",
                    side="right"
                ),
                plot_bgcolor="rgba(30, 34, 43, 0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                legend=dict(x=0.01, y=0.99)
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # 채널의 비디오 리스트 및 상세 수치 출력
            st.markdown(f"#### 🎥 {selected_ch_title} 채널의 주요 업로드 비디오")
            conn = get_db_connection()
            df_videos = pd.read_sql_query(f"""
                SELECT v.title, v.duration, v.published_at, vs.view_count, vs.like_count
                FROM videos v
                LEFT JOIN video_stats_daily vs ON v.video_id = vs.video_id
                WHERE v.channel_id = '{selected_ch_id}'
                AND vs.record_date = (SELECT MAX(record_date) FROM video_stats_daily WHERE video_id = v.video_id)
                ORDER BY vs.view_count DESC
            """, conn)
            conn.close()
            
            if df_videos.empty:
                st.write("등록된 비디오 데이터가 없습니다.")
            else:
                # 비디오 정보 포맷팅
                df_videos['published_at'] = pd.to_datetime(df_videos['published_at']).dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(
                    df_videos,
                    use_container_width=True,
                    column_config={
                "title": "비디오 제목",
                        "duration": "재생시간",
                        "published_at": "업로드 일시",
                        "view_count": "조회수",
                        "like_count": "좋아요 수"
                    }
                )

# --- TAB 4: 레퍼런스 채널 진단 ---
with tab4:
    st.subheader("🔍 레퍼런스 채널 성공/취약 포인트 진단")
    st.write(
        "분석하고 싶은 유튜브 채널의 URL을 입력하면, 수집된 데이터를 기반으로 "
        "채널의 강점(성공 포인트)과 개선이 필요한 취약점(Weak Point)을 자동으로 진단합니다."
    )

    ref_url = st.text_input(
        "📋 채널 URL 또는 채널 ID 입력",
        placeholder="예: https://www.youtube.com/@lofi_lab_ai  또는  CH_LOFI_02",
        key="ref_channel_url"
    )

    if st.button("🔬 채널 분석 시작", key="btn_analyze_ref", type="primary"):
        if not ref_url.strip():
            st.warning("채널 URL을 입력해 주세요.")
        else:
            import re
            ref_id = None
            ref_custom = None

            match_custom = re.search(r'youtube\.com/(@[\w\-\.]+)', ref_url)
            if match_custom:
                ref_custom = match_custom.group(1)
            match_id = re.search(r'youtube\.com/channel/([\w\-]+)', ref_url)
            if match_id:
                ref_id = match_id.group(1)
            if not ref_custom and not ref_id and ref_url.strip().startswith('@'):
                ref_custom = ref_url.strip()
            if not ref_custom and not ref_id:
                ref_id = ref_url.strip()

            conn = get_db_connection()
            if ref_custom:
                df_ref = pd.read_sql_query(
                    "SELECT * FROM channels WHERE custom_url = ?", conn,
                    params=(ref_custom,)
                )
                if df_ref.empty:
                    alt = ref_custom.lstrip('@')
                    df_ref = pd.read_sql_query(
                        "SELECT * FROM channels WHERE custom_url LIKE ?", conn,
                        params=(f"%{alt}%",)
                    )
            else:
                df_ref = pd.read_sql_query(
                    "SELECT * FROM channels WHERE channel_id = ?", conn,
                    params=(ref_id,)
                )

            if df_ref.empty:
                conn.close()
                st.error("❌ 해당 채널을 DB에서 찾을 수 없습니다. 수집된 채널 목록 중 하나를 입력하거나, 데이터 수집 후 다시 시도해 주세요.")
                st.info("💡 현재 수집된 채널 목록은 '급상승 채널 Top 20' 탭에서 확인할 수 있습니다.")
            else:
                ch = df_ref.iloc[0]
                ch_id = ch['channel_id']
                ch_title = ch['title']

                df_stats = pd.read_sql_query(
                    "SELECT * FROM channel_stats_daily WHERE channel_id = ? ORDER BY record_date ASC",
                    conn, params=(ch_id,)
                )
                df_vids = pd.read_sql_query("""
                    SELECT v.title, v.tags, v.duration, v.published_at,
                           MAX(vs.view_count) as max_views,
                           MAX(vs.like_count) as max_likes,
                           MAX(vs.comment_count) as max_comments
                    FROM videos v
                    LEFT JOIN video_stats_daily vs ON v.video_id = vs.video_id
                    WHERE v.channel_id = ?
                    GROUP BY v.video_id
                    ORDER BY max_views DESC
                """, conn, params=(ch_id,))
                conn.close()

                st.success(f"✅ **{ch_title}** 채널 분석 완료")
                st.markdown("---")

                latest = df_stats.iloc[-1] if not df_stats.empty else None
                oldest = df_stats.iloc[0] if not df_stats.empty else None

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                if latest is not None:
                    with col_m1:
                        st.metric("구독자 수", f"{int(latest['subscriber_count']):,}명")
                    with col_m2:
                        st.metric("누적 조회수", f"{int(latest['view_count']):,}회")
                    with col_m3:
                        growth = int(latest['subscriber_count']) - int(oldest['subscriber_count']) if oldest is not None else 0
                        st.metric("기간 내 구독자 증가", f"+{growth:,}명")
                    with col_m4:
                        st.metric("업로드 비디오 수", f"{len(df_vids)}개")

                st.markdown("---")

                # 성공 포인트 / 취약 포인트 분석
                success_points = []
                weak_points = []

                if not df_stats.empty and len(df_stats) >= 7:
                    recent = df_stats.tail(7)
                    prev = df_stats.iloc[-14:-7] if len(df_stats) >= 14 else df_stats.head(7)
                    recent_view_growth = int(recent['view_count'].iloc[-1]) - int(recent['view_count'].iloc[0])
                    prev_view_growth = int(prev['view_count'].iloc[-1]) - int(prev['view_count'].iloc[0])
                    recent_sub_growth = int(recent['subscriber_count'].iloc[-1]) - int(recent['subscriber_count'].iloc[0])

                    if recent_view_growth > prev_view_growth * 1.3:
                        success_points.append(f"📈 **조회수 급상승 중**: 최근 7일 조회수 증가량({recent_view_growth:,}회)이 이전 대비 130% 이상 성장하고 있습니다.")
                    elif recent_view_growth < prev_view_growth * 0.7:
                        weak_points.append(f"📉 **조회수 성장 둔화**: 최근 7일 조회수 증가량({recent_view_growth:,}회)이 이전 대비 30% 이상 하락했습니다.")

                    if latest is not None:
                        sub_count = int(latest['subscriber_count'])
                        if sub_count < 100:
                            if recent_sub_growth > 5:
                                success_points.append(f"🌱 **초기 채널 폭발 성장**: 구독자 {sub_count}명의 신생 채널임에도 최근 7일 {recent_sub_growth}명이 유입되었습니다.")
                            else:
                                weak_points.append(f"⚠️ **초기 구독자 확보 부진**: 아직 구독자가 {sub_count}명으로 채널 인지도 확산이 필요합니다.")
                        elif sub_count < 1000:
                            efficiency = recent_view_growth / sub_count if sub_count > 0 else 0
                            if efficiency > 10:
                                success_points.append(f"⚡ **높은 바이럴 효율**: 구독자 대비 조회수 효율 지수 {efficiency:.1f}로, 구독하지 않은 신규 시청자 유입이 활발합니다.")

                if not df_vids.empty:
                    avg_views = df_vids['max_views'].mean()
                    top_view = df_vids['max_views'].max()

                    if top_view > avg_views * 5:
                        hit_video = df_vids.iloc[0]['title']
                        success_points.append(f"🎯 **히트작 보유**: '{hit_video[:30]}...' 등 평균 대비 5배 이상 조회된 대표 콘텐츠가 있습니다. 채널 성장의 핵심 동인입니다.")

                    if len(df_vids) >= 5:
                        success_points.append(f"📚 **콘텐츠 풍부도**: {len(df_vids)}개의 비디오를 보유하고 있어 시청자 체류 시간 확보에 유리합니다.")
                    elif len(df_vids) < 3:
                        weak_points.append(f"📂 **콘텐츠 부족**: 현재 비디오가 {len(df_vids)}개로 매우 적습니다. 꾸준한 업로드가 필요합니다.")

                    all_tags = []
                    for t in df_vids['tags'].dropna():
                        all_tags.extend([x.strip() for x in str(t).split(',')])
                    unique_tags = set(all_tags)
                    if len(unique_tags) >= 10:
                        success_points.append(f"🏷️ **태그 전략 우수**: {len(unique_tags)}개의 다양한 태그를 사용하여 검색 노출 범위가 넓습니다.")
                    elif len(unique_tags) < 5:
                        weak_points.append(f"🏷️ **태그 다양성 부족**: 사용 태그가 {len(unique_tags)}개로 적습니다. 더 많은 관련 키워드 태그로 검색 노출을 늘리세요.")

                    if avg_views < 100:
                        weak_points.append(f"👁️ **낮은 평균 조회수**: 비디오당 평균 조회수가 {avg_views:.0f}회로 매우 낮습니다. 썸네일과 제목 최적화를 권장합니다.")
                    elif avg_views > 10000:
                        success_points.append(f"👁️ **높은 평균 조회수**: 비디오당 평균 {avg_views:,.0f}회의 조회수는 해당 구독자 규모 대비 매우 우수한 수치입니다.")

                desc = ch.get('description', '') or ''
                if len(desc) < 50:
                    weak_points.append("📝 **채널 설명 부실**: 채널 소개 문구가 너무 짧거나 없습니다. SEO와 첫인상 개선을 위해 풍부한 채널 설명을 작성하세요.")
                elif len(desc) > 200:
                    success_points.append("📝 **채널 설명 충실**: 상세한 채널 소개가 작성되어 있어 채널의 전문성과 신뢰도를 높입니다.")

                # 결과 렌더링
                col_s, col_w = st.columns(2)
                with col_s:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, rgba(74,222,128,0.1), rgba(34,197,94,0.05));
                                border: 1px solid rgba(74,222,128,0.3); border-radius: 12px; padding: 20px;'>
                        <h3 style='color: #4ade80; margin-bottom: 16px;'>✅ 성공 포인트 (Strong Points)</h3>
                    """, unsafe_allow_html=True)
                    if success_points:
                        for sp in success_points:
                            st.markdown(f"<p style='color: #d1fae5; margin-bottom: 12px; line-height: 1.6;'>• {sp}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #86efac;'>아직 명확한 성공 패턴이 감지되지 않았습니다. 더 많은 데이터 수집 후 재분석하세요.</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                with col_w:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, rgba(248,113,113,0.1), rgba(239,68,68,0.05));
                                border: 1px solid rgba(248,113,113,0.3); border-radius: 12px; padding: 20px;'>
                        <h3 style='color: #f87171; margin-bottom: 16px;'>⚠️ 취약 포인트 (Weak Points)</h3>
                    """, unsafe_allow_html=True)
                    if weak_points:
                        for wp in weak_points:
                            st.markdown(f"<p style='color: #fecaca; margin-bottom: 12px; line-height: 1.6;'>• {wp}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color: #fca5a5;'>현재 수집된 데이터 내에서는 특별한 취약점이 발견되지 않았습니다.</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")

                # 성장 트렌드 미니 차트
                if not df_stats.empty:
                    st.markdown(f"#### 📊 {ch_title} 최근 성장 트렌드")
                    fig_ref = go.Figure()
                    fig_ref.add_trace(go.Scatter(
                        x=df_stats['record_date'], y=df_stats['subscriber_count'],
                        name="구독자 수", line=dict(color="#4ade80", width=2.5)
                    ))
                    fig_ref.add_trace(go.Scatter(
                        x=df_stats['record_date'], y=df_stats['view_count'],
                        name="조회수", yaxis="y2", line=dict(color="#a78bfa", width=2.5)
                    ))
                    fig_ref.update_layout(
                        height=280,
                        plot_bgcolor="rgba(30,34,43,0.4)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="white",
                        margin=dict(t=20, b=20),
                        yaxis=dict(
                            title=dict(text="구독자", font=dict(color="#4ade80")),
                            tickfont=dict(color="#4ade80"),
                            gridcolor='#2d323f'
                        ),
                        yaxis2=dict(
                            title=dict(text="조회수", font=dict(color="#a78bfa")),
                            tickfont=dict(color="#a78bfa"),
                            overlaying="y", side="right"
                        ),
                        legend=dict(x=0.01, y=0.99)
                    )
                    st.plotly_chart(fig_ref, use_container_width=True)

                # 인기 비디오 TOP 5
                if not df_vids.empty:
                    st.markdown("#### 🎬 인기 비디오 TOP 5")
                    df_top5 = df_vids.head(5)[['title', 'max_views', 'max_likes', 'max_comments', 'published_at']].copy()
                    df_top5['published_at'] = pd.to_datetime(df_top5['published_at']).dt.strftime('%Y-%m-%d')
                    st.dataframe(df_top5, use_container_width=True, column_config={
                        "title": "비디오 제목",
                        "max_views": st.column_config.NumberColumn("최고 조회수", format="%d회"),
                        "max_likes": st.column_config.NumberColumn("좋아요", format="%d"),
                        "max_comments": st.column_config.NumberColumn("댓글", format="%d"),
                        "published_at": "업로드일"
                    })
