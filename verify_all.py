import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

print("--- Verifying Imports ---")
try:
    import utils_data as ud
    print("[OK] utils_data imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import utils_data: {e}")

try:
    import utils_style as us
    print("[OK] utils_style imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import utils_style: {e}")

try:
    import utils_chart as uc
    print("[OK] utils_chart imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import utils_chart: {e}")

# Note: We can't fully import app.py because it contains streamlit commands that require a running app context
# But we can try to import it and catch the StreamlitAPIException if it's just about the context, 
# or syntax errors if there are any.
print("\n--- Verifying app.py Syntax ---")
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        compile(f.read(), 'app.py', 'exec')
    print("[OK] app.py syntax check passed")
except Exception as e:
    print(f"[FAIL] app.py syntax check failed: {e}")

print("\n--- Verifying utils_data Functionality ---")
try:
    df = ud.load_data_from_folder()
    print(f"[OK] load_data_from_folder executed. Data shape: {df.shape}")
    if not df.empty:
        print(f"   Columns: {list(df.columns)}")
except Exception as e:
    print(f"[FAIL] load_data_from_folder failed: {e}")

print("\n--- Verifying utils_style Functionality ---")
try:
    # Test color constants
    print(f"   Background Color: {us.COLORS['background']}")
    # Test formatting
    print(f"   Format 1000: {us.format_k(1000)}")
    print("[OK] utils_style basic checks passed")
except Exception as e:
    print(f"[FAIL] utils_style checks failed: {e}")
