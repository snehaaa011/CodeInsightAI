"""
CodeInsight AI - Code Chunking
NEW (CodeInsight AI): converts parsed CodeEntity objects into embedding-ready
chunks. Entity-aware chunking (one chunk per class/function/method) is used
whenever an entity's source is small enough; large entities are additionally
split into overlapping line-window sub-chunks so long files/methods remain
searchable (a simplified, documented alternative to CodeRAG's approach,
since our chunks feed a vector store rather than only a graph).
"""
from dataclasses import dataclass
from typing import List
from ..config import settings
from .code_parser import CodeEntity


@dataclass
class Chunk:
    id: str
    text: str
    file_path: str
    entity_id: str
    entity_name: str
    entity_type: str
    language: str
    start_line: int
    end_line: int


def _line_window_split(text: str, max_lines: int, overlap: int) -> List[str]:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return [text]
    chunks = []
    step = max(1, max_lines - overlap)
    for i in range(0, len(lines), step):
        window = lines[i:i + max_lines]
        if window:
            chunks.append("\n".join(window))
        if i + max_lines >= len(lines):
            break
    return chunks


def build_chunks(entities: List[CodeEntity]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for ent in entities:
        if ent.type == "File":
            continue  # file-level entity has no direct source body; skip as a chunk
        header = f"[{ent.language}] {ent.type} `{ent.name}` in {ent.file_path} (lines {ent.start_line}-{ent.end_line})\n"
        if ent.signature:
            header += f"Signature: {ent.signature}\n"
        body = ent.source or ent.signature or ent.name
        sub_texts = _line_window_split(body, settings.chunk_max_lines, settings.chunk_overlap_lines)
        for idx, sub in enumerate(sub_texts):
            chunks.append(Chunk(
                id=f"{ent.id}-{idx}",
                text=header + "\n" + sub,
                file_path=ent.file_path,
                entity_id=ent.id,
                entity_name=ent.name,
                entity_type=ent.type,
                language=ent.language,
                start_line=ent.start_line,
                end_line=ent.end_line,
            ))
    return chunks
