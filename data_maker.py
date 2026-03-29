import yfinance as yf
import pandas as pd
import numpy as np
import time

print("🚀 [전 종목 모드] 일본 시장 4,000개 종목 풀스캔 시작...")

# 1. 일본 주식 티커 생성기 (대부분의 일본 주식은 1000~9999 사이의 4자리 숫자입니다)
# 💡 모든 숫자를 다 훑는 것은 비효율적이므로, 실제 상장된 범위 위주로 스캔하거나 
# 💡 미리 준비된 리스트가 있다면 여기서 읽어옵니다.
def get_all_japanese_tickers():
    # 실제 운영 시에는 제가 별도로 드리는 4,000개 리스트를 tickers.txt에 넣고 읽는 게 가장 빠릅니다.
    # 여기서는 안전하게 기존에 검증된 50개 + 주요 섹터 범위를 예시로 구성합니다.
    base_tickers = ["7203.T", "6758.T", "8306.T", "9983.T", "9984.T"] # ... (생략)
    
    try:
        with open('tickers.txt', 'r') as f:
            full_list = [t.strip() for t in f.read().split(',') if t.strip()]
            return full_list
    except:
        return base_tickers

TICKERS = get_all_japanese_tickers()
print(f"📊 분석 대상: 총 {len(TICKERS)}개 종목")

results = []

# 2. 고속 분석 루프
for i, ticker in enumerate(TICKERS):
    try:
        # 100개 단위로 생존 신고
        if (i + 1) % 100 == 0:
            print(f"⏳ 현재 {i+1}번째 종목 분석 중... ({round((i+1)/len(TICKERS)*100, 1)}%)")
        
        stock = yf.Ticker(ticker)
        # 4,000개를 할 때는 period를 3mo나 6mo로 줄이면 훨씬 빨라집니다.
        hist = stock.history(period="6mo") 
        
        if len(hist) < 20: continue
        
        # 데이터 추출 및 계산
        last_close = hist['Close'].iloc[-1]
        vol_today = hist['Volume'].iloc[-1]
        vol_prev = hist['Volume'].iloc[-2]
        ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        
        # 거래량 비율
        vol_ratio = (vol_today / vol_prev * 100) if vol_prev > 0 else 0
        
        # RSI (빠른 연산 버전)
        delta = hist['Close'].diff()
        up = delta.clip(lower=0).rolling(window=14).mean().iloc[-1]
        down = -delta.clip(upper=0).rolling(window=14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (up / down))) if down > 0 else 100

        results.append({
            "종목코드": ticker.replace(".T", ""),
            "현재가": int(last_close),
            "20MA": int(ma20),
            "거래량비율": int(vol_ratio),
            "RSI": round(rsi, 2)
        })
        
        # ⚠️ 과부하 방지를 위한 미세 지연 (0.01초)
        # 4,000개일 때는 이 수치가 전체 시간에 큰 영향을 줍니다.
        time.sleep(0.01)
        
    except:
        continue

# 3. 최종 저장
df_final = pd.DataFrame(results)
df_final.to_csv("japan_market_latest.csv", index=False, encoding='utf-8-sig')

print(f"\n✅ 분석 완료! 총 {len(df_final)}개 종목의 데이터가 업데이트되었습니다.")
