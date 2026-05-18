# 도담 채점 대시보드 — 프로젝트 컨텍스트 (Claude용)

> 이 문서는 **Claude가 이 프로젝트를 이어받을 때 빠르게 이해하도록** 작성됨.
> 채점 작업의 행동 규약은 별도 파일 `CLAUDE.md` 참고. 사용자(선생님) 가이드는 `guide.md`.

---

## 0. 한 줄 요약

선생님이 브라우저에서 파일(문제·평가기준·모범답안·학생 코드)을 업로드하면, Flask 대시보드가 **`claude -p` 서브프로세스를 띄워 Claude Code CLI에게 채점을 맡기고**, Claude가 만든 리포트를 같은 페이지에 보여준다. 채점 로직 자체는 Python에 하드코딩되어 있지 않고 **매번 Claude가 동적으로** 평가기준을 읽어 수행한다.

---

## 1. 아키텍처 개요

```
┌─────────────────────────┐    HTTP     ┌──────────────────────────┐
│  Browser  (대시보드 UI)  │  ◀──────▶  │  Flask 서버 (app.py)      │
│  templates/index.html   │             │  - 업로드 / 다운로드        │
└─────────────────────────┘             │  - 코드 실행기 백엔드        │
                                        │  - SSE: 채점 진행 스트리밍   │
                                        └──────┬───────────────────┘
                                               │ subprocess Popen
                                               │ stream-json
                                               ▼
                                        ┌──────────────────────────┐
                                        │  Claude Code CLI          │
                                        │  ($ claude -p ...         │
                                        │       --output-format     │
                                        │       stream-json         │
                                        │       --verbose)          │
                                        │  → CLAUDE.md 규약대로      │
                                        │    학생 코드 실행/채점/리포트│
                                        └──────────────────────────┘
```

핵심 통찰: **Flask는 채점하지 않는다.** Flask는 (a) 파일 업로드/관리, (b) Claude 호출, (c) Claude가 만든 결과 파싱 및 표시만 담당한다.

---

## 2. 파일 구조

```
dodam/
├── app.py                  # Flask 서버 — 모든 백엔드 로직
├── CLAUDE.md               # 채점 시 Claude가 따라야 할 규약 (Claude Code가 자동 로드)
├── project.md              # ★ 이 문서 — 개발용 프로젝트 컨텍스트
├── guide.md                # 사용자(선생님)용 가이드
├── run_server.py           # ⭐ 크로스플랫폼 런처 (venv·Flask·포트 자동 처리, 한글 출력 담당)
├── run_server.sh           # macOS/Linux 진입점 (run_server.py 호출만)
├── run_server.bat          # Windows 진입점 (ASCII만, run_server.py 호출만)
├── templates/
│   └── index.html          # 단일 페이지 대시보드 (인라인 CSS+JS)
├── sample/                 # 샘플 데이터 (대시보드 다운로드 + Claude 출력 reference)
│   ├── question.md
│   ├── criteria.md             # → 다운로드 시 평가기준.md 로 변환
│   ├── answer/q1~q8.py
│   ├── data/<학번>/...
│   ├── report-template.md      # ★ MD 점수 데이터 형식 reference (Claude가 복제)
│   └── report-template.html    # ★ 학생 HTML 리포트 형식 reference (실행 버튼 포함)
│
├── question.md             # ▼ 사용자 업로드 (대시보드에서 갱신)
├── 평가기준.md
├── answer/qN.py
├── data/<학생폴더>/<문제폴더>/Project/Main.py
│
├── reports/                # ▼ Claude 생성 산출물
│   ├── <이름>(<학번>).md   # 점수 데이터 (대시보드 파싱용) — 또는 <학번>.md
│   ├── <학번>.html         # 학생 개별 리포트 (각 문제 카드에 실행 버튼 포함)
│   └── index.html          # 전체 요약
├── scores.tsv              # 점수 요약 (구글시트 붙여넣기용)
│
├── .venv/                  # Python 가상환경 (run_server.py가 자동 생성)
└── __pycache__/            # Python 캐시 (자동 생성)
```

**파일 분류 (`app.py`의 `PROJECT_FILES` / `UPLOAD_FILES`)**

- 🛡 **초기 파일** (절대 삭제 X): `app.py`, `CLAUDE.md`, `project.md`, `guide.md`, `run_server.py/.sh/.bat`, `templates/`, `sample/`, `requirements.txt`, `README.md`
- 📤 **업로드 파일** (결과 초기화 시 보존, 전체 초기화 시 삭제): `question.md`, `평가기준.md`, `answer/`, `data/`
- 🗑 **채점 부산물** (결과 초기화 시 함께 삭제): `reports/`, `scores.tsv`, root 직속의 그 외 파일 (Claude가 만든 임시 스크립트 등)
- 🔒 **숨김/캐시** (항상 보존): `.venv`, `.git`, `.bkit`, `.DS_Store`, `__pycache__`

