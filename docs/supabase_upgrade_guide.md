# Definitive Supabase Database Upgrade Guide
## Using Managed Backup & Restore (Production-Safe Route)

> **For Seamount.io PostgreSQL 17.x Security Patch Upgrade**  
> **Timeline: 2-4 hours total | Downtime: 5-30 minutes**

---

## Phase 1: Upgrade Plan & Pre-Flight Setup (30 minutes)

### Step 1.1: Upgrade Supabase Plan
1. **Go to** Supabase Dashboard → Your Project → Settings → Billing
2. **Upgrade to Pro Plan** ($25/month)
3. **Verify upgrade** - you should now see "Backups" in your dashboard
4. **Wait 5 minutes** for plan activation

### Step 1.2: Create Managed Backup (Critical Safety Net)
1. **Navigate to** Dashboard → Database → Backups
2. **Click** "Create Backup" 
3. **Name it:** `pre-upgrade-backup-security-patch`
4. **Wait for completion** (2-10 minutes depending on DB size)
5. **RECORD BACKUP ID** - write it down immediately: `backup-[ID]`

### Step 1.3: Verify Backup Integrity
```bash
# Test restore capability (optional but recommended)
# Go to Dashboard → Database → Backups → Your Backup → "Restore"
# Select "Restore to new project" to test (delete test project after)
```

### Step 1.4: Application Preparation
```bash
# Create maintenance page/mode
echo "MAINTENANCE_MODE=true" >> .env

# Notify users (if applicable)
# - Email notifications
# - In-app announcements
# - Status page updates
```

---

## Phase 2: Submit Upgrade Request (15 minutes)

### Step 2.1: Document Current State
```bash
# Run this in Supabase SQL Editor to document extensions:
SELECT extname, extversion FROM pg_extension ORDER BY extname;

# Document PostgreSQL version:
SELECT version();

# Record table count:
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
```

### Step 2.2: Submit Support Ticket

**Subject:** `URGENT: PostgreSQL 17.x Security Patch Upgrade - Project [YOUR_PROJECT_ID]`

**Template:**
```
Hi Supabase Support Team,

REQUEST: Managed PostgreSQL security patch upgrade for production system.

PROJECT DETAILS:
- Project ID: [YOUR_PROJECT_ID]
- Current Version: PostgreSQL 17.4 (aarch64)  
- Target: Latest PostgreSQL 17.x security patch
- Plan: Pro (recently upgraded for backup access)

PRE-UPGRADE SAFETY MEASURES COMPLETED:
✅ Managed backup created: backup-[YOUR_BACKUP_ID]
✅ Backup verified and accessible
✅ Application prepared for maintenance window
✅ Extensions documented: pg_graphql, pg_stat_statements, pgcrypto, plpgsql, supabase_vault, uuid-ossp

SYSTEM CONTEXT:
- Production fintech application (Seamount.io P2P payments)
- Zero-tolerance for data loss
- Stablecoin transaction processing system
- 26 tables with active user data

MAINTENANCE WINDOW PREFERENCES:
- Primary: [TODAY/TOMORROW] 23:00-01:00 UTC (2 hours)
- Backup: [DATE] 02:00-04:00 UTC (2 hours)

CRITICAL REQUIREMENTS:
1. Confirm extension compatibility with target patch
2. Provide accurate downtime estimate  
3. Confirm rollback procedure using managed backup
4. Any manual steps required post-upgrade?
5. Notification 30 minutes before starting upgrade

CONTACT: [YOUR_EMAIL]
PRIORITY: Critical Security Update
EXPECTED RESPONSE: Within 2 hours

This is production infrastructure processing financial transactions. 
Please confirm receipt and provide upgrade timeline.

Thank you,
[YOUR_NAME]
[YOUR_TITLE]
```

---

## Phase 3: Pre-Upgrade Final Preparations (30 minutes)

### Step 3.1: Application Readiness
```bash
# Enable maintenance mode
export MAINTENANCE_MODE=true

# Stop background jobs/cron tasks
# - Yield farming calculations  
# - Analytics processing
# - Email notifications
# - Report generation

# Scale down non-essential services
```

### Step 3.2: Monitor Setup
```bash
# Prepare monitoring dashboard
# - Database connection count
# - Query response times  
# - Error rates
# - Transaction throughput

# Alert team members
# - Database team on standby
# - DevOps team ready
# - Customer support prepared for inquiries
```

### Step 3.3: Communication
```bash
# User notifications:
# "Seamount.io will undergo a brief maintenance window from [TIME] to [TIME]
#  for a security update. All funds remain secure. Expected downtime: 15-30 minutes."

# Stakeholder notifications:
# "Security patch upgrade in progress. Monitoring all systems."
```

---

## Phase 4: During Upgrade (Supabase Handles)

### What Supabase Will Do:
1. **Pre-upgrade snapshot** (automatic)
2. **Apply PostgreSQL security patches**
3. **Extension compatibility verification**
4. **Database restart** (brief downtime)
5. **Post-upgrade validation**

