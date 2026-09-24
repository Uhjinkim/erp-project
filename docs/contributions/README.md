# 기능 브랜치 문서 기여 규칙

기능 브랜치에서는 공용 명세를 직접 수정하지 않고 다음 경로에 구현 중 발견한 결정과 변경 후보를
기록한다.

```text
docs/contributions/<module>/<branch-slug>/README.md
```

예:

```text
docs/contributions/payroll/feature-payroll-confirmation/README.md
```

초안은 `./scripts/docs-workflow.sh init <module>` 또는
`.\scripts\docs-workflow.ps1 init <module>`로 생성한다. 브랜치 이름은 스크립트가 충돌 없는 경로
문자열로 변환한다.

## 작성 원칙

- 구현 범위, 확정한 설계, API·스키마 영향, 테스트 결과와 공용 문서 반영 후보를 기록한다.
- 개인정보, 자격증명, 실제 급여·계좌 데이터와 환경파일 값은 기록하지 않는다.
- `docs/specs/`, `docs/reports/`, `docs/guides/`, 루트 `README.md`는 기능 브랜치에서 직접 수정하지 않는다.
- Notion 원문과 저장소의 공용 명세 갱신은 문서 담당자가 `dev`에서 수행한다.
- 공용 문서에 반영된 초안은 후속 `dev` 변경에서 삭제한다. Git 이력은 그대로 남는다.

전체 브랜치 및 병합 절차는 [기능 모듈 브랜치·문서 협업 가이드](../guides/module-branch-docs-workflow.md)를
따른다.
