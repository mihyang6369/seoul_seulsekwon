import pandas as pd
import os

# 데이터 파일 경로 설정
data_path = r'C:\Users\Administrator\Desktop\fcicb6\pj\pj1\data\child.csv'
output_path = r'C:\Users\Administrator\Desktop\fcicb6\pj\pj1\data\child_filtered.csv'

def filter_data():
    """
    child.csv 파일에서 '운영현황' 열의 값이 '정상'인 데이터만 추출하여 저장합니다.
    """
    try:
        # 1. CSV 파일 불러오기
        # 한글 깨짐 방지를 위해 utf-8-sig 인코딩을 주로 사용합니다.
        print(f"데이터를 불러오는 중: {data_path}")
        df = pd.read_csv(data_path, encoding='utf-8-sig')
        
        # 불러온 데이터의 처음 5행을 확인합니다.
        print("원본 데이터 요약:")
        print(df.head())
        print(f"원본 데이터 행 개수: {len(df)}")

        # 2. '운영현황' 열이 '정상'인 행만 필터링
        # df['운영현황'] == '정상' 조건이 참(True)인 행만 남깁니다.
        filtered_df = df[df['운영현황'] == '정상'].copy()
        
        # 3. 필터링 결과 확인
        print("\n필터링 후 데이터 요약:")
        print(filtered_df.head())
        print(f"필터링 후 데이터 행 개수: {len(filtered_df)}")
        
        # 4. 결과 저장
        # 엑셀과 일반 에디터 모두에서 한글이 잘 보이도록 utf-8-sig(BOM 포함) 인코딩으로 저장합니다.
        filtered_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n필터링된 데이터가 저장되었습니다: {output_path}")
        
        # 요구사항에 따라 원본 파일을 덮어쓰려면 아래 주석을 해제하세요.
        # os.replace(output_path, data_path)
        # print("원본 파일이 업데이트되었습니다.")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    filter_data()
