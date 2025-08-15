import { Router } from 'express';
import { requireUser } from '../middleware/auth';
import { getProfileById } from '../db/userProfiles';

const r = Router();

r.get('/api/v1/user/profile', requireUser, async (req, res) => {
  try {
    const userId = (req as any).authUser.id;
    const profile = await getProfileById(userId);
    if (!profile) return res.status(404).json({ error: 'profile not found' });
    return res.json(profile);
  } catch (e) {
    console.error('[GET /user/profile] error:', e);
    return res.status(500).json({ error: 'internal' });
  }
});

export default r;
