# B3-2 Code Helper

Git의 현재 변경 사항을 OpenAI API에 전달해 **커밋 메시지**와 **PR 제목·본문 초안**을 생성하는 Python CLI입니다. `git push`, 실제 커밋, GitHub PR 생성은 하지 않습니다. 보너스 과제는 포함하지 않았습니다.

## 요구 환경과 설치

- Python 3.10 이상, Git, OpenAI API Key
- 별도 Python 패키지 설치 불필요 (`urllib` 등 표준 라이브러리 사용)
- `main.py`가 있는 프로젝트 루트에서 실행합니다. 다른 Git 프로젝트에 적용할 때는 이 파일을 해당 프로젝트 루트에 복사하고 그곳에서 실행합니다.

```bash
git clone https://github.com/choijk136/B3-2_code-helper.git
cd B3-2_code-helper
python --version
python main.py --help
```

macOS/Linux에서는 `python`이 Python 3을 가리키지 않는다면 `python3`을 사용하세요. API Key는 [OpenAI API 대시보드](https://platform.openai.com/api-keys)에서 발급받아 환경변수로만 설정합니다. ChatGPT 구독과 API 사용 요금은 별도입니다.

```bash
# macOS / Linux (현재 터미널에서만 적용)
export AI_API_KEY="YOUR_KEY"

# Windows PowerShell (현재 창에서만 적용)
$env:AI_API_KEY="YOUR_KEY"
```

`.env` 파일이나 소스 코드에 키를 넣지 마세요. 실제 키가 들어간 터미널 출력이나 파일을 커밋하지 마세요.

## 실행 순서

변경 사항이 있는 Git 프로젝트 루트에서 실행합니다. 이 저장소를 방금 clone했으면 변경 사항이 없으므로, 예를 들어 `README.md`에 설명 한 줄을 추가해 실행해 볼 수 있습니다. **새 파일은 `git add 파일명`으로 스테이징**해야 diff 본문에 포함됩니다. 기존 파일의 스테이징 여부는 상관없습니다.

```bash
git status --short
git diff HEAD                       # 마지막 커밋 이후의 추적 파일 변경 확인
python main.py commit --safe-mode
python main.py pr --safe-mode --reason "사용자 오류 안내 개선"
```

아래 옵션은 `commit` 또는 `pr` **뒤에** 씁니다.

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `--model` | `gpt-4.1-mini` | Chat Completions 및 JSON 모드를 지원하는 모델 |
| `--temperature` | `0.2` | 결과의 변동성 조절, 0~2 |
| `--max-tokens` | `600` | 응답 토큰 상한 (`max_completion_tokens`로 전송) |
| `--reason` | 없음 | 실제 변경 이유를 사용자 맥락으로 제공 |
| `--safe-mode` | 꺼짐 | diff 최대 10개 파일, 200줄만 전송 |

```bash
python main.py commit --model gpt-4.1-mini --temperature 0.1 --max-tokens 500 --safe-mode
python main.py pr --model gpt-4.1-mini --temperature 0.2 --max-tokens 700 --safe-mode
```

한 번 실행할 때 API 요청은 **1회**입니다. 변경 사항이 없거나 API Key가 누락되면 요청하지 않습니다. `--max-tokens`를 지나치게 낮추면 JSON 응답이 잘릴 수 있습니다. 모델을 바꿀 경우 해당 모델의 Chat Completions, JSON 모드, temperature 지원 여부를 확인하세요.

## 출력 예시

다음은 형식을 보여 주는 **예시**이며 실제 API 실행 결과가 아닙니다.

```text
[INFO] Git status 수집 완료: 2개 파일 변경 감지
[INFO] Git diff 수집 완료: 전송 대상 35줄
[INFO] AI API 요청 중... (이번 실행 1회)
[DONE] 커밋 메시지 생성 완료 (API 호출 1회)
--- Commit Message ---
feat: Git 변경 사항에서 커밋 메시지 생성

- main.py에서 Git diff를 수집해 생성 요청에 포함
- API 오류를 사용자에게 안내
----------------------
[INFO] 내용을 검토한 후 직접 적용하세요.
```

```text
--- PR Title ---
feat: 변경 사항 기반 PR 초안 생성

--- PR Body ---
## Why
- 변경 사항을 리뷰어가 쉽게 파악할 설명이 필요합니다.

## What
- main.py에 PR 초안 생성 기능을 추가합니다.

## How to Test
- 변경된 파일을 만든 뒤 python main.py pr --safe-mode를 실행해 출력 구조를 확인합니다.
----------------------
```

## 처리 방식과 형식

1. `git rev-parse`로 루트를 확인하고 `git status --short`로 변경 파일 목록을 수집합니다.
2. 커밋이 있는 저장소는 `git diff HEAD`, 첫 커밋 전에는 `git diff --cached`와 `git diff`로 staged/unstaged 변경을 수집합니다. untracked 파일의 **내용**은 `git add` 전에는 diff에 나오지 않습니다.
3. 민감 파일 블록을 제외하고 알려진 키·토큰·이메일·자격 증명 값을 마스킹한 다음, 변경 이유와 원하는 JSON 형식을 프롬프트에 포함합니다. 모델 응답을 JSON으로 파싱합니다.
4. 커밋 제목은 최대 72자(50자 이내 권장), PR 제목은 최대 80자로 다듬고, PR의 `Why`, `What`, `How to Test` 각 섹션에 불릿이 있는지 검사합니다. 형식 오류는 실패로 표시합니다.

기본 정책도 `.env`, 개인키/인증 파일처럼 이름이 민감한 파일을 제외하고 대표적인 토큰·이메일 패턴을 마스킹합니다. `--safe-mode`는 여기에 파일·줄 수 제한을 추가합니다. 정규식은 모든 종류의 비밀 값을 찾을 수 없으므로 **실행 전에 diff를 직접 검토**하고 민감한 변경이 있다면 생성하지 마세요. `--reason`에도 개인정보를 입력하지 마세요. 큰 diff는 옵션 없이 실행하면 많은 토큰을 소비할 수 있으니 `--safe-mode`를 권장합니다.

API가 실패하면 HTTP 코드에 맞는 오류 안내를 출력하고 종료합니다. 생성 문구는 초안이며, 특히 변경 배경과 테스트 내용은 직접 확인한 뒤 복사해 적용하세요. 길이 초과 제목은 잘라내므로 의미가 자연스러운지도 검토해야 합니다.

## 검사

```bash
python -m unittest discover -s tests -v
```

테스트는 임시 Git 저장소에서 변경 수집을 확인하고, 가짜 HTTP 응답으로 호출 횟수·옵션·출력 형식을 검사합니다. 실제 API 호출에는 별도의 유효한 키와 네트워크 연결이 필요합니다.
