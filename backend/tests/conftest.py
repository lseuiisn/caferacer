import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
backend_path = str(BACKEND_ROOT)
if backend_path in sys.path:
    sys.path.remove(backend_path)
sys.path.insert(0, backend_path)

# 다른 작업공간에서 이미 import된 동일 이름 패키지가 테스트를 오염시키지 않게 한다.
loaded_app = sys.modules.get("app")
if loaded_app is not None:
    app_file = Path(getattr(loaded_app, "__file__", "")).resolve()
    if BACKEND_ROOT not in app_file.parents:
        for module_name in [name for name in sys.modules if name == "app" or name.startswith("app.")]:
            del sys.modules[module_name]
