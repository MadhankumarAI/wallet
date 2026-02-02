"""
Autonomous Agent API Endpoints

These endpoints control the 24/7 autonomous monitoring and execution system.
They allow users to:
1. Enable/disable autonomous monitoring for their wallets
2. Configure monitoring parameters (drift thresholds, risk profiles, etc.)
3. View autonomous actions and decisions
4. Control the autonomous service (start/stop)
5. Get real-time monitoring status

This is separate from the existing chatbot + execution pipeline endpoints.
"""

import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.services.autonomous_agent import (
    autonomous_agent_service, 
    MonitoringConfig
)
from app.db.mongo import (
    wallet_monitoring_configs, 
    autonomous_agent_logs,
    executions
)
from app.middleware.auth import get_current_user
from app.models.user import UserResponse

router = APIRouter(prefix="/autonomous", tags=["Autonomous Agent"])

# Request/Response Models
class WalletMonitoringRequest(BaseModel):
    """Request to add/update wallet monitoring configuration"""
    wallet_address: str
    enabled: bool = True
    check_interval_minutes: int = 15
    drift_threshold_percent: float = 5.0
    max_daily_trades: int = 3
    risk_profile: str = "balanced"  # conservative, balanced, aggressive
    auto_execute: bool = False
    slippage_tolerance: float = 1.0
    min_portfolio_value_usd: float = 100.0

class WalletDeleteRequest(BaseModel):
    """Request to delete wallet from monitoring"""
    wallet_address: str

class WalletMonitoringResponse(BaseModel):
    """Response for wallet monitoring configuration"""
    wallet_address: str
    enabled: bool
    check_interval_minutes: int
    drift_threshold_percent: float
    max_daily_trades: int
    risk_profile: str
    auto_execute: bool
    slippage_tolerance: float
    min_portfolio_value_usd: float
    created_at: datetime
    last_check: Optional[datetime]
    daily_trades_count: int
    last_trade_reset: datetime

class AutonomousActionLog(BaseModel):
    """Autonomous action log entry"""
    action_id: str
    wallet_address: str
    action_type: str
    drift_analysis: Dict
    target_allocation: Dict
    timestamp: datetime
    config_used: Dict

class AutonomousExecution(BaseModel):
    """Autonomous execution record"""
    execution_id: str
    wallet_address: str
    strategy_id: str
    target_allocation: Dict
    current_balances: Dict
    trades_executed: Dict
    tx_hash: str
    status: str
    created_at: datetime
    network: str
    execution_type: str
    drift_analysis: Dict

class ServiceStatusResponse(BaseModel):
    """Autonomous service status"""
    service_running: bool
    total_monitored_wallets: int
    active_monitored_wallets: int
    active_monitoring_tasks: int
    last_market_check: Optional[str]
    recent_autonomous_actions: int
    recent_autonomous_executions: int
    market_conditions: Dict

# Endpoints

