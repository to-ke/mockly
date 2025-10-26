"""
Test script to verify code evaluation with Claude.
This demonstrates the new code quality rating feature.
"""

import requests
import json

# Backend URL - adjust if needed
API_BASE = "http://localhost:8000/api"

# Sample code for testing
TEST_CODE = '''
def two_sum(nums, target):
    # Create a hash map to store numbers and their indices
    num_map = {}
    
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    
    return []
'''

# Sample question context
TEST_QUESTION = {
    "difficulty": "easy",
    "prompt": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
}

def test_code_evaluation():
    """Test the code evaluation endpoint"""
    print("Testing code evaluation endpoint...")
    print("=" * 60)
    
    payload = {
        "code": TEST_CODE,
        "language": "python",
        "question": TEST_QUESTION
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/feedback",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Evaluation successful!")
            print("\n" + "=" * 60)
            print("SCORES")
            print("=" * 60)
            print(f"  Code Cleanliness: {result['codeCleanliness']}/5")
            print(f"  Communication: {result['communication']}/5")
            print(f"  Code Efficiency: {result['codeEfficiency']}/5")
            print("\n" + "=" * 60)
            print("DETAILED FEEDBACK")
            print("=" * 60)
            print(result['comments'])
            print("=" * 60)
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to backend. Make sure it's running on port 8000.")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_code_evaluation()

