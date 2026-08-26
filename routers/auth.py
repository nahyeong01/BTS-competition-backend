import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase, supabase_admin
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
        return {"status": "created", "message": "프로필 생성됨", "age_verified": False}
    # 신규 가입 시점에 profiles 행은 바로 생기지만, 온보딩(AgeVerification/TermsAgreement)을
    # 끝까지 마치지 않고 이탈했을 수 있다 - 그 경우 age_verified가 여전히 false로 남아있다.
    # 프론트가 status만으로 판정하면 이런 유저는 다음 로그인부터 "기존 유저"로 취급돼
    # 온보딩을 영원히 다시 안 보게 되므로, 기존 유저 응답에도 age_verified를 함께 내려줘
    # 프론트가 status와 별개로 온보딩 완료 여부를 판단할 수 있게 한다.
    return {
        "status": "ok",
        "message": "기존 프로필 있음",
        "age_verified": existing.data[0].get("age_verified", False),
    }

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

@router.patch("/api/auth/onboarding")
def complete_onboarding(current_user = Depends(get_current_user)):
    supabase.table("profiles").update({
        "age_verified": True,
        "terms_agreed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", current_user.id).execute()
    return {"status": "ok"}

@router.delete("/api/auth/me")
def delete_my_account(current_user = Depends(get_current_user)):
    user_id = current_user.id

    # profiles를 참조하는 FK가 하나도 없어서(user_id 컬럼만 있고 실제 FK 제약은 없음)
    # CASCADE에 기댈 수 없다 - 이 유저 소유 데이터를 테이블별로 직접 지운다.
    # course만 예외적으로 순서가 중요하다:
    #   - course -> course_detail, course_wishlist는 CASCADE라 course 삭제 시 자동 정리됨
    #   - course -> course_report는 NO ACTION이라, 이 유저 코스가 신고당한 적 있으면
    #     course_report 행을 먼저 지워야 course 삭제가 안 막힌다
    #   - course.source_course_id/root_course_id(자기참조)도 NO ACTION이라, 다른 유저가
    #     이 유저의 코스를 원본으로 저장/재공유했다면 그 참조를 먼저 끊어야(NULL 처리)
    #     course 삭제가 안 막힌다. 참조하는 다른 유저의 코스 자체를 지우면 안 되므로
    #     삭제가 아니라 NULL로 끊는다.
    own_courses = supabase.table("course").select("course_id").eq("user_id", user_id).execute()
    own_course_ids = [row["course_id"] for row in own_courses.data]

    if own_course_ids:
        supabase.table("course_report").delete().in_("course_id", own_course_ids).execute()
        supabase.table("course").update({"source_course_id": None}).in_("source_course_id", own_course_ids).execute()
        supabase.table("course").update({"root_course_id": None}).in_("root_course_id", own_course_ids).execute()

    # 나머지 소유 데이터 삭제 (하위 참조 없어 순서 상관없음)
    supabase.table("accommodation_wishlist").delete().eq("user_id", user_id).execute()
    supabase.table("hospital_wishlist").delete().eq("user_id", user_id).execute()
    supabase.table("tourist_wishlist").delete().eq("user_id", user_id).execute()
    supabase.table("course_wishlist").delete().eq("user_id", user_id).execute()

    # course 삭제 - course_detail/course_wishlist는 CASCADE라 자동 정리됨
    supabase.table("course").delete().eq("user_id", user_id).execute()

    # profiles 삭제
    supabase.table("profiles").delete().eq("user_id", user_id).execute()

    # 이 유저가 "신고자"로서 남을 신고한 기록(course_report.reporter_user_id)은
    # 완전히 지우지 않고 신고자 식별자만 익명화한다 - 신고 자체(어떤 코스가 어떤
    # 사유로 신고됐는지)는 운영 기록으로 계속 남기되, 탈퇴한 유저의 활동 흔적은
    # 남기지 않는다. reporter_user_id는 원래 NOT NULL이었으나 이 처리를 위해
    # nullable로 스키마 변경했다(2026-08-26). 위 own_course_ids 처리(내 코스가
    # 신고당한 기록 삭제)와는 반대 방향 - 그건 course_id 쪽 FK 때문에 반드시
    # 지워야만 했던 것이고, 이건 reporter_user_id 쪽 FK 때문에 auth.users 삭제
    # 전에 반드시 정리해야 하는 것이다. auth.users 삭제보다 반드시 먼저 실행해야
    # 그 삭제가 FK 위반으로 막히지 않는다.
    supabase.table("course_report").update({"reporter_user_id": None}).eq("reporter_user_id", user_id).execute()

    # Supabase Auth 계정 자체 삭제 - service_role(Secret key) 클라이언트로만 가능
    try:
        supabase_admin.auth.admin.delete_user(user_id)
    except Exception as e:
        print(f"Auth 계정 삭제 실패 (user_id={user_id}): {e}")

    return {"status": "ok", "message": "탈퇴 완료"}