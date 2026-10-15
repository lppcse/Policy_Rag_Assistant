"""LangGraph orchestration workflow for policy-rag-assistant.

Implements a cyclic graph coordinating document retrieval, cited generation,
hallucination / groundedness validation, iterative query rewriting on failure,
and response finalization.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from src.config import (
    CHAT_MODEL,
    MAX_RETRIES,
    TOP_K,
    get_openai_api_key,
)
from src.vector_store import VectorStore


class RagState(TypedDict):
    """Execution state tracking for the policy RAG assistant workflow."""
    question: str
    search_query: str
    docs: List[Dict[str, Any]]
    answer: str
    grounded: bool
    reason: str
    retries: int


def format_context_passages(docs: List[Dict[str, Any]]) -> str:
    """Format retrieved document chunks into numbered context passages."""
    if not docs:
        return "No relevant policy documents were found."

    passages = []
    for idx, doc in enumerate(docs, start=1):
        source = doc.get("source_file", "unknown")
        section = doc.get("section", "General")
        text = doc.get("text", "")
        # Remove any internal formatting headers if already present in text
        passages.append(f"Passage [{idx}] (Source: {source} > {section}):\n{text}")

    return "\n\n".join(passages)


def create_policy_graph(
    vector_store: Optional[VectorStore] = None,
    client: Optional[OpenAI] = None,
) -> Any:
    """Construct and compile the LangGraph workflow.

    Args:
        vector_store: Instantiated and loaded VectorStore instance.
        client: Optional OpenAI client instance.

    Returns:
        Compiled LangGraph instance.
    """
    # Lazy initialization if not provided
    vs = vector_store or VectorStore()
    if vs.index is None:
        vs.load()

    ai_client = client or OpenAI(api_key=get_openai_api_key())

    # -------------------------------------------------------------------------
    # Node 1: Retrieve
    # -------------------------------------------------------------------------
    def retrieve_node(state: RagState) -> Dict[str, Any]:
        """Query vector store using current search query and return top-K docs."""
        query = state.get("search_query") or state["question"]
        retrieved_docs = vs.search(query=query, k=TOP_K, client=ai_client)
        return {"docs": retrieved_docs}

    # -------------------------------------------------------------------------
    # Node 2: Generate
    # -------------------------------------------------------------------------
    def generate_node(state: RagState) -> Dict[str, Any]:
        """Generate cited answer strictly constrained by retrieved passages."""
        passages_text = format_context_passages(state.get("docs", []))
        question = state["question"]

        system_prompt = (
            "You are an authoritative company policy assistant. Answer the user's question "
            "using ONLY the numbered context passages provided below.\n\n"
            "STRICT RULES:\n"
            "1. Answer strictly and exclusively using facts from the numbered passages.\n"
            "2. Cite the supporting passage number inline wherever you state a fact, e.g. [1] or [2].\n"
            "3. If the context passages do not contain sufficient information to answer the question, "
            "you MUST reply: 'I could not find the answer in the provided company policy documentation.' "
            "Do not attempt to answer from external knowledge or make assumptions."
        )

        user_content = (
            f"Context Passages:\n{passages_text}\n\n"
            f"User Question: {question}\n\n"
            "Your Answer (with inline citations like [1]):"
        )

        response = ai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
        )

        answer_text = response.choices[0].message.content or ""
        return {"answer": answer_text.strip()}

    # -------------------------------------------------------------------------
    # Node 3: Validate
    # -------------------------------------------------------------------------
    def validate_node(state: RagState) -> Dict[str, Any]:
        """Evaluate whether the generated answer is completely grounded in context passages."""
        answer = state.get("answer", "")
        passages_text = format_context_passages(state.get("docs", []))
        question = state["question"]

        # If model explicitly stated it could not find the answer, treat as grounded response
        if "could not find the answer" in answer.lower():
            return {
                "grounded": True,
                "reason": "Model correctly reported that the policy documents do not contain the answer.",
            }

        validation_prompt = (
            "You are an impartial compliance auditor reviewing an AI-generated answer for policy adherence.\n"
            "Your task: Check whether EVERY claim in the candidate answer is directly supported by the context passages.\n\n"
            "Output your judgment strictly as a JSON object with this schema:\n"
            "{\n"
            '  "grounded": true | false,\n'
            '  "reason": "concise explanation of why the answer is or is not fully supported by the text"\n'
            "}"
        )

        review_payload = (
            f"Context Passages:\n{passages_text}\n\n"
            f"Original Question:\n{question}\n\n"
            f"Candidate Answer:\n{answer}"
        )

        try:
            response = ai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": validation_prompt},
                    {"role": "user", "content": review_payload},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            is_grounded = bool(data.get("grounded", False))
            reason = str(data.get("reason", "Validation check completed."))
        except Exception as exc:
            # Fallback if parsing fails: assume ungrounded unless proven
            is_grounded = False
            reason = f"Validation parsing exception: {exc}"

        return {"grounded": is_grounded, "reason": reason}

    # -------------------------------------------------------------------------
    # Node 4: Rewrite Query
    # -------------------------------------------------------------------------
    def rewrite_query_node(state: RagState) -> Dict[str, Any]:
        """Formulate a refined search query to retrieve better supporting documents."""
        original_question = state["question"]
        current_query = state.get("search_query") or original_question
        reason = state.get("reason", "Retrieved passages were insufficient.")
        retries = state.get("retries", 0) + 1

        rewrite_prompt = (
            "You are an expert search retrieval optimizer. The previous policy document search failed "
            "to substantiate an answer to the employee's question.\n"
            "Generate an improved, targeted search query to find the relevant corporate policy text.\n"
            "Respond ONLY with the rewritten search query keywords, nothing else."
        )

        user_content = (
            f"Original Employee Question: {original_question}\n"
            f"Previous Search Query: {current_query}\n"
            f"Why it was insufficient: {reason}\n\n"
            "Rewritten Search Query:"
        )

        response = ai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": rewrite_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )

        new_query = (response.choices[0].message.content or "").strip()
        if not new_query:
            new_query = original_question

        return {
            "search_query": new_query,
            "retries": retries,
        }

    # -------------------------------------------------------------------------
    # Node 5: Finalize
    # -------------------------------------------------------------------------
    def finalize_node(state: RagState) -> Dict[str, Any]:
        """Append disclaimer if answer remains ungrounded after maximum retries."""
        answer = state.get("answer", "")
        grounded = state.get("grounded", False)

        if not grounded and "could not find the answer" not in answer.lower():
            disclaimer = "\n\n[Note: This response could not be fully verified against company policy documents. Please confirm with HR or People Operations.]"
            return {"answer": answer + disclaimer}

        return {"answer": answer}

    # -------------------------------------------------------------------------
    # Conditional Edge Routing
    # -------------------------------------------------------------------------
    def route_after_validate(state: RagState) -> str:
        """Route to rewrite_query if ungrounded and retry budget remains, else finalize."""
        grounded = state.get("grounded", False)
        retries = state.get("retries", 0)

        if not grounded and retries < MAX_RETRIES:
            return "rewrite_query"
        return "finalize"

    # Build Graph
    workflow = StateGraph(RagState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("finalize", finalize_node)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "rewrite_query": "rewrite_query",
            "finalize": "finalize",
        },
    )
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("finalize", END)

    return workflow.compile()


def run_policy_query(
    question: str,
    vector_store: Optional[VectorStore] = None,
    client: Optional[OpenAI] = None,
) -> RagState:
    """Helper function to execute the LangGraph workflow for a single question.

    Args:
        question: Employee question.
        vector_store: Optional pre-loaded VectorStore.
        client: Optional OpenAI client.

    Returns:
        Final RagState dict containing question, answer, docs, grounded, etc.
    """
    app = create_policy_graph(vector_store=vector_store, client=client)
    initial_state: RagState = {
        "question": question,
        "search_query": question,
        "docs": [],
        "answer": "",
        "grounded": False,
        "reason": "",
        "retries": 0,
    }
    final_state = app.invoke(initial_state)
    return final_state
