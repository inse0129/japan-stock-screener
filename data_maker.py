import pandas as pd
import requests
from io import StringIO

print("🔍 [진단 모드] 에러의 진짜 원인을 찾기 위해 5개 종목만 테스트합니다.")

# 가장 확실한 우량주 5개로만 테스트
TICKERS = ["7203.JP", "6758.JP", "9984.JP", "8306.JP", "9983.JP"]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for ticker in TICKERS:
    print(f"\n▶️ [{ticker}] 서버에 요청 중...")
    url = f"https://stooq.com/q/d/l/?s={ticker}&i=d"
    
    try:
        req = requests.get(url, headers=headers, timeout=10)
        print(f"상태 코드 (200이면 정상): {req.status_code}")
        
        if req.status_code == 200:
            # Stooq가 보내준 데이터의 첫 150글자를 그대로 출력해 봅니다.
            print(f"응답 내용 미리보기:\n{req.text[:150]}")
            
            # CSV로 변환 시도
            df = pd.read_csv(StringIO(req.text))
            print(f"✅ 정상 변환 완료! 데이터 개수: {len(df)}개")
        else:
            print("❌ 서버가 접근을 거절했습니다.")
            
    except Exception as e:
        print(f"❌ 치명적 에러 발생: {e}")

print("\n🏁 진단 완료!")
