import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from auth import get_current_user

router = APIRouter()

# 프론트 utils/publicAlias.js의 ALIAS_CODE_CHARS/ALIAS_CODE_LENGTH/ALIAS_TOKEN_PREFIX와
# 반드시 동일하게 유지해야 한다 - 여기서 만든 "alias:XXXX" 토큰을 프론트가 그대로
# formatAuthorDisplay()로 감싸서 "여행자 XXXX" 형태로 보여주기 때문. 0/O, 1/I처럼
# 혼동되는 문자는 제외한다.
ALIAS_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ALIAS_CODE_LENGTH = 4
ALIAS_TOKEN_PREFIX = "alias:"
ALIAS_GENERATION_MAX_ATTEMPTS = 5


def _generate_alias_code() -> str:
    return "".join(random.choice(ALIAS_CODE_CHARS) for _ in range(ALIAS_CODE_LENGTH))


def generate_unique_alias_nickname() -> str:
    """profiles.nickname에 저장할 "alias:XXXX" 토큰을 생성한다. 이메일/구글 실명/기존
    nickname 등 개인정보를 재료로 쓰지 않고 무작위로만 만든다(publicAlias.js와 동일 원칙).
    충돌 가능성은 4자리(33^4 ≈ 130만 가지)라 낮지만, 여러 번 시도해도 계속 겹치면 마지막
    후보를 그대로 쓴다(가입 자체가 막히는 것보다 훨씬 낫다)."""
    for _ in range(ALIAS_GENERATION_MAX_ATTEMPTS):
        candidate = f"{ALIAS_TOKEN_PREFIX}{_generate_alias_code()}"
        existing = supabase.table("profiles")\
            .select("user_id")\
            .eq("nickname", candidate)\
            .execute()
        if not existing.data:
            return candidate
    return candidate

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
        # 구글 user_metadata의 full_name(실명)은 절대 저장하지 않는다 - 신규 가입 시
        # 서버가 직접 "alias:XXXX" 익명 토큰을 생성해 영구 저장한다. 프론트는 이 값을
        # 그대로 받아 formatAuthorDisplay()로 "여행자 XXXX" 형태로만 화면에 보여준다.
        nickname = generate_unique_alias_nickname()
        supabase.table("profiles").insert({
            "user_id": user_id,
            "nickname": nickname,
            "nation_id": "KOR",
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