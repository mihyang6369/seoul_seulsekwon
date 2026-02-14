import streamlit as st
import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
import os
import requests
from dotenv import load_dotenv
from streamlit_folium import st_folium
import re
import base64
from io import BytesIO

# ==========================================
# 1. 환경 설정 및 상수 정의
# ==========================================
# 초보자 팁: 환경 변수(.env)는 API 키와 같은 민감 정보를 소스 코드와 분리하여 저장하는 장소입니다.
load_dotenv()

st.set_page_config(page_title="서울 슬세권 분석 리팩토링 앱", page_icon="🏙️", layout="wide")

# 세련된 디자인을 위한 컬러 코드 정의 (Hex Code)
PRIMARY_COLOR = "#3b82f6"   # 메인 파란색
SECONDARY_COLOR = "#1e293b" # 어두운 남색 (텍스트용)
ACCENT_COLOR = "#6366f1"    # 강조용 보라색
BACKGROUND_COLOR = "#f8fafc" # 은은한 배경색

# 이모지 맵: 시설 종류별로 아이콘을 지정합니다.
EMOJI_MAP = {
    "스타벅스": "☕", "카페": "☕", "편의점": "🏪", "세탁소": "🏪", "마트": "🏪", "대형마트": "🏬",
    "백화점": "🏬", "버스": "🚌", "bus": "🚌", "정류장": "🚌", "지하철": "🚇", 
    "역": "🚇", "병원": "🏥", "의원": "💊", "약국": "💊", "경찰": "🚓", 
    "도서관": "📚", "서점": "📚", "학교": "🏫", "공원": "🌳", "은행": "🏦"
}

# 카테고리 그룹: 여러 세부 시설을 하나의 큰 분석 단위로 묶습니다.
CATEGORY_GROUPS = {
    "생활/편의🏪": ["스타벅스", "편의점", "세탁소", "마트", "대형마트", "백화점", "카페"],
    "교통🚌": ["버스", "지하철", "정류장", "정류소", "역", "bus", "metro"],
    "의료💊": ["병원", "의원", "약국", "치과", "한의원"],
    "안전/치안🚨": ["경찰", "파출소", "치안", "소방", "119"],
    "교육/문화📚": ["도서관", "서점", "학교", "유치원", "학원"],
    "자연/여가🌳": ["공원", "체육", "운동", "산책", "park"],
    "금융🏦": ["은행", "금융", "ATM"]
}

# 기본 가중치 설정 (사용자 선호도에 따라 변경 가능)
DEFAULT_WEIGHTS = {"생활/편의🏪": 30, "교통🚌": 20, "의료💊": 15, "안전/치안🚨": 10, "교육/문화📚": 5, "자연/여가🌳": 15, "금융🏦": 5}

