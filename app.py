import streamlit as st
import pandas as pd
import yfinance as yf

# 페이지 기본 설정
st.set_page_config(page_title="일본 주식 조건검색기", page_icon="📈", layout="wide")

st.title("📈 일본 주식 실전 조건검색기")
st.markdown("나만의 정교한 매매 타점을 찾아보세요. (무료 체험판은 시총 상위 20종목만 제공됩니다.)")

# --- 탭(Tab)을 활용한 UI 분리 (무료 vs 유료) ---
tab_free, tab_pro = st.tabs(["🟢 무료 체험 (우량주 실시간 검색)", "👑 Pro 버전 (전 종목 CSV 업로드)"])

# ---------------------------------------------------------
# [Tab 1] 무료 체험 모드 (yfinance 실시간 크롤링)
# ---------------------------------------------------------
with tab_free:
    st.subheader("무료 체험: 일본 시총 상위 대표 종목 실시간 스캔")
    st.info("💡 팁: 현재 야후 파이낸스에서 실시간 데이터를 불러와 연산 중입니다. (약 5~10초 소요)")
    
    # 대표 20종목 리스트 (빠른 로딩을 위해 20개로 제한, 필요시 늘릴 수 있음)
    TOP_20_TICKERS = {
        "7203.T": "토요타 자동차", "6758.T": "소니 그룹", "8306.T": "미쓰비시 UFJ",
        "6861.T": "키엔스", "9983.T": "패스트리테일링", "7974.T": "닌텐도",
        "9984.T": "소프트뱅크", "8035.T": "도쿄 일렉트론", "4063.T": "신에츠 화학",
        "8058.T": "미쓰비시 상사", "6501.T": "히타치", "8316.T": "미쓰이스미토모",
        "8001.T": "이토추 상사", "9432.T": "NTT", "4568.T": "다이이치산쿄",
        "6902.T": "덴소", "6098.T": "리크루트", "8031.T": "미쓰이 물산",
        "7267.T": "혼다", "4519.T": "츄가이 제약"
    }

    @st.cache_data(ttl=600) # 10분간 데이터 캐싱 (속도 향상)
    def fetch_live_data():
        results = []
        progress_bar = st.progress(0, text="실시간 시장 데이터 분석 중...")
        
        for i, (ticker, name) in enumerate(TOP_20_TICKERS.items()):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="3mo")
                if len(hist) < 25: continue
                
                # 지표 연산
                close_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
                vol_today = hist['Volume'].iloc[-1]
                vol_prev = hist['Volume'].iloc[-2]
                
                # 거래량 비율 계산 (전일 대비)
                vol_ratio = (vol_today / vol_prev * 100) if vol_prev > 0 else 0
                
                # 간단한 RSI 계산 (14일)
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
                rs = gain / loss if loss > 0 else 0
                rsi = 100 - (100 / (1 + rs)) if loss > 0 else 100

                results.append({
                    "종목코드": ticker.replace(".T", ""),
                    "종목명": name,
                    "현재가": int(close_price),
                    "20MA": int(ma20),
                    "거래량비율": int(vol_ratio),
                    "RSI": round(rsi, 2)
                })
            except: pass
            progress_bar.progress((i + 1) / len(TOP_20_TICKERS), text=f"{name} 분석 완료...")
            
        progress_bar.empty()
        return pd.DataFrame(results)

    # 데이터 로드
    df_free = fetch_live_data()
    df_active = df_free # 현재 활성화된 데이터프레임
    
    st.success("✅ 실시간 데이터 로딩 완료! 좌측 사이드바에서 조건을 설정해보세요.")


# ---------------------------------------------------------
# [Tab 2] Pro 버전 (전 종목 CSV 업로드)
# ---------------------------------------------------------
with tab_pro:
    st.markdown("### 🚀 매일 4,000개 전 종목의 완벽한 매매 타점을 원하시나요?")
    st.info("Pro 플랜에 가입하시면 매일 장 마감 후 업데이트되는 **[전 종목 분석 데이터 CSV]**를 구글 드라이브로 보내드립니다.")
    
    # 결제 유도 버튼 (임시 링크)
    st.link_button("💎 Pro 플랜 구독 알아보기", "https://your-landing-page.com")
    
    st.divider()
    
    uploaded_file = st.file_uploader("구독자 전용 데이터 파일(CSV) 업로드", type=['csv'])
    
    if uploaded_file is not None:
        df_pro = pd.read_csv(uploaded_file)
        df_active = df_pro # 파일이 업로드되면 활성 데이터를 Pro 데이터로 교체
        st.success(f"✅ Pro 데이터 업로드 완료! 총 {len(df_pro)}개 종목이 준비되었습니다.")


# ---------------------------------------------------------
# 좌측 사이드바 & 검색 로직 (공통 적용)
# ---------------------------------------------------------
st.sidebar.header("🛠️ 나만의 조건식 만들기")

min_price, max_price = st.sidebar.slider("1. 주가 범위 (엔)", 100, 100000, (500, 50000), 100)
vol_ratio = st.sidebar.number_input("2. 전일 대비 거래량 비율 (최소 %)", 50, 1000, 150, 10)
rsi_max = st.sidebar.slider("3. RSI (14일) 상한선 (예: 30 이하는 과매도)", 0, 100, 100)
ma20_condition = st.sidebar.radio("4. 20일 이동평균선 위치", ("상관없음", "현재가가 20일선 위에 위치 (상승추세)", "현재가가 20일선 아래에 위치 (낙폭과대)"))

st.sidebar.markdown("---")

if st.sidebar.button("🚀 조건검색 실행", type="primary", use_container_width=True):
    
    # df_active (무료 20종목 or 유료 4000종목) 기준으로 필터링
    mask = (
        (df_active['현재가'] >= min_price) & 
        (df_active['현재가'] <= max_price) & 
        (df_active['거래량비율'] >= vol_ratio) &
        (df_active['RSI'] <= rsi_max)
    )
    
    if "위에 위치" in ma20_condition:
        mask = mask & (df_active['현재가'] > df_active['20MA'])
    elif "아래에 위치" in ma20_condition:
        mask = mask & (df_active['현재가'] < df_active['20MA'])
        
    df_filtered = df_active[mask]
    
    st.subheader(f"📊 검색 결과: {len(df_filtered)} 종목 포착")
    
    if len(df_filtered) > 0:
        df_filtered['차트링크'] = "https://finance.yahoo.co.jp/quote/" + df_filtered['종목코드'].astype(str) + ".T"
        st.dataframe(
            df_filtered, hide_index=True, use_container_width=True,
            column_config={
                "차트링크": st.column_config.LinkColumn("📈 상세 차트", display_text="야후 차트 열기 ↗")
            }
        )
    else:
        st.warning("조건에 맞는 종목이 없습니다. 좌측에서 조건을 완화해 보세요!")
