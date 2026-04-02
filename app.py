"""
매물대 패턴 탐지기 (PoC)
-----------------------
① CSV(OHLCV) 업로드
② 매물대 구간 직접 레이블링
③ 특징 추출 → 전체 차트에서 유사 구간 자동 탐지
④ Plotly 캔들스틱 + 매물대 오버레이 시각화
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="매물대 탐지기",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 매물대 패턴 탐지기")
st.caption("OHLCV CSV를 업로드하고 매물대 구간을 직접 표시하면, 유사한 구간을 자동으로 찾아드립니다.")

# ─────────────────────────────────────────────────────────────────────────────
# 세션 상태 초기화 (레이블 목록 유지)
# ─────────────────────────────────────────────────────────────────────────────
if "labels" not in st.session_state:
    st.session_state.labels = []  # [{"price_lo", "price_hi", "date_start", "date_end", "name"}, ...]

if "df" not in st.session_state:
    st.session_state.df = None


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: CSV 파싱
# ─────────────────────────────────────────────────────────────────────────────
def parse_csv(uploaded_file) -> pd.DataFrame | None:
    """
    CSV를 파싱해서 표준 컬럼(date, open, high, low, close, volume)으로 반환.
    컬럼명은 대소문자 무관하게 처리.
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"CSV 읽기 오류: {e}")
        return None

    # 컬럼명 소문자 정규화
    df.columns = [c.strip().lower() for c in df.columns]

    # 날짜 컬럼 탐지 (date, datetime, 일자, 날짜 등)
    date_candidates = [c for c in df.columns if any(k in c for k in ["date", "time", "일자", "날짜"])]
    if not date_candidates:
        st.error("날짜 컬럼을 찾을 수 없습니다. 컬럼명에 'date' 또는 'time'이 포함되어야 합니다.")
        return None

    df = df.rename(columns={date_candidates[0]: "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # OHLCV 컬럼 필수 확인
    required = ["open", "high", "low", "close", "volume"]
    # 일본어/한국어 컬럼명 매핑 시도
    col_map = {
        "시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume",
        "始値": "open", "高値": "high", "安値": "low", "終値": "close", "出来高": "volume",
    }
    df = df.rename(columns=col_map)

    missing = [r for r in required if r not in df.columns]
    if missing:
        st.error(f"필수 컬럼 없음: {missing}. CSV에 open/high/low/close/volume 컬럼이 필요합니다.")
        return None

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)
    return df[["date", "open", "high", "low", "close", "volume"]]


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: 구간 특징 추출
# ─────────────────────────────────────────────────────────────────────────────
def extract_features(df: pd.DataFrame, price_lo: float, price_hi: float,
                      date_start, date_end) -> dict | None:
    """
    지정 매물대 구간의 특징값 추출:
    - vol_ratio       : 구간 평균 거래량 / 전체 평균 거래량
    - touch_count     : 가격이 구간 안으로 진입한 봉 수
    - price_range_pct : 구간 가격폭 (%)
    - vol_density     : 거래량 집중도 (구간 내 거래량 표준편차 / 평균) — 낮을수록 고른 집중
    - bounce_count    : 구간 경계에서 반등한 횟수
    """
    # 날짜 필터
    mask_date = (df["date"] >= pd.Timestamp(date_start)) & (df["date"] <= pd.Timestamp(date_end))
    seg = df[mask_date & (df["low"] <= price_hi) & (df["high"] >= price_lo)]

    if len(seg) < 2:
        return None

    global_avg_vol = df["volume"].mean()
    seg_avg_vol    = seg["volume"].mean()

    # 전체 데이터에서 해당 가격대를 터치한 봉 수 (날짜 제한 없음)
    touch_all = df[(df["low"] <= price_hi) & (df["high"] >= price_lo)]
    touch_count = len(touch_all)

    # 가격 범위 %
    mid_price      = (price_lo + price_hi) / 2
    price_range_pct = (price_hi - price_lo) / mid_price * 100

    # 거래량 집중도 (CV: 변동계수, 낮을수록 고른 집중)
    vol_std  = seg["volume"].std()
    vol_cv   = vol_std / seg_avg_vol if seg_avg_vol > 0 else 999

    # 경계 반등: 저가가 price_lo 근처(-2%)에서 상승 마감한 봉
    tol = (price_hi - price_lo) * 0.15
    bounce = df[
        (df["low"] >= price_lo - tol) & (df["low"] <= price_lo + tol) &
        (df["close"] > df["open"])
    ]
    bounce_count = len(bounce)

    return {
        "vol_ratio"       : seg_avg_vol / global_avg_vol if global_avg_vol > 0 else 1.0,
        "touch_count"     : touch_count,
        "price_range_pct" : price_range_pct,
        "vol_density_cv"  : vol_cv,
        "bounce_count"    : bounce_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: 전체 차트에서 유사 구간 자동 탐지
# ─────────────────────────────────────────────────────────────────────────────
def detect_similar_zones(df: pd.DataFrame, ref_features: dict,
                          n_rows: int = 50, sensitivity: float = 0.6) -> list[dict]:
    """
    레이블된 구간들의 평균 특징을 기준으로, 전체 차트를 슬라이딩 윈도우로 탐색.
    유사도가 sensitivity 이상인 구간을 반환.
    """
    if not ref_features:
        return []

    # 레이블 구간들의 평균 기준값
    avg_vol_ratio    = np.mean([f["vol_ratio"]       for f in ref_features])
    avg_touch        = np.mean([f["touch_count"]     for f in ref_features])
    avg_price_range  = np.mean([f["price_range_pct"] for f in ref_features])
    avg_vol_cv       = np.mean([f["vol_density_cv"]  for f in ref_features])
    avg_bounce       = np.mean([f["bounce_count"]    for f in ref_features])

    global_avg_vol = df["volume"].mean()
    detected_zones = []

    # 가격 구간 분할 (전체 고/저를 n_rows 등분)
    price_min = df["low"].min()
    price_max = df["high"].max()
    step      = (price_max - price_min) / n_rows

    # 탐색: 각 가격 구간에 대해 전체 기간 평가
    checked_bands = set()
    for i in range(n_rows):
        p_lo = price_min + step * i
        p_hi = p_lo + step

        band_key = round(p_lo, 2)
        if band_key in checked_bands:
            continue
        checked_bands.add(band_key)

        touch_df = df[(df["low"] <= p_hi) & (df["high"] >= p_lo)]
        if len(touch_df) < 3:
            continue

        seg_vol    = touch_df["volume"].mean()
        vol_ratio  = seg_vol / global_avg_vol if global_avg_vol > 0 else 1.0
        touch_cnt  = len(touch_df)
        pr_pct     = (p_hi - p_lo) / ((p_lo + p_hi) / 2) * 100
        vol_cv     = touch_df["volume"].std() / seg_vol if seg_vol > 0 else 999

        tol = step * 0.15
        bounce_cnt = len(df[
            (df["low"] >= p_lo - tol) & (df["low"] <= p_lo + tol) &
            (df["close"] > df["open"])
        ])

        # 유사도 점수 계산 (각 특징이 기준에 얼마나 가까운지)
        scores = []

        # 거래량 비율: 기준의 70% 이상이면 점수
        scores.append(min(vol_ratio / avg_vol_ratio, 1.0) if avg_vol_ratio > 0 else 0)

        # 터치 횟수: 기준의 50% 이상
        scores.append(min(touch_cnt / max(avg_touch, 1), 1.0))

        # 거래량 집중도: CV가 낮을수록 좋음 (기준보다 낮으면 만점)
        cv_score = 1.0 - min(vol_cv / max(avg_vol_cv, 0.01), 1.0) if avg_vol_cv > 0 else 0
        scores.append(max(cv_score, 0))

        # 반등 횟수
        scores.append(min(bounce_cnt / max(avg_bounce, 1), 1.0))

        similarity = np.mean(scores)

        if similarity >= sensitivity:
            # 이미 레이블된 구간과 겹치면 스킵
            is_labeled = any(
                lbl["price_lo"] <= p_hi and lbl["price_hi"] >= p_lo
                for lbl in st.session_state.labels
            )
            if not is_labeled:
                date_start_det = touch_df["date"].min()
                date_end_det   = touch_df["date"].max()
                detected_zones.append({
                    "price_lo"   : p_lo,
                    "price_hi"   : p_hi,
                    "date_start" : date_start_det,
                    "date_end"   : date_end_det,
                    "similarity" : round(similarity * 100, 1),
                    "touch_count": touch_cnt,
                    "vol_ratio"  : round(vol_ratio, 2),
                })

    # 유사도 내림차순 정렬, 상위만 반환
    detected_zones.sort(key=lambda x: -x["similarity"])

    # 인접 구간 병합 (가격이 step*1.5 이내면 합침)
    merged = []
    for z in detected_zones:
        if merged and abs(z["price_lo"] - merged[-1]["price_hi"]) < step * 1.5:
            merged[-1]["price_hi"]   = max(merged[-1]["price_hi"], z["price_hi"])
            merged[-1]["similarity"] = max(merged[-1]["similarity"], z["similarity"])
        else:
            merged.append(z)

    return merged[:20]  # 상위 20개만


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: Plotly 캔들스틱 차트 생성
# ─────────────────────────────────────────────────────────────────────────────
def build_chart(df: pd.DataFrame, labels: list, detected: list) -> go.Figure:
    """캔들스틱 + 거래량 + 매물대 오버레이 차트 생성"""

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=("가격 (캔들스틱)", "거래량"),
    )

    # ── 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"], high=df["high"],
            low=df["low"],   close=df["close"],
            name="가격",
            increasing_line_color="#ef5350",  # 상승: 빨강 (한국식)
            decreasing_line_color="#26a69a",  # 하락: 파랑/초록
        ),
        row=1, col=1,
    )

    # ── 거래량 막대
    colors_vol = ["#ef5350" if c >= o else "#26a69a"
                  for c, o in zip(df["close"], df["open"])]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["volume"], name="거래량",
               marker_color=colors_vol, opacity=0.7),
        row=2, col=1,
    )

    # ── 레이블된 매물대 (빨간 박스)
    for lbl in labels:
        fig.add_vrect(
            x0=str(lbl["date_start"]), x1=str(lbl["date_end"]),
            y0=0, y1=1, yref="paper",
            fillcolor="rgba(255, 80, 80, 0.0)",
            line_width=0,
            row=1, col=1,
        )
        fig.add_shape(
            type="rect",
            x0=lbl["date_start"], x1=lbl["date_end"],
            y0=lbl["price_lo"],   y1=lbl["price_hi"],
            line=dict(color="rgba(255,50,50,0.9)", width=2),
            fillcolor="rgba(255,50,50,0.15)",
            row=1, col=1,
        )
        # 레이블 텍스트
        mid_date = lbl["date_start"] + (lbl["date_end"] - lbl["date_start"]) / 2
        fig.add_annotation(
            x=mid_date,
            y=lbl["price_hi"],
            text=f"🏷️ {lbl.get('name','매물대')}",
            showarrow=False,
            font=dict(color="red", size=11),
            yanchor="bottom",
            row=1, col=1,
        )

    # ── 탐지된 유사 구간 (파란 박스)
    for i, z in enumerate(detected):
        fig.add_shape(
            type="rect",
            x0=z["date_start"], x1=z["date_end"],
            y0=z["price_lo"],   y1=z["price_hi"],
            line=dict(color="rgba(30,144,255,0.8)", width=1.5, dash="dot"),
            fillcolor="rgba(30,144,255,0.10)",
            row=1, col=1,
        )
        mid_date = z["date_start"] + (z["date_end"] - z["date_start"]) / 2
        fig.add_annotation(
            x=mid_date,
            y=z["price_lo"],
            text=f"🔵 {z['similarity']}%",
            showarrow=False,
            font=dict(color="#1e90ff", size=10),
            yanchor="top",
            row=1, col=1,
        )

    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9"),
    )
    fig.update_xaxes(gridcolor="#21262d", zeroline=False)
    fig.update_yaxes(gridcolor="#21262d", zeroline=False)

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 샘플 CSV 생성 (테스트용)
# ─────────────────────────────────────────────────────────────────────────────
def generate_sample_csv() -> str:
    """테스트용 가상 OHLCV 데이터 생성"""
    np.random.seed(42)
    dates  = pd.date_range("2023-01-01", periods=250, freq="B")
    closes = [1000.0]
    for _ in range(249):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.015)))

    rows = []
    for i, (d, c) in enumerate(zip(dates, closes)):
        o = c * (1 + np.random.normal(0, 0.005))
        h = max(o, c) * (1 + abs(np.random.normal(0, 0.007)))
        l = min(o, c) * (1 - abs(np.random.normal(0, 0.007)))
        # 특정 구간(50~80봉)에 거래량 집중시켜 매물대 패턴 생성
        base_vol = 1_000_000
        if 50 <= i <= 80 or 150 <= i <= 170:
            base_vol *= np.random.uniform(2.5, 4.0)
        v = int(base_vol * np.random.uniform(0.7, 1.3))
        rows.append({"date": d.strftime("%Y-%m-%d"),
                     "open": round(o, 1), "high": round(h, 1),
                     "low": round(l, 1), "close": round(c, 1), "volume": v})

    return pd.DataFrame(rows).to_csv(index=False)