# 전역 스타일(CSS) 설정: 대시보드의 전체적인 분위기를 결정합니다.
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp {{ font-family: 'Inter', sans-serif; background-color: {BACKGROUND_COLOR}; }}
    .dashboard-card {{
        background: white; padding: 1.5rem; border-radius: 1.2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(226, 232, 240, 0.8); margin-bottom: 1.2rem;
    }}
    .metric-value {{
        font-size: 4rem; font-weight: 800;
        background: linear-gradient(135deg, {PRIMARY_COLOR}, {ACCENT_COLOR});
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 핵심 분석 로직 (엔진)
# ==========================================

def get_coords_from_address(address: str):
    """카카오 API를 통해 입력한 주소나 이름의 위경도 정보를 가져옵니다."""
    api_key = st.secrets.get("KAKAO_REST_API_KEY") or os.getenv("KAKAO_REST_API_KEY")
    if not api_key: return None
    
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        response = requests.get(url, headers=headers, params={"query": address})
        if response.status_code == 200:
            result = response.json()
            if result['documents']:
                info = result['documents'][0]
                return {"address_name": info['address_name'], "lat": float(info['y']), "lng": float(info['x'])}
    except: pass
    return None

@st.cache_data
def load_all_data():
    """프로젝트 내 정제된 CSV 데이터 파일들을 모두 불러와 통합합니다."""
    # 리팩토링 노트: 프로젝트 폴더 구조에 맞춘 상대 경로 설정
    base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/cleaned")
    if not os.path.exists(base_path): return pd.DataFrame()

    # 파일명과 기본 카테고리 매핑
    file_map = {
        'starbucks_seoul_cleaned.csv': '스타벅스', 'bus_station_seoul_cleaned.csv': '버스정류장',
        'metro_station_seoul_cleaned.csv': '지하철역', 'hospital_seoul_cleaned.csv': '병원',
        'police_seoul_cleaned_ver2.csv': '경찰서', 'library_seoul_cleaned.csv': '도서관',
        'bookstore_seoul_cleaned.csv': '서점', 'school_seoul_cleaned.csv': '학교',
        'park_raw_cleaned_revised.csv': '공원', 'finance_seoul_cleaned.csv': '은행',
        'large_scale_shop_seoul_cleaned.csv': '대형마트', 'sosang_seoul_cleaned_ver2.csv': '소상공인'
    }

    all_dfs = []
    # 컬럼명이 데이터마다 다를 수 있으므로 가능한 후보들을 정의합니다.
    lat_cols = ['위도', 'lat', 'latitude', '좌표정보(Y)']
    lon_cols = ['경도', 'lon', 'longitude', '좌표정보(X)']

    for file, default_cat in file_map.items():
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            try:
                # 인코딩 오류 방지 (utf-8-sig 선호)
                try: df = pd.read_csv(path, encoding='utf-8-sig')
                except: df = pd.read_csv(path, encoding='cp949')
                
                # '카테고리_소' 컬럼이 없으면 기본값 적용
                df['sub_category'] = df['카테고리_소'] if '카테고리_소' in df.columns else default_cat
                
                # 위경도 및 이름 컬럼 자동 매핑
                lat_c = next((c for c in lat_cols if c in df.columns), None)
                lon_c = next((c for c in lon_cols if c in df.columns), None)
                name_c = next((c for c in df.columns if any(k in str(c) for k in ['명', '이름', '역', '상호'])), df.columns[0])

                if lat_c and lon_c:
                    temp_df = df[[name_c, lat_c, lon_c, 'sub_category']].copy()
                    temp_df.columns = ['name', 'lat', 'lon', 'sub_category']
                    temp_df['lat'] = pd.to_numeric(temp_df['lat'], errors='coerce')
                    temp_df['lon'] = pd.to_numeric(temp_df['lon'], errors='coerce')
                    temp_df = temp_df.dropna(subset=['lat', 'lon'])
                    
                    # 위경도 값이 뒤바뀌어 있는 경우(서울 지역 특성상 위도 < 100) 자동 교정
                    if temp_df['lat'].mean() > 100:
                        temp_df['lat'], temp_df['lon'] = temp_df['lon'], temp_df['lat']
                    
                    # 서울 지역 데이터만 필터링 (이상치 제거)
                    mask = (temp_df['lat'] > 36) & (temp_df['lat'] < 39) & (temp_df['lon'] > 125) & (temp_df['lon'] < 129)
                    all_dfs.append(temp_df[mask])
            except: continue
    
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

def calculate_seulsekwon_index(center_lat, center_lon, data, weights, radius_m):
    """현재 위치(center_lat, lon) 기준으로 주변 인프라 점수를 계산합니다."""
    if data.empty: return 0.0, {}, {}, [], {}
    
    # 분석을 위한 좌표 범위 설정 (마진을 주어 연산 속도 향상)
    radius_km = radius_m / 1000.0
    lat_margin, lon_margin = radius_km / 111.0, radius_km / 88.0
    mask = (data['lat'] >= center_lat - lat_margin) & (data['lat'] <= center_lat + lat_margin) & \
           (data['lon'] >= center_lon - lon_margin) & (data['lon'] <= center_lon + lon_margin)
    filtered = data[mask].copy()

    # 각 그룹별 점수 산출 기준값 (이 개수가 있으면 100점 만점 기준)
    max_counts = {"생활/편의🏪": 15, "교통🚌": 8, "의료💊": 5, "안전/치안🚨": 1, "교육/문화📚": 2, "자연/여가🌳": 2, "금융🏦": 3}
    
    scores, counts, nearby, raw_scores = {}, {}, [], {}
    for g_name, sub_cats in CATEGORY_GROUPS.items():
        # 해당 카테고리에 속하는 시설들 필터링
        g_data = filtered[filtered['sub_category'].apply(lambda x: any(str(sc) in str(x) for sc in sub_cats))]
        
        group_list = []
        for _, row in g_data.iterrows():
            dist = geodesic((center_lat, center_lon), (row['lat'], row['lon'])).meters
            if dist <= radius_m:
                item = row.to_dict()
                item['distance'] = dist
                item['emoji'] = next((emoji for key, emoji in EMOJI_MAP.items() if key in str(row['sub_category'])), "📍")
                group_list.append(item)
        
        # 중복 제거 (이름이 같고 거리가 5m 이내면 동일 시설로 간주)
        final_group = []
        for item in sorted(group_list, key=lambda x: x['distance']):
            if not any(item['name'] == other['name'] and abs(item['distance']-other['distance']) < 5 for other in final_group):
                final_group.append(item)
        
        count = len(final_group)
        counts[g_name] = count
        nearby.extend(final_group)
        
        # 가중치 대비 점수 계산
        rate = min(count, max_counts.get(g_name, 5)) / max_counts.get(g_name, 5)
        raw_scores[g_name] = rate
        scores[g_name] = round(rate * weights.get(g_name, 0), 2)
    
    total = round(sum(scores.values()), 1)
    return total, scores, counts, sorted(nearby, key=lambda x: x['distance']), raw_scores

# ==========================================
# 3. Streamlit UI 실행부
# ==========================================

# 앱의 데이터 초기 로드
if 'app_data' not in st.session_state:
    st.session_state.app_data = load_all_data()

# 초기 설정값 (강남역 인근)
if 'st_coords' not in st.session_state:
    st.session_state.st_coords = (37.5006, 127.0363)
    st.session_state.st_address = "강남역"
    st.session_state.st_radius = 500

# 사이드바 설정 영역
with st.sidebar:
    st.title("⚙️ 분석 설정")
    query = st.text_input("📍 분석 위치 주소", value=st.session_state.st_address)
    rad = st.slider("📏 분석 반경 (m)", 300, 1000, st.session_state.st_radius, step=100)
    
    if st.button("🚀 분석 시작"):
        res = get_coords_from_address(query)
        if res:
            st.session_state.st_coords = (res['lat'], res['lng'])
            st.session_state.st_address = res['address_name']
            st.session_state.st_radius = rad
            st.rerun()

    st.divider()
    st.subheader("⚖️ 인프라 가중치 (%)")
    # 가중치 합이 100이 되도록 조심해야 합니다. (여기서는 슬라이더로만 구현)
    w = {}
    for cat, val in DEFAULT_WEIGHTS.items():
        w[cat] = st.sidebar.slider(cat, 0, 50, val, key=f"w_{cat}")

# 실시간 분석 수행
t_score, scores, counts, facilities, raw_scores = calculate_seulsekwon_index(
    st.session_state.st_coords[0], st.session_state.st_coords[1], st.session_state.app_data, w, st.session_state.st_radius
)

# 메인 대시보드 화면
st.header(f"🏙️ 서울 슬세권 분석 리포트: {st.session_state.st_address}")

# 1. 상단 분석 카드 및 지도
c1, c2 = st.columns([1, 1.8])

with c1:
    # 종합 지수 출력
    st.markdown(f'''
    <div class="dashboard-card" style="text-align: center;">
        <h3 style="margin-top:0;">종합 슬세권 지수</h3>
        <div class="metric-value">{t_score}</div>
        <p style="font-size: 1.2rem; color: #64748b;">분석 반경: {st.session_state.st_radius}m</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # 레이더 차트로 인프라 균형 확인
    fig = go.Figure(data=go.Scatterpolar(
        r=[v*100 for v in raw_scores.values()],
        theta=list(raw_scores.keys()), fill='toself'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=350, margin=dict(t=30, b=30))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    # 지도 출력
    m = folium.Map(location=st.session_state.st_coords, zoom_start=16, tiles="cartodbpositron")
    folium.Circle(st.session_state.st_coords, radius=st.session_state.st_radius, color=PRIMARY_COLOR, fill=True, fill_opacity=0.05).add_to(m)
    folium.Marker(st.session_state.st_coords, icon=folium.Icon(color='red', icon='home', prefix='fa')).add_to(m)
    
    # 주요 시설 100개 마커 표시
    for f in facilities[:100]:
        folium.Marker([f['lat'], f['lon']], popup=f['name'], 
                      tooltip=f"{f['emoji']} {f['name']}").add_to(m)
    
    st_folium(m, width="100%", height=550)

# 상세 리스트
st.divider()
st.subheader("📍 주변 주요 인프라 리스트")
if facilities:
    df_list = pd.DataFrame(facilities)[['emoji', 'sub_category', 'name', 'distance']]
    df_list.columns = ['아이콘', '분류', '시설명', '거리(m)']
    st.dataframe(df_list, use_container_width=True)
else:
    st.info("검색 반경 내에 결과가 없습니다.")

st.markdown("<div style='text-align: center; color: #94a3b8; padding: 2rem;'>© 2026 Seoul Seulsekwon Analytics Refactored</div>", unsafe_allow_html=True)
