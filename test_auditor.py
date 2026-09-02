import pytest
import sqlite3
from unittest.mock import MagicMock
from auditor_bridge import fast_syntax_check, save_to_db, audit_submission, DB_PATH

# ----------------------------------------------------
# 1. ทดสอบ Fast Syntax Check (Stage 1)
# ----------------------------------------------------
def test_syntax_check_valid_python():
    valid_code = "```python\ndef add(a, b):\n    return a + b\n```"
    is_valid, err = fast_syntax_check(valid_code)
    assert is_valid is True
    assert err == ""

def test_syntax_check_invalid_python():
    invalid_code = "```python\ndef broken_func(\n    print('Missing closing parenthesis')\n```"
    is_valid, err = fast_syntax_check(invalid_code)
    assert is_valid is False
    assert "Syntax Error" in err

def test_syntax_check_plain_text():
    plain_text = "นี่คือข้อความผลลัพธ์ธรรมดา ไม่ใช่โค้ด"
    is_valid, err = fast_syntax_check(plain_text)
    assert is_valid is True
    assert err == ""

# ----------------------------------------------------
# 2. ทดสอบ Data Sink (Database)
# ----------------------------------------------------
def test_save_to_db():
    goal = "Test Unit Goal"
    content = "print('hello')"
    status = "APPROVED"
    feedback = "STATUS: APPROVED"
    duration = 0.45

    save_to_db(goal, content, status, feedback, duration)

    # ดึงข้อมูลมาตรวจสอบว่าลง DB จริงไหม
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_goal, status, duration_sec FROM audit_logs WHERE task_goal = ?", (goal,))
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == goal
    assert row[1] == "APPROVED"
    assert row[2] == 0.45

# ----------------------------------------------------
# 3. ทดสอบ Audit Submission (Stage 2-4 with Mock)
# ----------------------------------------------------
def test_audit_submission_fast_fail():
    # โค้ดผิดไวยากรณ์ ต้องถูก Reject ทันทีโดยไม่ยิงหา LLM
    broken_code = "```python\ndef err(\n```"
    result = audit_submission("สร้างฟังก์ชัน", broken_code)
    
    assert "STATUS: REJECTED" in result
    assert "Syntax Error" in result

def test_audit_submission_llm_approved(mocker):
    # จำลอง Response จาก OpenAI API (ไม่ต้องเปิด LM Studio ตอนเทสต์)
    mock_choice = MagicMock()
    mock_choice.message.content = "STATUS: APPROVED\nISSUES_FOUND:\n- None\nACTIONABLE_FEEDBACK:\n- Pass"
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mocker.patch("auditor_bridge.client.chat.completions.create", return_value=mock_response)

    result = audit_submission("สร้างฟังก์ชันบวกเลข", "def add(x, y): return x + y")
    assert "STATUS: APPROVED" in result