---

## 3. 데이터 흐름 (채점 1회)

1. 선생님이 대시보드에서 4개 카드를 통해 파일 업로드
   → Flask 가 `question.md`, `평가기준.md`, `answer/`, `data/` 에 저장
   → 학생 zip은 `__MACOSX`/`.DS_Store` 정리 + 단일 wrapper 폴더 자동 unwrap
2. "채점 시작" 클릭 → `GET /api/grade` (SSE) 호출
3. Flask 가 다음 명령으로 Claude Code CLI 서브프로세스 spawn:
   ```
   claude -p "<채점 지시 프롬프트>" --output-format stream-json --verbose
   ```
4. Claude 가 `CLAUDE.md` 를 자동으로 읽고, 절차대로:
   - `question.md`/`평가기준.md`/`answer/*.py` 로 채점 기준 파악
   - `data/<학생>/<문제>/Project/Main.py` 를 Bash + python3 + timeout 5초로 직접 실행
   - 테스트케이스 비교, 평가기준 항목 충족 여부 판단, 점수 계산
   - `reports/` 에 4종 산출물 생성 (`이름(학번).md`, `학번.html`, `index.html`, `scores.tsv`)
5. Claude 가 stream-json 으로 진행 메시지를 흘려보내면 Flask 가 SSE 로 변환해 브라우저에 표시
6. 종료 시 Flask가 `get_results()` 로 reports 폴더 파싱 → 점수표 렌더링
7. (선택) 사용자가 구글시트 URL을 줬다면 Claude 가 추가로 시트 입력

---

## 4. 산출물 형식

> Claude 가 매번 처음부터 만드는 게 아니라 `sample/report-template.{md,html}` 을 reference 로 보고 데이터만 갈아끼우는 방식. CLAUDE.md §2 가 이를 강제한다.

### 4-1. `reports/<이름>(<학번>).md` 또는 `<학번>.md` — 대시보드 파싱용

```markdown
# 채점 결과: 홍길동 (20203)

## 총점

| 평가요소 | 만점 | 점수 |
|----------|------|------|
| 함수 설계 및 구현 | 10 | 8 |
| 변수 활용 | 6 | 4 |
| 재귀 알고리즘의 설계 | 10 | 6 |
| 구조 비교 및 변환 | 7 | 5 |
| **합계** | **33** | **23** |

## 문제별 결과
...
```

**파싱 정규식 (`app.py` 의 `_parse_md_report`)**:
- 합계: `\*\*합계\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*`
- 카테고리 행: `\|\s*([^|*]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|` (단, `합계`/`평가요소`/`만점` 헤더는 필터링됨)

이 형식이 어긋나면 대시보드 점수표가 비어 보인다. `sample/report-template.md` 가 표준 형식.

### 4-2. `reports/<학번>.html` — 학생/선생님용 개별 리포트

큰 틀(빠지면 안 되는 기능):
1. 헤더(이름·학번·총점/만점)
2. 평가요소별 점수 카드 (각 항목 ✓/✗)
3. 문제별 카드: 학생 코드 + 모범 답안 나란히 + 평가기준 항목별 ✓/✗ + 코멘트
4. **각 문제 카드 안에 학생 코드 실행 컨트롤** (인라인 runner)
5. 미제출 문제는 "미제출" 명시

**runner 컨트롤** (CLAUDE.md §2-2-A 사양):
- 표준입력 박스 + ▶ 실행 버튼 + 결과 영역
- 첫 테스트케이스 입력값을 자동 채움
- `/api/run` POST(`{code, input}`) 호출, timeout 5초
- Ctrl/⌘+Enter 단축키 지원
- iframe / 새 탭 / 직접 호스트 열기 모두에서 동작 (동일 출처)

**셀렉터 계약 (변경 금지)**: `.q-card`, `.code-grid pre` 첫 번째(=학생 코드), `table tbody tr td:first-child em`(=입력 없음 표시). 이게 깨지면 모든 리포트의 실행 버튼이 한 번에 죽는다.

**fallback 파싱**: MD 가 없어도 `app.py` 의 `_parse_html_report` 가 `<span class='score'>...</span>` + `<span class='cat-name'>...</span><span class='cat-score'>...</span>` 패턴으로 점수 추출.

`sample/report-template.html` 이 모든 변형(통과/실패/미제출, 입력 있음/없음)을 포함한 reference.