@router.post("/monitor/wallet", response_model=WalletMonitoringResponse)
async def add_wallet_to_monitoring(
    request: WalletMonitoringRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Add a wallet to autonomous monitoring.
    
    This enables 24/7 monitoring of the wallet for portfolio drift
    and automatic rebalancing when conditions are met.
    """
    try:
        # Validate risk profile
        if request.risk_profile not in ["conservative", "balanced", "aggressive"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid risk profile. Must be conservative, balanced, or aggressive"
            )
        
        # Validate drift threshold
        if request.drift_threshold_percent < 1.0 or request.drift_threshold_percent > 50.0:
            raise HTTPException(
                status_code=400,
                detail="Drift threshold must be between 1.0% and 50.0%"
            )
        
        # Validate check interval
        if request.check_interval_minutes < 5 or request.check_interval_minutes > 1440:
            raise HTTPException(
                status_code=400,
                detail="Check interval must be between 5 minutes and 24 hours (1440 minutes)"
            )
        
        # Create monitoring configuration
        config = MonitoringConfig(
            wallet_address=request.wallet_address,
            enabled=request.enabled,
            check_interval_minutes=request.check_interval_minutes,
            drift_threshold_percent=request.drift_threshold_percent,
            max_daily_trades=request.max_daily_trades,
            risk_profile=request.risk_profile,
            auto_execute=request.auto_execute,
            slippage_tolerance=request.slippage_tolerance,
            min_portfolio_value_usd=request.min_portfolio_value_usd
        )
        
        # Add to autonomous monitoring
        await autonomous_agent_service.add_wallet_to_monitoring(config)
        
        # Get the saved configuration
        saved_config = await wallet_monitoring_configs.find_one(
            {"wallet_address": request.wallet_address}
        )
        
        if not saved_config:
            raise HTTPException(status_code=500, detail="Failed to save monitoring configuration")
        
        # Convert ObjectId to string
        saved_config["_id"] = str(saved_config["_id"])
        
        return WalletMonitoringResponse(**saved_config)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add wallet to monitoring: {str(e)}"
        )

@router.post("/monitor/wallet/public", response_model=WalletMonitoringResponse)
async def add_wallet_to_monitoring_public(
    request: WalletMonitoringRequest
):
    """
    Add a wallet to autonomous monitoring (public endpoint for testing).
    
    This enables 24/7 monitoring of the wallet for portfolio drift
    and automatic rebalancing when conditions are met.
    """
    try:
        print(f"[DEBUG] Public endpoint called with wallet: {request.wallet_address}")
        print(f"[DEBUG] Request data: {request}")
        
        # Validate risk profile
        if request.risk_profile not in ["conservative", "balanced", "aggressive"]:
            print(f"[DEBUG] Invalid risk profile: {request.risk_profile}")
            raise HTTPException(
                status_code=400, 
                detail="Invalid risk profile. Must be conservative, balanced, or aggressive"
            )
        
        # Validate drift threshold
        if request.drift_threshold_percent < 1.0 or request.drift_threshold_percent > 50.0:
            print(f"[DEBUG] Invalid drift threshold: {request.drift_threshold_percent}")
            raise HTTPException(
                status_code=400,
                detail="Drift threshold must be between 1.0% and 50.0%"
            )
        
        # Validate check interval
        if request.check_interval_minutes < 5 or request.check_interval_minutes > 1440:
            print(f"[DEBUG] Invalid check interval: {request.check_interval_minutes}")
            raise HTTPException(
                status_code=400,
                detail="Check interval must be between 5 minutes and 24 hours (1440 minutes)"
            )
        
        print(f"[DEBUG] Validation passed, creating config...")
        
        # Create monitoring configuration
        config = MonitoringConfig(
            wallet_address=request.wallet_address,
            enabled=request.enabled,
            check_interval_minutes=request.check_interval_minutes,
            drift_threshold_percent=request.drift_threshold_percent,
            max_daily_trades=request.max_daily_trades,
            risk_profile=request.risk_profile,
            auto_execute=request.auto_execute,
            slippage_tolerance=request.slippage_tolerance,
            min_portfolio_value_usd=request.min_portfolio_value_usd
        )
        
        print(f"[DEBUG] Config created: {config}")
        print(f"[DEBUG] Calling autonomous_agent_service.add_wallet_to_monitoring...")
        
        # Add to autonomous monitoring
        await autonomous_agent_service.add_wallet_to_monitoring(config)
        
        print(f"[DEBUG] Service call completed, fetching saved config...")
        
        # Get the saved configuration
        saved_config = await wallet_monitoring_configs.find_one(
            {"wallet_address": request.wallet_address}
        )
        
        print(f"[DEBUG] Saved config from DB: {saved_config}")
        
        if not saved_config:
            print(f"[DEBUG] No saved config found in DB!")
            raise HTTPException(status_code=500, detail="Failed to save monitoring configuration")
        
        # Convert ObjectId to string
        saved_config["_id"] = str(saved_config["_id"])
        
        print(f"[DEBUG] Returning response: {saved_config}")
        return WalletMonitoringResponse(**saved_config)
        
    except HTTPException:
        print(f"[DEBUG] HTTPException raised, re-raising...")
        raise
    except Exception as e:
        print(f"[DEBUG] Unexpected error: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add wallet to monitoring: {str(e)}"
        )

@router.get("/monitor/wallet/{wallet_address}", response_model=WalletMonitoringResponse)
async def get_wallet_monitoring_config(
    wallet_address: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get monitoring configuration for a specific wallet"""
    try:
        config = await wallet_monitoring_configs.find_one({"wallet_address": wallet_address})
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found in monitoring"
            )
        
        # Convert ObjectId to string
        config["_id"] = str(config["_id"])
        
        return WalletMonitoringResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitoring configuration: {str(e)}"
        )

