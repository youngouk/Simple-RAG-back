#!/usr/bin/env python3
"""
Qdrant Collection Creator for jungGU
기존 'documents' 컬렉션과 동일한 구조로 'documents-junggu' 컬렉션을 생성합니다.
"""

import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, 
    Distance,
    SparseVectorParams,
    Modifier,
    SparseIndexParams,
    CollectionInfo
)

def get_qdrant_client():
    """Qdrant 클라이언트 생성"""
    url = os.getenv("QDRANT_URL", "https://2a1f59c7-8264-43eb-b7fa-1143147aa92f.us-west-1-0.aws.cloud.qdrant.io:6333")
    api_key = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8yE7RlvWFM2HILKIAwP7i39rUTtM7j_pSxx7vs5idjY")
    
    return QdrantClient(url=url, api_key=api_key)

def get_collection_info(client: QdrantClient, collection_name: str):
    """컬렉션 정보 가져오기"""
    try:
        info = client.get_collection(collection_name)
        return info
    except Exception as e:
        print(f"❌ 컬렉션 '{collection_name}' 정보 가져오기 실패: {e}")
        return None

def create_junggu_collection(client: QdrantClient):
    """documents-junggu 컬렉션 생성"""
    collection_name = "documents-junggu"
    
    # 기존 컬렉션이 있는지 확인
    try:
        existing_collections = client.get_collections()
        collection_names = [col.name for col in existing_collections.collections]
        
        if collection_name in collection_names:
            print(f"⚠️ 컬렉션 '{collection_name}'이 이미 존재합니다.")
            response = input("기존 컬렉션을 삭제하고 새로 생성하시겠습니까? (y/N): ")
            if response.lower() == 'y':
                client.delete_collection(collection_name)
                print(f"🗑️ 기존 컬렉션 '{collection_name}' 삭제 완료")
            else:
                print("작업이 취소되었습니다.")
                return False
                
    except Exception as e:
        print(f"컬렉션 목록 확인 중 오류: {e}")
    
    # 기존 documents 컬렉션 정보 확인
    print("📋 기존 'documents' 컬렉션 구조 분석 중...")
    original_collection = get_collection_info(client, "documents")
    
    if original_collection:
        print(f"✅ 기존 컬렉션 정보:")
        vectors_config = original_collection.config.params.vectors
        if isinstance(vectors_config, dict) and 'default' in vectors_config:
            default_vector = vectors_config['default']
            print(f"   - 벡터 크기: {default_vector.size}")
            print(f"   - 거리 메트릭: {default_vector.distance}")
        elif hasattr(vectors_config, 'size'):
            print(f"   - 벡터 크기: {vectors_config.size}")
            print(f"   - 거리 메트릭: {vectors_config.distance}")
        else:
            print(f"   - 벡터 정보: 확인 불가")
        print(f"   - 스파스 벡터: {'있음' if original_collection.config.params.sparse_vectors else '없음'}")
    
    # 새로운 컬렉션 생성 (기존 컬렉션과 동일한 구조)
    print(f"🔨 새로운 컬렉션 '{collection_name}' 생성 중...")
    
    try:
        # Dense vector 설정 (기존 컬렉션과 동일)
        vectors_config = VectorParams(
            size=3072,  # gemini-embedding-001
            distance=Distance.COSINE,
        )
        
        # Sparse vector 설정 (기존과 동일하게 keywords로 설정)
        sparse_vectors_config = {
            "keywords": SparseVectorParams(
                index=SparseIndexParams()
            )
        }
        
        # 컬렉션 생성
        client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config,
        )
        
        print(f"✅ 컬렉션 '{collection_name}' 생성 완료!")
        
        # 생성된 컬렉션 정보 확인
        new_collection = get_collection_info(client, collection_name)
        if new_collection:
            print(f"📊 생성된 컬렉션 정보:")
            print(f"   - 벡터 크기: {new_collection.config.params.vectors.size}")
            print(f"   - 거리 메트릭: {new_collection.config.params.vectors.distance}")
            print(f"   - 스파스 벡터: {'활성화됨' if new_collection.config.params.sparse_vectors else '비활성화됨'}")
            print(f"   - 포인트 수: {new_collection.points_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 컬렉션 생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 Qdrant 'documents-junggu' 컬렉션 생성기")
    print("=" * 50)
    
    # 환경 변수 확인
    if not os.getenv("QDRANT_URL") or not os.getenv("QDRANT_API_KEY"):
        print("⚠️ QDRANT_URL 또는 QDRANT_API_KEY 환경변수가 설정되지 않았습니다.")
        print("환경변수를 확인해주세요.")
        return
    
    try:
        # Qdrant 클라이언트 생성
        client = get_qdrant_client()
        print("✅ Qdrant 클라이언트 연결 성공")
        
        # 컬렉션 생성
        success = create_junggu_collection(client)
        
        if success:
            print("\n🎉 작업 완료! 이제 'documents-junggu' 컬렉션을 사용할 수 있습니다.")
            print("\n📝 다음 단계:")
            print("1. config.yaml에서 collection_name을 'documents-junggu'로 변경")
            print("2. 애플리케이션 재시작")
            print("3. 문서 업로드 테스트")
        else:
            print("❌ 컬렉션 생성에 실패했습니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()