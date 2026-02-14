
import pandas as pd
import os

base_path = 'c:/Users/Administrator/Desktop/fcicb6/pj/seoul_seulsekwon/data/cleaned'
file_map = {
    'starbucks_seoul_cleaned.csv': '스타벅스', 'bus_station_seoul_cleaned.csv': '버스정류장',
    'metro_station_seoul_cleaned.csv': '지하철역', 'hospital_seoul_cleaned.csv': '병원',
    'police_seoul_cleaned_ver2.csv': '경찰서', 'library_seoul_cleaned.csv': '도서관',
    'bookstore_seoul_cleaned.csv': '서점', 'school_seoul_cleaned.csv': '학교',
    'park_raw_cleaned_revised.csv': '공원', 'finance_seoul_cleaned.csv': '은행',
    'large_scale_shop_seoul_cleaned.csv': '대형마트', 'sosang_seoul_cleaned.csv': '소상공인'
}

lat_cols = ['위도', 'lat', 'latitude', 'Y', 'y']
lon_cols = ['경도', 'lon', 'longitude', 'lng', 'X', 'x']

results = []
for file, sub_cat in file_map.items():
    path = os.path.join(base_path, file)
    if not os.path.exists(path):
        results.append(f'{file}: NOT FOUND')
        continue
    
    df = None
    applied_enc = None
    for enc in ['utf-8-sig', 'cp949', 'utf-8', 'euc-kr']:
        try:
            df = pd.read_csv(path, encoding=enc)
            applied_enc = enc
            break
        except: continue
    
    if df is None:
        results.append(f'{file}: FAILED TO READ (ENCODING)')
        continue
        
    lat_c = next((c for c in lat_cols if c in df.columns), None)
    lon_c = next((c for c in lon_cols if c in df.columns), None)
    name_c = next((c for c in ['상호명', '점포명', '이름', 'name'] if c in df.columns), None)
    
    if not lat_c or not lon_c or not name_c:
        reason = []
        if not lat_c: reason.append('lat')
        if not lon_c: reason.append('lon')
        if not name_c: reason.append('name')
        results.append(f'{file}: MISSING COLUMNS ({", ".join(reason)}) - Columns: {list(df.columns[:5])}')
    else:
        results.append(f'{file}: LOADED - {len(df)} rows ({applied_enc})')

for r in results:
    print(r)
