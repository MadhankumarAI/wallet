from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import wallet, agent, tx
from app.services.rebalance import router as rebalance_router
from app.routes.execution import router as execution_router

app = FastAPI(
    title="AI Crypto Wallet Assistant",
    description="Backend for AI-powered crypto wallet assistant using FastAPI, LangChain, and Groq.",
    version="0.1.0"
)

#cors middleware is established so that fe can connect with be
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(execution_router, tags=["Execution"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(agent.router, prefix="/agent", tags=["AI Agent"])
app.include_router(tx.router, prefix="/transaction", tags=["Transaction"])
app.include_router(rebalance_router)

@app.get("/")
def root():
    return {"status": "Backend running", "message": "Crypto Wallet Assistant API"}


