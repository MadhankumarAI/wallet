#!/usr/bin/env python3
"""
Test script to debug wallet monitoring database operations
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.db.mongo import wallet_monitoring_configs, setup_database
from app.services.autonomous_agent import autonomous_agent_service, MonitoringConfig
from datetime import datetime, timezone

async def test_wallet_monitoring():
    """Test wallet monitoring operations"""
    print("🔧 Setting up database...")
    await setup_database()
    
    print("\n📊 Current database state:")
    total_configs = await wallet_monitoring_configs.count_documents({})
    enabled_configs = await wallet_monitoring_configs.count_documents({"enabled": True})
    print(f"Total configs: {total_configs}")
    print(f"Enabled configs: {enabled_configs}")
    
    # List all configs
    all_configs = await wallet_monitoring_configs.find({}).to_list(length=None)
    print(f"\n📋 All configs in database:")
    for config in all_configs:
        print(f"  - {config['wallet_address']}: enabled={config.get('enabled', False)}")
    
    print("\n🚀 Testing wallet addition...")
    
    # Test wallet address
    test_wallet = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    
    # Create monitoring config
    config = MonitoringConfig(
        wallet_address=test_wallet,
        enabled=True,
        check_interval_minutes=15,
        drift_threshold_percent=5.0,
        max_daily_trades=3,
        risk_profile="balanced",
        auto_execute=False,
        slippage_tolerance=1.0,
        min_portfolio_value_usd=100.0
    )
    
    print(f"Adding wallet {test_wallet} to monitoring...")
    
    try:
        await autonomous_agent_service.add_wallet_to_monitoring(config)
        print("✅ Wallet added successfully!")
    except Exception as e:
        print(f"❌ Error adding wallet: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n📊 Database state after addition:")
    total_configs_after = await wallet_monitoring_configs.count_documents({})
    enabled_configs_after = await wallet_monitoring_configs.count_documents({"enabled": True})
    print(f"Total configs: {total_configs_after}")
    print(f"Enabled configs: {enabled_configs_after}")
    
    # List all configs again
    all_configs_after = await wallet_monitoring_configs.find({}).to_list(length=None)
    print(f"\n📋 All configs in database after addition:")
    for config in all_configs_after:
        print(f"  - {config['wallet_address']}: enabled={config.get('enabled', False)}")
    
    # Test the specific wallet query
    print(f"\n🔍 Testing specific wallet query for {test_wallet}:")
    specific_config = await wallet_monitoring_configs.find_one({"wallet_address": test_wallet})
    if specific_config:
        print(f"✅ Found config: {specific_config}")
    else:
        print(f"❌ No config found for {test_wallet}")
    
    # Test the enabled wallets query
    print(f"\n🔍 Testing enabled wallets query:")
    enabled_wallets = await wallet_monitoring_configs.find({"enabled": True}).to_list(length=None)
    print(f"Enabled wallets count: {len(enabled_wallets)}")
    for wallet in enabled_wallets:
        print(f"  - {wallet['wallet_address']}")
    
    # Test service status
    print(f"\n📊 Testing service status:")
    try:
        status = await autonomous_agent_service.get_monitoring_status()
        print(f"Service status: {status}")
    except Exception as e:
        print(f"❌ Error getting service status: {str(e)}")

if __name__ == "__main__":
    print("🧪 Starting wallet monitoring test...")
    asyncio.run(test_wallet_monitoring())
    print("\n✅ Test completed!")
