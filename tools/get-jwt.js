// File Location: /tools/get-jwt.js
const { createClient } = require('@supabase/supabase-js');
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'logs/get-jwt.log' }),
    new winston.transports.Console()
  ]
});

const supabaseUrl = 'https://opqnoficlhbylxfpaehp.supabase.co';
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wcW5vZmljbGhieWx4ZnBhZWhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAxNzUwNjksImV4cCI6MjA2NTc1MTA2OX0.G0GBnChH_7MugThxXpkYivN_sfBWts6ehaWjtM6B50I';

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function withRetry(fn, retries = 3, delay = 1000) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      logger.error(`Attempt ${attempt} failed: ${error.message}`);
      if (attempt === retries) {
        logger.error('Max retries reached. Giving up.');
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, delay));
      logger.info(`Retrying... (${attempt + 1}/${retries})`);
    }
  }
}

async function getJwt() {
  try {
    const signIn = async () => {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: 'support@seamount.io',
        password: 'acce$$free' // REPLACE WITH YOUR REAL PASSWORD
      });
      if (error) throw new Error(`Sign-in failed: ${error.message}`);
      return data;
    };

    const data = await withRetry(signIn);
    const jwt = data.session?.access_token;
    if (!jwt) {
      throw new Error('No JWT found in session');
    }
    logger.info('JWT retrieved successfully');
    console.log('JWT:', jwt);
    return jwt;
  } catch (error) {
    logger.error(`Failed to retrieve JWT: ${error.message}`);
    console.error('Error:', error.message);
    throw error;
  }
}

getJwt().catch(error => {
  logger.error('Script execution failed', { error: error.message });
  process.exit(1);
});