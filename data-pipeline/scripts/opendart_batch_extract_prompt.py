#!/usr/bin/env python3
"""
# [2026-02-04] OpenDART Batch 추출용 프롬프트 템플릿
OpenDART 사업보고서 XML에서 기업 연관관계 데이터를 추출하기 위한
시스템 프롬프트 및 출력 스키마 정의. OpenAI Batch API 입력 생성 시 사용.
"""

from __future__ import annotations

import argparse
import json


SYSTEM_PROMPT = """OpenDART 사업보고서 XML에서 기업 연관관계 데이터를 추출합니다.

## 추출 대상 및 설명

### 1. products (주요 제품 및 서비스)
- 출처: "2. 주요 제품 및 서비스" 섹션의 "주요 제품 등의 현황" 테이블
- item_name: 품목, 제품명, 서비스명 (예: "2차전지 소재", "신선육", "합성고무")
- sales_type: 매출유형 컬럼 값 (예: "제품", "상품", "서비스")
- sales_amount: 매출액 원문 그대로 (예: "82,594", "663,139")
- sales_ratio: 비율(%) 컬럼 값 (예: "51.12%", "59.00%")
- brand: 주요상표 컬럼 값 (예: "강원이솔루션", "하림 닭고기")
- description: 제품설명 컬럼 값 (예: "리튬 가공, 첨가제 가공")

### 2. materials (원재료)
- 출처: "3. 원재료 및 생산설비" 섹션의 "주요원재료 등의 매입 현황" 테이블
- item_name: 품목 컬럼 (예: "수산화리튬", "철판류", "SM", "BD")
- use: 구체적용도 컬럼 (예: "SBR, PS, ABS 외", "리튬 원료")
- purchase_type: 매입유형 컬럼 (예: "원재료", "부재료", "상품")
- purchase_amount: 매입액 원문 (예: "77,160,306", "1,046,219")
- purchase_ratio: 비율(%) 컬럼 (예: "57.5%", "78.75%")

### 3. suppliers (공급처/매입처)
- 출처: 원재료 테이블의 "비고", "주요매입처", "공급처" 컬럼 또는 본문 "다. 주요 매입처에 관한 사항"
- name: 공급업체명 (예: "여천NCC", "에스케이피아이씨글로벌", "YNCC")
- item: 관련 품목 (예: "BD", "SM", "BENZENE")
- ratio: 비중 있으면 기재

### 4. customers (주요 고객)
- 출처: 제품 테이블의 "주요 고객정보", "주요 고객" 컬럼 또는 사업부문 테이블
- name: 고객사명 (예: "한국전력거래소", "한국전력공사", "Jindal")
- segment: 관련 사업부문 (예: "가스전력사업", "무역")
- ratio: 매출비중 있으면 기재

### 5. subsidiaries (종속회사/자회사)
- 출처: "[주요 종속회사 : ...]" 문구, 또는 별도 종속회사 섹션
- name: 종속회사명 (예: "금호피앤비화학", "하림", "강원이솔루션")
- business_type: 사업유형 (예: "기초유기화합물", "육계", "2차전지 소재")
- main_products: 주요 제품 (예: "Phenol, BPA", "닭고기", "수산화리튬")

### 6. business_segments (사업부문)
- 출처: 사업부문별 매출 테이블, 보고부문 설명
- segment_name: 사업부문명 (예: "2차전지사업부문", "플랜트사업부문", "유통", "합성고무")
- main_goods_services: 주요 재화/용역 (예: "2차전지 소재, 2차전지 설비", "일반소비용품")
- sales_amount: 매출액 원문 (예: "140,096", "8,755,587")

### 7. exceptions (예외 플래그)
- supplier_confidential: "보안유지", "영업비밀", "기재하지 않았습니다" 등 비공개 문구 있으면 true
- no_products_section: 제품 섹션/테이블이 없으면 true
- no_materials_section: 원재료 섹션/테이블이 없으면 true
- empty_xml: XML에 유효한 데이터가 거의 없으면 true
- holding_company: "순수지주회사", "생산하는 제품이 없습니다" 문구 있으면 true

## 추출 규칙
1. 테이블 <TD> 셀에서 텍스트를 추출. HTML 태그는 제외하고 텍스트만 추출.
2. 회사명 정규화: "(주)", "주식회사", "㈜" 제거. 영문명은 원문 유지.
3. 숫자는 단위 변환 없이 원문 그대로 기재 (예: "82,594" → "82,594").
4. 데이터가 없으면 빈 배열 [], 미확인 필드는 null.
5. "-", "해당없음", "합계", "소계" 등 의미 없는 행은 제외.
6. 여러 회사명이 쉼표/공백으로 나열되면 각각 별도 객체로 분리.
"""

