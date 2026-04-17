#!/usr/bin/env python3
import requests
import os

# Test if server is running
base_url = "http://localhost:50263"

print("Testing backend endpoints...")

# Test 1: Check if server is responding
try:
    response = requests.get(base_url)
    print(f"✓ Server is running on {base_url}")
except requests.exceptions.ConnectionError:
    print(f"✗ Server is not running on {base_url}")
    exit(1)

# Test 2: Test transcribe endpoint with a file
audio_file = "Fairfield Dr 16.m4a"
if os.path.exists(audio_file):
    print(f"\nTesting /transcribe endpoint with {audio_file}...")
    
    with open(audio_file, 'rb') as f:
        files = {'audio': (audio_file, f, 'audio/m4a')}
        try:
            response = requests.post(f"{base_url}/transcribe", files=files)
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Transcription successful!")
                print(f"  Transcribed text: {result.get('text', '')[:100]}...")
                
                # Test 3: Test generate-sections endpoint
                print("\nTesting /generate-sections endpoint...")
                sections_response = requests.post(
                    f"{base_url}/generate-sections",
                    json={"text": result.get('text', '')}
                )
                if sections_response.status_code == 200:
                    sections = sections_response.json()
                    print("✓ GPT sections generated successfully!")
                    print(f"  Notes: {sections.get('notes', '')[:50]}...")
                    print(f"  Summary: {sections.get('summary', '')[:50]}...")
                    print(f"  Action items: {sections.get('action', '')[:50]}...")
                else:
                    print(f"✗ Generate sections failed: {sections_response.status_code}")
                    print(f"  Response: {sections_response.text}")
            else:
                print(f"✗ Transcription failed: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error during testing: {e}")
else:
    print(f"✗ Test file {audio_file} not found")

print("\nBackend test complete!")