@router.put("/monitor/wallet/{wallet_address}", response_model=WalletMonitoringResponse)
async def update_wallet_monitoring(
    wallet_address: str,
    request: WalletMonitoringRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update monitoring configuration for a wallet"""
    try:
        # Validate the request
        if request.risk_profile not in ["conservative", "balanced", "aggressive"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid risk profile. Must be conservative, balanced, or aggressive"
            )
        
        if request.drift_threshold_percent < 1.0 or request.drift_threshold_percent > 50.0:
            raise HTTPException(
                status_code=400,
                detail="Drift threshold must be between 1.0% and 50.0%"
            )
        
        # Update the configuration
        update_data = {
            "enabled": request.enabled,
            "check_interval_minutes": request.check_interval_minutes,
            "drift_threshold_percent": request.drift_threshold_percent,
            "max_daily_trades": request.max_daily_trades,
            "risk_profile": request.risk_profile,
            "auto_execute": request.auto_execute,
            "slippage_tolerance": request.slippage_tolerance,
            "min_portfolio_value_usd": request.min_portfolio_value_usd,
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = await wallet_monitoring_configs.update_one(
            {"wallet_address": wallet_address},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found in monitoring"
            )
        
        # Get updated configuration
        updated_config = await wallet_monitoring_configs.find_one(
            {"wallet_address": wallet_address}
        )
        
        # Convert ObjectId to string
        updated_config["_id"] = str(updated_config["_id"])
        
        return WalletMonitoringResponse(**updated_config)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update monitoring configuration: {str(e)}"
        )

@router.delete("/monitor/wallet/public")
async def remove_wallet_from_monitoring_public(
    request: WalletDeleteRequest
):
    """Remove a wallet from autonomous monitoring (public endpoint for testing)"""
    try:
        wallet_address = request.wallet_address
        
        await autonomous_agent_service.remove_wallet_from_monitoring(wallet_address)
        
        return {
            "status": "success",
            "message": f"Wallet {wallet_address} removed from autonomous monitoring"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove wallet from monitoring: {str(e)}"
        )

@router.delete("/monitor/wallet/{wallet_address}")
async def remove_wallet_from_monitoring(
    wallet_address: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Remove a wallet from autonomous monitoring"""
    try:
        await autonomous_agent_service.remove_wallet_from_monitoring(wallet_address)
        
        return {
            "status": "success",
            "message": f"Wallet {wallet_address} removed from autonomous monitoring"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove wallet from monitoring: {str(e)}"
        )

@router.get("/monitor/wallets", response_model=List[WalletMonitoringResponse])
async def get_all_monitored_wallets(
    current_user: UserResponse = Depends(get_current_user),
    enabled_only: bool = False
):
    """Get all wallets under autonomous monitoring"""
    try:
        query = {}
        if enabled_only:
            query["enabled"] = True
        
        configs = await wallet_monitoring_configs.find(query).to_list(length=None)
        
        # Convert ObjectIds to strings
        for config in configs:
            config["_id"] = str(config["_id"])
        
        return [WalletMonitoringResponse(**config) for config in configs]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitored wallets: {str(e)}"
        )

@router.get("/monitor/wallets/public", response_model=List[WalletMonitoringResponse])
async def get_all_monitored_wallets_public(
    enabled_only: bool = False
):
    """Get all wallets under autonomous monitoring (public endpoint for testing)"""
    try:
        query = {}
        if enabled_only:
            query["enabled"] = True
        
        configs = await wallet_monitoring_configs.find(query).to_list(length=None)
        
        # Convert ObjectIds to strings
        for config in configs:
            config["_id"] = str(config["_id"])
        
        return [WalletMonitoringResponse(**config) for config in configs]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitored wallets: {str(e)}"
        )

