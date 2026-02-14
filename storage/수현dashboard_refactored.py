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

# .env 파일 로드 (카카오 API 키 등 보안 변수 관리용)
# 초보자 팁: .env 파일은 API 키처럼 노출되면 안 되는 정보를 저장하는 비밀 장부입니다.
load_dotenv()

# --- 페이지 설정 ---
st.set_page_config(
    page_title="서울시 슬세권 지수 대시보드 v2 (리팩토링)",
    page_icon="🏙️",
    layout="wide"
)

# --- 커스텀 CSS (고급스러운 디자인 적용) ---
# 초보자 팁: CSS는 웹 페이지의 '글꼴, 색상, 배치' 등 디자인을 담당하는 코드입니다.
st.markdown("""
    <style>
    /* 폰트 로드: Pretendard (가독성이 좋은 프리미엄 폰트) */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 전체 배경: 화사한 라이트 블루 */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #f1f7fe !important;
    }
    
    /* 메트릭 카드: 깔끔한 화이트 카드 디자인 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0, 70, 150, 0.08);
        border: 1px solid #eef2f8;
    }
    
    /* 다방(Dabang) 스타일의 블루 테마 색상 적용 */
    div[data-testid="stMetricValue"] {
        color: #1062e0 !important;
        font-weight: 700 !important;
        font-size: 2.2rem !important;
    }
    
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e6ed;
    }
    
    /* 본문 폰트 설정 */
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# --- 카카오 로컬 API 핸들러 클래스 ---
# 초보자 팁: 클래스는 관련된 기능(함수)들을 하나로 묶어 관리하는 '기능 주머니'입니다.
class KakaoLocalHandler:
    def __init__(self):
        """API 키를 초기화합니다."""
        self.api_key = self._get_api_key()
        self.headers = {"Authorization": f"KakaoAK {self.api_key}"} if self.api_key else {}

    def _get_api_key(self):
        """환경 변수 또는 Streamlit secrets에서 API 키를 가져옵니다."""
        try:
            if "KAKAO_REST_API_KEY" in st.secrets:
                return st.secrets["KAKAO_REST_API_KEY"]
        except: pass
        return os.getenv("KAKAO_REST_API_KEY")

    def search_by_address(self, query):
        """주소 또는 키워드로 좌표(위도, 경도)를 검색합니다."""
        if not self.api_key:
            return {"status": "error", "message": "API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."}
            
        # 1. 키워드 검색 시도 (예: '강남역' 등 장소명)
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            # API 권한 문제 발생 시 상세 에러 메시지 반환
            if response.status_code in [401, 403]:
                return {"status": "error", "message": "Kakao API 키 권한 오류입니다."}

            if response.status_code == 200:
                data = response.json()
                if data['documents']:
                    doc = data['documents'][0]
                    return {
                        "status": "success",
                        "address_name": doc['address_name'] or doc.get('place_name', query),
                        "lat": float(doc['y']),
                        "lng": float(doc['x'])
                    }
            
            # 2. 결과가 없으면 상세 주소 검색 시도
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
                        "lng": float(doc['x'])
                    }
        except Exception as e:
            return {"status": "error", "message": f"연결 오류: {str(e)}"}
        return {"status": "fail", "message": "검색 결과를 찾을 수 없습니다."}

# --- 유틸리티 함수 (공통 기능들) ---
def get_dong_name(address):
    """주소 텍스트에서 '~~동' 형태의 행정동 이름을 추출합니다."""
    if not isinstance(address, str): return "알 수 없음"
    match = re.search(r'([가-힣]+동)', address)
    return match.group(1) if match else "서울시"

def haversine(lon1, lat1, lon2, lat2):
    """두 위경도 좌표 사이의 직선 거리(km)를 구합니다. (하버사인 공식)"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371

@st.cache_data
def load_and_preprocess_data(data_dir):
    """지정된 폴더에서 12개의 데이터 파일을 읽어 하나로 합칩니다."""
    # 리팩토링 노트: 경로가 프로젝트 루트의 data/cleaned를 바라보도록 상대 경로를 사용합니다.
    data_files = {
        "지하철": "metro_station_seoul_cleaned.csv",
        "버스": "bus_station_seoul_cleaned.csv",
        "스타벅스": "starbucks_seoul_cleaned.csv",
        "서점": "bookstore_seoul_cleaned.csv",
        "경찰": "police_seoul_cleaned_ver2.csv",
        "병원": "hospital_seoul_cleaned.csv",
        "금융": "finance_seoul_cleaned.csv",
        "도서관": "library_seoul_cleaned.csv",
        "공원": "park_raw_cleaned_revised.csv", # 파일명 수정
        "学校": "school_seoul_cleaned.csv",
        "소상공인": "sosang_seoul_cleaned.csv",
        "대형마트": "large_scale_shop_seoul_cleaned.csv"
    }
    
    combined_list = []
    # 데이터 폴더가 존재하지 않을 경우를 대비한 처리
    if not os.path.exists(data_dir):
        # 현재 파일의 위치를 기준으로 data 폴더를 찾습니다.
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/cleaned")

    for label, filename in data_files.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            try:
                # 한국어 깨짐 방지를 위해 cp949와 utf-8-sig를 순차적으로 시도합니다.
                try: df = pd.read_csv(path, encoding='utf-8-sig')
                except: df = pd.read_csv(path, encoding='cp949')
                
                # 좌표 컬럼 이름을 표준화 (여러 데이터의 형식을 하나로 맞춤)
                col_rename = {'위도': 'lat', '경도': 'lon', 'X좌표': 'lon', 'Y좌표': 'lat', 'y': 'lat', 'x': 'lon'}
                df = df.rename(columns=col_rename)
                
                # 시설명 추출 (데이터마다 다른 컬럼명을 'name'으로 통일)
                name_candidates = ['시설명', '점포명', '상호명', '역명', '관서명', '학교명', '공원명', '도서관명', '정류소명']
                df['name'] = '정보없음'
                for col in name_candidates:
                    if col in df.columns:
                        df['name'] = df[col]
                        break
                
                if 'lat' in df.columns and 'lon' in df.columns:
                    # 필수 데이터만 추출 후 카테고리 태그 추가
                    df = df[['lat', 'lon', 'name']].dropna(subset=['lat', 'lon'])
                    df['category'] = label
                    combined_list.append(df)
            except Exception as e:
                st.warning(f"{filename} 파일을 읽는 중 오류 발생: {e}")
    
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- 메인 실행 로직 ---
# 리팩토링 노트: 하드코딩된 절대 경로를 삭제하고 상대 경로를 사용합니다.
CURRENT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data/cleaned")
raw_df = load_and_preprocess_data(DATA_DIR)

# --- 사이드바: 검색 및 설정 ---
st.sidebar.title("🔍 슬세권 주소 검색")
kakao_handler = KakaoLocalHandler()

# API 키가 환경 변수에 없는 경우 안내
if not kakao_handler.api_key:
    st.sidebar.error("⚠️ 카카오 API 키가 설정되지 않았습니다.")

search_query = st.sidebar.text_input("분석할 주소(예: 강남역)", value="서울시청")
search_button = st.sidebar.button("검색 및 분석 시작")

st.sidebar.divider()
st.sidebar.subheader("📐 가중치 설정 (%)")
# 초보자 팁: 슬라이더를 사용하여 각 인프라의 중요도를 조절할 수 있습니다.
w_traffic = st.sidebar.slider("교통 편의", 0, 100, 30)
w_life = st.sidebar.slider("생활/상권", 0, 100, 25)
w_safety = st.sidebar.slider("안전/의료", 0, 100, 20)
w_culture = st.sidebar.slider("문화/환경", 0, 100, 25)

# 분석 반경 설정 (수현 버전은 500m 고정)
radius_km = 0.5

# --- 카테고리 필터 관리 ---
all_cats = sorted(raw_df['category'].unique()) if not raw_df.empty else []
if 'selected_cats' not in st.session_state:
    st.session_state['selected_cats'] = all_cats

st.sidebar.subheader("🏗️ 시설 표시 필터")
selected_cats = st.sidebar.multiselect("지도에 표시할 시설 선택", all_cats, key='selected_cats_multi')

# --- 검색 처리 ---
if 'target_pos' not in st.session_state:
    st.session_state['target_pos'] = {"lat": 37.5665, "lng": 126.9780, "name": "서울시청"}

if search_button:
    with st.spinner("위치 정보를 가져오는 중..."):
        res = kakao_handler.search_by_address(search_query)
        if res['status'] == 'success':
            st.session_state['target_pos'] = {"lat": res['lat'], "lng": res['lng'], "name": res['address_name']}
            st.rerun()
        else:
            st.sidebar.error(res.get('message', '결과 없음'))

target_lat = st.session_state['target_pos']['lat']
target_lon = st.session_state['target_pos']['lng']
target_name = st.session_state['target_pos']['name']

# --- 지수 계산 로직 ---
def calculate_seulsekwon_index(df_final, weights):
    # 각 시설물 카테고리별로 만점 기준 개수 설정
    caps = {"지하철": 2, "버스": 8, "스타벅스": 3, "소상공인": 50, "병원": 5, "경찰": 1, "금융": 5, "공원": 2, "도서관": 1, "서점": 2, "학교": 2, "대형마트": 1}
    
    counts = df_final['category'].value_counts().to_dict()
    scores = {cat: min(counts.get(cat, 0)/cap, 1.0)*100 for cat, cap in caps.items()}
    
    # 그룹별 점수 통합
    group_scores = {
        "traffic": (scores.get("지하철", 0) * 0.7 + scores.get("버스", 0) * 0.3),
        "life": (scores.get("스타벅스", 0)*0.3 + scores.get("소상공인", 0)*0.5 + scores.get("대형마트", 0)*0.2),
        "safety": (scores.get("경찰", 0)*0.4 + scores.get("병원", 0)*0.4 + scores.get("금융", 0)*0.2),
        "culture": (scores.get("공원", 0)*0.3 + scores.get("도서관", 0)*0.2 + scores.get("서점", 0)*0.2 + scores.get("학교", 0)*0.3)
    }
    
    # 최종 가중치 합산 (총합의 비율로 계산)
    total_w = sum(weights.values()) or 1
    final_score = sum(group_scores[k] * weights[k] for k in group_scores) / total_w
    return final_score, group_scores

# --- 데이터 필터링 및 분석 실행 ---
if not raw_df.empty:
    # 하버사인 공식을 사용하여 기준 위치 주변 시설만 추출
    mask = raw_df.apply(lambda r: haversine(target_lon, target_lat, r['lon'], r['lat']) <= radius_km, axis=1)
    df_final = raw_df[mask].copy()
    
    weights = {"traffic": w_traffic, "life": w_life, "safety": w_safety, "culture": w_culture}
    final_index, group_scores = calculate_seulsekwon_index(df_final, weights)
else:
    final_index, group_scores = 0, {k: 0 for k in ["traffic", "life", "safety", "culture"]}
    df_final = pd.DataFrame()

# --- 메인 화면 구성 ---
st.title("🏙️ 서울시 슬세권 지수 대시보드")
st.markdown(f"**기준 위치:** `{target_name}`")

# 주요 수치 요약 (KPI 매트릭)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("슬세권 지수", f"{final_index:.1f}")
k2.metric("교통", f"{group_scores['traffic']:.1f}")
k3.metric("생활", f"{group_scores['life']:.1f}")
k4.metric("안전", f"{group_scores['safety']:.1f}")
k5.metric("문화", f"{group_scores['culture']:.1f}")

# 지도 및 차트 레이아웃
col_map, col_chart = st.columns([2, 1])

with col_map:
    # 지도 구성
    m = folium.Map(location=[target_lat, target_lon], zoom_start=15, tiles="CartoDB positron")
    
    # 500m 반경 표시
    folium.Circle([target_lat, target_lon], radius=500, color="#1062e0", fill=True, fill_opacity=0.05).add_to(m)
    
    # 시설물 마커 찍기 (필터링된 것만)
    display_df = df_final[df_final['category'].isin(st.session_state['selected_cats'])]
    for _, row in display_df.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=row['name'],
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
    
    # 기준점 마커
    folium.Marker([target_lat, target_lon], icon=folium.Icon(color='red', icon='home', prefix='fa')).add_to(m)
    
    st_folium(m, width="100%", height=500, returned_objects=[])

with col_chart:
    # 레이더 차트 (인프라 달성률 시각화)
    fig = go.Figure(data=go.Scatterpolar(
        r=[group_scores[k] for k in ["traffic", "life", "safety", "culture"]],
        theta=['교통', '생활', '안전', '문화'], fill='toself',
        line=dict(color='#1062e0'), fillcolor='rgba(16, 98, 224, 0.2)'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# 하단 상세 목록
st.divider()
st.subheader("📋 주변 시설 상세 리스트")
if not df_final.empty:
    st.dataframe(df_final[['category', 'name']].sort_values('category'), use_container_width=True)
else:
    st.info("반경 내에 시설이 검색되지 않았습니다.")

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Seoul Seulsekwon Dashboard v2.5")