### 4-3. `reports/index.html`

전체 학생 점수표 + 평균/최고/최저 + 학생별 `<학번>.html` 링크. 대시보드의 "📄 전체 리포트 페이지 열기" 버튼이 새 탭으로 연다.

### 4-4. `scores.tsv`

탭 구분 점수표 (구글시트 붙여넣기용). 헤더 1줄 + 학생당 1줄.

---

## 5. API 엔드포인트 (app.py)

| 메서드 | 경로 | 용도 |
|------|------|------|
| GET | `/` | 대시보드 SSR (status + results) |
| GET | `/api/status` | 파일 준비 상태 (`question`, `criteria`, `answer`, `data`, `reports`, `index_html`) |
| GET | `/api/results` | 점수 요약 JSON |
| POST | `/api/upload` | `type=question/criteria/answer/data` + `file` |
| POST | `/api/reset` | `target=all/question/criteria/answer/data/reports` |
| GET | `/api/grade?sheet_url=...` | SSE 스트림. Claude Code CLI 호출 |
| GET | `/api/sample/<kind>` | 샘플 다운로드 (`question`/`criteria`/`answer`/`data`) |
| GET | `/api/students` | 학생/문제 목록 (코드 실행기용) |
| GET | `/api/student-code?id=&problem=` | 특정 학생의 특정 문제 Main.py 내용 |
| POST | `/api/run` | `{code, input}` 로 임시 .py 실행 (timeout 5초, UTF-8) |
| GET | `/reports/<path>` | reports/ 정적 서빙 |

**SSE 메시지 타입**: `status`, `log`, `tool`, `result_text`, `error`, `complete` (with `results`)

---

## 6. 프런트엔드 (templates/index.html — 단일 파일)

인라인 CSS/JS, 외부 CDN 미사용 (오프라인 재현성).

**주요 섹션**:

1. **Hero** (결과 없을 때만)
2. **파일 업로드** (4 카드, 호버 시 우상단 × 버튼으로 개별 초기화)
3. **샘플 다운로드 바** (4 링크: question/평가기준/answer.zip/data.zip)
4. **파일 가이드 표** (각 행에 다운로드 링크)
5. **🗑 전체 초기화 버튼**
6. **구글시트 URL 입력** (선택)
7. **액션 바**: 채점 시작 / 전체 리포트 보기 / 결과 표 보기 / 결과 초기화
8. **진행 로그** (SSE 메시지 표시) + **완료 카드** (✅ 성공 시)
9. **🧪 학생 코드 실행기** (data 있을 때만 노출) — 학생/문제 select → 코드 textarea → stdin → 결과
10. **결과 섹션** (results 있을 때) — 통계 박스 + 학생별 점수 테이블 + 개별 리포트 iframe 뷰어

---

## 7. 핵심 함수/클래스 (app.py)

