import json
import os
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, Query, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from salesgpt.salesgptapi import SalesGPTAPI

# Загружаем .env только локально
if os.getenv("ENVIRONMENT") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Переменные окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://react-frontend:80",
    "https://sales-gpt-frontend-git-main-filip-odysseypartns-projects.vercel.app",
    "https://sales-gpt-frontend.vercel.app"
]
CORS_METHODS = ["GET", "POST"]

# FastAPI-приложение
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=["*"],
)

class AuthenticatedResponse(BaseModel):
    message: str

def get_auth_key(authorization: str = Header(...)) -> None:
    auth_key = os.getenv("AUTH_KEY")
    if not auth_key:
        raise HTTPException(status_code=500, detail="AUTH_KEY not configured")
    expected_header = f"Bearer {auth_key}"
    if authorization != expected_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
async def say_hello():
    return {"message": "Hello World"}

class MessageList(BaseModel):
    session_id: str
    human_say: str

sessions = {}

@app.get("/botname")
async def get_bot_name(authorization: Optional[str] = Header(None)):
    if os.getenv("ENVIRONMENT") == "production":
        get_auth_key(authorization)

    sales_api = SalesGPTAPI(
        config_path=os.getenv("CONFIG_PATH", "examples/example_agent_setup.json"),
        product_catalog=os.getenv("PRODUCT_CATALOG", "examples/sample_product_catalog.txt"),
        verbose=True,
        model_name=os.getenv("GPT_MODEL", "gpt-3.5-turbo-0613"),
    )
    name = sales_api.sales_agent.salesperson_name
    return {"name": name, "model": sales_api.sales_agent.model_name}

@app.post("/chat")
async def chat_with_sales_agent(req: MessageList, stream: bool = Query(False), authorization: Optional[str] = Header(None)):
    sales_api = None
    if os.getenv("ENVIRONMENT") == "production":
        get_auth_key(authorization)

    if req.session_id in sessions:
        sales_api = sessions[req.session_id]
    else:
        sales_api = SalesGPTAPI(
            config_path=os.getenv("CONFIG_PATH", "examples/example_agent_setup.json"),
            verbose=True,
            product_catalog=os.getenv("PRODUCT_CATALOG", "examples/sample_product_catalog.txt"),
            model_name=os.getenv("GPT_MODEL", "gpt-3.5-turbo-0613"),
            use_tools=os.getenv("USE_TOOLS_IN_API", "True").lower() in ["true", "1", "t"],
        )
        sessions[req.session_id] = sales_api

    if stream:
        async def stream_response():
            stream_gen = sales_api.do_stream(req.conversation_history, req.human_say)
            async for message in stream_gen:
                yield json.dumps({"token": message}).encode("utf-8") + b"\n"
        return StreamingResponse(stream_response())

    response = await sales_api.do(req.human_say)
    return response
