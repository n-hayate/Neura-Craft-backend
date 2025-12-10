"""
検索APIの動作確認スクリプト
search_service.pyのデコード処理が正しく動作しているか確認
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.search_service import SearchService

def test_search():
    print("=" * 60)
    print("SearchService テスト")
    print("=" * 60)
    
    service = SearchService()
    
    if not service.is_enabled():
        print("ERROR: SearchService is not enabled. Check Azure Search configuration.")
        return
    
    print("SearchService initialized successfully.\n")
    
    # テスト1: 全件検索
    print("-" * 40)
    print("テスト1: 全件検索")
    print("-" * 40)
    total_count, files = service.search(
        query=None,
        application=None,
        issue=None,
        ingredient=None,
        customer=None,
        trial_id=None,
        author=None,
        owner_id=None,
        page=1,
        page_size=3,
    )
    print(f"Total count: {total_count}")
    print(f"Retrieved: {len(files)} files\n")
    
    # テスト2: 日本語キーワード検索（メタデータ）
    print("-" * 40)
    print("テスト2: 日本語検索「グラニュー糖」（ingredient）")
    print("-" * 40)
    total_count, files = service.search(
        query="グラニュー糖",
        application=None,
        issue=None,
        ingredient=None,
        customer=None,
        trial_id=None,
        author=None,
        owner_id=None,
        page=1,
        page_size=5,
    )
    print(f"Total count: {total_count}")
    for f in files:
        print(f"  - {f.get('original_name')} | ingredient: {f.get('ingredient')}")
    print()
    
    # テスト3: 日本語キーワード検索（application）
    print("-" * 40)
    print("テスト3: 日本語検索「低糖質クッキー」（application）")
    print("-" * 40)
    total_count, files = service.search(
        query="低糖質クッキー",
        application=None,
        issue=None,
        ingredient=None,
        customer=None,
        trial_id=None,
        author=None,
        owner_id=None,
        page=1,
        page_size=5,
    )
    print(f"Total count: {total_count}")
    for f in files:
        print(f"  - {f.get('original_name')} | application: {f.get('application')}")
    print()
    
    # テスト4: 顧客名検索
    print("-" * 40)
    print("テスト4: 日本語検索「ABC製菓」（customer）")
    print("-" * 40)
    total_count, files = service.search(
        query="ABC製菓",
        application=None,
        issue=None,
        ingredient=None,
        customer=None,
        trial_id=None,
        author=None,
        owner_id=None,
        page=1,
        page_size=5,
    )
    print(f"Total count: {total_count}")
    for f in files:
        print(f"  - {f.get('original_name')} | customer: {f.get('customer')}")
    print()
    
    # テスト5: フィルター検索（ingredient）
    print("-" * 40)
    print("テスト5: フィルター検索 ingredient=グラニュー糖")
    print("-" * 40)
    total_count, files = service.search(
        query=None,
        application=None,
        issue=None,
        ingredient="グラニュー糖",
        customer=None,
        trial_id=None,
        author=None,
        owner_id=None,
        page=1,
        page_size=5,
    )
    print(f"Total count: {total_count}")
    for f in files:
        print(f"  - {f.get('original_name')} | ingredient: {f.get('ingredient')}")
    print()
    
    # テスト6: フィルター検索（customer）
    print("-" * 40)
    print("テスト6: フィルター検索 customer=ABC製菓")
    print("-" * 40)
    total_count, files = service.search(
        query=None,
        application=None,
        issue=None,
        ingredient=None,
        customer="ABC製菓",
        trial_id=None,
        author=None,
        owner_id=None,
        page=1,
        page_size=5,
    )
    print(f"Total count: {total_count}")
    for f in files:
        print(f"  - {f.get('original_name')} | customer: {f.get('customer')}")
    print()

if __name__ == "__main__":
    test_search()