@router.get("/actions/{wallet_address}", response_model=List[AutonomousActionLog])
async def get_autonomous_actions(
    wallet_address: str,
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 50,
    action_type: Optional[str] = None
):
    """Get autonomous actions for a specific wallet"""
    try:
        query = {"wallet_address": wallet_address}
        if action_type:
            query["action_type"] = action_type
        
        cursor = autonomous_agent_logs.find(query).sort("timestamp", -1).limit(limit)
        actions = await cursor.to_list(length=limit)
        
        # Convert ObjectIds to strings
        for action in actions:
            action["_id"] = str(action["_id"])
        
        return [AutonomousActionLog(**action) for action in actions]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get autonomous actions: {str(e)}"
        )

@router.get("/actions/public", response_model=List[AutonomousActionLog])
async def get_autonomous_actions_public(
    limit: int = 50,
    action_type: Optional[str] = None
):
    """Get recent autonomous actions (public endpoint for testing)"""
    try:
        query = {}
        if action_type:
            query["action_type"] = action_type
        
        cursor = autonomous_agent_logs.find(query).sort("timestamp", -1).limit(limit)
        actions = await cursor.to_list(length=limit)
        
        # Convert ObjectIds to strings
        for action in actions:
            action["_id"] = str(action["_id"])
        
        return [AutonomousActionLog(**action) for action in actions]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get autonomous actions: {str(e)}"
        )

# Also add a general actions endpoint without wallet address requirement
@router.get("/actions", response_model=List[AutonomousActionLog])
async def get_all_autonomous_actions_public(
    limit: int = 50,
    action_type: Optional[str] = None
):
    """Get recent autonomous actions for all wallets (public endpoint for testing)"""
    try:
        query = {}
        if action_type:
            query["action_type"] = action_type
        
        cursor = autonomous_agent_logs.find(query).sort("timestamp", -1).limit(limit)
        actions = await cursor.to_list(length=limit)
        
        # Convert ObjectIds to strings
        for action in actions:
            action["_id"] = str(action["_id"])
        
        return [AutonomousActionLog(**action) for action in actions]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get autonomous actions: {str(e)}"
        )

@router.get("/executions/{wallet_address}", response_model=List[AutonomousExecution])
async def get_autonomous_executions(
    wallet_address: str,
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 50,
    status: Optional[str] = None
):
    """Get autonomous executions for a specific wallet"""
    try:
        query = {
            "wallet_address": wallet_address,
            "execution_type": "autonomous"
        }
        
        if status:
            query["status"] = status
        
        cursor = executions.find(query).sort("created_at", -1).limit(limit)
        execution_list = await cursor.to_list(length=limit)
        
        # Convert ObjectIds to strings
        for execution in execution_list:
            execution["_id"] = str(execution["_id"])
        
        return [AutonomousExecution(**execution) for execution in execution_list]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get autonomous executions: {str(e)}"
        )

