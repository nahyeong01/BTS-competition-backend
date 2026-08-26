from fastapi import Header, HTTPException
from database import supabase

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="잘못된 토큰 형식")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")


async def get_current_user_optional(authorization: str = Header(None)):
    """Authorization 헤더가 아예 없으면 None을 반환해 비로그인 공개 조회를 그대로
    허용한다(예: GET /api/shared-courses/{course_id}의 is_owner 판정용 - 로그인
    안 한 사용자도 공유 코스는 볼 수 있어야 하므로). 헤더가 있는데 형식이 틀리거나
    토큰이 유효하지 않으면(만료 포함) get_current_user와 완전히 동일하게 401을
    던진다 - "아예 로그인 안 함"과 "로그인은 시도했는데 토큰이 잘못됨"을 구분해서,
    후자를 마치 비로그인인 것처럼 조용히 넘기지 않는다. 검증 로직 자체는
    get_current_user를 그대로 재사용해 중복을 두지 않는다.
    """
    if authorization is None:
        return None
    return await get_current_user(authorization)