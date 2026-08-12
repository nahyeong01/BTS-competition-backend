from fastapi import APIRouter, Depends
from database import supabase
from auth import get_current_user

router = APIRouter()

# 이미 찜돼 있는 상태에서 다시 "찜 추가" 요청이 오면(프론트 로컬 상태와 서버 상태가 일시적
# 으로 어긋났을 때, 같은 요청이 중복 전송됐을 때 등) INSERT가 unique 제약 위반으로 실패해서
# 500을 내는 문제가 있었다. 이 경우는 서버 에러가 아니라 "이미 찜된 상태"일 뿐이므로,
# 예외 메시지에 duplicate key/unique violation 신호(postgres 에러 코드 23505)가 있으면
# 실패로 취급하지 않고 조용히 성공 처리한다. 그 외 예외는 원래대로 그대로 올려서 500이
# 나게 둔다(진짜 서버 에러를 숨기면 안 되니까).
def _is_duplicate_key_error(error) -> bool:
    message = str(error)
    return "23505" in message or "duplicate key" in message.lower()


def _insert_wishlist_idempotent(table: str, row: dict):
    try:
        supabase.table(table).insert(row).execute()
    except Exception as error:
        if not _is_duplicate_key_error(error):
            raise

# ==================== 병원 ====================
@router.post("/api/wishlist/hospitals/{hosp_id}")
def add_hospital_wishlist(hosp_id: str, current_user = Depends(get_current_user)):
    user_id = current_user.id
    _insert_wishlist_idempotent("hospital_wishlist", {
        "hosp_id": hosp_id,
        "user_id": user_id,
    })
    return {"status": "ok", "message": "병원 찜 추가됨"}

@router.delete("/api/wishlist/hospitals/{hosp_id}")
def delete_hospital_wishlist(hosp_id: str, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("hospital_wishlist")\
        .delete()\
        .eq("hosp_id", hosp_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "병원 찜 해제됨"}

@router.get("/api/wishlist/hospitals")
def get_hospital_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("hospital_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

# ==================== 숙소 ====================
@router.post("/api/wishlist/accommodations/{acc_id}")
def add_accommodation_wishlist(acc_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    _insert_wishlist_idempotent("accommodation_wishlist", {
        "acc_id": acc_id,
        "user_id": user_id,
    })
    return {"status": "ok", "message": "숙소 찜 추가됨"}

@router.delete("/api/wishlist/accommodations/{acc_id}")
def delete_accommodation_wishlist(acc_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("accommodation_wishlist")\
        .delete()\
        .eq("acc_id", acc_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "숙소 찜 해제됨"}

@router.get("/api/wishlist/accommodations")
def get_accommodation_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("accommodation_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

# ==================== 관광지 ====================
@router.post("/api/wishlist/tourist-spots/{tour_id}")
def add_tourist_wishlist(tour_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    _insert_wishlist_idempotent("tourist_wishlist", {
        "tour_id": tour_id,
        "user_id": user_id,
    })
    return {"status": "ok", "message": "관광지 찜 추가됨"}

@router.delete("/api/wishlist/tourist-spots/{tour_id}")
def delete_tourist_wishlist(tour_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("tourist_wishlist")\
        .delete()\
        .eq("tour_id", tour_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "관광지 찜 해제됨"}

@router.get("/api/wishlist/tourist-spots")
def get_tourist_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("tourist_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

# ==================== 코스 ====================
@router.post("/api/wishlist/courses/{course_id}")
def add_course_wishlist(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    _insert_wishlist_idempotent("course_wishlist", {
        "course_id": course_id,
        "user_id": user_id,
    })
    return {"status": "ok", "message": "코스 찜 추가됨"}

@router.delete("/api/wishlist/courses/{course_id}")
def delete_course_wishlist(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    supabase.table("course_wishlist")\
        .delete()\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "코스 찜 해제됨"}

@router.get("/api/wishlist/courses")
def get_course_wishlist(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course_wishlist")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data