@router.get("/status", response_model=ServiceStatusResponse)
async def get_autonomous_service_status(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current status of the autonomous agent service"""
    try:
        status = await autonomous_agent_service.get_monitoring_status()
        return ServiceStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get service status: {str(e)}"
        )

@router.get("/status/public", response_model=ServiceStatusResponse)
async def get_autonomous_service_status_public():
    """Get current status of the autonomous agent service (public endpoint for testing)"""
    try:
        status = await autonomous_agent_service.get_monitoring_status()
        return ServiceStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get service status: {str(e)}"
        )

@router.post("/service/start")
async def start_autonomous_service(
    current_user: UserResponse = Depends(get_current_user)
):
    """Start the autonomous agent service"""
    try:
        await autonomous_agent_service.start_monitoring()
        
        return {
            "status": "success",
            "message": "Autonomous agent service started successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start autonomous service: {str(e)}"
        )

@router.post("/service/start/public")
async def start_autonomous_service_public():
    """Start the autonomous agent service (public endpoint for testing)"""
    try:
        await autonomous_agent_service.start_monitoring()
        
        return {
            "status": "success",
            "message": "Autonomous agent service started successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start autonomous service: {str(e)}"
        )

@router.post("/service/stop")
async def stop_autonomous_service(
    current_user: UserResponse = Depends(get_current_user)
):
    """Stop the autonomous agent service"""
    try:
        await autonomous_agent_service.stop_monitoring()
        
        return {
            "status": "success",
            "message": "Autonomous agent service stopped successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop autonomous service: {str(e)}"
        )

@router.post("/service/stop/public")
async def stop_autonomous_service_public():
    """Stop the autonomous agent service (public endpoint for testing)"""
    try:
        await autonomous_agent_service.stop_monitoring()
        
        return {
            "status": "success",
            "message": "Autonomous agent service stopped successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop autonomous service: {str(e)}"
        )

@router.post("/service/restart")
async def restart_autonomous_service(
    current_user: UserResponse = Depends(get_current_user)
):
    """Restart the autonomous agent service"""
    try:
        await autonomous_agent_service.stop_monitoring()
        await asyncio.sleep(2)  # Brief pause
        await autonomous_agent_service.start_monitoring()
        
        return {
            "status": "success",
            "message": "Autonomous agent service restarted successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart autonomous service: {str(e)}"
        )

@router.get("/market/conditions")
async def get_current_market_conditions(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current market conditions assessment"""
    try:
        status = await autonomous_agent_service.get_monitoring_status()
        market_conditions = status.get("market_conditions", {})
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_conditions": market_conditions,
            "last_updated": status.get("last_market_check")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get market conditions: {str(e)}"
        )

@router.post("/force-check/{wallet_address}")
async def force_wallet_check(
    wallet_address: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Force an immediate check of a specific wallet"""
    try:
        # Get the wallet's monitoring configuration
        config = await wallet_monitoring_configs.find_one({"wallet_address": wallet_address})
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found in monitoring"
            )
        
        if not config.get("enabled"):
            raise HTTPException(
                status_code=400,
                detail="Wallet monitoring is disabled"
            )
        
        # Force a check by updating the last_check time to trigger immediate monitoring
        await wallet_monitoring_configs.update_one(
            {"wallet_address": wallet_address},
            {"$set": {"last_check": None}}  # This will trigger immediate check
        )
        
        return {
            "status": "success",
            "message": f"Forced check scheduled for wallet {wallet_address}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to force wallet check: {str(e)}"
        )

@router.get("/analytics/summary")
async def get_autonomous_analytics_summary(
    current_user: UserResponse = Depends(get_current_user),
    days: int = 7
):
    """Get summary analytics for autonomous operations"""
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Count autonomous actions
        total_actions = await autonomous_agent_logs.count_documents({
            "timestamp": {"$gte": cutoff_date}
        })
        
        # Count autonomous executions
        total_executions = await executions.count_documents({
            "execution_type": "autonomous",
            "created_at": {"$gte": cutoff_date}
        })
        
        # Count successful executions
        successful_executions = await executions.count_documents({
            "execution_type": "autonomous",
            "status": "confirmed",
            "created_at": {"$gte": cutoff_date}
        })
        
        # Count monitored wallets
        total_monitored = await wallet_monitoring_configs.count_documents({})
        active_monitored = await wallet_monitoring_configs.count_documents({"enabled": True})
        
        # Get most active wallets
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_date}}},
            {"$group": {"_id": "$wallet_address", "action_count": {"$sum": 1}}},
            {"$sort": {"action_count": -1}},
            {"$limit": 5}
        ]
        
        most_active_wallets = await autonomous_agent_logs.aggregate(pipeline).to_list(length=5)
        
        return {
            "period_days": days,
            "total_autonomous_actions": total_actions,
            "total_autonomous_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            "total_monitored_wallets": total_monitored,
            "active_monitored_wallets": active_monitored,
            "most_active_wallets": [
                {
                    "wallet_address": wallet["_id"],
                    "action_count": wallet["action_count"]
                }
                for wallet in most_active_wallets
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics summary: {str(e)}"
        )
