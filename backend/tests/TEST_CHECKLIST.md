# File: backend/tests/TEST_CHECKLIST.md

# Seamount Integration Test Checklist

## Component A: On-Ramp Aggregator
- [ ] Initialize on-ramp for NGN
- [ ] Initialize on-ramp for KES
- [ ] Get supported providers
- [ ] Verify fee calculation (2.5%)
- [ ] Test provider selection logic
- [ ] Test webhook handling (mock)

## Component B: Off-Ramp Service
- [ ] Initialize bank withdrawal (NGN)
- [ ] Initialize mobile money (KES M-Pesa)
- [ ] Get withdrawal limits
- [ ] Verify fee calculation (2.8%)
- [ ] Test balance validation
- [ ] Test refund on failure

## Component C: Wallet Connect
- [ ] Generate deposit address
- [ ] Validate withdrawal address
- [ ] Get supported exchanges list
- [ ] Test transaction monitoring (requires mainnet)
- [ ] Test balance crediting

## Component D: Yield Manager
- [ ] Create stake (Stable tier 7.5%)
- [ ] Create stake (Growth tier 9.0%)
- [ ] Create stake (Alpha tier 11.0%)
- [ ] Calculate yield
- [ ] Partial unstake
- [ ] Full unstake
- [ ] Get tier information
- [ ] Verify fee calculation (2% mgmt + 20% performance)

## End-to-End Journey
- [ ] Deposit (on-ramp)
- [ ] Stake for yield
- [ ] Check earnings
- [ ] Unstake
- [ ] Withdraw (off-ramp)
- [ ] Verify total revenue captured

## Revenue Tracking
- [ ] On-ramp fees recorded
- [ ] Off-ramp fees recorded
- [ ] Yield management fees recorded
- [ ] Revenue dashboard accurate