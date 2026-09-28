"""Phase 6.3: answer questions using only the retrieved documents.

Two modes:

  extractive (default)  returns the passages themselves with citations. No API
                        key, no model writing prose, nothing invented - the
                        answer IS the source text.
  --generate            uses Claude to write an answer constrained to the
                        retrieved passages, with citations. Requires
                        ANTHROPIC_API_KEY (Phase 7).

Both refuse to answer when retrieval is weak. If the best match is below the
similarity floor, the honest response is "the documents do not cover this",
not a confident paragraph assembled from unrelated text.

Usage:
  .venv/bin/python rag/query.py "Can federal agencies search Washington Flock data?"
  .venv/bin/python rag/query.py --generate "What does SB 34 prohibit?"
  .venv/bin/python rag/query.py --samples
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

RAG = Path(__file__).resolve().parent
STORE = RAG / "chroma"
COLLECTION = "flock_documents"
EMBED_MODEL = "all-MiniLM-L6-v2"

TOP_K = 6
# Cosine distance; 0 is identical. Above this the match is too weak to trust.
MAX_DISTANCE = 0.85

SAMPLE_QUESTIONS = [
    "Can federal immigration agencies access Washington state Flock camera data?",
    "What does California SB 34 prohibit regarding sharing ALPR data?",
    "How long can Washington agencies retain license plate reader data?",
    "Where are agencies banned from placing license plate readers in Washington?",
    "Has any audit found misuse of a Flock camera system?",
]


def get_collection():
    if not STORE.exists():
        print("No vector store found. Run: .venv/bin/python rag/build_index.py")
        sys.exit(1)
    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    client = chromadb.PersistentClient(path=str(STORE))
    return client.get_collection(COLLECTION, embedding_function=embedder)


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    collection = get_collection()
    res = collection.query(query_texts=[question], n_results=k)
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append({"text": doc, "meta": meta, "distance": dist})
    return hits


def citation(meta: dict) -> str:
    bits = [meta["title"]]
    if meta.get("publisher"):
        bits.append(meta["publisher"])
    if meta.get("date"):
        bits.append(str(meta["date"]))
    return f"{' - '.join(bits)} [{meta['file']}]"


def answer_extractive(question: str, hits: list[dict]) -> str:
    usable = [h for h in hits if h["distance"] <= MAX_DISTANCE]
    if not usable:
        return (
            "The documents in this corpus do not appear to cover that question.\n"
            f"(closest match distance {hits[0]['distance']:.2f}, "
            f"floor is {MAX_DISTANCE})\n"
            "Try rephrasing, or add a relevant document to rag/documents/ "
            "and re-run rag/build_index.py."
        )

    out = [f"Found {len(usable)} relevant passage(s).\n"]
    for i, hit in enumerate(usable, 1):
        text = textwrap.fill(hit["text"].replace("\n", " ").strip(), width=88)
        out.append(f"--- [{i}] {citation(hit['meta'])}")
        out.append(f"    relevance: {1 - hit['distance']:.2f}")
        if hit["meta"].get("url"):
            out.append(f"    {hit['meta']['url']}")
        out.append(textwrap.indent(text, "    "))
        out.append("")
    out.append(
        "These are the source passages verbatim. Every claim above is quoted "
        "from the cited file; nothing is summarised or inferred."
    )
    return "\n".join(out)


def answer_generative(question: str, hits: list[dict]) -> str:
    load_dotenv(RAG.parent / ".env")
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return (
            "ANTHROPIC_API_KEY is not set in .env, so --generate is unavailable.\n"
            "Run without --generate for extractive answers."
        )

    usable = [h for h in hits if h["distance"] <= MAX_DISTANCE]
    if not usable:
        return "The documents in this corpus do not cover that question."

    import anthropic

    context = "\n\n".join(
        f"[{i}] {citation(h['meta'])}\n{h['text']}" for i, h in enumerate(usable, 1)
    )
    prompt = (
        "Answer the question using ONLY the numbered sources below. Cite each "
        "claim with its bracket number and file name. If the sources do not "
        "contain the answer, say exactly that - do not use outside knowledge "
        "and do not guess.\n\n"
        f"SOURCES:\n{context}\n\nQUESTION: {question}"
    )

    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )
    body = msg.content[0].text
    refs = "\n".join(f"  [{i}] {citation(h['meta'])}" for i, h in enumerate(usable, 1))
    return f"{body}\n\nSources used:\n{refs}"


def run(question: str, generate: bool) -> None:
    print(f"\n{'=' * 90}\nQ: {question}\n{'=' * 90}")
    hits = retrieve(question)
    answer = answer_generative(question, hits) if generate else answer_extractive(
        question, hits
    )
    print(answer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="*", help="question to ask")
    parser.add_argument("--generate", action="store_true",
                        help="write a prose answer with Claude (needs API key)")
    parser.add_argument("--samples", action="store_true",
                        help="run the five sample questions")
    args = parser.parse_args()

    if args.samples:
        for q in SAMPLE_QUESTIONS:
            run(q, args.generate)
        return 0

    if not args.question:
        parser.print_help()
        return 1

    run(" ".join(args.question), args.generate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
