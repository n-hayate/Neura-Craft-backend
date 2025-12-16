import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.services.extraction_service import get_extraction
from app.services.search_service import SearchService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_with_ai(
    request: AIAnalysisRequest,
    response: Response,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    あなたは熟練の食品開発アドバイザーです。
    #検索結果の上位N件からLLMで分析・要約を行う
    #全体の文字数は1000文字を標準とし、1500文字程度を上限とする。但し参照するデータが少ないなどの場合は1000文字より少なくてもよい。
    #回答にあたり、余計な前置きはなるべく所略する。
    
    例:
    - 「このファイルから失敗の原因について考察している内容をまとめる」
    - 「これらの資料から最適な配合比率を抽出する」
    """
    try:
        # 1. 検索サービスで上位N件を取得（contentを含む）
        search_service = SearchService()
        if not search_service.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Azure Search is not configured.",
            )

        search_results = search_service.search_for_rag(
            query=request.q,
            sort_by=request.sort_by,
            top=request.top,
        )

        if not search_results:
            response.headers["X-AI-Context-Mode"] = "none"
            response.headers["X-AI-Context-Extraction-Count"] = "0"
            response.headers["X-AI-Context-Content-Count"] = "0"
            return AIAnalysisResponse(
                answer="検索結果が見つかりませんでした。検索条件を変更して再度お試しください。",
                sources=[],
                error=None,
            )

        # 2. 抽出データを優先してLLM用コンテキストを構築（抽出が無い場合は既存contentを短くフォールバック）
        used_ex = 0
        used_content = 0
        docs_for_llm = []
        for doc in search_results:
            file_id = doc.get("id") or doc.get("file_id")
            original_name = doc.get("original_name") or doc.get("file_name") or file_id or "unknown"

            ex = get_extraction(db, file_id) if file_id else None
            if ex:
                used_ex += 1
                content = _extraction_to_text(ex)
            else:
                used_content += 1
                content = (doc.get("content") or "")[:3000]

            docs_for_llm.append({"original_name": original_name, "content": content})

        if used_ex and not used_content:
            mode = "extraction"
        elif used_content and not used_ex:
            mode = "content"
        elif used_ex or used_content:
            mode = "mixed"
        else:
            mode = "none"

        response.headers["X-AI-Context-Mode"] = mode
        response.headers["X-AI-Context-Extraction-Count"] = str(used_ex)
        response.headers["X-AI-Context-Content-Count"] = str(used_content)

        # 3. LLMサービスで分析
        llm_service = LLMService()
        if not llm_service.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service is not configured. Please configure LLM_API_KEY and related settings.",
            )

        result = await llm_service.generate_response(request.question, docs_for_llm)

        if result.get("error"):
            logger.error(f"LLM error: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM processing failed: {result['error']}",
            )

        return AIAnalysisResponse(
            answer=result["answer"],
            sources=[d.get("original_name", "") for d in docs_for_llm if d.get("original_name")],
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in AI analysis endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


def _extraction_to_text(ex: dict) -> str:
    meta = ex.get("meta", {}) or {}
    logs = ex.get("log", []) or []
    form = ex.get("formulation", {}) or {}

    lines: list[str] = []
    lines.append("【メタ】")
    for k in [
        "trial_id",
        "application",
        "issue",
        "ingredient",
        "customer",
        "author",
        "date",
        "selected_variant",
        "outcome",
        "failure_tags",
        "keywords",
    ]:
        if meta.get(k):
            lines.append(f"- {k}: {meta.get(k)}")

    lines.append("\n【LOG】")
    for row in logs[:3]:
        lines.append(
            f"- {row.get('variant_id')} {row.get('variant_label')}: "
            f"判定={row.get('judgement')}, "
            f"結果={row.get('result')}, "
            f"失敗={row.get('failure_symptoms')}, "
            f"仮説={row.get('cause_hypothesis')}, "
            f"次={row.get('next_action')}"
        )
        q = row.get("quote")
        if q:
            lines.append(f"  引用: {q}")

    lines.append("\n【配合（抜粋）】")
    rows = (form.get("rows") or [])[:10]
    for r in rows:
        ing = r.get("ingredient")
        v = r.get("variants", {}) or {}
        if ing:
            n1 = v.get("No.1", {}) or {}
            lines.append(f"- {ing}: {n1.get('pct')}% / {n1.get('g')}g（No.1）")

    return "\n".join(lines)

