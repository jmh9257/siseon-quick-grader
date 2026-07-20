import hashlib
import json
import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from supabase import create_client


# =========================
# 1. 기본 설정
# =========================

APP_TITLE = "시선모의고사 빠른 채점"

EXAM_ROUNDS = ["1회", "2회", "3회"]
ELECTIVES = ["화법과작문", "언어와매체"]
PREVIOUS_GRADES = ["입력 안 함"] + [f"{i}등급" for i in range(1, 10)]

CHOICE_TO_MARK = {
    "1": "①",
    "2": "②",
    "3": "③",
    "4": "④",
    "5": "⑤",
}
MARK_TO_CHOICE = {v: k for k, v in CHOICE_TO_MARK.items()}

COMMON_GROUPS = [
    ("1번~5번", 1, 5),
    ("6번~10번", 6, 10),
    ("11번~15번", 11, 15),
    ("16번~20번", 16, 20),
    ("21번~25번", 21, 25),
    ("26번~30번", 26, 30),
    ("31번~34번", 31, 34),
]

ELECTIVE_GROUPS = [
    ("35번~39번", 35, 39),
    ("40번~44번", 40, 44),
    ("45번", 45, 45),
]


# =========================
# 2. 정답표: 실제 정답으로 교체
# =========================

ANSWER_KEYS = {
    "1회": {
        "공통": {
            1: "⑤", 2: "④", 3: "④", 4: "②", 5: "③",
            6: "②", 7: "③", 8: "③", 9: "②", 10: "④",
            11: "①", 12: "②", 13: "②", 14: "②", 15: "⑤",
            16: "④", 17: "⑤", 18: "③", 19: "④", 20: "②",
            21: "④", 22: "④", 23: "③", 24: "③", 25: "④",
            26: "②", 27: "⑤", 28: "①", 29: "④", 30: "②",
            31: "④", 32: "④", 33: "④", 34: "③",
        },
        "화법과작문": {
            35: "②", 36: "③", 37: "④", 38: "⑤", 39: "①",
            40: "②", 41: "④", 42: "⑤", 43: "⑤", 44: "①", 45: "③",
        },
        "언어와매체": {
            35: "③", 36: "⑤", 37: "④", 38: "③", 39: "③",
            40: "⑤", 41: "④", 42: "②", 43: "⑤", 44: "④", 45: "⑤",
        },
    },

    "2회": {
        "공통": {
            1: "③", 2: "②", 3: "③", 4: "③", 5: "③",
            6: "②", 7: "①", 8: "⑤", 9: "②", 10: "⑤",
            11: "④", 12: "③", 13: "②", 14: "④", 15: "③",
            16: "⑤", 17: "⑤", 18: "④", 19: "④", 20: "②",
            21: "⑤", 22: "④", 23: "⑤", 24: "②", 25: "③",
            26: "③", 27: "③", 28: "③", 29: "⑤", 30: "②",
            31: "④", 32: "③", 33: "④", 34: "③",
        },
        "화법과작문": {
            35: "③", 36: "③", 37: "①", 38: "④", 39: "④",
            40: "②", 41: "⑤", 42: "④", 43: "③", 44: "①", 45: "⑤",
        },
        "언어와매체": {
            35: "③", 36: "④", 37: "④", 38: "⑤", 39: "③",
            40: "⑤", 41: "③", 42: "④", 43: "①", 44: "④", 45: "⑤",
        },
    },

    "3회": {
        "공통": {
            1: "⑤", 2: "③", 3: "⑤", 4: "⑤", 5: "④",
            6: "③", 7: "④", 8: "⑤", 9: "④", 10: "③",
            11: "①", 12: "④", 13: "①", 14: "⑤", 15: "③",
            16: "④", 17: "③", 18: "⑤", 19: "③", 20: "⑤",
            21: "②", 22: "③", 23: "④", 24: "②", 25: "③",
            26: "⑤", 27: "④", 28: "②", 29: "④", 30: "②",
            31: "②", 32: "④", 33: "③", 34: "⑤",
        },
        "화법과작문": {
            35: "④", 36: "①", 37: "③", 38: "③", 39: "④",
            40: "④", 41: "①", 42: "⑤", 43: "④", 44: "④", 45: "④",
        },
        "언어와매체": {
            35: "④", 36: "④", 37: "②", 38: "⑤", 39: "③",
            40: "④", 41: "④", 42: "③", 43: "③", 44: "②", 45: "④",
        },
    },
}
# =========================
# 3. 배점: 실제 배점으로 교체
# =========================

