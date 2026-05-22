# FILE: backend/api/routes/learn.py
# Production-Ready Simplified Financial Literacy Routes — Focused on Quest Core
# Mount at: /api/v1/learn in main.py

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from backend.dependencies import get_current_user, get_supabase_client
from backend.services.qvac_service import (
    stream_qvac_response,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/learn", tags=["financial-literacy"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class TutorAskRequest(BaseModel):
    message:     str
    module_id:   Optional[str]  = None
    device_tier: str            = "desktop"

class QuizAnswerRequest(BaseModel):
    question_id: str
    answer:      int            # index into options_json


# ── Helper: get user's total XP ───────────────────────────────────────────────

async def get_user_xp(user_id: str, supabase) -> int:
    """Calculates total XP from the ledger for the user."""
    result = (
        supabase.from_("xp_ledger")
        .select("xp_amount")
        .eq("user_id", user_id)
        .execute()
    )
    return sum(r["xp_amount"] for r in (result.data or []))


# ──────────────────────────────────────────────────────────────────────────────
# LOOP A: FINANCE QUEST & AI TUTOR
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
        track["unlocked"] = True   # All tracks visible

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

    # Strip correct_answer from questions to prevent client-side cheating
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
            # Streams token-by-token to bypass network timeouts
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
        # Award XP to ledger
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

    # Prevent double-awarding
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


# ── XP summary (used by frontend) ────────────────────────────────────────────

@router.get("/xp")
async def get_xp_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase                     = Depends(get_supabase_client),
):
    """Get user's total XP and recent activity."""
    user_id  = current_user["id"]
    total_xp = await get_user_xp(user_id, supabase)

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
        "recent_events": recent_events.data or [],
    }