# ─────────────────────────────────────────────────────────────────────────────
# 사이드바: CSV 업로드 & 샘플 다운로드
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("① 데이터 로드")

    sample_csv = generate_sample_csv()
    st.download_button(
        "📥 샘플 CSV 다운로드",
        data=sample_csv,
        file_name="sample_ohlcv.csv",
        mime="text/csv",
        help="형식 확인용 샘플 데이터 (250일, 가상 종목)"
    )

    uploaded = st.file_uploader(
        "CSV 파일 업로드",
        type=["csv"],
        help="컬럼: date, open, high, low, close, volume"
    )

    if uploaded:
        df = parse_csv(uploaded)
        if df is not None:
            st.session_state.df = df
            st.success(f"✅ {len(df)}행 로드 완료")
            st.caption(f"기간: {df['date'].min().date()} ~ {df['date'].max().date()}")

    # ── 레이블링 UI
    st.divider()
    st.header("② 매물대 구간 입력")

    if st.session_state.df is not None:
        df = st.session_state.df

        with st.form("label_form", clear_on_submit=True):
            label_name = st.text_input("구간 이름 (선택)", placeholder="예: 1차 매물대")

            col1, col2 = st.columns(2)
            with col1:
                price_lo = st.number_input(
                    "시작 가격",
                    min_value=float(df["low"].min()),
                    max_value=float(df["high"].max()),
                    value=float(df["close"].quantile(0.3)),
                    step=float((df["high"].max() - df["low"].min()) / 200),
                    format="%.1f",
                )
            with col2:
                price_hi = st.number_input(
                    "끝 가격",
                    min_value=float(df["low"].min()),
                    max_value=float(df["high"].max()),
                    value=float(df["close"].quantile(0.4)),
                    step=float((df["high"].max() - df["low"].min()) / 200),
                    format="%.1f",
                )

            col3, col4 = st.columns(2)
            with col3:
                date_start = st.date_input(
                    "시작일",
                    value=df["date"].min().date(),
                    min_value=df["date"].min().date(),
                    max_value=df["date"].max().date(),
                )
            with col4:
                date_end = st.date_input(
                    "종료일",
                    value=(df["date"].min() + timedelta(days=30)).date(),
                    min_value=df["date"].min().date(),
                    max_value=df["date"].max().date(),
                )

            submitted = st.form_submit_button("➕ 매물대 추가", use_container_width=True)
            if submitted:
                if price_lo >= price_hi:
                    st.error("시작 가격이 끝 가격보다 낮아야 합니다.")
                elif date_start >= date_end:
                    st.error("시작일이 종료일보다 앞이어야 합니다.")
                else:
                    st.session_state.labels.append({
                        "name"       : label_name or f"매물대 {len(st.session_state.labels)+1}",
                        "price_lo"   : price_lo,
                        "price_hi"   : price_hi,
                        "date_start" : pd.Timestamp(date_start),
                        "date_end"   : pd.Timestamp(date_end),
                    })
                    st.success("추가됨!")

        # 레이블 목록 표시 & 삭제
        if st.session_state.labels:
            st.caption(f"등록된 구간: {len(st.session_state.labels)}개")
            for i, lbl in enumerate(st.session_state.labels):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"**{lbl['name']}**  \n"
                                f"`{lbl['price_lo']:.1f} ~ {lbl['price_hi']:.1f}`  \n"
                                f"{lbl['date_start'].date()} ~ {lbl['date_end'].date()}")
                with col_b:
                    if st.button("🗑", key=f"del_{i}"):
                        st.session_state.labels.pop(i)
                        st.rerun()
    else:
        st.info("먼저 CSV를 업로드하세요.")

    # ── 탐지 설정
    st.divider()
    st.header("③ 탐지 설정")
    sensitivity = st.slider(
        "민감도",
        min_value=0.3, max_value=0.9, value=0.55, step=0.05,
        help="낮을수록 더 많은 구간 탐지, 높을수록 정밀"
    )
    n_rows = st.slider(
        "가격 분할 수",
        min_value=20, max_value=100, value=50, step=10,
        help="차트 가격 범위를 몇 개 구간으로 나눌지"
    )

    run_btn = st.button(
        "🔍 유사 매물대 탐지 실행",
        use_container_width=True,
        disabled=(st.session_state.df is None or len(st.session_state.labels) == 0),
        type="primary",
    )

