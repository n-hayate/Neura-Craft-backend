import asyncio
import logging
from typing import List, Dict, Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """LLM統合サービス（Azure OpenAI / Gemini対応）"""

    def __init__(self) -> None:
        self.provider = getattr(settings, "llm_provider", "azure_openai").lower()
        self.api_key = getattr(settings, "llm_api_key", "")
        self.endpoint = getattr(settings, "llm_endpoint", "")
        self.model = getattr(settings, "llm_model", "gpt-4")
        self.max_tokens = getattr(settings, "llm_max_tokens", 2000)
        self.temperature = getattr(settings, "llm_temperature", 0.7)

        if not self.api_key:
            logger.warning("LLM API key not configured. LLM features will be disabled.")
            self.enabled = False
        else:
            self.enabled = True

            if self.provider == "azure_openai":
                try:
                    from openai import AsyncAzureOpenAI
                    self.client = AsyncAzureOpenAI(
                        api_key=self.api_key,
                        api_version=getattr(settings, "azure_openai_api_version", "2024-02-15-preview"),
                        azure_endpoint=self.endpoint,
                    )
                except ImportError:
                    logger.error("openai package not installed. Install with: pip install openai")
                    self.enabled = False
            elif self.provider == "gemini":
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    self.client = genai.GenerativeModel(self.model)
                except ImportError:
                    logger.error("google-generativeai package not installed. Install with: pip install google-generativeai")
                    self.enabled = False
            else:
                logger.warning(f"Unknown LLM provider: {self.provider}")
                self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled

    def create_prompt_with_search_results(
        self, user_question: str, search_results: List[Dict[str, Any]], max_content_length: int = 10000
    ) -> tuple[str, str]:
        """
        検索結果からプロンプトを作成する
        
        Returns:
            (system_prompt, user_message) のタプル
        """
        # 1. 検索結果をLLMが読みやすいテキスト形式に整形
        context_text = ""
        for index, item in enumerate(search_results, 1):
            file_name = item.get("original_name", "不明なファイル")
            content = item.get("content", "")

            # 文字数制限対策
            if len(content) > max_content_length:
                content = content[:max_content_length] + "\n[... 以下省略 ...]"

            # XMLタグ風に囲むとAIが区切りを認識しやすい
            context_text += f"""
<document index="{index}">
<source>{file_name}</source>
<content>
{content}
</content>
</document>
"""

        # 2. プロンプトの組み立て
        system_prompt = """あなたは熟練の食品開発アドバイザーです。
提供された `<document>` タグ内の情報**のみ**に基づいて、ユーザーの質問に回答してください。
情報がない場合は「提供された資料には記載がありません」と答えてください。
回答の際は、根拠となったファイル名（source）を必ず明記してください。
回答は日本語で、わかりやすく構造化された形式で提供してください。"""

        user_message = f"""質問: {user_question}

以下の参照ドキュメントを使用して回答を作成してください:

{context_text}
"""

        return system_prompt, user_message

    async def generate_response(
        self, user_question: str, search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        LLMを使って検索結果から回答を生成する
        
        Returns:
            {
                "answer": str,
                "sources": List[str],  # 参照したファイル名のリスト
                "error": Optional[str]
            }
        """
        if not self.enabled:
            return {
                "answer": "",
                "sources": [],
                "error": "LLM service is not configured or enabled.",
            }

        try:
            system_prompt, user_message = self.create_prompt_with_search_results(user_question, search_results)

            if self.provider == "azure_openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                answer = response.choices[0].message.content
                sources = [item.get("original_name", "") for item in search_results if item.get("original_name")]

            elif self.provider == "gemini":
                # Geminiは同期APIなので、asyncio.to_threadで実行
                prompt = f"{system_prompt}\n\n{user_message}"
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self.client.generate_content, prompt)
                answer = response.text
                sources = [item.get("original_name", "") for item in search_results if item.get("original_name")]

            else:
                return {
                    "answer": "",
                    "sources": [],
                    "error": f"Unsupported provider: {self.provider}",
                }

            return {
                "answer": answer or "",
                "sources": sources,
                "error": None,
            }

        except Exception as e:
            logger.exception("Error generating LLM response")
            return {
                "answer": "",
                "sources": [],
                "error": str(e),
            }

