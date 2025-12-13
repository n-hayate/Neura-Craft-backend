from pydantic import BaseModel, Field
from typing import List, Optional


class AIAnalysisRequest(BaseModel):
    """AI分析リクエスト"""
    question: str = Field(..., description="分析したい質問（例: このファイルから失敗の原因について考察している内容をまとめる）")
    q: Optional[str] = Field(None, description="検索キーワード")
    sort_by: str = Field("updated_at_desc", description="ソートキー")
    top: int = Field(3, ge=1, le=10, description="分析に使用する上位N件（デフォルト: 3）")


class AIAnalysisResponse(BaseModel):
    """AI分析レスポンス"""
    answer: str = Field(..., description="LLMが生成した回答")
    sources: List[str] = Field(default_factory=list, description="参照したファイル名のリスト")
    error: Optional[str] = Field(None, description="エラーメッセージ（エラー時のみ）")

