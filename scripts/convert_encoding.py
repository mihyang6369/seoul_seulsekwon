
import os
import pandas as pd

def convert_to_utf8(data_dir):
    # 대상 파일 확장자
    extensions = ('.csv', '.CSV')
    
    # 데이터 디렉토리 내의 파일들을 순회합니다.
    if not os.path.exists(data_dir):
        print(f"Error: Directory not found - {data_dir}")
        return

    for filename in os.listdir(data_dir):
        if filename.endswith(extensions):
            file_path = os.path.join(data_dir, filename)
            
            # shcool.csv 관련 예외 처리는 그대로 유지하거나 필요 시 수정 가능
            # 여기서는 전반적인 변환 로직에 상대 경로를 적용하는 데 집중합니다.
            if filename == 'shcool.csv':
                # 이전 작업에서 이미 수동으로 수정한 경우를 고려하여 메시지만 출력
                print(f"Checking {filename}...")
                
            print(f"Processing {filename}...")
            
            try:
                # 대용량 파일(sosang_shop_seoul.csv)인 경우 청크 단위로 처리합니다.
                if filename == 'sosang_shop_seoul.csv':
                    chunksize = 10 ** 5 # 10만 행씩 처리
                    temp_output = file_path + '.tmp'
                    
                    first_chunk = True
                    # 원본이 이미 UTF-8일 수도 있으므로 인코딩 감지 후 처리하는 것이 좋으나
                    # 여기서는 기존 계획에 따라 CP949 -> UTF-8 변환을 기본으로 하되 오류 시 건너뜁니다.
                    try:
                        for chunk in pd.read_csv(file_path, encoding='cp949', chunksize=chunksize):
                            chunk.to_csv(temp_output, index=False, encoding='utf-8', mode='w' if first_chunk else 'a', header=first_chunk)
                            first_chunk = False
                        os.remove(file_path)
                        os.rename(temp_output, file_path)
                    except UnicodeDecodeError:
                        print(f"Skip {filename}: Already UTF-8 or unknown encoding")
                    
                else:
                    # 일반 파일은 인코딩 확인 후 필요 시 변환
                    try:
                        df = pd.read_csv(file_path, encoding='cp949')
                        df.to_csv(file_path, index=False, encoding='utf-8')
                        print(f"Successfully converted {filename} to UTF-8")
                    except UnicodeDecodeError:
                        print(f"Skip {filename}: Already UTF-8 or unknown encoding")
                
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

if __name__ == "__main__":
    # 스크립트 위치(pj1/output)를 기준으로 데이터 폴더 경로 설정 (pj1/data)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.normpath(os.path.join(current_dir, '..', 'data'))
    convert_to_utf8(data_path)
