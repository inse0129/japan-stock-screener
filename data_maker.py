import yfinance as yf
import pandas as pd
import numpy as np
import time

print("🚀 [벌크 시스템] 1,500개 종목 고속 병렬 수집 및 지표 연산 가동...")

# 1. 티커 읽기 및 청크(Chunk) 나누기
try:
    with open('tickers.txt', 'r') as f:
        all_tickers = [t.strip() for t in f.read().split(',') if t.strip()]
except:
    all_tickers = ["7203.T", "6758.T"]

# 한 번에 50개씩 묶어서 요청 (서버 부하 최소화)
chunk_size = 50
chunks = [all_tickers[i:i + chunk_size] for i in range(0, len(all_tickers), chunk_size)]

final_results = []

# 2. 벌크 다운로드 및 로컬 연산
for i, chunk in enumerate(chunks):
    try:
        print(f"📦 [{i+1}/{len(chunks)}] {len(chunk)}개 종목 덩어리 수집 중...")
        
        # 💡 핵심: 여러 종목을 한 번에 다운로드 (문 두드리는 횟수 1/50로 감소)
        data = yf.download(chunk, period="2mo", group_by='ticker', threads=True, progress=False)
        
        for ticker in chunk:
            try:
                # 해당 종목의 데이터만 추출
                df = data[ticker].dropna()
                if len(df) < 20: continue
                
                # --- [데이터 메이커 자체 로직] ---
                close = df['Close']
                last_price = close.iloc[-1]
                
                # 20일 이동평균선
                ma20 = close.rolling(window=20).mean().iloc[-1]
                
                # 거래량 비율
                vol_today = df['Volume'].iloc[-1]
                vol_prev = df['Volume'].iloc[-2]
                vol_ratio = (vol_today / vol_prev * 100) if vol_prev > 0 else 0
                
                # RSI 직접 계산 (자체 로직)
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(window=14).mean().iloc[-1]
                loss = -delta.where(delta < 0, 0).rolling(window=14).mean().iloc[-1]
                rs = gain / loss if loss > 0 else 0
                rsi = 100 - (100 / (1 + rs))

                final_results.append({
                    "종목코드": ticker.replace(".T", ""),
                    "현재가": int(last_price),
                    "20MA": int(ma20),
                    "거래량비율": int(vol_ratio),
                    "RSI": round(rsi, 2)
                })
            except:
                continue
                
        # 덩어리 수집 사이사이에 짧은 휴식 (차단 방지)
        time.sleep(2)
        
    except Exception as e:
        print(f"⚠️ 덩어리 {i+1} 처리 중 오류 발생: {e}")
        continue

# 3. 최종 저장
if final_results:
    df_final = pd.DataFrame(final_results)
    df_final.to_csv("japan_market_latest.csv", index=False, encoding='utf-8-sig')
    print(f"\n✨ 완료! 총 {len(df_final)}개 종목 분석 정답지 생성 성공.")
else:
    print("❌ 수집된 데이터가 없습니다.")
