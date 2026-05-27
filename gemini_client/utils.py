# -*- coding: utf-8 -*-
import json
import mimetypes
from pathlib import Path
from typing import Dict, Tuple, Union, Optional

# FIX: Import CurlMime for modern multipart/form-data uploads.
# FIX: Migrated exceptions from `requests.exceptions` to `curl_cffi.requests.errors`
# as curl_cffi's `raise_for_status()` raises its own exceptions, not `requests` exceptions.
from curl_cffi import CurlError, CurlMime
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestException, HTTPError, Timeout

from rich.console import Console

# Assuming Endpoint and Headers enums are in 'enums.py' within the same package
from .enums import Endpoint, Headers

console = Console() # Instantiate console for logging

async def upload_file(
    file: Union[bytes, str, Path],
    proxy: Optional[Union[str, Dict[str, str]]] = None,
    impersonate: str = "chrome120", # Updated impersonation target to a more modern Chrome version
    filename: str = "upload.jpg" # Fallback filename for raw bytes
) -> str:
    """
    Uploads a file to Google's Gemini server using curl_cffi's modern multipart implementation.

    Args:
        file (bytes | str | Path): File data in bytes or path to the file to be uploaded.
        proxy (str | dict, optional): Proxy URL or dictionary for the request.
        impersonate (str, optional): Browser profile for curl_cffi to impersonate.
        filename (str, optional): Filename to use if raw bytes are passed.

    Returns:
        str: Identifier/Response text of the uploaded file.
    """
    file_content = b""
    content_type = "application/octet-stream"

    # 1. Handle file input and dynamically guess MIME type for png/jpg/webp support
    if isinstance(file, bytes):
        file_content = file
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    else:
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found at path: {file_path}")
        
        file_content = file_path.read_bytes()
        filename = file_path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    # 2. Prepare proxy dictionary for curl_cffi
    proxies_dict = None
    if isinstance(proxy, str):
        proxies_dict = {"http": proxy, "https": proxy} 
    elif isinstance(proxy, dict):
        proxies_dict = proxy 

    # --- ARCHITECTURE & HEADER ANALYSIS ---
    # Analysis of `UPLOAD = {"Push-ID": "feeds/mcudyrk2a4khkz"}`:
    # 1. OUTDATED/INCORRECT: The `Push-ID` header is generally utilized by Google's Server-Sent Events (SSE) 
    #    or real-time channel API (e.g., Batchelor/Channel API) for listening to UI updates, NOT for file uploads.
    # 2. RESUMABLE UPLOADS: Yes, modern Google WebUI uploads strictly require the Resumable Upload Protocol.
    #    A standard direct multipart post might fail with 400/403 on the latest Gemini UI. 
    #    The correct modern flow usually entails:
    #      a. Initial POST to `https://content-push.googleapis.com/upload/` (or similar) 
    #         with headers: `X-Goog-Upload-Protocol: resumable`, `X-Goog-Upload-Command: start`.
    #      b. Read the `X-Goog-Upload-URL` from the response headers.
    #      c. PUT/POST the actual bytes (`file_content`) to that specific URL with `X-Goog-Upload-Offset: 0`.
    #
    # Action: If your `Endpoint.UPLOAD.value` still accepts a raw payload, the multipart fix below will work.
    # However, if it starts failing with 4xx errors, you must refactor `enums.py` and this function 
    # to implement the two-step `X-Goog-Upload-*` resumable protocol.
    
    headers = dict(Headers.UPLOAD.value)
    
    # 3. Request Execution using correct `multipart` (CurlMime) pattern
    try:
        async with AsyncSession(
            proxies=proxies_dict,
            impersonate=impersonate,
            headers=headers
        ) as client:
            
            # FIX: The outdated `files={"file": ...}` dict approach is strictly unsupported in modern curl_cffi.
            # We must construct a `CurlMime` object. This perfectly aligns with FastAPI compatibility 
            # and handles Base64-decoded frontend payloads cleanly.
            multipart = CurlMime()
            multipart.addpart(
                name="file",             # Form field name expected by the server
                content_type=content_type, # Automatically resolved image/jpeg, image/png, image/webp
                filename=filename,       # Essential for Google's backend to process the file type
                data=file_content        # Raw bytes
            )

            # Execution
            response = await client.post(
                url=Endpoint.UPLOAD.value, 
                multipart=multipart, # Injected modern payload parameter
                timeout=30.0 # Added explicit timeout for large image uploads
            )
            
            response.raise_for_status() 
            return response.text
            
    except HTTPError as e:
        console.log(f"[red]HTTP error during file upload: {e.response.status_code if e.response else 'Unknown'} {e}[/red]")
        raise 
    except (RequestException, CurlError, Timeout) as e: 
        console.log(f"[red]Network error during file upload: {e}[/red]")
        raise 


def load_cookies(cookie_path: str) -> Tuple[str, str]:
    """
    Loads authentication cookies from a JSON file.

    Args:
        cookie_path (str): Path to the JSON file containing cookies.

    Returns:
        tuple[str, str]: Tuple containing __Secure-1PSID and __Secure-1PSIDTS cookie values.

    Raises:
        Exception: If the file is not found, invalid, or required cookies are missing.
    """
    try:
        with open(cookie_path, 'r', encoding='utf-8') as file:
            cookies = json.load(file)
            
        session_auth1 = next((item['value'] for item in cookies if item['name'].upper() == '__SECURE-1PSID'), None)
        session_auth2 = next((item['value'] for item in cookies if item['name'].upper() == '__SECURE-1PSIDTS'), None)

        if not session_auth1 or not session_auth2:
             raise StopIteration("Required cookies (__Secure-1PSID or __Secure-1PSIDTS) not found.")

        return session_auth1, session_auth2
        
    except FileNotFoundError:
        raise Exception(f"Cookie file not found at path: {cookie_path}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON format in the cookie file.")
    except StopIteration as e:
        raise Exception(f"{e} Check the cookie file format and content.")
    except Exception as e: 
        raise Exception(f"An unexpected error occurred while loading cookies: {e}")