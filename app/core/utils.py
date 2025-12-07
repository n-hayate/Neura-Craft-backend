import re

def normalize_tags(text: str | None) -> str:
    """
    入力文字列のゆらぎを吸収して正規化する。
    
    - Noneの場合は空文字を返す
    - 読点、カンマ、全角スペースを「半角スペース」に統一
    - 連続するスペースを除去し、前後の空白を削除
    """
    if not text:
        return ""
    # 読点、カンマ、全角スペースを「半角スペース」に統一
    clean_text = re.sub(r'[、,，\u3000]', ' ', text)
    # 連続するスペースを除去し、前後の空白を削除
    return re.sub(r'\s+', ' ', clean_text).strip()
