# Few-shot 예시 (중괄호는 {{}} 로 이스케이프)
FEW_SHOT_EXAMPLE = """{{
  "products": [
    {{"item_name": "2차전지 소재", "sales_type": "제품", "sales_amount": "82,594", "sales_ratio": "51.12%", "brand": "강원이솔루션", "description": "리튬 가공, 첨가제 가공"}},
    {{"item_name": "산업용증기발생기", "sales_type": "제품", "sales_amount": "17,523", "sales_ratio": "10.85%", "brand": "강원에너지", "description": "수관식증기발생기 등"}}
  ],
  "materials": [
    {{"item_name": "수산화리튬", "use": "2차전지 소재 원료", "purchase_type": "원재료", "purchase_amount": "77,160,306", "purchase_ratio": null}},
    {{"item_name": "SM", "use": "SBR, PS, ABS 외", "purchase_type": "원재료", "purchase_amount": "519,653", "purchase_ratio": "28.5%"}}
  ],
  "suppliers": [
    {{"name": "여천NCC", "item": "BD", "ratio": null}},
    {{"name": "에스케이피아이씨글로벌", "item": "SM", "ratio": null}}
  ],
  "customers": [
    {{"name": "한국전력거래소", "segment": "가스전력사업", "ratio": null}},
    {{"name": "Jindal", "segment": "무역", "ratio": null}}
  ],
  "subsidiaries": [
    {{"name": "금호피앤비화학", "business_type": "기초유기화합물", "main_products": "Phenol, BPA"}},
    {{"name": "강원이솔루션", "business_type": "2차전지 소재", "main_products": "수산화리튬"}}
  ],
  "business_segments": [
    {{"segment_name": "2차전지사업부문", "main_goods_services": "2차전지 소재, 2차전지 설비", "sales_amount": "140,096"}},
    {{"segment_name": "플랜트사업부문", "main_goods_services": "산업용증기발생기, 화공설비", "sales_amount": "21,462"}}
  ],
  "exceptions": {{
    "supplier_confidential": false,
    "no_products_section": false,
    "no_materials_section": false,
    "empty_xml": false,
    "holding_company": false
  }}
}}"""

USER_PROMPT_TEMPLATE = """다음 OpenDART 사업보고서 XML(사업의 내용 중 주요 제품·원재료 섹션)에서
기업 연관관계 데이터를 추출하여 JSON으로만 응답하세요.

- corp_code: {corp_code}
- rcept_no: {rcept_no}
- rcept_dt: {rcept_dt}

XML:
```
{xml_content}
```

## 출력 예시
다음과 같은 형식으로 JSON을 출력하세요:
```json
""" + FEW_SHOT_EXAMPLE + """
```

위 예시를 참고하여, 주어진 XML에서 추출한 데이터를 JSON으로만 출력하세요.
다른 설명은 포함하지 마세요."""


OUTPUT_SCHEMA = {
    "products": [
        {
            "item_name": "str: 품목/제품명",
            "sales_type": "str|null: 매출유형(제품/서비스/상품 등)",
            "sales_amount": "str|null: 매출액 원문",
            "sales_ratio": "str|null: 매출비중(%)",
            "brand": "str|null: 주요상표",
            "description": "str|null: 제품설명",
        }
    ],
    "materials": [
        {
            "item_name": "str: 품목명",
            "use": "str|null: 용도/구체적용도",
            "purchase_type": "str|null: 매입유형(원재료/부재료/상품 등)",
            "purchase_amount": "str|null: 매입액 원문",
            "purchase_ratio": "str|null: 매입비중(%)",
        }
    ],
    "suppliers": [
        {
            "name": "str: 공급처명",
            "item": "str|null: 관련 품목",
            "ratio": "str|null: 비중",
        }
    ],
    "customers": [
        {
            "name": "str: 고객사명",
            "segment": "str|null: 관련 사업부문",
            "ratio": "str|null: 매출비중(존재 시)",
        }
    ],
    "subsidiaries": [
        {
            "name": "str: 종속회사명",
            "business_type": "str|null: 사업유형",
            "main_products": "str|null: 주요 제품/서비스",
        }
    ],
    "business_segments": [
        {
            "segment_name": "str: 사업부문명",
            "main_goods_services": "str|null: 주요 재화/용역",
            "sales_amount": "str|null: 매출액 원문",
        }
    ],
    "exceptions": {
        "supplier_confidential": "bool: 공급처 등 비공개 명시",
        "no_products_section": "bool: 제품 섹션 없음",
        "no_materials_section": "bool: 원재료 섹션 없음",
        "empty_xml": "bool: 유효 데이터 없음",
        "holding_company": "bool: 지주회사로 제품 없음",
    },
}


def get_system_prompt() -> str:
    return SYSTEM_PROMPT


def get_user_prompt(corp_code: str, rcept_no: str, rcept_dt: str, xml_content: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        corp_code=corp_code,
        rcept_no=rcept_no,
        rcept_dt=rcept_dt,
        xml_content=xml_content,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenDART Batch 추출 프롬프트 템플릿")
    parser.add_argument("--output-schema", action="store_true", help="출력 스키마 JSON 출력")
    args = parser.parse_args()
    if args.output_schema:
        print(json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
