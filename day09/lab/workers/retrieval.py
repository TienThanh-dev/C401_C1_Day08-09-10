"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_log: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import sys
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix encoding issue for Vietnamese characters on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except AttributeError:
        pass

# ─────────────────────────────────────────────
# Absolute paths — luôn resolve từ project root (lab/)
# Hoạt động đúng dù chạy từ bất kỳ thư mục nào
# ─────────────────────────────────────────────

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # workers/ → lab/
_CHROMA_DB_PATH = os.path.join(_PROJECT_ROOT, "chroma_db")
_DATA_DOCS_PATH = os.path.join(_PROJECT_ROOT, "data", "docs")

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    # Option A: OpenAI (text-embedding-3-small) - Ưu tiên hàng đầu nếu có API Key
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key and api_key.startswith("sk-"):
            client = OpenAI(api_key=api_key)
            def embed(text: str) -> list:
                resp = client.embeddings.create(input=text, model="text-embedding-3-small")
                return resp.data[0].embedding
            return embed
    except ImportError:
        pass

    # Option B: Sentence Transformers (offline fallback)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random
    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]
    print("⚠️  WARNING: Using random embeddings (test only). Install sentence-transformers.")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection. 
    Tối ưu hoá Self-healing: 
    1. Kiểm tra nếu trống -> Auto Index.
    2. Kiểm tra nếu sai Dimension (do đổi model Embedding) -> Xoá và Re-index.
    """
    import chromadb
    client = chromadb.PersistentClient(path=_CHROMA_DB_PATH)
    collection_name = "day09_docs"
    embed_fn = _get_embedding_fn()
    
    should_reindex = False
    try:
        collection = client.get_collection(collection_name)
        if collection.count() == 0:
            should_reindex = True
        else:
            # Test query để kiểm tra Dimension Mismatch
            test_embed = embed_fn("test")
            collection.query(query_embeddings=[test_embed], n_results=1)
    except Exception as e:
        # Nếu lỗi (Dimension mismatch hoặc Collection not found), đánh dấu cần reindex
        print(f"⚠️  Phát hiện vấn đề với Collection (Lỗi: {e}). Đang chuẩn bị Self-healing...")
        should_reindex = True
        try: client.delete_collection(collection_name)
        except: pass

    if should_reindex:
        collection = client.create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"🚀 Đang tối ưu hoá Self-healing: Tự động Indexing dữ liệu từ {_DATA_DOCS_PATH}...")

        if os.path.exists(_DATA_DOCS_PATH):
            for fname in os.listdir(_DATA_DOCS_PATH):
                if fname.endswith(".txt"):
                    with open(os.path.join(_DATA_DOCS_PATH, fname), "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Tối ưu hoá Chunking: Chia nhỏ file theo các đề mục '==='
                    import re
                    chunks = re.split(r'\n(?=== )', content)
                    
                    for i, chunk in enumerate(chunks):
                        if not chunk.strip(): continue
                        chunk_id = f"{fname}_chunk_{i}"
                        print(f"   Indexing: {chunk_id}...")
                        collection.add(
                            documents=[chunk],
                            ids=[chunk_id],
                            metadatas=[{"source": fname, "chunk": i}],
                            embeddings=[embed_fn(chunk)]
                        )
            print("✅ Tối ưu hoá Self-healing hoàn tất. Dữ liệu đã sẵn sàng.")
        else:
            print(f"❌ Không tìm thấy thư mục {_DATA_DOCS_PATH}.")

    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    TODO Sprint 2: Implement phần này.
    - Dùng _get_embedding_fn() để embed query
    - Query collection với n_results=top_k
    - Format result thành list of dict

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    embed = _get_embedding_fn()
    query_embedding = embed(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for i, (doc, dist, meta) in enumerate(zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        )):
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4),  # cosine similarity
                "metadata": meta,
            })
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)

        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n| Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
