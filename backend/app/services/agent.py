import base64
from datetime import datetime
from nanoid import generate
from playwright.async_api import async_playwright
from google import genai
from google.genai import types
from google.genai.types import Content, Part

from app.models import Action, TestCase
from app.store import store
from backend.app.services.gemini import GEMINI_API_KEY

# Screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900

async def run_agent(test_id: str, url: str, focus: str, sio) -> None:
    """Main agent that uses Gemini's computer use API with Playwright to complete tests."""
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
            
            # Configure the model with Computer Use tool
            config = types.GenerateContentConfig(
                tools=[types.Tool(computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER
                ))],
            )
            
            # Take initial screenshot
            initial_screenshot = await page.screenshot(type="png")
            
            # Create initial prompt
            user_prompt = f"{focus}"
            
            # Initialize conversation history
            contents = [
                Content(role="user", parts=[
                    Part(text=user_prompt),
                    Part.from_bytes(data=initial_screenshot, mime_type='image/png')
                ])
            ]
            
            # Agent loop - max 15 turns
            turn_limit = 15
            for i in range(turn_limit):
                print(f"Turn {i+1}/{turn_limit}")
                
                # Send request to Gemini
                response = client.models.generate_content(
                    model='gemini-2.5-computer-use-preview-10-2025',
                    contents=contents,
                    config=config,
                )
                
                candidate = response.candidates[0]
                contents.append(candidate.content)
                
                # Check if there are function calls to execute
                has_function_calls = any(part.function_call for part in candidate.content.parts)
                
                if not has_function_calls:
                    # Agent finished - extract final response
                    text_response = " ".join([part.text for part in candidate.content.parts if part.text])
                    print(f"Agent finished: {text_response}")
                    
                    # Emit completion action
                    action = Action(
                        type="screenshot",
                        element="Test completed",
                        timestamp=datetime.now()
                    )
                    store.add_action(test_id, action)
                    await sio.emit('action', action.model_dump(), room=test_id)
                    break
                
                # Execute function calls
                results = await execute_function_calls(candidate, page, SCREEN_WIDTH, SCREEN_HEIGHT)
                
                # Log each action
                for fname, result in results:
                    action = Action(
                        type=fname,
                        element=result.get('element', ''),
                        timestamp=datetime.now()
                    )
                    store.add_action(test_id, action)
                    await sio.emit('action', action.model_dump(), room=test_id)
                
                # Get function responses with new screenshot
                function_responses = await get_function_responses(page, results)
                
                # Add function responses to conversation
                contents.append(
                    Content(role="user", parts=[Part(function_response=fr) for fr in function_responses])
                )
            
            await browser.close()
        
        # Mark test as complete
        store.update(test_id, status="complete", completed_at=datetime.now())
        await sio.emit('complete', {"test_completed": True}, room=test_id)
        
    except Exception as e:
        print(f"Agent error: {str(e)}")
        store.update(test_id, status="failed")
        await sio.emit('error', {"message": str(e)}, room=test_id)

def denormalize_x(x: int, screen_width: int) -> int:
    """Convert normalized x coordinate (0-1000) to actual pixel coordinate."""
    return int(x / 1000 * screen_width)

def denormalize_y(y: int, screen_height: int) -> int:
    """Convert normalized y coordinate (0-1000) to actual pixel coordinate."""
    return int(y / 1000 * screen_height)

async def execute_function_calls(candidate, page, screen_width, screen_height):
    """Execute function calls returned by Gemini."""
    results = []
    function_calls = []
    
    for part in candidate.content.parts:
        if part.function_call:
            function_calls.append(part.function_call)
    
    for function_call in function_calls:
        action_result = {}
        fname = function_call.name
        args = function_call.args
        print(f"  -> Executing: {fname}")
        
        try:
            if fname == "open_web_browser":
                pass  # Already open
                action_result = {"element": "browser"}
            elif fname == "navigate":
                url = args.get("url", "")
                await page.goto(url, wait_until="networkidle")
                action_result = {"element": url}
            elif fname == "click_at":
                actual_x = denormalize_x(args["x"], screen_width)
                actual_y = denormalize_y(args["y"], screen_height)
                await page.mouse.click(actual_x, actual_y)
                action_result = {"element": f"({actual_x}, {actual_y})"}
            elif fname == "type_text_at":
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
            elif fname == "scroll_document":
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
            elif fname == "go_back":
                await page.go_back()
                action_result = {"element": "back"}
            elif fname == "go_forward":
                await page.go_forward()
                action_result = {"element": "forward"}
            elif fname == "wait_5_seconds":
                await page.wait_for_timeout(5000)
                action_result = {"element": "wait"}
            elif fname == "key_combination":
                keys = args["keys"]
                await page.keyboard.press(keys)
                action_result = {"element": keys}
            else:
                print(f"Warning: Unimplemented function {fname}")
                action_result = {"element": fname}
            
            # Wait for page to settle
            await page.wait_for_load_state("networkidle", timeout=5000)
            await page.wait_for_timeout(1000)
            
        except Exception as e:
            print(f"Error executing {fname}: {e}")
            action_result = {"error": str(e), "element": "error"}
        
        results.append((fname, action_result))
    
    return results

async def get_function_responses(page, results):
    """Capture new environment state and create function responses."""
    screenshot_bytes = await page.screenshot(type="png")
    current_url = page.url
    function_responses = []
    
    for name, result in results:
        response_data = {"url": current_url}
        response_data.update(result)
        function_responses.append(
            types.FunctionResponse(
                name=name,
                response=response_data,
                parts=[types.FunctionResponsePart(
                    inline_data=types.FunctionResponseBlob(
                        mime_type="image/png",
                        data=screenshot_bytes))
                ]
            )
        )
    
    return function_responses

