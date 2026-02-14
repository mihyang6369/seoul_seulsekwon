
import os
import pandas as pd

def filter_park_seoul():
    # 스크립트 위치(pj1/output)를 기준으로 프로젝트 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(current_dir, '..', 'data'))
    
    input_file = os.path.join(data_dir, 'park.csv')
    output_file = os.path.join(data_dir, 'park_seoul.csv')
    
    if not os.path.exists(input_file):
        print(f"Error: Input file NOT found - {input_file}")
        return

    print(f"Reading {input_file}...")
    # 데이터 로드
    df = pd.read_csv(input_file)
    
    # '소재지도로명주소' 열에서 '서울특별시'를 포함하는 행만 필터링
    # 결측치(NaN) 처리를 위해 na=False 옵션 사용
    seoul_df = df[df['소재지도로명주소'].str.contains('서울특별시', na=False)].copy()
    
    # 결과 저장 (UTF-8 인코딩)
    seoul_df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"Filtering complete: {len(df)} -> {len(seoul_df)} rows.")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    filter_park_seoul()
