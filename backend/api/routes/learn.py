# FILE: backend/api/routes/learn.py
# Financial Literacy Routes — Loops A (Quest), C (Wellbeing), D (Signal Guild)
# Mount at: /api/v1/learn in main.py

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse

from backend.dependencies import get_current_user, get_supabase_client
from backend.services.qvac_service import (
    tutor_ask,
    coach_analyze,
    generate_wellbeing_score,
    validate_signal,
    stream_qvac_response,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/learn", tags=["financial-literacy"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class TutorAskRequest(BaseModel):
    message:     str
    module_id:   Optional[str]  = None
    device_tier: str            = "desktop"

class FinancialProfileRequest(BaseModel):
    country_code:            str   = "NG"
    income_range:            Optional[str]
    income_source:           Optional[str]
    debt_total:              float = 0
    savings_rate:            float = 0
    crypto_exposure_pct:     float = 0
    mobile_money_balance:    Optional[str]
    remittance_monthly:      float = 0
    susu_ajo_participation:  bool  = False
    chama_participation:     bool  = False
    goals_json:              dict  = {}

class CoachAskRequest(BaseModel):
    message:     str
    device_tier: str = "desktop"

class QuizAnswerRequest(BaseModel):
    question_id: str
    answer:      int            # index into options_json

class SignalSubmitRequest(BaseModel):
    asset_symbol: str
    direction:    str           = Field(..., pattern="^(BUY|SELL)$")
    thesis:       str           = Field(..., min_length=50, max_length=2000)
    timeframe:    str
    entry_price:  Optional[float]
    target_price: Optional[float]
    stop_loss:    Optional[float]

class VoteRequest(BaseModel):
    vote_type: str = Field(..., pattern="^(up|down|flag)$")


# ── Helper: get user's total XP ───────────────────────────────────────────────

async def get_user_xp(user_id: str, supabase) -> int:
    result = (
        supabase.from_("xp_ledger")
        .select("xp_amount")
        .eq("user_id", user_id)
        .execute()
    )
    return sum(r["xp_amount"] for r in (result.data or []))


async def check_access_gate(action: str, user_id: str, supabase) -> None:
    """Raise 403 if user doesn't meet XP/wellbeing requirements."""
    gate = (
        supabase.from_("guild_access_gates")
        .select("*")
        .eq("action_type", action)
        .single()
        .execute()
    )
    if not gate.data:
        return  # No gate configured = open access

    g       = gate.data
    user_xp = await get_user_xp(user_id, supabase)

    if user_xp < g["min_xp"]:
        raise HTTPException(
            status_code=403,
            detail=f"Need {g['min_xp']} XP to {action}. You have {user_xp} XP. "
                   f"Complete quests to unlock this feature."
        )

    if g.get("min_wellbeing_score"):
        latest_score = (
            supabase.from_("wellbeing_scores")
            .select("score")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not latest_score.data:
            raise HTTPException(
                status_code=403,
                detail="Complete your Financial Wellbeing Score first to access this feature."
            )
        if latest_score.data[0]["score"] < g["min_wellbeing_score"]:
            raise HTTPException(
                status_code=403,
                detail=f"Wellbeing Score too low. Improve your financial health to unlock this feature."
            )


# ──────────────────────────────────────────────────────────────────────────────
# LOOP A: FINANCE QUEST
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/quests/tracks")
async def get_quest_tracks(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get all active quest tracks with user progress."""
    user_id = current_user["id"]

    tracks = (
        supabase.from_("quest_tracks")
        .select("*, quest_modules(id, title, xp_reward, order_index)")
        .eq("is_active", True)
        .order("order_index")
        .execute()
    )

    # Get user progress for all modules
    progress = (
        supabase.from_("user_quest_progress")
        .select("module_id, completed, xp_earned")
        .eq("user_id", user_id)
        .execute()
    )
    completed_modules = {p["module_id"] for p in (progress.data or []) if p["completed"]}
    total_xp          = await get_user_xp(user_id, supabase)

    # Enrich tracks with progress
    for track in (tracks.data or []):
        modules           = track.get("quest_modules", [])
        completed_count   = sum(1 for m in modules if m["id"] in completed_modules)
        track["progress"] = {"completed": completed_count, "total": len(modules)}
        track["unlocked"] = True   # All tracks visible; individual modules gate by XP

    return {
        "success": True,
        "tracks":  tracks.data or [],
        "user_xp": total_xp,
    }


@router.get("/quests/module/{module_id}")
async def get_quest_module(
    module_id:    str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get a specific module with its questions."""
    module = (
        supabase.from_("quest_modules")
        .select("*, quest_tracks(title, difficulty), quest_questions(*)")
        .eq("id", module_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    if not module.data:
        raise HTTPException(status_code=404, detail="Module not found")

    # Strip correct_answer from questions (sent only after answer submission)
    questions = module.data.get("quest_questions", [])
    for q in questions:
        q.pop("correct_answer", None)

    return {"success": True, "module": module.data}


@router.post("/quests/tutor/ask")
async def ask_tutor(
    body:         TutorAskRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Ask the QVAC tutor a question via real-time stream."""
    user_id = current_user["id"]
    context = {"module_id": body.module_id} if body.module_id else {}
    
    logger.info(f"[Tutor] User {user_id[:8]} asking (streaming): {body.message[:60]}")
    
    payload = {
        "message": body.message,
        "context": context,
        "device_tier": body.device_tier
    }

    async def event_generator():
        try:
            async for token in stream_qvac_response("/v1/tutor/ask", payload):
                yield token
        except Exception as e:
            logger.error(f"[Tutor Stream Error] {e}")
            yield "\n\n⚠️ Connection interrupted. Please try again."

    return StreamingResponse(event_generator(), media_type="text/plain")


@router.post("/quests/answer")
async def submit_quiz_answer(
    body:         QuizAnswerRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Submit a quiz answer — returns correct/incorrect + explanation + XP."""
    user_id = current_user["id"]

    question = (
        supabase.from_("quest_questions")
        .select("*, quest_modules(id, xp_reward)")
        .eq("id", body.question_id)
        .single()
        .execute()
    )
    if not question.data:
        raise HTTPException(status_code=404, detail="Question not found")

    q          = question.data
    is_correct = body.answer == q["correct_answer"]
    xp_earned  = q["xp_reward"] if is_correct else 0

    if is_correct and xp_earned > 0:
        # Award XP
        supabase.from_("xp_ledger").insert({
            "user_id":        user_id,
            "event_type":     "quiz_correct",
            "xp_amount":      xp_earned,
            "reference_id":   body.question_id,
            "reference_type": "quest_question",
        }).execute()

        # Update module progress
        module_id = q["quest_modules"]["id"]
        supabase.from_("user_quest_progress").upsert({
            "user_id":   user_id,
            "module_id": module_id,
            "score":     1,
            "xp_earned": xp_earned,
        }, on_conflict="user_id,module_id").execute()

    return {
        "success":     True,
        "correct":     is_correct,
        "explanation": q.get("explanation", ""),
        "xp_earned":   xp_earned,
        "message":     f"Correct! +{xp_earned} XP 🎉" if is_correct else "Not quite — review the explanation below.",
    }


@router.post("/quests/module/{module_id}/complete")
async def complete_module(
    module_id:    str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Mark a module as fully completed — awards module completion XP."""
    user_id = current_user["id"]

    module = (
        supabase.from_("quest_modules")
        .select("xp_reward, title")
        .eq("id", module_id)
        .single()
        .execute()
    )
    if not module.data:
        raise HTTPException(status_code=404, detail="Module not found")

    # Idempotent — don't double-award
    existing = (
        supabase.from_("user_quest_progress")
        .select("completed")
        .eq("user_id", user_id)
        .eq("module_id", module_id)
        .execute()
    )
    if existing.data and existing.data[0].get("completed"):
        return {"success": True, "message": "Already completed", "xp_earned": 0}

    xp = module.data["xp_reward"]
    supabase.from_("xp_ledger").insert({
        "user_id":        user_id,
        "event_type":     "module_complete",
        "xp_amount":      xp,
        "reference_id":   module_id,
        "reference_type": "quest_module",
    }).execute()

    supabase.from_("user_quest_progress").upsert({
        "user_id":      user_id,
        "module_id":    module_id,
        "completed":    True,
        "xp_earned":    xp,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,module_id").execute()

    return {
        "success":   True,
        "xp_earned": xp,
        "message":   f"Module complete! +{xp} XP 🎓",
    }


# ──────────────────────────────────────────────────────────────────────────────
# LOOP C: WELLBEING COACH
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/wellbeing/profile")
async def save_financial_profile(
    body:         FinancialProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Save or update the user's financial profile."""
    user_id = current_user["id"]

    supabase.from_("user_financial_profiles").upsert(
        {"user_id": user_id, **body.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()},
        on_conflict="user_id"
    ).execute()

    return {"success": True, "message": "Profile saved"}


@router.get("/wellbeing/profile")
async def get_financial_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get the user's financial profile."""
    user_id = current_user["id"]
    result  = (
        supabase.from_("user_financial_profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return {"success": True, "profile": result.data}


@router.post("/wellbeing/score")
async def generate_score(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Generate a fresh Wellbeing Score from the user's financial profile."""
    user_id = current_user["id"]

    profile_result = (
        supabase.from_("user_financial_profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(
            status_code=400,
            detail="Complete your financial profile first to generate a score."
        )

    profile = profile_result.data

    try:
        score_data = await generate_wellbeing_score(profile)
    except RuntimeError as e:
        logger.error(f"[Wellbeing] Score generation failed for {user_id}: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    # Persist score
    supabase.from_("wellbeing_scores").insert({
        "user_id":        user_id,
        "score":          score_data["score"],
        "breakdown_json": score_data["breakdown"],
        "ai_summary":     score_data["summary"],
        "top_action":     score_data["top_action"],
        "risk_flags":     score_data["risk_flags"],
    }).execute()

    # Award XP for first score completion
    existing_scores = (
        supabase.from_("wellbeing_scores")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    if len(existing_scores.data or []) == 1:   # first score just created
        supabase.from_("xp_ledger").insert({
            "user_id":        user_id,
            "event_type":     "wellbeing_complete",
            "xp_amount":      200,
            "reference_type": "wellbeing_score",
        }).execute()

    # Generate first nudge
    await _generate_nudge(user_id, score_data, profile, supabase)

    return {"success": True, **score_data}


@router.get("/wellbeing/scores")
async def get_score_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get wellbeing score history."""
    user_id = current_user["id"]
    scores  = (
        supabase.from_("wellbeing_scores")
        .select("score, breakdown_json, ai_summary, top_action, risk_flags, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    return {"success": True, "scores": scores.data or []}


@router.post("/wellbeing/coach/ask")
async def ask_coach(
    body:         CoachAskRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Ask the wellbeing coach a question via real-time stream."""
    user_id = current_user["id"]

    profile_result = (
        supabase.from_("user_financial_profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    profile = profile_result.data or {}
    
    payload = {
        "message": body.message,
        "profile": profile,
        "device_tier": body.device_tier
    }

    async def event_generator():
        try:
            async for token in stream_qvac_response("/v1/coach/analyze", payload):
                yield token
        except Exception as e:
            logger.error(f"[Coach Stream Error] {e}")
            yield "\n\n⚠️ Connection interrupted. Please try again."

    return StreamingResponse(event_generator(), media_type="text/plain")


@router.get("/wellbeing/nudges")
async def get_nudges(
    unread_only:  bool                = Query(default=False),
    current_user: Dict[str, Any]      = Depends(get_current_user),
    supabase                          = Depends(get_supabase_client),
):
    """Get user's wellbeing nudges."""
    user_id = current_user["id"]
    query   = (
        supabase.from_("wellbeing_nudges")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
    )
    if unread_only:
        query = query.eq("is_read", False)

    result = query.execute()
    return {"success": True, "nudges": result.data or []}


@router.patch("/wellbeing/nudges/{nudge_id}/read")
async def mark_nudge_read(
    nudge_id:     str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    supabase.from_("wellbeing_nudges").update({"is_read": True}).eq("id", nudge_id).eq("user_id", current_user["id"]).execute()
    return {"success": True}


async def _generate_nudge(user_id: str, score_data: dict, profile: dict, supabase) -> None:
    """Generate a contextual nudge based on score breakdown."""
    breakdown  = score_data.get("breakdown", {})
    risk_flags = score_data.get("risk_flags", [])
    country    = profile.get("country_code", "NG")

    nudges = []

    # Savings health nudge
    if breakdown.get("savings_health", 25) < 15:
        platform = "PiggyVest" if country == "NG" else "M-Shwari"
        nudges.append({
            "nudge_text":  f"Your savings score is low. Try automating 5% of your income to {platform} this week — small consistent amounts beat large irregular ones.",
            "category":    "savings",
            "action_type": "view_yield",
            "action_data": {"route": "/xrp"},
        })

    # Debt management nudge
    if breakdown.get("debt_management", 25) < 15:
        nudges.append({
            "nudge_text":  "High debt ratio detected. List all your debts by interest rate today. Pay minimums on everything — attack the highest rate first.",
            "category":    "debt",
            "action_type": "complete_quest",
            "action_data": {"quest_slug": "credit-mastery"},
        })

    # Crypto exposure nudge
    if profile.get("crypto_exposure_pct", 0) > 30:
        nudges.append({
            "nudge_text":  "Your crypto exposure exceeds 30% of your portfolio. Consider rebalancing — high crypto allocation in volatile markets is a risk flag.",
            "category":    "crypto",
            "action_type": "complete_quest",
            "action_data": {"quest_slug": "sustainable-investing"},
        })

    # Top action nudge
    if score_data.get("top_action"):
        nudges.append({
            "nudge_text":  score_data["top_action"],
            "category":    "general",
            "action_type": None,
            "action_data": {},
        })

    for nudge in nudges[:3]:   # Max 3 nudges per score generation
        supabase.from_("wellbeing_nudges").insert({
            "user_id": user_id,
            **nudge,
        }).execute()


# ──────────────────────────────────────────────────────────────────────────────
# LOOP D: SIGNAL GUILD
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/guild/signals")
async def get_guild_signals(
    asset:        Optional[str]  = Query(default=None),
    limit:        int            = Query(default=20, le=50),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get approved guild signals. Requires min 50 XP."""
    user_id = current_user["id"]
    await check_access_gate("view_signals", user_id, supabase)

    query = (
        supabase.from_("guild_signals")
        .select("""
            id, asset_symbol, direction, thesis, timeframe,
            entry_price, target_price, stop_loss,
            qvac_score, qvac_explanation, qvac_recommendation,
            upvotes, downvotes, flag_count, expires_at, created_at,
            guild_reputation!inner(reputation_score, accuracy_rate)
        """)
        .eq("status", "approved")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if asset:
        query = query.ilike("asset_symbol", f"%{asset}%")

    result = query.execute()
    return {"success": True, "signals": result.data or []}


@router.post("/guild/signals")
async def submit_signal(
    body:         SignalSubmitRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Submit a signal to the guild. Requires 500 XP + Wellbeing Score."""
    user_id = current_user["id"]
    await check_access_gate("submit_signal", user_id, supabase)

    # Get submitter reputation for QVAC context
    rep = (
        supabase.from_("guild_reputation")
        .select("reputation_score, accuracy_rate, total_signals")
        .eq("user_id", user_id)
        .execute()
    )
    submitter_stats = rep.data[0] if rep.data else {}

    signal_data = body.model_dump()
    signal_data["user_id"] = user_id

    # Validate with QVAC before saving
    try:
        validation = await validate_signal(signal_data, submitter_stats)
    except Exception as e:
        logger.error(f"[Guild] QVAC validation failed for {user_id}: {e}")
        raise HTTPException(status_code=503, detail="Signal validation temporarily unavailable.")

    # Auto-reject scams
    if validation.get("recommendation") == "SCAM_ALERT":
        logger.warning(f"[Guild] SCAM_ALERT signal rejected from {user_id}: {signal_data['thesis'][:100]}")
        raise HTTPException(
            status_code=422,
            detail=f"Signal rejected: {', '.join(validation.get('manipulation_flags', ['Manipulation detected']))}. "
                   f"⚠️ Submitting manipulative signals will result in account suspension."
        )

    # Auto-reject very low quality
    if validation.get("quality_score", 0) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Signal quality too low (score: {validation['quality_score']}/100). "
                   f"Improve your thesis clarity and include a stop loss."
        )

    status     = "approved" if validation.get("quality_score", 0) >= 50 else "pending_review"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    new_signal = supabase.from_("guild_signals").insert({
        **signal_data,
        "status":              status,
        "qvac_score":          validation.get("quality_score"),
        "qvac_explanation":    validation.get("plain_explanation"),
        "qvac_recommendation": validation.get("recommendation"),
        "manipulation_flags":  validation.get("manipulation_flags", []),
        "expires_at":          expires_at,
    }).execute()

    # Init reputation record if first signal
    supabase.from_("guild_reputation").upsert({
        "user_id":       user_id,
        "total_signals": 1,
    }, on_conflict="user_id").execute()

    # Award XP for submitting a quality signal
    if status == "approved":
        supabase.from_("xp_ledger").insert({
            "user_id":        user_id,
            "event_type":     "signal_submitted",
            "xp_amount":      100,
            "reference_id":   new_signal.data[0]["id"] if new_signal.data else None,
            "reference_type": "guild_signal",
        }).execute()

    return {
        "success":    True,
        "signal_id":  new_signal.data[0]["id"] if new_signal.data else None,
        "status":     status,
        "qvac_score": validation.get("quality_score"),
        "explanation":validation.get("plain_explanation"),
        "disclaimer": validation.get("disclaimer"),
        "message":    "Signal submitted and approved!" if status == "approved" else "Signal submitted for review.",
    }


@router.post("/guild/signals/{signal_id}/vote")
async def vote_on_signal(
    signal_id:    str,
    body:         VoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Vote or flag a signal. Requires 100 XP."""
    user_id = current_user["id"]
    await check_access_gate("vote", user_id, supabase)

    # Can't vote on own signals
    signal = supabase.from_("guild_signals").select("user_id").eq("id", signal_id).single().execute()
    if signal.data and signal.data["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot vote on your own signal.")

    try:
        supabase.from_("guild_signal_votes").insert({
            "signal_id": signal_id,
            "user_id":   user_id,
            "vote_type": body.vote_type,
        }).execute()
    except Exception:
        raise HTTPException(status_code=400, detail="Already voted on this signal.")

    # Denormalise vote counts
    if body.vote_type == "up":
        supabase.rpc("increment_signal_upvotes",   {"signal_id": signal_id}).execute()
    elif body.vote_type == "down":
        supabase.rpc("increment_signal_downvotes", {"signal_id": signal_id}).execute()
    elif body.vote_type == "flag":
        supabase.rpc("increment_signal_flags",     {"signal_id": signal_id}).execute()
        # Auto-hide signals with 5+ flags
        flag_count = (
            supabase.from_("guild_signals")
            .select("flag_count")
            .eq("id", signal_id)
            .single()
            .execute()
        )
        if flag_count.data and flag_count.data.get("flag_count", 0) >= 5:
            supabase.from_("guild_signals").update({"status": "flagged"}).eq("id", signal_id).execute()
            logger.warning(f"[Guild] Signal {signal_id} auto-hidden: 5+ community flags")

    return {"success": True, "voted": body.vote_type}


@router.get("/guild/reputation/{user_id}")
async def get_reputation(
    user_id:      str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get a user's guild reputation (public)."""
    result = (
        supabase.from_("guild_reputation")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return {"success": True, "reputation": result.data}


# ── XP summary (used by frontend) ────────────────────────────────────────────

@router.get("/xp")
async def get_xp_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get user's XP total and unlock status for all access gates."""
    user_id  = current_user["id"]
    total_xp = await get_user_xp(user_id, supabase)

    gates = supabase.from_("guild_access_gates").select("*").execute()
    unlocks = {}
    for gate in (gates.data or []):
        unlocks[gate["action_type"]] = total_xp >= gate["min_xp"]

    recent_events = (
        supabase.from_("xp_ledger")
        .select("event_type, xp_amount, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    return {
        "success":       True,
        "total_xp":      total_xp,
        "unlocks":       unlocks,
        "recent_events": recent_events.data or [],
    }