import { Router } from 'express';
const r = Router();

r.post('/consent/cookies', (req, res) => {
  // no-op storage or persist minimal record if you like
  return res.json({ ok: true });
});

export default r;
