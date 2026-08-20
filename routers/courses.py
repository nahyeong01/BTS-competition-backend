from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase
from auth import get_current_user

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
    response = supabase.table("course")\
        .select("course_id, course_name, trip_start, trip_end, user_id, source_course_id, root_course_id, published_at, created_at")\
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

    for c in courses:
        c["nickname"] = nickname_by_user_id.get(c["user_id"])
    return courses

@router.get("/api/shared-courses/{course_id}")
def get_shared_course_detail(course_id: int):
    """공개된(visibility=public) 코스라면, 작성자 본인이 아니어도 상세(Day별 관광지
    목록 + 작성자 닉네임)를 조회할 수 있다. get_course()와 달리 user_id로 필터링하지
    않는다 - "다른 사람이 만든 추천코스"를 보는 화면이 이 엔드포인트를 쓴다."""
    course = supabase.table("course")\
        .select("*")\
        .eq("course_id", course_id)\
        .eq("visibility", "public")\
        .execute()
    if not course.data:
        raise HTTPException(status_code=404, detail="공개된 코스를 찾을 수 없습니다")

    result = course.data[0]

    details = supabase.table("course_detail")\
        .select("*")\
        .eq("course_id", course_id)\
        .order("day")\
        .order("visit_order")\
        .execute()
    result["details"] = details.data

    profile = supabase.table("profiles")\
        .select("nickname")\
        .eq("user_id", result["user_id"])\
        .execute()
    result["nickname"] = profile.data[0]["nickname"] if profile.data else None

    return result

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