"""
시장 심리(Sentiment) 에이전트

MarketSentimentCollector를 호출해 VKOSPI·외국인수급·코스피 모멘텀 기반
시장 심리 지표를 수집·반환합니다.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # market/

from market_collectors.sentiment_collector import MarketSentimentCollector


def run_sentiment_agent(as_of: str | None = None) -> dict:
    """
    Sentiment 에이전트 실행

    Args:
        as_of: 기준일 YYYYMMDD. None이면 오늘 기준(실전용).

    Returns:
        dict: MarketSentimentCollector.analyze_sentiment() 반환값
              오류 시 {"errors": [str]}
    """
    try:
        collector = MarketSentimentCollector()
        payload = collector.analyze_sentiment(as_of=as_of)
        return payload
    except Exception as e:
        return {"errors": [str(e)]}
