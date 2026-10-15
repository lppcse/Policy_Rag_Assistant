"""Configuration management for policy-rag-assistant.

Loads environment variables from .env and exposes model names,
retrieval hyperparameters, text chunking bounds, and directory paths.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Resolve project base directory (parent of src/)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
ENV_PATH: Path = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Directory paths
DATA_DIR: Path = BASE_DIR / "data"
POLICIES_DIR: Path = DATA_DIR / "policies"
INDEX_DIR: Path = BASE_DIR / "index"
INDEX_FILE: Path = INDEX_DIR / "faiss.index"
METADATA_FILE: Path = INDEX_DIR / "metadata.json"

# Models
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")

# Retrieval and Workflow hyperparameters
TOP_K: int = int(os.getenv("TOP_K", "4"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))

# Text Chunking parameters
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))


def get_openai_api_key() -> str:
    """Retrieve and validate the OpenAI API key.

    Raises:
        RuntimeError: If OPENAI_API_KEY is unset, empty, or has placeholder value.
    """
    key = os.getenv("OPENAI_API_KEY", "").strip()
    placeholder_indicators = ("sk-your-key-here", "your-openai-api-key", "sk-...", "")

    if not key or any(p in key for p in placeholder_indicators if p):
        msg = (
            "\n" + "=" * 70 + "\n"
            "CONFIGURATION ERROR: Missing or Invalid OPENAI_API_KEY\n"
            "=" * 70 + "\n"
            "A valid OpenAI API key is required to run policy-rag-assistant.\n"
            "Please copy .env.example to .env and configure your key:\n\n"
            "    cp .env.example .env\n"
            "    # Edit .env and set: OPENAI_API_KEY=sk-...\n\n"
            "Or set the environment variable directly:\n"
            "    export OPENAI_API_KEY=sk-...\n"
            "=" * 70 + "\n"
        )
        raise RuntimeError(msg)
    return key


def validate_environment() -> None:
    """Check configuration and ensure key directories exist."""
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
