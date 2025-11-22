import asyncio
from playwright.async_api import async_playwright
from nanoid import generate
from datetime import datetime

from app.models import Action, TestCase
from app.store import store
from app.services.gemini import get_next_action, evaluate_outcome

async def get_interactive_elements(page) -> list[dict]:
    """Extract interactive elements from the page."""
    return await page.evaluate("""
        () => {
            const elements = [];
            document.querySelectorAll('button, a, input, select, textarea, [role="button"]').forEach((el, i) => {
                const text = el.innerText?.trim().slice(0, 50) || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const type = el.getAttribute('type') || '';
                const tag = el.tagName.toLowerCase();
                
                // Generate selector
                let selector = '';
                if (el.id) {
                    selector = '#' + el.id;
                } else if (text && ['button', 'a'].includes(tag)) {
                    selector = tag + ":has-text('" + text.slice(0, 20) + "')";
                } else if (placeholder) {
                    selector = tag + "[placeholder='" + placeholder + "']";
                } else if (type) {
                    selector = tag + "[type='" + type + "']";
                } else {
                    selector = tag + ':nth-of-type(' + (i + 1) + ')';
                }
                
                elements.push({
                    index: i,
                    tag: tag,
                    text: text,
                    placeholder: placeholder,
                    type: type,
                    selector: selector
                });
            });
            return elements;
        }
    """)

async def run_agent(test_id: str, url: str, focus: str | None, sio) -> None:
    """Main agent loop that explores the site and generates test cases."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to URL
            await page.goto(url, wait_until="networkidle")
            
            # Emit initial action
            action = Action(
                type="navigate",
                element=url,
                timestamp=datetime.now()
            )
            store.add_action(test_id, action)
            await sio.emit('action', action.model_dump(), room=test_id)
            
            # Exploration loop
            for i in range(15):  # Max 15 iterations
                # Take screenshot
                screenshot_bytes = await page.screenshot()
                screenshot_b64 = screenshot_bytes.hex()  # or base64 encode
                
                # Get interactive elements
                elements = await get_interactive_elements(page)
                
                if not elements:
                    break
                
                # Ask Gemini what to do next
                decision = await get_next_action(screenshot_b64, elements, focus)
                
                if decision.get("done"):
                    break
                
                # Execute the action
                target_index = decision.get("index", 0)
                action_type = decision.get("action", "click")
                
                if target_index < len(elements):
                    target = elements[target_index]
                    selector = target["selector"]
                    
                    try:
                        if action_type == "click":
                            await page.click(selector, timeout=5000)
                        elif action_type == "fill":
                            await page.fill(selector, decision.get("value", "test@example.com"))
                        
                        await page.wait_for_timeout(1000)  # Wait for page to settle
                        
                        # Take after screenshot
                        after_screenshot = await page.screenshot()
                        
                        # Evaluate outcome
                        evaluation = await evaluate_outcome(
                            action_type,
                            target["text"] or target["selector"],
                            decision.get("expectation", "Action should complete successfully"),
                            after_screenshot.hex()
                        )
                        
                        # Create test case
                        test_case = TestCase(
                            id=f"case_{generate(size=8)}",
                            title=evaluation.get("title", f"Test {action_type} on {target['text']}"),
                            steps=[f"{action_type} on '{target['text'] or target['selector']}'"],
                            expected=decision.get("expectation", "Should work"),
                            actual=evaluation.get("actual", "Completed"),
                            status="pass" if evaluation.get("passed") else "fail",
                            screenshot=after_screenshot.hex()
                        )
                        
                        store.add_case(test_id, test_case)
                        await sio.emit('testcase', test_case.model_dump(), room=test_id)
                        
                        # Log action
                        action = Action(
                            type=action_type,
                            element=target["text"] or selector,
                            screenshot=after_screenshot.hex(),
                            timestamp=datetime.now()
                        )
                        store.add_action(test_id, action)
                        await sio.emit('action', action.model_dump(), room=test_id)
                        
                    except Exception as e:
                        # Action failed — log as failed test case
                        test_case = TestCase(
                            id=f"case_{generate(size=8)}",
                            title=f"Failed: {action_type} on {target['text']}",
                            steps=[f"Attempted {action_type} on '{target['text']}'"],
                            expected="Action should complete",
                            actual=str(e),
                            status="fail"
                        )
                        store.add_case(test_id, test_case)
                        await sio.emit('testcase', test_case.model_dump(), room=test_id)
            
            await browser.close()
        
        # Mark complete
        store.update(test_id, status="complete", completed_at=datetime.now())
        await sio.emit('complete', {"cases_count": len(store.get(test_id).cases)}, room=test_id)
        
    except Exception as e:
        store.update(test_id, status="failed")
        await sio.emit('error', {"message": str(e)}, room=test_id)

