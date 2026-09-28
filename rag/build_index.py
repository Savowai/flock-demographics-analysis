"""Phase 6.2: chunk the documents, embed them locally, store in ChromaDB.

Chunking splits on paragraph boundaries and packs paragraphs up to a target
size, with overlap carried between chunks so a sentence spanning a boundary is
still retrievable. Splitting mid-sentence on a fixed character count would
produce chunks that retrieve badly and quote badly.

Embeddings use sentence-transformers all-MiniLM-L6-v2, which runs locally on
CPU - no API key, no data leaving the machine.

Run: .venv/bin/python rag/build_index.py [--rebuild]
Writes: rag/chroma/ (persistent vector store)
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

RAG = Path(__file__).resolve().parent
DOCS = RAG / "documents"
STORE = RAG / "chroma"
COLLECTION = "flock_documents"
EMBED_MODEL = "all-MiniLM-L6-v2"

TARGET_CHARS = 1400      # ~250 words: big enough to hold an argument
OVERLAP_CHARS = 250
HEADER_SEPARATOR = "-" * 70


def load_sources() -> dict[str, dict]:
    path = DOCS / "sources.csv"
    if not path.exists():
        print(f"missing {path}; run src/collect/rag_documents.py first")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return {row["file"]: row for row in csv.DictReader(fh)}


def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # A single oversized paragraph is split on its own.
        if len(para) > TARGET_CHARS:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(para), TARGET_CHARS - OVERLAP_CHARS):
                chunks.append(para[i : i + TARGET_CHARS])
            continue

        if len(current) + len(para) + 2 <= TARGET_CHARS:
            current = f"{current}\n\n{para}" if current else para
        else:
            chunks.append(current)
            tail = current[-OVERLAP_CHARS:] if len(current) > OVERLAP_CHARS else current
            current = f"{tail}\n\n{para}"

    if current:
        chunks.append(current)
    return [c for c in chunks if len(c.strip()) > 80]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true",
                        help="delete and rebuild the vector store")
    args = parser.parse_args()

    sources = load_sources()
    files = sorted(DOCS.glob("*.txt"))
    if not files:
        print("no documents found in rag/documents/")
        return 1

    if args.rebuild and STORE.exists():
        shutil.rmtree(STORE)
        print("removed existing store")

    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    client = chromadb.PersistentClient(path=str(STORE))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.create_collection(
        COLLECTION, embedding_function=embedder,
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0
    unlisted = []

    for path in files:
        raw = path.read_text(encoding="utf-8")
        body = raw.split(HEADER_SEPARATOR, 1)[-1].strip() if HEADER_SEPARATOR in raw else raw
        meta_row = sources.get(path.name)
        if meta_row is None:
            unlisted.append(path.name)
            meta_row = {"title": path.stem, "publisher": "unknown", "date": "",
                        "url": "", "bucket": "unlisted", "date_retrieved": ""}

        chunks = chunk_text(body)
        if not chunks:
            print(f"  WARNING: no chunks from {path.name}")
            continue

        collection.add(
            ids=[f"{path.stem}::{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[
                {
                    "file": path.name,
                    "title": meta_row["title"],
                    "publisher": meta_row["publisher"],
                    "date": meta_row["date"],
                    "url": meta_row["url"],
                    "bucket": meta_row["bucket"],
                    "chunk_index": i,
                    "n_chunks": len(chunks),
                }
                for i in range(len(chunks))
            ],
        )
        total_chunks += len(chunks)
        print(f"  {path.name:52s} {len(chunks):>4} chunks")

    print(f"\n{len(files)} documents -> {total_chunks:,} chunks in {STORE.name}/")
    print(f"embedding model: {EMBED_MODEL} (local, CPU)")
    if unlisted:
        print(f"\nNOTE: not listed in sources.csv (add provenance): {unlisted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
