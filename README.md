# 정보 수행평가 채점 대시보드

고등학생 Python 과제를 자동으로 채점하는 로컬 Flask 도구입니다.
문제·평가기준·모범답안·학생 제출물을 업로드하면 Claude Code CLI 가 학생별로 코드를 실제 실행해 채점하고, 학생용 HTML 리포트와 점수 TSV 를 만들어줍니다.

> **로컬 도구**입니다. 서버에 띄우는 용도가 아니라 본인 PC 에서 띄워 본인이 채점할 때만 사용하세요.

---

## 0. 준비물

| 항목 | 설명 |
|------|------|
| Python 3.9+ | 서버 구동 (`run_server.py` 가 venv·Flask 자동 설치) |
| Claude Code CLI | 채점 실행에 필요. 없으면 결과 보기만 가능 |
| Node.js (npm) | Claude Code CLI 를 npm 으로 설치할 때 필요 |

### Claude Code CLI 설치

```bash
npm install -g @anthropic-ai/claude-code
```

설치 후 한 번은 직접 실행해서 로그인까지 끝내두세요:

```bash
claude
```

---

## 1. 다운로드 & 실행

### macOS

```bash
git clone https://github.com/grayhh/code-grader.git
cd code-grader
chmod +x run_server.sh         # 처음 한 번만
./run_server.sh
```

> Python3 이 없다면 `brew install python` 으로 먼저 설치하세요.

### Windows

