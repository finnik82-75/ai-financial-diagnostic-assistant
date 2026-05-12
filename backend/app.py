import os
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import numpy as np
from openai import OpenAI

from .rag_index import load_index, search_similar


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Please set it in your environment or in a .env file."
    )

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="AI Financial Diagnostic Assistant",
    version="1.0.0-beta",
    description=(
        "AI assistant for financial diagnostics, cash flow analysis "
        "and business reporting explanations."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "http://72.56.241.226:5000",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    top_k: int = 3


class ChatResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]


INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index.bin")
META_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faqs_metadata.npy")

faiss_index, metadata = load_index(INDEX_PATH, META_PATH)


SYSTEM_PROMPT = """
Ты — AI-ассистент финансовой диагностики бизнеса.

Твоя задача:
объяснять собственнику бизнеса, что происходит с прибылью, расходами и денежными потоками компании.

Правила ответа:
- отвечай максимально кратко и по существу;
- используй простой управленческий язык;
- не используй сложную терминологию;
- не повторяй одну и ту же мысль;
- не пересказывай контекст полностью;
- сначала вывод, потом причины и рекомендации;
- пиши как финансовый директор, а не как учебник;
- ответ должен читаться за 5–7 секунд;
- не более 2 коротких абзацев;
- избегай длинных рекомендаций.

Если данных недостаточно — прямо говори об этом.
Не выдумывай цифры и факты.
Используй только предоставленный контекст.
"""


def embed_text(texts: List[str]) -> np.ndarray:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    vectors = [d.embedding for d in response.data]
    return np.array(vectors, dtype="float32")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is empty")

    query_vec = embed_text([req.message])
    similar_items = search_similar(faiss_index, metadata, query_vec, k=req.top_k)

    context_text = "\n\n".join(
        [f"Q: {item['question']}\nA: {item['answer']}" for item in similar_items]
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Вопрос пользователя: {req.message}\n\n"
                f"Контекст базы знаний:\n{context_text}"
            ),
        },
    ]

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.2,
    )

    answer = completion.choices[0].message.content

    return ChatResponse(answer=answer, context=similar_items)


@app.get("/health")
async def health():
    return {"status": "ok"}