# 채점 작업 규약 (Claude 전용)

이 파일은 Claude Code가 자동으로 읽는 프로젝트 규약입니다.
사용자가 "채점해줘"라고 요청하면 **이 문서의 모든 항목을 그대로 따르세요**.
규약 위반 시 대시보드(app.py)가 결과를 인식하지 못합니다.

---

## 0. 한 줄 요약

`question.md` + `평가기준.md` + `answer/*.py` + `data/<학생>/<문제>/Project/Main.py` 를 읽어,
학생별로 코드를 실제 실행해 채점하고, **`reports/` 폴더에 4종 산출물**을 만든다.

---

## 1. 입력 파일

| 경로 | 내용 |
|------|------|
| `question.md` | 문제별 지시사항과 테스트케이스 (Input/Print 표) |
| `평가기준.md` | 평가 요소·배점·문제별 세부 기준. **특이사항을 반드시 반영** |
| `answer/qN.py` | 문제 N의 모범 답안 |
| `data/<이름(학번@dodam.hs.kr)>/<문제폴더>/Project/Main.py` | 학생의 답안 |

**학생/문제 폴더 식별**:
- 학생 폴더명 패턴: `이름(학번@dodam.hs.kr)` — 학번은 5자리 숫자
- 문제 폴더명에 `_1`, `_2`, … 또는 `q1`, `q2`, … 같은 숫자 토큰이 있으며 그 숫자가 문제 번호
- 폴더가 없거나 `Main.py`가 비어있으면 → 미제출(0점), 리포트에 명시

---

## 2. 출력 산출물

대시보드는 `reports/` 폴더의 파일들을 파싱해 결과 테이블을 그립니다.

### 큰 틀: 절대 빠지면 안 되는 기능 (= 학생/선생님이 기대하는 것)

리포트가 "쓸모 있다"는 건 다음이 모두 살아 있다는 뜻입니다. **이게 깨지지 않게 하는 것이 1순위.** CSS 클래스명, 색, 레이아웃, 카피 문구 같은 미세 변화는 자유롭게 해도 됩니다.

1. 학생 정보(학번, 이름이 있으면 이름)와 총점/만점이 한눈에 보임
2. 평가요소별 점수 카드 — 평가기준의 각 요소마다 만점/획득점수가 보임
3. 문제별 상세에 **(a) 학생 코드 + (b) 모범 답안 코드**가 나란히 표시됨
4. 각 문제마다 평가기준 항목별 ✓/✗ + 짧은 코멘트(=점수를 준 근거)
5. 각 문제 카드 안에서 **학생 코드를 그 자리에서 실행해볼 수 있는 컨트롤** (표준입력 박스 + 실행 버튼 + 결과 영역)
6. 미제출 문제는 "미제출"로 명확히 표시
7. 대시보드가 점수를 파싱할 수 있는 형식의 `이름(학번).md` (또는 `학번.md`)
8. 전체 학생 통합 페이지 `index.html` 과 `scores.tsv`

### Reference 파일 (그대로 복제하면 위 8가지가 자동 충족됨)

> 📐 **리포트를 만들기 전에 먼저 읽으세요:**
>
> - `sample/report-template.md` — 점수 데이터 MD 의 표준 형식
> - `sample/report-template.html` — 학생 리포트 HTML 의 표준 구조
>
> 학생별로 바뀌는 건 **데이터(이름·학번·점수·코드·테스트 결과)** 뿐입니다.

### 어겨도 되는 것 / 절대 어기면 안 되는 것

| 변형 자유 | 변형 금지 (어기면 큰 틀이 깨짐) |
|----------|----------------------------|
| 색·폰트·여백·카드 디자인 | MD 의 `## 총점` 표 컬럼 순서와 `**합계**` 행 형식 (대시보드 정규식 파서가 의존) |
| 카피 문구·이모지·격려 메시지 | 평가요소 이름 — `평가기준.md` 표기와 글자 그대로 일치해야 함 |
| 카드 배치 순서·요소 추가 | runner 스크립트의 셀렉터(`.q-card`, `.code-grid pre`, `table tbody tr td:first-child em`)와 `/api/run` POST 형식 |
| HTML 클래스명을 새로 추가 | reference 의 셀렉터를 임의로 *제거하거나 이름 변경* (그러면 실행 버튼이 동작 안 함) |