1. [Python 3 공식 사이트](https://www.python.org/downloads/) 에서 설치.
   설치 화면에서 **"Add Python to PATH"** 체크를 꼭 켜세요.
2. 저장소를 다운로드 (`Code > Download ZIP`) 받거나 `git clone`:
   ```cmd
   git clone https://github.com/grayhh/code-grader.git
   cd code-grader
   ```
3. 폴더 안의 `run_server.bat` 을 **더블클릭**하거나 명령창에서:
   ```cmd
   run_server.bat
   ```

> `python` 을 쳤을 때 Microsoft Store 가 뜬다면:
> 설정 → 앱 → 고급 앱 설정 → 앱 실행 별칭 → `python.exe` / `python3.exe` 끄기.

### 실행 후

콘솔에 다음과 같이 뜹니다:

```
📋 채점 대시보드: http://localhost:5050
```

브라우저로 열면 대시보드가 보입니다. 종료는 `Ctrl+C`.

> 5050 포트가 막혀 있으면 5051·5052·8000·8080 순으로 자동 탐색합니다.

---

## 2. 데이터 작성 방법

대시보드는 **세션(채점 회차)** 별로 입력을 받습니다. 새 세션을 만들고 아래 4가지를 업로드하면 됩니다.

### 2-1. `question.md` — 문제 지시문

문제마다 **`### 문제 N`** 헤더로 구분하고, 각 문제에 테스트케이스 표(`|Input|Print|`)를 적습니다.

```markdown
### 문제 1

> '대한'을 출력하는 함수를 선언하고 호출하세요.

- 함수 기능: '대한' 출력하기
- 메인 기능: 함수 호출하기
- 테스트케이스

  | Input | Print |
  |-------|-------|
  |       | 대한  |

---

### 문제 2
...
```

`sample/question.md` 가 그대로 쓸 수 있는 템플릿입니다.

### 2-2. `평가기준.md` — 채점 기준

평가요소를 `## 평가 요소: <이름>` 으로 선언하고, 만점 항목 수에 따른 배점표와 문제별 세부 기준을 작성합니다. 이름 글자는 점수 MD 와 한 글자도 어긋나지 않아야 합니다(자동 파싱이 이걸 기준으로 함).

```markdown
## 평가 요소: 함수 설계 및 구현
> 특이사항: 문제 1번에서 함수를 선언/호출할 수 있으면 2~3번에서는 관대하게 채점

| 만족 항목 수 | 배점 |
|-----------|----|
| 0 | 2 |
| 1 | 4 |
| 2 | 6 |
| 3 | 8 |
| 4 | 10 |

### 문제 1
- 문제 상황에 적합한 함수를 정의(선언)할 수 있음
- 정의한 함수를 호출할 수 있음
```

`sample/criteria.md` 참고.

### 2-3. `answer/` — 모범답안

문제 번호별로 `q1.py`, `q2.py`, … 한 파일씩.
대시보드 업로드 시에는 zip 으로 묶어 올려도 되고, 개별 `.py` 파일을 차례로 올려도 됩니다.

```
answer/
├── q1.py
├── q2.py
└── q3.py
```

### 2-4. `data/` — 학생 제출물 (zip)

학생 폴더 안에 문제 폴더, 그 안에 `Project/Main.py` 가 들어가는 구조입니다.

```
data/
├── 홍길동(20106@sample.kr)/
│   ├── q1/Project/Main.py
│   ├── q2/Project/Main.py
│   └── ...
├── 김영희(20107@sample.kr)/
│   ├── q1/Project/Main.py
│   └── ...
```

**폴더명 규칙**

- 학생 폴더: `이름(학번@sample.kr)` — 괄호는 반각 `(` `)`, 학번은 보통 5자리 숫자.
  학번만 (`20106/` 처럼) 둬도 동작합니다. 이름이 있으면 리포트가 더 친절해집니다.
- 문제 폴더: `q1`, `q2`, … 혹은 `1_…`, `_2_…` 처럼 숫자 토큰만 들어 있으면 됨.
- 비어 있는 `Main.py` 나 폴더가 없는 문제는 자동으로 **미제출(0점)** 처리.

이 구조 그대로 `data` 라는 폴더로 zip 압축해서 업로드하면 됩니다.

`sample/data/홍길동(20106@sample.kr)/` 가 실제 예시입니다.

---

## 3. 채점하기

1. 대시보드 좌측에서 **새 세션** 만들기 → 활성화.
2. `question.md`, `평가기준.md`, `answer/`, `data.zip` 을 차례로 업로드.
3. **채점 시작** 버튼 클릭. Claude Code CLI 가 백그라운드에서 동작하면서 학생별로 코드를 실행하고 점수를 매깁니다.
4. 완료되면 학생 목록에서 개별 리포트(`<학번>.html`) 와 점수 시트(`scores.tsv`) 를 확인.

각 학생 리포트 안에서는 학생 코드를 즉석으로 다시 실행해볼 수 있는 **▶ 학생 코드 실행** 버튼이 문제마다 들어 있습니다 (Ctrl/⌘+Enter 단축키 지원).

---

## 4. 저장 위치

- 모든 채점 회차는 `sessions/<세션ID>/` 폴더에 격리되어 저장됩니다.
- 리포트와 점수 시트는 `sessions/<세션ID>/reports/` 와 `sessions/<세션ID>/scores.tsv` 에 생성.
- `sessions/`, `reports/`, `uploads/`, `.venv/` 는 모두 `.gitignore` 처리되어 있어 커밋되지 않습니다.

---

## 5. 자주 막히는 곳

| 증상 | 해결 |
|------|------|
| `Claude Code CLI 가 설치되어 있지 않습니다` 경고 | `npm install -g @anthropic-ai/claude-code` 후 `claude` 한 번 실행해 로그인 |
| 한글이 깨져 보임 (Windows) | `run_server.bat` 으로 실행할 것 (UTF-8 자동 설정). PowerShell 직접 실행 시 `chcp 65001` 먼저 |
| 채점 결과 점수가 0 으로 파싱 | 평가요소 이름이 `평가기준.md` 와 정확히 일치하는지 확인 (공백·한 글자 차이도 안 됨) |
| 학생 리포트가 안 보임 | 학생 폴더명에 괄호가 전각(`（`,`）`)으로 들어간 경우 — 반각으로 바꿔야 함 |
| 5050 포트 충돌 | 콘솔에 안내된 대체 포트(5051 등)로 접속 |

---

## 6. 라이선스 / 면책

개인용·교육용 도구입니다. 학생 제출물(`data/`) 은 PII 가 포함될 수 있으므로 절대 공개 저장소에 커밋하지 마세요 — `.gitignore` 가 막아주지만 직접 추가하지 않도록 주의하세요.
