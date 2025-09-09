"""
Retrieval and reranking module
검색 및 리랭킹 모듈 (Qdrant + 하이브리드 검색 + 리랭킹)
"""
import asyncio
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, CollectionInfo, SparseVectorParams,
    PointStruct, Filter, FieldCondition, MatchValue,
    ScoredPoint, SparseVector, NamedVector,
    FusionQuery, Fusion, NearestQuery, Prefetch
)
from fastembed import SparseTextEmbedding

# Reranking clients
import httpx
from cohere import Client as CohereClient

# Query expansion
from .query_expansion import GPT5QueryExpansionEngine, ExpandedQuery

from ..lib.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SearchResult:
    """검색 결과 데이터 클래스"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        # 하위 호환성을 위해 속성으로도 접근 가능하게 설정
        for key, value in self.metadata.items():
            setattr(self, key, value)

class RetrievalModule:
    """검색 및 리랭킹 모듈"""
    
    def __init__(self, config: Dict[str, Any], embedder):
        self.config = config
        self.qdrant_config = config.get('qdrant', {})
        self.reranking_config = config.get('reranking', {})
        self.multi_query_config = config.get('multi_query', {})
        self.embeddings_config = config.get('embeddings', {})
        self.sparse_embedding_config = config.get('sparse_embeddings', {})  # Sparse embedding 설정 추가
        
        # Qdrant 클라이언트
        self.qdrant_client = None
        self.collection_name = self.qdrant_config.get('collection_name', 'documents')
        
        # 임베딩 모델들
        self.embedder = embedder  # Dense embedder
        self.sparse_embedder = None  # Sparse embedder (BM42)
        
        # 하이브리드 검색 설정
        self.dense_weight = self.qdrant_config.get('hybrid_search', {}).get('dense_weight', 0.6)
        self.sparse_weight = self.qdrant_config.get('hybrid_search', {}).get('sparse_weight', 0.4)
        self.hybrid_enabled = False
        
        # 리랭킹 클라이언트들
        self.rerankers = {}
        
        # 쿼리 확장 엔진
        self.query_expansion_engine = None
        self.query_expansion_enabled = self.multi_query_config.get('enable_query_expansion', False)
        
        # 통계
        self.stats = {
            'total_searches': 0,
            'total_documents': 0,
            'vector_count': 0,
            'rerank_requests': 0,
            'hybrid_searches': 0,
            'query_expansions': 0
        }
        
        # 동시성 제어 및 상태 관리 (Race Condition 방지)
        self._collection_lock = asyncio.Lock()  # 콜렉션 관리 동시성 제어
        self._hybrid_compatibility_checked = False  # 하이브리드 호환성 체크 완료 플래그
        self._collection_initialized = False  # 콜렉션 초기화 완료 플래그
    
    async def initialize(self):
        """모듈 초기화"""
        try:
            logger.info("Initializing retrieval module...")
            
            # 1. Sparse embedder 초기화
            await self._init_sparse_embedder()
            
            # 2. Qdrant 클라이언트 초기화
            await self._init_qdrant()
            
            # 3. 컬렉션 초기화
            await self._init_collection()
            
            # 4. 리랭커 초기화
            await self._init_rerankers()
            
            # 5. 쿼리 확장 엔진 초기화 
            await self._init_query_expansion()
            
            logger.info(f"Retrieval module initialized successfully (hybrid: {self.hybrid_enabled}, query_expansion: {self.query_expansion_enabled})")
            
        except Exception as e:
            logger.error(f"Retrieval module initialization failed: {e}")
            raise
    
    async def close(self):
        """모듈 정리"""
        try:
            if self.qdrant_client:
                self.qdrant_client.close()
            logger.info("Retrieval module closed")
        except Exception as e:
            logger.error(f"Retrieval module close error: {e}")
    
    async def _init_qdrant(self):
        """Qdrant 클라이언트 초기화"""
        # URL 우선 사용 (클라우드 서비스의 경우)
        qdrant_url = self.qdrant_config.get('url')
        api_key = self.qdrant_config.get('api_key')
        
        if qdrant_url and qdrant_url.startswith('https://'):
            # 클라우드 Qdrant 서비스
            self.qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=api_key,
                timeout=30
            )
            logger.info(f"Qdrant client connected to cloud service: {qdrant_url}")
        else:
            # 로컬 Qdrant 서버
            host = self.qdrant_config.get('host', 'localhost')
            port = self.qdrant_config.get('port', 6333)
            
            # HTTP vs gRPC 선택
            prefer_grpc = self.qdrant_config.get('prefer_grpc', False)
            
            if prefer_grpc:
                self.qdrant_client = QdrantClient(host=host, port=port, prefer_grpc=True)
            else:
                self.qdrant_client = QdrantClient(url=f"http://{host}:{port}")
            
            logger.info(f"Qdrant client connected to local server: {host}:{port}")
        
        # 연결 테스트
        await asyncio.to_thread(self.qdrant_client.get_collections)
        logger.info("Qdrant connection test successful")
    
    async def _init_sparse_embedder(self):
        """Sparse embedder 초기화 (BM42 모델 사용)"""
        try:
            if not self.sparse_embedding_config.get('enabled', False):
                logger.info("Sparse embeddings disabled in config")
                self.sparse_embedder = None
                self.hybrid_enabled = False
                return
            
            model_id = self.sparse_embedding_config.get('model', "Qdrant/bm42-all-minilm-l6-v2-attentions")
            from fastembed import SparseTextEmbedding
            
            self.sparse_embedder = SparseTextEmbedding(
                model_name=model_id,
                cache_dir="models/sparse"
            )
            
            # 하이브리드 모드 활성화
            self.hybrid_enabled = True
            logger.info(f"Sparse embedder initialized and hybrid mode enabled: {model_id}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize sparse embedder: {e}")
            self.sparse_embedder = None
            self.hybrid_enabled = False
    
    async def _init_collection(self):
        """컬렉션 초기화 (하이브리드 벡터 지원)"""
        try:
            # 컬렉션 존재 확인
            collections = await asyncio.to_thread(self.qdrant_client.get_collections)
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating hybrid collection: {self.collection_name}")
                
                # Dense 임베딩 차원 계산
                test_embedding = await asyncio.to_thread(
                    self.embedder.embed_query, "test"
                )
                dense_vector_size = len(test_embedding)
                
                # 하이브리드 벡터 설정 (Qdrant 문서 기준)
                # Dense vectors: 기본 vectors 필드
                # Sparse vectors: sparse_vectors 필드
                if self.hybrid_enabled and self.sparse_embedder:
                    # 하이브리드 모드: dense + sparse
                    from qdrant_client.models import SparseVectorParams, SparseIndexParams
                    
                    vectors_config = VectorParams(
                        size=dense_vector_size,
                        distance=Distance.COSINE
                    )
                    
                    sparse_vectors_config = {
                        "keywords": SparseVectorParams(
                            index=SparseIndexParams(
                                on_disk=False
                            )
                        )
                    }
                    
                    logger.info(f"Creating hybrid collection with dense (size: {dense_vector_size}) and sparse vectors")
                    
                    await asyncio.to_thread(
                        self.qdrant_client.create_collection,
                        collection_name=self.collection_name,
                        vectors_config=vectors_config,
                        sparse_vectors_config=sparse_vectors_config
                    )
                else:
                    # Dense-only 모드
                    vectors_config = VectorParams(
                        size=dense_vector_size,
                        distance=Distance.COSINE
                    )
                    logger.info(f"Creating collection with dense vectors only (size: {dense_vector_size})")
                    
                    await asyncio.to_thread(
                        self.qdrant_client.create_collection,
                        collection_name=self.collection_name,
                        vectors_config=vectors_config
                    )
                
                logger.info(f"Collection {self.collection_name} created successfully with dense vectors")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
            # 컬렉션 정보 업데이트
            await self._update_collection_stats()
            
            # 컬렉션 초기화 완료 표시
            self._collection_initialized = True
            
        except Exception as e:
            logger.error(f"Collection initialization failed: {e}")
            raise
    
    async def _init_rerankers(self):
        """리랭커 초기화"""
        if not self.reranking_config.get('enabled', False):
            logger.info("Reranking disabled")
            return
        
        providers = self.reranking_config.get('providers', {})
        
        # Cohere 리랭커
        if 'cohere' in providers:
            cohere_config = providers['cohere']
            if cohere_config.get('api_key'):
                self.rerankers['cohere'] = CohereClient(
                    api_key=cohere_config['api_key']
                )
                logger.info("Cohere reranker initialized")
        
        # Jina 리랭커 (HTTP API)
        if 'jina' in providers:
            jina_config = providers['jina']
            if jina_config.get('api_key'):
                self.rerankers['jina'] = {
                    'api_key': jina_config['api_key'],
                    'model': jina_config.get('model', 'jina-reranker-v1-base-en'),
                    'endpoint': jina_config.get('endpoint', 'https://api.jina.ai/v1/rerank')
                }
                logger.info("Jina reranker initialized")
        
        logger.info(f"Initialized {len(self.rerankers)} rerankers")
    
    async def _update_collection_stats(self):
        """컬렉션 통계 업데이트"""
        try:
            collection_info = await asyncio.to_thread(
                self.qdrant_client.get_collection,
                collection_name=self.collection_name
            )
            
            self.stats['vector_count'] = collection_info.vectors_count or 0
            self.stats['total_documents'] = collection_info.points_count or 0
            
        except Exception as e:
            logger.warning(f"Failed to update collection stats: {e}")
    
    async def _ensure_hybrid_collection_compatibility(self):
        """안전한 하이브리드 벡터 지원을 위한 컬렉션 호환성 확인 (Race Condition 방지)"""
        # 이미 체크가 완료되었거나 하이브리드가 비활성화된 경우 스킵
        if self._hybrid_compatibility_checked or not self.hybrid_enabled:
            return
        
        # 동시성 제어: 하나의 프로세스만 호환성 체크를 수행
        async with self._collection_lock:
            # Double-check locking: lock을 획득한 후 다시 한 번 체크
            if self._hybrid_compatibility_checked:
                return
            
            try:
                logger.info("안전한 하이브리드 호환성 체크 시작...")
                
                # 컬렉션 존재 여부 확인
                collections = await asyncio.to_thread(
                    self.qdrant_client.get_collections
                )
                collection_names = [col.name for col in collections.collections]
                
                if self.collection_name not in collection_names:
                    logger.info(f"컬렉션 '{self.collection_name}'이 존재하지 않음. 하이브리드 지원 컬렉션으로 생성 중...")
                    await self._init_collection()
                    self._hybrid_compatibility_checked = True
                    return
                
                # 컬렉션 정보 조회
                collection_info = await asyncio.to_thread(
                    self.qdrant_client.get_collection, self.collection_name
                )
                
                # vectors_config에서 sparse 벡터 설정 확인
                vectors_config = collection_info.config.params.vectors
                needs_hybrid_support = False
                
                # sparse 벡터 지원 여부 확인
                if isinstance(vectors_config, dict):
                    if "sparse" not in vectors_config:
                        needs_hybrid_support = True
                        logger.info("기존 컬렉션에 sparse 벡터 지원이 없음")
                else:
                    # VectorParams 단일 객체인 경우 (dense only)
                    needs_hybrid_support = True
                    logger.info("기존 컬렉션이 단일 벡터 구성임 (dense only)")
                
                if needs_hybrid_support:
                    # 기존 데이터 보존을 위한 안전한 마이그레이션
                    await self._safe_migrate_to_hybrid_collection()
                else:
                    logger.info("컬렉션이 이미 하이브리드 벡터를 지원함")
                
                # 호환성 체크 완료 표시
                self._hybrid_compatibility_checked = True
                logger.info("하이브리드 호환성 체크 완료")
                
            except Exception as e:
                logger.error(f"하이브리드 호환성 체크 실패: {e}")
                # 오류 발생 시에도 체크 완료로 표시하여 무한 재시도 방지
                self._hybrid_compatibility_checked = True
                # sparse 임베딩을 비활성화하여 기존 기능 유지
                logger.warning("하이브리드 기능을 임시 비활성화하여 기존 기능 유지")
                self.hybrid_enabled = False
    
    async def _safe_migrate_to_hybrid_collection(self):
        """기존 데이터를 보존하면서 하이브리드 지원 컬렉션으로 안전하게 마이그레이션"""
        try:
            logger.info("기존 데이터 보존하며 하이브리드 컬렉션으로 마이그레이션 시작...")
            
            # 백업 컬렉션 이름 생성
            backup_collection_name = f"{self.collection_name}_backup_{int(asyncio.get_event_loop().time())}"
            
            # 1. 기존 데이터 개수 확인
            collection_info = await asyncio.to_thread(
                self.qdrant_client.get_collection, self.collection_name
            )
            existing_count = collection_info.points_count
            logger.info(f"기존 컬렉션에서 {existing_count}개의 포인트 발견")
            
            if existing_count == 0:
                # 데이터가 없는 경우 단순히 컬렉션 재생성
                logger.info("기존 데이터가 없으므로 단순 재생성 수행")
                await asyncio.to_thread(
                    self.qdrant_client.delete_collection, self.collection_name
                )
                await self._init_collection()
                return
            
            # 2. 기존 컬렉션을 백업 이름으로 생성 (복사)
            logger.info(f"기존 데이터를 '{backup_collection_name}'으로 백업 중...")
            
            # 기존 컬렉션과 동일한 구조로 백업 컬렉션 생성
            vectors_config = collection_info.config.params.vectors
            await asyncio.to_thread(
                self.qdrant_client.create_collection,
                collection_name=backup_collection_name,
                vectors_config=vectors_config
            )
            
            # 모든 포인트를 백업 컬렉션으로 복사
            scroll_result = await asyncio.to_thread(
                self.qdrant_client.scroll,
                collection_name=self.collection_name,
                limit=existing_count,
                with_vectors=True,
                with_payload=True
            )
            points = scroll_result[0]  # scroll returns (points, next_page_offset)
            
            if points:
                await asyncio.to_thread(
                    self.qdrant_client.upsert,
                    collection_name=backup_collection_name,
                    points=points
                )
                logger.info(f"{len(points)}개의 포인트를 백업 컬렉션에 복사 완료")
            
            # 3. 기존 컬렉션 삭제
            logger.info("기존 컬렉션 삭제 중...")
            await asyncio.to_thread(
                self.qdrant_client.delete_collection, self.collection_name
            )
            
            # 4. 하이브리드 지원 컬렉션 생성
            logger.info("하이브리드 지원 컬렉션 재생성 중...")
            await self._init_collection()
            
            # 5. 사용자에게 알림
            if existing_count > 0:
                logger.warning(f"마이그레이션 완료: 기존 {existing_count}개 문서는 '{backup_collection_name}' 컬렉션에 백업됨")
                logger.warning("하이브리드 검색을 위해서는 문서를 다시 업로드해주세요.")
                logger.info("백업 컬렉션은 기존 문서 검색 및 복원에 사용할 수 있습니다.")
            
            logger.info("하이브리드 컬렉션 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"하이브리드 컬렉션 마이그레이션 실패: {e}")
            # 백업 컬렉션 정리 (오류 발생 시)
            try:
                backup_collection_name = f"{self.collection_name}_backup_{int(asyncio.get_event_loop().time())}"
                await asyncio.to_thread(
                    self.qdrant_client.delete_collection, backup_collection_name
                )
            except:
                pass
            raise e
    
    async def add_documents(self, embedded_chunks: List[Dict[str, Any]]) -> bool:
        """문서 추가 (하이브리드 벡터 지원)"""
        if not embedded_chunks:
            return True
        
        try:
            logger.info(f"Adding {len(embedded_chunks)} documents to collection")
            
            # 하이브리드 모드이지만 기존 컬렉션이 sparse vector를 지원하지 않는 경우 체크
            if self.hybrid_enabled and any('sparse_embedding' in chunk for chunk in embedded_chunks):
                await self._ensure_hybrid_collection_compatibility()
            
            # Point 객체 생성
            points = []
            for i, chunk in enumerate(embedded_chunks):
                # UUID 기반 point ID 생성
                import uuid
                point_id = str(uuid.uuid4())
                
                # 벡터 구성 - 하이브리드 모드 지원
                if self.hybrid_enabled and 'sparse_embedding' in chunk:
                    # 하이브리드 모드: dense + sparse
                    # Qdrant 문서 기준: dense는 기본 vector, sparse는 named vector
                    from qdrant_client.models import SparseVector
                    
                    vectors = {
                        "": chunk['dense_embedding'],  # 기본 dense vector (unnamed)
                        "keywords": SparseVector(
                            indices=chunk['sparse_embedding']['indices'],
                            values=chunk['sparse_embedding']['values']
                        )
                    }
                else:
                    # Dense-only 모드
                    vectors = chunk['dense_embedding']
                
                points.append(PointStruct(
                    id=point_id,
                    vector=vectors,
                    payload={
                        'content': chunk['content'],
                        'metadata': chunk['metadata']
                    }
                ))
            
            # 배치로 업로드 - sparse vector 오류 감지 및 복구
            batch_size = self.qdrant_config.get('batch_size', 100)
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                
                try:
                    await asyncio.to_thread(
                        self.qdrant_client.upsert,
                        collection_name=self.collection_name,
                        points=batch
                    )
                    
                    logger.debug(f"Uploaded batch {i//batch_size + 1}/{math.ceil(len(points)/batch_size)}")
                    
                except Exception as upsert_error:
                    error_msg = str(upsert_error)
                    
                    # 오류 로깅 및 전파
                    logger.error(f"Failed to upload batch {i//batch_size + 1}: {error_msg}")
                    raise upsert_error
            
            # 통계 업데이트
            await self._update_collection_stats()
            
            logger.info(f"Successfully added {len(embedded_chunks)} documents with hybrid vectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    async def search(self, query: str, options: Dict[str, Any] = None) -> List[SearchResult]:
        """검색 실행 (개선된 검색 및 중복 제거)"""
        options = options or {}
        limit = options.get('limit', 20)
        min_score = options.get('min_score', 0.5)  # 기본 임계값을 0.5로 상향
        
        self.stats['total_searches'] += 1
        
        try:
            logger.debug(f"Searching for: {query[:50]}... (min_score={min_score})")
            
            # 쿼리 전처리 - 한국어 검색 개선
            processed_query = self._preprocess_korean_query(query)
            
            # 쿼리 확장 시도
            expanded_query = await self.expand_query(processed_query)
            queries_to_search = []
            
            if expanded_query:
                # 확장된 쿼리들과 원본 쿼리 결합
                queries_to_search = [processed_query]
                for exp_q in expanded_query.expanded_queries[:3]:  # 최대 3개 추가 쿼리
                    queries_to_search.append(exp_q['query'])
                logger.info(f"Using multi-query search with {len(queries_to_search)} queries")
            else:
                # 확장 실패 시 원본 쿼리만 사용
                queries_to_search = [processed_query]
            
            # 다중 쿼리 검색 결과 수집
            all_results = []
            
            for search_query in queries_to_search:
                try:
                    if self.hybrid_enabled and self.sparse_embedder:
                        # 하이브리드 검색 실행
                        query_results = await self._hybrid_search(search_query, limit, min_score)
                        self.stats['hybrid_searches'] += 1
                    else:
                        # Dense 검색만 실행
                        query_embedding = await asyncio.to_thread(
                            self.embedder.embed_query, search_query
                        )
                        query_results = await self._dense_search(query_embedding, limit=limit)
                        
                        # 점수 필터링
                        query_results = [
                            result for result in query_results 
                            if result.score >= min_score
                        ]
                    
                    all_results.extend(query_results)
                    
                except Exception as e:
                    logger.warning(f"Search failed for query '{search_query[:30]}...': {e}")
                    continue
            
            # 다중 쿼리 결과 융합 및 중복 제거
            if expanded_query and len(queries_to_search) > 1:
                final_results = self._fuse_multi_query_results(all_results, expanded_query)
                logger.info(f"Multi-query fusion: {len(all_results)} -> {len(final_results)} results")
            else:
                final_results = all_results
            
            # 최종 결과 품질 검증
            quality_results = self._validate_search_quality(query, final_results)
            
            logger.info(f"Search completed: {len(quality_results)} high-quality results returned")
            return quality_results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def _hybrid_search(self, query: str, limit: int, min_score: float) -> List[SearchResult]:
        """Qdrant 네이티브 하이브리드 검색"""
        try:
            # 쿼리 임베딩 생성
            dense_embedding = await asyncio.to_thread(
                self.embedder.embed_query, query
            )
            
            # Sparse 임베딩 생성
            sparse_results = await asyncio.to_thread(
                list, self.sparse_embedder.embed([query])
            )
            sparse_embedding = sparse_results[0] if sparse_results else None
            
            if sparse_embedding is None:
                logger.warning("Failed to generate sparse embedding, falling back to dense search")
                return await self._dense_search(dense_embedding, limit)
            
            # Sparse vector 생성
            sparse_vector = SparseVector(
                indices=sparse_embedding.indices.tolist(),
                values=sparse_embedding.values.tolist()
            )
            
            # Qdrant 네이티브 하이브리드 검색 실행
            logger.debug("Executing Qdrant native hybrid search with RRF fusion")
            query_response = await asyncio.to_thread(
                self.qdrant_client.query_points,
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=NearestQuery(nearest=dense_embedding),
                        using="",  # Dense vector는 unnamed (기본)
                        limit=limit * 2
                    ),
                    Prefetch(
                        query=NearestQuery(nearest=sparse_vector),
                        using="keywords",  # Sparse vector는 "keywords"로 명명
                        limit=limit * 2
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=limit,
                with_payload=True,
                score_threshold=min_score
            )
            
            # 결과 처리
            results = []
            for point in query_response.points:
                results.append(SearchResult(
                    id=str(point.id),
                    content=point.payload['content'],
                    score=point.score,
                    metadata=point.payload['metadata']
                ))
            
            logger.info(f"Native hybrid search completed: {len(results)} results (RRF fusion)")
            return results
            
        except Exception as e:
            logger.error(f"Native hybrid search failed: {e}")
            logger.info("Falling back to legacy hybrid search implementation")
            
            # 실패 시 기존 방식으로 폴백
            try:
                return await self._legacy_hybrid_search(query, limit, min_score)
            except Exception as fallback_error:
                logger.error(f"Legacy hybrid search also failed: {fallback_error}")
                # 최종적으로 dense 검색으로 폴백
                return await self._dense_search(
                    await asyncio.to_thread(self.embedder.embed_query, query), limit
                )
    
    async def _legacy_hybrid_search(self, query: str, limit: int, min_score: float) -> List[SearchResult]:
        """기존 방식의 하이브리드 검색 (폴백용)"""
        try:
            logger.info("Using legacy hybrid search implementation")
            
            # 쿼리 임베딩 생성
            dense_embedding = await asyncio.to_thread(
                self.embedder.embed_query, query
            )
            
            # Sparse 임베딩 생성
            sparse_results = await asyncio.to_thread(
                list, self.sparse_embedder.embed([query])
            )
            sparse_embedding = sparse_results[0] if sparse_results else None
            
            if sparse_embedding is None:
                logger.warning("Failed to generate sparse embedding in legacy mode")
                return await self._dense_search(dense_embedding, limit)
            
            # 별도 검색 실행 (기존 방식)
            dense_results = await asyncio.to_thread(
                self.qdrant_client.search,
                collection_name=self.collection_name,
                query_vector=dense_embedding,  # Dense vector는 unnamed (기본)
                limit=limit * 2,
                with_payload=True
            )
            
            # Sparse vector 생성
            from qdrant_client.models import SparseVector
            sparse_vector = SparseVector(
                indices=sparse_embedding.indices.tolist(),
                values=sparse_embedding.values.tolist()
            )
            
            sparse_results = await asyncio.to_thread(
                self.qdrant_client.search,
                collection_name=self.collection_name,
                query_vector=("sparse", SparseVector(
                    indices=sparse_embedding.indices.tolist(),
                    values=sparse_embedding.values.tolist()
                )),
                limit=limit * 2,
                with_payload=True
            )
            
            # RRF 융합
            fused_results = self._rrf_fusion(dense_results, sparse_results, limit)
            
            # 점수 필터링
            filtered_results = [
                result for result in fused_results 
                if result.score >= min_score
            ]
            
            logger.info(f"Legacy hybrid search: {len(dense_results)} dense + {len(sparse_results)} sparse -> {len(fused_results)} fused -> {len(filtered_results)} filtered")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Legacy hybrid search failed: {e}")
            # 최종 폴백: dense 검색만
            return await self._dense_search(
                await asyncio.to_thread(self.embedder.embed_query, query), limit
            )
    
    async def _dense_search(self, query_embedding: List[float], limit: int) -> List[SearchResult]:
        """Dense 벡터 검색 (중복 제거 및 스코어 정규화 포함)"""
        try:
            # 더 많은 결과를 가져와서 중복 제거 후 필터링
            search_result = await asyncio.to_thread(
                self.qdrant_client.search,
                collection_name=self.collection_name,
                query_vector=query_embedding,  # Dense vector는 unnamed (기본)
                limit=limit * 3,  # 중복 제거를 고려하여 3배 더 가져옴
                with_payload=True
            )
            
            # 중복 제거를 위한 콘텐츠 해시 추적
            seen_content = set()
            unique_results = []
            
            for point in search_result:
                content = point.payload['content']
                # 콘텐츠 해시로 중복 검사 (공백 정규화 후)
                content_hash = hash(content.strip())
                
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    # 코사인 유사도 스코어 정규화 (0~1 범위로 변환)
                    normalized_score = max(0.0, min(1.0, (point.score + 1.0) / 2.0))
                    
                    unique_results.append(SearchResult(
                        id=str(point.id),
                        content=content,
                        score=normalized_score,
                        metadata=point.payload['metadata']
                    ))
            
            # 스코어 기준으로 정렬하고 limit만큼 반환
            unique_results.sort(key=lambda x: x.score, reverse=True)
            final_results = unique_results[:limit]
            
            logger.info(f"Dense search: {len(search_result)} raw -> {len(unique_results)} unique -> {len(final_results)} final results")
            
            # 상위 3개 결과의 스코어 로깅
            for i, result in enumerate(final_results[:3]):
                logger.info(f"Result {i+1}: score={result.score:.3f} (normalized), content: {result.content[:50]}...")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            return []
    
    def _rrf_fusion(self, dense_points: List, sparse_points: List, limit: int) -> List[SearchResult]:
        """Reciprocal Rank Fusion으로 dense와 sparse 결과 융합"""
        try:
            k = 60  # RRF 상수
            doc_scores = {}
            
            # Dense 결과 처리
            for rank, point in enumerate(dense_points):
                point_id = str(point.id)
                if point_id not in doc_scores:
                    doc_scores[point_id] = {
                        'point': point,
                        'rrf_score': 0
                    }
                
                rrf_score = 1 / (k + rank + 1)
                doc_scores[point_id]['rrf_score'] += rrf_score * self.dense_weight
            
            # Sparse 결과 처리
            for rank, point in enumerate(sparse_points):
                point_id = str(point.id)
                if point_id not in doc_scores:
                    doc_scores[point_id] = {
                        'point': point,
                        'rrf_score': 0
                    }
                
                rrf_score = 1 / (k + rank + 1)
                doc_scores[point_id]['rrf_score'] += rrf_score * self.sparse_weight
            
            # 점수순 정렬
            sorted_docs = sorted(
                doc_scores.values(),
                key=lambda x: x['rrf_score'],
                reverse=True
            )
            
            # SearchResult 객체 생성
            results = []
            for doc_data in sorted_docs[:limit]:
                point = doc_data['point']
                results.append(SearchResult(
                    id=str(point.id),
                    content=point.payload['content'],
                    score=doc_data['rrf_score'],
                    metadata=point.payload['metadata']
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"RRF fusion failed: {e}")
            # 실패 시 dense 결과만 반환
            results = []
            for point in dense_points[:limit]:
                results.append(SearchResult(
                    id=str(point.id),
                    content=point.payload['content'],
                    score=point.score,
                    metadata=point.payload['metadata']
                ))
            return results
    
    
    async def rerank(self, query: str, search_results: List[SearchResult], 
                    options: Dict[str, Any] = None) -> List[SearchResult]:
        """리랭킹 실행"""
        if not self.reranking_config.get('enabled', False) or not search_results:
            return search_results
        
        options = options or {}
        top_k = options.get('top_k', 5)
        min_score = options.get('min_score', 0.4)  # 최소 유사도 임계값 추가
        provider = self.reranking_config.get('default_provider', 'cohere')
        
        self.stats['rerank_requests'] += 1
        
        try:
            logger.debug(f"Reranking {len(search_results)} results with {provider}")
            
            reranked_results = None
            if provider == 'cohere' and 'cohere' in self.rerankers:
                reranked_results = await self._rerank_cohere(query, search_results, top_k)
            elif provider == 'jina' and 'jina' in self.rerankers:
                reranked_results = await self._rerank_jina(query, search_results, top_k)
            elif provider == 'llm':
                reranked_results = await self._rerank_gpt5_nano(query, search_results, top_k)
            else:
                logger.warning(f"Reranker {provider} not available, skipping reranking")
                return search_results
            
            # 리랭킹 후 최소 점수 필터링 적용
            if reranked_results:
                filtered_results = [
                    result for result in reranked_results 
                    if result.score >= min_score
                ]
                logger.info(f"Post-reranking filtering: {len(reranked_results)} -> {len(filtered_results)} results (min_score={min_score})")
                return filtered_results
                
            return search_results
                
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return search_results  # 실패 시 원본 결과 반환
    
    async def _rerank_cohere(self, query: str, results: List[SearchResult], top_k: int) -> List[SearchResult]:
        """Cohere 리랭킹"""
        try:
            cohere_client = self.rerankers['cohere']
            
            # 문서 텍스트 추출
            documents = [result.content for result in results]
            
            # 리랭킹 실행
            rerank_response = await asyncio.to_thread(
                cohere_client.rerank,
                model="rerank-multilingual-v2.0",
                query=query,
                documents=documents,
                top_k=min(top_k, len(documents))
            )
            
            # 결과 재구성
            reranked_results = []
            for rank_result in rerank_response.results:
                original_result = results[rank_result.index]
                original_result.score = rank_result.relevance_score
                reranked_results.append(original_result)
            
            logger.debug(f"Cohere reranking completed: {len(reranked_results)} results")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Cohere reranking failed: {e}")
            return results
    
    async def _rerank_gpt5_nano(self, query: str, results: List[SearchResult], top_k: int) -> List[SearchResult]:
        """GPT-5-nano 기반 리랭킹 (고속 분류 작업 최적화)"""
        try:
            # OpenAI 설정 가져오기 (인스턴스 config 사용)
            llm_config = self.config.get('llm', {}).get('openai', {})
            
            if not llm_config.get('api_key'):
                logger.warning("OpenAI API key not available for GPT-5-nano reranking")
                return results
            
            # OpenAI 클라이언트 사용
            from openai import OpenAI
            client = OpenAI(api_key=llm_config['api_key'])
            
            # 리랭킹용 문서 및 프롬프트 생성
            documents_text = ""
            for i, result in enumerate(results[:12]):  # GPT-5-nano는 더 많은 문서 처리 가능
                # 문서 내용을 더 길게 포함 (300자)
                content_preview = result.content[:300].replace('\n', ' ')
                documents_text += f"\n[{i}] {content_preview}..."
            
            # GPT-5-nano 최적화 프롬프트 (더 명확한 JSON 지시)
            prompt = f"""You are a document ranking expert. Evaluate and rank documents based on their relevance to the query.

