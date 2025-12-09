from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import market, auth, predict, chat

app = FastAPI(title="Infosys Stock AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api/market", tags=["Market Data"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(predict.router, prefix="/api/predict", tags=["AI Predictions"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chatbot"])

@app.get("/")
async def root():
    return {"status": "Service is running"}