from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import time
import uuid
import base64

import database as db
from gemini_client.core import AsyncChatbot
from gemini_client.enums import Model

app = FastAPI(title="Gemini-to-OpenAI API")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: Optional[Union[str, List[Any]]] = None
    name: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Prevents 422 errors from unexpected fields

class ChatCompletionRequest(BaseModel):
    model: str 
    messages: List[Message]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    seed: Optional[int] = None
    response_format: Optional[Dict[str, str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

    class Config:
        extra = "ignore"  # Strongly prevents 422 errors

class CookieUpdateRequest(BaseModel):
    psid: str
    psidts: str

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    details = db.get_api_key_details(credentials.credentials)
    if not details or not details[0]: 
        raise HTTPException(status_code=401, detail="Invalid or deactivated API Key")
    return {"key": credentials.credentials, "allowed_models": details[1], "role": details[2]}

def verify_admin_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    details = db.get_api_key_details(credentials.credentials)
    if not details or not details[0]: 
        raise HTTPException(status_code=401, detail="Invalid or deactivated API Key")
    if details[2] != 'admin':
        raise HTTPException(status_code=403, detail="API Key lacks 'admin' permissions required for this endpoint")
    return {"key": credentials.credentials}

# ==========================================
# SECURE EXTENSION AUTO-HEALER ENDPOINTS
# ==========================================
@app.get("/v1/admin/cookie_status")
async def check_cookie_status(admin_auth = Depends(verify_admin_key)):
    """Extension securely polls this to see if intervention is needed."""
    return {"needs_update": db.get_needs_update()}

@app.post("/v1/admin/cookies")
async def update_cookies_api(request: CookieUpdateRequest, admin_auth = Depends(verify_admin_key)):
    """Extension pushes JSON Secure data packet here to fix cookies."""
    db.update_cookies(request.psid, request.psidts)
    db.set_needs_update(False) # Turn off the distress signal
    
    from admin_bot import bot, ADMIN_ID
    if bot and ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, "✅ <b>Auto-Heal Complete:</b> The Chrome Extension securely intercepted the error and updated the database with fresh cookies!", parse_mode="HTML")
        except: pass
        
    return {"status": "success", "message": "Secure payload accepted. Cookies updated."}

@app.get("/v1/models")
async def list_models(auth_data: dict = Depends(verify_api_key)):
    allowed_models_str = auth_data["allowed_models"]
    allowed_list = [m.strip() for m in allowed_models_str.split(",")] if allowed_models_str != "all" else None
    
    models_data = []
    for m in Model:
        if m == Model.UNSPECIFIED:
            continue
        if allowed_list and m.model_name not in allowed_list:
            continue
            
        models_data.append({
            "id": m.model_name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "google",
            "permission": [],
            "root": m.model_name,
            "parent": None,
        })
        
    return {"object": "list", "data": models_data}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, auth_data: dict = Depends(verify_api_key)):
    cookies = db.get_cookies()
    if not cookies or not cookies[0]:
        raise HTTPException(status_code=500, detail="Gemini Cookies not set. Admin must set them via Telegram.")
    
    allowed_models_str = auth_data["allowed_models"]
    allowed_list = [m.strip() for m in allowed_models_str.split(",")] if allowed_models_str != "all" else None
    
    if allowed_list and request.model not in allowed_list:
        raise HTTPException(status_code=403, detail=f"Your API key does not have access to model: {request.model}.")
        
    # Get the last message to process
    last_msg_content = request.messages[-1].content if request.messages else ""
    image_bytes = None
    prompt = ""

    # Check for Vision Payload (List of Dictionaries/Objects)
    if isinstance(last_msg_content, list):
        for item in last_msg_content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    prompt += item.get("text", "") + " "
                elif item.get("type") == "image_url":
                    img_data = item.get("image_url", {}).get("url", "")
                    if img_data.startswith("data:image"):
                        try:
                            b64_str = img_data.split("base64,")[1]
                            image_bytes = base64.b64decode(b64_str)
                        except Exception as e:
                            print(f"Failed to decode base64 image: {e}")
        prompt = prompt.strip()
        if not prompt and image_bytes:
            prompt = "Describe this image."
    else:
        # Standard text message
        prompt = str(last_msg_content) if last_msg_content else ""
    
    api_key_token = auth_data["key"]

    try:
        try:
            requested_model = Model.from_name(request.model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
                
        bot = await AsyncChatbot.create(
            secure_1psid=cookies[0],
            secure_1psidts=cookies[1],
            model=requested_model
        )
        
        session_data = db.get_api_key_session(api_key_token)
        if session_data and session_data["cid"]:
            bot.conversation_id = session_data["cid"]
            bot.response_id = session_data["rid"] or ""
            bot.choice_id = session_data["chid"] or ""

        # Pass both prompt and potentially parsed image_bytes to core.py logic
        response = await bot.ask(prompt, image=image_bytes)
        
        db.update_api_key_session(api_key_token, bot.conversation_id, bot.response_id, bot.choice_id)
        await bot.session.close()

        if response.get("error"):
            raise HTTPException(status_code=500, detail=response.get("content"))
            
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": response.get("content", "")}, "finish_reason": "stop"}]
        }

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        
        # SMART AUTO-HEALER TRIGGER & FLOOD CONTROL
        if any(kw in error_str.lower() for kw in ["cookie", "snlm0e", "auth", "permission", "status: 40", "status: 50"]):
            # Signal the Chrome Extension
            db.set_needs_update(True)
            
            # Flood Control: Only alert Telegram once every 5 minutes
            if db.check_and_set_alert_flood(cooldown_seconds=300):
                from admin_bot import send_admin_alert
                send_admin_alert("Cookies expired! Notifying Chrome Extension Auto-Healer to execute payload...")
                
        raise HTTPException(status_code=500, detail=error_str)