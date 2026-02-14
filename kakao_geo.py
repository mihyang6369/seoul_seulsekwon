import requests
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

def get_coordinates(query, api_key):
    """
    대략적인 주소나 키워드를 입력받아 위도(lat), 경도(lng)를 반환합니다.
    """
    # 1. 키워드 검색 API 사용 (대략적인 주소나 장소명에 유리)
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        result = response.json()
        if result['documents']:
            # 가장 연관도 높은 첫 번째 결과의 좌표 추출
            address_info = result['documents'][0]
            return {
                "address_name": address_info['address_name'],
                "lat": address_info['y'],  # 위도
                "lng": address_info['x']   # 경도
            }
        else:
            return "검색 결과가 없습니다."
    else:
        return f"Error: {response.status_code}"

# app.py와의 호환성을 위한 래퍼 함수
def get_coords_from_address(address: str):
    """
    주소 검색 API를 호출하여 (위도, 경도) 튜플을 반환합니다.
    """
    api_key = os.getenv("KAKAO_REST_API_KEY")
    if not api_key:
        return None
    result = get_coordinates(address, api_key)
    if isinstance(result, dict):
        return float(result['lat']), float(result['lng'])
    return None

# --- 사용 예시 ---
if __name__ == "__main__":
    # .env 파일의 키를 우선 사용하고, 없을 경우 안내 메시지 출력
    REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "여기에_복사한_REST_API_키를_입력하세요")
    search_query = "삼성동"

    location_data = get_coordinates(search_query, REST_API_KEY)

    if isinstance(location_data, dict):
        print(f"입력한 주소: {search_query}")
        print(f"검색된 전체 주소: {location_data['address_name']}")
        print(f"위도(Latitude): {location_data['lat']}")
        print(f"경도(Longitude): {location_data['lng']}")
    else:
        print(location_data)