"""Document ingestion pipeline for policy-rag-assistant.

Reads Markdown and text policy documents, splits them on headings into
overlapping chunks, associates each chunk with its source section title,
and builds and persists the FAISS vector index.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from openai import OpenAI

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    INDEX_FILE,
    METADATA_FILE,
    POLICIES_DIR,
    get_openai_api_key,
    validate_environment,
)
from src.vector_store import VectorStore


def parse_markdown_sections(content: str, default_title: str) -> List[Dict[str, str]]:
    """Split markdown text into distinct sections based on markdown headings.

    Args:
        content: The raw markdown or text document content.
        default_title: Fallback section title if no heading is found.

    Returns:
        List of dicts with 'section' and 'text'.
    """
    lines = content.splitlines()
    sections: List[Dict[str, str]] = []

    current_section = default_title
    current_lines: List[str] = []

    # Regex matching markdown headings: #, ##, ###, etc.
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            # Save accumulated content from previous section if non-empty
            section_body = "\n".join(current_lines).strip()
            if section_body:
                sections.append({
                    "section": current_section,
                    "text": section_body,
                })
            current_section = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Append the final section
    remaining_body = "\n".join(current_lines).strip()
    if remaining_body:
        sections.append({
            "section": current_section,
            "text": remaining_body,
        })

    return sections


def chunk_section_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Split section text into overlapping character chunks with sentence-aware boundaries.

    Args:
        text: Text of the section to chunk.
        chunk_size: Maximum character count per chunk.
        chunk_overlap: Overlapping character count between consecutive chunks.

    Returns:
        List of chunk strings.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    stride = max(chunk_size - chunk_overlap, 100)

    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk_slice = cleaned[start:end]

        # If not at the very end of the text, look for clean paragraph or sentence breaks
        if end < len(cleaned):
            break_point = max(
                chunk_slice.rfind("\n\n"),
                chunk_slice.rfind(". "),
                chunk_slice.rfind(".\n"),
            )
            # Only snap to break point if it's within the upper half of the chunk
            if break_point != -1 and break_point >= (chunk_size // 2):
                end = start + break_point + 1
                chunk_slice = cleaned[start:end].strip()

        if chunk_slice:
            chunks.append(chunk_slice)

        if end >= len(cleaned):
            break

        start += stride

    return chunks


def process_policy_documents(
    policies_dir: Path = POLICIES_DIR,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """Scan directory for .md/.txt files and produce structured, section-aware chunks.

    Args:
        policies_dir: Directory containing policy documents.
        chunk_size: Character length limit for chunks.
        chunk_overlap: Character overlap between contiguous chunks.

    Returns:
        List of chunk dictionaries with 'text', 'source_file', 'section', and 'chunk_id'.
    """
    if not policies_dir.exists():
        raise FileNotFoundError(f"Policies directory does not exist: {policies_dir}")

    policy_files = sorted(list(policies_dir.glob("*.md")) + list(policies_dir.glob("*.txt")))
    if not policy_files:
        raise FileNotFoundError(f"No .md or .txt policy files found in {policies_dir}")

    all_chunks: List[Dict[str, Any]] = []

    for file_path in policy_files:
        content = file_path.read_text(encoding="utf-8")
        default_title = file_path.stem.replace("_", " ").title()
        sections = parse_markdown_sections(content, default_title=default_title)

        chunk_counter = 0
        for sec in sections:
            section_title = sec["section"]
            section_body = sec["text"]

            raw_chunks = chunk_section_text(
                section_body,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            for c in raw_chunks:
                chunk_counter += 1
                # Format chunk text with contextual header to maximize embedding and retrieval accuracy
                contextual_text = f"[{file_path.name} > {section_title}]\n{c}"
                all_chunks.append({
                    "chunk_id": f"{file_path.name}#{section_title}#{chunk_counter}",
                    "source_file": file_path.name,
                    "section": section_title,
                    "text": contextual_text,
                    "raw_body": c,
                })

    return all_chunks


def run_ingestion(
    policies_dir: Path = POLICIES_DIR,
    index_file: Path = INDEX_FILE,
    metadata_file: Path = METADATA_FILE,
    client: Optional[OpenAI] = None,
) -> int:
    """Execute complete ingestion pipeline: parse, chunk, embed, and persist.

    Args:
        policies_dir: Path containing policy documents.
        index_file: Target FAISS index file path.
        metadata_file: Target metadata JSON file path.
        client: Optional OpenAI client.

    Returns:
        Total number of policy chunks indexed.
    """
    validate_environment()

    # Pre-flight check for OpenAI API key
    if client is None:
        client = OpenAI(api_key=get_openai_api_key())

    print(f"[*] Scanning policy documents in: {policies_dir.resolve()}")
    chunks = process_policy_documents(policies_dir)
    print(f"[*] Generated {len(chunks)} contextual chunks across policy files.")

    print("[*] Generating embeddings and building FAISS IndexFlatIP index...")
    store = VectorStore()
    store.build(chunks, client=client)

    print(f"[*] Saving vector index to: {index_file.resolve()}")
    print(f"[*] Saving chunk metadata to: {metadata_file.resolve()}")
    store.save(index_path=index_file, metadata_path=metadata_file)

    print(f"[✓] Ingestion completed successfully! {len(chunks)} chunks indexed.")
    return len(chunks)


if __name__ == "__main__":
    run_ingestion()
