import csv
import io
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from app.database import get_db_connection
from app.models import AdminLoginRequest, TargetUpdateRequest, SettingUpdateRequest
from app.auth import verify_password, create_admin_session, verify_admin_token

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/login")
def admin_login(req: AdminLoginRequest):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (req.username.strip(),)).fetchone()
    conn.close()

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤 (Invalid username or password)")

    token = create_admin_session(user["username"], user["role"])
    return {
        "status": "success",
        "token": token,
        "username": user["username"],
        "role": user["role"]
    }

@router.get("/stats")
def get_admin_stats(session=Depends(verify_admin_token)):
    conn = get_db_connection()
    total_challengers = conn.execute("SELECT COUNT(*) FROM challengers").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM game_sessions WHERE total_score > 0").fetchone()[0]
    avg_score = conn.execute("SELECT COALESCE(AVG(total_score), 0) FROM game_sessions WHERE total_score > 0").fetchone()[0]
    
    accuracy_row = conn.execute("""
    SELECT COALESCE(SUM(correct_count) * 100.0 / NULLIF(SUM(total_questions), 0), 0) 
    FROM game_sessions WHERE total_questions > 0
    """).fetchone()[0]

    mode_map = {
        "scenario": "生活情境入門",
        "standard": "標準細項配對",
        "cards": "翻牌記憶連連看",
        "master169": "169細項極限闖關"
    }
    mode_counts = []
    for r in conn.execute("""
        SELECT mode, COUNT(*) as count, AVG(total_score) as avg_score
        FROM game_sessions WHERE total_score > 0 GROUP BY mode
    """).fetchall():
        d = dict(r)
        d["mode_zh"] = mode_map.get(d["mode"], d["mode"])
        mode_counts.append(d)

    most_mistaken = [dict(r) for r in conn.execute("""
    SELECT t.code, t.description, g.name as goal_name, g.color,
           COUNT(*) as wrong_count
    FROM game_details gd
    JOIN targets t ON gd.target_id = t.id
    JOIN goals g ON t.goal_id = g.id
    WHERE gd.is_correct = 0
    GROUP BY t.id
    ORDER BY wrong_count DESC
    LIMIT 5
    """).fetchall()]

    goal_stats = [dict(r) for r in conn.execute("""
    SELECT g.id, g.code, g.name, g.color,
           COUNT(gd.id) as total_attempts,
           SUM(CASE WHEN gd.is_correct = 1 THEN 1 ELSE 0 END) as correct_attempts
    FROM goals g
    LEFT JOIN game_details gd ON g.id = gd.goal_id
    GROUP BY g.id
    ORDER BY g.id ASC
    """).fetchall()]

    conn.close()

    return {
        "summary": {
            "total_challengers": total_challengers,
            "total_sessions": total_sessions,
            "avg_score": round(avg_score, 1),
            "avg_accuracy_pct": round(accuracy_row, 1)
        },
        "mode_breakdown": mode_counts,
        "most_mistaken_targets": most_mistaken,
        "goal_stats": goal_stats
    }

@router.get("/records")
def get_game_records(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    mode: Optional[str] = None,
    session=Depends(verify_admin_token)
):
    conn = get_db_connection()
    offset = (page - 1) * page_size
    
    where_clauses = ["1=1"]
    params = []

    if search:
        where_clauses.append("(c.nickname LIKE ? OR c.organization LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if mode and mode != "all":
        where_clauses.append("gs.mode = ?")
        params.append(mode)

    where_sql = " AND ".join(where_clauses)
    count_sql = f"SELECT COUNT(*) FROM game_sessions gs JOIN challengers c ON gs.challenger_id = c.id WHERE {where_sql}"
    total_count = conn.execute(count_sql, params).fetchone()[0]

    sql = f"""
    SELECT gs.id, gs.mode, gs.difficulty, gs.total_score, gs.total_questions,
           gs.correct_count, gs.combo_max, gs.time_taken_seconds, gs.completed_at,
           c.nickname, c.organization, c.avatar
    FROM game_sessions gs
    JOIN challengers c ON gs.challenger_id = c.id
    WHERE {where_sql}
    ORDER BY gs.completed_at DESC
    LIMIT ? OFFSET ?
    """
    params.extend([page_size, offset])
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": rows
    }

