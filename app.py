import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from IPython.display import display, HTML

# 1. API 설정
url = 'https://apis.data.go.kr/1741000/animal_hospitals/info'
service_key = '2f470b5a09e984c04d6729c7bd7f0e9451c3407c594d5767b9d7846c2cbb8faf'

# 2. 사용자 입력
base_date_input = input("조회 기준 날짜를 입력하세요 (예: 2026-02-28): ")
target_date = pd.to_datetime(base_date_input)

# 3. 데이터 고속 수집 함수
def fetch_page(page_no):
    params = {'serviceKey': service_key, 'pageNo': str(page_no), 'numOfRows': '100', 'resultType': 'json'}
    try:
        response = requests.get(url, params=params, verify=False, timeout=10)
        return response.json()['response']['body']['items']['item']
    except:
        return []

all_items = []
print(f"\n📡 전국 데이터를 고속 수집 중입니다...")
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_page, range(1, 81)))
for items in results:
    if items: all_items.extend(items)

# 4. 데이터 정제
df = pd.DataFrame(all_items)
df['LCPMT_YMD'] = pd.to_datetime(df['LCPMT_YMD'], errors='coerce') # 개업일
df['CLSBIZ_YMD'] = pd.to_datetime(df['CLSBIZ_YMD'], errors='coerce') # 폐업일

# 통합 주소 컬럼 만들기 (도로명 우선, 없으면 지번)
df['전체주소'] = df['ROAD_NM_ADDR'].fillna(df['LOTNO_ADDR'])
# 시도 정보 추출
df['시도'] = df['전체주소'].str.split().str[0].fillna('미분류')

# 5. 개업/폐업 필터링
new_open = df[df['LCPMT_YMD'] >= target_date].copy()
new_closed = df[df['CLSBIZ_YMD'] >= target_date].copy()

# 6. 지역별 리스트 출력 함수
def display_regional_list(target_df, mode="개업"):
    if target_df.empty:
        print(f"\n검색된 {mode} 정보가 없습니다.")
        return
    
    regions = sorted(target_df['시도'].unique())
    for region in regions:
        region_df = target_df[target_df['시도'] == region].copy()
        
        # 출력용 데이터 정리
        if mode == "개업":
            display_df = region_df[['BPLC_NM', '전체주소', 'LCPMT_YMD', 'TELNO']].copy()
            display_df['LCPMT_YMD'] = display_df['LCPMT_YMD'].dt.strftime('%Y-%m-%d')
            display_df.columns = ['병원명', '상세주소', '개업일자', '전화번호']
        else:
            display_df = region_df[['BPLC_NM', '전체주소', 'CLSBIZ_YMD', 'SALS_STTS_NM']].copy()
            display_df['CLSBIZ_YMD'] = display_df['CLSBIZ_YMD'].dt.strftime('%Y-%m-%d')
            display_df.columns = ['병원명', '상세주소', '폐업일자', '현재상태']
            
        # 가독성을 위한 HTML 출력
        title_color = "#1a73e8" if mode == "개업" else "#d93025"
        display(HTML(f"<div style='background-color:{title_color}; color:white; padding:5px 15px; border-radius:5px; margin-top:20px;'><b>📍 {region} - {mode} 리스트 ({len(display_df)}건)</b></div>"))
        display(display_df.reset_index(drop=True))

# 7. 실행 및 결과 표시
print("\n" + "★"*40)
print(f"   {base_date_input} 이후 전국 동물병원 변동 리포트")
print("★"*40)

print(f"\n[1. 신규 개업 상세 명단]")
display_regional_list(new_open, "개업")

print(f"\n\n[2. 신규 폐업 상세 명단]")
display_regional_list(new_closed, "폐업")

# 8. 엑셀 저장 (모든 정보 포함)
file_name = f"병원변동_지역별상세_{base_date_input}.xlsx"
with pd.ExcelWriter(file_name) as writer:
    if not new_open.empty: new_open.to_excel(writer, sheet_name='신규개업', index=False)
    if not new_closed.empty: new_closed.to_excel(writer, sheet_name='신규폐업', index=False)
print(f"\n💾 상세 주소가 포함된 '{file_name}' 파일이 저장되었습니다. 왼쪽 폴더에서 확인하세요.")