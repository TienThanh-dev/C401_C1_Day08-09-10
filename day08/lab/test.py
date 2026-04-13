import json
from datetime import datetime
import os
from rag_answer import rag_answer

with open(r"C:\D\AI_in_action\Day_8\Lecture-Day-08-09-10\day08\lab\data\grading_questions.json",encoding="utf-8") as f:
    questions = json.load(f)

log = []
for q in questions:
    result = rag_answer(q["question"], retrieval_mode="hybrid", verbose=False)
    log.append({
        "id": q["id"],
        "question": q["question"],
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks_retrieved": len(result["chunks_used"]),
        "retrieval_mode": result["config"]["retrieval_mode"],
        "timestamp": datetime.now().isoformat(),
    })
os.makedirs("logs", exist_ok=True)
with open("logs/grading_run.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)