# Bull-Bear 에이전트 백테스팅

Bull-Bear 에이전트의 stance 및 confidence 출력이 실제 주가 방향과 얼마나 일치하는지 과거 데이터로 검증한다.

## 폴더 구조

```
bull-bear/backtest/
├── README.md                    # (이 파일) 실험 결과 요약
├── exp_backtest_plan.md         # 상세 실험 계획서
├── backtest_runner.py           # 메인 실행 스크립트 (예정)
├── backtest_analysis.py         # 결과 분석·통계 스크립트 (예정)
├── masking.py                   # 마스킹 함수 모듈 (예정)
├── data/                        # OHLCV 캐시·GT 라벨 (gitignore)
└── result/                      # 실험 결과 JSON (커밋)
    ├── phase1_technical_only/
    ├── phase2_4tickers_rounds/
    └── phase3_full_data/
```

## 실험 설계 요약

자세한 내용은 [`exp_backtest_plan.md`](./exp_backtest_plan.md) 참조.

### 핵심 질문

| # | 질문 | 검증 단계 |
|---|------|-----------|
| Q1 | Bull > Bear 판정 시 실제로 주가가 올랐는가? | Phase 1, 2 |
| Q2 | Confidence 값이 높을수록 적중률이 높은가? | Phase 4 |
| Q3 | 2라운드 토론이 1라운드보다 정확한가? | Phase 2 |
| Q4 | Macro/Sector 데이터 추가 시 정확도가 오르는가? | Phase 3 (트랙 A vs C) |

### 두 트랙 병행

| 트랙 | 데이터 | 마스킹 | 결과 신뢰도 |
|------|--------|--------|-------------|
| **A — Clean** | Technical만 | ON | 절대 적중률 신뢰 가능 |
| **C — Full** | Technical+Macro+Sector | OFF | 트랙 A 대비 상대 차이만 신뢰 |

## 실행 (예정)

```bash
# 트랙 A (Technical only, 마스킹 ON)
python bull-bear/backtest/backtest_runner.py --track=A

# 트랙 C (Full data, 마스킹 OFF)
python bull-bear/backtest/backtest_runner.py --track=C

# 결과 분석
python bull-bear/backtest/backtest_analysis.py
```

## 진행 현황

- [x] 실험 계획서 작성 (2026-05-05)
- [ ] Phase 0: 사전 검증
- [ ] Phase 1: Technical 파이프라인 (1종목)
- [ ] Phase 2: 4종목 확장 + ROUNDS 비교
- [ ] Phase 3: Macro + Sector 추가 (트랙 C)
- [ ] Phase 4: 분석 및 시각화

## 결과 (실험 후 작성)

> 실험이 완료되면 이 섹션을 채운다.

### Phase 1 결과
_미실행_

### Phase 2 결과
_미실행_

### Phase 3 결과 (트랙 A vs C)
_미실행_
