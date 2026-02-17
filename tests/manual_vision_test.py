"""
Manual test for Vision capabilities.
Directly invokes ModelRouter with a multimodal message to verify image handling.
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

from src.infra.model_router import model_router

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_vision():
    print("--- Starting Vision Test ---")
    
    # URL of a cat image
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/320px-Cat03.jpg"
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "O que você vê nesta imagem? Responda em uma frase curta."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ]
    
    print(f"Testing with image: {image_url}")
    
    try:
        # Test with Native Gemini (forcing default chain which usually falls back to flash)
        result = await model_router.generate_with_history(
            messages=messages,
            chain="default", 
            temperature=0.0
        )
        
        print("\n--- Result ---")
        print(f"Model used: {result.get('model')}")
        print(f"Content: {result.get('content')}")
        print("--------------\n")
        
        if "gato" in result.get("content", "").lower() or "cat" in result.get("content", "").lower():
            print("✅ TEST PASSED: Cat detected.")
        else:
            print("⚠️ TEST WARNING: Cat not explicitly mentioned (check output).")
            
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vision())
