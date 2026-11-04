from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.agents.scenario_group_agent.schemas.event_search_document import EventSearchDocument  # noqa: E402
from apps.common.exceptions.custom import MIBaseError  # noqa: E402
from apps.common.values.error_codes import ErrorCode  # noqa: E402
from apps.connectors.vdb.local_event_search import MODEL_ID, MODEL_REVISION, collection_name  # noqa: E402


if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


LOGGER = logging.getLogger("local_event_vector_search")
DEFAULT_DOCUMENTS = ROOT_DIR / "local/output/event_search_documents/20261030_sample/documents.jsonl"


def load_documents(path: Path) -> tuple[list[EventSearchDocument], str]:
    raw = path.read_bytes()
    documents = [
        EventSearchDocument.model_validate_json(line) for line in raw.decode("utf-8").splitlines() if line.strip()
    ]
    if not 1 <= len(documents) <= 1000 or len({doc.document_id for doc in documents}) != len(documents):
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="로컬 샘플은 중복 ID 없는 문서 1~1,000개여야 합니다.")
    return documents, collection_name(raw)


def event_query(documents: Sequence[EventSearchDocument], event_id: int) -> str:
    chunks = sorted(
        (doc for doc in documents if doc.metadata.event_id == event_id),
        key=lambda doc: doc.metadata.chunk_index,
    )
    if not chunks:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"샘플에 Event {event_id}가 없습니다.")
    if [doc.metadata.chunk_index for doc in chunks] != list(range(chunks[0].metadata.chunk_count)):
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="기준 Event의 문서 조각이 누락되거나 중복되었습니다.")
    return "".join(doc.content for doc in chunks)


def _encode(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    for text in texts:
        token_ids = model.tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"]
        if len(token_ids) > model.max_seq_length:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="임베딩 입력 한도를 초과했습니다. 문서를 더 작게 분할하세요.",
            )
    return model.encode(texts, batch_size=2, normalize_embeddings=True, show_progress_bar=True).tolist()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Small, single-process BGE-M3 + Qdrant local demo.")
    parser.add_argument("--documents", type=Path, default=DEFAULT_DOCUMENTS)
    parser.add_argument("--db-path", type=Path, default=ROOT_DIR / "local/qdrant_event_demo")
    parser.add_argument("--model-cache", type=Path, default=ROOT_DIR / "local/models")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Check JSONL without downloading models or opening Qdrant",
    )
    query_args = parser.add_mutually_exclusive_group()
    query_args.add_argument("--query", help="Free-text similarity query")
    query_args.add_argument("--event-id", type=int, help="Find other Events related to this Event in the sample")
    args = parser.parse_args(argv)
    if args.top_k < 1 or (args.event_id is not None and args.event_id <= 0):
        parser.error("top-k and event-id must be positive")
    if args.query is not None and not args.query.strip():
        parser.error("query must not be blank")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    documents, collection = load_documents(args.documents)
    query = event_query(documents, args.event_id) if args.event_id is not None else args.query
    if args.validate_only:
        LOGGER.info(
            "Valid JSONL: %s documents / %s Events",
            len(documents),
            len({doc.metadata.event_id for doc in documents}),
        )
        return 0

    from qdrant_client import QdrantClient, models
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        MODEL_ID,
        revision=MODEL_REVISION,
        device=args.device,
        cache_folder=str(args.model_cache),
        trust_remote_code=False,
    )
    args.db_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(args.db_path))
    try:
        if not client.collection_exists(collection):
            client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
            )
        if client.count(collection_name=collection, exact=True).count != len(documents):
            vectors = _encode(model, [doc.text for doc in documents])
            client.upsert(
                collection_name=collection,
                points=[
                    models.PointStruct(
                        id=str(uuid5(NAMESPACE_URL, doc.document_id)),
                        vector=vector,
                        payload={
                            **doc.metadata.model_dump(mode="json"),
                            "document_id": doc.document_id,
                            "text": doc.text,
                        },
                    )
                    for doc, vector in zip(documents, vectors, strict=True)
                ],
                wait=True,
            )
            LOGGER.info("Indexed %s documents in %s", len(documents), collection)
        else:
            LOGGER.info("Reusing %s indexed documents in %s", len(documents), collection)
        if query is None:
            return 0
        query_filter = models.Filter(
            must=[
                models.FieldCondition(key="publish_status", match=models.MatchValue(value="PUBLISHED")),
                models.FieldCondition(key="del_yn", match=models.MatchValue(value="N")),
            ],
            must_not=[models.FieldCondition(key="event_id", match=models.MatchValue(value=args.event_id))]
            if args.event_id is not None
            else [],
        )
        hits = client.query_points(
            collection_name=collection,
            query=_encode(model, [query])[0],
            query_filter=query_filter,
            limit=len(documents),  # Bounded demo corpus: retrieve all to avoid chunk duplicates consuming top-k.
            with_payload=True,
        ).points
        seen: set[int] = set()
        for hit in hits:
            payload = hit.payload or {}
            event_id = int(payload["event_id"])
            if event_id in seen:
                continue
            seen.add(event_id)
            LOGGER.info(
                "%s",
                json.dumps(
                    {
                        "event_id": event_id,
                        "cosine_similarity": round(hit.score, 4),
                        "title": payload["title"],
                        "warnings": payload.get("warnings", []),
                    },
                    ensure_ascii=False,
                ),
            )
            if len(seen) >= args.top_k:
                break
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
