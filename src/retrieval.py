"""
검색 로직
- 키워드 검색 (토큰 오버랩 기반)
- 벡터 검색 (OpenAI 임베딩 기반)
- 하이브리드 (벡터 60% + 키워드 40%)
- 질문에서 필터(카드사/카테고리/연회비구간) 자동 추론
"""

import json
import os
import re
import unicodedata
from pathlib import Path

_RE_HAS_KOREAN = re.compile(r"[가-힣]")
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import numpy as np
except Exception:
    np = None

from .utils import (
    FEE_BANDS_ORDERED,
    classify_fee_band,
    expand_query_with_synonyms,
    safe_get,
    tokenize,
)


def load_rag_settings(config_path: Path) -> Dict[str, Any]:
    default_settings = {
        "top_k": 5,
        "similarity_threshold": 0.6,
        "embedding_model": "text-embedding-3-small",
    }
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        search_cfg = raw.get("검색설정", {}) if isinstance(raw, dict) else {}
        emb_cfg = raw.get("임베딩설정", {}) if isinstance(raw, dict) else {}
        top_k = int(search_cfg.get("상위K", default_settings["top_k"]))
        threshold = float(search_cfg.get("유사도_임계값", default_settings["similarity_threshold"]))
        model = str(emb_cfg.get("모델", default_settings["embedding_model"]))
        return {
            "top_k": max(1, top_k),
            "similarity_threshold": max(0.0, min(1.0, threshold)),
            "embedding_model": model,
        }
    except Exception:
        return default_settings


def load_vector_store(index_dir: Path) -> Optional[Dict[str, Any]]:
    if np is None:
        return None
    index_path = index_dir / "vector_index.npz"
    meta_path = index_dir / "vector_meta.jsonl"
    info_path = index_dir / "index_info.json"
    if not (index_path.exists() and meta_path.exists() and info_path.exists()):
        return None
    try:
        npz = np.load(index_path)
        embeddings = npz["embeddings"]
        if embeddings.ndim != 2 or embeddings.shape[0] == 0:
            return None
        meta_rows: List[Dict[str, Any]] = []
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    meta_rows.append(json.loads(line))
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if len(meta_rows) != int(embeddings.shape[0]):
            return None
        return {
            "embeddings": embeddings,
            "meta": meta_rows,
            "normalized": bool(info.get("normalized", False)),
        }
    except Exception:
        return None


def infer_fee_bands_from_question(question: str) -> Set[str]:
    q = question.replace(",", "")
    q_lower = q.lower()
    bands: Set[str] = set()

    premium_keywords = ["비싼", "고급", "프리미엄", "프리미엄", "럭셔리", "고가", "최고급"]
    cheap_keywords = ["싼", "저렴", "싸다", "저가", "무료"]
    standard_keywords = ["일반", "보통", "중간", "표준"]

    if any(kw in q_lower for kw in premium_keywords):
        bands.update(["PREMIUM(3~10만원)", "PRESTIGE(10만원 초과)"])
        return bands
    if any(kw in q_lower for kw in cheap_keywords):
        bands.update(["FREE", "ENTRY(1만원 이하)", "STANDARD(1~3만원)"])
        return bands
    if any(kw in q_lower for kw in standard_keywords):
        bands.add("STANDARD(1~3만원)")
        return bands

    nums = re.findall(r"(\d+)\s*만원", q)
    if not nums:
        return bands
    amount = int(nums[0]) * 10000
    has_under = any(token in q for token in ["이하", "미만", "까지", "under", "less than"])
    has_over = any(token in q for token in ["이상", "초과", "over", "more than"])
    target = classify_fee_band(amount)
    idx = FEE_BANDS_ORDERED.index(target)
    if has_under:
        bands.update(FEE_BANDS_ORDERED[: idx + 1])
    elif has_over:
        bands.update(FEE_BANDS_ORDERED[idx:])
    else:
        bands.add(target)
    return bands


