#!/usr/bin/env node
// deploy-usds-devnet.js
// Location: /scripts/deploy-usds-devnet.js

import DevnetDeploymentExecutor from '../backend/deployment/devnet-deployment-executor.js';
import fs from 'fs';
import path from 'path';

/**
 * USDS Devnet Deployment Script - FIXED VERSION
 * Addresses the summary file not found error
 */

async function main() {
    const executor = new DevnetDeploymentExecutor();
    
    try {
        console.log('🚀 Starting USDS Devnet Deployment...');
        console.log('⏰ Timestamp:', new Date().toISOString());
        
        // Execute deployment
        const summary = await executor.execute();
        
        // Double-check file exists
        const summaryPath = path.join(process.cwd(), 'deployment-artifacts', 'devnet-deployment-summary.json');
        
        if (!fs.existsSync(summaryPath)) {
            throw new Error('❌ Summary file not found after deployment');
        }
        
        const fileSize = fs.statSync(summaryPath).size;
        console.log(`✅ Summary file verified: ${fileSize} bytes`);
        
        // Print success summary
        console.log('\n🎉 DEPLOYMENT SUCCESSFUL!');
        console.log('========================');
        console.log(`📄 Summary: ${summaryPath}`);
        console.log(`🪙 USDS Token: ${summary.token.mint}`);
        console.log(`🌐 Explorer: ${summary.endpoints.explorer}`);
        console.log(`⛽ Gas Reserve: ${summary.feeStructure.gasReserve}`);
        console.log(`⏱️ Duration: ${(summary.deployment.duration / 1000).toFixed(2)}s`);
        
        if (summary.deployment.warnings.length > 0) {
            console.log('\n⚠️ Warnings:');
            summary.deployment.warnings.forEach(w => console.log(`  - ${w}`));
        }
        
        console.log('\n🎯 Next Steps:');
        console.log('1. Test token transfers');
        console.log('2. Verify fee calculations');
        console.log('3. Setup monitoring');
        console.log('4. Prepare mainnet deployment');
        
    } catch (error) {
        console.error('\n❌ DEPLOYMENT FAILED');
        console.error('Error:', error.message);
        
        // Check if we have partial artifacts
        const artifactsDir = path.join(process.cwd(), 'deployment-artifacts');
        if (fs.existsSync(artifactsDir)) {
            console.log('\n📁 Partial artifacts may be available in:', artifactsDir);
            
            const files = fs.readdirSync(artifactsDir);
            if (files.length > 0) {
                console.log('Available files:');
                files.forEach(f => console.log(`  - ${f}`));
            }
        }
        
        process.exit(1);
    }
}

// Run deployment
main().catch(error => {
    console.error('❌ Deployment script failed:', error);
    process.exit(1);
});