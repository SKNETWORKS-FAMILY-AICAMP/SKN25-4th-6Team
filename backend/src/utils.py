"""
유틸리티 함수 모음
- 토큰화, 안전 딕셔너리 접근, 연회비 분류
- 동의어 확장 (config/synonyms.json 로드)
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set


_KR_PARTICLES = re.compile(
    r"(한테서|에게서|로부터|으로부터|한테|에게|에서|부터|까지|처럼|만큼|뿐|만|씩|마다|로서|으로서|로써|으로써|는데|는지|는가|되는|하는|된다|한다|된|한|를|이|가|은|는|을|도|와|과|의|로|으로|이다)$"
)


def tokenize(text: str) -> List[str]:
    """텍스트를 토큰화 (한국어 조사·어미 분리, 한영 복합 토큰 분리)"""
    if not text:
        return []
    tokens: List[str] = []
    seen: set = set()

    def _add(t: str) -> None:
        if t and len(t) >= 2 and t not in seen:
            seen.add(t)
            tokens.append(t)

    for raw in re.findall(r"[0-9a-zA-Z가-힣&]+", text):
        t = raw.lower()
        _add(t)
        stripped = _KR_PARTICLES.sub("", t)
        if stripped != t:
            _add(stripped)
        # 한영·영한 경계 분리: "oil카드" → "oil" + "카드"
        for sub in re.findall(r"[가-힣]+|[a-zA-Z0-9]+", raw):
            _add(sub.lower())
    return tokens


def safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    """중첩 딕셔너리에서 안전하게 값 가져오기"""
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


@lru_cache(maxsize=4)
def load_synonyms(config_path: str) -> Dict[str, Set[str]]:
    """config/synonyms.json 로드. 경로를 문자열로 받아 캐시 가능하게 함."""
    try:
        raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
        syn = raw.get("synonyms", {}) if isinstance(raw, dict) else {}
        return {k: set(v) for k, v in syn.items() if isinstance(v, list)}
    except Exception:
        return {}


def expand_query_with_synonyms(query: str, synonyms: Dict[str, Set[str]]) -> Set[str]:
    """검색 쿼리에 동의어 확장. synonyms를 명시적으로 주입받음."""
    tokens = set(tokenize(query.lower()))
    expanded = set(tokens)
    for token in tokens:
        if token in synonyms:
            expanded.update(synonyms[token])
    return expanded


def classify_fee_band(annual_fee: int) -> str:
    """연회비를 구간으로 분류"""
    if annual_fee <= 0:
        return "FREE"
    if annual_fee <= 10000:
        return "ENTRY(1만원 이하)"
    if annual_fee <= 30000:
        return "STANDARD(1~3만원)"
    if annual_fee <= 100000:
        return "PREMIUM(3~10만원)"
    return "PRESTIGE(10만원 초과)"


FEE_BANDS_ORDERED: List[str] = [
    "FREE",
    "ENTRY(1만원 이하)",
    "STANDARD(1~3만원)",
    "PREMIUM(3~10만원)",
    "PRESTIGE(10만원 초과)",
]
