import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# 웹 화면 설정
st.set_page_config(page_title="동물병원 변동 알리미", layout="wide")

st.title("🐾 전국 동물병원 개업/폐업 실시간 추적기 "(경보제약 동물사업부)"")
st.write("공공데이터 API를 통해 전국 데이터를 즉시 분석합니다.")

# 1. 설정값
URL = 'https://apis.data.go.kr/1741000/animal_hospitals/info'
KEY = '2f470b5a09e984c04d6729c7bd7f0e9451c3407c594d5767b9d7846c2cbb8faf'

# 2. 사용자 입력 (날짜 선택)
with st.sidebar:
    st.header("🔍 조회 설정")
    base_date = st.date_input("기준 날짜를 선택하세요", pd.to_datetime("2026-02-28"))
    target_date = pd.to_datetime(base_date)
    run_btn = st.button("실시간 데이터 분석 시작")

# 3. 고속 수집 함수
@st.cache_data(ttl=3600)
def get_all_hospital_data():
    def fetch(p):
        params = {'serviceKey': KEY, 'pageNo': str(p), 'numOfRows': '100', 'resultType': 'json'}
        try:
            r = requests.get(URL, params=params, verify=False, timeout=5)
            return r.json()['response']['body']['items']['item']
        except: return []

    with ThreadPoolExecutor(max_workers=10) as exe:
        results = list(exe.map(fetch, range(1, 81)))
    return [item for sublist in results for item in sublist]

# 4. 분석 및 출력
if run_btn:
    with st.spinner("📡 전국 데이터를 수집 중입니다..."):
        all_data = get_all_hospital_data()
        df = pd.DataFrame(all_data)
        
        df['LCPMT_YMD'] = pd.to_datetime(df['LCPMT_YMD'], errors='coerce')
        df['CLSBIZ_YMD'] = pd.to_datetime(df['CLSBIZ_YMD'], errors='coerce')
        df['전체주소'] = df['ROAD_NM_ADDR'].fillna(df['LOTNO_ADDR'])
        df['시도'] = df['전체주소'].str.split().str[0].fillna('미분류')

        new_open = df[df['LCPMT_YMD'] >= target_date].copy()
        new_closed = df[df['CLSBIZ_YMD'] >= target_date].copy()

        st.success(f"분석 완료! 신규 개업 {len(new_open)}건, 신규 폐업 {len(new_closed)}건")

        tab1, tab2 = st.tabs(["🆕 신규 개업 상세", "❌ 신규 폐업 상세"])
        
        with tab1:
            if not new_open.empty:
                regions = sorted(new_open['시도'].unique())
                for reg in regions:
                    with st.expander(f"📍 {reg} 개업 ({len(new_open[new_open['시도']==reg])}건)"):
                        st.dataframe(new_open[new_open['시도']==reg][['BPLC_NM', '전체주소', 'LCPMT_YMD', 'TELNO']], use_container_width=True)
            else: st.info("내역이 없습니다.")

        with tab2:
            if not new_closed.empty:
                regions = sorted(new_closed['시도'].unique())
                for reg in regions:
                    with st.expander(f"📍 {reg} 폐업 ({len(new_closed[new_closed['시도']==reg])}건)"):
                        st.dataframe(new_closed[new_closed['시도']==reg][['BPLC_NM', '전체주소', 'CLSBIZ_YMD']], use_container_width=True)
            else: st.info("내역이 없습니다.")

