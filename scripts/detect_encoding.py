
import os
import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        # 파일의 앞부분 10000바이트를 읽어서 인코딩을 감지합니다.
        rawdata = f.read(10000)
        result = chardet.detect(rawdata)
        return result['encoding']

def main():
    # 스크립트 위치(pj1/output)를 기준으로 데이터 폴더 경로 설정 (pj1/data)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, '..', 'data')
    
    # 데이터 디렉토리 내의 모든 CSV 파일을 찾습니다.
    if not os.path.exists(data_dir):
        print(f"Error: Directory not found - {data_dir}")
        return

    for filename in os.listdir(data_dir):
        if filename.lower().endswith('.csv'):
            file_path = os.path.join(data_dir, filename)
            encoding = detect_encoding(file_path)
            print(f"{filename}: {encoding}")

if __name__ == "__main__":
    main()
