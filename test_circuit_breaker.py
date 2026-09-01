import os
from src import image_generator

# Fake token to force Hugging Face failure
os.environ["HF_TOKEN"] = "fake_invalid_token_to_force_failure"

def test():
    print("=== STARTING QA TEST: CIRCUIT BREAKER & DEEP LOGGING ===")
    
    # Try generating an image. Engine 1 should fail 3 times and open the circuit.
    print("\n--- Test 1: Forcing Engine 1 (Inkos) Failure ---")
    image_generator.generate_scene_image("Test scene 1", "output/test_img1.jpg")
    
    # Try generating a second image. Engine 1 should be skipped immediately.
    print("\n--- Test 2: Verifying Circuit Breaker Status ---")
    image_generator.generate_scene_image("Test scene 2", "output/test_img2.jpg")

    print("\n=== QA TEST COMPLETE ===")

if __name__ == "__main__":
    test()