@router.delete("/records/{session_id}")
def delete_game_record(session_id: int, session=Depends(verify_admin_token)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM game_sessions WHERE id = ?", (session_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="找不到指定之遊戲紀錄 (Record not found)")
    return {"status": "success", "message": f"紀錄 #{session_id} 已成功刪除"}

@router.get("/targets")
def get_all_targets_admin(
    goal_id: Optional[int] = None,
    search: Optional[str] = None,
    session=Depends(verify_admin_token)
):
    conn = get_db_connection()
    sql = """
    SELECT t.*, g.name as goal_name, g.color as goal_color, g.category_zh as category
    FROM targets t
    JOIN goals g ON t.goal_id = g.id
    WHERE 1=1
    """
    params = []
    if goal_id:
        sql += " AND t.goal_id = ?"
        params.append(goal_id)
    if search:
        sql += " AND (t.description LIKE ? OR t.code LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY t.goal_id ASC, t.id ASC"

    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows

@router.put("/targets/{target_id}")
def update_target(target_id: int, req: TargetUpdateRequest, session=Depends(verify_admin_token)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE targets
    SET description = ?, is_active = ?
    WHERE id = ?
    """, (req.description.strip(), 1 if req.is_active else 0, target_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="找不到指定細項目標 (Target not found)")
    return {"status": "success", "message": f"細項目標 #{target_id} 更新完成"}

@router.get("/settings")
def get_settings(session=Depends(verify_admin_token)):
    conn = get_db_connection()
    rows = [dict(r) for r in conn.execute("SELECT * FROM system_settings").fetchall()]
    conn.close()
    return rows

@router.put("/settings/{key}")
def update_setting(key: str, req: SettingUpdateRequest, session=Depends(verify_admin_token)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE system_settings
    SET value = ?, updated_at = CURRENT_TIMESTAMP
    WHERE key = ?
    """, (req.value.strip(), key))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="找不到指定設定項 (Setting key not found)")
    return {"status": "success", "message": f"設定 [{key}] 更新為 {req.value}"}

@router.get("/export/csv")
def export_csv(mode: Optional[str] = None, session=Depends(verify_admin_token)):
    conn = get_db_connection()
    where_sql = "1=1"
    params = []
    if mode and mode != "all":
        where_sql += " AND gs.mode = ?"
        params.append(mode)

    sql = f"""
    SELECT gs.id, c.nickname, c.organization, gs.mode, gs.difficulty,
           gs.total_score, gs.total_questions, gs.correct_count,
           ROUND(gs.correct_count * 100.0 / NULLIF(gs.total_questions, 0), 1) as accuracy_pct,
           gs.combo_max, gs.time_taken_seconds, gs.completed_at
    FROM game_sessions gs
    JOIN challengers c ON gs.challenger_id = c.id
    WHERE {where_sql}
    ORDER BY gs.completed_at DESC
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        "對局ID", "挑戰者暱稱", "所屬組織", "遊戲模式", "難度",
        "總分", "總題數", "答對數", "正確率(%)", "最高連擊",
        "耗時(秒)", "完成時間"
    ])
    mode_map = {
        "scenario": "生活情境入門",
        "standard": "標準細項配對",
        "cards": "翻牌記憶連連看",
        "master169": "169細項極限闖關"
    }
    for r in rows:
        row_list = list(r)
        if len(row_list) > 3 and row_list[3] in mode_map:
            row_list[3] = mode_map[row_list[3]]
        writer.writerow(row_list)

    output.seek(0)
    import urllib.parse
    mode_label = mode_map.get(mode, "全部模式") if mode and mode != "all" else "全部模式"
    filename_zh = f"sdgs_{mode_label}_挑戰紀錄.csv"
    encoded_filename = urllib.parse.quote(filename_zh)

    response = Response(content=output.getvalue(), media_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}; filename=\"{encoded_filename}\""
    return response