def infer_filters_from_question(
    question: str,
    banks: List[str],
    categories: List[str],
    fee_bands: List[str],
) -> Dict[str, List[str]]:
    q_lower = question.lower()
    inferred_banks = [b for b in banks if b.lower() in q_lower]
    inferred_categories = [c for c in categories if c.lower() in q_lower]
    inferred_fee = set([b for b in fee_bands if b.lower() in q_lower])
    inferred_fee.update(infer_fee_bands_from_question(question))
    inferred_fee = [b for b in fee_bands if b in inferred_fee]
    return {
        "banks": inferred_banks,
        "categories": inferred_categories,
        "fee_bands": inferred_fee,
    }


_NAME_BOOST_STOPWORDS = {"카드", "pdf", "json", "카드의", "카드를", "카드가", "카드는", "카드에", "이", "가", "은", "는", "을"}


def _passes_filters(
    card: Dict[str, Any],
    banks: List[str],
    categories: List[str],
    fee_bands: List[str],
) -> bool:
    bank = safe_get(card, ["card", "bank"], "미분류")
    if banks and bank not in banks:
        return False
    card_categories = safe_get(card, ["_derived", "categories"], [])
    card_fee_band = safe_get(card, ["_derived", "fee_band"], "")
    if categories and not any(c in card_categories for c in categories):
        return False
    if fee_bands and card_fee_band not in fee_bands:
        return False
    return True


def retrieve_cards_keyword(
    cards: List[Dict[str, Any]],
    query: str,
    top_k: int,
    banks: List[str],
    categories: List[str],
    fee_bands: List[str],
    synonyms: Dict[str, Set[str]],
) -> List[Tuple[float, Dict[str, Any]]]:
    q_tokens = expand_query_with_synonyms(query, synonyms)
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for card in cards:
        if not _passes_filters(card, banks, categories, fee_bands):
            continue

        overlap = q_tokens.intersection(card.get("_tokens", set()))
        if not overlap:
            continue

        score = float(len(overlap))
        benefit_overlap = q_tokens.intersection(card.get("_benefit_tokens", set()))
        if benefit_overlap:
            score += float(len(benefit_overlap)) * 2.2
        name = safe_get(card, ["card", "name"], "")
        file_name = card.get("_file", "")
        name_nfc = unicodedata.normalize("NFC", name or "")
        file_nfc = unicodedata.normalize("NFC", file_name or "")
        query_nfc = unicodedata.normalize("NFC", query or "").lower()
        name_tokens = set(tokenize(name_nfc)) | set(tokenize(file_nfc))
        name_overlap = q_tokens.intersection(name_tokens) - _NAME_BOOST_STOPWORDS
        if name_overlap:
            score += float(len(name_overlap)) * 4.0
        file_lower = unicodedata.normalize("NFC", file_name or "").lower()
        name_lower = name_nfc.lower()
        category_match = False
        for tok in q_tokens:
            tok_nfc = unicodedata.normalize("NFC", tok)
            if len(tok_nfc) < 2 or tok_nfc in _NAME_BOOST_STOPWORDS:
                continue
            is_korean = bool(_RE_HAS_KOREAN.search(tok_nfc))
            if is_korean:
                if tok_nfc in name_lower or tok_nfc in file_lower:
                    score += 6.0
                    category_match = True
            else:
                if tok_nfc in (set(tokenize(file_nfc)) | set(tokenize(name_nfc))):
                    score += 6.0
                    category_match = True
        if category_match:
            score *= 2.5
            card = dict(card)
            card["_category_match"] = True
        usage_scope = safe_get(card, ["card", "features", "usage_scope"], "")
        if usage_scope and usage_scope.lower() in query_nfc:
            score += 1.5

        scored.append((score, card))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[: max(1, top_k)]


