from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


MODEL_ID = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def collection_name(raw: bytes) -> str:
    identity = f"demo-v1:{MODEL_ID}:{MODEL_REVISION}:".encode() + raw
    return "events_demo_" + hashlib.sha256(identity).hexdigest()[:16]


class LocalEventSearch:
    """Read the CLI-built local index; serialize model and file-store access."""

    def __init__(self, documents: Path, db_path: Path, model_cache: Path) -> None:
        self.documents = documents
        self.db_path = db_path
        self.model_cache = model_cache
        self._lock = Lock()
        self._model: SentenceTransformer | None = None

    def search(self, texts: list[str], excluded_ids: list[int]) -> list[int]:
        try:
            with self._lock:
                return self._search(texts, excluded_ids)
        except MIBaseError:
            raise
        except Exception as exc:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail="로컬 벡터 검색 실패. 의존성 설치, 사전 적재 및 Qdrant 파일 잠금을 확인하세요.",
            ) from exc

    def _search(self, texts: list[str], excluded_ids: list[int]) -> list[int]:
        from qdrant_client import QdrantClient, models
        from sentence_transformers import SentenceTransformer

        raw = self.documents.read_bytes()
        documents = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        if not 1 <= len(documents) <= 1000:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="로컬 검색 문서는 1~1,000개여야 합니다.")
        collection = collection_name(raw)
        client = QdrantClient(path=str(self.db_path))
        try:
            if not client.collection_exists(collection) or client.count(collection, exact=True).count != len(documents):
                raise MIBaseError(
                    ErrorCode.DATA_RETRIEVAL_FAILED,
                    detail="검색 인덱스가 없습니다. local_event_vector_search.py로 먼저 적재하세요.",
                )
            if self._model is None:
                self._model = SentenceTransformer(
                    MODEL_ID,
                    revision=MODEL_REVISION,
                    device="cpu",
                    cache_folder=str(self.model_cache),
                    trust_remote_code=False,
                )
            for text in texts:
                tokens = self._model.tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"]
                if len(tokens) > self._model.max_seq_length:
                    raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Event가 임베딩 입력 한도를 초과했습니다.")
            vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
            query_filter = models.Filter(
                must_not=[
                    models.FieldCondition(key="event_id", match=models.MatchAny(any=excluded_ids)),
                ],
            )
            scores: dict[int, float] = {}
            for vector in vectors:
                hits = client.query_points(
                    collection_name=collection,
                    query=vector,
                    query_filter=query_filter,
                    limit=len(documents),
                    with_payload=True,
                ).points
                for hit in hits:
                    event_id = int((hit.payload or {})["event_id"])
                    if event_id not in excluded_ids:
                        scores[event_id] = max(scores.get(event_id, -1.0), hit.score)
            return sorted(scores, key=lambda event_id: (-scores[event_id], event_id))[:30]
        finally:
            client.close()


@lru_cache(maxsize=1)
def get_local_event_search(documents: Path, db_path: Path, model_cache: Path) -> LocalEventSearch:
    return LocalEventSearch(documents, db_path, model_cache)
