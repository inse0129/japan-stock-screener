import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="일본 주식 조건검색기", page_icon="📈", layout="wide")

st.title("📈 일본 주식 실전 조건검색기")
st.markdown("매일 오후 4시, 일본 증시 전 종목 분석 데이터가 자동으로 업데이트됩니다.")

# --- 1. 데이터 자동 로드 로직 (최상단) ---
RAW_URL = "https://raw.githubusercontent.com/inse0129/japan-stock-screener/main/japan_market_latest.csv"

@st.cache_data(ttl=3600) # 1시간 동안은 다시 안 읽어오고 기억함 (속도 향상)
def load_data():
    try:
        data = pd.read_csv(RAW_URL)
        return data
    except:
        return None

df_active = load_data()

# --- 2. 메인 화면 구성 ---
tab_free, tab_pro = st.tabs(["🟢 실시간 조건검색", "👑 서비스 안내"])

with tab_free:
    if df_active is not None:
        st.success(f"✅ 오늘자 최신 데이터({len(df_active)} 종목) 로드 완료!")
    else:
        st.error("⚠️ 데이터를 불러올 수 없습니다. 잠시 후 새로고침 해주세요.")

with tab_pro:
    st.markdown("### 🚀 왜 Pro 버전을 사용해야 할까요?")
    st.write("1. 4,000개 전 종목 독점 데이터 제공")
    st.write("2. 대표님의 '비기'가 담긴 특수 조건식 활용 가능")
    st.link_button("💎 구독 플랜 확인하기", "https://your-landing-page.com")

# --- 3. 사이드바 조건 설정 (공통) ---
st.sidebar.header("🛠️ 나만의 조건식 만들기")
min_price, max_price = st.sidebar.slider("1. 주가 범위 (엔)", 100, 100000, (500, 50000), 100)
vol_ratio = st.sidebar.number_input("2. 전일 대비 거래량 비율 (최소 %)", 50, 1000, 150, 10)
rsi_max = st.sidebar.slider("3. RSI 상한선", 0, 100, 100)
ma20_condition = st.sidebar.radio("4. 20일선 위치", ("상관없음", "20일선 위 (상승)", "20일선 아래 (눌림)"))

# --- 4. 검색 실행 ---
if st.sidebar.button("🚀 조건검색 실행", type="primary", use_container_width=True):
    if df_active is not None:
        # 필터링 로직
        mask = (
            (df_active['현재가'] >= min_price) & 
            (df_active['현재가'] <= max_price) & 
            (df_active['거래량비율'] >= vol_ratio) &
            (df_active['RSI'] <= rsi_max)
        )
        
        if "위" in ma20_condition:
            mask = mask & (df_active['현재가'] > df_active['20MA'])
        elif "아래" in ma20_condition:
            mask = mask & (df_active['현재가'] < df_active['20MA'])
            
        df_filtered = df_active[mask]
        
        st.subheader(f"📊 검색 결과: {len(df_filtered)} 종목 포착")
        
        if len(df_filtered) > 0:
            df_filtered['차트링크'] = "https://finance.yahoo.co.jp/quote/" + df_filtered['종목코드'].astype(str) + ".T"
            st.dataframe(
                df_filtered, hide_index=True, use_container_width=True,
                column_config={
                    "차트링크": st.column_config.LinkColumn("📈 차트", display_text="열기 ↗")
                }
            )
        else:
            st.warning("조건에 맞는 종목이 없습니다.")
    else:
        st.error("데이터가 없습니다.")
