#!/bin/bash
# Test script for wake word detection with Edge TTS
# FASE 0 #18: Voice Interface Integration

API_URL="https://optimus.tier.finance"
# For local testing: API_URL="http://localhost:8000"

echo "=== Wake Word Detection Test ==="
echo ""

# Test 1: Update config to use Edge TTS (free, no API key needed)
echo "1. Updating voice config to use Edge TTS..."
curl -X PUT "${API_URL}/api/v1/voice/config" \
  -H "Content-Type: application/json" \
  -d '{
    "tts_provider": "edge",
    "stt_provider": "stub"
  }'
echo -e "\n"

# Test 2: Get current config
echo "2. Getting current voice config..."
curl -X GET "${API_URL}/api/v1/voice/config"
echo -e "\n"

# Test 3: Test wake word detection (stub mode)
# In production, you would send real audio base64
echo "3. Testing wake word detection with stub provider..."
echo "   (In production, send real audio with 'Hey Optimus, what time is it?')"

# Create a fake base64 audio (just for testing the endpoint structure)
FAKE_AUDIO_B64=$(echo "fake audio data" | base64)

curl -X POST "${API_URL}/api/v1/voice/command" \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_base64\": \"${FAKE_AUDIO_B64}\",
    \"user_id\": \"test-user\",
    \"session_id\": \"test-session\"
  }"
echo -e "\n"

echo ""
echo "=== Test Complete ==="
echo ""
echo "To test with real audio from frontend:"
echo "1. Go to https://optimus.tier.finance/"
echo "2. Click the microphone button"
echo "3. Say: 'Hey Optimus, what time is it?'"
echo "4. Check browser console for 'Wake word detected!' message"
echo ""
echo "Wake words configured: 'optimus', 'hey optimus'"
echo "Voice provider: Edge TTS (pt-BR-AntonioNeural)"
