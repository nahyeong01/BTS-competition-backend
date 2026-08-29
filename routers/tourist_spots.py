import re
from collections import Counter
from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter()

# 한국관광공사(TourAPI) 원본 overview 텍스트에 <strong>, <br> 같은 HTML 태그가 섞여
# 있는 경우가 있다(2026-08-29 확인, 북촌한옥마을 등). 프론트(TouristDetailScreen.js)는
# 이 값을 그대로 <Text>에 렌더링하고 있어 태그 문자가 화면에 그대로 노출된다. BTS는
# 굵게 표시 같은 HTML 스타일을 살릴 필요가 없으므로, 응답을 내려주기 전에 태그만
# 제거해 일반 텍스트로 정제한다 - 프론트 코드/AAB를 건드리지 않고 백엔드 응답만
# 정제하면 기존 배포본도 재배포 없이 정제된 값을 받는다.
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _strip_html_tags(text):
    if not isinstance(text, str) or not text:
        return text
    return _HTML_TAG_PATTERN.sub("", text)


def _sanitize_spot(spot):
    """관광지 원본 행에 overview 필드가 있으면 HTML 태그를 제거한다. select 컬럼에
    애초에 overview가 없는 응답(예: get_popular_tourist_spots)에는 영향 없다."""
    if "overview" in spot:
        spot["overview"] = _strip_html_tags(spot["overview"])
    return spot


@router.get("/api/tourist-spots")
def get_tourist_spots():
    response = supabase.table("tourist").select("*").execute()
    return [_sanitize_spot(spot) for spot in response.data]

# recommendation_cache 테이블(score_a, rank_a)은 데이터가 없어서 당분간 미사용 상태로
# 남겨둔다. 대신 tourist_wishlist를 실시간으로 집계해서 순위를 매긴다 - 관광지가 782개
# 규모라 매 요청마다 계산해도 성능 부담이 없다(캐시 불필요). 이 상수는 응답을 몇 개까지
# 자를지에 대한 상한선일 뿐, 실제로는 찜이 하나라도 있는 관광지 수만큼만(그보다 적게)
# 반환될 수 있다 - 인기 없는 관광지를 억지로 채워 넣지 않는다.
POPULAR_SPOTS_LIMIT = 20

@router.get("/api/tourist-spots/popular")
def get_popular_tourist_spots(limit: int = POPULAR_SPOTS_LIMIT):
    """관광지별 tourist_wishlist 찜 개수를 세어 많이 찜된 순으로 반환한다. 화면 쪽
    카테고리 필터는 이 응답을 그대로 클라이언트에서 걸러 쓰므로(PopularSpotsScreen.js),
    여기서는 카테고리 구분 없이 전체를 순위대로 준다."""
    wishlist_res = supabase.table("tourist_wishlist").select("tour_id").execute()
    counts = Counter(row["tour_id"] for row in wishlist_res.data)
    if not counts:
        return []

    # 찜 개수 내림차순, 동점이면 tour_id 오름차순 - 매 요청마다 순서가 흔들리지 않도록
    # 항상 같은 기준으로 정렬한다.
    ordered_ids = [tour_id for tour_id, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    spots_res = supabase.table("tourist")\
        .select("tour_id, tour_name, gu_id, class_code_id, img_url")\
        .in_("tour_id", ordered_ids[:limit])\
        .execute()
    spot_by_id = {s["tour_id"]: s for s in spots_res.data}

    result = []
    for tour_id in ordered_ids:
        if len(result) >= limit:
            break
        spot = spot_by_id.get(tour_id)
        if not spot:
            # tourist_wishlist엔 있지만 tourist 원본이 삭제된 경우(정합성 깨진 데이터) -
            # 조용히 건너뛴다.
            continue
        result.append({**spot, "wish_count": counts[tour_id], "rank": len(result) + 1})
    return result

@router.get("/api/tourist-spots/{tour_id}")
def get_tourist_spot(tour_id: int):
    response = supabase.table("tourist")\
        .select("*")\
        .eq("tour_id", tour_id)\
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="관광지를 찾을 수 없습니다")
    return _sanitize_spot(response.data[0])