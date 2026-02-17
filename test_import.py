import sys, os

# Add local libs (priority)
libs_path = os.path.join(os.getcwd(), "libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

print(f"Libs path in sys.path: {libs_path in sys.path}")
print(f"Libs path: {libs_path}")

try:
    import google.generativeai
    print(f"Imported from: {google.generativeai.__file__}")
except Exception as e:
    print(f"Import Error: {e}")
    import traceback
    traceback.print_exc()

import importlib.util
spec = importlib.util.find_spec("google.generativeai")
print(f"Find spec: {spec}")
