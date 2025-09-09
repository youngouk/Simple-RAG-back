#!/usr/bin/env python3
"""
Qdrant 'documents-junggu' 컬렉션 확인 스크립트
"""
import os
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

def main():
    print("🔍 Qdrant 'documents-junggu' 컬렉션 확인기")
    print("=" * 50)
    
    # 환경변수 확인
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    
    if not qdrant_url or not qdrant_api_key:
        print("⚠️ QDRANT_URL 또는 QDRANT_API_KEY 환경변수가 설정되지 않았습니다.")
        print("환경변수를 확인해주세요.")
        return
    
    try:
        # Qdrant 클라이언트 초기화
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        print("✅ Qdrant 클라이언트 연결 성공")
        
        # 컬렉션 목록 확인
        collections = client.get_collections()
        print(f"📋 전체 컬렉션 수: {len(collections.collections)}")
        print("컬렉션 목록:")
        for collection in collections.collections:
            print(f"  - {collection.name}")
        
        # documents-junggu 컬렉션 정보 확인
        collection_name = "documents-junggu"
        try:
            collection_info = client.get_collection(collection_name)
            print(f"\n✅ '{collection_name}' 컬렉션 정보:")
            print(f"   - 벡터 설정: {collection_info.config.params.vectors}")
            print(f"   - 스파스 벡터: {collection_info.config.params.sparse_vectors}")
            print(f"   - 인덱스 크기: {collection_info.points_count}")
            print(f"   - 상태: {collection_info.status}")
            
            # 기존 documents 컬렉션과 비교
            try:
                original_info = client.get_collection("documents")
                print(f"\n📊 기존 'documents' 컬렉션과 비교:")
                print(f"   documents-junggu 벡터: {collection_info.config.params.vectors}")
                print(f"   documents 벡터: {original_info.config.params.vectors}")
                print(f"   documents-junggu 스파스: {bool(collection_info.config.params.sparse_vectors)}")
                print(f"   documents 스파스: {bool(original_info.config.params.sparse_vectors)}")
                
                if (str(collection_info.config.params.vectors) == str(original_info.config.params.vectors) and
                    bool(collection_info.config.params.sparse_vectors) == bool(original_info.config.params.sparse_vectors)):
                    print("✅ 구조가 완전히 일치합니다!")
                else:
                    print("⚠️ 구조가 다릅니다.")
                    
            except ResponseHandlingException:
                print("⚠️ 기존 'documents' 컬렉션을 찾을 수 없습니다.")
                
        except ResponseHandlingException as e:
            print(f"❌ '{collection_name}' 컬렉션을 찾을 수 없습니다: {e}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()