#!/usr/bin/env python3
"""
Phase 0: 기존 코드 테스트 스크립트

테스트 항목:
1. pykrx 급등/급락/거래량 조회
2. 네이버 리포트 크롤러
3. Perplexity API 검색
4. OpenAI Chat/Vision API
5. PostgreSQL/Redis 연결
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "ai-module"))

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestResults:
    """테스트 결과 수집기"""
    
    def __init__(self):
        self.results = {}
    
    def add(self, name: str, success: bool, message: str = ""):
        self.results[name] = {"success": success, "message": message}
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {name} - {message}")
    
    def summary(self):
        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)
        print("\n" + "=" * 60)
        print(f"📊 테스트 결과 요약: {passed}/{total} 통과")
        print("=" * 60)
        for name, result in self.results.items():
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {name}: {result['message']}")
        print("=" * 60)
        return passed == total


results = TestResults()


# ============================================
# 1. pykrx 테스트
# ============================================
def test_pykrx():
    """pykrx 급등/급락/거래량 조회 테스트"""
    print("\n" + "-" * 40)
    print("🧪 Test 1: pykrx 주식 데이터 수집")
    print("-" * 40)
    
    try:
        from collectors.stock_collector import (
            get_top_movers,
            get_high_volume_stocks,
            get_market_summary
        )
        
        # 최근 영업일 찾기 (주말 제외)
        today = datetime.now()
        test_date = today
        
        # 주말이면 금요일로 설정
        if test_date.weekday() == 5:  # 토요일
            test_date = test_date - timedelta(days=1)
        elif test_date.weekday() == 6:  # 일요일
            test_date = test_date - timedelta(days=2)
        
        # 오늘 데이터가 없을 수 있으니 전날도 시도
        for days_back in range(5):
            test_date_str = (test_date - timedelta(days=days_back)).strftime("%Y%m%d")
            
            try:
                # 급등/급락 테스트
                movers = get_top_movers(test_date_str, top_n=5)
                
                if movers["gainers"] or movers["losers"]:
                    print(f"  📅 테스트 날짜: {test_date_str}")
                    print(f"  📈 급등 종목 수: {len(movers['gainers'])}")
                    print(f"  📉 급락 종목 수: {len(movers['losers'])}")
                    
                    if movers["gainers"]:
                        top_gainer = movers["gainers"][0]
                        print(f"     Top Gainer: {top_gainer.get('name', 'N/A')} ({top_gainer.get('등락률', 0):.2f}%)")
                    
                    # 거래량 테스트
                    volume = get_high_volume_stocks(test_date_str, top_n=5)
                    print(f"  📊 고거래량 종목 수: {len(volume['high_volume'])}")
                    
                    # 시장 요약 테스트
                    summary = get_market_summary(test_date_str)
                    if summary["kospi"]:
                        print(f"  🏢 KOSPI 종가: {summary['kospi']['close']:,.0f}")
                    if summary["kosdaq"]:
                        print(f"  🏭 KOSDAQ 종가: {summary['kosdaq']['close']:,.0f}")
                    
                    results.add("pykrx", True, f"데이터 조회 성공 ({test_date_str})")
                    return
                    
            except Exception as e:
                continue
        
        results.add("pykrx", False, "최근 5일간 데이터 없음")
        
    except Exception as e:
        results.add("pykrx", False, str(e))


# ============================================
# 2. 네이버 크롤러 테스트
# ============================================
async def test_naver_crawler():
    """네이버 리포트 크롤러 테스트"""
    print("\n" + "-" * 40)
    print("🧪 Test 2: 네이버 금융 리서치 크롤러")
    print("-" * 40)
    
    try:
        from collectors.naver_report_crawler import fetch_report_list
        
        reports = await fetch_report_list(page=1)
        
        if reports:
            print(f"  📄 조회된 리포트 수: {len(reports)}")
            
            # 첫 번째 리포트 정보 출력
            first_report = reports[0]
            print(f"  📝 첫 번째 리포트:")
            print(f"     종목: {first_report.stock_name}")
            print(f"     제목: {first_report.title[:30]}...")
            print(f"     증권사: {first_report.broker}")
            print(f"     날짜: {first_report.date}")
            print(f"     PDF URL: {'있음' if first_report.pdf_url else '없음'}")
            
            results.add("naver_crawler", True, f"{len(reports)}개 리포트 조회 성공")
        else:
            results.add("naver_crawler", False, "리포트 목록이 비어있음")
            
    except Exception as e:
        results.add("naver_crawler", False, str(e))


# ============================================
# 3. Perplexity API 테스트
# ============================================
def test_perplexity():
    """Perplexity API 검색 테스트"""
    print("\n" + "-" * 40)
    print("🧪 Test 3: Perplexity API 검색")
    print("-" * 40)
    
    try:
        from openai import OpenAI
        
        # API 키 확인
        api_key = os.getenv("PERPLEXITY_API_KEY", "")
        if not api_key or api_key.startswith("pplx-xxx"):
            results.add("perplexity", False, "API 키가 설정되지 않음")
            return
        
        print(f"  🔑 API Key: {api_key[:10]}...")
        
        # Perplexity 클라이언트 (OpenAI 호환)
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        
        # 간단한 검색 테스트
        query = "삼성전자 2024년 실적"
        print(f"  🔍 검색 쿼리: {query}")
        
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful search assistant. Answer in Korean."
                },
                {"role": "user", "content": query}
            ],
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        if content:
            print(f"  ✅ 응답 길이: {len(content)} 글자")
            print(f"  📖 응답 미리보기: {content[:100]}...")
            results.add("perplexity", True, f"검색 성공 ({len(content)} 글자)")
        else:
            results.add("perplexity", False, "응답 없음")
            
    except Exception as e:
        results.add("perplexity", False, str(e))


# ============================================
# 4. OpenAI API 테스트
# ============================================
def test_openai():
    """OpenAI Chat API 테스트"""
    print("\n" + "-" * 40)
    print("🧪 Test 4: OpenAI Chat API")
    print("-" * 40)
    
    try:
        from openai import OpenAI
        
        # API 키 확인
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or "REPLACE" in api_key:
            results.add("openai_chat", False, "API 키가 설정되지 않음")
            return
        
        print(f"  🔑 API Key: {api_key[:15]}...")
        
        # OpenAI 클라이언트
        client = OpenAI(api_key=api_key)
        
        # 간단한 채팅 테스트
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "주식 투자에서 PER이란 무엇인가요? 한 문장으로 답해주세요."}
        ]
        
        print(f"  💬 질문: 주식 투자에서 PER이란 무엇인가요?")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200
        )
        
        content = response.choices[0].message.content
        
        if content:
            print(f"  ✅ 응답: {content[:100]}...")
            results.add("openai_chat", True, f"Chat API 성공 ({len(content)} 글자)")
        else:
            results.add("openai_chat", False, "응답 없음")
            
    except Exception as e:
        results.add("openai_chat", False, str(e))


# ============================================
# 5. PostgreSQL 연결 테스트
# ============================================
async def test_postgresql():
    """PostgreSQL 연결 테스트"""
    print("\n" + "-" * 40)
    print("🧪 Test 5: PostgreSQL 연결")
    print("-" * 40)
    
    try:
        import asyncpg
        
        database_url = os.getenv("DATABASE_URL", "")
        
        if not database_url:
            results.add("postgresql", False, "DATABASE_URL이 설정되지 않음")
            return
        
        # asyncpg URL 형식으로 변환
        conn_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        print(f"  🔗 연결 시도: {conn_url.split('@')[1] if '@' in conn_url else 'localhost'}")
        
        conn = await asyncpg.connect(conn_url)
        
        # 간단한 쿼리 테스트
        result = await conn.fetchval("SELECT 1")
        
        if result == 1:
            # 데이터베이스 버전 확인
            version = await conn.fetchval("SELECT version()")
            print(f"  ✅ 연결 성공")
            print(f"  📋 PostgreSQL 버전: {version.split(',')[0]}")
            results.add("postgresql", True, "연결 성공")
        else:
            results.add("postgresql", False, "쿼리 결과 오류")
        
        await conn.close()
        
    except Exception as e:
        results.add("postgresql", False, str(e))


# ============================================
# 6. Redis 연결 테스트
# ============================================
async def test_redis():
    """Redis 연결 테스트"""
    print("\n" + "-" * 40)
    print("🧪 Test 6: Redis 연결")
    print("-" * 40)
    
    try:
        import redis.asyncio as redis
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        print(f"  🔗 연결 시도: {redis_url.split('@')[-1] if '@' in redis_url else redis_url.split('//')[1]}")
        
        client = redis.from_url(redis_url)
        
        # PING 테스트
        pong = await client.ping()
        
        if pong:
            # 테스트 키 설정/조회
            await client.set("narrative_investment_test", "ok", ex=10)
            value = await client.get("narrative_investment_test")
            
            if value == b"ok":
                # Redis 정보 확인
                info = await client.info()
                print(f"  ✅ 연결 성공")
                print(f"  📋 Redis 버전: {info.get('redis_version', 'unknown')}")
                print(f"  📊 사용 메모리: {info.get('used_memory_human', 'unknown')}")
                results.add("redis", True, "연결 성공")
            else:
                results.add("redis", False, "SET/GET 테스트 실패")
        else:
            results.add("redis", False, "PING 응답 없음")
        
        await client.close()
        
    except Exception as e:
        results.add("redis", False, str(e))


# ============================================
# 메인 실행
# ============================================
async def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("🚀 Phase 0: 기존 코드 테스트 시작")
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. pykrx 테스트
    test_pykrx()
    
    # 2. 네이버 크롤러 테스트
    await test_naver_crawler()
    
    # 3. Perplexity API 테스트
    test_perplexity()
    
    # 4. OpenAI API 테스트
    test_openai()
    
    # 5. PostgreSQL 연결 테스트
    await test_postgresql()
    
    # 6. Redis 연결 테스트
    await test_redis()
    
    # 결과 요약
    all_passed = results.summary()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
