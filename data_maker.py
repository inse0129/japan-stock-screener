import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

print("🚀 [무인 공장] 일본 상장 전 종목(4,000+) 수집 및 지표 연산 시작...")

# 1. 🇯🇵 일본 거래소(JPX)에서 최신 상장 종목 리스트 엑셀을 직접 읽어옵니다.
# 이 URL은 JPX에서 공식 제공하는 통계 게시판 링크입니다.
try:
    jpx_url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    df_jpx = pd.read_excel(jpx_url)
    
    # '코드' 컬럼에서 종목코드만 추출하여 뒤에 '.T'를 붙입니다 (예: 7203 -> 7203.T)
    # 보통 2번째 컬럼이 종목코드입니다.
    raw_tickers = df_jpx.iloc[:, 1].dropna().astype(str).tolist()
    TICKERS = [t + ".T" for t in raw_tickers if len(t) == 4] # 4자리 숫자 종목만 필터링
    
    # 종목명 매핑 정보 생성 (나중에 CSV에 이름을 넣기 위함)
    ticker_to_name = dict(zip(TICKERS, df_jpx.iloc[:, 2].tolist()))
    
    print(f"✅ 총 {len(TICKERS)}개의 상장 종목 리스트를 확보했습니다.")
except Exception as e:
    print(f"❌ 종목 리스트 수집 실패: {e}")
    # 실패 시 비상용으로 아까 그 30개라도 돌립니다.
    TICKERS = ["7203.T", "6758.T", "8306.T"] 
    ticker_to_name = {"7203.T": "토요타", "6758.T": "소니", "8306.T": "미쓰비시"}

results = []
total_count = len(TICKERS)

# RSI 계산 함수
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 2. 데이터 수집 및 연산 루프
for i, ticker in enumerate(TICKERS):
    try:
        # 100종목마다 진행 상황 알림 (4,000개라 너무 자주 찍으면 지저분합니다)
        if (i + 1) % 100 == 0 or (i + 1) == total_count:
            print(f"⏳ 진행 중... [{i+1}/{total_count}] 완료")
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty or len(hist) < 120: continue
            
        # 기술적 지표 계산
        hist['20MA'] = hist['Close'].rolling(window=20).mean()
        hist['Vol_Ratio'] = (hist['Volume'] / hist['Volume'].shift(1)) * 100
        hist['RSI'] = calc_rsi(hist['Close'], 14)
        
        today_data = hist.iloc[-1]
        
        results.append({
            "종목코드": ticker.replace(".T", ""),
            "종목명": ticker_to_name.get(ticker, "Unknown"), # 수집한 이름 넣기
            "현재가": int(today_data['Close']),
            "20MA": int(today_data['20MA']),
            "거래량비율": int(today_data['Vol_Ratio']) if not pd.isna(today_data['Vol_Ratio']) else 0,
            "RSI": round(today_data['RSI'], 2) if not pd.isna(today_data['RSI']) else 50
        })
        
        # ⚠️ 중요: 4,000개를 연속으로 요청하면 차단당할 수 있습니다. 
        # 속도를 살짝 늦춰서 안전하게 수집합니다 (약 0.05초)
        time.sleep(0.05)
        
    except: continue

# 3. 결과 저장 (항상 동일한 이름으로 덮어쓰기)
df_final = pd.DataFrame(results)
file_name = "japan_market_latest.csv"
df_final.to_csv(file_name, index=False, encoding='utf-8-sig')

print(f"\n🎉 전 종목 분석 완료! '{file_name}' 파일이 업데이트되었습니다.")
