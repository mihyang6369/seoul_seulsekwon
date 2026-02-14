import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
import os
import streamlit as st
import kakao_geo

# 카테고리별 이모지 매핑 (작업지시서 기준)
EMOJI_MAP = {
    "스타벅스": "☕",
    "편의점": "🏪",
    "세탁소": "🏪",
    "마트": "🏪",
    "대형마트": "🏬",
    "백화점": "🏬",
    "버스정류장": "🚌",
    "지하철역": "🚇",
    "병원": "🏥",
    "의원": "💊",
    "약국": "💊",
    "경찰서": "🚓",
    "파출소": "🚓",
    "도서관": "📚",
    "서점": "📚",
    "학교": "🏫",
    "공원": "🌳",
    "체육시설": "🏋️",
    "은행": "🏦",
    "금융": "🏦"
}

# 분석용 큰 카테고리 매핑
CATEGORY_GROUPS = {
    "생활/편의🏪": ["스타벅스", "편의점", "세탁소", "마트", "대형마트", "백화점"],
    "교통🚌": ["버스정류장", "지하철역"],
    "의료💊": ["병원", "의원", "약국"],
    "안전/치안🚨": ["경찰서", "파출소"],
    "교육/문화📚": ["도서관", "서점", "학교"],
    "자연/여가🌳": ["공원", "체육시설"],
    "금융🏦": ["은행", "금융"]
}

@st.cache_data
def load_all_data():
    """
    cleaned 폴더 내의 모든 CSV 데이터를 로드합니다.
    """
    # 배포 환경과 로컬 환경 모두 호환되도록 상대 경로를 사용합니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, "data", "cleaned")
    
    # 만약 위의 경로에 데이터가 없다면 (app.py 기준 실행 시)
    if not os.path.exists(base_path):
        base_path = os.path.join("data", "cleaned")
    
    # 작업지시서 기반 파일 매핑
    file_map = {
        "starbucks_seoul_cleaned.csv": "스타벅스",
        "bus_station_seoul_cleaned.csv": "버스정류장",
        "metro_station_seoul_cleaned.csv": "지하철역",
        "hospital_seoul_cleaned.csv": "병원",
        "police_seoul_cleaned_ver2.csv": "경찰서",
        "library_seoul_cleaned.csv": "도서관",
        "bookstore_seoul_cleaned.csv": "서점",
        "school_seoul_cleaned.csv": "학교",
        "park_raw_cleaned_revised.csv": "공원",
        "finance_seoul_cleaned.csv": "은행",
        "large_scale_shop_seoul_cleaned.csv": "대형마트",
        "sosang_seoul_cleaned.csv": "소상공인" # 필터링 필요
    }
    
    all_dfs = []
    for file, sub_cat in file_map.items():
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            encodings = ['utf-8-sig', 'cp949', 'utf-8', 'euc-kr']
            df = None
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except:
                    continue
            
            if df is not None:
                if sub_cat == "소상공인":
                    # 소상공인 데이터에서 세부 카테고리 추출
                    # 작업지시서: 편의점, 세탁소, 마트, 의원, 약국, 파출소, 체육시설 등
                    # 여기서는 간단히 카테고리_소 열을 활용
                    df['sub_category'] = df['카테고리_소']
                else:
                    df['sub_category'] = sub_cat
                
                # 공통 열 선택 (위도, 경도, 상호명/점포명)
                name_col = '상호명' if '상호명' in df.columns else ('점포명' if '점포명' in df.columns else '이름')
                if name_col in df.columns and '위도' in df.columns and '경도' in df.columns:
                    temp_df = df[[name_col, '위도', '경도', 'sub_category']].copy()
                    temp_df.columns = ['name', 'lat', 'lon', 'sub_category']
                    # 주소 정보도 있으면 행정동 추출을 위해 가져옴
                    if '주소' in df.columns:
                        temp_df['address'] = df['주소']
                    all_dfs.append(temp_df)
                    
    if not all_dfs:
        # 데이터가 없을 경우 기본 컬럼 구조를 가진 빈 데이터프레임 반환
        return pd.DataFrame(columns=['name', 'lat', 'lon', 'sub_category', 'address'])
    return pd.concat(all_dfs, ignore_index=True)

