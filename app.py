#!/usr/bin/env python3
"""채점 대시보드 웹 서버
Usage: python app.py [port]
Then open http://localhost:5050
"""

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import subprocess
import os
import sys
import json
import zipfile
import shutil
import glob
import re
import platform
import datetime
import io

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True   # 로컬 도구 — 템플릿 수정 시 즉시 반영
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample")

# 모든 채점 회차는 sessions/<id>/ 폴더에 격리되어 저장됨
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
ACTIVE_FILE = os.path.join(SESSIONS_DIR, "active.json")

# 세션 폴더 안에 있어야 정상으로 간주되는 입력/출력 이름들
SESSION_OWNED_NAMES = ("question.md", "평가기준.md", "answer", "data", "reports", "scores.tsv")
# 세션 폴더 안에서 보존해야 하는 항목 (채점 부산물 정리 시 건드리지 않음)
SESSION_KEEP = frozenset({"question.md", "평가기준.md", "answer", "data", "meta.json"})

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _ensure_sessions_dir():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def _new_session_id() -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    suf = os.urandom(2).hex()
    return f"s_{ts}_{suf}"


def _session_path(sid: str) -> str:
    return os.path.join(SESSIONS_DIR, sid)


def _session_meta_path(sid: str) -> str:
    return os.path.join(_session_path(sid), "meta.json")


def _load_meta(sid: str) -> dict:
    p = _session_meta_path(sid)
    if not os.path.isfile(p):
        return {"name": sid, "created_at": ""}
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {"name": sid, "created_at": ""}


def _save_meta(sid: str, meta: dict) -> None:
    p = _session_meta_path(sid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)


def _list_session_ids() -> list[str]:
    if not os.path.isdir(SESSIONS_DIR):
        return []
    out = []
    for entry in os.listdir(SESSIONS_DIR):
        full = os.path.join(SESSIONS_DIR, entry)
        if os.path.isdir(full) and not entry.startswith(".") and entry != "__MACOSX":
            out.append(entry)
    return out


