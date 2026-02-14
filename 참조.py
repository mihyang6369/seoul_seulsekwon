import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import utils

# Page Configuration
st.set_page_config(
    page_title="서울시 슬세권 분석 대시보드",
    page_icon="",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #F0F2F6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title(" 서울시 슬세권(Sle-se-kwon) 지수 분석")
st.markdown("당신의 동네는 얼마나 살기 편한가요? 주소를 입력하고 슬세권 점수를 확인해보세요!")

# Load Data
with st.spinner('데이터를 불러오는 중입니다...'):
    data = utils.load_all_data()

if not data:
    st.error("데이터 로딩에 실패했습니다. data/cleaned 폴더를 확인해주세요.")
    st.stop()

# Sidebar - User Input
st.sidebar.header(" 분석 설정")

# Address Input
default_address = "서울특별시 강남구 테헤란로 427"
address = st.sidebar.text_input("주소를 입력하세요 (서울시 내)", value=default_address)

# Radius Slider
radius = st.sidebar.slider("분석 반경 (m)", min_value=300, max_value=1500, value=700, step=100)

# Weights
st.sidebar.subheader(" 가중치 설정")
weights = {}
with st.sidebar.expander("카테고리별 가중치 조절", expanded=True):
    weights['생활/편의'] = st.slider("생활/편의 (카페, 편의점)", 0.0, 2.0, 1.0, 0.1)
    weights['교통'] = st.slider("교통 (버스, 지하철)", 0.0, 2.0, 1.0, 0.1)
    weights['의료'] = st.slider("의료 (병원, 약국)", 0.0, 2.0, 1.0, 0.1)
    weights['안전/치안'] = st.slider("안전/치안 (경찰서)", 0.0, 2.0, 1.0, 0.1)
    weights['교육/문화'] = st.slider("교육/문화 (도서관, 학교)", 0.0, 2.0, 1.0, 0.1)
    weights['자연/여가'] = st.slider("자연/여가 (공원, 체육)", 0.0, 2.0, 1.0, 0.1)
    weights['금융'] = st.slider("금융 (은행)", 0.0, 2.0, 1.0, 0.1)

# Analysis Logic
if 'analyzed_coords' not in st.session_state:
    # Initialize with default address (Gangnam Teheran-ro 427) - Hardcoded to avoid API timeout on load
    default_lat, default_lon = 37.5061, 127.0543
    st.session_state.analyzed_coords = (default_lat, default_lon)
    st.session_state.current_address = "서울특별시 강남구 테헤란로 427"

    # Pre-populate facilities empty so filtering happens once
    st.session_state.nearby_facilities = []

def geocode_address(addr):
    coords = utils.get_coordinates(addr)
    return coords

map_clicked = False

# Sidebar Analysis Button
if st.sidebar.button("분석 시작", type="primary"):
    coords = geocode_address(address)
    if coords:
        st.session_state.analyzed_coords = coords
        st.session_state.current_address = address
    else:
        st.error("주소를 찾을 수 없습니다.")

# Main Layout
col1, col2 = st.columns([1, 2])

# Placeholder for map to be rendered later, but we need it for click interaction
# We can't easily perform "click analysis" without re-running. 
# Strategy: Render map first with default or last location. If clicked, update session_state.

with col2:
    st.subheader(" 주변 시설 지도")
    # Determine center
    if st.session_state.analyzed_coords:
        center_lat, center_lon = st.session_state.analyzed_coords
    else:
         # Default Seoul Center or initial address
        init_coords = geocode_address(default_address)
        if init_coords:
            center_lat, center_lon = init_coords
        else:
            center_lat, center_lon = 37.5665, 126.9780

    # Create Map interactively
    # We pass empty facilities first if not analyzed yet, or previous facilities
    # But wait, if we want to show results, we need calculations first.
    # Circular dependency? No, just use current state.

    nearby_facilities = st.session_state.get('nearby_facilities', [])
    m = utils.create_folium_map(center_lat, center_lon, nearby_facilities)

    # Render with st_folium to capture events
    map_data = st_folium(m, width="100%", height=500, key="folium_map")

    # Check for Click
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        new_lat, new_lon = clicked["lat"], clicked["lng"]

        # Only update if different enough to avoid infinite loops on re-render check
        if st.session_state.analyzed_coords != (new_lat, new_lon):
            st.session_state.analyzed_coords = (new_lat, new_lon)
            st.session_state.current_address = f"지점에서 선택된 위치 ({new_lat:.4f}, {new_lon:.4f})"
            st.rerun()

# Logic to calculate scores if coords exist
if st.session_state.analyzed_coords:
    lat, lon = st.session_state.analyzed_coords

    with st.spinner(f"분석 중... {st.session_state.get('current_address', '')}"):
        final_score, category_scores, facilities = utils.calculate_score(lat, lon, data, weights, radius)

        # Store facilities for map re-render (next run will show markers)
        # However, st_folium is already rendered above.
        # This is a classic Streamlit-Folium issue: update lag.
        # We need to re-render map if facilities changed? 
        # Actually, if we just calculated, the map above was rendered with OLD facilities (or empty).
        # We might need to force a rerun if this is a Fresh calculation that needs to update the Map.

        if st.session_state.get('nearby_facilities') != facilities:
            st.session_state.nearby_facilities = facilities
            st.rerun()

    with col1:
        # Score Display
        st.markdown(f"""
        <div class="metric-card">
            <h3>종합 슬세권 지수</h3>
            <h1 style="color: #4CAF50; font-size: 60px;">{final_score:.1f}</h1>
            <p>점</p>
        </div>
        """, unsafe_allow_html=True)

        # Grade
        grade = "C"
        if final_score >= 80: grade = "S (최상)"
        elif final_score >= 60: grade = "A (우수)"
        elif final_score >= 40: grade = "B (보통)"

        st.info(f"등급: **{grade}**")

        # Radar Chart
        fig = utils.create_radar_chart(category_scores)
        st.plotly_chart(fig, use_container_width=True)

    # Detailed Breakdown (Bottom)
    st.markdown("---")
    st.subheader(f"� 분석 위치: {st.session_state.get('current_address', 'Unknown')}")
    st.subheader(" 카테고리별 상세 점수 및 현황")

    cols = st.columns(3)
    idx = 0
    for cat, score in category_scores.items():
        with cols[idx % 3]:
            st.metric(label=cat, value=f"{score:.1f}점")
        idx += 1

    with st.expander("주변 시설 목록 보기"):
        if facilities:
            df_near = pd.DataFrame(facilities)
            df_near = df_near[['category', 'name', 'distance']]
            df_near['distance'] = df_near['distance'].apply(lambda x: f"{int(x)}m")
            df_near.columns = ['카테고리', '시설명', '거리']
            st.dataframe(df_near, use_container_width=True)
        else:
            st.write("반경 내 주요 시설이 없습니다.")

else:
    with col1:
        st.info("좌측 사이드바에서 주소를 입력하거나, 지도에서 위치를 클릭하세요.")