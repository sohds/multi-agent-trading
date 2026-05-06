# Phase 3b Macro + Sector 백테스트 결과 보고서

**날짜**: 2026-05-06  
**비교 기준**: Phase 3a Macro vs Phase 3b Macro + Sector  
**모델**: gpt-5.4-mini  
**케이스**: 96개, ROUNDS=1  
**Phase 3b 결과 파일**: `result/phase3b-patched_macro_sector/run_20260506_153226.json`

---

## 1. TL;DR

초기 Phase 3b 실행에서는 sector collector 오류가 발생했지만, 원인은 `sector/patch_pykrx.py` 미실행이었다. 패치 적용 후 재실행한 결과 runner error, macro error, sector error 모두 0건으로 정상 완료됐다.

다만 성능은 Phase 3a 대비 하락했다.

| N | Phase 3a Macro | Phase 3b Macro + Sector | 변화 |
|---|----------------|--------------------------|------|
| 5 | **54.5%** | 42.9% | -11.6%p |
| 10 | **56.7%** | 40.7% | -16.0%p |
| 20 | **48.4%** | 42.3% | -6.1%p |

결론: **P2는 기술적으로 정상 완료됐지만, 현재 sector 추가는 성능 개선으로 이어지지 않았다.** P3 진행 전에는 sector 신호가 Bull/Bear 판단에 어떤 방식으로 반영되는지 프롬프트/입력 패키지 레벨에서 재검토하는 것이 필요하다.

---

## 2. 실행 전제

Sector collector를 정상 동작시키려면 현재 Python 환경에 pykrx 로그인 패치를 먼저 적용해야 한다.

```bash
python sector/patch_pykrx.py
python bull-bear/backtest/backtest_runner.py --phase=3b-patched --track=A --macro=on --sector=on
```

검증 결과:

| 항목 | 결과 |
|------|------|
| `.env` 로드 | 정상 |
| `KRX_ID` / `KRX_PW` | 로드됨 |
| pykrx 로그인 패치 | 적용 성공 |
| sector 단위 collector | 수급/밸류에이션/상대강도 정상 payload 반환 |
| full backtest | 96건 완료 |

---

## 3. 실행 결과

| N | 유효 케이스 | 적중률 | Bull 정확 | Bear 정확 | Balanced |
|---|-------------|--------|-----------|-----------|----------|
| 5 | 49 | 42.9% | 50.0% | 33.3% | 41.7% |
| 10 | 54 | 40.7% | 43.8% | 36.4% | 40.1% |
| 20 | 52 | 42.3% | 51.8% | 32.0% | 41.9% |

에러:

| 항목 | 건수 |
|------|------|
| Runner error | 0 |
| Macro error | 0 |
| Sector error | 0 |

---

## 4. 예측 분포

| 예측 | Phase 3b |
|------|----------|
| bullish | 34 |
| neutral | 36 |
| bearish | 26 |

Phase 3a 대비 neutral 비중이 늘고 bearish 비중이 줄었다. N=10 기준으로는 이 변화가 성능 개선으로 이어지지 않았다.

---

## 5. 해석

이번 결과는 sector collector가 실패해서 생긴 문제가 아니다. 패치 적용 후에는 sector payload가 정상적으로 들어갔고, backtest 결과 JSON 기준 `sector_error`는 0건이다.

그럼에도 적중률이 하락했으므로 다음 중 하나일 가능성이 높다.

1. sector 신호 자체가 현재 평가 구간에서 추가 설명력을 주지 못함
2. sector payload는 들어가지만 Bull/Bear 프롬프트가 이를 일관되게 활용하지 못함
3. macro 신호와 sector 신호가 충돌할 때 판단 우선순위가 불안정함

---

## 6. 결론

P2는 완료 처리한다. 다만 P3로 바로 확장하기보다는, 다음 실행 전에 sector payload가 최종 Bull/Bear 입력에서 어떻게 요약되는지 확인하는 것이 낫다.

권장 다음 액션:

1. Phase 3a vs Phase 3b의 동일 케이스 몇 개를 골라 Bull/Bear 입력 패키지와 최종 rationale 비교
2. sector signal을 더 명시적으로 쓰도록 프롬프트 조정 여부 검토
3. 이후 P3 또는 sector prompt ablation 진행 결정
