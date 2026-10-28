# Sprint 2 - API & CI Foundation

Sprint dates: October 22 - November 4, 2026.
Goal: Enhance Orders functionality, establish reliable CI checks, and deploy the service to a local Kubernetes cluster.

## Backlog

| GitHub issue | Story | Estimate |
| --- | --- | --- |
| #36 | Existing model-level order filtering story | 1 SP |
| #37 | Existing filtering API story | 1 SP |
| #38 | Existing filtering API tests story | 1 SP |
| #39 | Cancel an eligible order | 3 SP |
| #40 | GitHub Actions tests and lint | 3 SP |
| #41 | Codecov integration | 2 SP |
| #42 | Health endpoint and container build | 2 SP |
| #43 | PostgreSQL StatefulSet and persistence | 3 SP |
| #44 | Orders Deployment, Service and Ingress | 5 SP |

Total: 21 SP. Preserve the three existing story identities. All stories remain open for remaining acceptance and teammate review.

## Implementation checkpoint

Branch: feature/sprint2-foundation. Published as [PR #45](https://github.com/CSCI-GA-2820-FA26-003/orders/pull/45). GitHub Actions tests/lint and the Codecov PR patch check passed on the published application source; details are recorded below.

- Status filtering now uses Order.find_by_status. No query returns all orders. Exact enum names NEW, SHIPPED, DELIVERED and CANCELLED are supported; invalid/empty/repeated status or unsupported query keys return JSON 400.
- Cancellation persists NEW to CANCELLED, returns 404/409 JSON errors, preserves items and treats repeated cancellation as a no-op.
- /health returns 200 with {"status":"OK"}.
- CI configuration runs PostgreSQL tests, flake8 and pylint with a 95% coverage gate and Codecov upload/badges.
- Production Dockerfile, image defaults, PostgreSQL StatefulSet/PVC, application Deployment/Service/Ingress, registry mapping and deployment script are present.
- Makefile now allows isolated registry name/port/config and ingress port overrides. The deployment output honors the selected ingress port.
- Automated external verification scripts and README instructions cover PostgreSQL/image/HTTP checks and the next K3s acceptance run.

## Verification observed on October 28, 2026

| Check | Result | Scope |
| --- | --- | --- |
| Current unit suite | Passed on PostgreSQL 15 and SQLite | Updated 142-method suite including filtering; PostgreSQL JUnit records 223 cases including subtests, zero failures/errors/skips |
| Current coverage | 99.02% (506 / 511 lines) | Confirmed on PostgreSQL 15 and SQLite; routes and Order model both 100% |
| Current flake8 / pylint | Passed; pylint 10.00 / 10 | service and tests |
| Latest PostgreSQL quality run | Passed | Locked Linux dependencies, lint, the updated suite and coverage gate: .test-tmp/postgres-c5f07cdd5c72/ |
| Current Docker image and HTTP run | Passed | Latest Dockerfile/source: health, create, cancel, repeat cancel, mixed-status filtering, JSON 400/404/409, and direct database container restart persistence |
| Restart harness correction | Confirmed in a successful external rerun | Host port changed from 61051 to 61057 on app restart; rediscovering it fixed the old timeout. Direct psql and HTTP confirmed the cancelled row remained. |
| Current HTTP helper logic | Passed against actual loopback HTTP on isolated SQLite | Mixed statuses, strict filtering/errors, saved order/item equality and DELETE. This was not a Kubernetes or database restart run. |
| Kubernetes schemas | 7 resources passed | Static validation against official Kubernetes v1.32 OpenAPI |
| make cluster | Passed | K3d v5.9.0 created orders-s2-4a89a37ebf; K3s v1.35.5 server and agent both Ready |
| make build / make push | Passed | localhost:48163/orders:sprint2 pushed, digest sha256:a031a8aeb423912316adaabe15a48268e88780f06fe87d59d375715ca5daa3f8 |
| PostgreSQL StatefulSet / PVC persistence | Passed | PostgreSQL Pod UID changed; PVC and PV identities stayed the same; cancelled order and item values survived the restart and another deployment |
| make deploy / ingress API | Passed on resumed cluster | Orders and PostgreSQL Pods both 1/1 Running; health, CRUD, mixed-status filtering, cancellation, JSON 400/404/409 and DELETE passed through Traefik ingress |
| Image substitution / repeated deployment | Passed | Requested image deployed successfully; repeated make deploy reused the same database Secret and retained the saved order/item values |
| Deployment / K3s runner syntax | Passed | Tree-sitter Bash parser; native Bash execution unavailable in this assistant session |
| PowerShell launchers / Python syntax / Git whitespace | Passed | Current scripts and modified source |
| GitHub Actions | Passed | Run 40730224809: 142 tests, coverage 99.02%, flake8 passed, pylint 10.00/10, Codecov upload succeeded |
| Codecov PR report | Passed | PR #45 codecov/patch: 100.00% changed-line coverage against the 95.00% target; Codecov bot report appeared |
| Fresh Kubernetes CI acceptance | Configured | Subsequent CI runs execute the same make/Ingress/Pod/PVC acceptance script on a fresh GitHub runner and retain allowlisted reports |

Saved external run evidence:

- .test-tmp/postgres-6c9240a0b2cc/: PostgreSQL coverage.xml, junit.xml and verification.log.
- .test-tmp/postgres-cd9264997299/: successful image/HTTP/container-restart verification.log.
- .test-tmp/postgres-c5f07cdd5c72/: latest PostgreSQL 99.02% coverage, zero-failure JUnit, image/HTTP/filter/restart checks passed.
- .test-tmp/kubernetes-34822d1be765/: launcher stopped during Linux snapshot preparation, before any K3s creation; native stderr was absent from the old transcript.
- .test-tmp/kubernetes-bc80a18b915d/: actual cluster/build/push and initial registry DNS failure.
- .test-tmp/kubernetes-156d948e87ca/: successful resumed K3s verification.log, resources.txt and connection.txt.
- .test-tmp/sqlite-coverage.xml: current 142-test coverage.

The first filtering smoke check was insufficient: only a CANCELLED order existed at query time, so returning all orders passed. Source review confirmed that status was ignored. The follow-up implements stories #36-38 and adds mixed-status controls to both unit and external HTTP checks. Do not treat the earlier external run as evidence that filtering was implemented.

## Next acceptance run

From normal Windows PowerShell with Docker access:

    powershell -NoProfile -File "D:\codex\devoops\orders\scripts\verify-kubernetes.ps1"

The launcher uses the existing nyu-project development container (override with -Container NAME). It first reruns the updated PostgreSQL suite, lint, image build and HTTP checks, then copies current deployment inputs into an isolated Linux snapshot and runs actual make cluster/build/push/deploy targets.

The K3s runner uses unique cluster/registry names, free local ports and a private kubeconfig. Checks include ingress API access, IMAGE override, PostgreSQL availability/database orders, a recreated PostgreSQL Pod with unchanged PVC/PV identities, preserved order/item values, and repeated deployment reusing the same database Secret. It retains any created cluster for inspection and copies reports back to .test-tmp/kubernetes-<run-id>/. Kubeconfig and Secret values are not copied into the report bundle. Its ingress is inside the development container; Windows browser access requires VS Code port forwarding.

The first K3s run (.test-tmp/kubernetes-bc80a18b915d/) passed cluster/build/push and PostgreSQL startup, then failed on the extra registry-hostname prefix. The resumed run (.test-tmp/kubernetes-156d948e87ca/) corrected registry aliases and passed deployment, all ingress/API checks, PostgreSQL Pod/PVC persistence and repeated deployment. Orders and PostgreSQL both finished 1/1 Running, with data-postgres-0 Bound to its original 1 GiB local-path PV. Use -SkipPostgres for repeat K3s-only checks.

## Verification scope and environment

- Docker Desktop is running and normal PowerShell can access it. This assistant session receives permission denied on the dockerDesktopLinuxEngine pipe under a Low Mandatory Level token; sandbox approvals are disabled. The user must launch the prepared external commands. The assistant can then read their saved reports and fix failures.
- The 142-test filtering follow-up passed PostgreSQL/image verification locally and the real GitHub Actions quality job.
- Exec-based source/report transfer is now proven in the real development container. Docker 29.9.0, k3d 5.9.0, make 4.4.1 and kubectl are available there.
- Registry DNS recovery passed on the retained cluster. Fresh runs use matching explicit registry names, including default k3d-cluster-registry. CI now runs fresh Kubernetes acceptance automatically; consult the PR's Kubernetes acceptance check for its latest outcome.
- The launcher now supports -ResumeRun bc80a18b915d. It validates prior saved metadata and unchanged image inputs, repairs aliases only on that owned registry/cluster network, restarts the pending Orders Deployment to trigger a fresh pull, and continues deployment/API/Pod/PVC checks without recreating the cluster or image. No registry data or PostgreSQL data is deleted. The actual resumed run completed with Result: PASSED.
- Kubernetes ingress/API, application-to-PostgreSQL connectivity and Pod/PVC restart persistence passed inside the development container. Windows browser access via VS Code port forwarding remains unverified.
- GitHub publication succeeded through the connected GitHub API after its write access became available. Invalid CLI credentials no longer block this PR. GitHub Actions and Codecov results were observed directly.

Use Refs #... in PR descriptions and avoid auto-closing stories before sprint review.

Static schema source: https://raw.githubusercontent.com/kubernetes/kubernetes/v1.32.0/api/openapi-spec/swagger.json
Registry CLI reference: https://k3d.io/v5.4.9/usage/commands/k3d_cluster_create/

To resume the retained verification cluster after the registry naming fix:

    powershell -NoProfile -File "D:\codex\devoops\orders\scripts\verify-kubernetes.ps1" -SkipPostgres -ResumeRun bc80a18b915d

The registry network is briefly disconnected/reconnected with corrected aliases. The registry image store and PostgreSQL PVC are retained. The resume path verifies existing image inputs against the old snapshot before reusing the image. Fresh runs use corrected explicit registry naming directly.

## GitHub publication and CI evidence

[PR #45](https://github.com/CSCI-GA-2820-FA26-003/orders/pull/45) targets master and references stories #36-44 without closing them. The connected GitHub API published commit 4de2fb5; its tree 37328852bd104232f0e09609ce78b58a38c291db exactly matches the locally verified source. Local implementation history is preserved on feature/sprint2-local-history, and feature/sprint2-foundation tracks the published branch.

[GitHub Actions run 40730224809](https://github.com/CSCI-GA-2820-FA26-003/orders/actions/runs/40730224809) completed successfully:
- 142 tests passed on PostgreSQL 15; coverage 99.02% (506/511 lines).
- flake8 passed; pylint scored 10.00/10.
- Codecov upload using the existing CODECOV_TOKEN succeeded.
- [Codecov PR report](https://app.codecov.io/gh/CSCI-GA-2820-FA26-003/orders/pull/45) appeared with a successful 100.00% patch check (95.00% target).
- Codecov's welcome comment notes that default-branch baseline comparisons become available after the first merge.

CI additionally runs a fresh K3s acceptance job after quality checks. It installs k3d v5.9.0 with the release asset's SHA-256 verified, executes scripts/verify-kubernetes.sh, and uploads only verification.log, resources.txt and available-replicas.txt. Kubeconfig and Secret values are excluded. The job checks actual make cluster/build/push/deploy, Ingress/API behavior, PostgreSQL connectivity, Pod recreation with the same PVC/PV, and data/Secret persistence across repeated deployment.

The Windows publication launcher remains available as an optional GitHub CLI fallback. No further user login was needed for the connected API publication. Keep stories open for teammate/sprint review.
