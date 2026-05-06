import json
import os
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np

from app.config import FAISS_INDEX_DIR


def _index_path(file_id: str) -> str:
    return os.path.join(FAISS_INDEX_DIR, f"{file_id}.index")


def _metadata_path(file_id: str) -> str:
    return os.path.join(FAISS_INDEX_DIR, f"{file_id}.json")


def build_faiss_index(
    file_id: str,
    segments: List[Dict[str, Any]],
    *,
    dimension: int = 768,
    embeddings: np.ndarray | None = None,
) -> Tuple[str, str]:
    """Build a FAISS index with deterministic vector_id -> segment coupling.

    Vector ids (0..N-1) correspond exactly to the provided `segments` ordering.

    Args:
      file_id: used for output paths
      segments: list of normalized transcript segments in the desired ordering
      dimension: embedding dimensionality
      embeddings: optional precomputed embeddings array shaped (N, dimension)

    Returns:
      (index_path, metadata_path)
    """

    if not segments:
        # Still create empty index/metadata for deterministic behavior.
        index = faiss.IndexFlatL2(dimension)
        os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
        faiss.write_index(index, _index_path(file_id))
        metadata = {"dimension": dimension, "vectors": {}}
        with open(_metadata_path(file_id), "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        return _index_path(file_id), _metadata_path(file_id)

    if embeddings is not None:
        embeddings_arr = np.asarray(embeddings).astype("float32")
        if embeddings_arr.ndim != 2:
            raise ValueError("embeddings must be a 2D array of shape (N, dimension)")
        if embeddings_arr.shape[0] != len(segments):
            raise ValueError("embeddings row count must match number of segments")
        if embeddings_arr.shape[1] != dimension:
            raise ValueError("embeddings column count must equal dimension")
    else:
        raise ValueError(
            "embeddings must be provided to build_faiss_index(file_id, segments)"
        )

    # Ensure deterministic ordering: vector_id == index in `segments`
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_arr)

    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    index_path = _index_path(file_id)
    faiss.write_index(index, index_path)

    vectors: Dict[str, Dict[str, Any]] = {}
    for vector_id, seg in enumerate(segments):
        # vector_id corresponds to seg ordering
        vectors[str(vector_id)] = {
            "segment_id": seg.get("segment_id"),
            "start": seg.get("start"),
            "end": seg.get("end"),
            "text": seg.get("text"),
        }

    metadata = {
        "dimension": dimension,
        "count": len(segments),
        "vectors": vectors,
    }

    metadata_path = _metadata_path(file_id)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    return index_path, metadata_path


def load_faiss_index(file_id: str) -> Tuple[faiss.Index, Dict[str, Any]]:
    """Load FAISS index + sidecar metadata."""

    index_path = _index_path(file_id)
    metadata_path = _metadata_path(file_id)

    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"FAISS metadata not found: {metadata_path}")

    index = faiss.read_index(index_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return index, metadata


def search_faiss(
    file_id: str,
    query_embedding: np.ndarray,
    *,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """Search FAISS index and return sorted metadata matches.

    Returns list of:
      {"segment_id", "start", "end", "text", "vector_id", "score"}

    Notes:
    - For IndexFlatL2, FAISS returns smaller distance = better match.
    - We sort by ascending distance to get best score first.
    """

    index, metadata = load_faiss_index(file_id)

    q = np.asarray(query_embedding).astype("float32")
    if q.ndim == 1:
        q = q.reshape(1, -1)

    # Determine effective k
    count = int(metadata.get("count", 0))
    if count == 0:
        return []

    k = int(min(max(top_k, 1), count))

    distances, indices = index.search(q, k)

    results: List[Dict[str, Any]] = []
    vectors = metadata.get("vectors", {})

    for dist, idx in zip(distances[0], indices[0]):
        vector_id = int(idx)
        seg_meta = vectors.get(str(vector_id))
        if not seg_meta:
            continue
        results.append(
            {
                "vector_id": vector_id,
                "segment_id": seg_meta.get("segment_id"),
                "start": seg_meta.get("start"),
                "end": seg_meta.get("end"),
                "text": seg_meta.get("text"),
                "score": float(dist),  # L2 distance (lower is better)
            }
        )

    # Return matches sorted by best score (ascending distance)
    results.sort(key=lambda r: r["score"])
    return results

