
import pandas as pd
import os
import re
from geopy.distance import geodesic

CATEGORY_GROUPS = {
    '생활/편의🏪': ['스타벅스', '편의점', '세탁소', '마트', '대형마트', '백화점'],
    '교통🚌': ['버스정류장', '지하철역'],
    '의료💊': ['병원', '의원', '약국'],
    '안전/치안🚨': ['경찰서', '파출소'],
    '교육/문화📚': ['도서관', '서점', '학교'],
    '자연/여가🌳': ['공원', '체육시설'],
    '금융🏦': ['은행', '금융']
}

def load_all_data():
    base_path = 'c:/Users/Administrator/Desktop/fcicb6/pj/seoul_seulsekwon/data/cleaned'
    file_map = {
        'starbucks_seoul_cleaned.csv': '스타벅스', 'bus_station_seoul_cleaned.csv': '버스정류장',
        'metro_station_seoul_cleaned.csv': '지하철역', 'hospital_seoul_cleaned.csv': '병원',
        'police_seoul_cleaned_ver2.csv': '경찰서', 'library_seoul_cleaned.csv': '도서관',
        'bookstore_seoul_cleaned.csv': '서점', 'school_seoul_cleaned.csv': '학교',
        'park_raw_cleaned_revised.csv': '공원', 'finance_seoul_cleaned.csv': '은행',
        'large_scale_shop_seoul_cleaned.csv': '대형마트', 'sosang_seoul_cleaned.csv': '소상공인'
    }
    all_dfs = []
    lat_cols = ['위도', 'lat', 'latitude', 'Y', 'y']
    lon_cols = ['경도', 'lon', 'longitude', 'lng', 'X', 'x']
    for file, sub_cat in file_map.items():
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            df = None
            for enc in ['utf-8-sig', 'cp949', 'utf-8', 'euc-kr']:
                try:
                    df = pd.read_csv(path, encoding=enc)
                    break
                except: continue
            if df is not None:
                if sub_cat == '소상공인' and '카테고리_소' in df.columns: df['sub_category'] = df['카테고리_소']
                else: df['sub_category'] = sub_cat
                lat_c = next((c for c in lat_cols if c in df.columns), None)
                lon_c = next((c for c in lon_cols if c in df.columns), None)
                name_c = next((c for c in ['상호명', '점포명', '이름', 'name'] if c in df.columns), None)
                if lat_c and lon_c and name_c:
                    temp_df = df[[name_c, lat_c, lon_c, 'sub_category']].copy()
                    temp_df.columns = ['name', 'lat', 'lon', 'sub_category']
                    all_dfs.append(temp_df)
    return pd.concat(all_dfs, ignore_index=True)

data = load_all_data()
# 역삼역 좌표
center_lat, center_lon = 37.5006, 127.0363
radius_m = 500

radius_km = radius_m / 1000.0
lat_margin, lon_margin = radius_km / 111.0, radius_km / 88.0
mask = (data['lat'] >= center_lat - lat_margin) & (data['lat'] <= center_lat + lat_margin) & \
       (data['lon'] >= center_lon - lon_margin) & (data['lon'] <= center_lon + lon_margin)
filtered = data[mask].copy()

counts = {}
for g_name, sub_cats in CATEGORY_GROUPS.items():
    g_data = filtered[filtered['sub_category'].apply(lambda x: any(sc in str(x) for sc in sub_cats))]
    actual_count = 0
    for _, row in g_data.iterrows():
        try:
            if geodesic((center_lat, center_lon), (row['lat'], row['lon'])).meters <= radius_m:
                actual_count += 1
        except: continue
    counts[g_name] = actual_count

weights = {"생활/편의🏪": 30, "교통🚌": 20, "의료💊": 15, "안전/치안🚨": 10, "교육/문화📚": 5, "자연/여가🌳": 15, "금융🏦": 5}
max_counts = {"생활/편의🏪": 15, "교통🚌": 10, "의료💊": 5, "안전/치안🚨": 2, "교육/문화📚": 5, "자연/여가🌳": 5, "금융🏦": 5}

scores = {}
for g_name, weight in weights.items():
    m = max_counts.get(g_name, 10)
    scores[g_name] = round((min(counts[g_name], m) / m) * weight, 2)

total_score = round(sum(scores.values()), 1)
print(f'Total data rows: {len(data)}')
unique_cats = data["sub_category"].unique()
print(f'Unique sub_categories count: {len(unique_cats)}')
print(f'Sample sub_categories: {unique_cats[:50]}')

print(f'Latitude range: {data["lat"].min()} ~ {data["lat"].max()}')
print(f'Longitude range: {data["lon"].min()} ~ {data["lon"].max()}')
print(f'Sample coordinates:\n{data[["name", "lat", "lon"]].head(10)}')
print(f'Counts: {counts}')
print(f'Scores: {scores}')
print(f'Total: {total_score}')
