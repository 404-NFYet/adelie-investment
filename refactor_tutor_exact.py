import sys

with open("fastapi/app/api/routes/tutor.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Extract blocks based on line number (0-indexed)
# page_context: 220-249 (lines 221-250)
page_ctx_lines = lines[220:250]
# portfolio_context: 250-267 (lines 251-268)
portfolio_lines = lines[250:268]
# sources: 268-287 (lines 269-288)
sources_lines = lines[268:288]
# prev_msgs: 311-330 (lines 312-331)
prev_msgs_lines = lines[311:331]

# Delete extracted blocks in reverse order so indices don't shift
del lines[311:331]
del lines[268:288]
del lines[250:268]
del lines[220:250]

# Insert them before line 153 (index 152) -> wait, actually index 153 (line 154) is '# 가드레일 검사'
insert_index = 153

db_imports = [
    "    from app.models.tutor import TutorSession, TutorMessage\n",
    "    from sqlalchemy import select\n",
    "    session_obj = None\n",
]

guardrail_context_logic = [
    "\n",
    "    # 가드레일용 문맥 조립\n",
    "    guardrail_context = page_context\n",
    "    last_assistant_msgs = [m[\"content\"] for m in prev_msgs if m[\"role\"] == \"assistant\"]\n",
    "    if last_assistant_msgs:\n",
    "        guardrail_context += f\"\\n\\n[직전 챗봇의 답변]\\n{last_assistant_msgs[-1]}\"\n",
    "\n"
]

all_moved_lines = db_imports + page_ctx_lines + portfolio_lines + sources_lines + prev_msgs_lines + guardrail_context_logic

lines = lines[:insert_index] + all_moved_lines + lines[insert_index:]

# Now replace the run_guardrail call (which used to be at line 156, now shifted down)
# Let's just find "run_guardrail(request.message)" and replace it
for i, line in enumerate(lines):
    if "guardrail_result = await run_guardrail(request.message)" in line:
        lines[i] = line.replace("await run_guardrail(request.message)", "await run_guardrail(request.message, context=guardrail_context)")
        break

with open("fastapi/app/api/routes/tutor.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

