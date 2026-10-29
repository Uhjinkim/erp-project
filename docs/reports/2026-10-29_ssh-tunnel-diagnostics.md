# SSH 터널 반복 종료 진단

- 날짜: 2026-10-29, dev
- 요청: 터널이 자주 끊기는 이유 확인. 실행 중 프로세스 중단·재시작·설정 변경 없음.

## 관찰

사용자 재연결 전에는 127.0.0.1의 5432/6379 리스너가 모두 없었다. 남아 있던 SSH 프로세스는
직접 SSH 세션으로, 명령행에 -L/-R/-D가 없고 ssh -G로 확인한 유효 설정에도 포워딩이 없었다.
해당 세션의 ServerAliveInterval=0이며 DB/Redis 터널 스크립트 세션과 구분해야 한다.

사용자가 다시 연결했다고 응답한 뒤 별도의 ssh -N 및 cloudflared access ssh 프로세스가 나타났고,
두 로컬 포워딩 리스너가 같은 ssh PID에 열렸다. 실제 실행 옵션은 저장소 스크립트와 동일하게
ExitOnForwardFailure=yes, ServerAliveInterval=60, ServerAliveCountMax=3이다.
클라이언트 버전은 OpenSSH 10.5p1 / cloudflared 2026.10.2이다.

Django development 설정을 사용해 읽기 전용 PostgreSQL 트랜잭션의 SELECT 1 및 Redis PING만
두 차례 수행했다. 공유 데이터·환경 비밀값·SSH 대상/사용자/키 경로를 보고서에 기록하지 않는다.

| 점검 | 첫 시도 | 두 번째 시도 |
| --- | --- | --- |
| PostgreSQL SELECT 1 | 성공, 1.99초 | 성공, 0.72초 |
| Redis PING | 성공, 1.08초 | 성공, 1.08초 |

두 차례 검사 후 동일 터널 프로세스와 리스너가 유지됐다. 약 1분 30초의 짧은 관찰이며
장기 연결의 안정성 검증이나 종료 재현을 의미하지 않는다.

macOS의 AC/Battery sleep 설정은 모두 1분이지만, 수집한 최근 절전/복귀 이벤트는 전날 저녁에
집중되어 있다. 이번 반복 종료와 일치하는 이벤트를 확인하지 못해 절전을 원인으로 확정하지 않는다.

## 결론과 미확인 사항

저장소 두 OS의 터널 스크립트는 이미 SSH 애플리케이션 keepalive를 사용한다. 약 3분 동안
응답이 오지 않으면 종료할 수 있다. 현재 스크립트는 exec/단일 ssh 실행이므로 종료 후 자동
재접속하지 않고 종료 사유도 별도 파일에 보관하지 않는다. keepalive는 단절된 연결을 복구하지 않는다.

이번 점검은 터널 부재 및 재연결 후 정상 응답을 확인했지만, 과거 종료의 SSH/cloudflared stderr
기록이나 서버 측 종료 로그가 없어 네트워크 단절, Cloudflare 경로 재시작, 터미널 종료 중 하나로
원인을 확정할 수 없다. 다음 종료의 마지막 오류와 시각이 필요하다. 설정 대기 시간을 늘리는 것만으로
반복 종료를 해결했다고 판단하지 않는다. 자동 재접속은 복구 수단이며 원인 진단과 구분한다.

참고한 공식 자료:
- [OpenSSH ssh_config](https://man.openbsd.org/ssh_config.5): ServerAliveInterval/ServerAliveCountMax 의미.
- [Cloudflare 터널 반복 종료](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/troubleshoot-tunnels/common-errors/#my-tunnel-randomly-disconnects): SSH 장기 연결 경로의 유지보수/재시작 및 idle 연결 관련 진단 권고.

SSH·개발 서버·8080·OS 절전·원격 서비스 설정을 변경하지 않았다. 공유 DB/Redis 쓰기 없음.


## API 호출 시 종료 제보 후속

사용자는 API 호출 뒤 `Connection to <host> closed by remote host`와
`client_loop: send disconnect: Broken pipe`를 보고했다. 이는 SSH 연결 경로가 종료된 증상이며
API 오류 자체가 종료 원인이라는 증거는 아니다. Cloudflare proxy pipe를 사용하므로 원격 sshd와
중간 Cloudflare 전송 경로 중 어느 쪽이 먼저 닫았는지는 이 두 줄만으로 확정할 수 없다.

재연결된 터널의 SSH PID를 250ms 간격으로 관찰하며 실제 `/api/health/`를 호출했다.
Django 8000 직접 1회, nginx 8080 경유 1회, nginx 경유 동시 4회 모두 HTTP 200이었다.
각 응답은 database/redis/workforce connected였으며 관찰 중 같은 SSH 프로세스가 유지됐다.
직렬 소요 2.70/2.51초, 동시 소요 2.60/2.60/4.27/5.21초였다. 사용자 업무 API·인증 요청의
재현이라고 주장하지 않는다. 서버 코드의 상태 점검에는 SSH 종료 명령이 없고 통합 스크립트의
cleanup은 관리 중인 backend/frontend/nginx PID만 대상으로 한다.

구성된 SSH 대상으로 키/에이전트 기반의 BatchMode·비밀번호/키보드 인증 비활성·호스트 검증 유지
진단 접속을 한 번 시도했으나 인증 거부(exit 255)로 서버 로그에 접근하지 못했다. 기존 터널이나
다른 SSH 세션을 조작하지 않았고 비밀번호·키·대상 호스트는 출력하지 않았다.

다음 종료 시 증거를 남기도록 선택형 진단 모드를 추가했다.
- macOS/Linux: ssh-tunnel.sh의 --diagnostic. 환경 파일 인자 앞/뒤 모두 지원.
- Windows: ssh-tunnel.ps1의 -Diagnostic.
- SSH -vv/-E로 사용자 임시 디렉터리에 시작 UTC와 SSH 상세 로그를 기록한다.
  일반 실행과 인증·포워딩·keepalive 설정은 동일하다. cloudflared의 인증 안내는 기존 터미널로
  표시하며 상세 Access 토큰 로그를 별도 수집하지 않는다. 로그는 접속 메타데이터를 포함하므로
  공유 시 가리고 저장소에 추가하지 않는다.
- 현재 실행 연결에는 소급 적용하지 않고 다음 사용자가 실행하는 세션부터 적용한다.

검증: sh -n 및 bash -n 통과, 가짜 ssh/cloudflared로 일반/진단 양 인자 순서/키 경로 공백/
두 포워딩 보존/진단 로그 생성·700 디렉터리/잘못된 인자 거부를 실제 셸 실행으로 검증했다.
이 검증은 네트워크에 접속하지 않는다. PowerShell 실행기가 없어 Windows 런타임 검증은 미실행이다.
기존 README의 실행 지침에 진단 옵션을 추가했고 종료 원인은 여전히 미확정임을 유지한다.
