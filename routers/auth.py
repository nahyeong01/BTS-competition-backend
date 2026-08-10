from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from auth import get_current_user

router = APIRouter()

class ProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    nation_id: Optional[str] = None
    avatar_id: Optional[str] = None

@router.get("/api/auth/me")
def get_my_profile(current_user = Depends(get_current_user)):
    user_id = current_user.id
    profile = supabase.table("profiles")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다")
    # profiles 행에 auth 이메일도 같이 붙여서 반환한다 - 화면에서 별도로 auth 유저를
    # 다시 조회하지 않아도 되게(현재는 이메일을 화면에 안 쓰지만, 향후 대비).
    result = profile.data[0]
    result["email"] = current_user.email
    return result

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
    if not response.data:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다")
    return response.data[0]

@router.post("/api/auth/logout")
def logout(current_user = Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return {"status": "ok", "message": "로그아웃 완료"}