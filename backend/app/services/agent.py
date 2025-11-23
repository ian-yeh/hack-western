import base64
import json
from datetime import datetime
from nanoid import generate
from playwright.async_api import async_playwright
from google import genai

from app.models import Action, TestCase
from app.store import store
from backend.app.services.gemini import GEMINI_API_KEY

# Screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900

SYSTEM_PROMPT = """You are a web automation agent that analyzes screenshots and decides what actions to take to complete a test.

Available actions (action_name variable):
- navigate: Navigate to a URL. Args: {"url": "string"}
- click_at: Click at coordinates. Args: {"x": int (0-999), "y": int (0-999)}
- type_text_at: Type text at coordinates. Args: {"x": int (0-999), "y": int (0-999), "text": "string", "press_enter": bool, "clear_before_typing": bool}
- scroll_document: Scroll the page. Args: {"direction": "up"|"down"|"left"|"right"}
- go_back: Go back in browser history. Args: {}
- go_forward: Go forward in browser history. Args: {}
- wait_5_seconds: Wait 5 seconds. Args: {}
- key_combination: Press keyboard keys. Args: {"keys": "string"}
- done: Mark test as complete. Args: {"success": bool, "message": "string"}

Respond with JSON only:
{
  "observation": "What you see in the screenshot and current state",
  "reasoning": "Why you're taking this action",
  "action": "action_name",
  "args": {action arguments}
}

Coordinates are normalized 0-999 for both x and y regardless of actual screen size."""

async def run_agent(test_id: str, url: str, focus: str, sio) -> None:
    """Main agent that uses Gemini to analyze screenshots and control browser via Playwright."""
    try:
        # Get the test run from store
        test_run = store.get(test_id)
        if not test_run:
            raise ValueError(f"Test run {test_id} not found")
        
        # Initialize Playwright
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT})
            page = await context.new_page()
            
            # Navigate to URL
            await page.goto(url, wait_until="networkidle")
            
            # Log initial navigation action
            action = Action(
                type="navigate",
                element=url,
                timestamp=datetime.now()
            )
            store.add_action(test_id, action)
            await sio.emit('action', action.model_dump(), room=test_id)
            
            # Get Gemini client
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Agent loop - max 15 turns
            turn_limit = 15
            conversation_history = []
            
            for i in range(turn_limit):
                print(f"Turn {i+1}/{turn_limit}")
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(type="png")
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # Build prompt for this turn
                if i == 0:
                    prompt = f"""Task: {focus}
Current URL: {url}

Analyze the screenshot and decide the first action to take to complete this test."""
                else:
                    prompt = f"""Task: {focus}
Current URL: {page.url}
Previous actions: {len(conversation_history)} steps taken

Analyze the screenshot and decide the next action. If the test is complete, use the 'done' action."""
                
                # Send request to Gemini
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        {"role": "user", "parts": [
                            {"text": SYSTEM_PROMPT},
                        ]},
                        {"role": "user", "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": screenshot_b64}}
                        ]}
                    ]
                )
                
                # Parse response
                response_text = response.text.strip()
                print(f"Model response: {response_text}")
                
                # Extract JSON from response
                decision = parse_json_response(response_text)
                
                if not decision:
                    print("Failed to parse model response, retrying...")
                    continue
                
                # Log observation
                observation = decision.get("observation", "")
                reasoning = decision.get("reasoning", "")
                print(f"Observation: {observation}")
                print(f"Reasoning: {reasoning}")
                
                action_name = decision.get("action", "")
                args = decision.get("args", {})
                
                # Check if done
                if action_name == "done":
                    success = args.get("success", True)
                    message = args.get("message", "Test completed")
                    print(f"Test {'passed' if success else 'failed'}: {message}")
                    
                    action = Action(
                        type="screenshot",
                        element=message,
                        timestamp=datetime.now()
                    )
                    store.add_action(test_id, action)
                    await sio.emit('action', action.model_dump(), room=test_id)
                    break
                
                # Execute the action
                result = await execute_single_action(action_name, args, page, SCREEN_WIDTH, SCREEN_HEIGHT)
                
                # Log action
                action = Action(
                    type=action_name,
                    element=result.get('element', ''),
                    timestamp=datetime.now()
                )
                store.add_action(test_id, action)
                await sio.emit('action', action.model_dump(), room=test_id)
                
                # Update conversation history
                conversation_history.append({
                    "action": action_name,
                    "args": args,
                    "observation": observation,
                    "result": result
                })
            
            await browser.close()
        
        # Mark test as complete
        store.update(test_id, status="complete", completed_at=datetime.now())
        await sio.emit('complete', {"test_completed": True}, room=test_id)
        
    except Exception as e:
        print(f"Agent error: {str(e)}")
        store.update(test_id, status="failed")
        await sio.emit('error', {"message": str(e)}, room=test_id)

