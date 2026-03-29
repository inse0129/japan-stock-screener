import pandas as pd
import time
import requests
from io import StringIO

print("🚀 [최종 결전] Stooq 무인 수집 엔진 가동 (목표: 전 종목 싹쓸이)")

# 1. 티커 리스트 불러오기 및 Stooq용으로 변환 (.T -> .JP)
try:
    with open('tickers.txt', 'r') as f:
        raw_tickers = [t.strip() for t in f.read().split(',') if t.strip()]
        # 야후용 티커(7203.T)를 Stooq용 티커(7203.JP)로 로봇이 알아서 변환합니다.
        TICKERS = [t.replace('.T', '.JP') if '.T' in t else t + '.JP' if t.isdigit() else t for t in raw_tickers]
except:
    TICKERS = ["7203.JP", "6758.JP", "9984.JP"] # 비상용

results = []
success_count = 0

# 깃허브 로봇인 척하지 않고 일반 브라우저인 척 위장 신분증 제시
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 2. 고속 직진 수집 시작
for i, ticker in enumerate(TICKERS):
    try:
        url = f"https://stooq.com/q/d/l/?s={ticker}&i=d"
        
        # 직접 requests로 받아서 pandas로 읽기 (안정성 200% 강화)
        req = requests.get(url, headers=headers, timeout=10)
        
        # Stooq에 데이터가 없거나 에러가 나면 조용히 패스
        if req.status_code != 200: continue
        
        df = pd.read_csv(StringIO(req.text))
        if len(df) < 20 or 'Close' not in df.columns: continue
        
        # --- [데이터 메이커 자체 연산 (대표님의 주방)] ---
        close_ser = df['Close']
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        ma20 = close_ser.rolling(window=20).mean().iloc[-1]
        vol_ratio = (last['Volume'] / prev['Volume'] * 100) if prev['Volume'] > 0 else 0
        
        # RSI 직접 계산
        delta = close_ser.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean().iloc[-1]
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean().iloc[-1]
        rs = gain / loss if loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        results.append({
            "종목코드": ticker.replace(".JP", ""), # 나중에 스트림릿에서 야후 차트 연결을 위해 숫자만 남김
            "현재가": int(last['Close']),
            "20MA": int(ma20),
            "거래량비율": int(vol_ratio),
            "RSI": round(rsi, 2)
        })
        
        success_count += 1
        
        # 100개 단위로 진행 상황 보고 (로그창 더러워짐 방지)
        if success_count % 100 == 0:
            print(f"🔥 {success_count}개 돌파! (현재 진행률: {round((i+1)/len(TICKERS)*100, 1)}%)")
            
        # Stooq는 야후처럼 빡빡하지 않습니다. 0.2초면 충분합니다.
        time.sleep(0.2) 
        
    except Exception as e:
        continue

# 3. 최종 정답지 생성
if results:
    pd.DataFrame(results).to_csv("japan_market_latest.csv", index=False, encoding='utf-8-sig')
    print(f"\n🎉 끝장 성공! 총 {len(results)}개 종목의 무사 통과를 확인했습니다.")
else:
    print("\n❌ 데이터가 없습니다. 무언가 단단히 꼬였습니다.")