POINTS = {
    "1회": {
        "공통": {
            1: 2, 2: 2, 3: 3, 4: 2, 5: 2,
            6: 2, 7: 2, 8: 3, 9: 2, 10: 2,
            11: 2, 12: 2, 13: 3, 14: 2, 15: 2,
            16: 3, 17: 2, 18: 2, 19: 2, 20: 2,
            21: 3, 22: 2, 23: 2, 24: 2, 25: 2,
            26: 2, 27: 3, 28: 2, 29: 2, 30: 2,
            31: 3, 32: 2, 33: 2, 34: 3,
        },
        "화법과작문": {
            35: 2, 36: 2, 37: 2, 38: 2, 39: 2,
            40: 3, 41: 2, 42: 2, 43: 2, 44: 2, 45: 3,
        },
        "언어와매체": {
            35: 2, 36: 2, 37: 2, 38: 3, 39: 2,
            40: 2, 41: 2, 42: 2, 43: 2, 44: 2, 45: 3,
        },
    },

    "2회": {
        "공통": {
            1: 2, 2: 2, 3: 3, 4: 2, 5: 2,
            6: 2, 7: 2, 8: 3, 9: 2, 10: 2,
            11: 2, 12: 3, 13: 2, 14: 2, 15: 2,
            16: 2, 17: 3, 18: 2, 19: 2, 20: 2,
            21: 3, 22: 2, 23: 2, 24: 2, 25: 2,
            26: 2, 27: 3, 28: 2, 29: 2, 30: 2,
            31: 3, 32: 2, 33: 2, 34: 3,
        },
        "화법과작문": {
            35: 2, 36: 2, 37: 2, 38: 2, 39: 2,
            40: 3, 41: 2, 42: 2, 43: 2, 44: 2, 45: 3,
        },
        "언어와매체": {
            35: 2, 36: 3, 37: 2, 38: 2, 39: 2,
            40: 2, 41: 2, 42: 2, 43: 2, 44: 3, 45: 2,
        },
    },

    "3회": {
        "공통": {
            1: 2, 2: 2, 3: 3, 4: 2, 5: 2,
            6: 2, 7: 2, 8: 3, 9: 2, 10: 2,
            11: 2, 12: 3, 13: 2, 14: 2, 15: 2,
            16: 2, 17: 3, 18: 2, 19: 2, 20: 2,
            21: 3, 22: 2, 23: 2, 24: 3, 25: 2,
            26: 2, 27: 2, 28: 2, 29: 2, 30: 3,
            31: 2, 32: 2, 33: 2, 34: 3,
        },
        "화법과작문": {
            35: 2, 36: 2, 37: 2, 38: 2, 39: 2,
            40: 3, 41: 2, 42: 2, 43: 2, 44: 2, 45: 3,
        },
        "언어와매체": {
            35: 2, 36: 2, 37: 2, 38: 2, 39: 3,
            40: 2, 41: 2, 42: 2, 43: 3, 44: 2, 45: 2,
        },
    },
}

# =========================
# 4. Supabase / 비밀번호
# =========================

@st.cache_resource
def get_supabase_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError:
        st.error(
            "Supabase 연결 정보가 없습니다. `.streamlit/secrets.toml`에 "
            "`SUPABASE_URL`, `SUPABASE_KEY`, `APP_SECRET`, `ADMIN_PASSWORD`를 설정하세요."
        )
        st.stop()
    return create_client(url, key)


def get_secret(name):
    try:
        return st.secrets[name]
    except KeyError:
        st.error(f"`{name}`이 설정되어 있지 않습니다.")
        st.stop()


def make_edit_code_hash(nickname, exam_round, edit_code):
    raw = f"{get_secret('APP_SECRET')}::{nickname.strip()}::{exam_round}::{edit_code.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# =========================
# 5. DB 함수
# =========================

