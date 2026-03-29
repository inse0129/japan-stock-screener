import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="일본 주식 조건검색기 (MVP)", page_icon="📈", layout="wide")

# UI: 제목 및 설명
st.title("📈 일본 주식 실전 조건검색기 (Beta)")
st.markdown("일본 프라임 시장 주요 종목 중, 승률 높은 차트 패턴이 발생한 종목을 즉시 찾아냅니다.")

# 검색 대상 종목 (MVP 테스트용: 일본 시총 상위 대표 주식들)
# 실제 런칭 시에는 프라임 시장 전체 티커 리스트로 확장 가능
TICKERS = {
    "7203.T": "토요타 자동차",
    "6758.T": "소니 그룹",
    "8306.T": "미쓰비시 UFJ",
    "6861.T": "키엔스",
    "9983.T": "패스트리테일링",
    "7974.T": "닌텐도",
    "9984.T": "소프트뱅크 그룹",
    "8035.T": "도쿄 일렉트론",
    "4063.T": "신에츠 화학",
    "8058.T": "미쓰비시 상사"
}

# 데이터 수집 및 분석 함수 (캐싱을 통해 속도 향상)
@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def get_stock_data_and_analyze():
    results = []
    
    # 진행 상태 표시 바
    progress_text = "야후 파이낸스에서 시장 데이터를 분석 중입니다..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, (ticker, name) in enumerate(TICKERS.items()):
        try:
            # 최근 3개월 데이터 로드
            stock = yf.Ticker(ticker)
            df = stock.history(period="3mo")
            
            if df.empty or len(df) < 21:
                continue
                
            # 기술적 지표 계산
            df['20MA'] = df['Close'].rolling(window=20).mean()
            df['Vol_20MA'] = df['Volume'].rolling(window=20).mean()
            
            # 최근일 데이터
            today = df.iloc[-1]
            yesterday = df.iloc[-2]
            
            # 1. 20일선 돌파 로직 (전일 20일선 아래 -> 금일 20일선 위)
            is_20ma_breakout = (yesterday['Close'] < yesterday['20MA']) and (today['Close'] > today['20MA'])
            
            # 2. 거래량 200% 급증 로직 (오늘 거래량이 20일 평균의 2배 이상)
            is_volume_spike = today['Volume'] > (today['Vol_20MA'] * 2)
            
            results.append({
                "종목코드": ticker.replace(".T", ""),
                "종목명": name,
                "현재가(JPY)": int(today['Close']),
                "거래량": int(today['Volume']),
                "20일선 돌파": "✅ 포착" if is_20ma_breakout else "-",
                "거래량 급증": "🔥 포착" if is_volume_spike else "-"
            })
            
        except Exception as e:
            pass
            
        # 프로그레스 바 업데이트
        my_bar.progress((i + 1) / len(TICKERS), text=progress_text)
        
    my_bar.empty()
    return pd.DataFrame(results)

# 사이드바: 조건식 선택
st.sidebar.header("🎯 조건식 선택 (프리셋)")
selected_strategy = st.sidebar.radio(
    "검색할 패턴을 선택하세요:",
    ("전체 종목 보기", "🟢 20일선 상향 돌파", "🔥 거래량 200% 급증")
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** 일본 주식은 미국과 달리 정교한 조건검색 툴이 부족합니다. 본 서비스는 야후 파이낸스 데이터를 기반으로 핵심 차트 패턴을 실시간으로 추적합니다.")

# 메인 화면: 버튼 클릭 시 실행
if st.button("🚀 조건검색 실행", type="primary", use_container_width=True):
    with st.spinner('데이터를 불러오는 중입니다...'):
        df_results = get_stock_data_and_analyze()
        
        # 선택된 조건에 따라 데이터 필터링
        if selected_strategy == "🟢 20일선 상향 돌파":
            df_filtered = df_results[df_results["20일선 돌파"] == "✅ 포착"]
        elif selected_strategy == "🔥 거래량 200% 급증":
            df_filtered = df_results[df_results["거래량 급증"] == "🔥 포착"]
        else:
            df_filtered = df_results
            
        st.subheader(f"📊 검색 결과: {len(df_filtered)} 종목 포착")
        
        if len(df_filtered) > 0:
            # 인덱스를 숨기고 깔끔하게 표 출력
            st.dataframe(df_filtered, hide_index=True, use_container_width=True)
        else:
            st.warning("현재 선택하신 조건에 맞는 종목이 없습니다. 장 마감 후 다시 시도해 보세요!")