| 함수 | 역할 |
|------|------|
| `file_status()` | 4개 업로드 + reports 상태 판정 |
| `get_results()` | reports/*.md 우선, 없으면 *.html 에서 점수 fallback 추출 |
| `_parse_md_report(path)` / `_parse_html_report(path)` | 단일 파일 파싱 |
| `_data_root()` | `data/` 또는 `data/data/` (이중 중첩 자동 감지) |
| `list_students()` | 학생/문제 목록 — `이름(학번@..)` 또는 `학번` 폴더 모두 지원, 문제 폴더는 마지막 숫자 시퀀스를 번호로 |
| `find_claude_cli()` | 시스템에서 `claude` 실행 파일 경로 탐색 (npm/nvm 경로 포함) |
| `_zip_directory_response()` | 메모리 zip 생성 (.DS_Store 제외) |
| `_delete_grading_artifacts()` | 화이트리스트 외 root 직속 파일 정리 |

---

## 8. 흔한 함정 (실제로 부딪힌 것들)

1. **macOS 5000 포트 충돌** — AirPlay Receiver 가 점유. 기본 포트는 **5050**. `run_server.sh`가 5050→5051→…→8000→8080 순으로 fallback.
2. **PEP 668 (externally-managed-environment)** — 시스템 Python에 pip 직접 설치 불가. `run_server.sh`가 `.venv` 자동 생성.
3. **`__MACOSX` 폴더** — Mac에서 만든 zip의 메타데이터. 학생 폴더로 오해되지 않게 unwrap 시 명시적 제외.
4. **이중 중첩 `data/data/...`** — 단일 wrapper 폴더 자동 unwrap 로직이 `__MACOSX` 때문에 fail. `_data_root()` 가 fallback 처리.
5. **한글 파일명** — `평가기준.md` 다운로드 시 `Content-Disposition: attachment; filename*=UTF-8''...` 형식 필요. Flask 의 `send_from_directory(download_name=...)` 로 자동 처리.
6. **Claude Code stream-json 옵션** — `-p` 와 `--output-format stream-json` 을 같이 쓰려면 **반드시 `--verbose` 필요** (안 그러면 즉시 종료).
7. **학생 폴더에 이름 없음** — 도담 zip 형식이 `학번/` 단독일 수 있음. `이름(학번@dodam.hs.kr)/` 와 모두 지원하도록 폴더명 파싱 + 리포트 파일명 두 가지 형식 허용.
8. **MD 없이 HTML만 생성된 상황** — Claude 가 `이름(학번).md` 단계를 빠뜨리고 HTML 만 만들면 파싱 실패. `get_results()` 가 HTML 에서 fallback 추출하도록 보강됨.
9. **`__pycache__` 보호** — Python 자동 생성 캐시. 결과 초기화 시 건드리지 않음 (다음 실행 시 자동 재생성).
10. **Flask 기본 포트 노출 확인** — `app.run(host="0.0.0.0", ...)` 로 LAN 노출. 학교 내 다른 PC에서 접속 가능.
11. **Windows BAT 파일 한글 인코딩** — Windows cmd 는 BAT 를 시스템 ANSI 코드페이지(Korean Windows = CP949)로 파싱하는데 UTF-8 BAT 안의 한글 multibyte 시퀀스가 어긋나 줄이 깨진 채로 실행됨 (`'pip'`, `'laude'` 같은 미인식 명령 에러). **해결: `run_server.bat` 은 ASCII 만 두고 모든 로직과 한글 출력은 `run_server.py` 가 담당.** 같은 이유로 sh 도 통일.

---

## 9. 개발 워크플로

- **서버 재시작 필수** — `app.py` 수정은 자동 reload 안 됨 (`debug=False`).
- **브라우저 캐시 강제 새로고침** — `templates/index.html` 수정 시 Cmd/Ctrl+Shift+R.
- **새 기능은 백엔드 → 프런트 순서** — 백엔드 엔드포인트를 먼저 만들고 `client.get(...)` 로 검증 후 UI 붙이기.
- **로컬 테스트** — `python -c "import app; client = app.app.test_client(); print(client.get('/api/...').get_json())"`.
- **샘플 데이터로 테스트** — `sample/` 의 question/criteria/answer/data 를 그대로 업로드하면 정상 채점 가능.
- **리포트 형식을 바꿀 때** — `sample/report-template.{md,html}` 을 먼저 수정하고, 다음 채점 시 Claude 가 그 형식으로 리포트를 생성하는지 확인. (Claude는 매번 reference 를 읽고 복제하는 흐름)

---

## 10. 환경 요구사항

- **Python 3.10+** (typing union `dict | None` 사용)
- **Flask** (자동 설치)
- **Claude Code CLI** — `npm install -g @anthropic-ai/claude-code`
- **macOS / Linux / Windows** — 모두 지원 (Windows 는 `run_server.bat`)

---

## 11. 확장 시 고려사항

- **학번-이름 매핑 업로드** — 학생 폴더가 학번 단독인 경우 별도 CSV 업로드를 받아 리포트에 이름 주입. `students.csv` 같은 새 카드 + `/api/upload?type=roster` 추가.
- **타임아웃 조정** — 알고리즘 문제는 5초 충분하지만, 입출력 많은 문제는 부족할 수 있음. `/api/run` 의 timeout 을 요청 파라미터화하거나 학생당 누적 한도.
- **여러 채점 동시 진행 방지** — 현재 `/api/grade` 는 동시 호출 시 두 개의 Claude 서브프로세스 spawn 가능. 락이 필요하면 모듈-수준 `threading.Lock`.
- **인증** — 현재는 LAN 안에서 누구나 접속 가능. 학교 내부망이면 충분하지만, 외부 노출 시 BasicAuth 또는 토큰 추가.
- **runner 컨트롤 자동 검증** — 채점 완료 후 모든 `reports/<학번>.html` 에서 `.runner-box` / `.runner-btn` 가 모두 들어 있는지 자동 점검. 누락된 학생 학번을 경고 표시. (지금은 CLAUDE.md §8 셀프 체크에 의존)
- **runner 컨트롤 일괄 주입** — 만에 하나 Claude 가 일부 리포트에 컨트롤을 빼먹어도 되살릴 수 있도록, `/reports/<학번>.html` 응답을 Flask 측에서 후처리해 스크립트가 없으면 자동 주입.