def calculate_seulsekwon_index(center_lat, center_lon, data, weights, radius_m):
    """
    작업지시서 공식을 기반으로 슬세권 지수를 산출합니다.
    """
    radius_km = radius_m / 1000.0
    scores = {}
    counts = {}
    nearby_facilities = []
    
    # 데이터가 비어있거나 필수 컬럼이 없는 경우 예외 처리
    if data.empty or 'lat' not in data.columns:
        empty_scores = {cat: 0.0 for cat in CATEGORY_GROUPS.keys()}
        empty_counts = {cat: 0 for cat in CATEGORY_GROUPS.keys()}
        return 0.0, empty_scores, empty_counts, []

    # 카테고리별 max 설정 (임의 기준값, 요구사항에 맞춰 조정 가능)
    max_counts = {
        "생활/편의🏪": 20, "교통🚌": 10, "의료💊": 8, "안전/치안🚨": 3,
        "교육/문화📚": 5, "자연/여가🌳": 5, "금융🏦": 5
    }

    # 위경도 박스 필터링 (속도 개선)
    lat_margin = radius_km / 111.0
    lon_margin = radius_km / 88.0
    mask = (data['lat'] >= center_lat - lat_margin) & (data['lat'] <= center_lat + lat_margin) & \
           (data['lon'] >= center_lon - lon_margin) & (data['lon'] <= center_lon + lon_margin)
    filtered_data = data[mask].copy()

    for group_name, sub_cats in CATEGORY_GROUPS.items():
        group_data = filtered_data[filtered_data['sub_category'].apply(lambda x: any(sc in str(x) for sc in sub_cats))]
        
        actual_count = 0
        for _, row in group_data.iterrows():
            dist = geodesic((center_lat, center_lon), (row['lat'], row['lon'])).meters
            if dist <= radius_m:
                actual_count += 1
                row_dict = row.to_dict()
                row_dict['distance'] = dist
                row_dict['group'] = group_name
                # 이모지 추가
                found_emoji = "📍"
                for key, emoji in EMOJI_MAP.items():
                    if key in str(row['sub_category']):
                        found_emoji = emoji
                        break
                row_dict['emoji'] = found_emoji
                nearby_facilities.append(row_dict)

        counts[group_name] = actual_count
        m = max_counts.get(group_name, 10)
        # 공식: (min(실제 개수, max) / max) * 가중치
        score = (min(actual_count, m) / m) * weights.get(group_name, 0)
        scores[group_name] = round(score, 2)

    total_score = sum(scores.values())
    return round(total_score, 1), scores, counts, nearby_facilities

def get_dong_name(address):
    """
    주소에서 행정동 이름을 추출합니다.
    """
    if not isinstance(address, str): return "알 수 없음"
    # 보통 ~동 으로 끝나는 단어 찾기
    import re
    match = re.search(r'([가-힣]+동)', address)
    if match: return match.group(1)
    return "서울시 전체"

def create_visualizations(total_score, scores, counts, facilities, dong_name):
    """
    5종 이상의 시각화 자료를 생성합니다.
    """
    viz = {}
    
    # 1. 영역별 레이더 차트
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=list(scores.values()) + [list(scores.values())[0]],
        theta=list(scores.keys()) + [list(scores.keys())[0]],
        fill='toself',
        fillcolor='rgba(30, 58, 138, 0.4)',  # 투명도 있는 남색 채우기
        line_color='#1e3a8a',
        name='영역별 점수'
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 30], gridcolor="#e2e8f0"),
            angularaxis=dict(gridcolor="#e2e8f0")
        ),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=20, b=20)
    )
    viz['radar'] = fig_radar

    # 2. 종합 지수 게이지 차트
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = total_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "종합 슬세권 지수", 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#1e3a8a"},
            'steps': [
                {'range': [0, 70], 'color': "#fee2e2"},
                {'range': [70, 80], 'color': "#fef3c7"},
                {'range': [80, 90], 'color': "#dcfce7"},
                {'range': [90, 100], 'color': "#dbeafe"}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': total_score}}))
    viz['gauge'] = fig_gauge

    # 3. 우리 동네 지수 비교 (임의의 동 평균값 시뮬레이션 - 실제 데이터 기반 시 부하 큼)
    # 실제로는 해당 동의 데이터 샘플을 통해 계산 가능하나, 여기서는 시각화 목적상 랜덤 보정값 사용
    avg_score = 75.5 # 서울시 평균 예시
    fig_compare = px.bar(
        x=[f"현재 위치 ({dong_name})", "서울시 평균"],
        y=[total_score, avg_score],
        color=[f"현재 위치 ({dong_name})", "서울시 평균"],
        labels={'x': '분석 대상', 'y': '지수'},
        title=f"'{dong_name}' vs 서울시 평균 비교"
    )
    fig_compare.update_layout(showlegend=False)
    viz['compare'] = fig_compare

    # 4. 인프라 구성 비율 (파이 차트)
    fig_pie = px.pie(
        names=list(counts.keys()),
        values=list(counts.values()),
        title="분역별 인프라 시설 비중",
        hole=.3
    )
    viz['pie'] = fig_pie

    # 5. 시설 구성 상세 (트리맵)
    facility_df = pd.DataFrame(facilities)
    if not facility_df.empty:
        fig_tree = px.treemap(
            facility_df, 
            path=['group', 'sub_category', 'name'], 
            values='distance', # 거리가 가까울수록 크게 표시할 순 없으니 반정렬 필요
            title="주변 시설 상세 분포 (트리맵)"
        )
        viz['tree'] = fig_tree
    
    return viz

def create_enhanced_map(lat, lon, facilities, radius_m):
    """
    이모지 마커가 포함된 지도를 생성합니다.
    """
    m = folium.Map(location=[lat, lon], zoom_start=16, tiles="cartodbpositron")
    
    # 기준점
    folium.Marker([lat, lon], icon=folium.Icon(color='red', icon='star')).add_to(m)
    folium.Circle([lat, lon], radius=radius_m, color='#3186cc', fill=True, fill_opacity=0.1).add_to(m)

    # 시설 마커 (이모지 활용)
    for f in facilities[:200]: # 성능을 위해 상위 200개만
        html = f"""
        <div style="font-size: 20px; background: white; border-radius: 50%; width: 30px; height: 30px; 
                    display: flex; align-items: center; justify-content: center; border: 2px solid #1e3a8a;">
            {f['emoji']}
        </div>
        """
        folium.Marker(
            [f['lat'], f['lon']],
            icon=folium.DivIcon(html=html),
            popup=f"{f['name']} ({f['distance']:.0f}m)"
        ).add_to(m)
        
    return m
