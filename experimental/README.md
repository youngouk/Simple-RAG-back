# 실험적 코드 모음 (Experimental Code Collection)

이 폴더는 RAG 시스템 개발 과정에서 연구되고 실험된 고급 기능들을 포함합니다.

## 📁 파일 구성

### 🔬 동적 임계값 시스템
- **`dynamic_threshold_design.py`**: 기본 동적 임계값 조정 시스템
- **`dynamic_threshold_system_detailed.py`**: 고급 동적 임계값 시스템 (통계 기반)

### 📄 문서 처리 연구
- **`semantic_chunking_strategy.py`**: 시맨틱 청킹 전략 (현재는 `app/modules/document_processing.py`에 통합됨)

### ⚡ 성능 최적화 연구
- **`performance_optimization_error_handling.py`**: 고급 캐싱, 회로 차단기, 에러 처리 시스템

### 🏗️ 시스템 아키텍처 연구
- **`system_integration_design.py`**: 전체 시스템 통합 및 플로우 설계

## ⚠️ 주의사항

1. **실험적 코드**: 이 폴더의 모든 코드는 실험적 성격으로, 프로덕션 환경에 직접 적용되지 않습니다.

2. **일부 기능 통합됨**: 
   - 쿼리 확장 → `app/modules/query_expansion.py`
   - 시맨틱 청킹 → `app/modules/document_processing.py`

3. **안정성 검증 필요**: 실제 적용 전 충분한 테스트와 검증이 필요합니다.

4. **복잡도 고려**: 고급 기능들은 시스템 복잡도를 증가시킬 수 있습니다.

## 🎯 향후 활용 방안

- 성능 개선이 필요한 시점에 선택적으로 적용
- 새로운 기능 개발 시 참고 자료로 활용
- 아키텍처 설계 시 레퍼런스로 사용

## 🔍 현재 운영 중인 시스템

실제 운영 중인 코드는 다음 위치에 있습니다:
- **메인 애플리케이션**: `app/` 폴더
- **API 엔드포인트**: `app/api/`
- **핵심 모듈**: `app/modules/`
- **설정**: `app/config/`