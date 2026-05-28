from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import time
import uuid
import base64
import json
import os

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
    # IMPORTANT: List[Any] MUST come before str so Pydantic doesn't cast arrays into strings!
    content: Optional[Union[List[Any], str]] = None
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

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not db.verify_api_key(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return credentials.credentials

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, token: str = Depends(verify_token)):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")

    api_key_token = token
    session_data = db.get_api_key_session(api_key_token)
    
    if session_data is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    allowed_models, conversation_id, response_id, choice_id = session_data
    
    # Model Authorization Check
    if allowed_models != 'all':
        allowed_list = [m.strip() for m in allowed_models.split(',')]
        if request.model not in allowed_list:
            raise HTTPException(status_code=403, detail=f"Model '{request.model}' is not authorized for this API key. Allowed: {allowed_models}")

    cookies = db.get_cookies()
    if not cookies or not cookies.get('psid'):
        raise HTTPException(status_code=500, detail="Google Gemini cookies not configured in database. Run admin_bot.py to set them.")

    # Initialize Bot Session
    try:
        gemini_model = Model.from_name(request.model)
    except ValueError:
        # Fallback to default if model isn't precisely mapped in enums
        gemini_model = Model.UNSPECIFIED

    try:
        bot = await AsyncChatbot.create(
            secure_1psid=cookies['psid'],
            secure_1psidts=cookies.get('psidts', ''),
            model=gemini_model
        )
        
        # Restore session memory if it exists
        if conversation_id and response_id and choice_id:
            bot.conversation_id = conversation_id
            bot.response_id = response_id
            bot.choice_id = choice_id

        # Multi-modal extraction (Images & Files Aggregation)
        prompt_parts = []
        files_to_upload = []
        temp_files = []
        
        if isinstance(request.messages[-1].content, list):
            for item in request.messages[-1].content:
                if item.get("type") == "text":
                    prompt_parts.append(item.get("text", ""))
                elif item.get("type") in ["image_url", "file_url"]:
                    url_obj = item.get("image_url") or item.get("file_url")
                    if not url_obj: continue
                    
                    url = url_obj.get("url", "")
                    filename = url_obj.get("name", f"upload_{len(files_to_upload)}.bin")
                    
                    if url.startswith("data:"):
                        try:
                            header, encoded = url.split(",", 1)
                            file_bytes = base64.b64decode(encoded)
                            
                            # Save to temp file to retain original extension for MIME detection
                            tmp_dir = os.path.join("data", "temp_uploads")
                            os.makedirs(tmp_dir, exist_ok=True)
                            tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_{filename}")
                            
                            with open(tmp_path, "wb") as f:
                                f.write(file_bytes)
                            
                            files_to_upload.append(tmp_path)
                            temp_files.append(tmp_path)
                        except Exception as e:
                            print(f"Error decoding attachment: {e}")
            prompt = "\n".join(prompt_parts)
        else:
            prompt = request.messages[-1].content

        # Handle Stream = True
        if request.stream:
            async def stream_generator():
                try:
                    async for result in bot.ask_stream(prompt, files=files_to_upload):
                        if result.get("error"):
                            yield f"data: {json.dumps({'error': result.get('content')})}\n\n"
                            break

                        chunk_text = result.get("chunk", "")
                        cid = result.get("conversation_id")
                        rid = result.get("response_id")
                        chid = result.get("choice_id")
                        
                        # Extract and format images securely for JSON serialization
                        raw_imgs = result.get("images", [])
                        safe_imgs = []
                        for img in raw_imgs:
                            if hasattr(img, 'url'):
                                safe_imgs.append({"url": img.url, "title": getattr(img, 'title', 'Image')})
                            elif isinstance(img, dict) and 'url' in img:
                                safe_imgs.append({"url": img['url'], "title": img.get('title', 'Image')})
                        
                        # Emit the live text chunk and images
                        if chunk_text or safe_imgs:
                            delta_data = {}
                            if chunk_text:
                                delta_data["content"] = chunk_text
                            if safe_imgs:
                                delta_data["images"] = safe_imgs
                                
                            chunk_json = {
                                "id": f"chatcmpl-{uuid.uuid4().hex}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": request.model,
                                "choices": [{"index": 0, "delta": delta_data, "finish_reason": None}]
                            }
                            yield f"data: {json.dumps(chunk_json)}\n\n"

                    # Update persistent conversation session after stream is fully complete
                    if cid and rid and chid:
                        db.update_api_key_session(api_key_token, cid, rid, chid)

                    yield "data: [DONE]\n\n"
                
                finally:
                    await bot.session.close()
                    # Clean up temporary uploaded files
                    for p in temp_files:
                        if os.path.exists(p):
                            try:
                                os.remove(p)
                            except:
                                pass

            return StreamingResponse(stream_generator(), media_type="text/event-stream")

        # Handle Stream = False
        response = await bot.ask(prompt, files=files_to_upload)
        
        db.update_api_key_session(api_key_token, bot.conversation_id, bot.response_id, bot.choice_id)
        await bot.session.close()
        
        # Clean up temporary files
        for p in temp_files:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

        if response.get("error"):
            raise HTTPException(status_code=500, detail=response.get("content"))
            
        # Safely extract text from nested lists if present
        raw_content = response.get("content", "")
        def extract_text(item: Any) -> str:
            if isinstance(item, str):
                return item
            elif isinstance(item, list):
                return "".join(extract_text(x) for x in item if x is not None)
            return str(item) if item is not None else ""
            
        final_content = extract_text(raw_content).strip()

        # Extract images for non-streaming mode
        raw_imgs = response.get("images", [])
        safe_imgs = []
        for img in raw_imgs:
            if hasattr(img, 'url'):
                safe_imgs.append({"url": img.url, "title": getattr(img, 'title', 'Image')})
            elif isinstance(img, dict) and 'url' in img:
                safe_imgs.append({"url": img['url'], "title": img.get('title', 'Image')})

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": final_content, "images": safe_imgs}, "finish_reason": "stop"}]
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
                send_admin_alert("Cookies expired! Notifying Chrome Extension Auto-Healer.")
            
            raise HTTPException(status_code=401, detail="Gemini Cookies Expired. The Auto-Healer extension has been signaled to update them automatically. Please try again in a moment.")
            
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models(token: str = Depends(verify_token)):
    api_key_token = token
    session_data = db.get_api_key_session(api_key_token)
    
    if session_data is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    allowed_models = session_data[0]
    
    # Core Gemini Models Mapping
    models = [
        {"id": "gemini-1.5-pro", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-1.5-flash", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-1.0-pro", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-advanced", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-2.0-flash-exp", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-2.0-pro-exp", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-2.0-flash-thinking-exp", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "gemini-exp-1206", "object": "model", "created": int(time.time()), "owned_by": "google"},
        {"id": "learnlm-1.5-pro-experimental", "object": "model", "created": int(time.time()), "owned_by": "google"}
    ]

    # Filter by user's assigned scope
    if allowed_models != 'all':
        allowed_list = [m.strip() for m in allowed_models.split(',')]
        models = [m for m in models if m["id"] in allowed_list]

    return {
        "object": "list",
        "data": models
    }