# Cloudflared SSH 터널 전환 · 2026-10-22

## 변경

사용자의 cloudflared 경유 SSH 전환 요청에 따라 macOS/Linux·Windows 터널 스크립트를 수정했다. 기존 dev 작업 트리의 다른 구현/문서와 staged 변경은 보존했다. commit/push는 수행하지 않았다.

- OpenSSH에 ProxyCommand=cloudflared access ssh --hostname %h를 전달한다. cloudflared는 PATH에서 실행하며 설치되어 있지 않으면 SSH를 실행하기 전에 안내 후 종료한다.
- SSH_HOST는 Cloudflare SSH 공개 호스트명 또는 해당 HostName을 가리키는 SSH 별칭이다. URL·셸 문자가 있는 값은 ProxyCommand 확장 전에 거절한다. 기존 서버 IP에서 전환 시 공개 호스트명으로 바꿔야 한다.
- 기존 SSH_USER·개인 키·keepalive·포워딩 실패 처리와 PostgreSQL/Redis -L 옵션을 유지한다. 별도 로컬 cloudflared TCP 리스너를 추가하지 않는다.
- SSH_PORT는 별도 안내가 없으면 22다. 원격 SSH 서비스 포트는 Cloudflare Tunnel 서버 측 경로의 책임이다. 브라우저 Access 인증 뒤 기존 SSH 인증을 진행한다.
- .env.example과 README에 설치·호스트 입력·인증·실행 방법을 반영했다. 실제 환경 파일·SSH 설정·자격증명은 수정하거나 출력하지 않았다. 새 환경변수는 추가하지 않았다.

## 검증

- sh -n scripts/ssh-tunnel.sh 통과.
- 네트워크 없는 임시 SSH 대역으로 15개 확인: 기본 ProxyCommand/두 포워딩, 실제 OpenSSH -G 해석, 사용자 지정 포트·원격 DB 호스트·공백 포함 키 경로, CRLF, SSH 종료 코드 전달, 부적절한 호스트 6종, 잘못된 포트, 이전 변수명 거절, 필수값 누락, cloudflared 누락.
- bash -n scripts/start-dev.sh, start-dev.sh --check 및 bash -n scripts/docs-workflow.sh 통과. nginx 구성 유효.
- Windows 스크립트는 같은 인수·의존성 검사를 정적 검토했다. 이 호스트에 pwsh가 없어 PowerShell/Windows 실제 실행은 미검증이다.
- 실제 Access 브라우저 인증·원격 SSH 접속·포워딩 개통은 이번 검증에서 수행하지 않았다. 공유 DB/Redis 접속·migration·데이터 변경은 없다. 앱 코드/의존성 변화가 없어 backend/frontend 전체 테스트는 반복하지 않았다.

## 실행

인프라 담당자의 Cloudflare 공개 호스트명을 루트 .env의 SSH_HOST에 설정하고 cloudflared를 PATH에 설치한 후 기존 명령을 실행한다.

```bash
./scripts/ssh-tunnel.sh
```

```powershell
.\scripts\ssh-tunnel.ps1
```

Access 인증이 필요하면 브라우저 인증을 완료하고 기존 SSH 키/비밀번호로 서버 인증을 진행한다. 로컬 DB/Redis 포트를 변경하지 않았다면 Backend 접속 설정은 유지한다. 터미널을 열어 둔 채 통합 개발 스크립트를 실행한다. 상세는 [개발 설정](../../README.md)을 따른다.

## 근거

- [Cloudflare 공식 SSH 연결](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/ssh-cloudflared-authentication/)
- [Cloudflared 공식 다운로드](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)
- [WinGet cloudflared 패키지](https://github.com/microsoft/winget-pkgs/tree/master/manifests/c/Cloudflare/cloudflared)