def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from model response."""
    try:
        # Try direct parse
        return json.loads(text)
    except:
        pass
    
    # Try to extract from markdown code blocks
    if "```json" in text:
        try:
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except:
            pass
    elif "```" in text:
        try:
            json_str = text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        except:
            pass
    
    # Try to find JSON object in text
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except:
        pass
    
    return None

async def execute_single_action(action_name: str, args: dict, page, screen_width: int, screen_height: int) -> dict:
    """Execute a single action returned by the model."""
    action_result = {}
    print(f"  -> Executing: {action_name} with args: {args}")
    
    try:
        if action_name == "navigate":
            url = args.get("url", "")
            await page.goto(url, wait_until="networkidle")
            action_result = {"element": url}
        elif action_name == "click_at":
            actual_x = denormalize_x(args["x"], screen_width)
            actual_y = denormalize_y(args["y"], screen_height)
            await page.mouse.click(actual_x, actual_y)
            action_result = {"element": f"({actual_x}, {actual_y})"}
        elif action_name == "type_text_at":
            actual_x = denormalize_x(args["x"], screen_width)
            actual_y = denormalize_y(args["y"], screen_height)
            text = args["text"]
            press_enter = args.get("press_enter", False)
            clear_before_typing = args.get("clear_before_typing", True)
            
            await page.mouse.click(actual_x, actual_y)
            if clear_before_typing:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
            await page.keyboard.type(text)
            if press_enter:
                await page.keyboard.press("Enter")
            action_result = {"element": text}
        elif action_name == "scroll_document":
            direction = args["direction"]
            if direction == "down":
                await page.mouse.wheel(0, 500)
            elif direction == "up":
                await page.mouse.wheel(0, -500)
            elif direction == "left":
                await page.mouse.wheel(-500, 0)
            elif direction == "right":
                await page.mouse.wheel(500, 0)
            action_result = {"element": direction}
        elif action_name == "go_back":
            await page.go_back()
            action_result = {"element": "back"}
        elif action_name == "go_forward":
            await page.go_forward()
            action_result = {"element": "forward"}
        elif action_name == "wait_5_seconds":
            await page.wait_for_timeout(5000)
            action_result = {"element": "wait"}
        elif action_name == "key_combination":
            keys = args["keys"]
            await page.keyboard.press(keys)
            action_result = {"element": keys}
        else:
            print(f"Warning: Unknown action {action_name}")
            action_result = {"element": action_name}
        
        # Wait for page to settle
        await page.wait_for_load_state("networkidle", timeout=5000)
        await page.wait_for_timeout(1000)
        
    except Exception as e:
        print(f"Error executing {action_name}: {e}")
        action_result = {"error": str(e), "element": "error"}
    
    return action_result

def denormalize_x(x: int, screen_width: int) -> int:
    """Convert normalized x coordinate (0-1000) to actual pixel coordinate."""
    return int(x / 1000 * screen_width)

def denormalize_y(y: int, screen_height: int) -> int:
    """Convert normalized y coordinate (0-1000) to actual pixel coordinate."""
    return int(y / 1000 * screen_height)