### 2-1. `reports/<이름>(<학번>).md` — 점수 데이터 (대시보드가 파싱)

학생마다 한 개. 파일명 예: `홍길동(20203).md`

> ⚠️ 만약 학생 폴더명에 이름이 없고 학번만 있다면 (예: `data/20203/...`),
> 파일명을 `학번.md` 만으로 두어도 됩니다 (예: `20203.md`). 대시보드가 둘 다 받습니다.

내부에 반드시 **`## 총점` 섹션**과 **`**합계**` 행**이 있어야 합니다.

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

### 문제 1
- 테스트케이스: 통과 / 실패 사유
- 평가요소 충족: …

(문제 1 ~ 8 모두 작성)

## 총평
- 잘한 점, 보완할 점 (2~3 문장)
```

**파싱 규칙 (반드시 지킬 것)**:
- 파일명은 `이름(학번).md` — 괄호 안은 5자리 숫자만
- `## 총점` 다음 표의 행은 `| 평가요소이름 | 만점 | 점수 |` (앞뒤 공백 OK)
- 합계 행은 정확히 `| **합계** | **<만점>** | **<점수>** |` (별표 둘로 굵게)
- 평가요소 이름에 `|`, `*` 문자 사용 금지
- 평가요소는 **`평가기준.md`에 등장한 순서/이름 그대로** (글자 단 한 자라도 다르면 안됨)

### 2-2. `reports/<학번>.html` — 학생용 개별 리포트

학생/선생님이 브라우저에서 보는 페이지. 파일명 예: `20203.html`

포함 요소:
- 헤더: 이름, 학번, 총점/만점, 등급(A/B/C 같은 시각적 표시)
- 평가요소별 점수 카드 (점수/만점, 달성률 색상 표시)
- 문제별 상세
  - 문제 텍스트 요약
  - 학생 코드 (코드블록)
  - 테스트케이스별 실제 입출력 vs 기대 출력
  - 평가기준 항목별 ✓/✗ 와 짧은 코멘트
- 총평 / 격려 메시지
- **각 문제 카드 아래에 학생 코드 실행 컨트롤** (아래 §2-2-A 사양 참고, 모든 학생 리포트에 빠짐없이 포함)

스타일은 **인라인 `<style>`**, 외부 CDN 사용 금지(오프라인 재현성).
배경 흰색, 본문 네이비/슬레이트 톤, 점수에 따라 초록/주황/빨강 사용.
모바일 반응형. UTF-8.

#### 2-2-A. 인라인 코드 실행 컨트롤 (필수, 모든 리포트)

학생 코드를 그 자리에서 다시 실행해볼 수 있도록, 각 문제 카드 안에 표준입력 박스 + 실행 버튼 + 결과 영역을 포함시킨다. 단순 정적 페이지가 아니라 Flask 서버(`/api/run`)에 fetch 하는 인터랙티브 요소이며, **iframe / 새 탭 / 같은 호스트 직접 열기** 모두에서 동작한다 (동일 출처).

**동작 요건**

- 각 문제 카드(`.q-card`) 마다 컨트롤 1개씩 자동 주입
- 학생 코드는 카드 안의 `.code-grid pre` 중 첫 번째 (= 학생 코드) 의 `textContent` 사용
- 표준입력 박스는 `question.md`의 첫 테스트케이스 input 으로 자동 채움 (없으면 빈 문자열)
- "▶ 학생 코드 실행" 버튼 클릭 또는 입력 박스에서 **Ctrl/⌘+Enter** 시 실행
- POST `/api/run` body: `{ "code": "<학생코드>", "input": "<표준입력>" }`
- 응답 `{ ok: true, output: "..." }` → 결과 영역에 표시
- 응답 `{ ok: false, error: "..." }` → 결과 영역에 빨간 left-border + ❌ 메시지
- timeout 5초는 서버에서 처리됨 — 클라이언트는 그저 결과 표시
- 미제출 카드(코드 없음)는 컨트롤 주입 스킵

