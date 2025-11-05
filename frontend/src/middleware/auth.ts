import type { Request, Response, NextFunction } from 'express';
const jwt = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');

const client = jwksClient({
  jwksUri: `${process.env.SUPABASE_URL}/auth/v1/.well-known/jwks.json`,
  cache: true,
  cacheMaxEntries: 5,
  cacheMaxAge: 600000, // 10 min
});

async function getSigningKey(kid: string): Promise<string> {
  return new Promise((resolve, reject) => {
    client.getSigningKey(kid, (err: Error | null, key: any) => {
      if (err) return reject(err);
      resolve(key.publicKey || key.rsaPublicKey);
    });
  });
}

export async function requireUser(req: Request, res: Response, next: NextFunction) {
  try {
    const auth = req.headers.authorization || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : null;
    console.log(`[requireUser] Token prefix: ${token ? token.slice(0,6) : 'no token'}`);
    if (!token) return res.status(401).json({ error: 'missing token' });

    const decoded = jwt.decode(token, { complete: true });
    if (!decoded || !decoded.header.kid) return res.status(401).json({ error: 'invalid token format' });
    const key = await getSigningKey(decoded.header.kid);
    const verified = jwt.verify(token, key, { algorithms: ['RS256'], audience: 'authenticated' });
    (req as any).authUser = { id: verified.sub };
    next();
  } catch (e) {
    console.error('[requireUser] validation error:', (e as Error).name || (e as Error).message);
    return res.status(401).json({ error: 'unauthorized' });
  }
}