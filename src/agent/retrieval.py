"""
Knowledge Base Retrieval for Meridian Pay Support Agent.
Braintrust SDK Version: 0.39.0
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KB_DIR = BASE_DIR / "data" / "kb"


class KBRetriever:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.kb_dir = kb_dir
        self.chunks: List[Dict[str, Any]] = []
        self._load_and_chunk_docs()

    def _load_and_chunk_docs(self):
        self.chunks = []
        if not self.kb_dir.exists():
            return

        for path in sorted(self.kb_dir.rglob("*.md")):
            rel_path = path.relative_to(self.kb_dir).as_posix()
            content = path.read_text(encoding="utf-8")
            
            # Split into sections by H1/H2 headings
            sections = re.split(r'\n(?=#{1,3}\s)', content)
            for idx, sec in enumerate(sections):
                sec = sec.strip()
                if not sec:
                    continue
                first_line = sec.split("\n")[0].strip("# ")
                self.chunks.append({
                    "doc_path": rel_path,
                    "title": first_line,
                    "content": sec,
                    "words": set(re.findall(r'\w+', sec.lower()))
                })

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Simple BM25-like term frequency keyword matching over KB chunks.
        """
        query_words = set(re.findall(r'\w+', query.lower()))
        # remove common stopwords
        stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "is", "are", "was"}
        query_words = {w for w in query_words if w not in stopwords and len(w) > 1}

        if not query_words:
            return self.chunks[:top_k]

        scored = []
        for chunk in self.chunks:
            overlap = len(query_words & chunk["words"])
            # Bonus if query words appear in the title
            title_words = set(re.findall(r'\w+', chunk["title"].lower()))
            title_overlap = len(query_words & title_words)
            score = overlap * 1.0 + title_overlap * 2.0
            
            # Additional match for exact numbers or dollar values
            numbers_in_query = set(re.findall(r'\$?\d+', query))
            for num in numbers_in_query:
                if num in chunk["content"]:
                    score += 2.0
                    
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored[:top_k]]
        
        # Fallback to first chunks if no keyword overlap
        if not results:
            results = self.chunks[:top_k]
            
        return [
            {
                "doc_path": r["doc_path"],
                "title": r["title"],
                "content": r["content"]
            }
            for r in results
        ]


# Singleton instance
_retriever = None

def get_retriever() -> KBRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KBRetriever()
    return _retriever