**스타일 (다크 테마 리포트 기준 — 인라인 `<style>` 끝에 추가)**

```css
.runner-box  { margin-top:14px; padding-top:12px; border-top:1px dashed #334155; }
.runner-row  { display:flex; gap:8px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }
.runner-row label { font-size:11px; color:var(--muted); font-weight:600;
                    text-transform:uppercase; letter-spacing:0.05em; }
.runner-stdin {
  flex:1; min-width:120px;
  padding:6px 10px; border:1px solid #334155; border-radius:6px;
  background:#0b1224; color:var(--text);
  font-family:'JetBrains Mono','SF Mono',Monaco,Consolas,monospace; font-size:13px;
}
.runner-stdin:focus { outline:none; border-color:var(--accent); }
.runner-btn {
  padding:6px 14px; border:none; border-radius:6px;
  background:var(--accent); color:#0f172a;
  font-weight:700; cursor:pointer; font-size:13px;
}
.runner-btn:hover    { background:#93c5fd; }
.runner-btn:disabled { opacity:0.5; cursor:wait; }
.runner-status { font-size:12px; color:var(--muted); }
.runner-out {
  background:#0b1224; padding:10px 14px; border-radius:6px;
  font-family:'JetBrains Mono','SF Mono',Monaco,Consolas,monospace; font-size:13px;
  color:var(--text); white-space:pre-wrap; word-break:break-word;
  margin:0; min-height:34px; line-height:1.6;
}
.runner-out.muted { color:var(--muted); }
.runner-out.err   { border-left:3px solid var(--bad); }
```

**스크립트 (리포트 끝, `</body>` 직전에 추가 — 한 글자도 바꾸지 말 것)**

```html
<script>
/* 각 문제 카드에 "실행" 버튼을 동적으로 주입.
   첫 테스트케이스 입력값을 표준입력 박스에 자동 채움.  */
(function () {
  const cards = document.querySelectorAll('.q-card');
  cards.forEach((card) => {
    const codeBlocks = card.querySelectorAll('.code-grid pre');
    if (codeBlocks.length === 0) return;          // 미제출 카드 skip
    const studentPre = codeBlocks[0];

    // 첫 테스트케이스 입력 자동 채우기 (입력 없음이면 빈 문자열)
    let firstInput = '';
    const firstCell = card.querySelector('table tbody tr td:first-child');
    if (firstCell && !firstCell.querySelector('em')) {
      firstInput = (firstCell.textContent || '').trim();
    }

    const box = document.createElement('div');
    box.className = 'runner-box';
    box.innerHTML = `
      <div class="runner-row">
        <label>표준입력</label>
        <input type="text" class="runner-stdin" placeholder="(없음)">
        <button class="runner-btn" type="button">▶ 학생 코드 실행</button>
        <span class="runner-status"></span>
      </div>
      <pre class="runner-out muted">실행 버튼을 누르면 결과가 표시됩니다 · Ctrl/⌘+Enter 단축키 지원</pre>
    `;
    card.appendChild(box);

    const btn      = box.querySelector('.runner-btn');
    const stdinIn  = box.querySelector('.runner-stdin');
    const out      = box.querySelector('.runner-out');
    const status   = box.querySelector('.runner-status');
    stdinIn.value  = firstInput;

    async function run() {
      btn.disabled = true;
      status.textContent = '실행 중...';
      out.className = 'runner-out muted';
      out.textContent = '⏳';
      try {
        const res = await fetch('/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: studentPre.textContent, input: stdinIn.value }),
        });
        const data = await res.json();
        if (data.ok) {
          out.className = 'runner-out';
          out.textContent = data.output && data.output.length ? data.output : '(출력 없음)';
        } else {
          out.className = 'runner-out err';
          out.textContent = '❌ ' + (data.error || '실행 실패');
        }
      } catch (e) {
        out.className = 'runner-out err';
        out.textContent = '❌ 실행 실패: ' + e.message;
      }
      btn.disabled = false;
      status.textContent = '';
    }

    btn.addEventListener('click', run);
    stdinIn.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); run(); }
    });
  });
})();
</script>
```

