import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# 웹 화면 설정
st.set_page_config(page_title="동물병원 변동 알리미", layout="wide")
st.title("전국 동물병원 개업/폐업 실시간 추적기")
st.write("공공데이터 API를 통해 전국 데이터를 즉시 분석합니다.")

# ─────────────────────────────────────────────
# 담당자별 담당 지역 정의
# ─────────────────────────────────────────────
MANAGER_REGIONS = {
    "전체": [],
    "에이벳": ["인천", "고양", "김포", "부천", "광명", "시흥", "안산", "파주", "원주", "춘천"],
    "천성":  ["충청", "대전", "세종", "충남", "충북"],
}

# 1. 설정값
URL = 'https://apis.data.go.kr/1741000/animal_hospitals/info'
KEY = '2f470b5a09e984c04d6729c7bd7f0e9451c3407c594d5767b9d7846c2cbb8faf'

# 2. 사이드바
with st.sidebar:
    st.header("🔍 조회 설정")
    base_date   = st.date_input("기준 날짜를 선택하세요", pd.to_datetime("2026-02-28"))
    target_date = pd.to_datetime(base_date)
    run_btn     = st.button("실시간 데이터 분석 시작", use_container_width=True)

    st.markdown("---")
    st.markdown("**👤 담당 필터**")
    selected_manager = st.radio(
        "담당을 선택하면 해당 지역만 표시됩니다.",
        options=list(MANAGER_REGIONS.keys()),
        index=0,
        label_visibility="collapsed",
    )
    if selected_manager != "전체":
        st.caption(f"담당 지역: {', '.join(MANAGER_REGIONS[selected_manager])}")

# 3. 고속 수집 함수
@st.cache_data(ttl=3600)
def get_all_hospital_data():
    def fetch(p):
        params = {
            'serviceKey': KEY,
            'pageNo': str(p),
            'numOfRows': '100',
            'resultType': 'json'
        }
        try:
            r = requests.get(URL, params=params, verify=False, timeout=5)
            return r.json()['response']['body']['items']['item']
        except:
            return []

    with ThreadPoolExecutor(max_workers=10) as exe:
        results = list(exe.map(fetch, range(1, 81)))
    return [item for sublist in results for item in sublist]


# ─────────────────────────────────────────────
# 담당자 지역 필터 함수
# ─────────────────────────────────────────────
def filter_by_manager(df: pd.DataFrame, manager: str) -> pd.DataFrame:
    """선택한 담당자의 담당 지역에 해당하는 행만 반환."""
    if manager == "전체":
        return df
    keywords = MANAGER_REGIONS[manager]
    mask = df['전체주소'].fillna('').apply(
        lambda addr: any(kw in addr for kw in keywords)
    )
    return df[mask]


# 4. 분석 및 출력
if run_btn:
    with st.spinner("📡 전국 데이터를 수집 중입니다..."):
        all_data = get_all_hospital_data()
        df = pd.DataFrame(all_data)

        df['LCPMT_YMD']  = pd.to_datetime(df['LCPMT_YMD'],  errors='coerce')
        df['CLSBIZ_YMD'] = pd.to_datetime(df['CLSBIZ_YMD'], errors='coerce')
        df['전체주소']    = df['ROAD_NM_ADDR'].fillna(df['LOTNO_ADDR'])
        df['시도']        = df['전체주소'].str.split().str[0].fillna('미분류')

        new_open   = df[df['LCPMT_YMD']  >= target_date].copy()
        new_closed = df[df['CLSBIZ_YMD'] >= target_date].copy()

        # 담당자 필터 적용
        open_filtered   = filter_by_manager(new_open,   selected_manager)
        closed_filtered = filter_by_manager(new_closed, selected_manager)

        # 결과 요약
        label = f"[{selected_manager}]" if selected_manager != "전체" else "[전체]"
        st.success(
            f"분석 완료! {label}  "
            f"신규 개업 **{len(open_filtered)}건**, "
            f"신규 폐업 **{len(closed_filtered)}건**"
        )

        # 담당자 필터 안내 배너
        if selected_manager != "전체":
            st.info(
                f"👤 **{selected_manager}** 담당 지역 필터 적용 중: "
                f"{', '.join(MANAGER_REGIONS[selected_manager])}"
            )

        tab1, tab2 = st.tabs(["🆕 신규 개업 상세", "❌ 신규 폐업 상세"])
        st.warning("※개원 신고만 하고 실제로는 아직 오픈 전인 경우가 있으니 반드시 사전에 네이버지도 검색 혹은 전화를 통해 확인 후 방문 부탁 드립니다.")

        with tab1:
            if not open_filtered.empty:
                regions = sorted(open_filtered['시도'].unique())
                for reg in regions:
                    reg_df = open_filtered[open_filtered['시도'] == reg]
                    with st.expander(f"📍 {reg} 개업 ({len(reg_df)}건)", expanded=True):
                        st.dataframe(
                            reg_df[['BPLC_NM', '전체주소', 'LCPMT_YMD', 'TELNO']],
                            use_container_width=True
                        )
            else:
                st.info("내역이 없습니다.")

        with tab2:
            if not closed_filtered.empty:
                regions = sorted(closed_filtered['시도'].unique())
                for reg in regions:
                    reg_df = closed_filtered[closed_filtered['시도'] == reg]
                    with st.expander(f"📍 {reg} 폐업 ({len(reg_df)}건)", expanded=True):
                        st.dataframe(
                            reg_df[['BPLC_NM', '전체주소', 'CLSBIZ_YMD']],
                            use_container_width=True
                        )
            else:
                st.info("내역이 없습니다.")
