#!/usr/bin/env python3
"""채점 대시보드 서버 launcher (cross-platform).

기능:
- 가상환경(.venv) 자동 생성
- Flask 자동 설치 (PEP 668 우회)
- 사용 가능한 포트 자동 탐지 (5050부터)
- Claude Code CLI 설치 확인
- app.py 실행

Windows 의 BAT 파일이 한글을 못 읽는 문제를 피하기 위해
모든 한글 출력은 이 Python 스크립트에서 담당.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
VENV = BASE / ".venv"
DEFAULT_PORT = 5050
PORT_CANDIDATES = (DEFAULT_PORT, 5051, 5052, 5053, 8000, 8080)

IS_WIN = os.name == "nt"


def venv_python() -> Path:
    """가상환경의 Python 실행파일 경로"""
    return VENV / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")


def ensure_venv() -> None:
    """가상환경이 없으면 생성"""
    if venv_python().exists():
        return
    print("가상환경(.venv)을 생성합니다...")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    except subprocess.CalledProcessError as e:
        sys.exit(f"[오류] 가상환경 생성에 실패했습니다: {e}")


def ensure_flask() -> None:
    """Flask 가 venv 에 설치되어 있는지 확인하고, 없으면 설치"""
    py = str(venv_python())
    try:
        subprocess.check_call(
            [py, "-c", "import flask"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return
    except subprocess.CalledProcessError:
        pass

    print("Flask 를 설치합니다...")
    try:
        subprocess.check_call(
            [py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
        )
        subprocess.check_call([py, "-m", "pip", "install", "--quiet", "flask"])
    except subprocess.CalledProcessError as e:
        sys.exit(f"[오류] Flask 설치에 실패했습니다: {e}")


def has_claude_cli() -> bool:
    """시스템에서 claude 명령이 발견되는지 확인"""
    if shutil.which("claude"):
        return True
    # Windows: npm 글로벌 경로에 claude.cmd 가 있을 수 있음
    if IS_WIN:
        for env in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base and (Path(base) / "npm" / "claude.cmd").exists():
                return True
    return False


def find_open_port() -> int:
    """5050부터 후보 포트를 시도해 사용 가능한 첫 번째 포트 반환"""
    for port in PORT_CANDIDATES:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return DEFAULT_PORT  # 모두 막혔으면 그냥 시도하고 실패는 Flask 가 보고


def main() -> None:
    print("=" * 42)
    print("  채점 대시보드 서버 시작")
    print("=" * 42)
    print()

    ensure_venv()
    ensure_flask()

    if not has_claude_cli():
        print("[경고] Claude Code CLI 가 설치되어 있지 않습니다.")
        print("       채점 기능을 사용하려면: npm install -g @anthropic-ai/claude-code")
        print("       (결과 보기는 CLI 없이도 가능합니다.)")
        print()

    port = find_open_port()
    if port != DEFAULT_PORT:
        print(f"  ⚠ 기본 포트({DEFAULT_PORT}) 가 사용 중이라 {port} 으로 실행합니다.")
    print(f"  📋  채점 대시보드: http://localhost:{port}")
    print(f"  📁  작업 폴더:    {BASE}")
    print("  종료하려면 Ctrl+C 를 누르세요.")
    print()

    py = str(venv_python())
    app_py = str(BASE / "app.py")

    # 한글 출력 깨짐 방지
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        subprocess.run([py, app_py, str(port)], env=env)
    except KeyboardInterrupt:
        print("\n서버를 종료했습니다.")


if __name__ == "__main__":
    main()
