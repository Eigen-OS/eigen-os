from __future__ import annotations

import sys
import subprocess
from pathlib import Path


_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    import google.rpc  # type: ignore
except ModuleNotFoundError:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "googleapis-common-protos>=1.72",
            "grpcio-status>=1.76",
        ],
        check=True,
    )