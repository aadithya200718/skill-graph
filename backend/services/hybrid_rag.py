import json
import math
import logging
from pathlib import Path
from collections import defaultdict

from services.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)

_concepts_cache: list[dict] | None = None


def _load_concepts() -> list[dict]:
    global _concepts_cache
    if _concepts_cache is not None:
        return _concepts_cache
    path = Path(__file__).parent.parent / "data" / "concepts.json"
    with open(path, "r", encoding="utf-8") as f:
        _concepts_cache = json.load(f)
    return _concepts_cache


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = []
    current = []
    for ch in text:
        if ch.isalnum():
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[dict] = []
        self.doc_tokens: list[list[str]] = []
        self.df: dict[str, int] = defaultdict(int)
        self.avg_dl: float = 0.0
        self._built = False

    def build(self, concepts: list[dict]):
        self.docs = concepts
        self.doc_tokens = []
        token_counts: dict[str, set[int]] = defaultdict(set)

        for i, concept in enumerate(concepts):
            text = " ".join([
                concept.get("concept_id", ""),
                concept.get("name", ""),
                concept.get("subject", ""),
                concept.get("category", ""),
            ])
            tokens = _tokenize(text)
            self.doc_tokens.append(tokens)
            for token in set(tokens):
                token_counts[token].add(i)

        self.df = {token: len(doc_ids) for token, doc_ids in token_counts.items()}
        total_len = sum(len(t) for t in self.doc_tokens)
        self.avg_dl = total_len / len(self.doc_tokens) if self.doc_tokens else 1.0
        self._built = True

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        if not self._built:
            return []

        query_tokens = _tokenize(query)
        n = len(self.docs)
        scores: dict[int, float] = defaultdict(float)

        for token in query_tokens:
            if token not in self.df:
                continue
            idf = math.log((n - self.df[token] + 0.5) / (self.df[token] + 0.5) + 1.0)

            for doc_idx, doc_tokens in enumerate(self.doc_tokens):
                tf = doc_tokens.count(token)
                if tf == 0:
                    continue
                dl = len(doc_tokens)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                scores[doc_idx] += idf * numerator / denominator

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.docs[idx]["concept_id"], score) for idx, score in ranked]


class HybridRAG:
    def __init__(self, neo4j_service: Neo4jService):
        self._neo4j = neo4j_service
        self._bm25 = BM25Index()
        self._initialized = False
        self.bm25_weight = 0.35
        self.graph_weight = 0.65

    def _ensure_initialized(self):
        if self._initialized:
            return
        concepts = _load_concepts()
        self._bm25.build(concepts)
        self._initialized = True

    async def search(
        self,
        query: str,
        gap_ids: list[str] | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        self._ensure_initialized()

        bm25_results = self._bm25.search(query, top_k=top_k * 2)
        bm25_scores: dict[str, float] = {}
        if bm25_results:
            max_bm25 = max(s for _, s in bm25_results) or 1.0
            bm25_scores = {cid: s / max_bm25 for cid, s in bm25_results}

        graph_scores: dict[str, float] = {}
        if gap_ids:
            for gap_id in gap_ids[:5]:
                prereqs = await self._neo4j.get_prerequisites(gap_id)
                depth = 1.0
                for prereq in prereqs:
                    pid = prereq.concept_id if hasattr(prereq, 'concept_id') else (
                        prereq["concept_id"] if isinstance(prereq, dict) else str(prereq)
                    )
                    score = 0.5 / depth
                    graph_scores[pid] = max(graph_scores.get(pid, 0.0), score)
                    depth += 0.5

        all_ids = set(bm25_scores.keys()) | set(graph_scores.keys())
        combined: list[dict] = []

        concepts = _load_concepts()
        concept_map = {c["concept_id"]: c for c in concepts}

        for cid in all_ids:
            bm25_s = bm25_scores.get(cid, 0.0)
            graph_s = graph_scores.get(cid, 0.0)
            final = self.bm25_weight * bm25_s + self.graph_weight * graph_s

            concept = concept_map.get(cid, {})
            combined.append({
                "concept_id": cid,
                "name": concept.get("name", cid),
                "subject": concept.get("subject", ""),
                "semester": concept.get("semester", 0),
                "score": round(final, 4),
                "bm25_score": round(bm25_s, 4),
                "graph_score": round(graph_s, 4),
            })

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:top_k]