### Your Monitoring Tasks:
```bash
# Watch for Supabase notifications
# - Email updates from support team
# - Dashboard status changes
# - Upgrade progress indicators

# Monitor your application:
# - Connection pool status
# - Health check endpoints  
# - Error logging systems
```

### Expected Timeline:
- **Preparation:** 15 minutes (by Supabase)
- **Actual upgrade:** 5-30 minutes (database restart)
- **Validation:** 10 minutes (by Supabase)
- **Total:** 30-60 minutes

---

## Phase 5: Post-Upgrade Validation (45 minutes)

### Step 5.1: Immediate Health Checks (15 minutes)
```sql
-- Run in Supabase SQL Editor:

-- Verify PostgreSQL version
SELECT version();

-- Check extension integrity  
SELECT extname, extversion FROM pg_extension ORDER BY extname;

-- Verify RLS policies
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables WHERE table_schema = 'public' AND rowsecurity = true;

-- Count tables and basic data integrity
SELECT 
  schemaname,
  COUNT(*) as table_count
FROM pg_tables 
WHERE schemaname = 'public' 
GROUP BY schemaname;

-- Test critical queries
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM user_profiles;
SELECT COUNT(*) FROM transactions;
```

### Step 5.2: Application Testing (20 minutes)
```bash
# Disable maintenance mode
unset MAINTENANCE_MODE

# Test core functionality:
# ✅ User authentication
# ✅ Database connections
# ✅ Read/write operations
# ✅ Payment processing (test mode)
# ✅ API endpoints
# ✅ Real-time features

# Integration smoke tests
npm run test:integration:critical
```

### Step 5.3: Performance Validation (10 minutes)
```bash
# Monitor for 10 minutes:
# - Query response times
# - Connection pool utilization  
# - Error rates
# - Memory usage
# - CPU utilization

# Compare against pre-upgrade baselines
```

---

## Phase 6: Full System Restoration (30 minutes)

### Step 6.1: Re-enable Services
```bash
# Restart background jobs
# - Yield farming calculations
# - Analytics processing  
# - Scheduled reports
# - Email notifications

# Scale services back to normal
```

### Step 6.2: User Communication
```bash
# Success notification:
# "✅ Seamount.io maintenance complete! All systems operational with enhanced security."

# Monitor user activity:
# - Login success rates
# - Transaction volumes
# - Support ticket volume
# - User feedback
```

### Step 6.3: Extended Monitoring (24 hours)
```bash
# Enhanced monitoring for 24-48 hours:
# - Database performance metrics
# - Application error rates  
# - User experience metrics
# - Transaction processing times

# Daily reports for first week post-upgrade
```

---

## Emergency Rollback Procedures

### If Issues Detected During Upgrade:
```bash
# Contact Supabase Support immediately:
# "URGENT: Request immediate rollback for project [PROJECT_ID] 
#  using backup backup-[BACKUP_ID]. Critical issues detected."

# Expected rollback time: 10-30 minutes
```

### If Issues Detected Post-Upgrade:
```bash
# 1. Enable maintenance mode immediately
export MAINTENANCE_MODE=true

# 2. Contact Supabase Support:
# "URGENT: Request database restore from backup-[BACKUP_ID] 
#  for project [PROJECT_ID]. Production issues detected post-upgrade."

# 3. Prepare incident report
# 4. Notify stakeholders
# 5. Monitor rollback process
```

---

## Success Criteria Checklist

### ✅ Pre-Upgrade Complete:
- [ ] Supabase Pro plan activated
- [ ] Managed backup created and verified  
- [ ] Support ticket submitted
- [ ] Application prepared for maintenance
- [ ] Team notified and on standby
- [ ] Users notified of maintenance window

### ✅ Upgrade Complete:
- [ ] PostgreSQL version updated to latest 17.x patch
- [ ] All extensions functional and compatible
- [ ] RLS policies preserved
- [ ] Table integrity verified (26 tables present)
- [ ] Data integrity confirmed (row counts match)
- [ ] Application functionality restored

### ✅ Post-Upgrade Validation:
- [ ] Core user flows working (auth, payments, transactions)
- [ ] Performance metrics within acceptable ranges
- [ ] No increase in error rates
- [ ] Background jobs resumed successfully
- [ ] User activity returned to normal levels
- [ ] 24-hour monitoring period completed

---

## Cost Analysis

**Supabase Pro Plan:** $25/month (cancel after upgrade if desired)
**Total Upgrade Cost:** $25 one-time
**Downtime Cost Avoided:** Potentially thousands (vs. failed upgrade)
**Data Protection:** Priceless for fintech application

**ROI:** Managed backup alone is worth the upgrade cost for peace of mind.

---

## Final Notes

- **This is the production-safe approach** for financial applications
- **Supabase's managed infrastructure** handles the complex upgrade process
- **Your data is protected** with enterprise-grade backup and restore
- **Minimal downtime** with professional support team handling the upgrade
- **Complete rollback capability** if any issues arise

**Execute this plan during low-traffic hours for optimal user experience.**