def retrieve_cards_vector(
    cards: List[Dict[str, Any]],
    query: str,
    top_k: int,
    banks: List[str],
    categories: List[str],
    fee_bands: List[str],
    vector_store: Dict[str, Any],
    embedding_model: str,
    similarity_threshold: float,
) -> List[Tuple[float, Dict[str, Any]]]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or np is None:
        return []

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        q = client.embeddings.create(model=embedding_model, input=[query]).data[0].embedding
        q_vec = np.asarray(q, dtype=np.float32)
        if vector_store.get("normalized", False):
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec = q_vec / q_norm

        matrix = vector_store["embeddings"]
        sims = matrix @ q_vec
        order = np.argsort(-sims)

        file_to_card: Dict[str, Dict[str, Any]] = {c.get("_file", ""): c for c in cards}
        card_scores: Dict[str, float] = {}
        card_evidence: Dict[str, str] = {}

        for idx in order[: min(len(order), max(50, top_k * 8))]:
            score = float(sims[idx])
            if score < similarity_threshold:
                continue
            meta = vector_store["meta"][int(idx)]
            src_file = meta.get("source_file", "")
            if not src_file or src_file not in file_to_card:
                continue
            card = file_to_card[src_file]
            if not _passes_filters(card, banks, categories, fee_bands):
                continue
            prev = card_scores.get(src_file, -1.0)
            if score > prev:
                card_scores[src_file] = score
                snippet = str(meta.get("text", "")).replace("\n", " ").strip()
                if len(snippet) > 220:
                    snippet = snippet[:220].rstrip() + "..."
                card_evidence[src_file] = snippet

        ranked = sorted(card_scores.items(), key=lambda x: x[1], reverse=True)
        results: List[Tuple[float, Dict[str, Any]]] = []
        for src, score in ranked[: max(1, top_k)]:
            base = file_to_card[src]
            card_with_evidence = dict(base)
            card_with_evidence["_retrieval_evidence"] = card_evidence.get(src, "")
            results.append((score, card_with_evidence))
        return results
    except Exception:
        return []


def retrieve_cards_hybrid(
    cards: List[Dict[str, Any]],
    query: str,
    top_k: int,
    banks: List[str],
    categories: List[str],
    fee_bands: List[str],
    vector_store: Optional[Dict[str, Any]],
    embedding_model: str,
    similarity_threshold: float,
    synonyms: Dict[str, Set[str]],
    vector_weight: float = 0.6,
    keyword_weight: float = 0.4,
) -> List[Tuple[float, Dict[str, Any]]]:
    """벡터 + 키워드 하이브리드 랭킹 (정규화 점수 가중합)"""
    vec_results: List[Tuple[float, Dict[str, Any]]] = []
    key_results: List[Tuple[float, Dict[str, Any]]] = []

    if vector_store:
        vec_results = retrieve_cards_vector(
            cards,
            query,
            top_k=top_k * 2,
            banks=banks,
            categories=categories,
            fee_bands=fee_bands,
            vector_store=vector_store,
            embedding_model=embedding_model,
            similarity_threshold=similarity_threshold,
        )

    key_results = retrieve_cards_keyword(
        cards,
        query,
        top_k=top_k * 2,
        banks=banks,
        categories=categories,
        fee_bands=fee_bands,
        synonyms=synonyms,
    )

    if not vec_results and not key_results:
        return []
    if not vec_results:
        return key_results[:top_k]
    if not key_results:
        return vec_results[:top_k]

    # Reciprocal Rank Fusion: score = vec_weight/(k+rank_v) + kw_weight/(k+rank_k)
    # category_match 카드(파일명/카드명 직접 일치)는 keyword RRF 가중치 2배 적용
    RRF_K = 30
    file_to_card: Dict[str, Dict[str, Any]] = {}
    rrf_scores: Dict[str, float] = {}

    for rank, (_, card) in enumerate(vec_results):
        fn = card.get("_file", "")
        file_to_card[fn] = card
        rrf_scores[fn] = rrf_scores.get(fn, 0.0) + vector_weight / (RRF_K + rank + 1)

    for rank, (_, card) in enumerate(key_results):
        fn = card.get("_file", "")
        file_to_card.setdefault(fn, card)
        kw = keyword_weight * (2.5 if card.get("_category_match") else 1.0)
        rrf_scores[fn] = rrf_scores.get(fn, 0.0) + kw / (RRF_K + rank + 1)

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [(score, file_to_card[fn]) for fn, score in ranked[:top_k]]
