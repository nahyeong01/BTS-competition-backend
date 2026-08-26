from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from auth import get_current_user, get_current_user_optional

router = APIRouter()

class CourseCreate(BaseModel):
    course_name: str
    trip_start: str
    trip_end: str
    proc_id: str

class CourseUpdate(BaseModel):
    course_name: Optional[str] = None
    trip_start: Optional[str] = None
    trip_end: Optional[str] = None
    status: Optional[str] = None

class CourseDetailItem(BaseModel):
    tour_id: int
    day: int
    visit_order: int

class CourseDetailsCreate(BaseModel):
    details: list[CourseDetailItem]

@router.post("/api/courses")
def create_course(body: CourseCreate, current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course").insert({
        "user_id": user_id,
        "proc_id": body.proc_id,
        "course_name": body.course_name,
        "trip_start": body.trip_start,
        "trip_end": body.trip_end,
        "status": "DRAFT",
    }).execute()
    return response.data[0]

@router.get("/api/courses")
def get_courses(current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute()
    return response.data

@router.get("/api/courses/{course_id}")
def get_course(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    course = supabase.table("course")\
        .select("*")\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    details = supabase.table("course_detail")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("day")\
        .order("visit_order")\
        .execute()
    result = course.data[0]
    result["details"] = details.data
    return result

@router.patch("/api/courses/{course_id}")
def update_course(
    course_id: int,
    body: CourseUpdate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id
    update_data = body.model_dump(exclude_none=True)
    response = supabase.table("course")\
        .update(update_data)\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    return response.data[0]

@router.delete("/api/courses/{course_id}")
def delete_course(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id

    # 소유자 확인을 먼저 한다 - 아래 참조 정리(다른 유저 코스의 source/root NULL 처리,
    # course_report 삭제)는 course_id만으로 동작하므로, 소유권 확인 없이 먼저 실행하면
    # 남의 코스에 대해서도 부수효과가 발생한다(실제 course 삭제는 .eq("user_id", ...)로
    # 막히지만, 그 전에 이미 참조가 끊기고 신고 기록이 지워져버린다).
    course = supabase.table("course").select("course_id").eq("course_id", course_id).eq("user_id", user_id).execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")

    # 이 코스를 다른 유저가 복사해갔다면(source_course_id/root_course_id로 이 코스를
    # 참조) DB가 fk_course_source_course/fk_course_root_course의 ON DELETE SET NULL로
    # course 삭제 시 그 참조를 자동으로 NULL 처리한다(2026-08-26 스키마 변경, 민지 확인).
    # 아래 두 update는 그 DB 안전장치의 애플리케이션 레벨 이중 방어다 - 없어도 DB가
    # 처리하지만, 남겨둬도 이미 NULL인 값을 다시 NULL로 쓰는 것뿐이라 해롭지 않고
    # 코드만 보고도 이 삭제가 참조 정리를 고려했다는 의도가 드러난다.
    supabase.table("course").update({"source_course_id": None}).eq("source_course_id", course_id).execute()
    supabase.table("course").update({"root_course_id": None}).eq("root_course_id", course_id).execute()
    # course_report는 SET NULL 대상이 아니다 - 신고 기록은 "유지"가 아니라 "삭제"가
    # 정책이므로(course_id가 사라지는 코스에 대한 신고는 의미가 없음) 이건 DB 제약과
    # 무관하게 계속 코드에서 직접 지워야 한다. course_report도 이 코스를 course_id로
    # 참조하므로(fk_course_report_course, ON DELETE NO ACTION - 변경 안 함), 신고 기록이
    # 있으면 어차피 course 삭제가 막힌다.
    supabase.table("course_report").delete().eq("course_id", course_id).execute()

    supabase.table("course")\
        .delete()\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "ok", "message": "코스 삭제됨"}

@router.post("/api/courses/{course_id}/details")
def add_course_details(
    course_id: int,
    body: CourseDetailsCreate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id
    course = supabase.table("course")\
        .select("course_id")\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    supabase.table("course_detail")\
        .delete()\
        .eq("course_id", course_id)\
        .execute()
    rows = [
        {
            "course_id": course_id,
            "tour_id": d.tour_id,
            "day": d.day,
            "visit_order": d.visit_order,
        }
        for d in body.details
    ]
    response = supabase.table("course_detail").insert(rows).execute()
    return response.data

    # ==================== 공개 코스 ====================
@router.get("/api/shared-courses")
def get_shared_courses():
    # 데이터 최소화: trip_start/trip_end는 프론트가 목록 카드에서 쓰지 않아 select
    # 단계에서 아예 제외한다(2026-08-26 백엔드 검토 반영). user_id는 아래 nickname
    # 매칭에 backend 내부적으로만 필요하고, 최종 응답에는 raw user_id 대신 nickname만
    # 내려준다 - copy 엔드포인트(POST /api/shared-courses/{id}/copy)는 이 응답을 쓰지
    # 않고 DB를 직접 재조회하므로 이 변경과 무관하다.
    response = supabase.table("course")\
        .select("course_id, course_name, user_id, source_course_id, root_course_id, published_at, created_at")\
        .eq("visibility", "public")\
        .order("published_at", desc=True)\
        .execute()
    courses = response.data
    if not courses:
        return []

    # user_id마다 별도 쿼리를 반복하지 않도록, 이 목록에 등장하는 user_id를 한 번에
    # 모아서 profiles를 한 번만 조회한 뒤 파이썬에서 매칭한다.
    user_ids = list({c["user_id"] for c in courses if c.get("user_id")})
    nickname_by_user_id = {}
    if user_ids:
        profiles_res = supabase.table("profiles")\
            .select("user_id, nickname")\
            .in_("user_id", user_ids)\
            .execute()
        nickname_by_user_id = {p["user_id"]: p["nickname"] for p in profiles_res.data}

    return [
        {
            "course_id": c["course_id"],
            "course_name": c.get("course_name"),
            "nickname": nickname_by_user_id.get(c["user_id"]),
            "source_course_id": c.get("source_course_id"),
            "root_course_id": c.get("root_course_id"),
            "published_at": c.get("published_at"),
            "created_at": c.get("created_at"),
        }
        for c in courses
    ]

@router.get("/api/shared-courses/{course_id}")
def get_shared_course_detail(course_id: int, current_user = Depends(get_current_user_optional)):
    """공개된(visibility=public) 코스라면, 작성자 본인이 아니어도 상세(Day별 관광지
    목록 + 작성자 닉네임)를 조회할 수 있다. get_course()와 달리 user_id로 필터링하지
    않는다 - "다른 사람이 만든 추천코스"를 보는 화면이 이 엔드포인트를 쓴다.

    데이터 최소화: 예전에는 .select("*")로 proc_id/trip_start/trip_end/raw user_id/
    visibility/status/updated_at까지 응답에 그대로 실려 나갔다(프론트는 이 필드들을
    쓰지 않음이 확인됨, 2026-08-26 백엔드 검토). 필요한 컬럼만 select하고, 최종
    응답도 명시적으로 필드를 골라 구성한다 - copy 엔드포인트는 이 응답 구조를 가져다
    쓰지 않고 DB를 직접 재조회하므로 이 변경과 무관하다.

    is_owner: raw user_id를 응답에서 제거한 뒤(위 데이터 최소화), 프론트의 "내가 만든
    공유 코스인지" 판정(신고 버튼 숨김, 찜하기/코스 저장 버튼 숨김 등)이 깨지는 회귀가
    발견되어(2026-08-26, 민지 확인) 대신 이 boolean 하나만 내려준다. 비로그인 조회도
    허용해야 하므로 get_current_user_optional을 쓴다 - Authorization 헤더가 없으면
    current_user가 None이라 is_owner는 그냥 False, 헤더가 있는데 형식 오류/만료/무효
    토큰이면 get_current_user_optional이 자체적으로 401을 던진다(이 함수까지 도달하지
    않음)."""
    course = supabase.table("course")\
        .select("course_id, course_name, user_id, source_course_id, root_course_id")\
        .eq("course_id", course_id)\
        .eq("visibility", "public")\
        .execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="공개된 코스를 찾을 수 없습니다")

    course_row = course.data[0]
    is_owner = bool(current_user and current_user.id == course_row["user_id"])

    details = supabase.table("course_detail")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("day")\
        .order("visit_order")\
        .execute()

    profile = supabase.table("profiles")\
        .select("nickname")\
        .eq("user_id", course_row["user_id"])\
        .execute()
    nickname = profile.data[0]["nickname"] if profile.data else None

    return {
        "course_id": course_row["course_id"],
        "course_name": course_row.get("course_name"),
        "nickname": nickname,
        "details": details.data,
        "source_course_id": course_row.get("source_course_id"),
        "root_course_id": course_row.get("root_course_id"),
        "is_owner": is_owner,
    }

@router.post("/api/shared-courses/{course_id}/copy")
def copy_shared_course(course_id: int, current_user = Depends(get_current_user)):
    """공개 코스를 로그인한 사용자의 "내 코스"로 복사한다. 원작성자의 개인정보
    (trip_start/trip_end/proc_id)는 가져오지 않고, 관광지 목록(day/visit_order)만
    복사한다 - course_name/trip_start/trip_end/proc_id는 모두 비워서(NULL) 저장하고,
    사용자가 나중에 CourseSetup 등에서 직접 채워 넣게 한다."""
    user_id = current_user.id

    source_course = supabase.table("course")\
        .select("*")\
        .eq("course_id", course_id)\
        .eq("visibility", "public")\
        .execute()
    if not source_course.data:
        raise HTTPException(status_code=404, detail="공개된 코스를 찾을 수 없습니다")

    source = source_course.data[0]

    # root_course_id: 복사가 여러 번 이어져도(복사한 걸 또 복사) 항상 최초 원본을
    # 가리키도록, source에 이미 root_course_id가 있으면 그걸 그대로 물려받고
    # 없으면(source 자신이 원본) source의 course_id를 root으로 삼는다.
    root_course_id = source.get("root_course_id") or source["course_id"]

    new_course = supabase.table("course").insert({
        "user_id": user_id,
        "course_name": None,
        "trip_start": None,
        "trip_end": None,
        "proc_id": None,
        "status": "DRAFT",
        "visibility": "private",
        "source_course_id": course_id,
        "root_course_id": root_course_id,
    }).execute()

    new_course_id = new_course.data[0]["course_id"]

    source_details = supabase.table("course_detail")\
        .select("tour_id, day, visit_order")\
        .eq("course_id", course_id)\
        .execute()

    if source_details.data:
        rows = [
            {
                "course_id": new_course_id,
                "tour_id": d["tour_id"],
                "day": d["day"],
                "visit_order": d["visit_order"],
            }
            for d in source_details.data
        ]
        supabase.table("course_detail").insert(rows).execute()

    return new_course.data[0]

@router.patch("/api/courses/{course_id}/publish")
def publish_course(course_id: int, current_user = Depends(get_current_user)):
    from datetime import datetime, timezone
    user_id = current_user.id
    response = supabase.table("course")\
        .update({
            "visibility": "public",
            "published_at": datetime.now(timezone.utc).isoformat()
        })\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    return {"status": "ok", "message": "코스가 공개됐습니다"}

@router.patch("/api/courses/{course_id}/unpublish")
def unpublish_course(course_id: int, current_user = Depends(get_current_user)):
    user_id = current_user.id
    response = supabase.table("course")\
        .update({
            "visibility": "private",
            "published_at": None
        })\
        .eq("course_id", course_id)\
        .eq("user_id", user_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="코스를 찾을 수 없습니다")
    return {"status": "ok", "message": "코스가 비공개됐습니다"}