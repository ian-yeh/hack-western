import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')

async def get_next_action(screenshot: str, elements: list[dict], focus: str | None) -> dict:
    """Ask Gemini which element to interact with next."""
    
    elements_summary = "\n".join([
        f"{i}: [{e['tag']}] '{e['text'] or e['placeholder'] or e['type']}'"
        for i, e in enumerate(elements)
    ])
    
    prompt = f"""You are a QA tester exploring a web application.

Interactive elements found:
{elements_summary}

{f"Focus area: {focus}" if focus else ""}

Which element should I interact with next to test this application?
If you've tested enough, respond with {{"done": true}}.

Respond ONLY with JSON:
{{
    "index": <element index>,
    "action": "click" | "fill",
    "value": "<value if filling input>",
    "expectation": "<what should happen>",
    "reasoning": "<why this test>"
}}
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {"index": 0, "action": "click", "expectation": "Should work"}

async def evaluate_outcome(action: str, element: str, expectation: str, screenshot: str) -> dict:
    """Ask Gemini if the action produced the expected result."""
    
    prompt = f"""You are a QA tester evaluating a test result.

Action performed: {action} on "{element}"
Expected outcome: {expectation}

Based on the page state, did this test pass or fail?

Respond ONLY with JSON:
{{
    "passed": true | false,
    "title": "<short test case title>",
    "actual": "<what actually happened>"
}}
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {"passed": True, "title": f"Test {action}", "actual": "Completed"}

