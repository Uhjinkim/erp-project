# AWS 배포 실행 파일

`main` CI/CD의 운영 계약은 [실행 가이드](../../docs/guides/aws-main-cicd.md)에 기록한다.
기존 Cloudflare/env-file Compose 경로와 별도이며 `compose.yml`은 ECR SHA 이미지만 실행한다.

`asm_exec.py`는 AWS Core 1.0.0 `aws-secrets-manager/references/asm-exec`를 바탕으로 한다.
원본의 동적 참조 문법과 단일 치환을 유지하고 환경변수 치환·SSRF token 파일·인증된 ping을 추가했다.
운영은 로컬 provider만 사용하고, 실패 시 응답 원문 대신 상태 코드·오류 분류만 기록한다.
AWS Workload Credentials Provider를 로컬에서 실행해 비밀값은 wrapper와 자식 프로세스에만 전달한다.
Agent나 운영자가 값을 출력하는 진단은 실행하지 않는다. Secret을 수정하려면 AWS 콘솔을 사용한다.
컨테이너 운영 권한을 가진 사용자는 컨테이너 환경변수를 볼 수 있으므로 `erp` 접근을 제한한다.

`create-database.psql`은 신규 DB/role 준비를 위한 검토용 SQL이다. CI/CD에서 실행하지 않는다.
대상·관리자 인증·복구 지점·쓰기 승인을 확인한 뒤 별도 앱 Secret과 `psql -X`로만 사용한다.
업무 schema baseline은 별도이며, SQL 검증과 미해결 사항은
[10-30 재개 보고서](../../docs/reports/2026-10-30_aws-deployment-resume.md)에 기록한다.
