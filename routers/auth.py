from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import supabase
from auth import get_current_user

router = APIRouter()

class ProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    nation_id: Optional[str] = None

@router.get("/api/auth/me")
def get_my_profile(current_user = Depends(get_current_user)):
    return current_user

@router.post("/api/auth/session")
def create_or_get_session(current_user = Depends(get_current_user)):
    user_id = current_user.id
    existing = supabase.table("profiles")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    if not existing.data:
        nickname = current_user.user_metadata.get("full_name", "사용자")
        supabase.table("profiles").insert({
            "user_id": user_id,
            "nickname": nickname,
            "nation_id": "KR",
        }).execute()
        return {"status": "created", "message": "프로필 생성됨"}
    return {"status": "ok", "message": "기존 프로필 있음"}

@router.patch("/api/auth/me")
def update_my_profile(
    body: ProfileUpdate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id
    update_data = body.model_dump(exclude_none=True)
    response = supabase.table("profiles")\
        .update(update_data)\
        .eq("user_id", user_id)\
        .execute()
    return response.data

@router.post("/api/auth/logout")
def logout(current_user = Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return {"status": "ok", "message": "로그아웃 완료"}