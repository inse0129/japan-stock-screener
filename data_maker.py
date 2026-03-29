import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

print("🚀 일본 주식 전 종목 데이터 수집 및 지표 연산 봇 가동 시작...\n")

# 1. 수집 대상 티커 리스트 (테스트용으로 프라임 시장 대표 30종목 세팅)
# 💡 실제 런칭 시에는 엑셀 파일에서 4000개 티커를 불러오도록 수정하면 됩니다.
TICKERS = [
    "7203.T", "6758.T", "8306.T", "6861.T", "9983.T", "7974.T", "9984.T", "8035.T", 
    "4063.T", "8058.T", "6501.T", "8316.T", "8001.T", "9432.T", "4568.T", "6902.T", 
    "6098.T", "8031.T", "7267.T", "4519.T", "6981.T", "8766.T", "8053.T", "7741.T", 
    "6594.T", "3382.T", "4502.T", "8411.T", "9022.T", "4901.T"
]

results = []
total_count = len(TICKERS)

# 2. RSI 계산 함수
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 3. 데이터 수집 및 연산 메인 루프
for i, ticker in enumerate(TICKERS):
    try:
        # 진행률 표시
        print(f"[{i+1}/{total_count}] {ticker} 데이터 수집 및 분석 중...")
        
        stock = yf.Ticker(ticker)
        # 120일선 및 52주 최고/최저가를 구하기 위해 1년치 데이터 호출
        hist = stock.history(period="1y")
        
        # 데이터가 부족한 상장 폐지/신규 상장 종목 건너뛰기
        if hist.empty or len(hist) < 120:
            continue
            
        # --- 📈 기술적 지표 (Indicators) 계산 ---
        # 1. 가격 및 이동평균선
        hist['5MA'] = hist['Close'].rolling(window=5).mean()
        hist['20MA'] = hist['Close'].rolling(window=20).mean()
        hist['60MA'] = hist['Close'].rolling(window=60).mean()
        hist['120MA'] = hist['Close'].rolling(window=120).mean()
        
        # 2. 거래량 비율 (전일 대비)
        hist['Vol_Ratio'] = (hist['Volume'] / hist['Volume'].shift(1)) * 100
        
        # 3. RSI (14일)
        hist['RSI'] = calc_rsi(hist['Close'], 14)
        
        # 4. MACD (12, 26, 9)
        exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
        exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
        hist['MACD'] = exp1 - exp2
        hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
        
        # 5. 볼린저 밴드 (20일 기준)
        hist['BB_Mid'] = hist['20MA']
        hist['BB_Std'] = hist['Close'].rolling(window=20).std()
        hist['BB_Upper'] = hist['BB_Mid'] + (hist['BB_Std'] * 2)
        hist['BB_Lower'] = hist['BB_Mid'] - (hist['BB_Std'] * 2)
        
        # 6. 52주 최고/최저가
        hist['52W_High'] = hist['Close'].rolling(window=250, min_periods=1).max()
        hist['52W_Low'] = hist['Close'].rolling(window=250, min_periods=1).min()
        
        # --- 💾 가장 최근(오늘) 데이터만 추출하여 저장 ---
        today_data = hist.iloc[-1]
        
        results.append({
            "종목코드": ticker.replace(".T", ""),
            "현재가": round(today_data['Close'], 2),
            "거래량": int(today_data['Volume']),
            "거래량비율": round(today_data['Vol_Ratio'], 2) if not pd.isna(today_data['Vol_Ratio']) else 0,
            "5MA": round(today_data['5MA'], 2),
            "20MA": round(today_data['20MA'], 2),
            "60MA": round(today_data['60MA'], 2),
            "120MA": round(today_data['120MA'], 2),
            "RSI": round(today_data['RSI'], 2) if not pd.isna(today_data['RSI']) else 50,
            "MACD": round(today_data['MACD'], 2),
            "MACD_Signal": round(today_data['MACD_Signal'], 2),
            "BB_Upper": round(today_data['BB_Upper'], 2),
            "BB_Lower": round(today_data['BB_Lower'], 2),
            "52주최고가": round(today_data['52W_High'], 2),
            "52주최저가": round(today_data['52W_Low'], 2)
        })
        
        # 야후 파이낸스 서버 차단(IP Block) 방지를 위한 0.1초 휴식 (필수)
        time.sleep(0.1)
        
    except Exception as e:
        print(f"⚠️ {ticker} 처리 중 에러 발생: {e}")
        continue

# 4. 수집된 데이터를 DataFrame으로 변환 및 CSV 저장
df_final = pd.DataFrame(results)

# 항상 동일한 이름으로 덮어쓰기
file_name = "japan_market_latest.csv"

df_final.to_csv(file_name, index=False, encoding='utf-8-sig')

print("\n🎉 모든 데이터 수집 및 연산이 완료되었습니다!")
print(f"📁 저장된 파일명: {file_name}")
print(f"📊 총 수집 종목 수: {len(df_final)}개")
