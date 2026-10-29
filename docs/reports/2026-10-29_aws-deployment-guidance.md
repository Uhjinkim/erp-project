# 빈 Ubuntu EC2 · GitHub Actions 배포 안내

- 일자: 2026-10-29
- 사용자 조건: Ubuntu 26.04.1 EC2 미설정, GitHub Actions 사용, 운영 .env 배포 제외.

현재 Dockerfile/Compose/systemd/production 설정과 legacy state-only migration을 읽고
[설치·권한·기동 준비 안내](../guides/github-actions-aws-deployment.md)를 작성했다.
기존 README/EC2 가이드의 서버 env 파일 경로를 현재 구현 설명으로 구분해 연결했다.

공식 Docker Ubuntu 지원 목록의 26.04와 AWS SSM OS 목록의 26.04 미기재를 구분했다.
SSM 등록을 실제 검증하기 전 지원/자동 배포 가능을 확정하지 않는다. Secrets Manager 조회는
EC2 역할, GitHub는 OIDC로 ECR/배포 역할을 사용하도록 설계했으며 비밀은 CI를 거치지 않는다.

Actions workflow, ECR image 참조, Compose 환경변수 매핑, 호스트 Secret launcher/systemd 변경은
필요한 구현으로만 명시했다. 해당 코드가 구현·검증되었다고 주장하지 않았다. 빈 RDS는 별도
승인된 baseline/기준정보/migration 대응표 없이는 첫 기동할 수 없음을 기존 가이드와 일치시켰다.

검증: 로컬 문서 링크 확인, shell 코드 블록 bash -n 검사, git diff --check.
실제 Ubuntu 설치·SSM 연결·AWS IAM/Secret/ECR/S3 변경·공유 DB 쓰기·서비스 배포 없음.
문서 변경만 수행하여 백엔드/프론트 테스트는 재실행하지 않았다.
