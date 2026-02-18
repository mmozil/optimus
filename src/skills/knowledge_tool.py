"""
Agent Optimus — Knowledge Base Tool (Phase 17 + FASE 0 #9).
Allows agents to search the long-term memory / knowledge base using RAGPipeline.
"""

from src.memory.rag import rag_pipeline
from src.infra.supabase_client import get_async_session

async def search_knowledge_base(query: str, limit: int = 5) -> str:
    """
    Search the Agent Optimus Knowledge Base for information using RAGPipeline.
    Use this tool when you need to answer questions based on uploaded documents,
    technical manuals, or company policies.

    FASE 0 #9: Now uses rag_pipeline for semantic chunking + retrieval.

    Args:
        query: The search question or topic.
        limit: Max number of results (default 5).

    Returns:
        A string containing relevant excerpts found in the knowledge base.
    """
    try:
        # FASE 0 #9: Use RAGPipeline for retrieval with semantic chunking
        async with get_async_session() as db_session:
            # Update rag_pipeline config for this search
            original_max = rag_pipeline.max_results
            rag_pipeline.max_results = limit

            try:
                # Get RAG-augmented context (formatted for agent)
                context = await rag_pipeline.augment_prompt(
                    db_session=db_session,
                    query=query,
                    source_type="document",  # Only search documents
                )

                if not context:
                    return "No relevant information found in the Knowledge Base."

                return context

            finally:
                # Restore original config
                rag_pipeline.max_results = original_max

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"