# ─────────────────────────────────────────────────────────────────────────────
# 메인 영역: 차트 & 결과
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.df is None:
    st.info("👈 왼쪽 사이드바에서 CSV를 업로드하면 차트가 표시됩니다.")
    with st.expander("CSV 형식 안내"):
        st.markdown("""
        | date | open | high | low | close | volume |
        |------|------|------|-----|-------|--------|
        | 2023-01-01 | 1000 | 1050 | 980 | 1030 | 1500000 |
        | 2023-01-02 | 1030 | 1080 | 1020 | 1060 | 2100000 |
        
        - **date**: YYYY-MM-DD 형식 권장
        - **volume**: 정수 또는 소수
        - 한국어/일본어 컬럼명(시가/고가/低値 등)도 자동 인식
        """)
    st.stop()

df = st.session_state.df

# 탐지 실행
detected_zones = []
if run_btn:
    if len(st.session_state.labels) == 0:
        st.warning("매물대 구간을 먼저 하나 이상 입력하세요.")
    else:
        with st.spinner("유사 구간 탐지 중..."):
            # 각 레이블 구간의 특징 추출
            ref_features = []
            for lbl in st.session_state.labels:
                feat = extract_features(
                    df, lbl["price_lo"], lbl["price_hi"],
                    lbl["date_start"], lbl["date_end"]
                )
                if feat:
                    ref_features.append(feat)

            if not ref_features:
                st.error("레이블 구간에서 충분한 데이터를 찾지 못했습니다. 구간을 다시 확인하세요.")
            else:
                detected_zones = detect_similar_zones(df, ref_features, n_rows, sensitivity)
                st.session_state["detected"] = detected_zones

                # 특징 요약 표시
                with st.expander("📐 레이블 구간 특징 요약"):
                    feat_df = pd.DataFrame(ref_features)
                    feat_df.index = [lbl["name"] for lbl in st.session_state.labels[:len(ref_features)]]
                    feat_df.columns = ["거래량배율", "터치횟수", "가격폭%", "거래량CV", "반등횟수"]
                    st.dataframe(feat_df.round(2))