**구조 가정 (이 스크립트가 깨지지 않으려면 리포트가 만족해야 할 조건)**

- 각 문제 카드는 `.q-card` 클래스
- 카드 안 첫 `<table>` 의 `<tbody><tr><td>` 첫 셀이 첫 테스트케이스 입력값
- 입력 없음 표시는 `<em>(없음)</em>` 형태 (쿼리 셀렉터가 `em` 으로 입력 없음 판단)
- 학생 코드 블록은 `.code-grid pre` 중 첫 번째 `<pre>` (모범답안은 두 번째)
- 미제출 문제 카드는 `.code-grid` 자체가 없거나 비어 있음

**요약**: 위의 CSS 와 스크립트는 **그대로 복사** 하는 것이 가장 안전합니다. 디자인을 바꾸고 싶으면 색·여백만 손대고, 셀렉터 이름은 건드리지 마세요. 이 부분이 한 글자라도 어긋나면 모든 학생 리포트의 실행 버튼이 한 번에 죽습니다.

### 2-3. `reports/index.html` — 전체 요약

전체 학생 점수표 + 평균/최고/최저 + 개별 리포트 링크 (`<학번>.html`).

### 2-4. `scores.tsv` — 점수 요약 (탭 구분)

구글시트에 그대로 붙여넣을 수 있게:

```
이름	학번	함수 설계 및 구현	변수 활용	재귀 알고리즘의 설계	구조 비교 및 변환	총점
홍길동	20203	8	4	6	5	23
```

(헤더 한 줄 + 학생 한 명당 한 줄)

---

## 3. 채점 절차

1. **읽기 (병렬)** — `question.md`, `평가기준.md`, `answer/*.py`, `sample/report-template.md`, `sample/report-template.html` 을 한꺼번에 읽기. 마지막 두 파일은 산출물 형식 reference 임.
2. **데이터 파악** — `평가기준.md`에서 평가요소 목록, 배점표, 문제별 항목, **특이사항**을 추출. 만점 합계 계산.
3. **학생 목록** — `data/` 하위 폴더를 훑어 `이름`/`학번`/문제별 `Main.py` 경로 정리.
4. **학생별 채점**
   - 각 문제의 학생 코드를 **실제로 실행** (Bash + python3, `timeout 5`초)
   - `question.md`의 테스트케이스 입력을 stdin으로 주고 stdout 비교
   - 출력 비교는 양 끝 공백/개행 차이는 무시 (`.strip()` 후 비교)
   - 코드를 정적으로도 읽어 평가기준 항목 충족 여부 판정
5. **점수 합산** — 평가요소별로 충족 항목 수 → 배점표에서 점수 lookup → 합계
6. **리포트 작성** — 위 4가지 산출물 생성. `reports/` 폴더가 없으면 만들기.
7. **(선택) 구글시트 입력** — 사용자가 시트 URL을 줬다면 점수 자동 입력 시도.

---

## 4. 채점 정책

- **고등학생 대상이라 후하게** — 의도가 보이면 부분 점수 인정
- **코드가 실행 안 돼도** 함수 정의·매개변수·return 등 개념 이해가 코드에 보이면 해당 항목은 인정
- **출력 형식 차이**(끝 공백/개행/공백 개수)는 무시 — 알고리즘 결과가 맞으면 통과 처리
- **시간 초과/무한루프**: 0점 처리하되 알고리즘 의도가 옳으면 부분 인정 가능
- **import 누락 등 사소한 실수**: 의도가 분명하면 인정
- **`평가기준.md`의 특이사항** (예: "문제 1 통과하면 2~3은 관대하게")은 **반드시 적용**
- **미제출 문제**: 0점, 리포트에서 "미제출"로 명시
- 동률 처리는 표준 라운딩 (반올림) — 단, 평가기준에 명시된 배점 외 점수는 만들지 말 것

