from datetime import datetime
from app.db.mongo import agent_logs

async def log_agent_interaction(data: dict):
    data["timestamp"] = datetime.utcnow()
    await agent_logs.insert_one(data)