# 세션에 탐지 결과 유지
if "detected" in st.session_state and not run_btn:
    detected_zones = st.session_state["detected"]

# ── 차트 출력
fig = build_chart(df, st.session_state.labels, detected_zones)
st.plotly_chart(fig, use_container_width=True)

# ── 탐지 결과 테이블
if detected_zones:
    st.subheader(f"🔵 탐지된 유사 매물대 구간 ({len(detected_zones)}개)")
    result_df = pd.DataFrame([{
        "가격 하단": f"{z['price_lo']:.1f}",
        "가격 상단": f"{z['price_hi']:.1f}",
        "시작일"   : z["date_start"].strftime("%Y-%m-%d"),
        "종료일"   : z["date_end"].strftime("%Y-%m-%d"),
        "유사도"   : f"{z['similarity']}%",
        "터치 횟수": z["touch_count"],
        "거래량 배율": f"{z['vol_ratio']}x",
    } for z in detected_zones])
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    # CSV 다운로드
    st.download_button(
        "📥 탐지 결과 CSV 다운로드",
        data=result_df.to_csv(index=False),
        file_name="detected_maemuldae.csv",
        mime="text/csv",
    )
elif run_btn:
    st.info("탐지된 유사 구간이 없습니다. 민감도를 낮추거나 레이블 구간을 추가해 보세요.")

# ── 하단 안내
st.divider()
st.caption("""
**사용 순서**: ① CSV 업로드 → ② 사이드바에서 매물대 구간 1~3개 입력 → ③ 탐지 실행  
**탐지 원리**: 레이블 구간의 거래량 밀도·터치 횟수·반등 패턴을 기준으로 전체 차트에서 유사 구간 자동 식별  
**민감도 조절**: 결과가 너무 많으면 높이고, 너무 적으면 낮추세요.
""")
