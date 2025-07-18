from fastapi import APIRouter
from app.models.request_schemas import AgentQueryRequest
from app.models.response_schemas import AgentResponse
from app.services.agent_runner import run_agent

from fastapi import Query
from app.db.mongo import agent_logs

from app.services.agent_runner import llm
from datetime import datetime
from langchain_core.messages import AIMessage

router = APIRouter()


@router.post("/ask", response_model=AgentResponse)
async def ask_agent(req: AgentQueryRequest):
    reply = await run_agent(req.prompt, req.wallet_address)
    return {"response": reply}




@router.get("/logs")
async def get_logs(wallet_address: str = Query(..., description="Wallet address to filter logs")):
    cursor = agent_logs.find({"wallet_address": wallet_address}).sort("timestamp", -1).limit(20)
    logs = await cursor.to_list(length=20)

    # Convert ObjectId to string for JSON
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs


@router.get("/summary")
async def get_wallet_summary(wallet_address: str = Query(...), limit: int = 5):
    cursor = agent_logs.find({"wallet_address": wallet_address}).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)

    if not logs:
        return {"summary": "No history found for this wallet."}

    history = "\n---\n".join([
        f"Prompt: {log['user_prompt']}\nResponse: {log['agent_response']}" for log in logs
    ])

    prompt = f"""You are a crypto analysis assistant.Summarize the following interaction history for wallet {wallet_address} into 3-5 bullet points of DeFi advice/actions.
    {history}
"""

    result = llm.invoke(prompt)
    if isinstance(result, AIMessage):
        return {"summary": result.content}
    return {"summary": str(result)}

#------------------------
import re
from app.models. request_schemas import AgentQueryRequest
from app.services.wallet_utils import get_all_token_balances,get_erc20_balance,get_eth_balance
import aiohttp
from app.services.coingecko import fetch_token_prices

def build_prompt(eth, eth_usd, usdc, usdc_usd, link, link_usd, total, user_prompt):
    return f"""
You are a crypto portfolio rebalancing agent.

Based on the wallet's token holdings and market prices, generate **3 optimal portfolio strategies** with the following for each:
1. A strategy label (e.g., Conservative, Balanced)
2. Target % allocation across ETH, USDC, LINK
3. Rationale for the recommendation (risk, stability, yield, etc.)

Wallet Balances:
- ETH: {eth:.4f} (${eth_usd:,.2f})
- USDC: {usdc:.2f} (${usdc_usd:,.2f})
- LINK: {link:.2f} (${link_usd:,.2f})
Total Portfolio USD: ~${total:,.2f}

User request: {user_prompt}
"""

def parse_strategies(response: str):
    blocks = re.split(r"\n\s*\n", response.strip())
    strategies = []

    for block in blocks:
        lines = block.splitlines()
        if len(lines) >= 3:
            label = lines[0].strip(":- ")
            target = {}
            rationale = ""

            for line in lines[1:]:
                if "%" in line:
                    parts = re.findall(r"([A-Z]+)\s*[:\-]?\s*(\d+)%", line)
                    for token, percent in parts:
                        target[token] = int(percent)
                elif line.strip():
                    rationale += line.strip() + " "

            if target:
                strategies.append({
                    "label": label,
                    "target_allocation": target,
                    "rationale": rationale.strip()
                })
    return strategies

@router.post("/rebalance")
async def generate_rebalance(data: AgentQueryRequest):
    w_address = data.wallet_address
    user_prompt = data.prompt

    try:
        async with aiohttp.ClientSession() as session:
            eth = await get_eth_balance(w_address, session)
            usdc = await get_erc20_balance(address=w_address,contract_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",decimals=6, session=session )
            link = await get_erc20_balance(address=w_address,contract_address="0x514910771af9ca656af840dff83e8264ecf986ca", decimals=18, session=session)

        
        balances = {
            "ETH": eth,
            "USDC": usdc,
            "LINK": link
        }

        
        prices = await fetch_token_prices(list(balances.keys())) #returns prices in Us SDdollars

        
        usd_value = {
            symbol: round(balances[symbol] * prices.get(symbol, 0.0), 2)
            for symbol in balances
        }

        total_usd = round(sum(usd_value.values()), 2)

        
        prompt = build_prompt(
            eth, usd_value["ETH"],
            usdc, usd_value["USDC"],
            link, usd_value["LINK"],
            total_usd, user_prompt
        )

        print(f"\n[AGENT BALANCER PROMPT]\n{prompt}")

        
        response = llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        strategies = parse_strategies(raw)

        return {
            "balances": balances,
            "usd_value": usd_value,
            "strategies": strategies,
            "raw_agent_response": raw
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": str(e)}