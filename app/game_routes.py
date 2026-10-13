import random
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import get_db_connection
from app.models import GameStartRequest, GameAnswerRequest, GameFinishRequest

router = APIRouter(prefix="/api/game", tags=["game"])

@router.get("/goals")
def get_all_goals():
    conn = get_db_connection()
    goals = conn.execute("SELECT * FROM goals ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(g) for g in goals]

@router.get("/targets")
def get_targets(goal_id: Optional[int] = None, q: Optional[str] = None):
    conn = get_db_connection()
    sql = "SELECT t.*, g.name as goal_name, g.color as goal_color, g.category_zh as category_5p FROM targets t JOIN goals g ON t.goal_id = g.id WHERE t.is_active = 1"
    params = []
    if goal_id:
        sql += " AND t.goal_id = ?"
        params.append(goal_id)
    if q:
        sql += " AND (t.description LIKE ? OR t.code LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    sql += " ORDER BY t.goal_id ASC, t.id ASC"
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/start")
def start_game(req: GameStartRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO challengers (nickname, organization, avatar)
    VALUES (?, ?, ?)
    """, (req.nickname.strip(), req.organization.strip() if req.organization else "一般挑戰者", req.avatar))
    challenger_id = cursor.lastrowid

    count = req.question_count or 10
    if req.mode == "master169":
        count = min(count, 30)
    elif req.mode == "cards":
        count = 8

    cursor.execute("""
    INSERT INTO game_sessions (challenger_id, mode, difficulty, total_questions)
    VALUES (?, ?, ?, ?)
    """, (challenger_id, req.mode, req.difficulty, count))
    session_id = cursor.lastrowid

    all_goals = [dict(g) for g in cursor.execute("SELECT id, code, name, full_name, category_zh, color, icon FROM goals WHERE is_active = 1").fetchall()]
    goals_by_id = {g["id"]: g for g in all_goals}

    questions = []

    if req.mode == "scenario":
        scenarios = [dict(s) for s in cursor.execute("SELECT * FROM scenarios WHERE is_active = 1").fetchall()]
        sample_scenarios = random.sample(scenarios, min(count, len(scenarios)))
        for idx, sc in enumerate(sample_scenarios):
            correct_goal = goals_by_id[sc["goal_id"]]
            other_goals = [g for g in all_goals if g["id"] != correct_goal["id"]]
            distractors = random.sample(other_goals, 3)
            options = [correct_goal] + distractors
            random.shuffle(options)
            questions.append({
                "question_id": idx + 1,
                "type": "scenario",
                "scenario_id": sc["id"],
                "target_id": None,
                "prompt_text": sc["scenario_text"],
                "real_life_example": sc["real_life_example"],
                "code": f"SDG {correct_goal['id']}",
                "correct_goal_id": correct_goal["id"],
                "options": [{"id": o["id"], "code": o["code"], "name": o["name"], "color": o["color"], "icon": o["icon"]} for o in options]
            })

    elif req.mode == "cards":
        targets = [dict(t) for t in cursor.execute("SELECT * FROM targets WHERE is_active = 1").fetchall()]
        selected_targets = random.sample(targets, count)
        cards = []
        for t in selected_targets:
            g = goals_by_id[t["goal_id"]]
            pair_key = f"pair_{t['id']}"
            cards.append({
                "card_id": f"A_{t['id']}",
                "pair_key": pair_key,
                "goal_id": g["id"],
                "card_type": "target",
                "title": f"細項 {t['code']}",
                "text": t["description"][:55] + ("..." if len(t["description"]) > 55 else ""),
                "badge": t["type"],
                "color": g["color"],
                "icon": "📜"
            })
            cards.append({
                "card_id": f"B_{t['id']}",
                "pair_key": pair_key,
                "goal_id": g["id"],
                "card_type": "goal",
                "title": f"{g['code']} {g['name']}",
                "text": g["full_name"],
                "badge": f"{g['category_zh']}領域",
                "color": g["color"],
                "icon": g["icon"]
            })
        random.shuffle(cards)
        questions = {"cards": cards, "total_pairs": count}

    else:
        targets = [dict(t) for t in cursor.execute("SELECT * FROM targets WHERE is_active = 1").fetchall()]
        selected_targets = random.sample(targets, min(count, len(targets)))
        for idx, t in enumerate(selected_targets):
            correct_goal = goals_by_id[t["goal_id"]]
            other_goals = [g for g in all_goals if g["id"] != correct_goal["id"]]
            distractors = random.sample(other_goals, 3)
            options = [correct_goal] + distractors
            random.shuffle(options)
            questions.append({
                "question_id": idx + 1,
                "type": "target",
                "target_id": t["id"],
                "prompt_text": t["description"],
                "code": t["code"],
                "target_type": t["type"],
                "correct_goal_id": correct_goal["id"],
                "options": [{"id": o["id"], "code": o["code"], "name": o["name"], "color": o["color"], "icon": o["icon"]} for o in options]
            })

    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "challenger_id": challenger_id,
        "mode": req.mode,
        "difficulty": req.difficulty,
        "questions": questions
    }

@router.post("/answer")
def check_answer(req: GameAnswerRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    is_correct = (req.selected_goal_id == req.correct_goal_id)

    settings = dict(cursor.execute("SELECT key, value FROM system_settings").fetchall())
    base_points = int(settings.get("points_base", 100))
    combo_bonus = int(settings.get("points_combo_bonus", 25))
    penalty = int(settings.get("points_penalty_wrong", 20))

    score_delta = 0
    new_combo = req.current_combo
    if is_correct:
        new_combo += 1
        score_delta = base_points + (new_combo - 1) * combo_bonus
    else:
        new_combo = 0
        score_delta = -penalty

    cursor.execute("""
    INSERT INTO game_details (session_id, target_id, goal_id, selected_goal_id, is_correct, time_spent_ms)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (req.session_id, req.target_id, req.correct_goal_id, req.selected_goal_id, 1 if is_correct else 0, req.time_spent_ms))

    correct_goal = dict(cursor.execute("SELECT * FROM goals WHERE id = ?", (req.correct_goal_id,)).fetchone())
    target_info = None
    if req.target_id:
        target_row = cursor.execute("SELECT * FROM targets WHERE id = ?", (req.target_id,)).fetchone()
        if target_row:
            target_info = dict(target_row)

    conn.commit()
    conn.close()

    return {
        "is_correct": is_correct,
        "score_delta": score_delta,
        "new_combo": new_combo,
        "correct_goal": {
            "id": correct_goal["id"],
            "code": correct_goal["code"],
            "name": correct_goal["name"],
            "full_name": correct_goal["full_name"],
            "category_zh": correct_goal["category_zh"],
            "color": correct_goal["color"],
            "icon": correct_goal["icon"],
            "slogan": correct_goal["slogan"]
        },
        "target": target_info
    }

@router.post("/finish")
def finish_game(req: GameFinishRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE game_sessions
    SET total_score = ?,
        total_questions = ?,
        correct_count = ?,
        combo_max = ?,
        time_taken_seconds = ?,
        completed_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (req.total_score, req.total_questions, req.correct_count, req.combo_max, req.time_taken_seconds, req.session_id))

    cursor.execute("""
    SELECT COUNT(*) + 1 AS rank FROM game_sessions
    WHERE total_score > ?
    """, (req.total_score,))
    rank = cursor.fetchone()["rank"]

    accuracy = (req.correct_count / req.total_questions * 100) if req.total_questions > 0 else 0
    badge = "永續種子 (Eco Seed)"
    if accuracy >= 90:
        badge = "永續傳教士 (SDGs Champion)"
    elif accuracy >= 70:
        badge = "永續實踐家 (SDGs Practitioner)"
    elif accuracy >= 50:
        badge = "永續探險者 (SDGs Explorer)"

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "rank": rank,
        "accuracy_pct": round(accuracy, 1),
        "badge": badge,
        "total_score": req.total_score,
        "combo_max": req.combo_max,
        "time_taken": req.time_taken_seconds
    }

@router.get("/leaderboard")
def get_leaderboard(mode: Optional[str] = None, limit: int = 20):
    conn = get_db_connection()
    sql = """
    SELECT gs.id as session_id, gs.mode, gs.total_score, gs.total_questions,
           gs.correct_count, gs.combo_max, gs.time_taken_seconds, gs.completed_at,
           c.nickname, c.organization, c.avatar
    FROM game_sessions gs
    JOIN challengers c ON gs.challenger_id = c.id
    WHERE gs.total_score > 0
    """
    params = []
    if mode and mode != "all":
        sql += " AND gs.mode = ?"
        params.append(mode)
    sql += " ORDER BY gs.total_score DESC, gs.time_taken_seconds ASC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    result = []
    for idx, r in enumerate(rows):
        d = dict(r)
        d["rank"] = idx + 1
        d["accuracy"] = round((d["correct_count"] / d["total_questions"] * 100), 1) if d["total_questions"] > 0 else 0
        result.append(d)
    return result