---

## 5. 학생 코드 실행 시 주의사항

- 항상 **격리된 임시 파일이나 폴더 안**에서 실행 (학생 코드가 다른 파일을 만들 수 있음)
- `timeout 5` 로 무한루프 방지
- `input()` 이 여러 번 호출될 수 있으니 stdin은 줄바꿈으로 합쳐서 전달
- 한글 출력이 깨지지 않도록 `PYTHONIOENCODING=utf-8` 설정
- 표준에러는 따로 잡아서 리포트의 "실행 오류" 섹션에 요약

예시 셸:
```bash
cd /tmp/grade_<학번>_<문제>
PYTHONIOENCODING=utf-8 timeout 5 python3 Main.py <<< "<input>"
```

---

## 6. 효율성 가이드

- 모범답안과 평가기준은 **첫 학생 처리 시 한 번만 읽고 머릿속에 보관** — 반복 Read 금지
- 학생 코드는 한 번 읽고 그 학생의 모든 문제 채점 끝낼 때까지 들고 있기
- 큰 토큰을 차지하는 학생 코드 전체를 리포트에 그대로 박지 말고, **요점 부분만 발췌**
- 작업 진행을 짧은 메시지로 알리되, 학생당 한두 줄로 충분 ("20203 홍길동 채점 중…")
- 리포트 HTML/MD 작성은 **`Write` 한 방**으로 — 부분 Edit 반복 금지

---

## 7. 흔한 함정

- 파일명 인코딩: `이름(학번).md` 의 괄호는 **반각 `(`, `)`** (`（`, `）` 아님)
- 학번을 6자리로 쓰지 말 것 (정규식이 5자리 가정 — 실제로는 `\d+`라 가변이지만 데이터는 5자리)
- 평가요소 이름 띄어쓰기가 `평가기준.md`와 다르면 대시보드의 카테고리 컬럼이 비어버림
- `## 총점` 헤더 앞뒤로 빈 줄 한 줄씩 두기 (마크다운 표 인식 안정성)
- `reports/` 안에 다른 `.md` 파일을 두지 말 것 — 모두 학생 점수 데이터로 파싱됨

---

## 8. 마지막 점검 (생성 후 셀프 체크)

리포트 생성을 마치면 다음을 본인 확인:

**큰 틀(§2 의 8가지) 이 모든 리포트에서 살아 있는지** 가 통과 기준입니다.

1. `reports/<이름>(<학번>).md` 또는 `<학번>.md` 가 학생 수만큼 있는가?
2. 각 MD 안에 `## 총점` 섹션과 `**합계**` 행이 있는가? (대시보드 파싱)
3. 평가요소 이름이 `평가기준.md` 와 정확히 일치하는가?
4. `reports/<학번>.html` 가 학생 수만큼 있는가?
5. `reports/index.html` 과 `scores.tsv` 가 있는가?
6. 합계 점수 ≤ 평가기준 만점인가?
7. **모든 학생 HTML 리포트에서 학생 코드 실행 컨트롤이 정상 노출** 되는가? (스크립트와 `.runner-*` 스타일이 누락된 학생이 있으면 그 학생 리포트만 실행 버튼이 안 보임 — 일괄 검사 필요)
8. **각 문제 카드에 학생 코드 + 모범 답안 코드 + 평가기준 항목별 ✓/✗ 코멘트** 가 모두 들어 있는가? (이게 학생/선생님이 가장 많이 보는 정보)

체크가 끝나면 콘솔에 "채점 완료: N명, 평균 X.X점" 한 줄로 요약.
