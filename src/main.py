"""Command-line interface for policy-rag-assistant.

Provides subcommands for policy document ingestion, single-shot question answering,
and an interactive chat session with source attribution and similarity scores.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path so both 'python src/main.py' and 'python -m src.main' work
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import validate_environment
from src.ingest import run_ingestion
from src.graph import run_policy_query
from src.vector_store import VectorStore


def print_sources(docs: List[Dict[str, Any]]) -> None:
    """Format and print retrieved document sources and similarity scores."""
    if not docs:
        return

    print("\n" + "—" * 60)
    print("SOURCES:")
    seen_sources = set()
    source_idx = 1

    for doc in docs:
        source_file = doc.get("source_file", "unknown")
        section = doc.get("section", "General")
        score = doc.get("score")
        key = (source_file, section)

        if key in seen_sources:
            continue
        seen_sources.add(key)

        score_str = f"similarity: {score:.4f}" if score is not None else "similarity: N/A"
        print(f"  [{source_idx}] {source_file} > {section} ({score_str})")
        source_idx += 1
    print("—" * 60)


def handle_ask(question: str, show_sources: bool) -> None:
    """Execute single-question query and display result."""
    print(f"\n[?] Question: {question}\n")

    vs = VectorStore()
    vs.load()

    state = run_policy_query(question=question, vector_store=vs)

    print("Answer:")
    print(state["answer"])

    if show_sources:
        print_sources(state.get("docs", []))

    if not state.get("grounded", True):
        print(f"\n[Audit Flag] Reason: {state.get('reason', 'Unverified')}")


def handle_chat(show_sources: bool) -> None:
    """Run interactive question-answering session."""
    print("=" * 65)
    print(" Policy RAG Assistant — Interactive Terminal")
    print(" Ask any question about company leave, security, or HR policies.")
    print(" Type 'exit', 'quit', or press Ctrl+C to return to shell.")
    print("=" * 65)

    vs = VectorStore()
    vs.load()

    while True:
        try:
            print()
            user_input = input("You > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nGoodbye!")
                break

            print("\nSearching policies & generating verified answer...")
            state = run_policy_query(question=user_input, vector_store=vs)

            print("\nAssistant:")
            print(state["answer"])

            if show_sources:
                print_sources(state.get("docs", []))

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession terminated. Goodbye!")
            break
        except Exception as exc:
            print(f"\n[Error] {exc}", file=sys.stderr)


def main() -> None:
    """Parse CLI arguments and dispatch commands."""
    validate_environment()

    parser = argparse.ArgumentParser(
        prog="policy-rag",
        description="Policy RAG Assistant: Retrieve and answer questions from company policy documents using FAISS and LangGraph.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: ingest
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Parse markdown policies in data/policies/, build FAISS vector index, and save to index/",
    )

    # Command: ask
    ask_parser = subparsers.add_parser(
        "ask",
        help="Ask a single question about company policies",
    )
    ask_parser.add_argument("question", type=str, help="The policy question to ask")
    ask_parser.add_argument(
        "--no-sources",
        action="store_true",
        default=False,
        help="Suppress output of source citations and similarity scores",
    )

    # Command: chat
    chat_parser = subparsers.add_parser(
        "chat",
        help="Start an interactive multi-turn policy Q&A session",
    )
    chat_parser.add_argument(
        "--no-sources",
        action="store_true",
        default=False,
        help="Suppress output of source citations and similarity scores",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "ingest":
            run_ingestion()
        elif args.command == "ask":
            handle_ask(question=args.question, show_sources=not args.no_sources)
        elif args.command == "chat":
            handle_chat(show_sources=not args.no_sources)
    except FileNotFoundError as fnf_err:
        print(f"\n[Configuration Error] {fnf_err}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as rt_err:
        print(str(rt_err), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n[Unexpected Error] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