Query: "{query}"

Documents:
{documents_text}

Task: Score each document from 0.0 to 1.0 based on relevance to the query.
Select only the top {top_k} most relevant documents.

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{{"results": [{{"index": 0, "score": 0.95}}, {{"index": 2, "score": 0.8}}, {{"index": 1, "score": 0.6}}]}}

Do not include any other text, explanation, or formatting. Only the JSON object."""
            
            # GPT-5-nano 리랭킹 요청 (분류 작업에 최적화된 설정)
            logger.debug(f"Requesting GPT-5-nano reranking for {len(results)} documents")
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-5-nano",  # 고속 분류/순위 작업용
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=800,  # nano 모델용 파라미터
                # GPT-5는 temperature가 고정되므로 설정하지 않음
            )
            
            # 응답 파싱
            response_content = response.choices[0].message.content
            if not response_content:
                logger.warning("GPT-5-nano returned empty response, using original results")
                results.sort(key=lambda x: x.score, reverse=True)
                return results[:top_k]
            
            response_content = response_content.strip()
            logger.info(f"GPT-5-nano raw response: {response_content}")  # 전체 응답 로깅
            
            # JSON 결과 추출 및 파싱
            import json
            import re
            
            # 다양한 JSON 추출 시도
            # 1. 전체가 JSON인 경우
            try:
                rerank_data = json.loads(response_content)
                logger.debug("Successfully parsed entire response as JSON")
            except json.JSONDecodeError:
                # 2. JSON 부분만 추출 (코드 블록이나 다른 텍스트 제거)
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    try:
                        rerank_data = json.loads(json_match.group())
                        logger.debug("Successfully extracted and parsed JSON from response")
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse extracted JSON: {je}")
                        logger.error(f"Extracted text: {json_match.group()[:500]}")
                        # 폴백: 원본 결과 반환 (점수 기준 상위 top_k개)
                        logger.info("Fallback: returning original results sorted by score")
                        results.sort(key=lambda x: x.score, reverse=True)
                        return results[:top_k]
                else:
                    logger.warning("No JSON pattern found in GPT-5-nano response")
                    logger.warning(f"Response was: {response_content[:500]}")
                    # 폴백: 원본 결과 반환
                    results.sort(key=lambda x: x.score, reverse=True)
                    return results[:top_k]
            
            # JSON 파싱 성공 시 결과 처리
            if 'rerank_data' in locals():
                reranked_results = []
                for item in rerank_data.get('results', [])[:top_k]:
                    idx = item.get('index', 0)
                    score = max(0.0, min(1.0, float(item.get('score', 0.5))))  # 0~1 범위 제한
                    
                    if 0 <= idx < len(results):
                        original_result = results[idx]
                        # 새로운 SearchResult 객체 생성 (원본 수정 방지)
                        reranked_result = SearchResult(
                            id=original_result.id,
                            content=original_result.content,
                            score=score,
                            metadata=original_result.metadata
                        )
                        reranked_results.append(reranked_result)
                        logger.debug(f"Reranked doc {idx}: score={score:.3f}")
                
                # 점수순으로 정렬
                reranked_results.sort(key=lambda x: x.score, reverse=True)
                
                logger.info(f"GPT-5-nano reranking completed: {len(results)} -> {len(reranked_results)} results")
                
                # 상위 결과 로깅
                for i, result in enumerate(reranked_results[:3]):
                    logger.debug(f"Top {i+1}: score={result.score:.3f}, content: {result.content[:50]}...")
                
                return reranked_results if reranked_results else results[:top_k]
            else:
                return results[:top_k]
                
        except Exception as e:
            logger.error(f"GPT-5-nano reranking failed: {e}")
            return results
    
    async def _rerank_jina(self, query: str, results: List[SearchResult], top_k: int) -> List[SearchResult]:
        """Jina 리랭킹"""
        try:
            jina_config = self.rerankers['jina']
            
            # HTTP 요청 데이터
            documents = [result.content for result in results]
            
            request_data = {
                "model": jina_config['model'],
                "query": query,
                "documents": documents,
                "top_n": min(top_k, len(documents))
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jina_config['api_key']}"
            }
            
            # HTTP 요청 실행
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    jina_config['endpoint'],
                    json=request_data,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                
                rerank_response = response.json()
            
            # 결과 재구성
            reranked_results = []
            for rank_result in rerank_response['results']:
                original_result = results[rank_result['index']]
                original_result.score = rank_result['relevance_score']
                reranked_results.append(original_result)
            
            logger.debug(f"Jina reranking completed: {len(reranked_results)} results")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Jina reranking failed: {e}")
            return results
    
    async def list_documents(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """문서 목록 조회"""
        try:
            offset = (page - 1) * page_size
            
            # 스크롤로 문서 조회
            scroll_result = await asyncio.to_thread(
                self.qdrant_client.scroll,
                collection_name=self.collection_name,
                limit=page_size,
                offset=offset,
                with_payload=True
            )
            
            points, next_page_offset = scroll_result
            
            documents = []
            unique_docs = {}  # 중복 제거를 위한 딕셔너리
            
            for point in points:
                metadata = point.payload['metadata']
                doc_id = metadata.get('file_hash', str(point.id))
                
                # 중복 문서 체크 및 처리
                if doc_id not in unique_docs:
                    unique_docs[doc_id] = {
                        'id': str(point.id),
                        'filename': metadata.get('source_file', 'unknown'),
                        'file_type': metadata.get('file_type', 'unknown'),
                        'file_size': metadata.get('file_size', 0),
                        'upload_date': metadata.get('load_timestamp', 0),
                        'chunk_count': metadata.get('total_chunks', 1)
                    }
            
            # 고유 문서들만 리스트에 추가
            documents = list(unique_docs.values())
            
            return {
                'documents': documents,
                'total_count': self.stats['total_documents'],
                'page': page,
                'page_size': page_size,
                'has_next': next_page_offset is not None
            }
            
        except Exception as e:
            logger.error(f"List documents failed: {e}")
            return {
                'documents': [],
                'total_count': 0,
                'page': page,
                'page_size': page_size,
                'has_next': False
            }
    
    async def delete_document(self, document_id: str):
        """문서 삭제"""
        try:
            await asyncio.to_thread(
                self.qdrant_client.delete,
                collection_name=self.collection_name,
                points_selector=[document_id]
            )
            
            await self._update_collection_stats()
            logger.info(f"Document deleted: {document_id}")
            
        except Exception as e:
            logger.error(f"Document deletion failed: {e}")
            raise
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """특정 문서의 모든 청크 조회 (순서대로 정렬) - Point ID 기반"""
        try:
            logger.info(f"Retrieving chunks for document: {document_id}")
            
            # 1단계: Point ID로 단일 포인트 조회하여 file_hash 추출
            point_result = await asyncio.to_thread(
                self.qdrant_client.retrieve,
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=True
            )
            
            if not point_result:
                logger.warning(f"No point found for document ID: {document_id}")
                return []
            
            # file_hash 추출
            file_hash = point_result[0].payload['metadata'].get('file_hash')
            if not file_hash:
                logger.error(f"No file_hash found in document {document_id}")
                return []
                
            logger.info(f"Found file_hash {file_hash} for document {document_id}")
            
            # 2단계: file_hash로 모든 청크 조회
            search_result = await asyncio.to_thread(
                self.qdrant_client.scroll,
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.file_hash",
                            match=MatchValue(value=file_hash)
                        )
                    ]
                ),
                limit=10000,  # 충분히 큰 수로 모든 청크 가져오기
                with_payload=True
            )
            
            points = search_result[0]
            if not points:
                logger.warning(f"No chunks found for file_hash: {file_hash}")
                return []
            
            chunks = []
            for point in points:
                chunks.append({
                    'content': point.payload['content'],
                    'metadata': point.payload['metadata']
                })
            
            # chunk_index로 정렬 (순서 보장)
            chunks.sort(key=lambda x: x['metadata'].get('chunk_index', 0))
            
            logger.info(f"Retrieved {len(chunks)} chunks for document: {document_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get document chunks for {document_id}: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        await self._update_collection_stats()
        
        return {
            **self.stats,
            'collection_name': self.collection_name,
            'hybrid_search_enabled': self.hybrid_enabled,
            'dense_weight': self.dense_weight,
            'sparse_weight': self.sparse_weight,
            'reranking_enabled': self.reranking_config.get('enabled', False),
            'available_rerankers': list(self.rerankers.keys()),
            'sparse_embedder_available': self.sparse_embedder is not None
        }
    
    def _preprocess_korean_query(self, query: str) -> str:
        """한국어 쿼리 전처리"""
        import re
        
        # 기본 전처리
        processed = query.strip()
        
        # 숫자 및 특수문자 정규화
        processed = re.sub(r'\s+', ' ', processed)  # 여러 공백을 하나로
        
        # 질문 형식 처리 ("~인가요?", "~인가?" -> 핵심 단어만 추출)
        if '인가' in processed and ('?' in processed or '요' in processed):
            # 질문에서 핵심 단어 추출
            processed = re.sub(r'인가요?\??', '', processed)
            processed = re.sub(r'[?\uc694]', '', processed)
        
        return processed.strip()
    
    def _validate_search_quality(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """검색 결과 품질 검증 및 필터링"""
        if not results:
            return results
        
        # 쿼리의 핵심 키워드 추출
        import re
        query_keywords = set(re.findall(r'[\uac00-\ud7a3]+|\d+', query.lower()))
        
        quality_results = []
        for result in results:
            # 콘텐츠에서 키워드 매칭 여부 확인
            content_keywords = set(re.findall(r'[\uac00-\ud7a3]+|\d+', result.content.lower()))
            
            # 키워드 교집 비율 계산
            if query_keywords:
                intersection = query_keywords.intersection(content_keywords)
                relevance_ratio = len(intersection) / len(query_keywords)
                
                # 유사도 조정 (키워드 매칭 고려)
                adjusted_score = result.score * (0.7 + 0.3 * relevance_ratio)
                result.score = min(1.0, adjusted_score)
                
                # 최소 연관성 임계값
                if relevance_ratio > 0.1 or result.score > 0.7:  # 10% 이상 매칭 또는 높은 유사도
                    quality_results.append(result)
            else:
                quality_results.append(result)  # 키워드가 없으면 모두 포함
        
        logger.info(f"Quality validation: {len(results)} -> {len(quality_results)} results after relevance filtering")
        return quality_results
    
    async def clear_cache(self):
        """캐시 클리어 (현재 구현에서는 통계만 업데이트)"""
        await self._update_collection_stats()
        logger.info("Retrieval cache cleared (stats updated)")
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 상세 정보 조회"""
        try:
            if not self.qdrant_client:
                return {"size_mb": 0, "oldest_document": None, "newest_document": None}
            
            # 컬렉션 정보 조회
            collection_info = await asyncio.to_thread(
                self.qdrant_client.get_collection, self.collection_name
            )
            
            # 컬렉션 크기 추정 (벡터 수 * 평균 벡터 크기)
            vector_count = collection_info.vectors_count or 0
            estimated_size_mb = vector_count * 768 * 4 / (1024 * 1024)  # float32 기준
            
            return {
                "size_mb": round(estimated_size_mb, 2),
                "oldest_document": None,  # 추후 구현 가능
                "newest_document": None   # 추후 구현 가능
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"size_mb": 0, "oldest_document": None, "newest_document": None}
    
    async def delete_all_documents(self) -> bool:
        """
        전체 문서 일괄 삭제 - Qdrant 컬렉션의 모든 벡터 삭제
        
        Returns:
            bool: 컬렉션이 완전히 클리어되었는지 여부
        """
        try:
            if not self.qdrant_client:
                raise Exception("Qdrant client not initialized")
            
            logger.warning(f"Deleting all documents from collection: {self.collection_name}")
            
            # 현재 문서 수 확인 (삭제 전)
            initial_stats = await self.get_stats()
            initial_docs = initial_stats.get('total_documents', 0)
            
            if initial_docs == 0:
                logger.info("No documents to delete - collection is already empty")
                return True
            
            # 방법 1: 컬렉션 재생성 시도
            collection_recreated = False
            try:
                logger.info("Attempting collection recreation method...")
                
                # 먼저 컬렉션 삭제
                await asyncio.to_thread(
                    self.qdrant_client.delete_collection, self.collection_name
                )
                logger.info("Original collection deleted successfully")
                
                # 기본 설정으로 컬렉션 재생성 (가장 안전한 방법)
                await self._init_collection()
                collection_recreated = True
                logger.info("Collection recreated with default settings")
                
            except Exception as recreation_error:
                logger.error(f"Collection recreation failed: {recreation_error}")
                
                # 컬렉션이 삭제되었지만 재생성 실패한 경우
                # 수동으로 기본 컬렉션 생성 시도
                try:
                    logger.warning("Attempting manual collection creation...")
                    
                    # 기본 벡터 설정으로 생성
                    test_embedding = await asyncio.to_thread(
                        self.embedder.embed_query, "test"
                    )
                    dense_size = len(test_embedding)
                    
                    # 벡터 설정 구성 (하이브리드 지원)
                    vectors_config = {
                        "dense": VectorParams(
                            size=dense_size,
                            distance=Distance.COSINE
                        )
                    }
                    
                    # Sparse 벡터 추가 (하이브리드 활성화된 경우)
                    if self.hybrid_enabled:
                        vectors_config["sparse"] = SparseVectorParams()
                        logger.info(f"Manual collection creation with hybrid support: dense({dense_size}) + sparse")
                    else:
                        logger.info(f"Manual collection creation with dense only (size: {dense_size})")
                    
                    # 수동으로 컬렉션 생성
                    await asyncio.to_thread(
                        self.qdrant_client.create_collection,
                        collection_name=self.collection_name,
                        vectors_config=vectors_config
                    )
                    
                    collection_recreated = True
                    logger.info("Manual collection creation successful")
                    
                except Exception as manual_error:
                    logger.error(f"Manual collection creation also failed: {manual_error}")
                    # 컬렉션 재생성 실패했지만 문서는 이미 삭제됨
                    collection_recreated = False
            
            # 방법 2: Fallback - 컬렉션이 여전히 존재하고 포인트가 있다면 개별 삭제
            if not collection_recreated:
                try:
                    logger.warning("Collection recreation failed, attempting individual point deletion...")
                    
                    # 컬렉션 존재 여부 확인
                    await asyncio.to_thread(
                        self.qdrant_client.get_collection, self.collection_name
                    )
                    
                    # 모든 포인트 ID 조회
                    search_results = await asyncio.to_thread(
                        self.qdrant_client.scroll,
                        collection_name=self.collection_name,
                        limit=10000,  # 최대 10,000개씩
                        with_payload=False,
                        with_vectors=False
                    )
                    
                    points = search_results[0]
                    
                    if points:
                        point_ids = [point.id for point in points]
                        
                        # 일괄 삭제
                        await asyncio.to_thread(
                            self.qdrant_client.delete,
                            collection_name=self.collection_name,
                            points_selector=point_ids
                        )
                        
                        logger.info(f"Fallback deletion completed: {len(point_ids)} points deleted")
                    else:
                        logger.info("No points found for individual deletion")
                        
                except Exception as fallback_error:
                    logger.warning(f"Fallback deletion failed (expected if collection was already deleted): {fallback_error}")
                    # 컬렉션이 이미 삭제되었다면 이것은 정상적인 상황
            
            # 통계 재설정 및 최종 확인
            self.stats.update({
                'total_documents': 0,
                'vector_count': 0
            })
            
            # 실제 삭제 확인
            try:
                final_stats = await self.get_stats()
                final_docs = final_stats.get('total_documents', 0)
                
                if final_docs == 0:
                    logger.info(f"✅ All documents successfully deleted: {initial_docs} → 0")
                    return True
                else:
                    logger.warning(f"⚠️ Partial deletion: {initial_docs} → {final_docs} documents remaining")
                    return False
                    
            except Exception as stats_error:
                logger.warning(f"Could not verify final deletion status: {stats_error}")
                # 통계 확인에 실패해도 삭제 작업 자체는 성공했을 수 있음
                logger.info(f"Deletion process completed (initial documents: {initial_docs})")
                return True
            
        except Exception as e:
            logger.error(f"Delete all documents failed completely: {e}")
            raise Exception(f"Failed to delete documents: {e}")
    
    async def recreate_collection(self):
        """컬렉션 재생성 (개발/디버그용)"""
        try:
            if not self.qdrant_client:
                raise Exception("Qdrant client not initialized")
            
            logger.info(f"Recreating collection: {self.collection_name}")
            
            # 기존 컬렉션 삭제
            try:
                await asyncio.to_thread(
                    self.qdrant_client.delete_collection, self.collection_name
                )
            except Exception:
                logger.warning("Collection deletion failed or collection didn't exist")
            
            # 새 컬렉션 생성 (원래 설정 사용)
            await self._init_collection()
            
            logger.info("Collection recreated successfully")
            
        except Exception as e:
            logger.error(f"Failed to recreate collection: {e}")
            raise
    
    async def backup_metadata(self) -> List[Dict[str, Any]]:
        """문서 메타데이터 백업"""
        try:
            if not self.qdrant_client:
                return []
            
            backup_data = []
            
            # 모든 포인트의 메타데이터 조회
            search_results = await asyncio.to_thread(
                self.qdrant_client.scroll,
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            points = search_results[0]
            
            for point in points:
                backup_data.append({
                    "id": str(point.id),
                    "payload": point.payload,
                    "backup_timestamp": datetime.now().isoformat()
                })
            
            logger.info(f"Metadata backup completed: {len(backup_data)} documents")
            return backup_data
            
        except Exception as e:
            logger.error(f"Failed to backup metadata: {e}")
            return []
    
    async def _init_query_expansion(self):
        """쿼리 확장 엔진 초기화"""
        logger.info(f"🔍 Query expansion initialization starting... enabled: {self.query_expansion_enabled}")
        logger.info(f"🔍 Multi query config: {self.multi_query_config}")
        
        if not self.query_expansion_enabled:
            logger.info("❌ Query expansion disabled in configuration")
            return
        
        try:
            logger.info("🚀 Initializing GPT5QueryExpansionEngine...")
            self.query_expansion_engine = GPT5QueryExpansionEngine(self.config)
            logger.info("✅ Query expansion engine initialized successfully")
        except Exception as e:
            logger.error(f"❌ Query expansion engine initialization failed: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.query_expansion_enabled = False
    
    async def expand_query(self, query: str) -> Optional[ExpandedQuery]:
        """쿼리를 확장하여 다중 쿼리를 생성"""
        if not self.query_expansion_enabled or not self.query_expansion_engine:
            return None
        
        try:
            expanded = await self.query_expansion_engine.expand_query(query)
            self.stats['query_expansions'] += 1
            logger.info(f"Query expanded: {query} -> {len(expanded.expanded_queries)} queries")
            return expanded
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return None
    
    def _fuse_multi_query_results(self, all_results: List[SearchResult], expanded_query: ExpandedQuery) -> List[SearchResult]:
        """다중 쿼리 결과를 융합하고 중복을 제거"""
        try:
            # ID별로 결과 그룹화 및 점수 융합
            result_groups = {}
            for result in all_results:
                doc_id = result.id
                if doc_id not in result_groups:
                    result_groups[doc_id] = {
                        'result': result,
                        'scores': [],
                        'queries': []
                    }
                result_groups[doc_id]['scores'].append(result.score)
                result_groups[doc_id]['queries'].append(result.metadata.get('query', ''))
            
            # 융합된 결과 생성
            fused_results = []
            for doc_id, group in result_groups.items():
                # 다양한 융합 전략 사용 가능 (평균, 최대값, RRF 등)
                # 현재는 평균 점수 사용
                avg_score = sum(group['scores']) / len(group['scores'])
                max_score = max(group['scores'])
                
                # 쿼리 다양성에 따른 보너스 점수
                diversity_bonus = len(set(group['queries'])) * 0.05
                final_score = max_score + diversity_bonus
                
                result = group['result']
                result.score = final_score
                result.metadata['multi_query_count'] = len(group['scores'])
                result.metadata['score_details'] = {
                    'avg_score': avg_score,
                    'max_score': max_score,
                    'diversity_bonus': diversity_bonus
                }
                
                fused_results.append(result)
            
            # 점수 기준으로 정렬
            fused_results.sort(key=lambda x: x.score, reverse=True)
            
            return fused_results
            
        except Exception as e:
            logger.error(f"Multi-query fusion failed: {e}")
            # 융합 실패 시 원본 결과 반환
            return all_results