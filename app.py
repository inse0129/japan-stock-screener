import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="일본 주식 조건검색기", page_icon="📈", layout="wide")

st.title("📈 일본 주식 실전 조건검색기 (Custom Builder Ver.)")
st.markdown("매일 업데이트되는 시장 데이터(CSV)를 업로드하고, 나만의 정교한 매매 타점을 찾아보세요.")

# 1. 파일 업로드 위젯
uploaded_file = st.file_uploader("최신 일본 증시 데이터 파일(CSV)을 업로드해주세요.", type=['csv'])

if uploaded_file is not None:
    # 데이터 읽기
    df = pd.read_csv(uploaded_file)
    st.success(f"✅ 데이터 업로드 완료! 총 {len(df)}개 종목이 준비되었습니다.")
    
    # --- 좌측 사이드바: 나만의 커스텀 조건식 빌더 ---
    st.sidebar.header("🛠️ 나만의 조건식 만들기")
    
    # 주가 범위 설정 (엔)
    min_price, max_price = st.sidebar.slider(
        "1. 주가 범위 (엔)", 
        min_value=100, max_value=100000, value=(500, 50000), step=100
    )
    
    # 거래량 급증 조건
    vol_ratio = st.sidebar.number_input(
        "2. 전일 대비 거래량 비율 (최소 %)", 
        min_value=50, max_value=1000, value=200, step=10
    )
    
    # 보조지표: RSI
    rsi_max = st.sidebar.slider(
        "3. RSI (14일) 상한선 (예: 30 이하는 과매도)", 
        min_value=0, max_value=100, value=100
    )
    
    # 이평선 조건
    ma20_condition = st.sidebar.radio(
        "4. 20일 이동평균선 위치", 
        ("상관없음", "현재가가 20일선 위에 위치 (정배열/상승추세)", "현재가가 20일선 아래에 위치 (눌림목/낙폭과대)")
    )

    st.sidebar.markdown("---")

    # 검색 실행 버튼
    if st.button("🚀 내 조건식으로 검색", type="primary", use_container_width=True):
        
        # --- 유저가 설정한 값으로 데이터 필터링 ---
        # (주의: 아래 '현재가', '거래량비율', 'RSI', '20MA' 등은 향후 만들 CSV 파일의 실제 컬럼명과 일치해야 합니다)
        
        # 기본 필터 적용 (안전하게 컬럼이 존재하는지 확인하는 로직 추가 권장, MVP는 직관적으로 작성)
        mask = (
            (df['현재가'] >= min_price) & 
            (df['현재가'] <= max_price) & 
            (df['거래량비율'] >= vol_ratio) &
            (df['RSI'] <= rsi_max)
        )
        
        # 이평선 필터 적용
        if ma20_condition == "현재가가 20일선 위에 위치 (정배열/상승추세)":
            mask = mask & (df['현재가'] > df['20MA'])
        elif ma20_condition == "현재가가 20일선 아래에 위치 (눌림목/낙폭과대)":
            mask = mask & (df['현재가'] < df['20MA'])
            
        df_filtered = df[mask]
        
        st.subheader(f"📊 커스텀 검색 결과: {len(df_filtered)} 종목 포착")
        
        if len(df_filtered) > 0:
            # --- 야후 재팬 파이낸스 링크 생성 로직 ---
            # 종목코드 뒤에 '.T'를 붙여 야후 재팬 URL 완성
            df_filtered['차트링크'] = "https://finance.yahoo.co.jp/quote/" + df_filtered['종목코드'].astype(str) + ".T"
            
            # 스트림릿 표 출력 (LinkColumn 적용)
            st.dataframe(
                df_filtered,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "차트링크": st.column_config.LinkColumn(
                        "📈 상세 차트", 
                        help="야후 재팬 파이낸스로 이동합니다", 
                        display_text="차트 열기 ↗"
                    )
                }
            )
        else:
            st.warning("조건에 맞는 종목이 없습니다. 조건을 조금 완화해 보세요!")

else:
    st.info("👈 왼쪽 사이드바가 열려있다면 닫아주시고, 먼저 중앙에 데이터를 업로드해주세요.")
