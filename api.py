from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import time
import uuid

import database as db
from gemini_client.core import AsyncChatbot
from gemini_client.enums import Model

app = FastAPI(title="Gemini-to-OpenAI API")
security = HTTPBearer()

# --- CORS Configuration ---
# This ensures that web browsers (like the api_tester.html) can interact 
# with this API without throwing Cross-Origin resource errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OpenAI Request/Response Models ---
class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]] # Supports both standard strings and vision object arrays
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str # REQUIRED field, no default.
    messages: List[Message]
    
    # --- OpenAI Compatibility Fields ---
    # These parameters allow true OpenAI SDKs (LangChain, AutoGen, etc.) to query this API 
    # without crashing due to "Unprocessable Entity" validation errors.
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

# --- Dependency to check API Key ---
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    details = db.get_api_key_details(credentials.credentials)
    if not details or not details[0]: # details[0] is active status
        raise HTTPException(status_code=401, detail="Invalid or deactivated API Key")
    return {"key": credentials.credentials, "allowed_models": details[1]}

# --- OpenAI-compatible Models Endpoint ---
@app.get("/v1/models")
async def list_models(auth_data: dict = Depends(verify_api_key)):
    """
    Allows OpenAI-compatible frontends to query available models.
    """
    allowed_models_str = auth_data["allowed_models"]
    allowed_list = [m.strip() for m in allowed_models_str.split(",")] if allowed_models_str != "all" else None
    
    models_data = []
    for m in Model:
        if m == Model.UNSPECIFIED:
            continue
            
        # Check model restrictions
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
        
    return {
        "object": "list",
        "data": models_data
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, auth_data: dict = Depends(verify_api_key)):
    cookies = db.get_cookies()
    if not cookies or not cookies[0]:
        raise HTTPException(status_code=500, detail="Gemini Cookies not set. Admin must set them via Telegram.")
    
    # Verify Model Authorization for this API Key
    allowed_models_str = auth_data["allowed_models"]
    allowed_list = [m.strip() for m in allowed_models_str.split(",")] if allowed_models_str != "all" else None
    
    if allowed_list and request.model not in allowed_list:
        raise HTTPException(status_code=403, detail=f"Your API key does not have access to model: {request.model}. Authorized models: {allowed_models_str}")
        
    # Extract the last message as the prompt
    # Safely handle standard strings vs complex vision dictionaries
    last_msg_content = request.messages[-1].content if request.messages else ""
    if isinstance(last_msg_content, list):
        # Flatten vision array into string prompt if applicable
        prompt = " ".join([item.get("text", "") for item in last_msg_content if item.get("type") == "text"])
    else:
        prompt = last_msg_content
    
    api_key_token = auth_data["key"]

    try:
        # Initialize Gemini Client with explicitly requested model
        try:
            requested_model = Model.from_name(request.model)
        except ValueError as e:
            # Instantly reject invalid models
            raise HTTPException(status_code=400, detail=str(e))
                
        bot = await AsyncChatbot.create(
            secure_1psid=cookies[0],
            secure_1psidts=cookies[1],
            model=requested_model
        )
        
        # --- NEW: Retrieve API Key Session from Database ---
        session_data = db.get_api_key_session(api_key_token)
        if session_data and session_data["cid"]:
            bot.conversation_id = session_data["cid"]
            bot.response_id = session_data["rid"] or ""
            bot.choice_id = session_data["chid"] or ""

        # Ask Gemini (Passing through prompt)
        response = await bot.ask(prompt)
        
        # --- NEW: Save the updated Session to Database ---
        db.update_api_key_session(
            api_key_token, 
            bot.conversation_id, 
            bot.response_id, 
            bot.choice_id
        )
        
        await bot.session.close()

        if response.get("error"):
            raise HTTPException(status_code=500, detail=response.get("content"))
            
        # Format exactly like a true OpenAI response
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "system_fingerprint": f"fp_{uuid.uuid4().hex[:10]}",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.get("content", "")
                },
                "logprobs": None,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt) // 4, # rough estimation
                "completion_tokens": len(response.get("content", "")) // 4,
                "total_tokens": (len(prompt) + len(response.get("content", ""))) // 4
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))