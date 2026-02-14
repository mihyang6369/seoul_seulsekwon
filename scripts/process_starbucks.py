import pandas as pd
import os

# 초보 데이터 분석가를 위한 서울 스타벅스 데이터 전처리 스크립트

def process_starbucks():
    # 1. 파일 경로 설정 (상대 경로 사용)
    # scripts 폴더 기준: ../data/raw/starbucks_seoul.csv
    raw_path = os.path.join('..', 'data', 'raw', 'starbucks_seoul.csv')
    cleaned_dir = os.path.join('..', 'data', 'cleaned')
    output_path = os.path.join(cleaned_dir, 'starbucks_seoul_cleaned.csv')

    # 출력 폴더가 없으면 생성하기
    if not os.path.exists(cleaned_dir):
        os.makedirs(cleaned_dir)
        print(f"폴더 생성됨: {cleaned_dir}")

    # 2. 데이터 불러오기
    print("데이터를 불러오는 중...")
    df = pd.read_csv(raw_path)

    # 3. 데이터 변환 작업
    # (1) 점포명 앞에 '스타벅스 ' 추가하기
    df['점포명'] = '스타벅스 ' + df['점포명'].astype(str)
    
    # (2) 카테고리 컬럼 추가 (값은 'cafe'로 통일)
    df['카테고리_대'] = 'cafe'
    df['카테고리_소'] = 'cafe'
    
    # (3) 위도/경도 컬럼명 변경 (기존 latitude, longitude 활용)
    df.rename(columns={'latitude': '위도', 'longitude': '경도'}, inplace=True)
    
    # (4) 필요한 컬럼만 필터링 및 순서 정렬
    # 요청된 순서: 카테고리_대, 카테고리_소, 점포명, 주소, 위도, 경도
    cols = ['카테고리_대', '카테고리_소', '점포명', '주소', '위도', '경도']
    df_cleaned = df[cols]

    # 4. 결과 저장 (엑셀에서도 잘 보이도록 utf-8-sig 인코딩 사용)
    df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"전처리 완료! 파일이 여기에 저장되었습니다: {output_path}")
    print(f"전체 데이터 행 수: {len(df_cleaned)}")

if __name__ == "__main__":
    # 스크립트 실행 위치를 파일이 있는 곳으로 변경 (경로 문제 방지)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    process_starbucks()
