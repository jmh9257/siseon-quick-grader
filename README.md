# 시선모의고사 빠른 채점: 선택과목별 등급컷·정답률 버전

## 이번 버전 반영 사항

- 등급컷을 `화법과작문`, `언어와매체` 각각 따로 관리합니다.
- 공개 등급컷은 1~4등급컷만 표시합니다.
- 관리자는 등급컷을 주관식으로 직접 입력할 수 있습니다.
- 학생들은 선택과목별 1~45번 전체 문항별 정답률을 볼 수 있습니다.
  - 화법과작문 선택자 기준 1~45번 정답률
  - 언어와매체 선택자 기준 1~45번 정답률
- 관리자 탭에서는 각 학생의 총점, 최근 모의고사 국어 등급, 공통과목 점수, 선택과목 점수를 확인할 수 있습니다.
- 관리자 데이터는 선택과목별로 구분되어 표시됩니다.

## 기존 Supabase를 이미 만들었다면

Supabase SQL Editor에서 아래 파일 내용을 한 번 실행하세요.

```text
supabase_migration_from_old_version.sql
```

## 새 Supabase 프로젝트라면

아래 파일 내용을 실행하세요.

```text
supabase_schema.sql
```

## secrets.toml

`.streamlit/secrets.toml`에 아래 4개가 있어야 합니다.

```toml
SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
APP_SECRET = "학생 수정 비밀번호 암호화용 긴 랜덤 문자열"
ADMIN_PASSWORD = "관리자 탭 접속 비밀번호"
```

## 실행

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## 전체 재채점 기능

관리자 탭의 `전체 재채점`에서 현재 `app.py`에 입력된 `ANSWER_KEYS`와 `POINTS` 기준으로 기존 제출 기록을 다시 채점할 수 있습니다.

사용 순서:

1. `app.py`에서 정답표 또는 배점표 수정
2. 앱 재실행
3. 관리자 탭 접속
4. `전체 재채점` 선택
5. 회차/선택과목 범위 선택
6. 확인 문구 `재채점` 입력
7. `선택한 기록 전체 재채점` 클릭

재채점하면 기존 기록의 `score`, `correct_count`, `result_json`, `updated_at`이 새 기준으로 덮어써집니다.