def _read_active() -> str | None:
    if not os.path.isfile(ACTIVE_FILE):
        return None
    try:
        with open(ACTIVE_FILE, "r", encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("id") or None
    except Exception:
        return None


def _write_active(sid: str | None) -> None:
    _ensure_sessions_dir()
    with open(ACTIVE_FILE, "w", encoding="utf-8") as fh:
        json.dump({"id": sid}, fh, ensure_ascii=False)


def _next_default_name() -> str:
    """`수행평가 1`, `수행평가 2`, ... 중 비어있는 가장 작은 번호의 이름."""
    existing = {_load_meta(s).get("name", "") for s in _list_session_ids()}
    n = 1
    while f"수행평가 {n}" in existing:
        n += 1
    return f"수행평가 {n}"


def _create_session(name: str | None = None) -> str:
    _ensure_sessions_dir()
    sid = _new_session_id()
    sdir = _session_path(sid)
    os.makedirs(sdir, exist_ok=True)
    if not name:
        name = _next_default_name()
    meta = {
        "name": name,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    _save_meta(sid, meta)
    return sid


def _migrate_legacy() -> None:
    """sessions/ 가 없는 첫 실행에서 root 의 기존 입력/출력 파일을 한 세션으로 옮김."""
    if os.path.isdir(SESSIONS_DIR):
        return
    legacy = [n for n in SESSION_OWNED_NAMES if os.path.exists(os.path.join(BASE_DIR, n))]
    _ensure_sessions_dir()
    if not legacy:
        return
    sid = _create_session("기존 채점")
    sdir = _session_path(sid)
    for name in legacy:
        src = os.path.join(BASE_DIR, name)
        dst = os.path.join(sdir, name)
        try:
            shutil.move(src, dst)
        except Exception:
            pass
    _write_active(sid)


def _ensure_active_session() -> str:
    """활성 세션 ID 반환. 없으면 (마이그레이션 후) 새로 만들고 활성화."""
    _migrate_legacy()
    _ensure_sessions_dir()
    sid = _read_active()
    if sid and os.path.isdir(_session_path(sid)):
        return sid
    ids = _list_session_ids()
    if ids:
        # 가장 최근에 만들어진 세션을 활성화
        ids.sort(key=lambda s: _load_meta(s).get("created_at", ""), reverse=True)
        sid = ids[0]
    else:
        sid = _create_session()
    _write_active(sid)
    return sid


def _active_dir() -> str:
    return _session_path(_ensure_active_session())


def _session_summary(sid: str) -> dict:
    """사이드바에 보여줄 세션 요약 (이름·생성일·점수 요약)."""
    meta = _load_meta(sid)
    sdir = _session_path(sid)
    reports_dir = os.path.join(sdir, "reports")
    score_summary = None
    if os.path.isdir(reports_dir):
        r = _get_results_for_dir(reports_dir)
        if r:
            score_summary = {
                "total": r["total"],
                "avg": r["avg"],
                "max_total": r["max_total"],
            }
    return {
        "id": sid,
        "name": meta.get("name") or sid,
        "created_at": meta.get("created_at", ""),
        "score_summary": score_summary,
    }


def _list_session_summaries() -> list[dict]:
    out = [_session_summary(sid) for sid in _list_session_ids()]
    out.sort(key=lambda s: s["created_at"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# File status / results parsing (active session 기준)
# ---------------------------------------------------------------------------

def file_status():
    """현재 활성 세션 폴더에 채점에 필요한 파일이 있는지 확인"""
    sdir = _active_dir()
    answer_dir = os.path.join(sdir, "answer")
    data_dir = os.path.join(sdir, "data")
    reports_dir = os.path.join(sdir, "reports")
    answer_count = len(glob.glob(os.path.join(answer_dir, "*.py"))) if os.path.isdir(answer_dir) else 0
    data_count = 0
    if os.path.isdir(data_dir):
        data_count = len([
            x for x in os.listdir(data_dir)
            if not x.startswith(".") and x != "__MACOSX"
        ])
    report_html = glob.glob(os.path.join(reports_dir, "*.html")) if os.path.isdir(reports_dir) else []
    report_count = len([f for f in report_html if os.path.basename(f) != "index.html"])
    return {
        "question": os.path.isfile(os.path.join(sdir, "question.md")),
        "criteria": os.path.isfile(os.path.join(sdir, "평가기준.md")),
        "answer": answer_count,
        "data": data_count,
        "reports": report_count,
        "index_html": os.path.isfile(os.path.join(reports_dir, "index.html")),
    }


def _parse_md_report(path: str):
    """`이름(학번).md` 또는 `학번.md` 형식의 점수 데이터를 파싱"""
    basename = os.path.basename(path).replace(".md", "")
    m = re.match(r"(.+?)\((\d+)\)\s*$", basename)
    if m:
        name, sid = m.group(1).strip(), m.group(2)
    elif basename.isdigit():
        name, sid = "", basename  # 이름 없음 — 학번만
    else:
        return None

    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    score_m = re.search(r"\*\*합계\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*", content)
    score = int(score_m.group(2)) if score_m else 0
    max_total = int(score_m.group(1)) if score_m else 0

    categories = []
    total_section = re.search(r"## 총점\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if total_section:
        rows = re.findall(r"\|\s*([^|*]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", total_section.group(1))
        for cname, mx, sc in rows:
            cname = cname.strip()
            if cname and "평가요소" not in cname and "합계" not in cname and "만점" not in cname:
                categories.append({"name": cname, "score": int(sc), "max": int(mx)})

    return {
        "name": name,
        "id": sid,
        "score": score,
        "max_score": max_total or sum(c["max"] for c in categories) or 0,
        "categories": categories,
        "report_url": f"/reports/{sid}.html",
    }


def _parse_html_report(path: str):
    """`학번.html` 형식의 개별 리포트에서 점수 추출 (.md 없을 때 fallback)"""
    basename = os.path.basename(path).replace(".html", "")
    if not basename.isdigit():
        return None

    with open(path, "r", encoding="utf-8") as fh:
        html = fh.read()

    total_m = re.search(
        r"<span[^>]*class=['\"]score['\"][^>]*>\s*(\d+)\s*</span>"
        r"\s*<span[^>]*class=['\"]score-meta['\"][^>]*>\s*/\s*(\d+)",
        html, re.DOTALL,
    )
    score = int(total_m.group(1)) if total_m else 0
    max_total = int(total_m.group(2)) if total_m else 0

    cat_re = re.compile(
        r"<span[^>]*class=['\"]cat-name['\"][^>]*>\s*([^<]+?)\s*(?:<|</span>)"
        r".*?<span[^>]*class=['\"]cat-score['\"][^>]*>\s*(\d+)\s*/\s*(\d+)\s*</span>",
        re.DOTALL,
    )
    categories = []
    for cname, sc, mx in cat_re.findall(html):
        cname = re.sub(r"\s+", " ", cname).strip()
        if cname:
            categories.append({"name": cname, "score": int(sc), "max": int(mx)})

    if score == 0 and not categories:
        return None

    return {
        "name": "",
        "id": basename,
        "score": score,
        "max_score": max_total or sum(c["max"] for c in categories) or 0,
        "categories": categories,
        "report_url": f"/reports/{basename}.html",
    }


def _get_results_for_dir(reports_dir: str):
    if not os.path.isdir(reports_dir):
        return None
    students_by_id: dict[str, dict] = {}

    for f in sorted(glob.glob(os.path.join(reports_dir, "*.md"))):
        rec = _parse_md_report(f)
        if rec:
            students_by_id[rec["id"]] = rec

    for f in sorted(glob.glob(os.path.join(reports_dir, "*.html"))):
        if os.path.basename(f) == "index.html":
            continue
        rec = _parse_html_report(f)
        if rec and rec["id"] not in students_by_id:
            students_by_id[rec["id"]] = rec

    if not students_by_id:
        return None

    students = sorted(students_by_id.values(), key=lambda s: s["id"])
    cat_names: list[str] = []
    for s in students:
        if len(s["categories"]) > len(cat_names):
            cat_names = [c["name"] for c in s["categories"]]

    scores = [s["score"] for s in students]
    max_total = max((s["max_score"] for s in students), default=0)
    return {
        "students": students,
        "cat_names": cat_names,
        "total": len(students),
        "avg": round(sum(scores) / len(scores), 1),
        "max": max(scores),
        "min": min(scores),
        "max_total": max_total,
    }


def get_results():
    """활성 세션의 reports/ 에서 점수 요약 파싱"""
    return _get_results_for_dir(os.path.join(_active_dir(), "reports"))


def find_claude_cli():
    """Claude Code CLI 경로 찾기"""
    found = shutil.which("claude")
    if found:
        return found
    if platform.system() == "Windows":
        candidates = [
            os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm", "claude.cmd"),
        ]
    else:
        candidates = [
            "/usr/local/bin/claude",
            os.path.expanduser("~/.npm-global/bin/claude"),
            os.path.expanduser("~/.nvm/versions/node/*/bin/claude"),
        ]
    for c in candidates:
        for p in glob.glob(c):
            if os.path.isfile(p):
                return p
    return None


# ---------------------------------------------------------------------------
# Routes — base
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    sid = _ensure_active_session()
    return render_template(
        "index.html",
        status=file_status(),
        results=get_results(),
        sessions=_list_session_summaries(),
        active=_session_summary(sid),
    )


@app.route("/api/status")
def api_status():
    return jsonify(file_status())


@app.route("/api/results")
def api_results():
    r = get_results()
    return jsonify(r) if r else jsonify(None)


# ---------------------------------------------------------------------------
# Routes — Sessions CRUD
# ---------------------------------------------------------------------------

@app.route("/api/sessions")
def api_sessions_list():
    sid = _ensure_active_session()
    return jsonify({
        "active_id": sid,
        "sessions": _list_session_summaries(),
    })


@app.route("/api/sessions", methods=["POST"])
def api_sessions_create():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip() or None
    sid = _create_session(name)
    _write_active(sid)
    return jsonify({"ok": True, "id": sid, "summary": _session_summary(sid)})


@app.route("/api/sessions/<sid>", methods=["PATCH"])
def api_sessions_rename(sid: str):
    if not os.path.isdir(_session_path(sid)):
        return jsonify({"ok": False, "error": "세션을 찾을 수 없습니다"}), 404
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "이름이 비어있습니다"}), 400
    meta = _load_meta(sid)
    meta["name"] = name
    _save_meta(sid, meta)
    return jsonify({"ok": True, "summary": _session_summary(sid)})


@app.route("/api/sessions/<sid>", methods=["DELETE"])
def api_sessions_delete(sid: str):
    sdir = _session_path(sid)
    if not os.path.isdir(sdir):
        return jsonify({"ok": False, "error": "세션을 찾을 수 없습니다"}), 404
    try:
        shutil.rmtree(sdir, ignore_errors=True)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    # 활성 세션을 지웠으면 다른 세션을 활성화 (없으면 새로 생성)
    if _read_active() == sid:
        _write_active(None)
        _ensure_active_session()

    return jsonify({"ok": True, "active_id": _read_active()})


@app.route("/api/sessions/<sid>/activate", methods=["POST"])
def api_sessions_activate(sid: str):
    if not os.path.isdir(_session_path(sid)):
        return jsonify({"ok": False, "error": "세션을 찾을 수 없습니다"}), 404
    _write_active(sid)
    return jsonify({"ok": True, "active_id": sid})


# ---------------------------------------------------------------------------
# Routes — Upload / Reset
# ---------------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload():
    file_type = request.form.get("type")
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "파일이 없습니다"}), 400

    sdir = _active_dir()
    try:
        if file_type == "question":
            f.save(os.path.join(sdir, "question.md"))

        elif file_type == "criteria":
            f.save(os.path.join(sdir, "평가기준.md"))

        elif file_type == "answer":
            answer_dir = os.path.join(sdir, "answer")
            os.makedirs(answer_dir, exist_ok=True)
            if f.filename.endswith(".zip"):
                tmp = os.path.join(sdir, "_tmp_answer.zip")
                f.save(tmp)
                with zipfile.ZipFile(tmp, "r") as z:
                    for info in z.infolist():
                        if info.filename.endswith(".py") and not info.is_dir():
                            info.filename = os.path.basename(info.filename)
                            z.extract(info, answer_dir)
                os.remove(tmp)
            else:
                f.save(os.path.join(answer_dir, f.filename))

        elif file_type == "data":
            if not f.filename.endswith(".zip"):
                return jsonify({"ok": False, "error": "학생 코드는 zip 파일로 업로드해주세요"}), 400
            data_dir = os.path.join(sdir, "data")
            if os.path.isdir(data_dir):
                shutil.rmtree(data_dir)
            os.makedirs(data_dir, exist_ok=True)
            tmp = os.path.join(sdir, "_tmp_data.zip")
            f.save(tmp)
            with zipfile.ZipFile(tmp, "r") as z:
                z.extractall(data_dir)
            os.remove(tmp)
            for junk in ("__MACOSX", ".DS_Store"):
                jpath = os.path.join(data_dir, junk)
                if os.path.isdir(jpath):
                    shutil.rmtree(jpath, ignore_errors=True)
                elif os.path.isfile(jpath):
                    os.remove(jpath)
            items = [
                x for x in os.listdir(data_dir)
                if not x.startswith(".") and x != "__MACOSX"
            ]
            if len(items) == 1 and os.path.isdir(os.path.join(data_dir, items[0])):
                inner = os.path.join(data_dir, items[0])
                for item in os.listdir(inner):
                    shutil.move(os.path.join(inner, item), os.path.join(data_dir, item))
                os.rmdir(inner)
        else:
            return jsonify({"ok": False, "error": f"알 수 없는 타입: {file_type}"}), 400

        return jsonify({"ok": True, "status": file_status()})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _delete_grading_artifacts(sdir: str, deleted: list[str]) -> None:
    """채점 부산물(임시 .py, scores.tsv 등) 정리. 입력 파일·메타·reports 는 보존.
    reports/ 는 호출자가 별도로 삭제하므로 여기선 스킵.
    """
    if not os.path.isdir(sdir):
        return
    for entry in os.listdir(sdir):
        if entry.startswith(".") or entry == "__pycache__":
            continue
        if entry == "reports":
            continue
        if entry in SESSION_KEEP:
            continue
        full = os.path.join(sdir, entry)
        try:
            if os.path.isfile(full):
                os.remove(full)
                deleted.append(entry)
            elif os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)
                deleted.append(entry + "/")
        except Exception:
            pass


