"""
Bulk-loads the SEO knowledge base (extracted from knowledge.zip) into the local
Qdrant instance, matching the exact payload/vector schema mcp-server-qdrant
already uses on the reference machine:
  payload: {"document": "<tagged text>", "metadata": null}
  vector name: "fast-all-minilm-l6-v2" (384-dim, cosine)

Bypasses the MCP tool-call loop entirely (thousands of chunks would be far too
slow/expensive to store one qdrant-store call at a time) by talking straight to
Qdrant's REST API with fastembed for embeddings.

Usage:
    python bulk_load_qdrant.py <knowledge_dir>

Requires: pip install fastembed requests
"""
import json
import sys
import uuid
from pathlib import Path

import requests
from fastembed import TextEmbedding

QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "claude_code_memory"
VECTOR_NAME = "fast-all-minilm-l6-v2"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64


def iter_ingestion_ndjson(path):
    """*.ndjson files with an "information" field are already ingestion-ready."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = row.get("information")
            if text:
                yield text


def iter_raw_chunk_json(path):
    """*.json array files with text/source/url fields (e.g. googledocs-chunks/*.json)."""
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        return
    for row in rows:
        text = row.get("text")
        if not text:
            continue
        source = row.get("source", "")
        url = row.get("url", "")
        tag = "[GOOGLE-DOCS]" if "developers.google.com" in url else "[SEO-KNOWLEDGE]"
        doc = f"{tag} {source} — {text}"
        if url:
            doc += f"\n\nSource URL: {url}"
        yield doc


def collect_documents(knowledge_dir):
    knowledge_dir = Path(knowledge_dir)
    seen_ingestion_stems = set()
    docs = []

    for p in sorted(knowledge_dir.rglob("*ingestion*.ndjson")):
        for doc in iter_ingestion_ndjson(p):
            docs.append(doc)
        seen_ingestion_stems.add(p.stem.replace("-ingestion", ""))

    for p in sorted(knowledge_dir.rglob("*.json")):
        if "chunks" not in p.parts and "chunks" not in p.stem:
            continue
        if p.stem in seen_ingestion_stems:
            continue  # already covered by a ready-made ingestion ndjson
        for doc in iter_raw_chunk_json(p):
            docs.append(doc)

    return docs


def main():
    if len(sys.argv) != 2:
        print("Usage: python bulk_load_qdrant.py <knowledge_dir>")
        sys.exit(1)

    docs = collect_documents(sys.argv[1])
    if not docs:
        print("No ingestible documents found under", sys.argv[1])
        sys.exit(1)
    print(f"Found {len(docs)} documents to embed and upsert.")

    model = TextEmbedding(model_name=MODEL)

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        vectors = list(model.embed(batch))
        points = [
            {
                "id": str(uuid.uuid4()),
                "vector": {VECTOR_NAME: vec.tolist()},
                "payload": {"document": doc, "metadata": None},
            }
            for doc, vec in zip(batch, vectors)
        ]
        resp = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            json={"points": points},
            timeout=30,
        )
        resp.raise_for_status()
        print(f"Upserted {i + len(batch)}/{len(docs)}")

    print("Done.")


if __name__ == "__main__":
    main()
