"""Company relationship tools using Neo4j and PostgreSQL."""

import os
import sys
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


@tool
def get_related_companies(stock_code: str) -> str:
    """
    특정 기업의 관련 기업들을 조회합니다. 공급망, 경쟁사 등의 관계를 포함합니다.
    
    Args:
        stock_code: 종목 코드 (예: 005930)
        
    Returns:
        관련 기업 목록 (JSON 형식)
    """
    import json
    
    try:
        from services.neo4j_service import get_neo4j_service
        
        neo4j = get_neo4j_service()
        
        if not neo4j.verify_connectivity():
            return json.dumps({"error": "Neo4j not available"}, ensure_ascii=False)
        
        # Get company info
        company = neo4j.get_company(stock_code)
        
        if not company:
            return json.dumps({"error": f"종목 {stock_code}를 찾을 수 없습니다."}, ensure_ascii=False)
        
        # Get supply chain
        supply_chain = neo4j.get_supply_chain(stock_code, direction="both", max_hops=2)
        
        # Get competitors
        competitors = neo4j.get_competitors(stock_code)
        
        result = {
            "company": {
                "stock_code": stock_code,
                "name": company.get("name", "Unknown"),
                "market": company.get("market", "Unknown"),
            },
            "supply_chain": [
                {
                    "stock_code": item["company"].get("stock_code"),
                    "name": item["company"].get("name"),
                    "hops": item["hops"],
                    "relationships": item.get("relationships", []),
                }
                for item in supply_chain[:10]
            ],
            "competitors": [
                {
                    "stock_code": item["company"].get("stock_code"),
                    "name": item["company"].get("name"),
                    "segment": item["segment"],
                }
                for item in competitors[:5]
            ],
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except ImportError:
        return json.dumps({
            "error": "Neo4j service not available",
            "company": {"stock_code": stock_code},
            "supply_chain": [],
            "competitors": [],
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


@tool
def get_supply_chain(
    stock_code: str,
    direction: str = "both",
    max_hops: int = 2,
) -> str:
    """
    특정 기업의 공급망(supply chain)을 조회합니다.
    
    Args:
        stock_code: 종목 코드
        direction: 방향 (suppliers/customers/both)
        max_hops: 최대 홉 수 (관계 거리)
        
    Returns:
        공급망 정보 (JSON 형식)
    """
    import json
    
    try:
        from services.neo4j_service import get_neo4j_service
        
        neo4j = get_neo4j_service()
        
        if not neo4j.verify_connectivity():
            return json.dumps({"error": "Neo4j not available"}, ensure_ascii=False)
        
        supply_chain = neo4j.get_supply_chain(
            stock_code,
            direction=direction,
            max_hops=max_hops,
        )
        
        result = {
            "stock_code": stock_code,
            "direction": direction,
            "max_hops": max_hops,
            "supply_chain": [
                {
                    "stock_code": item["company"].get("stock_code"),
                    "name": item["company"].get("name"),
                    "hops": item["hops"],
                    "products": [
                        rel.get("product", "Unknown")
                        for rel in item.get("relationships", [])
                    ],
                }
                for item in supply_chain
            ],
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except ImportError:
        return json.dumps({
            "error": "Neo4j service not available",
            "stock_code": stock_code,
            "supply_chain": [],
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
