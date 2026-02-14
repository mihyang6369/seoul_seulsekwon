import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np
import os
import requests
import re
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

# .env 파일 로드 (카카오 API 키 등 보안 변수 관리)
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="서울시 슬세권 지수 대시보드 v2",
    page_icon="🏙️",
    layout="wide"
)

# --- Custom CSS for Premium Look ---
st.markdown("""
    <style>
    /* 폰션 로드: Pretendard */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 전체 배경: 화사한 라이트 스카이 블루 */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #f1f7fe !important;
    }
    .main {
        background-color: #f1f7fe !important;
    }
    
    /* 메트릭 카드: 깔끔한 화이트 카드 + 부드러운 그림자 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0, 70, 150, 0.08);
        border: 1px solid #eef2f8;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 70, 150, 0.12);
    }
    
    /* 메트릭 라벨 및 값: 다방 블루 테마 */
    div[data-testid="stMetricLabel"] p {
        color: #6a748a !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        letter-spacing: -0.2px;
    }
    div[data-testid="stMetricValue"] {
        color: #1062e0 !important; /* 다방 메인 블루 */
        font-weight: 700 !important;
        font-size: 2.2rem !important;
    }
    
    /* 사이드바: 깨끗하고 정돈된 화이트/그레이 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e6ed;
    }
    
    /* 사이드바 텍스트/라벨 */
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] [data-testid="stSliderTickBar"] p,
    section[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] p {
        color: #333d4b !important;
        font-family: 'Pretendard', sans-serif;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #1062e0 !important;
    }
    
    /* 사이드바 버튼: 선명한 블루 버튼 */
    section[data-testid="stSidebar"] button {
        background-color: #1062e0 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px !important;
        font-weight: 700 !important;
        width: 100%;
    }
    section[data-testid="stSidebar"] button:hover {
        background-color: #0d4eb3 !important;
    }
    
    /* 제목 및 본문 폰트/색상 */
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, sans-serif;
    }
    h1, h2, h3 {
        color: #1a1f27 !important;
        font-weight: 700;
        letter-spacing: -0.8px;
    }
    .stMarkdown p, .stMarkdown span {
        color: #4e5968;
    }
    strong {
        color: #1a1f27 !important;
    }
    
    /* 범례 텍스트 색상 (라이트 모드용) */
    [data-testid="stCheckbox"] label p {
        color: #333d4b !important;
    }

    /* 입력창 스타일: 가시성 확보 및 소프트 쉐도우 */
    [data-testid="stTextInput"] input {
        border: 1px solid #d1d8e0 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05) !important;
        background-color: #ffffff !important;
        padding: 10px 14px !important;
        color: #1a1f27 !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #1062e0 !important;
        box-shadow: 0 0 0 2px rgba(16, 98, 224, 0.1) !important;
    }
    
    /* 슬라이더 컬러 변경 */
    .stSlider > div > div > div > div {
        background-color: #1062e0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Kakao REST API Handler ---
class KakaoLocalHandler:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.headers = {"Authorization": f"KakaoAK {self.api_key}"} if self.api_key else {}

    def _get_api_key(self):
        try:
            if "KAKAO_REST_API_KEY" in st.secrets:
                return st.secrets["KAKAO_REST_API_KEY"]
        except: pass
        return os.getenv("KAKAO_REST_API_KEY")

    def search_by_address(self, query):
        """주소 또는 키워드로 좌표를 검색합니다."""
        if not self.api_key:
            return {"status": "error", "message": "API 키가 설정되지 않았습니다."}
            
        # 키워드 검색을 우선 시도 (사용자 요청 로직 반영)
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            # 권한/설정 관련 상세 에러 처리
            if response.status_code in [401, 403]:
                err_data = response.json()
                msg = err_data.get('message', 'Access Denied')
                if "disabled" in msg:
                    msg = "카카오 개발자 센터에서 'Local' API 서비스를 활성화(ON)해주세요."
                elif "ip mismatched" in msg:
                    msg = "카카오 개발자 센터에서 현재 IP를 'IP 허용 리스트'에 추가하거나 기능을 꺼주세요."
                return {"status": "error", "message": f"Kakao API 권한 오류: {msg}"}

            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    doc = data['documents'][0]
                    return {
                        "status": "success",
                        "address_name": doc['address_name'] or doc.get('place_name', query),
                        "lat": float(doc['y']),
                        "lng": float(doc['x']),
                        "type": "keyword"
                    }
            
            # 키워드 결과 없으면 주소 검색 시도
            url = "https://dapi.kakao.com/v2/local/search/address.json"
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    doc = data['documents'][0]
                    return {
                        "status": "success",
                        "address_name": doc['address_name'],
                        "lat": float(doc['y']),
                        "lng": float(doc['x']),
                        "type": "address"
                    }
        except Exception as e:
            return {"status": "error", "message": f"연결 예외 발생: {str(e)}"}
        return {"status": "fail", "message": "결과를 찾을 수 없습니다."}

# --- Utility Functions ---
def get_dong_name(address):
    """주소에서 '동' 이름을 추출합니다."""
    if not isinstance(address, str): return "알 수 없음"
    match = re.search(r'([가-힣]+동)', address)
    return match.group(1) if match else "서울시 전체"
def haversine(lon1, lat1, lon2, lat2):
    """지구상의 두 지점 사이의 거리(km)를 계산합니다."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371

@st.cache_data
def load_and_preprocess_data(data_dir):
    """12개의 정제된 데이터셋을 로드하고 통합합니다."""
    data_files = {
        "지하철": "metro_station_seoul_cleaned.csv",
        "버스": "bus_station_seoul_cleaned.csv",
        "스타벅스": "starbucks_seoul_cleaned.csv",
        "서점": "bookstore_seoul_cleaned.csv",
        "경찰": "police_seoul_cleaned_ver2.csv",
        "병원": "hospital_seoul_cleaned.csv",
        "금융": "finance_seoul_cleaned.csv",
        "도서관": "library_seoul_cleaned.csv",
        "공원": "park_seoul_cleaned.csv",
        "학교": "school_seoul_cleaned.csv",
        "소상공인": "sosang_seoul_cleaned.csv",
        "대형마트": "large_scale_shop_seoul_cleaned.csv"
    }
    
    combined_list = []
    for label, filename in data_files.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            try:
                # 인코딩 대응 (utf-8-sig 선호)
                df = pd.read_csv(path, encoding='utf-8-sig')
            except:
                df = pd.read_csv(path, encoding='cp949')
            
            # 좌표 컬럼 통일
            df = df.rename(columns={'위도': 'lat', '경도': 'lon', 'X좌표': 'lon', 'Y좌표': 'lat'})
            
            # 시설명 컬럼 통일 (다양한 데이터셋의 시설명 컬럼 대응)
            name_cols = [
                '시설명', '점포명', '상호명', '역명', '관서명', '학교명', 
                '공원명', '도서관명', '서점명', '정류소명', '책방 이름', 
                '기관명', '지점명', '사업장명'
            ]
            df['name'] = 'Unknown'
            for col in name_cols:
                if col in df.columns:
                    df['name'] = df[col]
                    break
            
            if 'lat' in df.columns and 'lon' in df.columns:
                df = df[['lat', 'lon', 'name']].dropna(subset=['lat', 'lon'])
                df['category'] = label
                combined_list.append(df)
    
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- Main Logic ---
DATA_DIR = "/Users/kimsuhyun/Desktop/fcicb6/seoul_seulsekwon/data/cleaned"
raw_df = load_and_preprocess_data(DATA_DIR)

# --- Sidebar ---
# --- Sidebar API Logic ---
st.sidebar.title("🔍 슬세권 주소 검색")
# .env 또는 st.secrets에서 키를 자동으로 로드
kakao_handler = KakaoLocalHandler()

if not kakao_handler.api_key:
    st.sidebar.error("⚠️ 카카오 API 키가 설정되지 않았습니다. .env 파일에 'KAKAO_REST_API_KEY'를 입력해주세요.")

search_query = st.sidebar.text_input("분석할 주소 또는 장소 입력", value="서울시청")
search_button = st.sidebar.button("검색 및 분석 시작")

st.sidebar.divider()
st.sidebar.subheader("📐 가중치 설정 (%)")
w_traffic = st.sidebar.slider("교통 (지하철, 버스)", 0, 100, 30)
w_life = st.sidebar.slider("생활/상권 (스타벅스, 소상공인, 대형마트)", 0, 100, 25)
w_safety = st.sidebar.slider("안전/공공 (경찰, 병원, 금융)", 0, 100, 20)
w_culture = st.sidebar.slider("문화/환경 (공원, 서점, 도서관, 학교)", 0, 100, 25)

# 분석 반경 500m 고정
radius_km = 0.5

# --- Filter State Management ---
all_cats = sorted(raw_df['category'].unique()) if not raw_df.empty else []
if 'selected_cats' not in st.session_state:
    st.session_state['selected_cats'] = all_cats

st.sidebar.subheader("🏗️ 시설 카테고리 필터")
selected_cats = st.sidebar.multiselect(
    "지도에 표시할 시설", 
    all_cats, 
    key='selected_cats' # 세션 상태와 직접 연결
)

# --- Analysis Logic ---
if 'target_pos' not in st.session_state:
    st.session_state['target_pos'] = {"lat": 37.5665, "lng": 126.9780, "name": "서울시청"}

if search_button and kakao_handler:
    with st.spinner("주소 검색 및 데이터 분석 중..."):
        res = kakao_handler.search_by_address(search_query)
        if res['status'] == 'success':
            st.session_state['target_pos'] = {
                "lat": res['lat'], 
                "lng": res['lng'], 
                "name": res['address_name']
            }
            # 동 정보 추가 추출하여 상태 저장 (필요 시 활용)
            st.session_state['dong_name'] = get_dong_name(res['address_name'])
            st.rerun() # 기준 위치 변경을 위해 즉시 리런
        else:
            st.sidebar.error(res.get('message', '검색 결과가 없습니다.'))

target_lat = st.session_state['target_pos']['lat']
target_lon = st.session_state['target_pos']['lng']
target_name = st.session_state['target_pos']['name']
dong_label = get_dong_name(target_name)

# 거리 계산 및 필터링
if not raw_df.empty:
    df = raw_df.copy()
    # 대규모 연산 최적화를 위해 위경도 차이로 1차 필터링 후 Haversine 적용
    deg_diff = radius_km / 111.0 # 대략적인 위경도 1도 거리
    mask = (df['lat'] > target_lat - deg_diff) & (df['lat'] < target_lat + deg_diff) & \
           (df['lon'] > target_lon - deg_diff) & (df['lon'] < target_lon + deg_diff)
    
    df_near = df[mask].copy()
    if not df_near.empty:
        df_near['dist'] = df_near.apply(lambda r: haversine(target_lon, target_lat, r['lon'], r['lat']), axis=1)
        df_final = df_near[df_near['dist'] <= radius_km].copy()
    else:
        df_final = pd.DataFrame(columns=df.columns.tolist() + ['dist'])
else:
    df_final = pd.DataFrame()

# 지수 계산 (Seulsekwon Index)
def calculate_seulsekwon_index(counts, weights):
    # 각 카테고리별 상한값 (임의 설정, 실제 데이터 분포에 따라 조정 필요)
    caps = {
        "지하철": 2, "버스": 10, "스타벅스": 3, "소상공인": 100, 
        "병원": 5, "경찰": 1, "금융": 5, "공원": 2, "도서관": 1, "서점": 2, "학교": 3, "대형마트": 1
    }
    
    scores = {}
    for cat, cap in caps.items():
        count = counts.get(cat, 0)
        scores[cat] = min(count / cap, 1.0) * 100
        
    # 그룹별 점수
    group_scores = {
        "traffic": (scores.get("지하철", 0) * 0.7 + scores.get("버스", 0) * 0.3),
        "life": (scores.get("스타벅스", 0) * 0.4 + scores.get("소상공인", 0) * 0.4 + scores.get("대형마트", 0) * 0.2),
        "safety": (scores.get("경찰", 0) * 0.4 + scores.get("병원", 0) * 0.4 + scores.get("금융", 0) * 0.2),
        "culture": (scores.get("공원", 0) * 0.3 + scores.get("도서관", 0) * 0.3 + scores.get("서점", 0) * 0.2 + scores.get("학교", 0) * 0.2)
    }
    
    total_w = sum(weights.values())
    if total_w == 0: return 0, group_scores
    
    final_score = (group_scores['traffic'] * weights['traffic'] + 
                   group_scores['life'] * weights['life'] + 
                   group_scores['safety'] * weights['safety'] + 
                   group_scores['culture'] * weights['culture']) / total_w
    
    return final_score, group_scores

counts = df_final['category'].value_counts().to_dict()
weights = {"traffic": w_traffic, "life": w_life, "safety": w_safety, "culture": w_culture}
final_index, group_scores = calculate_seulsekwon_index(counts, weights)

# --- UI Content ---
st.title("🏙️ 서울시 슬세권 지수 대시보드")
st.markdown(f"**기준 위치:** {target_name} ({dong_label})")
st.caption(f"좌표: {target_lat:.5f}, {target_lon:.5f}")

# KPI 레이아웃
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1: st.metric("종합 슬세권 지수", f"{final_index:.1f}")
with kpi2: st.metric("교통 편의", f"{group_scores['traffic']:.1f}")
with kpi3: st.metric("생활/상권", f"{group_scores['life']:.1f}")
with kpi4: st.metric("안전/의료", f"{group_scores['safety']:.1f}")
with kpi5: st.metric("문화/환경", f"{group_scores['culture']:.1f}")

# Main Layout
col_map_area, col_chart = st.columns([2, 1])

with col_map_area:
    # 시설물별 아이콘 및 색상 정의
    cat_marker_settings = {
        "지하철": {"icon": "train", "color": "red", "prefix": "fa", "hex": "#d63031"},
        "버스": {"icon": "bus", "color": "orange", "prefix": "fa", "hex": "#e67e22"},
        "스타벅스": {"icon": "coffee", "color": "darkgreen", "prefix": "fa", "hex": "#1b4d3e"},
        "서점": {"icon": "book", "color": "brown", "prefix": "fa", "hex": "#6d4c41"},
        "경찰": {"icon": "shield", "color": "blue", "prefix": "fa", "hex": "#0984e3"},
        "병원": {"icon": "plus", "color": "pink", "prefix": "fa", "hex": "#e84393"},
        "금융": {"icon": "bank", "color": "cadetblue", "prefix": "fa", "hex": "#5f27cd"},
        "도서관": {"icon": "university", "color": "lightblue", "prefix": "fa", "hex": "#00d2d3"},
        "공원": {"icon": "leaf", "color": "green", "prefix": "fa", "hex": "#27ae60"},
        "학교": {"icon": "graduation-cap", "color": "purple", "prefix": "fa", "hex": "#6c5ce7"},
        "소상공인": {"icon": "shop", "color": "lightblue", "prefix": "fa", "hex": "#5BC0EB"},
        "대형마트": {"icon": "shopping-cart", "color": "darkblue", "prefix": "fa", "hex": "#2c3e50"}
    }
    
    col_map_sub, col_legend = st.columns([6, 1])
    
    with col_map_sub:
        # 지도 생성 (CartoDB positron 스타일 - 밝고 깨끗한 디자인)
        m = folium.Map(location=[target_lat, target_lon], zoom_start=15, tiles="CartoDB positron")
        
        # 1. 500m 반경 원 추가
        folium.Circle(
            location=[target_lat, target_lon],
            radius=radius_km * 1000,
            color="#1062e0", 
            fill=True,
            fill_color="#1062e0",
            fill_opacity=0.08,
            weight=2
        ).add_to(m)
        
        # 2. 시설물 마커 추가
        map_df = df_final[df_final['category'].isin(selected_cats)].copy()
        for _, row in map_df.iterrows():
            setting = cat_marker_settings.get(row['category'], {"icon": "info-sign", "color": "gray", "prefix": "glyphicon"})
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"{row['name']} ({row['category']})",
                icon=folium.Icon(color=setting['color'], icon=setting['icon'], prefix=setting['prefix'])
            ).add_to(m)
            
        # 3. 기준점 마커
        folium.Marker(
            location=[target_lat, target_lon],
            popup=f"기준: {target_name}",
            icon=folium.Icon(color='black', icon='home', prefix='fa')
        ).add_to(m)
        
        st_folium(m, width="100%", height=500, returned_objects=[])

    with col_legend:
        # 범례 최적화를 위한 CSS
        st.markdown("""
            <style>
            [data-testid="stCheckbox"] { 
                margin-bottom: -18px;
                padding-top: 0px;
            }
            [data-testid="stCheckbox"] label p {
                font-size: 0.75rem !important;
                white-space: nowrap !important;
                overflow: visible !important;
                font-weight: 500 !important;
                color: #c9d1d9 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # 전체 선택/해제 기능
        is_all_selected = len(st.session_state['selected_cats']) == len(all_cats)
        if st.checkbox("전체 선택", value=is_all_selected, key="select_all_cb"):
            if not is_all_selected:
                st.session_state['selected_cats'] = all_cats.copy()
                st.rerun()
        elif is_all_selected:
            st.session_state['selected_cats'] = []
            st.rerun()

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        for cat, s in cat_marker_settings.items():
            if cat in all_cats:
                is_checked = cat in st.session_state['selected_cats']
                
                # 컬러 도트와 체크박스를 가로로 배치 (다크 모드 가시성 확보)
                c1, c2 = st.columns([1, 6])
                with c1:
                    st.markdown(f"<div style='color:{s['hex']}; font-size: 1.2rem; margin-top: 8px;'>●</div>", unsafe_allow_html=True)
                with c2:
                    if st.checkbox(cat, value=is_checked, key=f"leg_cb_{cat}"):
                        if cat not in st.session_state['selected_cats']:
                            st.session_state['selected_cats'].append(cat)
                            st.rerun()
                    else:
                        if cat in st.session_state['selected_cats']:
                            st.session_state['selected_cats'].remove(cat)
                            st.rerun()

        st.markdown(f"""
            <div style='display: flex; align-items: center; margin-top: 25px; padding-top: 10px; border-top: 1px solid #edf2f7;'>
                <div style='width: 8px; height: 8px; background-color: #1a1f27; border-radius: 2px; margin-right: 6px;'></div>
                <span style='font-size: 0.75rem; color: #4e5968; font-weight: bold; white-space: nowrap;'>기준 위치</span>
            </div>
        """, unsafe_allow_html=True)

with col_chart:
    # 레이더 차트 (Plotly)
    categories_names = ['교통', '생활/상권', '안전/공공', '문화/환경']
    values = [group_scores['traffic'], group_scores['life'], group_scores['safety'], group_scores['culture']]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values, theta=categories_names, fill='toself', name='슬세권 지표',
        line=dict(color='#1062e0', width=3), fillcolor='rgba(16, 98, 224, 0.2)'
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#99a3ba", gridcolor="#eef2f8"), 
                   angularaxis=dict(color="#4e5968", gridcolor="#eef2f8"),
                   bgcolor="#ffffff"),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=50, l=50, r=50)
    )
    st.plotly_chart(fig, use_container_width=True)

# 상세 리스트
st.divider()
st.subheader("📋 반경 내 상세 시설 목록")
if not df_final.empty:
    display_df = df_final.sort_values('dist')[['category', 'name', 'dist']].copy()
    display_df['dist'] = display_df['dist'].apply(lambda x: f"{int(x*1000)}m")
    display_df.columns = ['카테고리', '시설명', '거리']
    st.dataframe(display_df, use_container_width=True, height=300)
else:
    st.info("선택한 반경 내에 시설이 없습니다.")

# 푸터
st.sidebar.markdown(f"---")
st.sidebar.caption("© 2026 Seoul Seulsekwon Dashbaord v2")
