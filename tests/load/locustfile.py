"""40인 동시 접속 부하 테스트.

사용법:
  locust -f tests/load/locustfile.py --headless -u 40 -r 5 --run-time 2m --host http://localhost:80
"""

import random
from locust import HttpUser, task, between


class AdelieUser(HttpUser):
    """아델리에 투자 사용자 시뮬레이션."""

    wait_time = between(1, 5)

    # 자주 조회하는 종목 코드
    STOCK_CODES = ["005930", "000660", "035420", "051910", "006400",
                   "005380", "035720", "068270", "028260", "105560"]

    @task(5)
    def view_home(self):
        """메인 페이지 조회."""
        self.client.get("/", name="[FE] Home")

    @task(3)
    def get_briefing(self):
        """최신 브리핑 조회."""
        self.client.get("/api/v1/briefings/latest", name="[API] Briefing")

    @task(3)
    def get_stock_price(self):
        """종목 시세 조회."""
        code = random.choice(self.STOCK_CODES)
        self.client.get(f"/api/v1/portfolio/stock/price/{code}", name="[API] Stock Price")

    @task(2)
    def search_stock(self):
        """종목 검색."""
        queries = ["삼성", "SK", "네이버", "카카오", "현대"]
        self.client.get(f"/api/v1/trading/search?q={random.choice(queries)}", name="[API] Search")

    @task(2)
    def get_ranking(self):
        """종목 랭킹."""
        types = ["volume", "gainers", "losers"]
        self.client.get(f"/api/v1/trading/ranking?type={random.choice(types)}", name="[API] Ranking")

    @task(1)
    def tutor_chat(self):
        """AI 튜터 질문."""
        questions = ["PER이 뭐야?", "삼성전자 분석해줘", "금리 인상이 뭐야?"]
        self.client.post(
            "/api/v1/tutor/chat",
            json={"message": random.choice(questions), "difficulty": "beginner"},
            name="[API] Tutor",
        )

    @task(1)
    def submit_feedback(self):
        """피드백 제출."""
        self.client.post(
            "/api/v1/feedback",
            json={
                "page": random.choice(["home", "narrative", "portfolio", "tutor"]),
                "rating": random.randint(3, 5),
                "category": random.choice(["design", "feature", "content"]),
                "comment": "부하 테스트 피드백",
            },
            name="[API] Feedback",
        )

    @task(1)
    def get_glossary(self):
        """용어 사전 조회."""
        self.client.get("/api/v1/glossary", name="[API] Glossary")

    @task(1)
    def get_portfolio(self):
        """포트폴리오 조회."""
        self.client.get("/api/v1/portfolio/1", name="[API] Portfolio")
