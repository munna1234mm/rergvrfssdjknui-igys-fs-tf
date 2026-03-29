import asyncio
import random
import sys
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# User Agents for randomization
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36"
]

async def hit_card(url, card_str):
    if '|' not in card_str:
        print(f"ERROR: Invalid card format {card_str}")
        return

    card, mm, yy, cvc = card_str.split('|')
    
    async with async_playwright() as p:
        # Launch browser (Headless=False to see it work, can be changed to True)
        browser = await p.chromium.launch(headless=False)
        
        # Random User Agent for this session
        ua = random.choice(USER_AGENTS)
        context = await browser.new_context(user_agent=ua)
        
        page = await context.new_page()
        await stealth_async(page)
        
        print(f"🚀 Navigating to: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Find Stripe Iframes
            print("⏳ Waiting for Stripe fields...")
            await page.wait_for_selector('iframe[name^="__privateStripeFrame"]', timeout=30000)
            
            # Fill Card Number
            card_frame = page.frame(name=lambda n: "__privateStripeFrame" in n and "1" in n) # Usually 1 or specific
            # Using selector search is safer
            frames = page.frames
            card_input_frame = None
            for f in frames:
                if "stripe" in f.url and "elements" in f.url:
                    card_input_frame = f
                    break
            
            if not card_input_frame:
                print("❌ Could not locate Stripe iframe.")
                await browser.close()
                return

            # Human-like typing
            async def human_type(frame, selector, text):
                await frame.click(selector)
                for char in text:
                    await frame.type(selector, char, delay=random.randint(50, 200))

            print("⌨️ Inputting card details...")
            # Note: Stripe usually uses 'input[name="cardnumber"]' inside the iframe
            # But the 'cardNumber' selector is more common in their SDK
            await human_type(card_input_frame, 'input[name="cardnumber"]', card)
            await human_type(card_input_frame, 'input[name="exp-date"]', f"{mm}{yy}")
            await human_type(card_input_frame, 'input[name="cvc"]', cvc)
            
            # Maybe Name/Zip if requested? (Optional for now)
            
            print("🔘 Clicking Pay...")
            # Try to find the submit button on the MAIN page
            submit_selectors = ['button[type="submit"]', '.SubmitButton', '#submit-button', 'button:has-text("Pay")']
            for s in submit_selectors:
                if await page.is_visible(s):
                    await page.click(s)
                    break
            
            # Wait for result
            print("⌛ Waiting for result (60s max)...")
            await asyncio.sleep(10) # Initial wait
            
            # Check for 3DS or Success/Failure
            content = await page.content()
            if "Successful" in content or "Thank you" in content:
                 print(f"SUCCESS: Payment successful for {card_str}")
            elif "declined" in content.lower() or "failed" in content.lower():
                 print(f"FAILURE: Card declined ({card_str})")
            elif "authenticate" in content.lower() or "security" in content.lower():
                 print(f"3DS: 3D Secure Verification Required")
            else:
                 print(f"UNKNOWN: Result not detected, please check manual window.")
                 await asyncio.sleep(15) # Give user time to see
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python browser_hitter.py <url> <card>")
    else:
        target_url = sys.argv[1]
        card_data = sys.argv[2]
        asyncio.run(hit_card(target_url, card_data))
