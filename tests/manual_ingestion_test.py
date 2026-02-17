"""
Manual test for Document Ingestion (PDF).
Downloads a dummy PDF and ingests it into KnowledgeBase.
"""
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Add local libs (priority)
libs_path = os.path.join(os.getcwd(), "libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

# Mocking modules BEFORE import
import sys
from unittest.mock import MagicMock, AsyncMock

# Mock src.infra.supabase_client
mock_supabase = MagicMock()
mock_session = AsyncMock()

# Configure the result object returned by await session.execute(...)
mock_result = MagicMock()
mock_result.scalar.return_value = "mock_file_id_123"

# key point: AsyncMock return_value is what is returned after await
mock_session.execute.return_value = mock_result
mock_session.__aenter__.return_value = mock_session
mock_supabase.get_async_session.return_value = mock_session

# Inject into sys.modules
sys.modules["src.infra.supabase_client"] = mock_supabase

# Mock model_router to avoid API calls
mock_router_module = MagicMock()
mock_router_instance = AsyncMock()
mock_router_instance.embed_text.return_value = [0.1] * 768  # Fake embedding
mock_router_module.model_router = mock_router_instance
sys.modules["src.infra.model_router"] = mock_router_module

# Now import
from src.core.knowledge_base import KnowledgeBase
from src.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pdf_ingestion():
    print("--- Starting PDF Ingestion Test (Mocked DB) ---")
    
    import httpx
    
    # 1. Download Dummy PDF
    url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    print(f"Downloading PDF from {url}...")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            print(f"❌ Failed to download PDF: {resp.status_code}")
            return
        pdf_bytes = resp.content
        print(f"Downloaded {len(pdf_bytes)} bytes.")

    # 2. Ingest
    kb = KnowledgeBase()
    
    try:
        # We need a valid user_id (UUID)
        import uuid
        user_id = uuid.uuid4()
        
        print("Ingesting document...")
        file_id = await kb.add_document(
            filename="dummy.pdf",
            content=pdf_bytes,
            mime_type="application/pdf",
            user_id=user_id
        )
        
        print(f"✅ Ingestion Successful! File ID: {file_id}")
        
    except RuntimeError as e:
        if "pypdf not installed" in str(e):
             print(f"❌ Failed: pypdf not installed. Check libs/ folder.")
        else:
             print(f"❌ Runtime Error: {e}")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not settings.GOOGLE_API_KEY:
        print("⚠️ GOOGLE_API_KEY not set. Embedding might fail.")
    
    asyncio.run(test_pdf_ingestion())
