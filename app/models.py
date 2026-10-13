from typing import Optional, List
from pydantic import BaseModel, Field

class ChallengerCreate(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    organization: Optional[str] = Field("一般挑戰者", max_length=50)
    avatar: Optional[str] = Field("🌱", max_length=10)

class GameStartRequest(BaseModel):
    nickname: str
    organization: Optional[str] = "一般挑戰者"
    avatar: Optional[str] = "🌱"
    mode: str = "standard"
    difficulty: Optional[str] = "medium"
    question_count: Optional[int] = 10

class QuestionItem(BaseModel):
    question_id: int
    type: str
    prompt_text: str
    code: Optional[str] = None
    target_type: Optional[str] = None
    options: List[dict]
    hint: Optional[str] = None

class GameAnswerRequest(BaseModel):
    session_id: int
    question_index: int
    target_id: Optional[int] = None
    scenario_id: Optional[int] = None
    selected_goal_id: int
    correct_goal_id: int
    time_spent_ms: int = 0
    current_combo: int = 0

class GameFinishRequest(BaseModel):
    session_id: int
    total_score: int
    total_questions: int
    correct_count: int
    combo_max: int
    time_taken_seconds: float
    details: Optional[List[dict]] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class TargetUpdateRequest(BaseModel):
    description: str
    type: Optional[str] = None
    is_active: Optional[bool] = True

class SettingUpdateRequest(BaseModel):
    value: str
