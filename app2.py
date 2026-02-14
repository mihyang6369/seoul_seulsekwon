import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import utils
import kakao_geo
import os

# Page Config
st.set_page_config(page_title="서울 슬세권 지수 대시보드", page_icon="🏙️", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #1e3a8a; color: white; }
    .score-card { 
        background-color: white; padding: 30px; border-radius: 15px; 
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); text-align: center;
        border-top: 5px solid #1e3a8a;
    }
    .metric-value { font-size: 50px; font-weight: bold; color: #1e3a8a; }
    .grade-badge { font-size: 24px; padding: 5px 15px; border-radius: 10px; color: white; background-color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# Data Load
if 'data' not in st.session_state:
    with st.spinner("🚀 데이터를 엔진에 로드 중입니다... 잠시만 기다려주세요."):
        st.session_state.data = utils.load_all_data()

# Session State for Location
if 'coords' not in st.session_state:
    st.session_state.coords = (37.5665, 126.9780) # Default: 서울시청
if 'address' not in st.session_state:
    st.session_state.address = "서울특별시 중구 세종대로 110"
if 'radius' not in st.session_state:
    st.session_state.radius = 500
if 'weights' not in st.session_state:
    st.session_state.weights = {
        "생활/편의🏪": 30, "교통🚌": 20, "의료💊": 15, "안전/치안🚨": 10,
        "교육/문화📚": 5, "자연/여가🌳": 15, "금융🏦": 5
    }

# --- SEARCH VIEW ---
st.title("🏙️ 서울시 '슬세권' 지수 분석 대시보드")
st.markdown("살기 좋은 서울, 우리 동네의 시설 접근성을 한눈에 분석하고 비교해보세요.")

with st.container():
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        address_query = st.text_input("📍 분석하고 싶은 주소나 장소를 입력하세요", placeholder="예: 강남역, 성수동, 서울시청 등")
    with col_s2:
        radius_input = st.select_slider("📏 분석 반경 (m)", options=[300, 500, 700, 1000, 1500], value=500)
    with col_s3:
        st.write("") # 패딩
        search_btn = st.button("🚀 지수 분석 시작")

if search_btn:
    if address_query:
        with st.spinner("🔍 위치 좌표를 검색 중입니다..."):
            result = kakao_geo.get_coords_from_address(address_query)
            if result:
                st.session_state.coords = result
                st.session_state.address = address_query
                st.session_state.radius = radius_input
                st.rerun()
            else:
                st.error("❌ 주소를 찾을 수 없습니다. 정확한 키워드로 다시 검색해주세요.")
    else:
        st.warning("⚠️ 주소를 입력해주세요.")

# --- RESULTS VIEW ---
if st.session_state.address:
    st.markdown("---")
    
    # 가중치 설정 (사이드바 - 검색 후에만 유효하게 보이도록 처리 가능)
    with st.sidebar:
        st.header("⚖️ 가중치 커스텀")
        st.caption("관심 있는 영역의 가중치를 조절해보세요 (총합 100 권장)")
        new_weights = {}
        for cat, val in st.session_state.weights.items():
            new_weights[cat] = st.slider(cat, 0, 50, val)
        if st.button("♻️ 가중치 적용"):
            st.session_state.weights = new_weights
            st.rerun()

    # 분석 수행
    total_score, scores, counts, facilities = utils.calculate_seulsekwon_index(
        st.session_state.coords[0], st.session_state.coords[1], 
        st.session_state.data, st.session_state.weights, st.session_state.radius
    )
    
    # 행정동 추출
    dong_name = utils.get_dong_name(st.session_state.address)
    
    # 시각화 데이터 생성
    viz = utils.create_visualizations(total_score, scores, counts, facilities, dong_name)
    
    # 레이아웃: 점수 및 주요 지표
    col_r1, col_r2, col_r3 = st.columns([1, 1, 1])
    
    with col_r1:
        grade = "C"
        if total_score >= 90: grade = "S (최상)"
        elif total_score >= 80: grade = "A (우수)"
        elif total_score >= 70: grade = "B (보통)"
        
        st.markdown(f"""
        <div class="score-card">
            <h3>{st.session_state.address}</h3>
            <div class="metric-value">{total_score}</div>
            <p>총점 100점 만점</p>
            <div class="grade-badge">{grade} 등급</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_r2:
        st.plotly_chart(viz['radar'], use_container_width=True)
        
    with col_r3:
        st.plotly_chart(viz['gauge'], use_container_width=True)

    # 레이아웃: 지도 및 비교
    col_m1, col_m2 = st.columns([1.5, 1])
    
    with col_m1:
        st.subheader("🗺️ 인터랙티브 시설 분포 지도")
        m = utils.create_enhanced_map(st.session_state.coords[0], st.session_state.coords[1], facilities, st.session_state.radius)
        map_out = st_folium(m, width="100%", height=500, key="main_map")
        
        # 지도 클릭 인터랙션
        if map_out and map_out.get("last_clicked"):
            new_c = (map_out["last_clicked"]["lat"], map_out["last_clicked"]["lng"])
            if round(new_c[0], 5) != round(st.session_state.coords[0], 5):
                st.session_state.coords = new_c
                st.session_state.address = f"지도 클릭 지점 ({new_c[0]:.4f}, {new_c[1]:.4f})"
                st.rerun()

    with col_m2:
        st.subheader("📊 지역 비교 분석")
        st.plotly_chart(viz['compare'], use_container_width=True)
        st.plotly_chart(viz['pie'], use_container_width=True)

    # 상세 트리맵
    if 'tree' in viz:
        st.markdown("---")
        st.subheader("🌳 시설 구성 상세 트리맵")
        st.plotly_chart(viz['tree'], use_container_width=True)

    # 시설 리스트
    with st.expander("📍 분석 반경 내 상세 시설 목록 확인하기"):
        if facilities:
            st.dataframe(pd.DataFrame(facilities)[['group', 'sub_category', 'name', 'distance', 'emoji']], use_container_width=True)
        else:
            st.write("반경 내에 분석된 시설이 없습니다.")

st.markdown("---")
st.caption("서울시 공개 데이터 및 Kakao Local API를 활용하여 제작되었습니다. Netlify 배포를 고려한 경량 구조입니다.")
