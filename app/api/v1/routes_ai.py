import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.services.search_service import SearchService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_with_ai(
    request: AIAnalysisRequest,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    あなたは熟練の食品開発アドバイザーです。
    検索結果の上位N件からLLMで分析・要約を行う
    
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
            return AIAnalysisResponse(
                answer="検索結果が見つかりませんでした。検索条件を変更して再度お試しください。",
                sources=[],
                error=None,
            )

        # 2. LLMサービスで分析
        llm_service = LLMService()
        if not llm_service.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service is not configured. Please configure LLM_API_KEY and related settings.",
            )

        result = await llm_service.generate_response(request.question, search_results)

        if result.get("error"):
            logger.error(f"LLM error: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM processing failed: {result['error']}",
            )

        return AIAnalysisResponse(
            answer=result["answer"],
            sources=result["sources"],
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

