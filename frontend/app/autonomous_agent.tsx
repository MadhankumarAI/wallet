import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  Dimensions,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { API_URL } from '../Api.jsx';
import PortfolioDriftChart from '../components/PortfolioDriftChart';

const { width, height } = Dimensions.get('window');

interface MonitoringConfig {
  wallet_address: string;
  enabled: boolean;
  check_interval_minutes: number;
  drift_threshold_percent: number;
  max_daily_trades: number;
  risk_profile: string;
  auto_execute: boolean;
  slippage_tolerance: number;
  min_portfolio_value_usd: number;
  created_at: string;
  last_check?: string;
  daily_trades_count: number;
  last_trade_reset: string;
}

interface ServiceStatus {
  service_running: boolean;
  total_monitored_wallets: number;
  active_monitored_wallets: number;
  active_monitoring_tasks: number;
  last_market_check?: string;
  recent_autonomous_actions: number;
  recent_autonomous_executions: number;
  market_conditions: any;
}

interface AutonomousAction {
  action_id: string;
  wallet_address: string;
  action_type: string;
  drift_analysis: any;
  target_allocation: any;
  timestamp: string;
  config_used: any;
}

export default function AutonomousAgentScreen() {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null);
  const [monitoredWallets, setMonitoredWallets] = useState<MonitoringConfig[]>([]);
  const [recentActions, setRecentActions] = useState<AutonomousAction[]>([]);
  const [isMonitoringEnabled, setIsMonitoringEnabled] = useState(false);
  const [portfolioData, setPortfolioData] = useState({
    currentAllocation: { ETH: 65, USDC: 20, LINK: 15 },
    targetAllocation: { ETH: 60, USDC: 25, LINK: 15 },
    driftHistory: [
      { timestamp: '2025-01-24T10:00:00Z', drift: 2.5 },
      { timestamp: '2025-01-24T11:00:00Z', drift: 4.2 },
      { timestamp: '2025-01-24T12:00:00Z', drift: 6.8 },
      { timestamp: '2025-01-24T13:00:00Z', drift: 5.1 },
      { timestamp: '2025-01-24T14:00:00Z', drift: 7.3 },
    ]
  });

  useEffect(() => {
    // Entrance animations
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        tension: 50,
        friction: 8,
        useNativeDriver: true,
      }),
    ]).start();

    // Continuous pulse animation for status indicator
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();

    loadData();
  }, []);

  // Debug logging for state changes
  useEffect(() => {
    console.log('👀 [DEBUG] monitoredWallets state changed:', monitoredWallets);
    console.log('👀 [DEBUG] Number of monitored wallets:', monitoredWallets.length);
  }, [monitoredWallets]);

  useEffect(() => {
    console.log('👀 [DEBUG] serviceStatus state changed:', serviceStatus);
  }, [serviceStatus]);

  const loadData = async () => {
    try {
      console.log('🔄 [DEBUG] loadData() called - starting to fetch data...');
      setIsLoading(true);
      
      // Load service status
      console.log('📊 [DEBUG] Fetching service status...');
      const statusResponse = await fetch(`${API_URL}/autonomous/status/public`);
      console.log('📊 [DEBUG] Status response status:', statusResponse.status);
      if (statusResponse.ok) {
        const status = await statusResponse.json();
        console.log('📊 [DEBUG] Status data received:', status);
        setServiceStatus(status);
        setIsMonitoringEnabled(status.service_running);
        console.log('📊 [DEBUG] Service status state updated');
      } else {
        console.error('❌ [DEBUG] Status response failed:', statusResponse.status);
      }

      // Load monitored wallets
      console.log('👛 [DEBUG] Fetching monitored wallets...');
      const walletsResponse = await fetch(`${API_URL}/autonomous/monitor/wallets/public`);
      console.log('👛 [DEBUG] Wallets response status:', walletsResponse.status);
      if (walletsResponse.ok) {
        const wallets = await walletsResponse.json();
        console.log('👛 [DEBUG] Wallets data received:', wallets);
        console.log('👛 [DEBUG] Number of wallets:', wallets.length);
        setMonitoredWallets(wallets);
        console.log('👛 [DEBUG] Monitored wallets state updated');
      } else {
        console.error('❌ [DEBUG] Wallets response failed:', walletsResponse.status);
      }

      // Load recent actions
      console.log('📝 [DEBUG] Fetching recent actions...');
      const actionsResponse = await fetch(`${API_URL}/autonomous/actions`);
      console.log('📝 [DEBUG] Actions response status:', actionsResponse.status);
      if (actionsResponse.ok) {
        const actions = await actionsResponse.json();
        console.log('📝 [DEBUG] Actions data received:', actions);
        console.log('📝 [DEBUG] Number of actions:', actions.length);
        setRecentActions(actions.slice(0, 10)); // Show last 10 actions
        console.log('📝 [DEBUG] Recent actions state updated');
      } else {
        console.error('❌ [DEBUG] Actions response failed:', actionsResponse.status);
      }
      
      console.log('✅ [DEBUG] loadData() completed successfully');
    } catch (error) {
      console.error('❌ [DEBUG] Error in loadData:', error);
      Alert.alert('Error', 'Failed to load autonomous agent data');
    } finally {
      setIsLoading(false);
      console.log('🏁 [DEBUG] Loading state set to false');
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const toggleMonitoring = async () => {
    try {
      const endpoint = isMonitoringEnabled ? '/autonomous/service/stop/public' : '/autonomous/service/start/public';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
      });

      if (response.ok) {
        setIsMonitoringEnabled(!isMonitoringEnabled);
        await loadData(); // Refresh data
        Alert.alert(
          'Success',
          `Autonomous monitoring ${isMonitoringEnabled ? 'stopped' : 'started'} successfully`
        );
      } else {
        Alert.alert('Error', 'Failed to toggle monitoring service');
      }
    } catch (error) {
      console.error('Error toggling monitoring:', error);
      Alert.alert('Error', 'Failed to toggle monitoring service');
    }
  };

  const [showWalletInput, setShowWalletInput] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [showStrategySelection, setShowStrategySelection] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('balanced');

  const addWalletToMonitoring = () => {
    setShowWalletInput(true);
  };

  const handleWalletSubmit = () => {
    if (walletAddress.trim()) {
      setShowWalletInput(false);
      setShowStrategySelection(true);
    }
  };

  const handleStrategySubmit = () => {
    if (selectedStrategy) {
      addWalletToMonitoringInternal(walletAddress.trim(), selectedStrategy);
      setShowStrategySelection(false);
      setWalletAddress('');
      setSelectedStrategy('balanced');
    }
  };

  const removeWalletFromMonitoring = async (walletAddress: string) => {
    // Simple confirmation alert
    Alert.alert(
      'Confirm Deletion',
      `Are you sure you want to remove wallet ${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)} from monitoring?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => executeWalletDeletion(walletAddress)
        }
      ]
    );
  };

  const executeWalletDeletion = async (walletAddress: string) => {
    try {
      console.log('🗑️ [DEBUG] Executing wallet deletion:', walletAddress);
      
      const response = await fetch(`${API_URL}/autonomous/monitor/wallet/public`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ wallet_address: walletAddress }),
      });

      if (response.ok) {
        console.log('✅ [DEBUG] Wallet removed successfully');
        
        // Remove from local state immediately
        setMonitoredWallets(prev => prev.filter(w => w.wallet_address !== walletAddress));
        
        Alert.alert('Success', 'Wallet removed from monitoring');
        
        // Refresh data from server
        await loadData();
      } else {
        const errorText = await response.text();
        console.error('❌ [DEBUG] Error removing wallet:', errorText);
        Alert.alert('Error', `Failed to remove wallet: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      console.error('❌ [DEBUG] Error removing wallet:', error);
      Alert.alert('Error', `Failed to remove wallet: ${error}`);
    }
  };

  const addWalletToMonitoringInternal = async (walletAddress: string, strategy: string = 'balanced') => {
    if (walletAddress && walletAddress.trim()) {
      try {
        console.log('🚀 [DEBUG] ===== WALLET ADDITION STARTED =====');
        console.log('🚀 [DEBUG] Adding wallet to monitoring:', walletAddress);
        console.log('🚀 [DEBUG] Strategy selected:', strategy);
        console.log('🚀 [DEBUG] API URL:', `${API_URL}/autonomous/monitor/wallet/public`);
        
        // Configure strategy-based parameters
        let driftThreshold = 5.0;
        let maxDailyTrades = 3;
        let riskProfile = 'balanced';
        
        switch (strategy) {
          case 'conservative':
            driftThreshold = 3.0;
            maxDailyTrades = 5;
            riskProfile = 'conservative';
            break;
          case 'aggressive':
            driftThreshold = 8.0;
            maxDailyTrades = 2;
            riskProfile = 'aggressive';
            break;
          case 'balanced':
          default:
            driftThreshold = 5.0;
            maxDailyTrades = 3;
            riskProfile = 'balanced';
            break;
        }
        
        const requestBody = {
          wallet_address: walletAddress.trim(),
          enabled: true,
          check_interval_minutes: 15,
          drift_threshold_percent: driftThreshold,
          max_daily_trades: maxDailyTrades,
          risk_profile: riskProfile,
          auto_execute: false,
          slippage_tolerance: 1.0,
          min_portfolio_value_usd: 100.0,
        };
        
        console.log('🚀 [DEBUG] Request body:', requestBody);
        console.log('🚀 [DEBUG] Current monitored wallets count BEFORE:', monitoredWallets.length);
        
        const response = await fetch(`${API_URL}/autonomous/monitor/wallet/public`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        console.log('🚀 [DEBUG] Response status:', response.status);
        console.log('🚀 [DEBUG] Response ok:', response.ok);
        
        if (response.ok) {
          const responseData = await response.json();
          console.log('🚀 [DEBUG] Response data:', responseData);
          console.log('🚀 [DEBUG] Wallet added successfully!');
          
          // Immediately add the new wallet to local state for instant UI update
          const newWallet: MonitoringConfig = {
            wallet_address: walletAddress.trim(),
            enabled: true,
            check_interval_minutes: 15,
            drift_threshold_percent: 5.0,
            max_daily_trades: 3,
            risk_profile: 'balanced',
            auto_execute: false,
            slippage_tolerance: 1.0,
            min_portfolio_value_usd: 100.0,
            created_at: new Date().toISOString(),
            last_check: undefined,
            daily_trades_count: 0,
            last_trade_reset: new Date().toISOString(),
          };
          
          console.log('🔄 [DEBUG] Updating local state immediately...');
          setMonitoredWallets(prev => {
            const updated = [...prev, newWallet];
            console.log('🔄 [DEBUG] Updated monitored wallets:', updated);
            return updated;
          });
          
          Alert.alert('Success', 'Wallet added to monitoring');
          
          // Force immediate re-render and then refresh from server
          console.log('🔄 [DEBUG] Forcing immediate re-render...');
          setMonitoredWallets(prev => [...prev]); // Force re-render
          
          // Refresh data from server to ensure consistency
          console.log('🔄 [DEBUG] Refreshing data from server...');
          await loadData();
          
        } else {
          const errorText = await response.text();
          console.error('❌ [DEBUG] Error response:', errorText);
          Alert.alert('Error', `Failed to add wallet to monitoring: ${response.status} - ${errorText}`);
        }
      } catch (error) {
        console.error('❌ [DEBUG] Error adding wallet:', error);
        Alert.alert('Error', `Failed to add wallet to monitoring: ${error}`);
      } finally {
        console.log('🚀 [DEBUG] ===== WALLET ADDITION COMPLETED =====');
      }
    } else {
      console.log('❌ [DEBUG] Invalid wallet address provided');
    }
  };

  const getRiskProfileColor = (profile: string) => {
    switch (profile) {
      case 'conservative': return '#4CAF50';
      case 'balanced': return '#FF9800';
      case 'aggressive': return '#F44336';
      default: return '#888';
    }
  };

  const getStatusColor = (enabled: boolean) => {
    return enabled ? '#4CAF50' : '#F44336';
  };

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getDriftLevel = (drift: number) => {
    if (drift > 20) return { level: 'Critical', color: '#F44336' };
    if (drift > 15) return { level: 'High', color: '#FF9800' };
    if (drift > 10) return { level: 'Medium', color: '#FFC107' };
    return { level: 'Low', color: '#4CAF50' };
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <BlurView intensity={40} style={styles.loadingBlur}>
          <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
            <Ionicons name="sync" size={40} color="#bb86fc" />
          </Animated.View>
          <Text style={styles.loadingText}>Loading Autonomous Agent...</Text>
        </BlurView>
      </View>
    );
  }

  // Debug logging for render
  console.log('🎨 [DEBUG] RENDERING with state:', {
    monitoredWalletsCount: monitoredWallets.length,
    monitoredWallets: monitoredWallets,
    serviceStatus: serviceStatus,
    isMonitoringEnabled: isMonitoringEnabled
  });

  return (
    <View style={styles.container}>
      {/* Background */}
      <LinearGradient
        colors={['rgba(0,0,0,0.9)', 'rgba(187,134,252,0.2)', 'rgba(0,0,0,0.9)']}
        style={styles.gradientOverlay}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
      />

      {/* Header */}
      <View style={styles.header}>
        <BlurView intensity={30} style={styles.headerBlur}>
          <View style={styles.headerContent}>
            <Pressable onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="#bb86fc" />
            </Pressable>
            <Text style={styles.headerTitle}>🤖 Autonomous Agent</Text>
            <View style={styles.headerSpacer} />
          </View>
        </BlurView>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <Animated.View
          style={[
            styles.content,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          {/* Service Status Card */}
          <View style={styles.statusCard}>
            <BlurView intensity={25} style={styles.cardBlur}>
              <View style={styles.statusHeader}>
                <View style={styles.statusIconContainer}>
                  <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
                    <Ionicons 
                      name={isMonitoringEnabled ? "checkmark-circle" : "close-circle"} 
                      size={32} 
                      color={getStatusColor(isMonitoringEnabled)} 
                    />
                  </Animated.View>
                </View>
                <View style={styles.statusInfo}>
                  <Text style={styles.statusTitle}>
                    {isMonitoringEnabled ? 'Monitoring Active' : 'Monitoring Inactive'}
                  </Text>
                  <Text style={styles.statusSubtitle}>
                    {isMonitoringEnabled ? '24/7 portfolio surveillance' : 'Service stopped'}
                  </Text>
                </View>
                <Pressable onPress={toggleMonitoring} style={styles.toggleButton}>
                  <Text style={styles.toggleButtonText}>
                    {isMonitoringEnabled ? 'Stop' : 'Start'}
                  </Text>
                </Pressable>
              </View>
              
              {serviceStatus && (
                <View style={styles.statusGrid}>
                  <StatusItem 
                    label="Monitored Wallets" 
                    value={serviceStatus.total_monitored_wallets.toString()} 
                    icon="wallet" 
                  />
                  <StatusItem 
                    label="Active Tasks" 
                    value={serviceStatus.active_monitoring_tasks.toString()} 
                    icon="layers" 
                  />
                  <StatusItem 
                    label="Recent Actions" 
                    value={serviceStatus.recent_autonomous_actions.toString()} 
                    icon="analytics" 
                  />
                  <StatusItem 
                    label="Executions" 
                    value={serviceStatus.recent_autonomous_executions.toString()} 
                    icon="rocket" 
                  />
                </View>
              )}
            </BlurView>
          </View>

          {/* Portfolio Drift Chart */}
          <PortfolioDriftChart
            currentAllocation={portfolioData.currentAllocation}
            targetAllocation={portfolioData.targetAllocation}
            driftHistory={portfolioData.driftHistory}
          />

          {/* Market Conditions Card */}
          {serviceStatus?.market_conditions && (
            <View style={styles.marketCard}>
              <BlurView intensity={25} style={styles.cardBlur}>
                <View style={styles.cardHeader}>
                  <Ionicons name="trending-up" size={24} color="#bb86fc" />
                  <Text style={styles.cardTitle}>Market Conditions</Text>
                </View>
                <View style={styles.marketGrid}>
                  <MarketConditionItem 
                    label="Risk Score" 
                    value={`${serviceStatus.market_conditions.risk_score || 0}/100`}
                    color={serviceStatus.market_conditions.risk_score > 70 ? '#F44336' : '#4CAF50'}
                  />
                  <MarketConditionItem 
                    label="Volatility" 
                    value={serviceStatus.market_conditions.volatility_high ? 'High' : 'Low'}
                    color={serviceStatus.market_conditions.volatility_high ? '#FF9800' : '#4CAF50'}
                  />
                  <MarketConditionItem 
                    label="Trend" 
                    value={serviceStatus.market_conditions.trend_direction || 'Sideways'}
                    color="#bb86fc"
                  />
                </View>
              </BlurView>
            </View>
          )}

          {/* Monitored Wallets */}
          <View style={styles.walletsCard}>
            <BlurView intensity={25} style={styles.cardBlur}>
              <View style={styles.cardHeader}>
                <Ionicons name="wallet" size={24} color="#bb86fc" />
                <Text style={styles.cardTitle}>Monitored Wallets</Text>
                <Pressable onPress={addWalletToMonitoring} style={styles.addButton}>
                  <Ionicons name="add" size={24} color="#bb86fc" />
                </Pressable>
              </View>
              
              {monitoredWallets.length === 0 ? (
                <View style={styles.emptyState}>
                  <Ionicons name="wallet-outline" size={48} color="#666" />
                  <Text style={styles.emptyStateText}>No wallets being monitored</Text>
                  <Text style={styles.emptyStateSubtext}>Add a wallet to start autonomous monitoring</Text>
                </View>
                             ) : (
                 monitoredWallets.map((wallet, index) => (
                   <WalletMonitoringCard 
                     key={index} 
                     wallet={wallet} 
                     onDelete={removeWalletFromMonitoring}
                   />
                 ))
               )}
            </BlurView>
          </View>

          {/* Recent Actions */}
          <View style={styles.actionsCard}>
            <BlurView intensity={25} style={styles.cardBlur}>
              <View style={styles.cardHeader}>
                <Ionicons name="analytics" size={24} color="#bb86fc" />
                <Text style={styles.cardTitle}>Recent Actions</Text>
              </View>
              
              {recentActions.length === 0 ? (
                <View style={styles.emptyState}>
                  <Ionicons name="analytics-outline" size={48} color="#666" />
                  <Text style={styles.emptyStateText}>No actions yet</Text>
                  <Text style={styles.emptyStateSubtext}>Actions will appear here as the agent monitors portfolios</Text>
                </View>
              ) : (
                recentActions.map((action, index) => (
                  <ActionCard key={index} action={action} />
                ))
              )}
            </BlurView>
          </View>

          {/* Quick Actions */}
          <View style={styles.quickActionsCard}>
            <BlurView intensity={25} style={styles.cardBlur}>
              <Text style={styles.cardTitle}>Quick Actions</Text>
              <View style={styles.quickActionsGrid}>
                <QuickActionButton
                  icon="refresh"
                  title="Force Check"
                  onPress={() => {
                    Alert.alert('Force Check', 'This will trigger an immediate portfolio check for all monitored wallets');
                  }}
                />
                <QuickActionButton
                  icon="settings"
                  title="Configure"
                  onPress={() => {
                    Alert.alert('Configure', 'Advanced configuration options coming soon');
                  }}
                />
                <QuickActionButton
                  icon="document-text"
                  title="Analytics"
                  onPress={() => {
                    Alert.alert('Analytics', 'Detailed analytics dashboard coming soon');
                  }}
                />
                <QuickActionButton
                  icon="help-circle"
                  title="Help"
                  onPress={() => {
                    Alert.alert('Help', 'Autonomous agent help and documentation coming soon');
                  }}
                />
              </View>
            </BlurView>
          </View>
        </Animated.View>
      </ScrollView>

      {/* Wallet Input Modal */}
      {showWalletInput && (
        <View style={styles.modalOverlay}>
          <BlurView intensity={40} style={styles.modalContent}>
            <Text style={styles.modalTitle}>Add Wallet to Monitoring</Text>
            <Text style={styles.modalSubtitle}>Enter the wallet address you want to monitor</Text>
            
            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Wallet Address:</Text>
              <TextInput
                style={styles.textInput}
                value={walletAddress}
                onChangeText={setWalletAddress}
                placeholder="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
                placeholderTextColor="#666"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>
            
            <View style={styles.modalButtons}>
              <Pressable 
                style={[styles.modalButton, styles.cancelButton]} 
                onPress={() => setShowWalletInput(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </Pressable>
              <Pressable 
                style={[styles.modalButton, styles.confirmButton]} 
                onPress={handleWalletSubmit}
              >
                <Text style={styles.confirmButtonText}>Next</Text>
              </Pressable>
            </View>
          </BlurView>
        </View>
      )}

      {/* Strategy Selection Modal */}
      {showStrategySelection && (
        <View style={styles.modalOverlay}>
          <BlurView intensity={40} style={styles.modalContent}>
            <Text style={styles.modalTitle}>Select Monitoring Strategy</Text>
            <Text style={styles.modalSubtitle}>Choose how aggressively to monitor this wallet</Text>
            
            <View style={styles.strategyContainer}>
              <Pressable 
                style={[
                  styles.strategyOption, 
                  selectedStrategy === 'conservative' && styles.strategyOptionSelected
                ]}
                onPress={() => setSelectedStrategy('conservative')}
              >
                <Ionicons name="shield-checkmark" size={24} color="#4CAF50" />
                <View style={styles.strategyInfo}>
                  <Text style={styles.strategyName}>Conservative</Text>
                  <Text style={styles.strategyDescription}>
                    Lower risk, lower drift threshold (3%), max 5 trades/day
                  </Text>
                </View>
                {selectedStrategy === 'conservative' && (
                  <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
                )}
              </Pressable>
              
              <Pressable 
                style={[
                  styles.strategyOption, 
                  selectedStrategy === 'balanced' && styles.strategyOptionSelected
                ]}
                onPress={() => setSelectedStrategy('balanced')}
              >
                <Ionicons name="analytics" size={24} color="#FF9800" />
                <View style={styles.strategyInfo}>
                  <Text style={styles.strategyName}>Balanced</Text>
                  <Text style={styles.strategyDescription}>
                    Medium risk, 5% drift threshold, max 3 trades/day
                  </Text>
                </View>
                {selectedStrategy === 'balanced' && (
                  <Ionicons name="checkmark-circle" size={24} color="#FF9800" />
                )}
              </Pressable>
              
              <Pressable 
                style={[
                  styles.strategyOption, 
                  selectedStrategy === 'aggressive' && styles.strategyOptionSelected
                ]}
                onPress={() => setSelectedStrategy('aggressive')}
              >
                <Ionicons name="rocket" size={24} color="#F44336" />
                <View style={styles.strategyInfo}>
                  <Text style={styles.strategyName}>Aggressive</Text>
                  <Text style={styles.strategyDescription}>
                    Higher risk, 8% drift threshold, max 2 trades/day
                  </Text>
                </View>
                {selectedStrategy === 'aggressive' && (
                  <Ionicons name="checkmark-circle" size={24} color="#F44336" />
                )}
              </Pressable>
            </View>
            
            <View style={styles.modalButtons}>
              <Pressable 
                style={[styles.modalButton, styles.cancelButton]} 
                onPress={() => setShowStrategySelection(false)}
              >
                <Text style={styles.cancelButtonText}>Back</Text>
              </Pressable>
              <Pressable 
                style={[styles.modalButton, styles.confirmButton]} 
                onPress={handleStrategySubmit}
              >
                <Text style={styles.confirmButtonText}>Add Wallet</Text>
              </Pressable>
            </View>
          </BlurView>
        </View>
      )}
    </View>
  );
}

// Status Item Component
const StatusItem = ({ label, value, icon }: { label: string; value: string; icon: string }) => (
  <View style={styles.statusItem}>
    <Ionicons name={icon as any} size={20} color="#bb86fc" />
    <Text style={styles.statusItemValue}>{value}</Text>
    <Text style={styles.statusItemLabel}>{label}</Text>
  </View>
);

// Market Condition Item Component
const MarketConditionItem = ({ label, value, color }: { label: string; value: string; color: string }) => (
  <View style={styles.marketConditionItem}>
    <Text style={styles.marketConditionLabel}>{label}</Text>
    <Text style={[styles.marketConditionValue, { color }]}>{value}</Text>
  </View>
);

// Wallet Monitoring Card Component
const WalletMonitoringCard = ({ wallet, onDelete }: { wallet: MonitoringConfig; onDelete: (walletAddress: string) => void }) => (
  <View style={styles.walletCard}>
    <View style={styles.walletHeader}>
      <View style={styles.walletAddressContainer}>
        <Ionicons name="wallet" size={16} color="#bb86fc" />
        <Text style={styles.walletAddress}>
          {wallet.wallet_address.slice(0, 6)}...{wallet.wallet_address.slice(-4)}
        </Text>
      </View>
      <View style={styles.walletHeaderRight}>
        <View style={[styles.statusIndicator, { backgroundColor: getStatusColor(wallet.enabled) }]} />
        <Pressable 
          style={styles.deleteButton}
          onPress={() => onDelete(wallet.wallet_address)}
        >
          <Ionicons name="trash-outline" size={16} color="#F44336" />
        </Pressable>
      </View>
    </View>
    
    <View style={styles.walletDetails}>
      <View style={styles.walletDetailRow}>
        <Text style={styles.detailLabel}>Risk Profile:</Text>
        <Text style={[styles.detailValue, { color: getRiskProfileColor(wallet.risk_profile) }]}>
          {wallet.risk_profile.charAt(0).toUpperCase() + wallet.risk_profile.slice(1)}
        </Text>
      </View>
      <View style={styles.walletDetailRow}>
        <Text style={styles.detailLabel}>Drift Threshold:</Text>
        <Text style={styles.detailValue}>{wallet.drift_threshold_percent}%</Text>
      </View>
      <View style={styles.walletDetailRow}>
        <Text style={styles.detailLabel}>Check Interval:</Text>
        <Text style={styles.detailValue}>{wallet.check_interval_minutes} min</Text>
      </View>
      <View style={styles.walletDetailRow}>
        <Text style={styles.detailLabel}>Daily Trades:</Text>
        <Text style={styles.detailValue}>{wallet.daily_trades_count}/{wallet.max_daily_trades}</Text>
      </View>
      <View style={styles.walletDetailRow}>
        <Text style={styles.detailLabel}>Last Check:</Text>
        <Text style={styles.detailValue}>{formatTimestamp(wallet.last_check)}</Text>
      </View>
    </View>
  </View>
);

// Action Card Component
const ActionCard = ({ action }: { action: AutonomousAction }) => {
  const driftLevel = getDriftLevel(action.drift_analysis?.total_drift || 0);
  
  return (
    <View style={styles.actionCard}>
      <View style={styles.actionHeader}>
        <View style={styles.actionTypeContainer}>
          <Ionicons 
            name={action.action_type === 'autonomous_rebalance' ? 'refresh' : 'analytics'} 
            size={16} 
            color="#bb86fc" 
          />
          <Text style={styles.actionType}>
            {action.action_type === 'autonomous_rebalance' ? 'Rebalance' : 'Analysis'}
          </Text>
        </View>
        <Text style={[styles.driftLevel, { color: driftLevel.color }]}>
          {driftLevel.level}
        </Text>
      </View>
      
      <Text style={styles.actionWallet}>
        {action.wallet_address.slice(0, 6)}...{action.wallet_address.slice(-4)}
      </Text>
      
      <Text style={styles.actionTimestamp}>
        {formatTimestamp(action.timestamp)}
      </Text>
    </View>
  );
};

// Quick Action Button Component
const QuickActionButton = ({ icon, title, onPress }: { icon: string; title: string; onPress: () => void }) => (
  <Pressable onPress={onPress} style={styles.quickActionButton}>
    <Ionicons name={icon as any} size={24} color="#bb86fc" />
    <Text style={styles.quickActionTitle}>{title}</Text>
  </Pressable>
);

// Helper functions
const getStatusColor = (enabled: boolean) => enabled ? '#4CAF50' : '#F44336';

const getRiskProfileColor = (profile: string) => {
  switch (profile) {
    case 'conservative': return '#4CAF50';
    case 'balanced': return '#FF9800';
    case 'aggressive': return '#F44336';
    default: return '#888';
  }
};

const formatTimestamp = (timestamp: string | undefined) => {
  if (!timestamp) return 'Never';
  const date = new Date(timestamp);
  return date.toLocaleString();
};

const getDriftLevel = (drift: number) => {
  if (drift > 20) return { level: 'Critical', color: '#F44336' };
  if (drift > 15) return { level: 'High', color: '#FF9800' };
  if (drift > 10) return { level: 'Medium', color: '#FFC107' };
  return { level: 'Low', color: '#4CAF50' };
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  gradientOverlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 0,
  },
  header: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 60 : 40,
    left: 20,
    right: 20,
    zIndex: 3,
  },
  headerBlur: {
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(187, 134, 252, 0.3)',
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  backButton: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(187, 134, 252, 0.2)',
  },
  headerTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: 'bold',
    color: '#bb86fc',
    textAlign: 'center',
    marginLeft: 16,
  },
  headerSpacer: {
    width: 40,
  },
  scrollView: {
    flex: 1,
    zIndex: 1,
  },
  scrollContent: {
    paddingTop: Platform.OS === 'ios' ? 140 : 120,
    paddingBottom: 40,
  },
  content: {
    paddingHorizontal: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000',
  },
  loadingBlur: {
    borderRadius: 20,
    padding: 40,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(187, 134, 252, 0.3)',
  },
  loadingText: {
    color: '#bb86fc',
    fontSize: 18,
    marginTop: 16,
    textAlign: 'center',
  },
  statusCard: {
    marginBottom: 20,
    borderRadius: 20,
    overflow: 'hidden',
  },
  cardBlur: {
    borderRadius: 20,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(187, 134, 252, 0.3)',
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
  },
  statusIconContainer: {
    marginRight: 16,
  },
  statusInfo: {
    flex: 1,
  },
  statusTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  statusSubtitle: {
    fontSize: 14,
    color: '#888',
  },
  toggleButton: {
    backgroundColor: '#bb86fc',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 12,
  },
  toggleButtonText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 14,
  },
  statusGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  statusItem: {
    width: '50%',
    alignItems: 'center',
    marginBottom: 16,
  },
  statusItemValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#bb86fc',
    marginTop: 8,
  },
  statusItemLabel: {
    fontSize: 12,
    color: '#888',
    textAlign: 'center',
    marginTop: 4,
  },
  marketCard: {
    marginBottom: 20,
    borderRadius: 20,
    overflow: 'hidden',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginLeft: 12,
    flex: 1,
  },
  addButton: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(187, 134, 252, 0.2)',
  },
  marketGrid: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  marketConditionItem: {
    flex: 1,
    alignItems: 'center',
  },
  marketConditionLabel: {
    fontSize: 12,
    color: '#888',
    marginBottom: 4,
    textAlign: 'center',
  },
  marketConditionValue: {
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  walletsCard: {
    marginBottom: 20,
    borderRadius: 20,
    overflow: 'hidden',
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
  },
  emptyStateText: {
    fontSize: 16,
    color: '#666',
    marginTop: 16,
    textAlign: 'center',
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#444',
    marginTop: 8,
    textAlign: 'center',
  },
  walletCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  walletHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  walletHeaderRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  walletAddressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  walletAddress: {
    fontSize: 14,
    color: '#fff',
    marginLeft: 8,
    fontFamily: 'monospace',
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  deleteButton: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(244, 67, 54, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(244, 67, 54, 0.3)',
  },
  walletDetails: {
    gap: 8,
  },
  walletDetailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  detailLabel: {
    fontSize: 12,
    color: '#888',
  },
  detailValue: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '500',
  },
  actionsCard: {
    marginBottom: 20,
    borderRadius: 20,
    overflow: 'hidden',
  },
  actionCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  actionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  actionTypeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionType: {
    fontSize: 14,
    color: '#bb86fc',
    marginLeft: 8,
    fontWeight: '500',
  },
  driftLevel: {
    fontSize: 12,
    fontWeight: 'bold',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  actionWallet: {
    fontSize: 12,
    color: '#888',
    fontFamily: 'monospace',
    marginBottom: 4,
  },
  actionTimestamp: {
    fontSize: 10,
    color: '#666',
  },
  quickActionsCard: {
    marginBottom: 20,
    borderRadius: 20,
    overflow: 'hidden',
  },
  quickActionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  quickActionButton: {
    width: '50%',
    alignItems: 'center',
    paddingVertical: 16,
  },
  quickActionTitle: {
    fontSize: 12,
    color: '#bb86fc',
    marginTop: 8,
    textAlign: 'center',
  },
  
  // Modal Styles
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modalContent: {
    width: '90%',
    maxWidth: 400,
    backgroundColor: 'rgba(30, 30, 30, 0.95)',
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: 'rgba(187, 134, 252, 0.3)',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
  },
  modalSubtitle: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    marginBottom: 24,
  },
  inputContainer: {
    marginBottom: 24,
  },
  inputLabel: {
    fontSize: 14,
    color: '#bb86fc',
    marginBottom: 8,
  },
  textInput: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: '#fff',
    borderWidth: 1,
    borderColor: 'rgba(187, 134, 252, 0.3)',
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 16,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  confirmButton: {
    backgroundColor: '#bb86fc',
  },
  cancelButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  confirmButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: '600',
  },
  
  // Strategy Selection Styles
  strategyContainer: {
    marginBottom: 24,
    gap: 12,
  },
  strategyOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  strategyOptionSelected: {
    borderColor: '#bb86fc',
    backgroundColor: 'rgba(187, 134, 252, 0.1)',
  },
  strategyInfo: {
    flex: 1,
    marginLeft: 16,
  },
  strategyName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  strategyDescription: {
    fontSize: 12,
    color: '#888',
    lineHeight: 16,
  },
});
