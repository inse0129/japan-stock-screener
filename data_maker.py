import yfinance as yf
import pandas as pd
import time

print("🚀 [안전 모드] 티커 리스트 파일에서 데이터 수집 시작...")

# 1. 파일에서 티커 읽어오기
try:
    with open('tickers.txt', 'r') as f:
        TICKERS = f.read().split(',')
    print(f"✅ 총 {len(TICKERS)}개 종목 분석 예정")
except:
    print("❌ tickers.txt 파일을 찾을 수 없습니다.")
    TICKERS = ["7203.T", "6758.T"] # 비상용

results = []
for i, ticker in enumerate(TICKERS):
    ticker = ticker.strip()
    try:
        print(f"[{i+1}/{len(TICKERS)}] {ticker} 분석 중...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if len(hist) < 20: continue
        
        # 지표 연산
        last = hist.iloc[-1]
        prev = hist.iloc[-2]
        ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        vol_ratio = (last['Volume'] / prev['Volume'] * 100) if prev['Volume'] > 0 else 0
        
        # RSI 계산
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        rs = gain / loss if loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        results.append({
            "종목코드": ticker.replace(".T", ""),
            "현재가": int(last['Close']),
            "20MA": int(ma20),
            "거래량비율": int(vol_ratio),
            "RSI": round(rsi, 2)
        })
        time.sleep(0.1) # 안전을 위한 지연
    except:
        continue

# 2. 결과 저장
df = pd.DataFrame(results)
df.to_csv("japan_market_latest.csv", index=False, encoding='utf-8-sig')
print("🎉 분석 완료 및 파일 업데이트 성공!")