@app.route("/api/reset", methods=["POST"])
def reset_uploads():
    """활성 세션의 업로드 파일과 채점 리포트를 초기화.
    body: { "target": "all" | "question" | "criteria" | "answer" | "data" | "reports" }
    """
    body = request.get_json(silent=True) or {}
    target = (body.get("target") or "all").strip()
    valid = {"all", "question", "criteria", "answer", "data", "reports"}
    if target not in valid:
        return jsonify({"ok": False, "error": f"target은 {sorted(valid)} 중 하나여야 합니다"}), 400

    sdir = _active_dir()
    deleted: list[str] = []

    def rm_file(path: str, label: str):
        if os.path.isfile(path):
            os.remove(path)
            deleted.append(label)

    def rm_dir(path: str, label: str):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            deleted.append(label)

    try:
        if target in ("question", "all"):
            rm_file(os.path.join(sdir, "question.md"), "question.md")
        if target in ("criteria", "all"):
            rm_file(os.path.join(sdir, "평가기준.md"), "평가기준.md")
        if target in ("answer", "all"):
            rm_dir(os.path.join(sdir, "answer"), "answer/")
        if target in ("data", "all"):
            rm_dir(os.path.join(sdir, "data"), "data/")
        if target in ("reports", "all"):
            rm_dir(os.path.join(sdir, "reports"), "reports/")
            _delete_grading_artifacts(sdir, deleted)
        return jsonify({"ok": True, "deleted": deleted, "status": file_status()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Routes — Code runner
# ---------------------------------------------------------------------------

@app.route("/api/run", methods=["POST"])
def run_code():
    """학생 코드를 실행하고 결과 반환 (timeout 5초)"""
    import tempfile
    data = request.get_json()
    code = data.get("code", "")
    stdin_input = data.get("input", "")

    if not code.strip():
        return jsonify({"ok": False, "error": "코드가 비어있습니다"})

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, tmp_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        os.unlink(tmp_path)

        output = proc.stdout
        if proc.returncode != 0:
            err_text = proc.stderr.strip()
            short_err = err_text.split("\n")[-1] if err_text else "런타임 오류"
            if output:
                return jsonify({"ok": True, "output": output + "\n⚠️ " + short_err})
            return jsonify({"ok": False, "error": short_err})

        return jsonify({"ok": True, "output": output})

    except subprocess.TimeoutExpired:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return jsonify({"ok": False, "error": "시간 초과 (5초)"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Routes — Grading
# ---------------------------------------------------------------------------

@app.route("/api/grade")
def grade():
    """Claude Code CLI를 호출하여 활성 세션을 채점 (SSE 스트리밍)"""
    sheet_url = request.args.get("sheet_url", "").strip()
    sdir = _active_dir()

    claude_cmd = find_claude_cli()
    if not claude_cmd:
        def err():
            yield _sse({"type": "error", "text": "Claude Code CLI를 찾을 수 없습니다.\nnpm install -g @anthropic-ai/claude-code 로 설치해주세요."})
        return Response(err(), mimetype="text/event-stream")

    template_md = os.path.join(SAMPLE_DIR, "report-template.md")
    template_html = os.path.join(SAMPLE_DIR, "report-template.html")
    claude_md = os.path.join(BASE_DIR, "CLAUDE.md")

    prompt = (
        "학생들의 파이썬 코드를 채점해줘.\n"
        f"절차·산출물 형식·채점 정책은 모두 `{claude_md}` 규약을 그대로 따라줘.\n"
        "\n"
        "현재 작업 폴더가 채점 대상 세션이야. 모든 입출력은 이 폴더 기준으로 진행:\n"
        "  - 입력: question.md, 평가기준.md, answer/*.py, data/<학생>/<문제>/Project/Main.py\n"
        "  - 출력: reports/<이름>(<학번>).md, reports/<학번>.html, reports/index.html, scores.tsv\n"
        "\n"
        "리포트 형식 reference (절대 경로 — 그대로 읽어서 데이터만 갈아끼우기):\n"
        f"  - {template_md}\n"
        f"  - {template_html}\n"
        "\n"
        "핵심:\n"
        "1) question.md, 평가기준.md, answer/*.py 를 먼저 읽어 채점 기준과 모범답안을 파악할 것.\n"
        "2) data/<학생>/<문제>/Project/Main.py 를 학생별로 실제 실행(timeout 5초, UTF-8)해 테스트케이스로 채점할 것.\n"
        "3) 평가기준.md 의 평가요소 이름을 글자 그대로 사용할 것 (대시보드 파싱용).\n"
        "4) reports/ 폴더에 산출물 4종을 모두 생성:\n"
        "   - reports/<이름>(<학번>).md — `## 총점` 섹션과 `| **합계** | **만점** | **점수** |` 행 필수\n"
        "   - reports/<학번>.html — 학생용 개별 리포트 (인라인 CSS, 외부 CDN 금지, 실행 컨트롤 포함)\n"
        "   - reports/index.html — 전체 학생 요약\n"
        "   - scores.tsv — 탭 구분 점수표\n"
        "5) 고등학생 대상이라 후하게 채점하고, 평가기준.md 의 특이사항을 반드시 반영할 것.\n"
        "6) 끝나면 \"채점 완료: N명, 평균 X.X점\" 한 줄로 요약 출력.\n"
    )
    if sheet_url:
        prompt += (
            f"\n추가로, 채점이 끝나면 다음 구글시트에 점수를 입력해줘: {sheet_url}\n"
            "시트 컬럼은 scores.tsv 와 동일한 순서로 맞춰줘."
        )

    def generate():
        yield _sse({"type": "status", "text": "Claude Code를 시작합니다..."})

        cmd = [claude_cmd, "-p", prompt, "--output-format", "stream-json", "--verbose"]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=sdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            yield _sse({"type": "error", "text": f"실행 실패: {e}"})
            return

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                msg_type = data.get("type", "")

                if msg_type == "assistant":
                    for block in data.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            yield _sse({"type": "log", "text": block["text"]})
                        elif block.get("type") == "tool_use":
                            name = block.get("name", "tool")
                            inp = block.get("input", {})
                            summary = ""
                            if "command" in inp:
                                summary = inp["command"][:120]
                            elif "file_path" in inp:
                                summary = inp["file_path"]
                            yield _sse({"type": "tool", "name": name, "detail": summary})

                elif msg_type == "tool_result" or msg_type == "result":
                    text = data.get("result", data.get("output", ""))
                    if isinstance(text, str) and text.strip():
                        yield _sse({"type": "result_text", "text": text[:500]})

                elif msg_type == "system":
                    yield _sse({"type": "status", "text": data.get("message", "")})

            except json.JSONDecodeError:
                yield _sse({"type": "log", "text": line})

        proc.wait()

        if proc.returncode == 0:
            results = get_results()
            yield _sse({"type": "complete", "results": results})
        else:
            yield _sse({"type": "error", "text": f"Claude Code 종료 (코드 {proc.returncode})"})

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(os.path.join(_active_dir(), "reports"), filename)


# ---------------------------------------------------------------------------
# Routes — Students / sample download
# ---------------------------------------------------------------------------

def _data_root():
    """활성 세션의 data/ 또는 data/data/ (이중 중첩)에서 실제 학생 폴더 루트를 찾음"""
    data_dir = os.path.join(_active_dir(), "data")
    if not os.path.isdir(data_dir):
        return None
    items = [
        x for x in os.listdir(data_dir)
        if not x.startswith(".") and x != "__MACOSX"
    ]
    if len(items) == 1:
        inner = os.path.join(data_dir, items[0])
        if os.path.isdir(inner):
            return inner
    return data_dir


def list_students():
    """활성 세션의 data/ 하위에서 학생/문제 목록을 추출."""
    root = _data_root()
    if not root:
        return []

    students = []
    for sf in sorted(os.listdir(root)):
        if sf.startswith(".") or sf == "__MACOSX":
            continue
        full = os.path.join(root, sf)
        if not os.path.isdir(full):
            continue

        m = re.search(r"(.+?)\((\d+)@", sf)
        if m:
            name, sid = m.group(1).strip(), m.group(2)
        elif sf.isdigit():
            name, sid = "", sf
        else:
            name, sid = sf, sf

        problems = []
        for pf in sorted(os.listdir(full)):
            if pf.startswith("."):
                continue
            pf_full = os.path.join(full, pf)
            if not os.path.isdir(pf_full):
                continue
            nums = re.findall(r"\d+", pf)
            if not nums:
                continue
            num = int(nums[-1])
            main_py = os.path.join(pf_full, "Project", "Main.py")
            if not os.path.isfile(main_py):
                cand = os.path.join(pf_full, "Main.py")
                if os.path.isfile(cand):
                    main_py = cand
                else:
                    continue
            problems.append({"num": num, "folder": pf, "path": main_py})

        problems.sort(key=lambda p: p["num"])
        students.append({
            "id": sid,
            "name": name,
            "label": f"{name} ({sid})" if name else sid,
            "folder": sf,
            "problems": [{"num": p["num"]} for p in problems],
            "_problem_paths": {p["num"]: p["path"] for p in problems},
        })

    return students


@app.route("/api/students")
def api_students():
    students = list_students()
    return jsonify([
        {k: v for k, v in s.items() if not k.startswith("_")}
        for s in students
    ])


@app.route("/api/student-code")
def api_student_code():
    sid = request.args.get("id", "").strip()
    pnum_raw = request.args.get("problem", "").strip()
    if not sid or not pnum_raw.isdigit():
        return jsonify({"ok": False, "error": "id와 problem 파라미터가 필요합니다"}), 400
    pnum = int(pnum_raw)

    students = list_students()
    student = next((s for s in students if s["id"] == sid), None)
    if not student:
        return jsonify({"ok": False, "error": f"학생 {sid}을(를) 찾을 수 없습니다"}), 404

    path = student["_problem_paths"].get(pnum)
    if not path or not os.path.isfile(path):
        return jsonify({"ok": False, "error": f"문제 {pnum} 코드가 없습니다 (미제출)"}), 404

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            code = fh.read()
    except Exception as e:
        return jsonify({"ok": False, "error": f"파일 읽기 실패: {e}"}), 500

    return jsonify({
        "ok": True,
        "id": sid,
        "name": student["name"],
        "problem": pnum,
        "code": code,
    })


@app.route("/api/sample/<kind>")
def download_sample(kind: str):
    if not os.path.isdir(SAMPLE_DIR):
        return jsonify({"ok": False, "error": "sample 폴더가 없습니다"}), 404

    if kind == "question":
        path = os.path.join(SAMPLE_DIR, "question.md")
        if not os.path.isfile(path):
            return jsonify({"ok": False, "error": "question.md가 없습니다"}), 404
        return send_from_directory(SAMPLE_DIR, "question.md", as_attachment=True)

    if kind == "criteria":
        path = os.path.join(SAMPLE_DIR, "criteria.md")
        if not os.path.isfile(path):
            return jsonify({"ok": False, "error": "criteria.md가 없습니다"}), 404
        return send_from_directory(
            SAMPLE_DIR, "criteria.md",
            as_attachment=True, download_name="평가기준.md",
        )

    if kind == "answer":
        return _zip_directory_response(os.path.join(SAMPLE_DIR, "answer"), "answer.zip")

    if kind == "data":
        return _zip_directory_response(os.path.join(SAMPLE_DIR, "data"), "data.zip")

    return jsonify({"ok": False, "error": f"알 수 없는 샘플: {kind}"}), 404


def _zip_directory_response(src_dir: str, download_name: str) -> Response:
    if not os.path.isdir(src_dir):
        return jsonify({"ok": False, "error": f"폴더가 없습니다: {os.path.basename(src_dir)}"}), 404

    base_name = os.path.basename(src_dir.rstrip(os.sep))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if fname.startswith("."):
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, src_dir)
                arc = f"{base_name}/{rel.replace(os.sep, '/')}"
                zf.write(full, arc)
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "Cache-Control": "no-store",
        },
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5050
    print(f"\n  📋  채점 대시보드: http://localhost:{port}")
    print(f"  📁  작업 폴더:    {BASE_DIR}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
