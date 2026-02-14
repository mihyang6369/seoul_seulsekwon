# ============================================================
# SEOUL SEULSEKWON DASHBOARD - REFACTORED VERSION 3.0
# ============================================================

import streamlit as st
import pandas as pd
import folium
import plotly.graph_objects as go
import plotly.express as px
from streamlit_folium import st_folium
import numpy as np
import os
import requests
import re
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="서울 슬세권 분석 대시보드",
    page_icon="🏙️",
    layout="wide"
)

DATA_DIR = "data/cleaned"
DEFAULT_RADIUS = 500

CATEGORY_GROUPS = {
    "교통": ["지하철", "버스"],
    "생활/상권": ["스타벅스", "소상공인", "대형마트"],
    "안전/의료": ["경찰", "병원", "금융"],
    "문화/환경": ["공원", "도서관", "서점", "학교"]
}

CATEGORY_CAPS = {
    "지하철": 2, "버스": 10,
    "스타벅스": 3, "소상공인": 80, "대형마트": 1,
    "경찰": 1, "병원": 5, "금융": 5,
    "공원": 2, "도서관": 1, "서점": 2, "학교": 3
}

# ============================================================
# 2. KAKAO API HANDLER
# ============================================================

class KakaoLocalAPI:
    def __init__(self):
        self.api_key = self._get_key()
        self.headers = {"Authorization": f"KakaoAK {self.api_key}"} if self.api_key else {}

    def _get_key(self):
        try:
            if "KAKAO_REST_API_KEY" in st.secrets:
                return st.secrets["KAKAO_REST_API_KEY"]
        except:
            pass
        return os.getenv("KAKAO_REST_API_KEY")

    def search(self, query):
        if not self.api_key:
            return None

        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        try:
            res = requests.get(url, headers=self.headers, params={"query": query})
            if res.status_code == 200:
                data = res.json()
                if data["documents"]:
                    doc = data["documents"][0]
                    return {
                        "name": doc.get("address_name", query),
                        "lat": float(doc["y"]),
                        "lon": float(doc["x"])
                    }
        except:
            pass
        return None

# ============================================================
# 3. DATA LOADING
# ============================================================

@st.cache_data
def load_data(data_dir):

    files = {
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

    dfs = []

    for cat, file in files.items():
        path = os.path.join(data_dir, file)
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")
            except:
                df = pd.read_csv(path, encoding="cp949")

            df = df.rename(columns={"위도":"lat","경도":"lon"})
            if "lat" in df.columns and "lon" in df.columns:
                df = df[["lat","lon"]].dropna()
                df["category"] = cat
                dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# ============================================================
# 4. DISTANCE ENGINE
# ============================================================

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians,[lon1,lat1,lon2,lat2])
    dlon = lon2-lon1
    dlat = lat2-lat1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2*asin(sqrt(a))*6371

# ============================================================
# 5. SCORE ENGINE
# ============================================================

def calculate_index(df, center_lat, center_lon, radius_km, weights):

    if df.empty:
        return 0, {}, pd.DataFrame()

    deg = radius_km / 111
    mask = (df.lat.between(center_lat-deg, center_lat+deg)) & \
           (df.lon.between(center_lon-deg, center_lon+deg))

    df2 = df[mask].copy()
    df2["dist"] = df2.apply(lambda r: haversine(center_lon,center_lat,r.lon,r.lat), axis=1)
    df_final = df2[df2.dist <= radius_km]

    counts = df_final.category.value_counts().to_dict()

    # 카테고리 점수
    cat_scores = {}
    for cat, cap in CATEGORY_CAPS.items():
        count = counts.get(cat,0)
        cat_scores[cat] = min(count/cap,1.0)*100

    # 그룹 점수
    group_scores = {}
    for group, cats in CATEGORY_GROUPS.items():
        group_scores[group] = np.mean([cat_scores.get(c,0) for c in cats])

    total_weight = sum(weights.values())
    if total_weight == 0:
        final = 0
    else:
        final = sum(group_scores[g]*weights[g] for g in weights)/total_weight

    return final, group_scores, df_final

# ============================================================
# 6. VISUALIZATION
# ============================================================

def create_radar(group_scores):

    labels = list(group_scores.keys())
    values = list(group_scores.values())

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill="toself",
        line=dict(color="#1062e0", width=3)
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
        showlegend=False
    )
    return fig

# ============================================================
# 7. STREAMLIT UI
# ============================================================

st.title("🏙️ 서울 슬세권 지수 대시보드")

api = KakaoLocalAPI()
data = load_data(DATA_DIR)

# Sidebar
st.sidebar.header("📍 주소 검색")

query = st.sidebar.text_input("주소 입력", value="서울시청")
search_btn = st.sidebar.button("검색")

if "center" not in st.session_state:
    st.session_state.center = {"lat":37.5665,"lon":126.9780,"name":"서울시청"}

if search_btn:
    res = api.search(query)
    if res:
        st.session_state.center = res

radius = st.sidebar.slider("반경 (m)",300,1500,DEFAULT_RADIUS,100)
radius_km = radius/1000

st.sidebar.subheader("⚖️ 가중치")

weights = {
    "교통": st.sidebar.slider("교통",0,100,30),
    "생활/상권": st.sidebar.slider("생활/상권",0,100,25),
    "안전/의료": st.sidebar.slider("안전/의료",0,100,20),
    "문화/환경": st.sidebar.slider("문화/환경",0,100,25)
}

# 계산
final_index, group_scores, df_near = calculate_index(
    data,
    st.session_state.center["lat"],
    st.session_state.center["lon"],
    radius_km,
    weights
)

# KPI
col1,col2,col3,col4,col5 = st.columns(5)
col1.metric("종합 지수",f"{final_index:.1f}")
for i,(g,v) in enumerate(group_scores.items()):
    [col2,col3,col4,col5][i].metric(g,f"{v:.1f}")

# 지도
col_map,col_chart = st.columns([2,1])

with col_map:
    m = folium.Map(
        location=[st.session_state.center["lat"],st.session_state.center["lon"]],
        zoom_start=15,
        tiles="CartoDB positron"
    )

    folium.Circle(
        location=[st.session_state.center["lat"],st.session_state.center["lon"]],
        radius=radius,
        color="#1062e0",
        fill=True,
        fill_opacity=0.1
    ).add_to(m)

    for _,row in df_near.iterrows():
        folium.CircleMarker(
            location=[row.lat,row.lon],
            radius=3,
            color="#e74c3c",
            fill=True
        ).add_to(m)

    st_folium(m,width="100%",height=500)

with col_chart:
    fig = create_radar(group_scores)
    st.plotly_chart(fig,use_container_width=True)

# 상세 테이블
st.divider()
st.subheader("📋 반경 내 시설 목록")

if not df_near.empty:
    df_show = df_near.copy()
    df_show["거리(m)"] = (df_show["dist"]*1000).astype(int)
    st.dataframe(df_show[["category","거리(m)"]], use_container_width=True)
else:
    st.info("시설 없음")

st.sidebar.caption("© 2026 Seulsekwon Analytics Engine v3.0")
