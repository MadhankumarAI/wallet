"""
Autonomous Agent Service for 24/7 Portfolio Monitoring and Auto-Execution

This service runs continuously in the background to:
1. Monitor wallet portfolios for drift from target allocations
2. Watch market conditions for optimal entry/exit points
3. Automatically execute rebalancing strategies when conditions are met
4. Manage risk and prevent excessive trading
5. Log all autonomous decisions and actions

The service integrates with existing rebalance and execution services.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid

from app.services.wallet_utils import get_eth_balance, get_erc20_balance
from app.services.coingecko import fetch_token_prices
from app.services.web3_utils import execute_rebalance_transaction, estimate_gas_fees
from app.db.mongo import (
    strategies, executions,
    autonomous_agent_logs, wallet_monitoring_configs
)

logger = logging.getLogger(__name__)

@dataclass
class MonitoringConfig:
    """Configuration for autonomous wallet monitoring"""
    wallet_address: str
    enabled: bool = True
    check_interval_minutes: int = 15  # How often to check this wallet
    drift_threshold_percent: float = 5.0  # % drift before triggering rebalance
    max_daily_trades: int = 3  # Maximum trades per day
    risk_profile: str = "balanced"  # conservative, balanced, aggressive
    auto_execute: bool = False  # Whether to auto-execute or just suggest
    slippage_tolerance: float = 1.0  # Max slippage % for trades
    min_portfolio_value_usd: float = 100.0  # Minimum portfolio value to monitor

@dataclass
class MarketCondition:
    """Market condition assessment"""
    volatility_high: bool
    trend_direction: str  # "bullish", "bearish", "sideways"
    volume_spike: bool
    correlation_breakdown: bool
    risk_score: float  # 0-100, higher = more risky

@dataclass
class PortfolioDrift:
    """Portfolio drift analysis"""
    total_drift_percent: float
    token_drifts: Dict[str, float]  # % drift for each token
    needs_rebalancing: bool
    suggested_allocation: Dict[str, float]
    urgency_level: str  # "low", "medium", "high", "critical"

class AutonomousAgentService:
    """
    Autonomous agent that continuously monitors wallets and executes strategies
    """
    
    def __init__(self):
        self.is_running = False
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.last_market_check = None
        self.market_conditions_cache = {}
        
    async def start_monitoring(self):
        """Start the autonomous monitoring service"""
        if self.is_running:
            logger.info("Autonomous agent already running")
            return
            
        logger.info("Starting autonomous agent service...")
        self.is_running = True
        
        # Start background tasks
        asyncio.create_task(self._market_monitor_loop())
        asyncio.create_task(self._wallet_monitor_loop())
        
        logger.info("Autonomous agent service started successfully")
    
    async def stop_monitoring(self):
        """Stop the autonomous monitoring service"""
        logger.info("Stopping autonomous agent service...")
        self.is_running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        self.monitoring_tasks.clear()
        logger.info("Autonomous agent service stopped")
    
    async def add_wallet_to_monitoring(self, config: MonitoringConfig):
        """Add a wallet to autonomous monitoring"""
        try:
            # Save monitoring configuration
            config_dict = {
                "wallet_address": config.wallet_address,
                "enabled": config.enabled,
                "check_interval_minutes": config.check_interval_minutes,
                "drift_threshold_percent": config.drift_threshold_percent,
                "max_daily_trades": config.max_daily_trades,
                "risk_profile": config.risk_profile,
                "auto_execute": config.auto_execute,
                "slippage_tolerance": config.slippage_tolerance,
                "min_portfolio_value_usd": config.min_portfolio_value_usd,
                "created_at": datetime.now(timezone.utc),
                "last_check": None,
                "daily_trades_count": 0,
                "last_trade_reset": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            }
            
            await wallet_monitoring_configs.update_one(
                {"wallet_address": config.wallet_address},
                {"$set": config_dict},
                upsert=True
            )
            
            # Start monitoring task for this wallet
            if config.enabled:
                await self._start_wallet_monitoring(config.wallet_address)
            
            logger.info(f"Added wallet {config.wallet_address} to autonomous monitoring")
            
        except Exception as e:
            logger.error(f"Failed to add wallet to monitoring: {str(e)}")
            raise
    
    async def remove_wallet_from_monitoring(self, wallet_address: str):
        """Remove a wallet from autonomous monitoring"""
        try:
            # Stop monitoring task
            if wallet_address in self.monitoring_tasks:
                self.monitoring_tasks[wallet_address].cancel()
                del self.monitoring_tasks[wallet_address]
            
            # Remove from database
            await wallet_monitoring_configs.delete_one({"wallet_address": wallet_address})
            
            logger.info(f"Removed wallet {wallet_address} from autonomous monitoring")
            
        except Exception as e:
            logger.error(f"Failed to remove wallet from monitoring: {str(e)}")
            raise
    
    async def _market_monitor_loop(self):
        """Background loop for monitoring market conditions"""
        while self.is_running:
            try:
                await self._assess_market_conditions()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in market monitor loop: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _wallet_monitor_loop(self):
        """Background loop for monitoring individual wallets"""
        while self.is_running:
            try:
                # Get all wallets that need monitoring
                configs = await wallet_monitoring_configs.find({"enabled": True}).to_list(length=None)
                
                for config in configs:
                    wallet_address = config["wallet_address"]
                    check_interval = config["check_interval_minutes"]
                    last_check = config.get("last_check")
                    
                    # Check if it's time to monitor this wallet
                    if (last_check is None or 
                        datetime.now(timezone.utc) - last_check > timedelta(minutes=check_interval)):
                        
                        # Start or restart monitoring task
                        await self._start_wallet_monitoring(wallet_address)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in wallet monitor loop: {str(e)}")
                await asyncio.sleep(60)
    
    async def _start_wallet_monitoring(self, wallet_address: str):
        """Start monitoring for a specific wallet"""
        if wallet_address in self.monitoring_tasks:
            # Cancel existing task if running
            self.monitoring_tasks[wallet_address].cancel()
        
        # Create new monitoring task
        task = asyncio.create_task(self._monitor_single_wallet(wallet_address))
        self.monitoring_tasks[wallet_address] = task
        
        logger.info(f"Started monitoring task for wallet {wallet_address}")
    
    async def _monitor_single_wallet(self, wallet_address: str):
        """Monitor a single wallet for portfolio drift and market opportunities"""
        try:
            # Get monitoring configuration
            config = await wallet_monitoring_configs.find_one({"wallet_address": wallet_address})
            if not config or not config.get("enabled"):
                return
            
            # Check daily trade limit
            if not await self._can_trade_today(wallet_address, config):
                logger.info(f"Daily trade limit reached for wallet {wallet_address}")
                return
            
            # Get current portfolio state
            portfolio_state = await self._get_portfolio_state(wallet_address)
            if not portfolio_state:
                logger.warning(f"Could not get portfolio state for wallet {wallet_address}, skipping monitoring cycle")
                return
            
            # Check if portfolio meets minimum value requirement
            total_value = portfolio_state.get("total_usd_value", 0)
            if total_value < config["min_portfolio_value_usd"]:
                logger.info(f"Portfolio value {total_value} below minimum {config['min_portfolio_value_usd']} for wallet {wallet_address}")
                return
            
            # Assess portfolio drift
            drift_analysis = await self._analyze_portfolio_drift(wallet_address, portfolio_state)
            
            # Check market conditions
            market_conditions = self.market_conditions_cache.get("current", {})
            
            # Decide if action is needed
            if await self._should_take_action(drift_analysis, market_conditions, config):
                await self._execute_autonomous_action(wallet_address, drift_analysis, config)
            
            # Update last check time
            await wallet_monitoring_configs.update_one(
                {"wallet_address": wallet_address},
                {"$set": {"last_check": datetime.now(timezone.utc)}}
            )
            
        except Exception as e:
            logger.error(f"Error monitoring wallet {wallet_address}: {str(e)}")
    
    async def _assess_market_conditions(self):
        """Assess current market conditions"""
        try:
            # Get market data for major tokens
            tokens = ["ETH", "USDC", "LINK"]
            prices = await fetch_token_prices(tokens)
            
            # Calculate volatility (simplified - in production, use proper volatility calculation)
            # For now, we'll use a basic approach
            volatility_high = False  # TODO: Implement proper volatility calculation
            
            # Determine trend direction (simplified)
            trend_direction = "sideways"  # TODO: Implement trend analysis
            
            # Check for volume spikes (would need volume data from CoinGecko or similar)
            volume_spike = False
            
            # Assess correlation breakdown
            correlation_breakdown = False
            
            # Calculate risk score
            risk_score = 50.0  # TODO: Implement proper risk scoring
            
            market_conditions = MarketCondition(
                volatility_high=volatility_high,
                trend_direction=trend_direction,
                volume_spike=volume_spike,
                correlation_breakdown=correlation_breakdown,
                risk_score=risk_score
            )
            
            # Cache market conditions as dict for easier access
            self.market_conditions_cache["current"] = {
                "volatility_high": market_conditions.volatility_high,
                "trend_direction": market_conditions.trend_direction,
                "volume_spike": market_conditions.volume_spike,
                "correlation_breakdown": market_conditions.correlation_breakdown,
                "risk_score": market_conditions.risk_score
            }
            self.last_market_check = datetime.now(timezone.utc)
            
            logger.debug(f"Market conditions assessed: {market_conditions}")
            
        except Exception as e:
            logger.error(f"Error assessing market conditions: {str(e)}")
    
    async def _get_portfolio_state(self, wallet_address: str) -> Optional[Dict]:
        """Get current portfolio state for a wallet"""
        try:
            async with asyncio.timeout(30):  # 30 second timeout
                # Get balances with null checks
                eth_balance = await get_eth_balance(wallet_address, None)
                usdc_balance = await get_erc20_balance(
                    wallet_address,
                    "0x14A3Fb98C14759169f998155ba4c31d1393D6D7c",  # Sepolia USDC
                    6,
                    None
                )
                link_balance = await get_erc20_balance(
                    wallet_address,
                    "0x779877A7B0D9E8603169DdbD7836e478b4624789",  # Sepolia LINK
                    18,
                    None
                )
                
                # Handle None values from balance functions
                if eth_balance is None:
                    eth_balance = 0.0
                if usdc_balance is None:
                    usdc_balance = 0.0
                if link_balance is None:
                    link_balance = 0.0
                
                # Get prices
                prices = await fetch_token_prices(["ETH", "USDC", "LINK"])
                
                # Handle None prices
                if not prices or any(price is None for price in prices.values()):
                    logger.warning(f"Some token prices are None for {wallet_address}, using default values")
                    prices = {"ETH": 2000.0, "USDC": 1.0, "LINK": 15.0}  # Default fallback prices
                
                balances = {
                    "ETH": eth_balance,
                    "USDC": usdc_balance,
                    "LINK": link_balance
                }
                
                usd_values = {
                    symbol: balances[symbol] * prices[symbol]
                    for symbol in balances
                }
                
                total_usd_value = sum(usd_values.values())
                
                return {
                    "balances": balances,
                    "usd_values": usd_values,
                    "total_usd_value": total_usd_value,
                    "prices": prices,
                    "timestamp": datetime.now(timezone.utc)
                }
                
        except Exception as e:
            logger.error(f"Error getting portfolio state for {wallet_address}: {str(e)}")
            return None
    
    async def _analyze_portfolio_drift(self, wallet_address: str, portfolio_state: Dict) -> PortfolioDrift:
        """Analyze portfolio drift from target allocation"""
        try:
            # Check if portfolio_state is valid
            if not portfolio_state or not isinstance(portfolio_state, dict):
                logger.warning(f"Invalid portfolio state for {wallet_address}, using default allocation")
                return PortfolioDrift(
                    total_drift_percent=0,
                    token_drifts={},
                    needs_rebalancing=False,
                    suggested_allocation={"ETH": 40, "USDC": 30, "LINK": 30},
                    urgency_level="low"
                )
            
            # Get the most recent strategy for this wallet
            strategy = await strategies.find_one(
                {"wallet_address": wallet_address},
                sort=[("created_at", -1)]
            )
            
            if not strategy:
                # No strategy found, create a default balanced allocation
                target_allocation = {"ETH": 40, "USDC": 30, "LINK": 30}
            else:
                target_allocation = strategy.get("target_allocation", {"ETH": 40, "USDC": 30, "LINK": 30})
            
            # Calculate current allocation percentages
            total_value = portfolio_state.get("total_usd_value", 0)
            if total_value == 0:
                return PortfolioDrift(
                    total_drift_percent=0,
                    token_drifts={},
                    needs_rebalancing=False,
                    suggested_allocation=target_allocation,
                    urgency_level="low"
                )
            
            current_allocation = {}
            usd_values = portfolio_state.get("usd_values", {})
            for token, usd_value in usd_values.items():
                current_allocation[token] = (usd_value / total_value) * 100
            
            # Calculate drift for each token
            token_drifts = {}
            total_drift = 0
            
            for token in target_allocation:
                target_pct = target_allocation[token]
                current_pct = current_allocation.get(token, 0)
                drift = abs(current_pct - target_pct)
                token_drifts[token] = drift
                total_drift += drift
            
            # Determine if rebalancing is needed
            needs_rebalancing = total_drift > 10  # 10% total drift threshold
            
            # Determine urgency level
            if total_drift > 20:
                urgency_level = "critical"
            elif total_drift > 15:
                urgency_level = "high"
            elif total_drift > 10:
                urgency_level = "medium"
            else:
                urgency_level = "low"
            
            return PortfolioDrift(
                total_drift_percent=total_drift,
                token_drifts=token_drifts,
                needs_rebalancing=needs_rebalancing,
                suggested_allocation=target_allocation,
                urgency_level=urgency_level
            )
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio drift: {str(e)}")
            return PortfolioDrift(
                total_drift_percent=0,
                token_drifts={},
                needs_rebalancing=False,
                suggested_allocation={},
                urgency_level="low"
            )
    
    async def _should_take_action(self, drift_analysis: PortfolioDrift, 
                                market_conditions: Dict, config: Dict) -> bool:
        """Determine if autonomous action should be taken"""
        try:
            # Check if drift is above threshold
            if not drift_analysis.needs_rebalancing:
                return False
            
            # Check drift threshold from config
            if drift_analysis.total_drift_percent < config["drift_threshold_percent"]:
                return False
            
            # Check risk profile considerations
            if config["risk_profile"] == "conservative":
                # Only act on high urgency for conservative profiles
                if drift_analysis.urgency_level not in ["high", "critical"]:
                    return False
            
            # Check market conditions
            if market_conditions:
                risk_score = market_conditions.get("risk_score", 50)
                if risk_score > 80:  # Very high risk
                    logger.info("Market risk too high, skipping autonomous action")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error determining if action should be taken: {str(e)}")
            return False
    
    async def _execute_autonomous_action(self, wallet_address: str, 
                                       drift_analysis: PortfolioDrift, config: Dict):
        """Execute autonomous portfolio rebalancing action"""
        try:
            logger.info(f"Executing autonomous action for wallet {wallet_address}")
            
            # Log the autonomous decision
            action_log = {
                "action_id": f"auto_{uuid.uuid4().hex[:8]}",
                "wallet_address": wallet_address,
                "action_type": "autonomous_rebalance",
                "drift_analysis": {
                    "total_drift": drift_analysis.total_drift_percent,
                    "token_drifts": drift_analysis.token_drifts,
                    "urgency_level": drift_analysis.urgency_level
                },
                "target_allocation": drift_analysis.suggested_allocation,
                "timestamp": datetime.now(timezone.utc),
                "config_used": {
                    "risk_profile": config["risk_profile"],
                    "drift_threshold": config["drift_threshold_percent"],
                    "auto_execute": config["auto_execute"]
                }
            }
            
            await autonomous_agent_logs.insert_one(action_log)
            
            if config["auto_execute"]:
                # Execute the rebalancing
                await self._execute_rebalancing(wallet_address, drift_analysis, config)
            else:
                # Just log the suggestion
                logger.info(f"Auto-execute disabled for {wallet_address}, logging suggestion only")
            
            # Increment daily trade count
            await self._increment_daily_trades(wallet_address)
            
        except Exception as e:
            logger.error(f"Error executing autonomous action: {str(e)}")
    
    async def _execute_rebalancing(self, wallet_address: str, 
                                  drift_analysis: PortfolioDrift, config: Dict):
        """Execute the actual rebalancing transaction"""
        try:
            logger.info(f"Executing rebalancing for wallet {wallet_address}")
            
            # Get current portfolio state
            portfolio_state = await self._get_portfolio_state(wallet_address)
            if not portfolio_state:
                logger.warning(f"Could not get portfolio state for wallet {wallet_address}, skipping rebalancing")
                return
            
            # Calculate required trades
            trades_needed = self._calculate_trades_needed(
                portfolio_state, drift_analysis.suggested_allocation
            )
            
            if not trades_needed:
                logger.info("No trades needed for rebalancing")
                return
            
            # Estimate gas fees
            estimated_gas = await estimate_gas_fees(trades_needed)
            
            # Execute the transaction
            tx_result = await execute_rebalance_transaction(
                wallet_address=wallet_address,
                trades=trades_needed,
                target_allocation=drift_analysis.suggested_allocation
            )
            
            # Log the execution
            execution_record = {
                "execution_id": f"auto_exec_{uuid.uuid4().hex[:8]}",
                "wallet_address": wallet_address,
                "strategy_id": "autonomous_rebalancing",
                "target_allocation": drift_analysis.suggested_allocation,
                "current_balances": portfolio_state.get("balances", {}),
                "trades_executed": trades_needed,
                "tx_hash": tx_result["tx_hash"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
                "network": "sepolia",
                "execution_type": "autonomous",
                "drift_analysis": {
                    "total_drift": drift_analysis.total_drift_percent,
                    "urgency_level": drift_analysis.urgency_level
                }
            }
            
            await executions.insert_one(execution_record)
            
            logger.info(f"Autonomous rebalancing executed successfully: {tx_result['tx_hash']}")
            
        except Exception as e:
            logger.error(f"Error executing rebalancing: {str(e)}")
    
    def _calculate_trades_needed(self, portfolio_state: Dict, 
                                target_allocation: Dict[str, float]) -> Dict:
        """Calculate trades needed to reach target allocation"""
        try:
            if not portfolio_state or not isinstance(portfolio_state, dict):
                logger.warning("Invalid portfolio state, cannot calculate trades")
                return {}
            
            total_value = portfolio_state.get("total_usd_value", 0)
            current_balances = portfolio_state.get("balances", {})
            prices = portfolio_state.get("prices", {})
            
            if total_value == 0 or not prices:
                logger.warning("Portfolio value is 0 or no prices available, cannot calculate trades")
                return {}
            
            trades_needed = {}
            
            for token, target_pct in target_allocation.items():
                if token not in prices or prices[token] == 0:
                    logger.warning(f"Price not available for {token}, skipping")
                    continue
                    
                target_usd_value = (target_pct / 100) * total_value
                target_token_amount = target_usd_value / prices[token]
                current_amount = current_balances.get(token, 0)
                
                difference = target_token_amount - current_amount
                
                if abs(difference) > 0.001:  # Minimum trade threshold
                    trades_needed[token] = {
                        "current": current_amount,
                        "target": target_token_amount,
                        "difference": difference,
                        "action": "buy" if difference > 0 else "sell"
                    }
            
            return trades_needed
            
        except Exception as e:
            logger.error(f"Error calculating trades needed: {str(e)}")
            return {}
    
    async def _can_trade_today(self, wallet_address: str, config: Dict) -> bool:
        """Check if wallet can trade today (daily limit)"""
        try:
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            last_reset = config.get("last_trade_reset")
            
            # Handle both timezone-aware and naive datetimes
            if last_reset:
                if last_reset.tzinfo is None:
                    # If naive, assume UTC
                    last_reset = last_reset.replace(tzinfo=timezone.utc)
                elif last_reset.tzinfo != timezone.utc:
                    # Convert to UTC if different timezone
                    last_reset = last_reset.astimezone(timezone.utc)
            
            # Reset daily count if it's a new day
            if not last_reset or last_reset < today:
                await wallet_monitoring_configs.update_one(
                    {"wallet_address": wallet_address},
                    {
                        "$set": {
                            "daily_trades_count": 0,
                            "last_trade_reset": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                        }
                    }
                )
                return True
            
            # Check if daily limit reached
            daily_count = config.get("daily_trades_count", 0)
            max_trades = config.get("max_daily_trades", 3)
            
            return daily_count < max_trades
            
        except Exception as e:
            logger.error(f"Error checking daily trade limit: {str(e)}")
            return False
    
    async def _increment_daily_trades(self, wallet_address: str):
        """Increment the daily trade count for a wallet"""
        try:
            await wallet_monitoring_configs.update_one(
                {"wallet_address": wallet_address},
                {"$inc": {"daily_trades_count": 1}}
            )
        except Exception as e:
            logger.error(f"Error incrementing daily trade count: {str(e)}")
    
    async def get_monitoring_status(self) -> Dict:
        """Get current monitoring service status"""
        try:
            # Safe database operations
            try:
                total_wallets = await wallet_monitoring_configs.count_documents({})
            except Exception as e:
                logger.error(f"Error counting total wallets: {str(e)}")
                total_wallets = 0
                
            try:
                active_wallets = await wallet_monitoring_configs.count_documents({"enabled": True})
            except Exception as e:
                logger.error(f"Error counting active wallets: {str(e)}")
                active_wallets = 0
            
            # Get recent autonomous actions
            try:
                recent_actions = await autonomous_agent_logs.find().sort("timestamp", -1).limit(10).to_list(length=10)
            except Exception as e:
                logger.error(f"Error getting recent actions: {str(e)}")
                recent_actions = []
            
            # Get recent executions
            try:
                recent_executions = await executions.find(
                    {"execution_type": "autonomous"}
                ).sort("created_at", -1).limit(10).to_list(length=10)
            except Exception as e:
                logger.error(f"Error getting recent executions: {str(e)}")
                recent_executions = []
            
            # Safe market conditions access
            market_conditions = {}
            try:
                market_conditions = self.market_conditions_cache.get("current", {})
                if not isinstance(market_conditions, dict):
                    market_conditions = {}
            except Exception as e:
                logger.error(f"Error accessing market conditions: {str(e)}")
                market_conditions = {}
            
            return {
                "service_running": self.is_running,
                "total_monitored_wallets": total_wallets,
                "active_monitored_wallets": active_wallets,
                "active_monitoring_tasks": len(self.monitoring_tasks),
                "last_market_check": self.last_market_check.isoformat() if self.last_market_check else None,
                "recent_autonomous_actions": len(recent_actions),
                "recent_autonomous_executions": len(recent_executions),
                "market_conditions": market_conditions
            }
            
        except Exception as e:
            logger.error(f"Error getting monitoring status: {str(e)}")
            # Return a default status instead of error object
            return {
                "service_running": False,
                "total_monitored_wallets": 0,
                "active_monitored_wallets": 0,
                "active_monitoring_tasks": 0,
                "last_market_check": None,
                "recent_autonomous_actions": 0,
                "recent_autonomous_executions": 0,
                "market_conditions": {}
            }

# Global instance
autonomous_agent_service = AutonomousAgentService()