def fetch_submission(nickname, exam_round):
    sb = get_supabase_client()
    res = (
        sb.table("submissions")
        .select("*")
        .eq("nickname", nickname.strip())
        .eq("exam_round", exam_round)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else None


def insert_submission(payload):
    return get_supabase_client().table("submissions").insert(payload).execute()


def update_submission(record_id, payload):
    return get_supabase_client().table("submissions").update(payload).eq("id", record_id).execute()


def fetch_records_by_nickname(nickname):
    res = (
        get_supabase_client()
        .table("submissions")
        .select("id,nickname,exam_round,elective,previous_korean_grade,score,correct_count,total_count,created_at,updated_at")
        .eq("nickname", nickname.strip())
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def fetch_record_detail(record_id):
    res = (
        get_supabase_client()
        .table("submissions")
        .select("*")
        .eq("id", record_id)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else None


def fetch_all_records(exam_round=None, elective=None):
    query = get_supabase_client().table("submissions").select("*")
    if exam_round:
        query = query.eq("exam_round", exam_round)
    if elective:
        query = query.eq("elective", elective)
    res = query.order("created_at", desc=True).execute()
    return res.data or []


def fetch_grade_cut(exam_round, elective):
    res = (
        get_supabase_client()
        .table("grade_cuts_by_elective")
        .select("*")
        .eq("exam_round", exam_round)
        .eq("elective", elective)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else None


def upsert_grade_cut(payload):
    return (
        get_supabase_client()
        .table("grade_cuts_by_elective")
        .upsert(payload, on_conflict="exam_round,elective")
        .execute()
    )


# =========================
# 6. 채점 관련 함수
# =========================

def clean_answer_text(text):
    return re.sub(r"[^1-5]", "", text or "")


def parse_group_inputs(raw_inputs, groups):
    answers = {}
    errors = []

    for label, start, end in groups:
        expected_len = end - start + 1
        cleaned = clean_answer_text(raw_inputs.get(label, ""))

        if len(cleaned) != expected_len:
            errors.append(f"{label}: {expected_len}개의 숫자를 입력해야 합니다. 현재 입력: {len(cleaned)}개")
            continue

        for offset, digit in enumerate(cleaned):
            answers[start + offset] = CHOICE_TO_MARK[digit]

    return answers, errors


def normalize_json_dict(obj):
    if isinstance(obj, str):
        obj = json.loads(obj)
    return {int(k): v for k, v in (obj or {}).items()}


def answers_to_group_strings(answers, groups):
    answers = normalize_json_dict(answers)
    group_strings = {}

    for label, start, end in groups:
        group_strings[label] = "".join(MARK_TO_CHOICE.get(answers.get(q_no, ""), "") for q_no in range(start, end + 1))

    return group_strings


def get_point(exam_round, elective, q_no):
    if 1 <= q_no <= 34:
        return POINTS[exam_round]["공통"][q_no]
    return POINTS[exam_round][elective][q_no]


def grade_answers(exam_round, elective, answers):
    answer_key = {}
    answer_key.update(ANSWER_KEYS[exam_round]["공통"])
    answer_key.update(ANSWER_KEYS[exam_round][elective])

    result = {}
    score = 0
    correct_count = 0

    for q_no in range(1, 46):
        student_answer = answers.get(q_no)
        correct_answer = answer_key[q_no]
        point = get_point(exam_round, elective, q_no)
        is_correct = student_answer == correct_answer

        if is_correct:
            score += point
            correct_count += 1

        result[q_no] = {
            "학생답": student_answer,
            "정답": correct_answer,
            "정오": "O" if is_correct else "X",
            "배점": point,
            "획득점수": point if is_correct else 0,
        }

    return score, correct_count, 45, result


def calculate_part_scores(result):
    result = normalize_json_dict(result)
    common_score = 0
    elective_score = 0

    for q_no, info in result.items():
        earned = int(info.get("획득점수", 0))
        if 1 <= q_no <= 34:
            common_score += earned
        elif 35 <= q_no <= 45:
            elective_score += earned

    return common_score, elective_score


def result_to_dataframe(result):
    result = normalize_json_dict(result)
    rows = []
    for q_no, info in sorted(result.items()):
        rows.append({
            "문항": q_no,
            "학생답": info["학생답"],
            "정답": info["정답"],
            "정오": info["정오"],
            "배점": info["배점"],
            "획득점수": info["획득점수"],
        })
    return pd.DataFrame(rows)


def make_payload(nickname, exam_round, elective, previous_grade, edit_code, answers, result, score, correct_count, total_count):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "nickname": nickname.strip(),
        "exam_round": exam_round,
        "elective": elective,
        "previous_korean_grade": None if previous_grade == "입력 안 함" else previous_grade,
        "score": int(score),
        "correct_count": int(correct_count),
        "total_count": int(total_count),
        "answers_json": {str(k): v for k, v in answers.items()},
        "result_json": {str(k): v for k, v in result.items()},
        "edit_code_hash": make_edit_code_hash(nickname, exam_round, edit_code),
        "created_at": now,
        "updated_at": now,
    }


def render_answer_inputs(prefix, default_answers=None):
    default_answers = default_answers or {}
    default_common = answers_to_group_strings(default_answers, COMMON_GROUPS) if default_answers else {}
    default_elective = answers_to_group_strings(default_answers, ELECTIVE_GROUPS) if default_answers else {}

    st.markdown("---")
    st.markdown("### 공통과목 1~34번")
    st.info("예: 1번~5번 답이 ①②③④⑤이면 `12345` 입력")

    common_inputs = {}
    common_cols = st.columns(4)
    for idx, (label, start, end) in enumerate(COMMON_GROUPS):
        with common_cols[idx % 4]:
            common_inputs[label] = st.text_input(
                label,
                value=default_common.get(label, ""),
                max_chars=end - start + 1,
                placeholder="".join(["1"] * (end - start + 1)),
                key=f"{prefix}_common_{label}",
            )

    st.markdown("---")
    st.markdown("### 선택과목 35~45번")

    elective_inputs = {}
    elective_cols = st.columns(3)
    for idx, (label, start, end) in enumerate(ELECTIVE_GROUPS):
        with elective_cols[idx % 3]:
            elective_inputs[label] = st.text_input(
                label,
                value=default_elective.get(label, ""),
                max_chars=end - start + 1,
                placeholder="".join(["1"] * (end - start + 1)),
                key=f"{prefix}_elective_{label}",
            )

    return common_inputs, elective_inputs


def calculate_item_accuracy(records, question_numbers):
    rows = []

    for q_no in question_numbers:
        total = 0
        correct = 0
        for record in records:
            result = normalize_json_dict(record.get("result_json", {}))
            if q_no in result:
                total += 1
                if result[q_no].get("정오") == "O":
                    correct += 1

        rate = round(correct / total * 100, 1) if total else 0
        rows.append({
            "문항": q_no,
            "응시자 수": total,
            "정답자 수": correct,
            "정답률(%)": rate,
            "오답률(%)": round(100 - rate, 1) if total else 0,
        })

    return pd.DataFrame(rows)


def records_to_admin_dataframe(records):
    rows = []
    for record in records:
        common_score, elective_score = calculate_part_scores(record.get("result_json", {}))

        row = {
            "id": record.get("id"),
            "닉네임": record.get("nickname"),
            "회차": record.get("exam_round"),
            "선택과목": record.get("elective"),
            "총점": record.get("score"),
            "최근 모의고사 국어 등급": record.get("previous_korean_grade") or "",
            "공통과목 점수": common_score,
            "선택과목 점수": elective_score,
            "정답 수": record.get("correct_count"),
            "전체 문항 수": record.get("total_count"),
            "제출일": record.get("created_at"),
            "수정일": record.get("updated_at"),
        }
        answers = normalize_json_dict(record.get("answers_json", {}))
        result = normalize_json_dict(record.get("result_json", {}))
        for q_no in range(1, 46):
            row[f"{q_no}번 학생답"] = answers.get(q_no, "")
            row[f"{q_no}번 정오"] = result.get(q_no, {}).get("정오", "")
        rows.append(row)
    return pd.DataFrame(rows)



def regrade_one_record(record):
    """현재 app.py의 ANSWER_KEYS와 POINTS 기준으로 한 기록을 다시 채점합니다."""
    answers = normalize_json_dict(record.get("answers_json", {}))
    exam_round = record.get("exam_round")
    elective = record.get("elective")

    score, correct_count, total_count, result = grade_answers(exam_round, elective, answers)
    common_score, elective_score = calculate_part_scores(result)

    payload = {
        "score": int(score),
        "correct_count": int(correct_count),
        "total_count": int(total_count),
        "result_json": {str(k): v for k, v in result.items()},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    update_submission(record["id"], payload)

    return {
        "id": record.get("id"),
        "닉네임": record.get("nickname"),
        "회차": exam_round,
        "선택과목": elective,
        "재채점 총점": score,
        "공통과목 점수": common_score,
        "선택과목 점수": elective_score,
        "정답 수": correct_count,
    }


def regrade_records(records):
    rows = []
    for record in records:
        rows.append(regrade_one_record(record))
    return pd.DataFrame(rows)

def has_cut_values(grade_cut):
    if not grade_cut:
        return False
    return any(bool(grade_cut.get(f"grade_{i}_cut")) for i in range(1, 5))


def render_grade_cut_box(exam_round, elective):
    grade_cut = fetch_grade_cut(exam_round, elective)
    message = "등급컷 산출 중입니다."
    if grade_cut and grade_cut.get("status_message"):
        message = grade_cut["status_message"]

    st.info(message)

    if has_cut_values(grade_cut):
        rows = [{"등급": f"{i}등급", "등급컷": grade_cut.get(f"grade_{i}_cut") or "-"} for i in range(1, 5)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if grade_cut.get("public_note"):
            st.caption(grade_cut["public_note"])


# =========================
# 7. 화면
# =========================

st.set_page_config(page_title=APP_TITLE, page_icon="📝", layout="wide")
st.title(APP_TITLE)
st.caption("구간별 답안을 숫자로 입력하면 자동 채점됩니다.\n①②③④⑤는 각각 1, 2, 3, 4, 5로 입력하세요.")

IS_ADMIN_URL = st.query_params.get("admin") == "1"

if IS_ADMIN_URL:
    tab_submit, tab_edit, tab_records, tab_public_stats, tab_admin = st.tabs(
        ["답안 제출", "답안 수정", "내 기록 조회", "등급컷·정답률", "관리자"]
    )
else:
    tab_submit, tab_edit, tab_records, tab_public_stats = st.tabs(
        ["답안 제출", "답안 수정", "내 기록 조회", "등급컷·정답률"]
    )
with tab_submit:
    st.subheader("답안 제출")

    with st.form("submit_form"):
        c1, c2, c3, c4 = st.columns([1.1, 0.8, 1.1, 1.2])
        with c1:
            nickname = st.text_input("닉네임", placeholder="예: 국어황")
        with c2:
            exam_round = st.selectbox("시험 회차", EXAM_ROUNDS, key="submit_round")
        with c3:
            elective = st.radio("선택 과목", ELECTIVES, horizontal=True, key="submit_elective")
        with c4:
            edit_code = st.text_input("수정 비밀번호", type="password", placeholder="답안을 수정할 때 필요")

        previous_grade = st.selectbox(
            "최근 모의고사 국어 등급(정확한 등급컷 산출에 큰 도움이 됩니다.)",
            PREVIOUS_GRADES,
            key="submit_previous_grade",
        )

        common_inputs, elective_inputs = render_answer_inputs("submit")
        submitted = st.form_submit_button("채점하기")

    if submitted:
        if not nickname.strip():
            st.error("닉네임을 입력해 주세요.")
        elif not edit_code.strip():
            st.error("수정 비밀번호를 입력해 주세요.")
        elif fetch_submission(nickname, exam_round):
            st.warning(f"`{nickname}` 닉네임으로 `{exam_round}`에 이미 제출한 기록이 있습니다. `답안 수정` 탭을 이용하세요.")
        else:
            common_answers, common_errors = parse_group_inputs(common_inputs, COMMON_GROUPS)
            elective_answers, elective_errors = parse_group_inputs(elective_inputs, ELECTIVE_GROUPS)
            errors = common_errors + elective_errors

            if errors:
                st.error("입력값을 확인해 주세요.")
                for error in errors:
                    st.write(f"- {error}")
            else:
                answers = {**common_answers, **elective_answers}
                score, correct_count, total_count, result = grade_answers(exam_round, elective, answers)
                insert_submission(make_payload(nickname, exam_round, elective, previous_grade, edit_code, answers, result, score, correct_count, total_count))

                common_score, elective_score = calculate_part_scores(result)

                st.success("채점이 완료되었습니다. 기록이 저장되었습니다.")
                m1, m2, m3 = st.columns(3)
                m1.metric("총점", f"{score}점")
                m2.metric("공통과목 점수", f"{common_score}점")
                m3.metric("선택과목 점수", f"{elective_score}점")
                st.metric("정답 개수", f"{correct_count}/{total_count}")

                df = result_to_dataframe(result)
                st.dataframe(df, use_container_width=True, hide_index=True)
                wrong_df = df[df["정오"] == "X"]
                if not wrong_df.empty:
                    st.markdown("### 오답 문항")
                    st.dataframe(wrong_df, use_container_width=True, hide_index=True)

with tab_edit:
    st.subheader("답안 수정")
    st.caption("처음 제출할 때 입력한 수정 비밀번호가 있어야 답안을 수정할 수 있습니다.")

    with st.form("load_edit_form"):
        c1, c2, c3 = st.columns([1.2, 0.8, 1.2])
        with c1:
            edit_nickname = st.text_input("닉네임", placeholder="예: 국어황", key="edit_nickname")
        with c2:
            edit_round = st.selectbox("시험 회차", EXAM_ROUNDS, key="edit_round")
        with c3:
            edit_code_for_load = st.text_input("수정 비밀번호", type="password", key="edit_code_for_load")
        load_clicked = st.form_submit_button("기존 답안 불러오기")

    if load_clicked:
        record = fetch_submission(edit_nickname, edit_round) if edit_nickname.strip() else None
        if not edit_nickname.strip():
            st.error("닉네임을 입력해 주세요.")
        elif not edit_code_for_load.strip():
            st.error("수정 비밀번호를 입력해 주세요.")
        elif not record:
            st.warning("해당 닉네임과 회차의 제출 기록이 없습니다.")
        elif make_edit_code_hash(edit_nickname, edit_round, edit_code_for_load) != record.get("edit_code_hash"):
            st.error("수정 비밀번호가 일치하지 않습니다.")
        else:
            st.session_state["loaded_edit_record"] = record
            st.success("기존 답안을 불러왔습니다.")

    loaded_record = st.session_state.get("loaded_edit_record")
    if loaded_record:
        st.markdown("---")
        st.markdown(f"### 불러온 기록: `{loaded_record['nickname']}` / `{loaded_record['exam_round']}` / 기존 점수 `{loaded_record['score']}점`")

        old_answers = normalize_json_dict(loaded_record.get("answers_json", {}))
        old_previous_grade = loaded_record.get("previous_korean_grade") or "입력 안 함"

        with st.form("update_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_elective = st.radio(
                    "선택 과목",
                    ELECTIVES,
                    index=ELECTIVES.index(loaded_record["elective"]),
                    horizontal=True,
                    key="new_elective",
                )
            with c2:
                new_previous_grade = st.selectbox(
                    "최근 모의고사 국어 등급(정확한 등급컷 산출에 큰 도움이 됩니다.)",
                    PREVIOUS_GRADES,
                    index=PREVIOUS_GRADES.index(old_previous_grade) if old_previous_grade in PREVIOUS_GRADES else 0,
                    key="new_previous_grade",
                )

            edit_common_inputs, edit_elective_inputs = render_answer_inputs("edit_loaded", old_answers)
            update_clicked = st.form_submit_button("수정 후 다시 채점하기")

        if update_clicked:
            common_answers, common_errors = parse_group_inputs(edit_common_inputs, COMMON_GROUPS)
            elective_answers, elective_errors = parse_group_inputs(edit_elective_inputs, ELECTIVE_GROUPS)
            errors = common_errors + elective_errors

            if errors:
                st.error("입력값을 확인해 주세요.")
                for error in errors:
                    st.write(f"- {error}")
            else:
                updated_answers = {**common_answers, **elective_answers}
                score, correct_count, total_count, result = grade_answers(loaded_record["exam_round"], new_elective, updated_answers)
                update_submission(
                    loaded_record["id"],
                    {
                        "elective": new_elective,
                        "previous_korean_grade": None if new_previous_grade == "입력 안 함" else new_previous_grade,
                        "score": int(score),
                        "correct_count": int(correct_count),
                        "total_count": int(total_count),
                        "answers_json": {str(k): v for k, v in updated_answers.items()},
                        "result_json": {str(k): v for k, v in result.items()},
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

                common_score, elective_score = calculate_part_scores(result)

                st.success("답안이 수정되었고, 다시 채점되었습니다.")
                m1, m2, m3 = st.columns(3)
                m1.metric("새 총점", f"{score}점")
                m2.metric("새 공통과목 점수", f"{common_score}점")
                m3.metric("새 선택과목 점수", f"{elective_score}점")
                st.metric("새 정답 개수", f"{correct_count}/{total_count}")
                st.dataframe(result_to_dataframe(result), use_container_width=True, hide_index=True)
                st.session_state["loaded_edit_record"] = fetch_submission(loaded_record["nickname"], loaded_record["exam_round"])

with tab_records:
    st.subheader("내 기록 조회")
    search_nickname = st.text_input("조회할 닉네임", placeholder="예: 국어황", key="search_nickname")

    if st.button("기록 조회"):
        if not search_nickname.strip():
            st.error("닉네임을 입력해 주세요.")
        else:
            records = fetch_records_by_nickname(search_nickname)
            if not records:
                st.warning("해당 닉네임의 채점 기록이 없습니다.")
            else:
                records_df = pd.DataFrame(records)
                st.dataframe(records_df, use_container_width=True, hide_index=True)

    if search_nickname.strip():
        records = fetch_records_by_nickname(search_nickname)
        if records:
            options = {f"{r['exam_round']} / {r['elective']} / {r['score']}점 / {r.get('updated_at','')}": r["id"] for r in records}
            selected = st.selectbox("상세 조회할 기록", list(options.keys()))
            detail = fetch_record_detail(options[selected])
            if detail:
                st.markdown("### 상세 결과")
                common_score, elective_score = calculate_part_scores(detail["result_json"])
                m1, m2, m3 = st.columns(3)
                m1.metric("총점", f"{detail['score']}점")
                m2.metric("공통과목 점수", f"{common_score}점")
                m3.metric("선택과목 점수", f"{elective_score}점")
                st.dataframe(result_to_dataframe(detail["result_json"]), use_container_width=True, hide_index=True)

with tab_public_stats:
    st.subheader("등급컷·문항별 정답률")
    st.caption("등급컷은 선택과목별로 따로 공개됩니다. 문항별 정답률도 선택과목 응시자 집단별 1~45번 전체를 기준으로 표시됩니다.")

    c1, c2 = st.columns(2)
    with c1:
        public_round = st.selectbox("회차 선택", EXAM_ROUNDS, key="public_round")
    with c2:
        public_elective = st.selectbox("선택과목 선택", ELECTIVES, key="public_elective")

    st.markdown(f"### {public_round} {public_elective} 등급컷")
    render_grade_cut_box(public_round, public_elective)

    st.markdown(f"### {public_round} {public_elective} 문항별 정답률")
    public_records = fetch_all_records(exam_round=public_round, elective=public_elective)
    if not public_records:
        st.warning("아직 해당 선택과목의 제출 기록이 없습니다.")
    else:
        item_df = calculate_item_accuracy(public_records, list(range(1, 46)))
        student_item_df = item_df[["문항", "정답률(%)", "오답률(%)"]]
        st.dataframe(student_item_df, use_container_width=True, hide_index=True)

        st.markdown("### 오답률 높은 문항 TOP 5")
        student_difficult_df = (
            student_item_df
            .sort_values(["정답률(%)", "문항"], ascending=[True, True])
            .head(5)
        )
        st.dataframe(student_difficult_df, use_container_width=True, hide_index=True)

if IS_ADMIN_URL:
    with tab_admin:
        st.subheader("관리자")
        st.caption("학생 채점 원자료, 선택과목별 점수 분리, 등급컷 수동 입력은 관리자만 볼 수 있습니다.")
        admin_password = st.text_input("관리자 비밀번호", type="password", key="admin_password")

        if not admin_password:
            st.warning("관리자 비밀번호를 입력하세요.")
        elif admin_password != get_secret("ADMIN_PASSWORD"):
            st.error("관리자 비밀번호가 일치하지 않습니다.")
        else:
            st.success("관리자 인증 완료")
            admin_cut_tab, admin_data_tab, admin_regrade_tab = st.tabs(["등급컷 수동 입력", "학생 데이터", "전체 재채점"])

            with admin_cut_tab:
                st.markdown("### 선택과목별 등급컷 수동 입력")
                c1, c2 = st.columns(2)
                with c1:
                    cut_round = st.selectbox("등급컷 입력 회차", EXAM_ROUNDS, key="admin_cut_round")
                with c2:
                    cut_elective = st.selectbox("등급컷 입력 선택과목", ELECTIVES, key="admin_cut_elective")

                current_cut = fetch_grade_cut(cut_round, cut_elective) or {}

                with st.form("grade_cut_form"):
                    status_message = st.text_input("공개 안내 문구", value=current_cut.get("status_message") or "등급컷 산출 중입니다.")
                    cols = st.columns(4)
                    grade_values = {}
                    for i in range(1, 5):
                        with cols[i - 1]:
                            grade_values[f"grade_{i}_cut"] = st.text_input(
                                f"{i}등급컷",
                                value=current_cut.get(f"grade_{i}_cut") or "",
                                key=f"grade_{i}_cut",
                                placeholder="예: 92점",
                            )
                    public_note = st.text_area("공개 비고", value=current_cut.get("public_note") or "")
                    save_cut = st.form_submit_button("등급컷 저장")

                if save_cut:
                    payload = {
                        "exam_round": cut_round,
                        "elective": cut_elective,
                        "status_message": status_message.strip() or "등급컷 산출 중입니다.",
                        "public_note": public_note.strip() or None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    payload.update({k: (v.strip() or None) for k, v in grade_values.items()})
                    upsert_grade_cut(payload)
                    st.success(f"{cut_round} {cut_elective} 등급컷 안내가 저장되었습니다.")

            with admin_data_tab:
                st.markdown("### 학생 데이터")
                st.caption("총점 옆에 최근 모의고사 국어 등급, 공통과목 점수, 선택과목 점수를 함께 표시합니다.")

                f1, f2 = st.columns(2)
                with f1:
                    data_round = st.selectbox("회차 필터", ["전체"] + EXAM_ROUNDS, key="admin_data_round")
                with f2:
                    data_elective = st.selectbox("선택과목 필터", ["전체"] + ELECTIVES, key="admin_data_elective")

                records = fetch_all_records(
                    exam_round=None if data_round == "전체" else data_round,
                    elective=None if data_elective == "전체" else data_elective,
                )

                if not records:
                    st.warning("조건에 맞는 제출 기록이 없습니다.")
                else:
                    if data_elective == "전체":
                        for elective_name in ELECTIVES:
                            elective_records = [r for r in records if r.get("elective") == elective_name]
                            st.markdown(f"### {elective_name} 선택자")
                            if not elective_records:
                                st.info(f"{elective_name} 선택자 기록이 없습니다.")
                                continue

                            admin_df = records_to_admin_dataframe(elective_records)
                            st.dataframe(admin_df, use_container_width=True, hide_index=True)
                            st.download_button(
                                f"{elective_name} 학생 데이터 CSV 다운로드",
                                data=admin_df.to_csv(index=False).encode("utf-8-sig"),
                                file_name=f"siseon_grader_{elective_name}_submissions.csv",
                                mime="text/csv",
                            )
                    else:
                        admin_df = records_to_admin_dataframe(records)
                        st.dataframe(admin_df, use_container_width=True, hide_index=True)
                        st.download_button(
                            "학생 데이터 CSV 다운로드",
                            data=admin_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="siseon_grader_submissions.csv",
                            mime="text/csv",
                        )

                    st.markdown("### 관리자용 문항별 정답률")
                    if data_elective == "전체":
                        st.caption("전체 필터에서는 선택과목별로 나누어 1~45번 정답률을 각각 표시합니다.")
                        for elective_name in ELECTIVES:
                            elective_records = [r for r in records if r.get("elective") == elective_name]
                            st.markdown(f"#### {elective_name} 선택자 문항별 정답률")
                            if not elective_records:
                                st.info(f"{elective_name} 선택자 기록이 없습니다.")
                                continue
                            item_df = calculate_item_accuracy(elective_records, list(range(1, 46)))
                            st.dataframe(item_df, use_container_width=True, hide_index=True)
                    else:
                        item_df = calculate_item_accuracy(records, list(range(1, 46)))
                        st.dataframe(item_df, use_container_width=True, hide_index=True)
                        st.download_button(
                            "문항별 정답률 CSV 다운로드",
                            data=item_df.to_csv(index=False).encode("utf-8-sig"),
                            file_name="siseon_grader_item_accuracy.csv",
                            mime="text/csv",
                        )

            with admin_regrade_tab:
                st.markdown("### 전체 재채점")
                st.caption(
                    "현재 app.py에 입력된 정답표(ANSWER_KEYS)와 배점표(POINTS)를 기준으로 "
                    "저장된 학생 답안을 다시 채점합니다. 정답이나 배점을 수정한 뒤 사용하세요."
                )

                r1, r2 = st.columns(2)
                with r1:
                    regrade_round = st.selectbox("재채점 회차", ["전체"] + EXAM_ROUNDS, key="regrade_round")
                with r2:
                    regrade_elective = st.selectbox("재채점 선택과목", ["전체"] + ELECTIVES, key="regrade_elective")

                target_records = fetch_all_records(
                    exam_round=None if regrade_round == "전체" else regrade_round,
                    elective=None if regrade_elective == "전체" else regrade_elective,
                )

                st.warning(
                    f"대상 기록은 {len(target_records)}건입니다. 실행하면 기존 점수, 정답 수, 문항별 정오 결과가 "
                    "현재 정답표와 배점표 기준으로 덮어써집니다."
                )

                confirm_text = st.text_input(
                    "실행하려면 아래 칸에 재채점 이라고 입력하세요.",
                    key="regrade_confirm_text",
                    placeholder="재채점",
                )

                if st.button("선택한 기록 전체 재채점", key="run_regrade_button"):
                    if confirm_text.strip() != "재채점":
                        st.error("확인 문구가 일치하지 않습니다. `재채점`이라고 입력해야 실행됩니다.")
                    elif not target_records:
                        st.warning("재채점할 기록이 없습니다.")
                    else:
                        result_df = regrade_records(target_records)
                        st.success(f"{len(target_records)}건을 현재 정답표와 배점표 기준으로 다시 채점했습니다.")
                        st.dataframe(result_df, use_container_width=True, hide_index=True)

                        csv = result_df.to_csv(index=False).encode("utf-8-sig")
                        st.download_button(
                            "재채점 결과 CSV 다운로드",
                            data=csv,
                            file_name="siseon_regrade_result.csv",
                            mime="text/csv",
                        )

