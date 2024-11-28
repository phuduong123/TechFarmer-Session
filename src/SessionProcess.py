import os
import re
import subprocess
import requests
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, field_validator
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor

# Đọc API_ID và API_HASH từ môi trường để bảo mật
API_ID = int(os.getenv("TELEGRAM_API_ID", "27477637"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "059ef651932df7a0a1998e5db5148127")
SESSIONS_DIR = "sessions"
TELEGRAM_SENDER_ID = "777000"  # Telegram system bot ID
TELEGRAM_WEB_URL = "https://web.telegram.org/a/"
TIMEOUT = 20  # Thời gian chờ Selenium

# FastAPI App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


class SignInRequest(BaseModel):
    phone_number: str
    password: str | None = None  # Mật khẩu 2FA (nếu có)
    verification_code: str | None = None  # Mã xác minh (nếu đã có)

    @field_validator("phone_number")
    def validate_phone(cls, value):
        if not re.match(r"^\+?\d{10,15}$", value):
            raise ValueError("Invalid phone number format. Must start with + and be 10-15 digits.")
        return value

def start_gpm_profile(profile_id, host, api_version="v3", win_scale=0.8, win_pos="150,150"):
    """Khởi chạy profile GPM."""
    start_url = f"{host}/api/{api_version}/profiles/start/{profile_id}"
    response = requests.get(start_url, params={"win_scale": win_scale, "win_pos": win_pos})
    if response.status_code == 200 and response.json().get("success"):
        return response.json()["data"]
    else:
        raise Exception(f"Failed to start GPM profile: {response.json().get('message')}")

def close_gpm_profile(profile_id, host, api_version="v3"):
    """Đóng profile GPM."""
    close_url = f"{host}/api/{api_version}/profiles/close/{profile_id}"
    response = requests.get(close_url)
    if response.status_code == 200 and response.json().get("success"):
        print("Profile closed successfully.")
    else:
        print(f"Failed to close profile: {response.json().get('message')}")

def configure_selenium_driver(profile_data):
    """Cấu hình và khởi tạo Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.binary_location = profile_data["browser_location"]
    options.add_experimental_option("debuggerAddress", profile_data["remote_debugging_address"])
    service = Service(profile_data["driver_path"])
    return webdriver.Chrome(service=service, options=options)

def extract_telegram_code(driver):
    """Trích xuất mã xác thực Telegram từ tin nhắn cuối cùng."""
    driver.get(TELEGRAM_WEB_URL)

    # Đợi giao diện Telegram tải
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, '//input[@placeholder="Search"]'))
    )

    
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, f'//*[@data-peer-id="{TELEGRAM_SENDER_ID}"]'))
    ).click()

    # Trích xuất mã từ tin nhắn cuối cùng
    message_xpath = '(//*[@class="text-content clearfix with-meta"])[last()]'
    code_block = WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, message_xpath))
    )
    code_match = re.search(r"\b\d{5,6}\b", code_block.text or "")

    if code_match:
        return int(code_match.group())
    else:
        raise Exception("No valid code found in the latest message.")

def getCodeFromBrowser():
    """Tự động lấy mã xác thực Telegram."""
    HOST = "http://127.0.0.1:19995"
    PROFILE_ID = "b605f155-7dc5-45f9-abf0-ee10cd2ea258"
    driver = None

    try:
        print("\n=== Starting browser automation ===")
        print(f"1. Starting GPM profile {PROFILE_ID} on {HOST}...")
        profile_data = start_gpm_profile(PROFILE_ID, HOST)
        print("2. GPM profile started successfully")
        
        print("3. Configuring Selenium driver...")
        driver = configure_selenium_driver(profile_data)
        print("4. Selenium driver configured")

        print("5. Starting code extraction...")
        code = extract_telegram_code(driver)
        print(f"6. Code extracted successfully: {code}")
        return code

    except Exception as e:
        print(f"❌ Error in browser automation: {str(e)}")
        raise e

    finally:
        if driver:
            print("7. Closing browser...")
            try:
                driver.quit()
                print("8. Browser closed successfully")
            except Exception as e:
                print(f"Warning: Failed to close browser: {str(e)}")

        print(f"9. Closing GPM profile {PROFILE_ID}...")
        try:
            close_gpm_profile(PROFILE_ID, HOST)
            print("10. GPM profile closed successfully")
        except Exception as e:
            print(f"Warning: Failed to close GPM profile: {str(e)}")

@app.get("/api/test")
async def test():
    code = getCodeFromBrowser()
    return {"session_file": code}

class CustomTelegramClient(TelegramClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._phone = None
        self._code = None
        
    async def start(self, phone=None, password=None, code_callback=None, first_name='New User', last_name=''):
        if phone is None:
            phone = self._phone
        if code_callback is None:
            code_callback = lambda: self._code
            
        return await super().start(phone=phone, password=password, code_callback=code_callback, first_name=first_name, last_name=last_name)
        # Đảm bảo session được lưu sau khi start thành công
        if hasattr(self, 'session') and self.session:
            self.session.save()
        return result
    
    async def get_phone(self):
        return self._phone
        
    async def get_code(self):
        return self._code
    
    def set_phone(self, phone):
        self._phone = phone
        
    def set_code(self, code):
        self._code = code

async def get_code_with_browser():
    """Wrapper bất đồng bộ cho getCodeFromBrowser"""
    print("\n=== Starting get_code_with_browser ===")
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            print("Executing getCodeFromBrowser in thread pool...")
            result = await loop.run_in_executor(executor, getCodeFromBrowser)
            print(f"Code retrieved: {result}")
            return result
    except Exception as e:
        print(f"Error in get_code_with_browser: {str(e)}")
        raise

async def wait_for_code(verification_code=None, max_retries=5, delay=5):
    """Đợi và lấy verification code từ browser"""
    if verification_code:
        print(f"Using provided code: {verification_code}")
        return verification_code
        
    print("\n=== Starting code retrieval process ===")
    for attempt in range(max_retries):
        print(f"\nAttempt {attempt + 1}/{max_retries} to get code")
        try:
            # Thêm delay trước khi lấy code
            await asyncio.sleep(10)
            code = await get_code_with_browser()
            print(f"Retrieved raw code: {code}")
            await asyncio.sleep(10)
            if code and str(code).isdigit() and len(str(code)) >= 5:
                print(f"✓ Valid code retrieved: {code}")
                return str(code)
            print(f"✗ Invalid code format: {code}")
        except Exception as e:
            print(f"✗ Attempt {attempt + 1} failed: {str(e)}")
        
        if attempt < max_retries - 1:
            print(f"Waiting {delay} seconds before next attempt...")
            await asyncio.sleep(delay)
    
    raise HTTPException(
        status_code=408,
        detail="Failed to get valid code after multiple attempts"
    )

@app.post("/api/generateSessionAndTData")
async def generate_session_and_tdata(request: SignInRequest):
    client = None
    try:
        phone_number = request.phone_number
        password = request.password
        verification_code = request.verification_code

        print(f"Request received: phone={phone_number}, has_password={bool(password)}, has_code={bool(verification_code)}")

        sanitized_phone = phone_number.replace("+", "").replace(" ", "")
        phone_dir = os.path.join(SESSIONS_DIR, sanitized_phone)
        session_file = os.path.join(phone_dir, f"{sanitized_phone}.session")
        tdata_dir = os.path.join(phone_dir, "tdata")

        os.makedirs(phone_dir, exist_ok=True)
        os.makedirs(tdata_dir, exist_ok=True)

        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                print(f"Removed existing session file: {session_file}")
            except Exception as e:
                print(f"Warning: Could not remove existing session file: {str(e)}")
                await asyncio.sleep(1)

        client = CustomTelegramClient(session_file, API_ID, API_HASH)
        client.set_phone(phone_number)
        
        # Kết nối trước
        await client.connect()
        
        if not await client.is_user_authorized():
            print("\n=== Starting authentication process ===")
            
            # Gửi yêu cầu mã xác minh
            print("Sending code request...")
            sent = await client.send_code_request(phone_number)
            print(f"Code request sent with hash: {sent.phone_code_hash}")
            
            print("Waiting for code message to arrive...")
            await asyncio.sleep(10)
            
            print("Starting code retrieval...")
            code = await wait_for_code()
            
            if not code:
                raise HTTPException(
                    status_code=400,
                    detail="Could not get valid verification code"
                )

            # Sau khi có code, thực hiện sign in
            print(f"Attempting to sign in with code: {code}")
            try:
                await client.sign_in(
                    phone=phone_number,
                    code=code,
                    phone_code_hash=sent.phone_code_hash
                )
                print("✓ Sign in successful")
            except SessionPasswordNeededError:
                if not password:
                    raise HTTPException(
                        status_code=401,
                        detail="2FA password required"
                    )
                print("2FA required, using password...")
                await client.sign_in(password=password)
                # Lưu session sau khi 2FA thành công
                if hasattr(client, 'session') and client.session:
                    client.session.save()
                print("✓ 2FA sign in successful")

        if await client.is_user_authorized():
            print("User is authorized")
            # Đảm bảo session được lưu lần cuối
            if hasattr(client, 'session') and client.session:
                client.session.save()
            
            # Convert session to TData format
            from opentele.tl import TelegramClient
            from opentele.api import UseCurrentSession
            print("Converting session to TData format...")
            tdesk = await client.ToTDesktop(flag=UseCurrentSession)
            tdesk.SaveTData(tdata_dir)
            print("✓ Conversion to TData completed successfully")

            await client.disconnect()
            
            return JSONResponse(
                content={
                    "status": "success",
                    "session_file": session_file,
                    "tdata_folder": tdata_dir
                }
            )

    except Exception as e:
        print(f"Error during client operations: {str(e)}")
        if client:
            await client.disconnect()
        await asyncio.sleep(2)
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
                print(f"Removed session file after error: {session_file}")
        except Exception as del_err:
            print(f"Could not remove session file: {str(del_err)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if client:
            await client.disconnect()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
