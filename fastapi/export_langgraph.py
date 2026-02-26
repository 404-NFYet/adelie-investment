import sys
from pathlib import Path

sys.path.append("/home/ubuntu/adelie-investment/fastapi")

from app.services.guardrail import guardrail_app

try:
    png_data = guardrail_app.get_graph().draw_mermaid_png()
    with open("/home/ubuntu/adelie-investment/langgraph_structure.png", "wb") as f:
        f.write(png_data)
    print("SUCCESS: langgraph_structure.png saved.")
except Exception as e:
    print(f"ERROR: {e}")
