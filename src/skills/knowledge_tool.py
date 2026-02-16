"""
Agent Optimus — Knowledge Base Tool (Phase 17).
Allows agents to search the long-term memory / knowledge base.
"""

from src.core.knowledge_base import knowledge_base

async def search_knowledge_base(query: str, limit: int = 5) -> str:
    """
    Search the Agent Optimus Knowledge Base for information.
    Use this tool when you need to answer questions based on uploaded documents, 
    technical manuals, or company policies.
    
    Args:
        query: The search question or topic.
        limit: Max number of results (default 5).
    
    Returns:
        A string containing relevant excerpts found in the knowledge base.
    """
    try:
        results = await knowledge_base.search(query, limit=limit)
        
        if not results:
            return "No relevant information found in the Knowledge Base."
            
        output = [f"Found {len(results)} relevant chunks:\n"]
        
        for i, res in enumerate(results, 1):
            source = res.get('metadata', {}).get('filename', 'Unknown Source')
            score = res.get('score', 0)
            content = res.get('content', '').replace('\n', ' ')
            
            output.append(f"--- Result {i} (Source: {source}, Relevance: {score:.2f}) ---")
            output.append(content)
            output.append("")
            
        return "\n".join(output)

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"
