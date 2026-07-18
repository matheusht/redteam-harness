# GHSA fix-diff corpus (real disclosed advisories -> the code delta that fixed them, per bug class)

Sibling to `severity-precedent-corpus.md`. That corpus mines the CVSS *vector* a bug class earned; this one mines the *code delta* that fixed it — the vulnerable pre-patch shape (removed lines) and the guard the fix adds (added lines). Every hunk below is copied verbatim from a re-fetchable primary-source fix commit (OSV GIT-range `fixed` SHA or the GHSA-linked commit/PR). **Not a live-bug claim** — every anchor is a *fixed* bug; a target matching a removed-line shape is a lead to investigate through the funnel, never a confirmation. Do not present a patched bug as a finding.

Provenance flag per anchor: `re-verified-this-session` = OSV record + diff fetched this run; `second-hand-reverify-before-citing` = surfaced via search, re-verify the exact commit before citing.

## SSRF  (CWE-918)

Grounds cards: skills/patterns/ssrf-server-side-fetch, skills/vulns/information-disclosure
Bucket verdict: **THIN -- 5 clean IN anchors (grafana, plane, new-api, axios, next.js), one short of the >=6 threshold, plus 2 CONTESTED (SuiteCRM, parse-server) kept as illustrative deletion-fixes. Dominant guard shape for the class is a pre-fetch destination check inserted right before the outbound sink -- either a destination allowlist / filter (bound: plane, new-api) or input canonicalization/format-constraint (grafana MD5 regex, axios scheme-mandatory regex) -- with param-binding (next.js trusted-host) and outright sink-removal (SuiteCRM, parse-server) as the minority variants.**  ·  5 IN / 2 CONTESTED / 9 dropped  ·  5 promotable signatures
Severity-corpus join: Joins the same-class SSRF (CWE-918) severity-corpus bucket: all are Network-AV / Low-AC outbound-fetch bugs whose vectors span Medium (authenticated fetch-and-echo proxy: SuiteCRM, parse-server, plane) up to High/Critical when unauthenticated or reaching cloud metadata for credential theft (grafana unauth avatar; new-api 169.254.169.254) -- use these to anchor the SSRF bucket's PR:L/PR:N and C-impact spread.

- **CVE-2020-13379 (GHSA-wc9w-wvq2-ffm9)** — CWE-918 · `grafana/grafana` · fixed 6.7.4 / 7.0.2 @ `ba953be95f0302c2ea80d23f1e5f2c1847365192` · **IN** (signature) · canonicalization
  - Mechanism: Grafana's unauthenticated avatar handler took the trailing URL-path segment verbatim as the gravatar 'hash' and used it to build the outbound fetch URL/cache key; with no format constraint an attacker could supply arbitrary content in that segment to make Grafana issue a request to an attacker-chosen target and echo the response, enabling internal network reconnaissance.
  - Affected -> Fixed: 3.0.1 - 6.7.3, 7.0.0 - 7.0.1 -> 6.7.4 / 7.0.2
  - Vulnerable shape (removed):
    ```
    func (this *CacheServer) Handler(ctx *macaron.Context) {
    	urlPath := ctx.Req.URL.Path
    	hash := urlPath[strings.LastIndex(urlPath, "/")+1:]
    ```
  - Guard added (post-patch):
    ```
    var validMD5 = regexp.MustCompile("^[a-fA-F0-9]{32}$")
    
    func (this *CacheServer) Handler(ctx *models.ReqContext) {
    	hash := ctx.Params("hash")
    
    	if len(hash) != 32 || !validMD5.MatchString(hash) {
    		ctx.JsonApiErr(404, "Avatar not found", nil)
    		return
    	}
    ```
  - Reachability: pkg/api/avatar.CacheServer.Handler, reached via any unauthenticated request to the avatar endpoint (/avatar/<value>)
  - Verdict: IN — Re-fetched the commit this session; the removed->added delta matches verbatim. Clean, isolable input-canonicalization guard: a 32-hex-char MD5 regex is applied to the path-derived hash before it is used to build the outbound gravatar fetch, so arbitrary content can no longer be injected into the request target. Unauthenticated fetch-and-echo SSRF matches CWE-918.
  - Source: https://api.osv.dev/v1/vulns/GHSA-wc9w-wvq2-ffm9 ; https://nvd.nist.gov/vuln/detail/CVE-2020-13379 ; https://github.com/grafana/grafana/commit/ba953be95f0302c2ea80d23f1e5f2c1847365192.diff  ·  provenance: re-verified-this-session

- **CVE-2024-31461 (GHSA-j77v-w36v-63v6)** — CWE-918 · `makeplane/plane` · fixed 0.17-dev @ `4b0ccea1461b7ca38761dfe0d0f07c2f94425005` · **IN** (signature) · bound
  - Mechanism: The Jira-importer endpoint accepted an attacker-supplied 'hostname'/'cloud_hostname' field and the server itself issued HTTP requests to that host with no destination check, letting the importer be turned into an open proxy against arbitrary internal/external hosts.
  - Affected -> Fixed: < 0.17-dev -> 0.17-dev
  - Vulnerable shape (removed):
    ```
    def jira_project_issue_summary(email, api_token, project_key, hostname):
        try:
            auth = HTTPBasicAuth(email, api_token)
            headers = {"Accept": "application/json"}
    
            issue_url = f"https://{hostname}/rest/api/3/search?jql=project={project_key} AND issuetype=Story"
    ```
  - Guard added (post-patch):
    ```
    def is_allowed_hostname(hostname):
        allowed_lists = ["atl-paas.net", "atlassian.com", "atlassian.net", "jira.com"]
        parsed_uri = urlparse(f"https://{hostname}")
        domain = parsed_uri.netloc.split(":")[0]
        base_domain = ".".join(domain.split(".")[-2:])
        return base_domain in allowed_lists
    
    
    def jira_project_issue_summary(email, api_token, project_key, hostname):
        try:
            if not is_allowed_hostname(hostname):
                print("Errored Hostname")
                return {"error": "Invalid or unauthorized hostname"}
    ```
  - Reachability: apiserver/plane/utils/importers/jira.py jira_project_issue_summary(hostname) and apiserver/plane/app/views/importer.py ImportServiceEndpoint.post (metadata['cloud_hostname']), reached via the workspace Jira-import API by an authenticated workspace admin
  - Verdict: IN — Re-fetched this session; delta matches verbatim. Clean, isolable destination-allowlist (bound) guard: is_allowed_hostname() restricts the base domain to a fixed set of Atlassian hosts and is invoked before the outbound request in jira_project_issue_summary(). Attacker-hostname SSRF matches CWE-918.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-31461 ; https://github.com/makeplane/plane/security/advisories/GHSA-j77v-w36v-63v6 ; https://github.com/makeplane/plane/commit/4b0ccea1461b7ca38761dfe0d0f07c2f94425005.diff  ·  provenance: re-verified-this-session

- **CVE-2025-59146 (GHSA-xxv6-m6fx-vfhh)** — CWE-918 · `QuantumNous/new-api` · fixed 0.9.0.5 @ `ef634160986c6f6b087cbfe131074fda862928af` · **IN** (signature) · bound
  - Mechanism: Any authenticated user could submit a URL for the LLM-gateway server to fetch/process (not limited to images); the server issued the outbound request with no destination validation, allowing pivoting to internal services and the cloud metadata endpoint (169.254.169.254) to steal credentials.
  - Affected -> Fixed: < 0.9.0.5 -> 0.9.0.5
  - Vulnerable shape (removed):
    ```
    	common.SysLog(fmt.Sprintf("downloading from origin with worker: %s, reason: %s", originUrl, strings.Join(reason, ", ")))
    		return http.Get(originUrl)
    ```
  - Guard added (post-patch):
    ```
    		// SSRF防护：验证请求URL（非Worker模式）
    		fetchSetting := system_setting.GetFetchSetting()
    		if err := common.ValidateURLWithFetchSetting(originUrl, fetchSetting.EnableSSRFProtection, fetchSetting.AllowPrivateIp, fetchSetting.DomainFilterMode, fetchSetting.IpFilterMode, fetchSetting.DomainList, fetchSetting.IpList, fetchSetting.AllowedPorts, fetchSetting.ApplyIPFilterForDomain); err != nil {
    			return nil, fmt.Errorf("request reject: %v", err)
    		}
    
    		common.SysLog(fmt.Sprintf("downloading from origin: %s, reason: %s", common.MaskSensitiveInfo(originUrl), strings.Join(reason, ", ")))
    		return http.Get(originUrl)
    ```
  - Reachability: service/download.go DoDownloadRequest(originUrl) (and equivalents in service/webhook.go, service/user_notify.go), reached via any authenticated-user-triggered fetch/webhook/notify path that lets the caller choose the target URL
  - Verdict: IN — Re-fetched this session; delta matches verbatim. Clean, isolable destination-filter (bound) guard: common.ValidateURLWithFetchSetting(originUrl, ...) is inserted immediately before the direct http.Get(originUrl) sink, enforcing SSRF protection / private-IP + domain/IP filtering on the caller-chosen URL. Metadata-endpoint credential-theft SSRF matches CWE-918.
  - Source: https://api.osv.dev/v1/vulns/CVE-2025-59146 ; https://github.com/QuantumNous/new-api/security/advisories/GHSA-xxv6-m6fx-vfhh ; https://github.com/QuantumNous/new-api/commit/ef634160986c6f6b087cbfe131074fda862928af.diff  ·  provenance: re-verified-this-session

- **CVE-2024-39338 (GHSA-8hc4-vh64-cxmj)** — CWE-918 · `axios/axios` · fixed 1.7.4 @ `07a661a2a6b9092c4aa640dcc7f724ec5e65bdda` · **IN** (signature) · canonicalization
  - Mechanism: isAbsoluteURL() treated protocol-relative paths ('//host') as already-absolute (the scheme portion of the regex was optional), so when a caller built a request path from attacker-controlled input that collapsed to '//attacker-host', buildFullPath() skipped combining it with the configured baseURL and axios/the underlying HTTP client resolved it straight to the attacker's host instead of the intended base host.
  - Affected -> Fixed: 1.3.2 - 1.7.3 -> 1.7.4
  - Vulnerable shape (removed):
    ```
      // A URL is considered absolute if it begins with "<scheme>://" or "//" (protocol-relative URL).
      return /^([a-z][a-z\d+\-.]*:)?\/\//i.test(url);
    ```
  - Guard added (post-patch):
    ```
      // A URL is considered absolute if it begins with "<scheme>://".
      return /^([a-z][a-z\d+\-.]*:)\/\//i.test(url);
    ```
  - Reachability: lib/helpers/isAbsoluteURL.js isAbsoluteURL(url), consumed by lib/core/buildFullPath.js when merging a request path with a configured baseURL, reached whenever a request path is built from a partially attacker-controlled path segment
  - Verdict: IN — Re-fetched this session; delta matches verbatim. Textbook single-token canonicalization/exact-match swap: the scheme capture group is made mandatory by removing the trailing '?', so a protocol-relative '//host' is no longer classified as absolute and baseURL merging is no longer skipped. baseURL-bypass SSRF matches CWE-918.
  - Source: https://api.osv.dev/v1/vulns/GHSA-8hc4-vh64-cxmj ; https://api.osv.dev/v1/vulns/CVE-2024-39338 ; https://github.com/axios/axios/commit/07a661a2a6b9092c4aa640dcc7f724ec5e65bdda.diff  ·  provenance: re-verified-this-session

- **CVE-2024-34351 (GHSA-fr5h-rqp8-mj6g)** — CWE-918 · `vercel/next.js` · fixed 14.1.1 @ `8f7a6ca7d21a97bc9f7a1bbe10427b5ad74b9085` · **IN** (signature) · param-binding
  - Mechanism: When a Server Action performed a redirect to a relative path, the self-hosted server rebuilt the internal fetch URL using the incoming (attacker-controllable) Host request header as the target host, letting an attacker who modifies the Host header make the server issue a request that appears to originate from itself, effectively an SSRF via a spoofed Host header.
  - Affected -> Fixed: 13.4.0 - 14.1.0 -> 14.1.1
  - Vulnerable shape (removed):
    ```
        const host = originalHost.value
        const proto =
          staticGenerationStore.incrementalCache?.requestProtocol || 'https'
    ```
  - Guard added (post-patch):
    ```
        const proto =
          staticGenerationStore.incrementalCache?.requestProtocol || 'https'
    
        // For standalone or the serverful mode, use the internal hostname directly
        // other than the headers from the request.
        const host = process.env.__NEXT_PRIVATE_HOST || originalHost.value
    ```
  - Reachability: packages/next/src/server/app-render/action-handler.ts createRedirectRenderResult(), reached by any client request to a self-hosted Next.js app whose Server Action redirects to a path starting with '/'
  - Verdict: IN — Re-fetched this session; delta matches verbatim. Clean, isolable param-binding guard: the host used to rebuild the internal fetch URL is sourced from a trusted server env (__NEXT_PRIVATE_HOST) instead of the attacker-controlled Host header (originalHost.value). Note the fix still falls back to originalHost.value when the env is unset, but the security-relevant delta is a clear trusted-source binding. Host-spoof SSRF matches CWE-918.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-34351 ; https://github.com/vercel/next.js/security/advisories/GHSA-fr5h-rqp8-mj6g ; https://github.com/vercel/next.js/commit/8f7a6ca7d21a97bc9f7a1bbe10427b5ad74b9085.diff  ·  provenance: re-verified-this-session

- **CVE-2024-36414 (GHSA-wg74-772c-8gr7)** — CWE-918 · `SuiteCRM/SuiteCRM` · fixed 7.14.4 / 8.6.1 @ `504d6f0ebd5847169d73c52d312e91916a7280bb` · **CONTESTED** (illustrative) · other
  - Mechanism: The Connectors module's action_CallRest AJAX action took a fully user-supplied 'url' request parameter, only checked it started with http(s)://, then did a raw file_get_contents on it and echoed the body back to the client -- a classic authenticated fetch-and-echo SSRF proxy against arbitrary internal/external hosts. Note: the SHA is a large hotfix/release commit (version bump, dependency updates, unrelated files); the connectors hunk below is the single unambiguous security-relevant change within it.
  - Affected -> Fixed: <= 7.14.3 (and 8.x < 8.6.1 per vendor advisory) -> 7.14.4 / 8.6.1
  - Vulnerable shape (removed):
    ```
    public function action_CallRest()
        {
            $this->view = 'ajax';
    
            $url = $_REQUEST['url'];
    
            if (!preg_match('/^http[s]{0,1}\:\/\//', (string) $url)) {
                throw new RuntimeException('Illegal request');
            }
    
            if (!$this->remoteFileExists($url)) {
                throw new RuntimeException('Requested URL is not exists.');
            }
    
    
            if (false === ($result = @file_get_contents($_REQUEST['url']))) {
                echo '';
            } else {
                ... echo $result; ...
            }
        }
    ```
  - Guard added (post-patch):
    ```
    public function action_CallRest()
        {
            $this->view = 'ajax';
        }
    ```
  - Reachability: modules/Connectors/controller.php Connectors_Controller::action_CallRest(), reached via index.php?module=Connectors&action=CallRest by any user who can invoke the controller action
  - Verdict: CONTESTED — Re-fetched this session and confirmed the fix is genuine, but it is not a cleanly isolable guard signature: the change is a functionality-deletion (the vulnerable fetch-and-echo body is gutted to an empty method, no added check to promote) embedded in a ~100+-file 7.14.4 release commit (version bump, phpseclib/TCPDF/tinymce dependency updates, many unrelated security fixes). The collector's removed_lines are also abbreviated with '...' ellipses, so the hunk is illustrative rather than machine-checkable. Mechanism is genuine CWE-918.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-36414 ; https://github.com/SuiteCRM/SuiteCRM/security/advisories/GHSA-wg74-772c-8gr7 ; https://github.com/SuiteCRM/SuiteCRM/commit/504d6f0ebd5847169d73c52d312e91916a7280bb.diff  ·  provenance: re-verified-this-session

- **CVE-2025-64430 (GHSA-x4qj-2f4q-r4rx)** — CWE-918 · `parse-community/parse-server` · fixed 7.5.4 / 8.4.0-alpha.1 @ `8bbe3efbcf4a3b66f4a8db9bfb18cd98c050db51` · **CONTESTED** (illustrative) · other
  - Mechanism: File-upload requests could set a Parse.File's _source to {format:'uri', uri:<attacker-controlled>}; the server-side save path fetched that URI directly via http.get with no destination validation and returned/stored the response, letting any client with upload access make the server issue a request to an arbitrary internal/external URI.
  - Affected -> Fixed: 4.2.0 - 7.5.3, 8.0.0 - 8.3.1-alpha.1 -> 7.5.4 / 8.4.0-alpha.1
  - Vulnerable shape (removed):
    ```
    const downloadFileFromURI = uri => {
      return new Promise((res, rej) => {
        http
          .get(uri, response => {
            response.setDefaultEncoding('base64');
            let body = `data:${response.headers['content-type']};base64,`;
            response.on('data', data => (body += data));
            response.on('end', () => res(body));
          })
          .on('error', e => {
            rej(`Error downloading file from ${uri}: ${e.message}`);
          });
      });
    };
    
    const addFileDataIfNeeded = async file => {
      if (file._source.format === 'uri') {
        const base64 = await downloadFileFromURI(file._source.uri);
        ...
      }
      return file;
    };
    ```
  - Guard added (post-patch):
    ```
    (no lines added as a replacement guard; the URI-fetch code path and its call site `await addFileDataIfNeeded(fileObject.file);` were deleted outright, disabling URI-backed file uploads)
    ```
  - Reachability: src/Routers/FilesRouter.js downloadFileFromURI(uri)/addFileDataIfNeeded(file), reached via the file-upload REST endpoint or a beforeSave trigger returning a URI-backed Parse.File
  - Verdict: CONTESTED — Re-fetched this session and confirmed the fix is genuine (downloadFileFromURI and its addFileDataIfNeeded call site were deleted outright with no replacement, and new tests assert URI uploads are rejected), but there is NO added guard to promote as a signature: added_lines is a prose note rather than code, and the removed_lines hunk is abbreviated with '...' ellipses, so it is illustrative, not machine-checkable. Genuine functionality-removal fix for CWE-918.
  - Source: https://api.osv.dev/v1/vulns/CVE-2025-64430 ; https://github.com/parse-community/parse-server/security/advisories/GHSA-x4qj-2f4q-r4rx ; https://github.com/parse-community/parse-server/commit/8bbe3efbcf4a3b66f4a8db9bfb18cd98c050db51.diff  ·  provenance: re-verified-this-session

Dropped: CVE-2024-36414 (NOT dropped -- kept as CONTESTED (see anchors). Listed here only to note it survived the gate as illustrative, not OUT.); CVE-2025-64430 (NOT dropped -- kept as CONTESTED (see anchors). Genuine deletion-fix, no promotable guard signature.); CVE-2025-50125 (Collector-dropped, upheld: Schneider Electric EcoStruxure IT Data Center Expert is proprietary/closed-source; not in OSV and no public git repo to resolve a fix commit. Unverifiable.); CVE-2025-54924 (Collector-dropped, upheld: Schneider Electric proprietary product; not in OSV, no public repo/fix commit. Unverifiable.); CVE-2025-54925 (Collector-dropped, upheld: Schneider Electric proprietary product; not in OSV, no public repo/fix commit. Unverifiable.); CVE-2024-43394 (Collector-dropped, upheld: OSV 'fixed' event points to apache/httpd commit 7e926454793abd7d71b6afc8bd1ec1648752c6ad, which is an SVN-mirror release/tag commit ('release 2.4.64') with a zero-line diff -- dead SHA, no fetchable code change.); CVE-2025-59775 (Collector-dropped, upheld: same as CVE-2024-43394 -- the OSV 'fixed' SHA (e4a77ef6051b3fe22eafacbcf54855b178a0bddd) is an empty apache/httpd SVN-mirror release-tag commit ('release 2.4.66') with no diff content.); CVE-2024-37818 (Collector-dropped, upheld: Strapi /_next/image SSRF -- OSV record (GHSA-p9ff-j98v-p435) has no GIT range and no FIX-type reference; version-string-only advisory, no resolvable fix commit. Unverifiable.); CVE-2025-2691 (Collector-dropped, upheld: nossrf npm package -- OSV record has only a SEMVER fixed-version event and a Snyk link, no FIX reference or GIT range; no public source repo to resolve a commit. Aggregator-only, unverifiable.)

## IDOR / BOLA (broken object-level authz)  (CWE-639 / CWE-284)

Grounds cards: skills/vulns/broken-object-level-authz, skills/patterns/client-supplied-selector-authz, skills/patterns/bopla-property-authz
Bucket verdict: **THIN — 4 clean IN anchors (grafana CVE-2024-1313, khoj CVE-2025-69207, chamilo CVE-2026-33702, moodle CVE-2025-3636), below the 6-anchor bar; 2 kept as CONTESTED (open-webui CVE-2026-29071 buried in a multi-file release commit with no advisory-cited SHA; LinkAce GHSA-cj8f-h888-m57m spread across 9 source files mixing per-function and per-object authz). Dominant guard shape: swap a client-controlled object key for the authenticated session identity, or scope the object lookup by owner (userid/OrgID) — i.e. exact-match-swap / owner-scoped per-object-authz.**  ·  4 IN / 2 CONTESTED / 13 dropped  ·  4 promotable signatures
Severity-corpus join: Joins the CWE-639/BOLA severity-corpus bucket: read-only cross-user object access clusters at CVSS 3.1 Low (open-webui memory/file read 3.1; grafana cross-org snapshot delete is integrity-only) and rises toward Medium/High when the object reference drives a destructive or account-scoped write (chamilo LP-progress overwrite, khoj Notion-integration hijack, moodle private-feed access); join key is guard_type in {per-object-authz, exact-match-swap} on a user-controlled object key.

- **CVE-2024-1313 (GHSA-67rv-qpw2-6qrr)** — CWE-639 · `grafana/grafana` · fixed 9.5.18 / 10.0.13 / 10.1.9 / 10.2.6 / 10.3.5 @ `f4c5a603b25f69127bfe065381ff454e55b334c5` · **IN** (signature) · per-object-authz
  - Mechanism: DELETE /api/snapshots/:key deletes a dashboard snapshot looked up only by its view key; the handler never compared the snapshot's OrgID to the requesting context's OrgID, so a user in a different org (knowing/guessing the key) could delete any org's snapshot.
  - Affected -> Fixed: 9.5.0-9.5.17, 10.0.0-10.0.12, 10.1.0-10.1.8, 10.2.0-10.2.5, 10.3.0-10.3.4 -> 9.5.18 / 10.0.13 / 10.1.9 / 10.2.6 / 10.3.5
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted immediately after the not-found check)
    	if queryResult == nil {
    		return response.Error(http.StatusNotFound, "Failed to get dashboard snapshot", nil)
    	}
    
    	if queryResult.External {
    ```
  - Guard added (post-patch):
    ```
    	if queryResult.OrgID != c.OrgID {
    		return response.Error(http.StatusUnauthorized, "OrgID mismatch", nil)
    	}
    ```
  - Reachability: DeleteDashboardSnapshot() in pkg/api/dashboard_snapshot.go, reached via DELETE /api/snapshots/:key (any authenticated user, no org membership required)
  - Verdict: IN — Re-fetched the commit .patch: touches only pkg/api/dashboard_snapshot.go (+3) and its test; the added delta is exactly the collector's per-object-authz guard (queryResult.OrgID != c.OrgID -> 401 OrgID mismatch) inserted after the not-found check. Clean, isolable, single-hunk. CWE-639 (user-controlled snapshot key with no org-ownership check) matches the bucket.
  - Source: https://grafana.com/security/security-advisories/cve-2024-1313/ ; https://github.com/advisories/GHSA-67rv-qpw2-6qrr ; https://nvd.nist.gov/vuln/detail/CVE-2024-1313 ; https://github.com/grafana/grafana/commit/f4c5a603b25f69127bfe065381ff454e55b334c5  ·  provenance: re-verified-this-session

- **CVE-2025-69207 (GHSA-6whj-7qmg-86qj)** — CWE-639 · `khoj-ai/khoj` · fixed 2.0.0-beta.23 @ `1b7ccd141d47f365edeccc57d7316cb0913d748b` · **IN** (signature) · exact-match-swap
  - Mechanism: GET /auth/callback (Notion OAuth callback) treated the attacker-controlled `state` query parameter as the target user's UUID key: it looked up an arbitrary KhojUser via aget_user_by_uuid(state) and then wrote/deleted that user's NotionConfig, with no verification the state belonged to the actual requester's session — an attacker who knew/leaked a victim's UUID could hijack the victim's Notion integration.
  - Affected -> Fixed: 0 - 2.0.0b25.dev3 -> 2.0.0-beta.23
  - Vulnerable shape (removed):
    ```
    from khoj.database.adapters import aget_user_by_uuid
    ...
    @notion_router.get("/auth/callback")
    async def notion_auth_callback(request: Request, background_tasks: BackgroundTasks):
        ...
        user: KhojUser = await aget_user_by_uuid(state)
    
        await NotionConfig.objects.filter(user=user).adelete()
    
        if not user:
            raise Exception("User not found")
    ```
  - Guard added (post-patch):
    ```
    @notion_router.get("/auth/callback")
    @requires(["authenticated"], redirect="login_page")
    async def notion_auth_callback(request: Request, background_tasks: BackgroundTasks):
        ...
        # Use authenticated user from session instead of trusting the state parameter
        user: KhojUser = request.user.object
    
        # Verify state matches user UUID as CSRF protection
        if state != str(user.uuid):
            logger.warning(f"Notion OAuth state mismatch for user {user.uuid}")
            return Response("Invalid state parameter", status_code=400)
    
        await NotionConfig.objects.filter(user=user).adelete()
    ```
  - Reachability: notion_auth_callback() in src/khoj/routers/notion.py, GET /auth/callback
  - Verdict: IN — Re-fetched the commit .patch: single file src/khoj/routers/notion.py (9 insertions / 5 deletions), removed/added lines match verbatim. Textbook CWE-639 user-controlled-key IDOR — the `state` param was used as the victim's UUID to look up and delete/modify their NotionConfig; the fix is a clean exact-match-swap to the authenticated session identity (request.user.object) plus a state==uuid check. Ellipses in the hunk only elide unchanged context; the swap is isolable.
  - Source: https://github.com/khoj-ai/khoj/security/advisories/GHSA-6whj-7qmg-86qj ; https://advisories.gitlab.com/pypi/khoj/CVE-2025-69207/ ; https://nvd.nist.gov/vuln/detail/CVE-2025-69207 ; https://github.com/khoj-ai/khoj/commit/1b7ccd141d47f365edeccc57d7316cb0913d748b  ·  provenance: re-verified-this-session

- **CVE-2026-33702 (GHSA-3rv7-9fhx-j654)** — CWE-639 · `chamilo/chamilo-lms` · fixed 1.11.38 / 2.0.0-RC.3 @ `6331d051b4468deb5830c01d1e047c5e5cf2c74f` · **IN** (signature) · exact-match-swap
  - Mechanism: main/lp/lp_ajax_save_item.php read the target `uid` for a Learning-Path progress save directly from $_REQUEST and passed it straight to save_item(); any enrolled/authenticated user could overwrite another user's LP progress (score, status, completion, time) by changing the uid parameter, with no check that uid matched the caller.
  - Affected -> Fixed: <= 1.11.36 -> 1.11.38 / 2.0.0-RC.3
  - Vulnerable shape (removed):
    ```
    echo save_item(
        (!empty($_REQUEST['lid']) ? $_REQUEST['lid'] : null),
        (!empty($_REQUEST['uid']) ? $_REQUEST['uid'] : null),
        (!empty($_REQUEST['vid']) ? $_REQUEST['vid'] : null),
    ```
  - Guard added (post-patch):
    ```
    // Always use the authenticated user's ID to prevent IDOR — never trust
    // the uid from the request, as any enrolled user could overwrite another
    // user's Learning Path progress by changing this parameter.
    echo save_item(
        (!empty($_REQUEST['lid']) ? $_REQUEST['lid'] : null),
        api_get_user_id(),
        (!empty($_REQUEST['vid']) ? $_REQUEST['vid'] : null),
    ```
  - Reachability: save_item() call in main/lp/lp_ajax_save_item.php, reached via the authenticated Learning-Path progress-save AJAX endpoint
  - Verdict: IN — Re-fetched the commit .patch: single file main/lp/lp_ajax_save_item.php; the load-bearing change is exactly the collector's exact-match-swap of the client-controlled $_REQUEST['uid'] object key for the server-side api_get_user_id(). Clean, isolable, CWE-639 user-controlled-key IDOR on a write path. Added comment is non-load-bearing but kept verbatim.
  - Source: https://github.com/chamilo/chamilo-lms/security/advisories/GHSA-3rv7-9fhx-j654 ; https://cve.threatint.eu/CVE/CVE-2026-33702 ; https://github.com/chamilo/chamilo-lms/commit/6331d051b4468deb5830c01d1e047c5e5cf2c74f  ·  provenance: re-verified-this-session

- **CVE-2025-3636 (GHSA-chmf-m33p-ph8m)** — CWE-639 · `moodle/moodle` · fixed 4.1.19 / 4.3.13 / 4.4.9 / 4.5.5 @ `0bd97209ac5e217dbec236c73e4f6fdcaee1c737` · **IN** (signature) · per-object-authz
  - Mechanism: blocks/rss_client/viewfeed.php fetched an RSS feed configuration by `$DB->get_record('block_rss_client', array('id' => $rssid), ...)` — an id-only lookup with no ownership or capability check (only an isguestuser() gate existed) — letting any logged-in user view/access any other user's or course's private RSS feed by guessing/incrementing rssid.
  - Affected -> Fixed: <= 4.1.18 (also 4.3.0beta-4.3.12, 4.4.0beta-4.4.8, 4.5.0beta-4.5.4) -> 4.1.19 / 4.3.13 / 4.4.9 / 4.5.5
  - Vulnerable shape (removed):
    ```
    require_login();
    if (isguestuser()) {
        throw new \moodle_exception('guestsarenotallowed');
    }
    ...
    $rssrecord = $DB->get_record('block_rss_client', array('id' => $rssid), '*', MUST_EXIST);
    ```
  - Guard added (post-patch):
    ```
    $managesharedfeeds = has_capability('block/rss_client:manageanyfeeds', $context);
    if (!$managesharedfeeds) {
        require_capability('block/rss_client:manageownfeeds', $context);
    }
    ...
    if ($managesharedfeeds) {
        $select = 'id = :id AND (userid = :userid OR shared = 1)';
    } else {
        $select = 'id = :id AND userid = :userid';
    }
    
    $rssrecord = $DB->get_record_select('block_rss_client', $select, [
        'id' => $rssid,
        'userid' => $USER->id,
    ], '*', MUST_EXIST);
    ```
  - Reachability: blocks/rss_client/viewfeed.php?rssid=<id>
  - Verdict: IN — Re-fetched the commit .patch: single file blocks/rss_client/viewfeed.php. Core signature is the collector's per-object-authz change — the id-only get_record is replaced by an owner-scoped get_record_select (id AND userid, or userid OR shared for manageanyfeeds). The added has_capability/require_capability lines are complementary (not an unrelated refactor); the whole fix is one file, one commit, isolable. CWE-639 guessable-rssid IDOR matches the bucket.
  - Source: https://github.com/advisories/GHSA-chmf-m33p-ph8m ; https://nvd.nist.gov/vuln/detail/CVE-2025-3636 ; https://github.com/moodle/moodle/commit/0bd97209ac5e217dbec236c73e4f6fdcaee1c737  ·  provenance: re-verified-this-session

- **CVE-2026-29071 (GHSA-w9f8-gxf9-rhvw)** — CWE-639 · `open-webui/open-webui` · fixed 0.8.6 @ `9c9a18d6d4311ff246d5d1345d94581bf25c604b` · **CONTESTED** (illustrative) · per-object-authz
  - Mechanism: POST /api/v1/retrieval/query/doc and /query/collection accept a client-supplied collection_name(s) string and query the vector store directly; nothing checked that the collection (a user-memory-* or file-* namespace) belonged to the caller, letting any authenticated user read another user's private memories or uploaded-file content by naming their collection.
  - Affected -> Fixed: < 0.8.6 -> 0.8.6
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard call inserted before the try: block)
    async def query_doc_handler(
        request: Request,
        form_data: QueryDocForm,
        user=Depends(get_verified_user),
    ):
        try:
    ```
  - Guard added (post-patch):
    ```
    def _validate_collection_access(collection_names: list[str], user) -> None:
        if user.role == "admin":
            return
        for name in collection_names:
            if name.startswith("user-memory-") and name != f"user-memory-{user.id}":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
            elif name.startswith("file-"):
                file_id = name[len("file-"):]
                if not has_access_to_file(file_id=file_id, access_type="read", user=user):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    ...
        _validate_collection_access([form_data.collection_name], user)
    ```
  - Reachability: query_doc_handler / query_collection_handler in backend/open_webui/routers/retrieval.py, reached via POST /api/v1/retrieval/query/doc and /query/collection
  - Verdict: CONTESTED — Class-match is solid: the GHSA advisory and NVD independently confirm CWE-639 IDOR in backend/open_webui/routers/retrieval.py query_collection_handler (no ownership check on client-supplied collection_names; user-memory-{uuid}/file-{uuid} predictable). BUT the fix is not cleanly isolable: the collector's fix_sha resolves to a large multi-purpose release commit (translations, package.json, workflows, dozens of unrelated backend/frontend files), and neither the advisory nor OSV cites a specific fix commit/PR — a fetch of the commit .patch did not surface the retrieval.py guard in the leading file set. The added hunk is also a stitched reconstruction (an ellipsis joins the _validate_collection_access helper definition to a far-removed call site). Genuine vuln, entangled/unverifiable SHA -> CONTESTED, do not promote as a machine-checkable signature.
  - Source: https://github.com/open-webui/open-webui/security/advisories/GHSA-w9f8-gxf9-rhvw ; https://nvd.nist.gov/vuln/detail/CVE-2026-29071 ; https://github.com/open-webui/open-webui/commit/9c9a18d6d4311ff246d5d1345d94581bf25c604b  ·  provenance: second-hand-reverify-before-citing

- **GHSA-cj8f-h888-m57m** — CWE-639 · `Kovah/LinkAce` · fixed 2.5.6 @ `2c121b4b179a07dfb9c3d2ffc33c9cc4ca029e88` · **CONTESTED** (illustrative) · exact-match-swap
  - Mechanism: LinkPolicy/LinkListPolicy/TagPolicy/NotePolicy's update() ability delegated to userCanAccessX(), which only checked resource visibility (public/internal vs private), never ownership; the API controllers additionally never called $this->authorize() at all before persisting an update. Any authenticated user (including via a scoped API token) could overwrite another user's public/internal link, list, tag, or note.
  - Affected -> Fixed: <= 2.5.5 -> 2.5.6
  - Vulnerable shape (removed):
    ```
    public function update(User $user, Link $link): bool
    {
        return $this->userCanAccessLink($user, $link);
    }
    (same pattern repeated in LinkListPolicy/TagPolicy/NotePolicy; API controllers' update() had no authorize() call at all)
    ```
  - Guard added (post-patch):
    ```
    public function update(LinkUpdateRequest $request, ApiLink $link): JsonResponse
    {
        $this->authorize('update', $link);
        ...
    }
    
    public function update(User $user, Link $link): bool
    {
        return $link->user->is($user);
    }
    ```
  - Reachability: update() in app/Http/Controllers/API/{Link,List,Note,Tag}Controller.php and matching Policies, reached via PATCH /api/v2/{links,lists,notes,tags}/{id}
  - Verdict: CONTESTED — Re-fetched the commit .patch and confirmed the fix is real and class-matching: all four Policy update() abilities change from a visibility check (userCanAccessX / visibility != PRIVATE) to an ownership check ($link->user->is($user), AuthorizesUserApiActions -> return false), and all four API controllers add $this->authorize('update', ...). BUT it is not a single isolable signature: the change is replicated across 9 source files (4 controllers + 5 policies, +10 test files) and mixes two guard types (per-function-authz authorize() call AND per-object-authz ownership check). The collector's removed_lines also carries prose annotation ('same pattern repeated ... had no authorize() call at all') and the added_lines stitches a controller method to a policy method. Genuine single-SHA fix but spread/entangled -> CONTESTED, promote_signature=false.
  - Source: https://github.com/Kovah/LinkAce/security/advisories/GHSA-cj8f-h888-m57m ; https://github.com/Kovah/LinkAce/commit/2c121b4b179a07dfb9c3d2ffc33c9cc4ca029e88  ·  provenance: re-verified-this-session

Dropped: CVE-2026-29071 / GHSA-cj8f-h888-m57m (NOTE: neither was dropped — open-webui and LinkAce are retained as CONTESTED in anchors[]. This entry is a pointer only; see anchors for their verdicts.); CVE-2024-10497 (Schneider Electric PowerLogic HDPM6000 — proprietary firmware, no public repo/commit to fetch a diff from. (collector-dropped, pass-through)); CVE-2025-46387 (Emby MediaBrowser is closed-source (unlike its Jellyfin fork); no public fix commit exists to verify. (collector-dropped, pass-through)); CVE-2026-57869 (GHSA-2rhx-q7hx-f25r) (MicroRealEstate — OSV API returns 404 for this GHSA id and the advisory page itself lists no fixed version or linked commit/PR; searches turned up no fetchable fix commit. (collector-dropped, pass-through)); CVE-2023-38051 (GHSA-mhhg-cwfq-wvgg) (Easy!Appointments /secretaries/{id} BOLA — patched inside the monolithic 1.5.0 release; the release-tag commit is a version bump and the closest identifiable authorization commit (b37b460) fixes a different endpoint (Calendar controller, not Secretaries). No single clean commit isolating this CVE's fix; would require hand-reconstruction. (collector-dropped, pass-through)); CVE-2023-40720 (FortiVoiceEnterprise — proprietary Fortinet firmware, no public repo/commit. (collector-dropped, pass-through)); CVE-2023-44254 (FortiAnalyzer/FortiManager — proprietary Fortinet software, no public repo/commit. (collector-dropped, pass-through)); CVE-2023-44249 (GHSA-c7m9-r72h-m8v2) (FortiManager/FortiAnalyzer — proprietary Fortinet software; GHSA exists only as an advisory record, no source repo/commit to fetch. (collector-dropped, pass-through)); CVE-2023-48783 (FortiPortal — proprietary Fortinet software, no public repo/commit. (collector-dropped, pass-through)); CVE-2022-39945 (FortiMail — proprietary Fortinet software, no public repo/commit. (collector-dropped, pass-through)); CVE-2024-28320 (Hospital Management System ('code-projects' source dump) — no real git history/repository exists; distributed as a static source archive, so there is no fixable single commit. (collector-dropped, pass-through)); CVE-2025-40660 (DM Corporative CMS by Dmacroweb — proprietary vendor CMS, no public source repository found. (collector-dropped, pass-through)); GHSA-5q8v-j673-m5v4 (Firefly III) (Primary record's CWE is CWE-863 (Incorrect Authorization): a missing role/admin check gating GET /api/v1/users and /users/{id} — a function-level (BFLA/CWE-862/863) gap, not a per-object-key IDOR. Mechanism mismatch for this CWE-639/284 bucket. (collector-dropped, pass-through; agreed OUT))

## BFLA (broken function-level authz)  (CWE-862 / CWE-285)

Grounds cards: skills/vulns/broken-function-level-authz, skills/patterns/unsafe-default-authz-helper, skills/patterns/ui-only-policy-enforcement
Bucket verdict: **IN — 7 clean anchors, all re-fetched and confirmed verbatim at primary sources this session (>=6 threshold met). Dominant guard shape: a per-function-authz check inserted immediately before a previously-unguarded sink (route middleware reqRepoReader / controller ForbiddenHttpException gate / method-level checkPermission — gitea, craftcms, pimcore, arcadedb), with two minority variants — an exact-match role-check swap on the auth gate (easyappointments) and field-level write-protection binding (shopware param-binding, plainpad per-object-authz). 6 of 7 carry promote_signature=true; arcadedb is IN but promote_signature=false because its provided hunk narrates the ~11-22 multi-method insertion sites rather than a single verbatim delta.**  ·  7 IN / 0 CONTESTED / 2 dropped  ·  6 promotable signatures
Severity-corpus join: Join to the severity-corpus 'missing/broken authorization (CWE-862/285/863)' bucket: these BFLA fixes cluster high — AV:N, low-priv PR:L, AC:L, no UI — for vertical privilege escalation to admin/schema control (shopware, plainpad, easyappointments, craftcms, arcadedb map to ~8.1-9.9 / Critical), with the read-only info-exposure variant (gitea issue-templates on a Code-unit-restricted token) sitting lower at ~4.3-6.5, consistent with the corpus split between privesc-to-admin and confidentiality-only authz gaps.

- **CVE-2026-41128 (GHSA-jq2f-59pj-p3m3)** — CWE-862 · `craftcms/cms` · fixed 5.9.15 (and 4.16.x fix line) @ `b135384808ad43fcf8836a9dd9b877fb0087bc27` · **IN** (signature) · per-function-authz
  - Mechanism: actionSavePermissions() controller action let any authenticated CP user (only viewUsers permission needed) submit a userId + empty 'groups' body param to strip a target user from every user group; the per-group check in _saveUserGroups() only validated additions, never removals. Fix adds a controller-level showPermissionsScreen() gate on the whole action plus a canAssignUserGroups() guard on the group-mutation helper.
  - Affected -> Fixed: <5.9.15 / <4.16.19 (pre-fix branches) -> 5.9.15 (and 4.16.x fix line)
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before the sink) — actionSavePermissions() called $this->requireCpRequest(); then went straight to editing groups/perms with no authorization check; _saveUserGroups() unconditionally read $this->request->getBodyParam('groups') and applied it.
    ```
  - Guard added (post-patch):
    ```
    if (!$this->showPermissionsScreen()) {
        throw new ForbiddenHttpException('User not authorized to perform this action.');
    }
    ...
    if (!$currentUser->canAssignUserGroups()) {
        return;
    }
    ```
  - Reachability: POST /admin/users/save-permissions -> UsersController::actionSavePermissions() -> private _saveUserGroups($user, $currentUser); entrypoint is any authenticated Control Panel user with the low-privilege 'viewUsers' permission.
  - Verdict: IN — Re-fetched commit b135384 (.patch); both guards confirmed verbatim — showPermissionsScreen()/ForbiddenHttpException gate on actionSavePermissions() and the canAssignUserGroups() guard in _saveUserGroups(). Clean per-function-authz guard-insertion before a previously-unauthorized sink; missing-authorization fix so no removed code is expected, and the added guards are the machine-checkable signature. CWE-862 mechanism-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-jq2f-59pj-p3m3 ; https://github.com/craftcms/cms/security/advisories/GHSA-jq2f-59pj-p3m3 ; https://nvd.nist.gov/vuln/detail/CVE-2026-41128  ·  provenance: re-verified-this-session

- **CVE-2026-48008 (GHSA-gv8p-48fr-4fxg)** — CWE-862 · `shopware/shopware` · fixed 6.6.10.18 / 6.7.10.1 @ `1e047f6d7fd9129271e28c1c9f1c272983c6f48f` · **IN** (signature) · param-binding
  - Mechanism: The regular POST /api/integration endpoint blocked a caller from setting admin=true without full admin rights (isAdmin() controller check), but the Sync API (POST /api/_action/sync) writes entities straight through the DAL EntityWriter, which has no equivalent check, so a user with only integration:create could create an admin integration via Sync and fully escalate.
  - Affected -> Fixed: <6.6.10.18 / <6.7.10.1 -> 6.6.10.18 / 6.7.10.1
  - Vulnerable shape (removed):
    ```
    new BoolField('admin', 'admin'),
    ```
  - Guard added (post-patch):
    ```
    (new BoolField('admin', 'admin'))->addFlags(new WriteProtected(Context::SYSTEM_SCOPE)),
    ```
  - Reachability: POST /api/_action/sync (Sync API) writing an `integration` entity -> IntegrationDefinition field collection -> DAL EntityWriter persists the 'admin' BoolField with no controller in front of it; entrypoint is any authenticated API user holding integration:create ACL privilege.
  - Verdict: IN — Re-fetched commit 1e047f6 (.patch) AND OSV GHSA-gv8p-48fr-4fxg — both confirm CWE-862 and the Sync-API vertical-privesc mechanism (the admin field lacked the write-protection the controller path enforced). One-line delta is clean and isolable. Reclassified guard_type per-object-authz -> param-binding: the remediation is a field-level WriteProtected(SYSTEM_SCOPE) write-binding restriction (only system scope may write the field), not an object-owner check.
  - Source: https://api.osv.dev/v1/vulns/GHSA-gv8p-48fr-4fxg ; https://github.com/shopware/shopware/security/advisories/GHSA-gv8p-48fr-4fxg ; https://github.com/shopware/shopware/commit/1e047f6d7fd9129271e28c1c9f1c272983c6f48f  ·  provenance: re-verified-this-session

- **CVE-2026-27783 (GHSA-3fwp-p5rj-2pxf)** — CWE-862 · `go-gitea/gitea` · fixed 1.26.2 @ `171df0c9ffcec1b0839431e75f3b59e35d39ddca` · **IN** (signature) · per-function-authz
  - Mechanism: The issue-template API routes (GET /issue_templates, /issue_config, /issue_config/validate) were registered with only context.ReferencesGitRepo() and no repository-unit authorization, unlike sibling routes (/languages, /licenses) which required reqRepoReader(unit.TypeCode); a token scoped to read-repository (no Code-unit access) could still read issue templates/config from repos where the Code unit is disabled/restricted.
  - Affected -> Fixed: <=1.26.1 -> 1.26.2
  - Vulnerable shape (removed):
    ```
    m.Get("/issue_templates", context.ReferencesGitRepo(), repo.GetIssueTemplates)
    m.Get("/issue_config", context.ReferencesGitRepo(), repo.GetIssueConfig)
    m.Get("/issue_config/validate", context.ReferencesGitRepo(), repo.ValidateIssueConfig)
    ```
  - Guard added (post-patch):
    ```
    m.Get("/issue_templates", reqRepoReader(unit.TypeCode), context.ReferencesGitRepo(), repo.GetIssueTemplates)
    m.Get("/issue_config", reqRepoReader(unit.TypeCode), context.ReferencesGitRepo(), repo.GetIssueConfig)
    m.Get("/issue_config/validate", reqRepoReader(unit.TypeCode), context.ReferencesGitRepo(), repo.ValidateIssueConfig)
    ```
  - Reachability: GET /api/v1/repos/{owner}/{repo}/issue_templates and /issue_config[/validate] -> routers/api/v1/api.go route table -> repo.GetIssueTemplates / GetIssueConfig / ValidateIssueConfig; entrypoint is any authenticated API token scoped only to read-repository, on a repo with the Code unit disabled for that caller.
  - Verdict: IN — Re-fetched commit 171df0c (.patch); all three route registrations gain reqRepoReader(unit.TypeCode) before context.ReferencesGitRepo() verbatim. Textbook per-function-authz middleware insertion closing a missing repo-unit authorization — the cleanest machine-checkable signature in the bucket. CWE-862 match.
  - Source: https://api.osv.dev/v1/vulns/CVE-2026-27783 ; https://github.com/go-gitea/gitea/security/advisories/GHSA-3fwp-p5rj-2pxf ; https://github.com/go-gitea/gitea/pull/37769 ; https://github.com/go-gitea/gitea/commit/171df0c9ffcec1b0839431e75f3b59e35d39ddca  ·  provenance: re-verified-this-session

- **CVE-2026-23496 (GHSA-4wg4-p27p-5q2r)** — CWE-284 · `pimcore/web2print-tools` · fixed 5.2.2 / 6.1.1 @ `7714452a04b9f9b077752784af4b8d0b05e464a1` · **IN** (signature) · per-function-authz
  - Mechanism: favoriteOutputDefinitionsTableProxyAction() (list/manage 'Favourite Output Channel Configurations') had no server-side permission check at all, so any authenticated Pimcore backend user — not just those granted the web2print permission — could list/create/update these configs via the admin API.
  - Affected -> Fixed: <5.2.2 / <6.1.1 -> 5.2.2 / 6.1.1
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before the sink) — public function favoriteOutputDefinitionsTableProxyAction(Request $request)
    {
        if ($request->request->getString('data')) {
    ```
  - Guard added (post-patch):
    ```
    $this->checkPermission('web2print_web2print_favourite_output_channels');
    ```
  - Reachability: Admin API route -> AdminController::favoriteOutputDefinitionsTableProxyAction() (list/xaction=destroy/update of favourite output-channel configs); entrypoint is any authenticated Pimcore backend user lacking the web2print favourite-output-channels permission.
  - Verdict: IN — Re-fetched commit 7714452 (.patch); the $this->checkPermission('web2print_web2print_favourite_output_channels') insertion into the previously-unguarded favoriteOutputDefinitionsTableProxyAction() is confirmed verbatim. Clean per-function-authz guard-insertion. Primary CWE-284 is the parent of CWE-862; the mechanism (no server-side permission check at all) is squarely missing-function-level authorization, so it is in-bucket. Minor: the .patch summarizer noted the check may have been relocated in a later commit, but this SHA adds the guard as cited — the anchor is the add.
  - Source: https://api.osv.dev/v1/vulns/CVE-2026-23496 ; https://github.com/pimcore/pimcore/security/advisories/GHSA-4wg4-p27p-5q2r ; https://github.com/pimcore/web2print-tools/commit/7714452a04b9f9b077752784af4b8d0b05e464a1  ·  provenance: re-verified-this-session

- **CVE-2026-54076 (GHSA-vg6x-6pg9-6qwg)** — CWE-862 · `ArcadeData/arcadedb` · fixed 26.6.1 @ `2ee76fe442b974b2482f1e9eddd1ab429bcac614` · **IN** (illustrative) · per-function-authz
  - Mechanism: A prior CVE's fix added an UPDATE_SCHEMA permission check to only LocalDocumentType.createProperty(); every other public schema-mutating method (dropProperty, rename, setAliases, addSuperType, addBucket/removeBucket, LocalProperty.setDefaultValue/setOfType, etc.) stayed unchecked, so a read-only API token could still DROP/ALTER schema through those other entrypoints.
  - Affected -> Fixed: <=26.5.1 -> 26.6.1
  - Vulnerable shape (removed):
    ```
    public LocalProperty createProperty(final String propertyName, final Type propertyType, final String ofType) {
        ((DatabaseInternal) schema.getDatabase()).checkPermissionsOnDatabase(SecurityDatabaseUser.DATABASE_ACCESS.UPDATE_SCHEMA);
    (only this one call site had the inline check; dropProperty/rename/setAliases/addSuperType/setSuperTypes/addBucket/removeBucket/LocalProperty.setDefaultValue/setOfType had none)
    ```
  - Guard added (post-patch):
    ```
    protected void checkForSchemaMutation() {
        ((DatabaseInternal) schema.getDatabase()).checkPermissionsOnDatabase(SecurityDatabaseUser.DATABASE_ACCESS.UPDATE_SCHEMA);
    }
    // ...then checkForSchemaMutation(); inserted at the top of removeSuperType(), rename(), setSuperTypes(), setAliases(), createProperty(), dropProperty(), addBucket(), removeBucket(), addSuperType(), and LocalProperty.setDefaultValue()/setOfType()
    ```
  - Reachability: SQL DDL statements (DROP PROPERTY / ALTER TYPE / ALTER PROPERTY / etc.) -> LocalDocumentType / LocalProperty schema-mutator methods; entrypoint is any authenticated identity holding only a read-only API token (no UPDATE_SCHEMA right).
  - Verdict: IN — Re-fetched commit 2ee76fe (.patch); primary source confirms a single, isolated security fix with no unrelated refactor — extracts checkForSchemaMutation() -> checkPermissionsOnDatabase(UPDATE_SCHEMA) and inserts it at the top of every schema mutator (dropProperty/rename/setAliases/addSuperType/removeSuperType/setSuperTypes/addBucket/removeBucket + LocalProperty setters), closing the gap left by the prior CVE that only guarded createProperty(). Uniform per-function-authz guard shape; CWE-862 match, so verdict IN. promote_signature=false: the collector's added_lines narrates the ~11-22 insertion sites rather than pasting the exact per-method hunk, so the delta as given is illustrative even though the guard itself is machine-checkable.
  - Source: https://api.osv.dev/v1/vulns/GHSA-vg6x-6pg9-6qwg ; https://github.com/ArcadeData/arcadedb/security/advisories/GHSA-vg6x-6pg9-6qwg ; https://github.com/ArcadeData/arcadedb/commit/2ee76fe442b974b2482f1e9eddd1ab429bcac614  ·  provenance: re-verified-this-session

- **CVE-2026-42562 (GHSA-pvfv-wvpm-q6f6)** — CWE-269 · `alextselegidis/plainpad` · fixed 1.1.1 @ `9216a876d27b22c3d9259551636d803f7cb075fc` · **IN** (signature) · per-object-authz
  - Mechanism: PUT /api.php/v1/users/{id} (UsersController::update) read $user->admin (the ALREADY-authorized target row) to decide who may edit, then unconditionally overwrote $user->admin = $request->input('admin') from client input — a low-privilege user editing their own profile could flip their own admin flag to true with no field-level check tying that write to the CALLER's role.
  - Affected -> Fixed: <1.1.1 -> 1.1.1
  - Vulnerable shape (removed):
    ```
    if (!$user->admin && $user->id !== $id) {
        return response('', 401);
    }
    ...
    $user->admin = $request->input('admin');
    ```
  - Guard added (post-patch):
    ```
    $authUser = Auth::user();
    if (!$authUser->admin && $authUser->id !== $user->id) {
        return response('', 401);
    }
    ...
    if ($authUser->admin) {
        $user->admin = (bool)$request->input('admin');
    }
    ```
  - Reachability: PUT /api.php/v1/users/{id} -> UsersController::update(); entrypoint is any authenticated user updating their own profile (id === their own id) via the 'admin' request body field.
  - Verdict: IN — Re-fetched commit 9216a87 (.patch); confirmed verbatim — the authorization decision moves from the target row ($user->admin) to the caller (Auth::user()/$authUser), and the admin-field write is gated on $authUser->admin. Fixes a broken-authorization vertical privesc (self-edit sets own admin flag). Collector CWE-269, but the mechanism is incorrect/missing authorization on a privileged write (CWE-285/863), placing it in-bucket; guard_type per-object-authz holds (field write gated on caller role). Caveat: OSV/advisory GHSA-pvfv-wvpm-q6f6 returned HTTP 404 (record not re-fetchable this session), but the fix commit — the load-bearing artifact — is confirmed at the primary source, so verdict remains IN.
  - Source: https://api.osv.dev/v1/vulns/CVE-2026-42562 ; https://github.com/alextselegidis/plainpad/security/advisories/GHSA-pvfv-wvpm-q6f6 ; https://github.com/alextselegidis/plainpad/commit/9216a876d27b22c3d9259551636d803f7cb075fc  ·  provenance: re-verified-this-session

- **CVE-2022-1397** — CWE-269 · `alextselegidis/easyappointments` · fixed 1.5.0 @ `63dbb51decfcc1631c398ecd6d30e3a337845526` · **IN** (signature) · exact-match-swap
  - Mechanism: Api::auth() (HTTP Basic Auth gate for the /index.php/api/v1/* endpoints, including account/role management) only verified that the given username/password matched SOME valid login via check_login(), with no check that the authenticated account actually held the admin role, so any valid low-privilege account's credentials granted full API/admin access, including creating new admin accounts.
  - Affected -> Fixed: <1.5.0 -> 1.5.0
  - Vulnerable shape (removed):
    ```
    if ( ! $this->CI->accounts->check_login($username, $password))
    {
        throw new RuntimeException('The provided credentials do not match any admin user!', 401, 'Unauthorized');
    }
    ```
  - Guard added (post-patch):
    ```
    $userdata = $this->CI->accounts->check_login($username, $password);
    if (empty($userdata['role_slug']) || $userdata['role_slug'] !== DB_SLUG_ADMIN)
    {
        throw new RuntimeException('The provided credentials do not match any admin user!', 401, 'Unauthorized');
    }
    ```
  - Reachability: Any /index.php/api/v1/* endpoint (account/role management functions) gated by HTTP Basic Auth -> Api::auth(); entrypoint is any valid non-admin easyappointments account's credentials.
  - Verdict: IN — Re-fetched commit 63dbb51 (.patch); confirmed verbatim — the admin-API Basic-Auth gate is changed from 'any valid login' (check_login truthy) to a role check (role_slug === DB_SLUG_ADMIN). Textbook missing-function-level-authorization on privileged API endpoints (CWE-862 substance; collector CWE-269 label). Clean exact-match-swap of the weak gate for a role-verified one.
  - Source: https://api.osv.dev/v1/vulns/CVE-2022-1397 ; https://nvd.nist.gov/vuln/detail/CVE-2022-1397 ; https://github.com/alextselegidis/easyappointments/commit/63dbb51decfcc1631c398ecd6d30e3a337845526  ·  provenance: re-verified-this-session

Dropped: CVE-2026-53645 (FOSSBilling, GHSA-4hf7-xxxw-64rm) (Pass-through of collector drop, confirmed appropriate. OSV's GIT-range 'fixed' SHA (3bd35f5b) resolves to an unrelated installer commit, not the security fix; the real self-edit-prevention + permission-ceiling check landed inside a large multi-commit 'Rework admin groups and permissions' refactor (PR #3821 + neighbors) that also converts the whole permission model member->group across dozens of unrelated files. No single isolable whole-fix SHA -> entangled/multi-commit, fails the machine-checkable-signature gate (would be CONTESTED at best, but with no fetchable single-commit delta it is dropped as unverifiable).); CVE-2024-25106 (OpenObserve, GHSA-3m5f-9m66-xgp7) (Pass-through of collector drop, confirmed appropriate. OSV's GIT-range 'fixed' SHA (921b3971) is the last commit before the v0.8.0 tag cut (unrelated 'enrichment table query' commit), not the fix. The actual fix (initiator_id + Admin/Root role check in remove_user_from_org, commit 7cbcee718e / #2493) is a plausible in-bucket CWE-862 anchor, but its full diff could not be fetched to verify the verbatim hunk before the fetch budget ran out. Dropped as unverifiable rather than cite an unconfirmed hunk; candidate for re-collection with an authenticated fetch.)

## Auth bypass (generic mechanism / middleware / gateway)  (CWE-287 / CWE-863)

Grounds cards: skills/vulns/jwt-authentication-bypass, skills/patterns/legacy-route-differential, skills/patterns/transitive-sanitizer-reliance
Bucket verdict: **THIN -- 4 clean IN (Next.js, openclaw, Moby, Quarkus) + 1 CONTESTED (fastify-express), 5 kept, below the 6 comfortable-coverage mark. No self-dropped OUT anchors; the corpus thinness is driven by closed-source vendor firmware/SaaS (F5, Palo Alto, Fortinet, Cisco, Atlassian, Lightspeed) with no fetchable public fix commit plus two unverifiable single-SHA cases (Kong, authentik). Dominant guard shapes across the bucket: (1) canonicalize-path-before-authz so the security matcher can't diverge from the routed path (Quarkus IN, fastify-express CONTESTED); (2) bind a trusted internal signal to an unforgeable identity -- per-process secret on a trusted header (Next.js param-binding) or immutable id instead of a spoofable display name (openclaw exact-match-swap); (3) enforce a body-size bound so an AuthZ gateway can't be starved of the real payload (Moby). Ecosystem spread: 3 npm/JS, 1 Go, 1 Java, npm-weighted.**  ·  4 IN / 1 CONTESTED / 8 dropped  ·  4 promotable signatures
Severity-corpus join: Joins the same severity-corpus broken-access-control / auth-bypass bucket at its high end: all five are network-reachable, no-privilege-required authorization/authentication bypasses (Next.js CVE-2025-29927 ~9.1 Critical full middleware-auth skip; Moby AuthZ-plugin and Quarkus path-policy bypasses in the High-Critical AV:N/PR:N band with high C/I impact), anchoring the Critical tail of the CVSS 3.1/4.0 distribution for this class.

- **CVE-2025-29927 (GHSA-f82v-jwr5-mffw)** — NVD: CWE-863 (Incorrect Authorization); GitHub CNA: CWE-285 (Improper Authorization) · `vercel/next.js` · fixed 12.3.5 / 13.5.9 / 14.2.25 / 15.2.3 @ `52a078da3884efe6501613c7834a3d02a91676d2` · **IN** (signature) · param-binding
  - Mechanism: Next.js's self-hosted server trusted the client-supplied x-middleware-subrequest header (used internally to prevent infinite middleware recursion) with no secret binding; a request forging this header caused middleware.ts (where auth/authz checks live) to be skipped entirely, e.g. GET /admin with header x-middleware-subrequest: middleware:middleware:middleware:middleware:middleware.
  - Affected -> Fixed: <12.3.5, <13.5.9, <14.2.25, <15.2.3 -> 12.3.5 / 13.5.9 / 14.2.25 / 15.2.3
  - Vulnerable shape (removed):
    ```
    (no lines removed from the header-filter call site; guard inserted around the pre-existing unguarded loop)
        if (INTERNAL_HEADERS.includes(header)) {
          delete headers[header]
        }
    ```
  - Guard added (post-patch):
    ```
      const randomBytes = new Uint8Array(8)
      crypto.getRandomValues(randomBytes)
      const middlewareSubrequestId = Buffer.from(randomBytes).toString('hex')
      ;(globalThis as any)[Symbol.for('@next/middleware-subrequest-id')] =
        middlewareSubrequestId
    ...
        if (
          header === 'x-middleware-subrequest' &&
          headers['x-middleware-subrequest-id'] !==
            (globalThis as any)[Symbol.for('@next/middleware-subrequest-id')]
        ) {
          delete headers['x-middleware-subrequest']
        }
    ```
  - Reachability: server-ipc/utils.ts filterInternalHeaders() (called for every proxied request from router-server.ts initialize()) strips x-middleware-subrequest only if it doesn't match a per-process random secret; sandbox/context.ts stamps that same secret onto genuine internal subrequests. Entrypoint: any inbound HTTP request carrying a crafted x-middleware-subrequest header.
  - Verdict: IN — Re-fetched commit 52a078da confirms the exact guard verbatim: a per-process random secret (crypto.getRandomValues -> hex) bound onto genuine internal subrequests as x-middleware-subrequest-id, and the inbound x-middleware-subrequest header stripped unless that id matches. Clean, isolable param-binding guard; CWE-863/285 auth-bypass-via-middleware-skip is squarely in-bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-f82v-jwr5-mffw ; https://github.com/vercel/next.js/security/advisories/GHSA-f82v-jwr5-mffw ; https://nvd.nist.gov/vuln/detail/CVE-2025-29927 ; https://github.com/vercel/next.js/commit/52a078da3884efe6501613c7834a3d02a91676d2  ·  provenance: re-verified-this-session

- **CVE-2026-28474 (GHSA-r5h9-vjqc-hq3r)** — NVD: CWE-863 (Incorrect Authorization); GHSA: CWE-290 (Authentication Bypass by Spoofing) · `openclaw/openclaw` · fixed 2026.2.6 @ `6b4b6049b47c3329a7014509594647826669892d` · **IN** (signature) · exact-match-swap
  - Mechanism: The Nextcloud-Talk channel plugin's allowlist check (resolveNextcloudTalkAllowlistMatch) matched an inbound message's sender against allowFrom by either immutable user id OR mutable display name (actor.name); an attacker who renames themselves to an allowlisted display name is authorized into restricted DMs/rooms without holding the allowlisted identity.
  - Affected -> Fixed: <2026.2.6 -> 2026.2.6
  - Vulnerable shape (removed):
    ```
      const senderName = params.senderName ? normalizeAllowEntry(params.senderName) : "";
      if (senderName && allowFrom.includes(senderName)) {
        return { allowed: true, matchKey: senderName, matchSource: "name" };
      }
    ```
  - Guard added (post-patch):
    ```
    export function resolveNextcloudTalkAllowlistMatch(params: {
      allowFrom: Array<string | number> | undefined;
      senderId: string;
    }): AllowlistMatch<"wildcard" | "id"> {
    ...
    - `allowFrom` matches Nextcloud user IDs only; display names are ignored.
    ```
  - Reachability: resolveNextcloudTalkAllowlistMatch() / resolveNextcloudTalkGroupAllow() in extensions/nextcloud-talk/src/policy.ts, invoked from handleNextcloudTalkInbound() in inbound.ts. Entrypoint: inbound Nextcloud Talk webhook payload's actor.name/actor.id.
  - Verdict: IN — Re-fetched commit 6b4b6049 (subject 'fix: enforce Nextcloud Talk allowlist by user id', author steipete) confirms removal of the mutable display-name authorization branch (senderName / matchSource:'name') and the type narrowing from AllowlistMatch<'wildcard'|'id'|'name'> to <'wildcard'|'id'>, binding allowFrom to immutable user ids only. Clean exact-match-swap; CWE-290/863 authn-bypass-by-spoofing in-bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-r5h9-vjqc-hq3r ; https://github.com/openclaw/openclaw/security/advisories/GHSA-r5h9-vjqc-hq3r ; https://github.com/openclaw/openclaw/commit/6b4b6049b47c3329a7014509594647826669892d  ·  provenance: re-verified-this-session

- **CVE-2026-34040 (GHSA-x744-4wpc-v9h2)** — GitHub CNA: CWE-288 (Authentication Bypass Using an Alternate Path or Channel); also tagged CWE-863 · `moby/moby` · fixed 29.3.1 / 2.0.0-beta.8 @ `e89edb19ad7de0407a5d31e3111cb01aa10b5a38` · **IN** (signature) · bound
  - Mechanism: Docker Engine's AuthZ plugin request path silently truncated/emptied request bodies larger than ~1MiB before forwarding them to authorization plugins for inspection, but still executed the original unredacted request against the daemon; plugins that default-allow when they observe an empty/small body never see the real (oversized) payload, letting a single padded HTTP request fully bypass AuthZ policy evaluation.
  - Affected -> Fixed: <29.3.1 (moby/moby, docker/docker); <2.0.0-beta.8 (moby/moby/v2) -> 29.3.1 / 2.0.0-beta.8
  - Vulnerable shape (removed):
    ```
    func isChunked(r *http.Request) bool { ... }
    if sendBody(ctx.requestURI, r.Header) && (r.ContentLength > 0 || isChunked(r)) && r.ContentLength < maxBodySize {
    	var err error
    	body, r.Body, err = drainBody(r.Body)
    ...
    // drainBody dump the body (if its length is less than 1MB) without modifying the request state
    func drainBody(body io.ReadCloser) ([]byte, io.ReadCloser, error) {
    	data, err := bufReader.Peek(maxBodySize)
    	if err == nil {
    		log.G(context.TODO()).Warnf("Request body is larger than: '%d' skipping body", maxBodySize)
    		return nil, newBody, nil
    	}
    ```
  - Guard added (post-patch):
    ```
    		peeked, err := bufBody.Peek(maxBodySize + 1)
    		if err == nil {
    			// Successfully peeked maxBodySize+1 bytes, so body is too large
    			return fmt.Errorf("request body too large for authorization plugin: size exceeds %d bytes", maxBodySize)
    		} else if err != io.EOF {
    			return err
    		}
    ```
  - Reachability: Ctx.AuthZRequest() in pkg/authorization/authz.go, invoked on every Docker Engine REST API call when AuthZ plugins are configured. Entrypoint: any Docker Engine API request whose body exceeds maxBodySize.
  - Verdict: IN — Re-fetched commit e89edb19 confirms the AuthZ body path now Peek(maxBodySize+1) and returns an error ('request body too large for authorization plugin') on oversize instead of silently forwarding a nil/empty body to plugins (it also bumps maxBodySize 1MiB->4MiB, a benign accompanying tweak). The security-relevant delta — silent-skip -> hard-fail bound so plugins can no longer be starved of the real payload — is clean and isolable; CWE-288/863 AuthZ-plugin gateway bypass in-bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-x744-4wpc-v9h2 ; https://github.com/moby/moby/security/advisories/GHSA-x744-4wpc-v9h2 ; https://nvd.nist.gov/vuln/detail/CVE-2026-34040 ; https://github.com/moby/moby/commit/e89edb19ad7de0407a5d31e3111cb01aa10b5a38  ·  provenance: re-verified-this-session

- **CVE-2026-50559 (GHSA-qcxp-gm7m-4j5v)** — GitHub, Inc. / Red Hat: CWE-863 (Incorrect Authorization) / CWE-287 (Improper Authentication) / CWE-551 (Incorrect Behavior Order: Authorization Before Parsing and Canonicalization) -- direct anchor match, multiply tagged · `quarkusio/quarkus` · fixed 3.37.0 / 3.36.3 / 3.33.2.1 / 3.33.3 / 3.27.4.1 / 3.27.5 / 3.20.6.2 @ `fc5c83aab65f62a2d7c7c8f9fd6845b080f94f53` · **IN** (signature) · canonicalization
  - Mechanism: Quarkus's HTTP path-based security policy (AbstractPathMatchingHttpSecurityPolicy) normalized paths via Vert.x's normalizedPath(), which only decodes unreserved RFC3986 characters, then stripped matrix params by searching for a literal ';'. An encoded semicolon (%3B) was never seen by the strip step, so /api/admin%3Bbypass=true/data failed to match the /api/admin/* policy and passed through unauthenticated; separately, static-resource handlers fully percent-decoded %2F/%5C after the security layer had already made its (looser) decision, letting encoded slashes/backslashes reach protected static files.
  - Affected -> Fixed: <=3.35.2, <=3.34.7, <=3.33.1.1, <=3.27.3.1, <=3.20.6.1 -> 3.37.0 / 3.36.3 / 3.33.2.1 / 3.33.3 / 3.27.4.1 / 3.27.5 / 3.20.6.2
  - Vulnerable shape (removed):
    ```
    PathMatch<List<HttpMatcher>> toCheck = pathMatcher.match(HttpSecurityUtils.pathWithoutMatrixParams(normalizedPath));
    ...
    builder.addPath(path, perms);
    ```
  - Guard added (post-patch):
    ```
    public static String normalizePath(String path) {
        while (path.indexOf('%') >= 0) {
            String decoded = decodePercent(path);
            if (decoded.equals(path)) { break; }
            path = decoded;
        }
        path = pathWithoutMatrixParams(path);
        if (path.indexOf('\0') >= 0) { path = path.replace("\0", ""); }
        if (path.indexOf('\\') >= 0) { path = path.replace('\\', '/'); }
        path = HttpUtils.removeDots(path);
        return path;
    }
    ...
    PathMatch<List<HttpMatcher>> toCheck = pathMatcher.match(HttpSecurityUtils.normalizePath(normalizedPath));
    ```
  - Reachability: HttpSecurityUtils.normalizePath(), consumed by AbstractPathMatchingHttpSecurityPolicy.findHttpMatchers()/addPermissionToPathMatcher() (extensions/vertx-http), KeycloakPolicyEnforcerAuthorizer, StaticTenantResolver, and CsrfRequestResponseReactiveFilter. Entrypoint: any HTTP request to a quarkus.http.auth.permission path-policy-protected endpoint or protected static resource, with %3B/%2F/%5C/double-encoding in the path.
  - Verdict: IN — Re-fetched commit fc5c83aa AND the raw HttpSecurityUtils.java at that SHA confirm normalizePath() verbatim (loop percent-decode until stable, pathWithoutMatrixParams, null-byte strip, backslash->slash, HttpUtils.removeDots) plus the call-site swap pathWithoutMatrixParams(...)->normalizePath(...). Single fix SHA; the change is large (15 files/+611) only because the same canonicalization-before-authz guard is applied consistently at each sink (Keycloak, StaticTenantResolver, CSRF, servlet) with tests, not an unrelated refactor. CWE-863/287/551 directly in-bucket; clean isolable canonicalization guard.
  - Source: https://github.com/quarkusio/quarkus/security/advisories/GHSA-qcxp-gm7m-4j5v ; https://quarkus.io/blog/CVE-2026-50559/ ; https://github.com/quarkusio/quarkus/commit/fc5c83aab65f62a2d7c7c8f9fd6845b080f94f53  ·  provenance: re-verified-this-session

- **CVE-2026-33808 (GHSA-6hw5-45gm-fj88)** — GitHub CNA: CWE-436 (Interpretation Conflict) -- off-anchor tag; mechanism is a canonicalization mismatch causing path-scoped Express auth middleware to be silently skipped, matching this bucket's CWE-287/863 by behavior · `fastify/fastify-express` · fixed 4.0.5 @ `674020f27ddc1d1709e4369cb40158d4c958d42b` · **CONTESTED** (illustrative) · canonicalization
  - Mechanism: @fastify/express forwarded the raw, only-percent-decoded request URL to Express middleware while Fastify's own router (when ignoreDuplicateSlashes/useSemicolonDelimiter are enabled) normalizes duplicate slashes and semicolon-delimited matrix params for its own route matching. The two layers disagreed on the canonical path, so a request like //admin/dashboard or /admin;bypass reached the Fastify route but never matched the path-scoped Express middleware registered at /admin, silently skipping that middleware's auth check.
  - Affected -> Fixed: <4.0.5 -> 4.0.5
  - Vulnerable shape (removed):
    ```
        const decodedUrl = decodeURI(url)
        req.raw.url = decodedUrl
    ...
          req.raw.url = decodedUrl
    ```
  - Guard added (post-patch):
    ```
        const decodedUrl = decodeURI(url)
        const normalizedUrl = normalizeUrl(decodedUrl, {
          ignoreDuplicateSlashes,
          useSemicolonDelimiter
        })
    
        req.raw.url = normalizedUrl
    ...
    function removeDuplicateSlashes (path) {
      return path.replace(/\/{2,}/g, '/')
    }
    ```
  - Reachability: index.js's onRequest hook (fastifyExpress plugin), which sets req.raw.url before Express middleware dispatch. Entrypoint: any HTTP request path containing duplicate slashes or a semicolon when the corresponding Fastify router option is enabled.
  - Verdict: CONTESTED — Re-fetched commit 674020f confirms a clean, single-commit canonicalization guard (normalizeUrl + removeDuplicateSlashes/semicolon handling applied to req.raw.url before Express dispatch) whose direct effect is path-scoped auth middleware being skipped -- mechanism belongs to this bucket by behavior and the guard is isolable. Contested (not IN) because the primary-record CWE is CWE-436 (Interpretation Conflict), a parser-differential classification adjacent to but outside this bucket's CWE-287/863; the record is not mislabeled (CWE-436 legitimately fits a canonicalization/interpretation conflict), it simply sits off-bucket, so it is kept as an illustrative canonicalization-mismatch->auth-skip exemplar rather than promoted as a CWE-287/863 signature.
  - Source: https://github.com/fastify/fastify-express/security/advisories/GHSA-6hw5-45gm-fj88 ; https://nvd.nist.gov/vuln/detail/CVE-2026-33808 ; https://github.com/fastify/fastify-express/commit/674020f27ddc1d1709e4369cb40158d4c958d42b  ·  provenance: re-verified-this-session

Dropped: CVE-2022-1388 (F5 BIG-IP iControl REST is closed-source vendor firmware; no public git repository or fix commit exists to fetch a diff from. (collector-dropped, confirmed)); CVE-2024-0012 (Palo Alto Networks PAN-OS is closed-source vendor firmware; no public git repository or fix commit exists. (collector-dropped, confirmed)); CVE-2022-40684 (Fortinet FortiOS/FortiProxy/FortiSwitchManager is closed-source vendor firmware; no public git repository or fix commit exists. (collector-dropped, confirmed)); CVE-2023-22515 (Atlassian Confluence Data Center/Server is closed-source; no public git repository for the vulnerable application code. (collector-dropped, confirmed)); CVE-2023-20198 (Cisco IOS XE is closed-source vendor firmware; no public git repository or fix commit exists. (collector-dropped, confirmed)); CVE-2026-30368 (Lightspeed Classroom (GHSA-fv9m-8cwh-9rgj) is a closed-source EdTech product; the GHSA id is not indexed in OSV and no public repo/commit could be located. (collector-dropped, confirmed)); CVE-2021-27306 (Kong Gateway (open source) but GHSA-vh85-5xw7-5gvq carries no linked fix commit/PR reference, and the current CHANGELOG.md no longer retains the 2.3.x-era entries; no single clean fix commit isolable for this 2021-era CVE. (collector-dropped, confirmed as unverifiable single-SHA)); CVE-2026-25748 (authentik (GHSA-fj56-5763-j8pp) -- several plausible related commits in goauthentik/authentik proxyv2 forward-auth session/cookie handling around the correct window, but no single commit conclusively matches the advisory's exact mechanism (malformed cookie causing checkAuth to omit X-Authentik-* headers while still permitting the proxy) versus adjacent session-robustness fixes. Dropped as unverifiable/entangled rather than cite a mechanism-mismatched anchor. (collector-dropped, confirmed))

## Insecure deserialization -> RCE  (CWE-502)

Grounds cards: skills/vulns/insecure-deserialization
Bucket verdict: **THIN -- only 3 clean IN anchors survived (< 6 target). Dominant guard shape is deser-type-filter: an assignability/allowlist check (Throwable.class.isAssignableFrom / SERIALIZABLE_PACKAGES package-allowlist) inserted immediately before the reflective Class.forName()+String-constructor instantiation. Two of the collector's 5 were removed on adjudication (Jenkins = per-function-authz mechanism mismatch; PyYAML = unmerged-proposal SHA contradicting the shipped 5.1 fix), and 7 of the 8 seed-bucket drops are Apache SVN-mirrored projects whose OSV 'fixed' SHAs are version-bump-only commits -- the corpus's CWE-502 seed is structurally hard to anchor to clean GitHub-native diffs.**  ·  3 IN / 0 CONTESTED / 10 dropped  ·  3 promotable signatures
Severity-corpus join: All 3 IN anchors join the severity-corpus CWE-502 bucket at its high-severity cluster (CVSS 9.8-10.0, AV:N/AC:L/PR:N/UI:N or file-triggered, C:H/I:H/A:H): ActiveMQ 2023-46604 and parquet 2025-30065 are unauth/file-read arbitrary-class instantiation (~10.0), fastjson 2022-25845 is autoType-bypass RCE (~8.1-9.8) -- the shared severity signature is reflective instantiation of an attacker-named class reachable pre-auth or via untrusted input.

- **CVE-2023-46604 (GHSA-crg9-44h2-xw35)** — CWE-502 · `apache/activemq` · fixed 5.15.16 / 5.16.7 / 5.17.6 / 5.18.3 @ `3eaf3107f4fb9a3ce7ab45c175bfaeac7e866d5b` · **IN** (signature) · deser-type-filter
  - Mechanism: Openwire protocol's BaseDataStreamMarshaller.createThrowable() takes an attacker-supplied class name off the wire, resolves it via Class.forName(), and directly invokes its String constructor via reflection with no check that the resolved class is actually a Throwable, letting a remote unauthenticated peer force instantiation of an arbitrary class (e.g. a Spring gadget that runs a shell command) via a crafted OpenWire ExceptionResponse packet.
  - Affected -> Fixed: >=5.8.0,<5.15.16 || >=5.16.0,<5.16.7 || >=5.17.0,<5.17.6 || >=5.18.0,<5.18.3 -> 5.15.16 / 5.16.7 / 5.17.6 / 5.18.3
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before instantiation)
    Class clazz = Class.forName(className, false, BaseDataStreamMarshaller.class.getClassLoader());
    Constructor constructor = clazz.getConstructor(new Class[] {String.class});
    return (Throwable)constructor.newInstance(new Object[] {message});
    ```
  - Guard added (post-patch):
    ```
    // new file OpenWireUtil.java
    public static void validateIsThrowable(Class<?> clazz) {
        if (!Throwable.class.isAssignableFrom(clazz)) {
            throw new IllegalArgumentException("Class " + clazz + " is not assignable to Throwable");
        }
    }
    // call site in createThrowable():
    OpenWireUtil.validateIsThrowable(clazz);
    ...
    } catch (IllegalArgumentException e) {
        return e;
    }
    ```
  - Reachability: BaseDataStreamMarshaller.createThrowable(className, message) <- tightUnmarsalThrowable() <- OpenWire wire-format unmarshalling of an ExceptionResponse, reached by any TCP client of the OpenWire transport connector (default port 61616), no authentication required.
  - Verdict: IN — Re-fetched the .patch this session: new OpenWireUtil.validateIsThrowable() with `if (!Throwable.class.isAssignableFrom(clazz))` plus the `OpenWireUtil.validateIsThrowable(clazz);` call inserted immediately after Class.forName() in createThrowable() across every marshaller version (v1/v2/v9-v12 + legacy). Uniform application of one guard across all OpenWire versions is the complete fix, not an unrelated refactor. Clean, isolable deser-type-filter; CWE-502 + mechanism match; single whole-fix SHA.
  - Source: https://api.osv.dev/v1/vulns/CVE-2023-46604 ; https://github.com/advisories/GHSA-crg9-44h2-xw35 ; https://github.com/apache/activemq/commit/3eaf3107f4fb9a3ce7ab45c175bfaeac7e866d5b  ·  provenance: re-verified-this-session

- **CVE-2022-25845 (GHSA-pv7h-hx5h-mgfj)** — CWE-502 · `alibaba/fastjson` · fixed 1.2.83 @ `35db4adad70c32089542f23c272def1ad920a60d` · **IN** (signature) · deser-type-filter
  - Mechanism: fastjson's ParserConfig.checkAutoType() gates which class names JSON.parse()/JSON.parseObject() may instantiate via the '@type' field using a denylist (denyHashCodes) plus an autoTypeSupport flag, but a class name ending in 'Exception'/assignable from Throwable slipped past both the denylist mapping lookup and the 'autoType not supported' rejection, letting an attacker name an Exception/Throwable subclass as '@type' to reach a gadget-chain constructor for RCE even with autoType disabled.
  - Affected -> Fixed: >=1.2.25,<1.2.83 -> 1.2.83
  - Vulnerable shape (removed):
    ```
    (no lines removed at the check site; guard inserted before existing fallthrough)
    if (clazz == null) {
        clazz = typeMapping.get(typeName);
    }
    ...
    if (!autoTypeSupport) {
        throw new JSONException("autoType is not support. " + typeName);
    }
    ```
  - Guard added (post-patch):
    ```
    if (expectClass == null && clazz != null && Throwable.class.isAssignableFrom(clazz) && !autoTypeSupport) {
        clazz = null;
    }
    ...
    if (!autoTypeSupport) {
        if (typeName.endsWith("Exception")) {
            return null;
        }
        throw new JSONException("autoType is not support. " + typeName);
    }
    // plus new entries appended to denyHashCodes[], e.g.:
    0x868385095A22725FL,
    0xAB82562F53E6E48FL,
    0x8BAAEE8F9BF77FA7L,
    ```
  - Reachability: ParserConfig.checkAutoType(typeName, expectClass, features) <- DefaultJSONParser's class-resolution during JSON.parse()/JSON.parseObject() on attacker-controlled JSON containing an '@type' naming an Exception/Throwable-derived class.
  - Verdict: IN — Re-fetched the .patch this session: commit touches only ParserConfig.java + a single test (Bug_for_Exception.java), 7.5KB total. The two guards land verbatim in checkAutoType() -- `if (expectClass == null && clazz != null && Throwable.class.isAssignableFrom(clazz) && !autoTypeSupport)` and `if (typeName.endsWith("Exception")) { return null; }` -- alongside new denyHashCodes entries. Denylist + Throwable/Exception type-filter are the same guard mechanism, tightly scoped, no unrelated refactor. Clean isolable deser-type-filter; CWE-502 + mechanism match; single whole-fix SHA.
  - Source: https://api.osv.dev/v1/vulns/CVE-2022-25845 ; https://github.com/advisories/GHSA-pv7h-hx5h-mgfj ; https://github.com/alibaba/fastjson/commit/35db4adad70c32089542f23c272def1ad920a60d  ·  provenance: re-verified-this-session

- **CVE-2025-30065 (GHSA-2c59-37c4-qrx5)** — CWE-502 · `apache/parquet-java` · fixed 1.15.1 @ `680edfa71c142d9eb63e76e5070b3713ba0cab53` · **IN** (signature) · deser-type-filter
  - Mechanism: parquet-avro's AvroConverters.FieldStringableConverter reflectively instantiates the Java class named by a schema's 'java-class' property (via a String constructor) with no restriction on which class may be named, so a malicious Parquet file whose embedded Avro schema sets 'java-class' to an attacker-chosen class forces that class's instantiation purely by reading the file, reaching RCE gadgets.
  - Affected -> Fixed: <1.15.1 -> 1.15.1
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before use)
    public FieldStringableConverter(ParentValueContainer parent, Class<?> stringableClass) {
      super(parent);
      stringableName = stringableClass.getName();
      try {
        this.ctor = stringableClass.getConstructor(String.class);
    ```
  - Guard added (post-patch):
    ```
    checkSecurity(stringableClass);
    ...
    private void checkSecurity(Class<?> clazz) throws SecurityException {
      List<String> trustedPackages = Arrays.asList(SERIALIZABLE_PACKAGES);
      boolean trustAllPackages = trustedPackages.size() == 1 && "*".equals(trustedPackages.get(0));
      if (trustAllPackages || clazz.isPrimitive()) { return; }
      ...
      if (!found) {
        throw new SecurityException("Forbidden " + clazz + "! This class is not trusted...");
      }
    }
    ```
  - Reachability: AvroConverters.FieldStringableConverter(parent, stringableClass) constructor <- Avro schema 'java-class' stringable-field converter setup <- reading any Parquet file via parquet-avro's AvroReadSupport whose embedded schema declares a stringable java-class.
  - Verdict: IN — Re-fetched the underlying commit SHA 680edfa directly this session (not just the PR URL): touches AvroConverters.java + 2 test files, 6.7KB. Adds `checkSecurity(stringableClass);` in the FieldStringableConverter ctor and a `private void checkSecurity(Class<?> clazz) throws SecurityException` that allowlists against SERIALIZABLE_PACKAGES and otherwise throws `new SecurityException("Forbidden ...")`. Package-allowlist type-filter inserted before reflective instantiation. fix_commit_url points at the PR but the fixed SHA re-fetches to a single clean whole-fix commit. Clean isolable deser-type-filter; CWE-502 + mechanism match.
  - Source: https://api.osv.dev/v1/vulns/CVE-2025-30065 ; https://github.com/advisories/GHSA-2c59-37c4-qrx5 ; https://github.com/apache/parquet-java/pull/3169  ·  provenance: re-verified-this-session

Dropped: CVE-2018-1000861 (OUT - mechanism mismatch (class-match is on mechanism, not NVD title). NVD tags this CWE-502, but the actual bug is Stapler URL-to-method dispatch invoking reflection over live Java objects, and the fix (new jenkins/security/stapler/DoActionFilter.java keep(Function m) method-allowlist + RoutingDecisionProvider) is a per-function-authz routing gate, NOT a serialized-object-graph type-filter. The collector itself concedes it is only 'equivalent to unfiltered deserialization'. A method-dispatch authz allowlist has a different exploitation/severity profile and would pollute the deser->RCE join, so it is OUT of this bucket per the explicit 'if the guard is actually an authz check, it is OUT' rule.); CVE-2017-18342 (OUT - wrong/unmerged commit; diff does not represent the shipped fix. The collector's SHA bbcf95fa (PR #74) renames Loader->DangerLoader / safe_load->'safe_load = load' / adds danger_load, and its .patch is fetchable, but this was an unmerged proposal. Verified the released PyYAML 5.1: lib3/yaml/loader.py still has `class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver)` (default stays UNSAFE), no DangerLoader, and __all__ lists FullLoader/UnsafeLoader instead; lib3/yaml/__init__.py ships `def load(stream, Loader=None)` -> FullLoader with a YAMLLoadWarning plus unsafe_load. The actual CVE-2017-18342 fix took a fundamentally different shape (add FullLoader/UnsafeLoader + deprecation warning, default not made safe), so this SHA is not the code that resolved the CVE -- not a genuine-fix-with-cosmetic-nit (keep-bias does not apply), it is the wrong artifact.); CVE-2017-9805 (Collector-dropped (pass-through): Struts S2-052 XStream RCE. OSV's two 'fixed' git events both resolve to maven-release-plugin version-bump commits (pom.xml only); the real XStreamHandler content-type fix commit could not be located via commit-message search within budget. Unverifiable single fix SHA.); CVE-2017-7525 (Collector-dropped (pass-through): jackson-databind polymorphic-deserialization denylist. OSV's 3 'fixed' events across 2.6/2.7/2.8 all resolve to maven release-tag version-bump commits; the actual denylist-array commits are unlabeled and buried earlier in each branch, not resolvable via commit-message search within budget.); CVE-2020-9484 (Collector-dropped (pass-through): Apache Tomcat FileStore/PersistenceManager session deserialization. OSV's 4 'fixed' events all resolve to version-bump-only commits; svn-mirrored messages don't reference the CVE/ticket and 'sessionAttributeValueClassNameFilter' search returned no code commit within budget.); CVE-2025-24813 (Collector-dropped (pass-through): Apache Tomcat partial-PUT path-equivalence session deserialization. OSV 'fixed' events resolve to version-bump-only commits; nearby partial-PUT hardening commits could not be confirmed as THE cited fix within budget.); CVE-2019-0192 (Collector-dropped (pass-through): Apache Solr Config API JMX/RMI deserialization. OSV gives only introduced/last_affected pairs for apache/solr and apache/lucene-solr, no 'fixed' event; SOLR-13301 commit-message search returned no hits within budget.); CVE-2022-1471 (Collector-dropped (pass-through): SnakeYAML Constructor() unrestricted type instantiation. Bitbucket-hosted; the only reachable commits are maven-release-plugin 'prepare release' commits with no code diff; Bitbucket commit-search did not surface the real security commit within budget.); CVE-2020-14343 (Collector-dropped (pass-through): PyYAML full_load()/FullLoader python/module|object|object/new tag RCE. A clean verified fix commit exists (PR #472, merge 7adc0db3...), but NVD and GHSA-8q59-q68h-6hv4 both tag it CWE-20 at the primary source, not CWE-502 -- dropped on CWE class-mismatch despite the deser-type-filter shape.); CVE-2021-42392 (Collector-dropped (pass-through): H2 JdbcUtils.getConnection() JNDI-driver RCE. CWE-502 confirmed at JFrog CNA + NVD, but OSV gives only introduced/last_affected for h2database/h2database with no 'fixed' git event; commit-message search returned no locatable single fix commit within budget.)

## OS command injection -> RCE  (CWE-78)

Grounds cards: skills/vulns/os-command-injection, skills/vulns/injection
Bucket verdict: **THIN — 5 clean IN anchors (< 6 threshold): shell-quote (CVE-2026-9277), claudecodeui (CVE-2026-31975), php-cgi (CVE-2024-4577), node-glob (CVE-2025-64756), @npmcli/git (GHSA-hxwm-x553-x359); haxcms (CVE-2025-49141) is CONTESTED (endpoint deletion, no added guard to promote). 0 new OUT — all 6 collector anchors re-fetched and confirmed at primary sources this session. Dominant guard shape: param-binding — stop interpolating attacker-controlled input into a shell-parsed command string and instead bind it as a positional argument / disable the shell (shell:false, cwd separation, \"$@\"); canonicalization (php Best-Fit byte remap, shell-quote line-terminator escape) is the secondary shape.**  ·  5 IN / 1 CONTESTED / 4 dropped  ·  5 promotable signatures
Severity-corpus join: Joins the CWE-78 command-injection->RCE severity bucket: unauth network RCE anchors the CVSS 3.1 9.8 top (php-cgi CVE-2024-4577, AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H, CISA KEV); authenticated web endpoints (haxcms gitImportSite, claudecodeui shell WS) sit ~8.8 (network, PR:L); CLI/library vectors (shell-quote as a quoting lib, node-glob -c, @npmcli/git) are caller-/attacker-file-dependent, typically AV:L or usage-gated, ~7.x-8.x.

- **CVE-2026-9277 (GHSA-w7jw-789q-3m8p)** — CWE-78 / CWE-77 · `ljharb/shell-quote` · fixed 1.8.4 @ `4378a6e613db5948168684864e49b42b83134d2d` · **IN** (signature) · canonicalization
  - Mechanism: shell-quote's quote() escaped object-token '.op' fields character-by-character with /(.)/g, which in JS does not match line terminators (\n, \r, U+2028, U+2029); a newline smuggled into .op passed through unescaped, and POSIX shells treat a literal newline as a command separator, letting a caller who quotes an attacker-shaped object token (direct construction, or via parse()'s documented envFn splice) achieve command injection when the quoted string is later run in a shell.
  - Affected -> Fixed: npm shell-quote >=1.1.0, <=1.8.3 -> 1.8.4
  - Vulnerable shape (removed):
    ```
    if (s && typeof s === 'object') {
    			return s.op.replace(/(.)/g, '\\$1');
    		}
    ```
  - Guard added (post-patch):
    ```
    if (s.op === 'glob') {
    				if (typeof s.pattern !== 'string') {
    					throw new TypeError('glob token requires a string `pattern`');
    				}
    				if (LINE_TERMINATORS.test(s.pattern)) {
    					throw new TypeError('glob `pattern` must not contain line terminators');
    				}
    				return s.pattern.replace(GLOB_SHELL_SPECIAL, '\\$&');
    			}
    			if (typeof s.op === 'string') {
    				if (OPS.indexOf(s.op) < 0) {
    					throw new TypeError('invalid `op` value: ' + JSON.stringify(s.op));
    				}
    				return s.op.replace(/[\s\S]/g, '\\$&');
    			}
    ```
  - Reachability: quote(xs) object-token branch in quote.js, reached by any caller (or parse()'s envFn splice) that builds { op } tokens from external input and later executes the quoted string via a shell (e.g. child_process.exec/execSync with shell:true).
  - Verdict: IN — Re-fetched at ljharb/shell-quote commit 4378a6e this session: diff confirms the escape regex /(.)/g (dot excludes JS line terminators) is swapped for /[\s\S]/g and an OPS exact-match allowlist plus a LINE_TERMINATORS guard on glob patterns is added. Clean, isolable canonicalization guard (escape now covers newline/U+2028/U+2029). Mechanism = line terminator smuggled into .op acting as a shell command separator = CWE-78/77 command injection. Machine-checkable signature.
  - Source: https://api.osv.dev/v1/vulns/GHSA-w7jw-789q-3m8p ; https://github.com/ljharb/shell-quote/security/advisories/GHSA-w7jw-789q-3m8p ; https://github.com/ljharb/shell-quote/commit/4378a6e613db5948168684864e49b42b83134d2d ; https://nvd.nist.gov/vuln/detail/CVE-2026-9277  ·  provenance: re-verified-this-session

- **CVE-2026-31975 (GHSA-gv8f-wpm2-m5wr)** — CWE-78 (chained with CWE-287, CWE-1188) · `siteboon/claudecodeui` · fixed 1.25.0 @ `12e7f074d9563b3264caf9cec6e1b701c301af26` · **IN** (signature) · param-binding
  - Mechanism: handleShellConnection() built the interactive-shell command by directly interpolating client-supplied projectPath and sessionId into shell strings (e.g. `cd "${projectPath}" && ${initialCommand}`) run via a pty, with cwd fixed to os.homedir(); chained with a JWT/WebSocket auth bypass elsewhere in the same advisory, this gives an attacker OS command injection via the path/session fields with no shell-metacharacter sanitization.
  - Affected -> Fixed: npm @siteboon/claude-code-ui <= 1.24.0 -> 1.25.0
  - Vulnerable shape (removed):
    ```
    if (os.platform() === 'win32') {
                                shellCommand = `Set-Location -Path "${projectPath}"; ${initialCommand}`;
                            } else {
                                shellCommand = `cd "${projectPath}" && ${initialCommand}`;
                            }
    ...
    cwd: os.homedir(),
    ```
  - Guard added (post-patch):
    ```
    const resolvedProjectPath = path.resolve(projectPath);
                        try {
                            const stats = fs.statSync(resolvedProjectPath);
                            if (!stats.isDirectory()) {
                                throw new Error('Not a directory');
                            }
                        } catch (pathErr) {
                            ws.send(JSON.stringify({ type: 'error', message: 'Invalid project path' }));
                            return;
                        }
                        const safeSessionIdPattern = /^[a-zA-Z0-9_.\-:]+$/;
                        if (sessionId && !safeSessionIdPattern.test(sessionId)) {
                            ws.send(JSON.stringify({ type: 'error', message: 'Invalid session ID' }));
                            return;
                        }
    ...
                            shellCommand = initialCommand;
    ...
    cwd: resolvedProjectPath,
    ```
  - Reachability: handleShellConnection(ws) WebSocket handler in server/index.js, reached by any client message carrying projectPath/sessionId/initialCommand that is spliced into a pty-spawned shell command string.
  - Verdict: IN — Re-fetched at siteboon/claudecodeui commit 12e7f07 this session: diff confirms removal of the `cd "${projectPath}" && ${initialCommand}` interpolation (now shellCommand = initialCommand, with projectPath bound out-of-band via cwd: resolvedProjectPath) plus path.resolve/statSync validation and a sessionId allowlist regex. All hunks are the single CWE-78 injection fix (the chained CWE-287 auth-bypass is patched elsewhere in the advisory) — no unrelated refactor. Isolable param-binding + canonicalization guard.
  - Source: https://api.osv.dev/v1/vulns/GHSA-gv8f-wpm2-m5wr ; https://github.com/siteboon/claudecodeui/security/advisories/GHSA-gv8f-wpm2-m5wr ; https://github.com/siteboon/claudecodeui/commit/12e7f074d9563b3264caf9cec6e1b701c301af26 ; https://nvd.nist.gov/vuln/detail/CVE-2026-31975  ·  provenance: re-verified-this-session

- **CVE-2024-4577 (GHSA-3qgc-jrrr-25jv)** — CWE-78 · `php/php-src` · fixed 8.1.29 / 8.2.20 / 8.3.8 @ `938267314835de3c2ed1a3da4f2959f1d2709468` · **IN** (signature) · canonicalization
  - Mechanism: On Windows, when QUERY_STRING has no '=', php-cgi decodes and inspects only the first raw byte to decide whether to skip PHP's own getopt parsing (treating it as a CLI flag start '-'); it did not account for Windows' 'Best-Fit' code-page remapping, so a high byte that Win32 remaps to ASCII '-' at the OS level was not caught, letting a remote request smuggle CLI flags (e.g. -d allow_url_include=1) into the php.exe invocation and achieve RCE.
  - Affected -> Fixed: PHP 8.1.0-8.1.28, 8.2.0-8.2.19, 8.3.0-8.3.7 (Windows + Apache/PHP-CGI or similarly configured CGI SAPI) -> 8.1.29 / 8.2.20 / 8.3.8
  - Vulnerable shape (removed):
    ```
    if((query_string = getenv("QUERY_STRING")) != NULL && strchr(query_string, '=') == NULL) {
    		/* we've got query string that has no = - apache CGI will pass it to command line */
    		unsigned char *p;
    ...
    		if(*p == '-') {
    			skip_getopt = 1;
    		}
    		free(decoded_query_string);
    ```
  - Guard added (post-patch):
    ```
    #ifdef PHP_WIN32
    		if (*p >= 0x80) {
    			wchar_t wide_buf[1];
    			wide_buf[0] = *p;
    			char char_buf[4];
    			size_t wide_buf_len = sizeof(wide_buf) / sizeof(wide_buf[0]);
    			size_t char_buf_len = sizeof(char_buf) / sizeof(char_buf[0]);
    			if (WideCharToMultiByte(CP_ACP, 0, wide_buf, wide_buf_len, char_buf, char_buf_len, NULL, NULL) == 0
    				|| char_buf[0] == '-') {
    				skip_getopt = 1;
    			}
    		}
    #endif
    ```
  - Reachability: main() in sapi/cgi/cgi_main.c, reached by any HTTP request whose QUERY_STRING contains no '=' and is routed to php-cgi.exe on Windows (e.g. via Apache CGI handler).
  - Verdict: IN — Re-fetched this session: NVD confirms CWE-78 (OS Command Injection), CVSS 3.1 9.8, CISA KEV / actively exploited. Commit 9382673 adds a Windows-only WideCharToMultiByte(CP_ACP,...) canonicalization that maps the raw high byte the way the OS will and re-checks for '-' before the getopt-skip decision, closing the Best-Fit flag-smuggle. Clean isolable canonicalization guard, unauthenticated remote RCE.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-4577 ; https://github.com/php/php-src/security/advisories/GHSA-3qgc-jrrr-25jv ; https://github.com/php/php-src/commit/938267314835de3c2ed1a3da4f2959f1d2709468 ; https://nvd.nist.gov/vuln/detail/CVE-2024-4577  ·  provenance: re-verified-this-session

- **CVE-2025-64756 (GHSA-5j98-mcp5-4vw2)** — CWE-78 · `isaacs/node-glob` · fixed 11.1.0 (10.5.0 on the 10.x line) @ `1e4e297342a09f2aa0ced87fcd4a70ddc325d75f` · **IN** (signature) · param-binding
  - Mechanism: The glob CLI's -c/--cmd option always ran the matched file paths through foregroundChild(cmd, matches, { shell: true }); with shell:true, Node re-parses the whole argv through /bin/sh, so a matched filename containing shell metacharacters (e.g. `$(...)`, backticks) executes as injected commands.
  - Affected -> Fixed: npm glob 11.0.0 - 11.0.x (and 10.2.0 - 10.4.x on the 10.x line) -> 11.1.0 (10.5.0 on the 10.x line)
  - Vulnerable shape (removed):
    ```
    const cmd = values.cmd
      if (!cmd) {
        matches.forEach(m => console.log(m))
        stream.on('data', f => console.log(f))
      } else {
        stream.on('data', f => matches.push(f))
        stream.on('end', () => foregroundChild(cmd, matches, { shell: true }))
      }
    ```
  - Guard added (post-patch):
    ```
    const { SHELL = 'unknown' } = process.env
        const shellBase = basename(SHELL)
        const knownShells = ['sh', 'ksh', 'zsh', 'bash', 'fish']
        if (
          (shell || /[ "']/.test(cmd)) &&
          knownShells.includes(shellBase)
        ) {
          const cmdWithArgs = `${cmd} "\$${shellBase === 'fish' ? 'argv' : '@'}"`
          if (shellBase !== 'fish') {
            cmdArg.unshift(SHELL)
          }
          cmdArg.unshift('-c', cmdWithArgs)
          stream.on('end', () => foregroundChild(SHELL, cmdArg))
        } else {
          ...
          stream.on('end', () => foregroundChild(cmd, cmdArg, { shell }))
        }
    ```
  - Reachability: src/bin.mts CLI entrypoint, -c/--cmd flag; reached whenever the glob CLI is invoked with -c against untrusted filenames in the search directory.
  - Verdict: IN — Re-fetched at isaacs/node-glob commit 1e4e297 this session: diff confirms removal of foregroundChild(cmd, matches, { shell: true }) (which re-parsed matched filenames through /bin/sh) in favor of passing matches as bound positional arguments via "$@"/"$argv" and invoking foregroundChild(SHELL, cmdArg) without shell:true (raw shell:true now gated behind an explicit deprecated --shell opt). Isolable param-binding guard; CWE-78 filename-metacharacter injection.
  - Source: https://api.osv.dev/v1/vulns/GHSA-5j98-mcp5-4vw2 ; https://github.com/isaacs/node-glob/security/advisories/GHSA-5j98-mcp5-4vw2 ; https://github.com/isaacs/node-glob/commit/1e4e297342a09f2aa0ced87fcd4a70ddc325d75f ; https://nvd.nist.gov/vuln/detail/CVE-2025-64756  ·  provenance: re-verified-this-session

- **GHSA-hxwm-x553-x359** — CWE-78 · `npm/git` · fixed 2.0.8 @ `766bfbedc053904ff25b47582e53e4b8a42d7484` · **IN** (signature) · denylist-to-safe-api
  - Mechanism: @npmcli/git spawned git with an opts object whose 'shell' field could be left as an arbitrary truthy value (e.g. a shell path) inherited from caller opts, and 'compensated' by manually quote-wrapping the target path (escapePath) only for the cmd.exe case; any other shell context, or an unescaped edge case, let a crafted target/repo path break out of the intended single argument and inject shell commands when spawn ran through a real shell.
  - Affected -> Fixed: npm @npmcli/git < 2.0.8 -> 2.0.8
  - Vulnerable shape (removed):
    ```
    module.exports = (opts = {}) => ({
      stdioString: true,
      ...opts,
      env: opts.env || { ...gitEnv, ...process.env }
    })
    ```
  - Guard added (post-patch):
    ```
    module.exports = (opts = {}) => ({
      stdioString: true,
      ...opts,
      shell: false,
      env: opts.env || { ...gitEnv, ...process.env }
    })
    ```
  - Reachability: lib/opts.js gitOpts() defaults, consumed by every spawn() call in lib/clone.js and friends; reached whenever @npmcli/git (used by the npm CLI) runs a git subcommand against a user-influenced repo/target path or ref.
  - Verdict: IN — Re-fetched at npm/git commit 766bfbe this session: diff confirms lib/opts.js gitOpts() now forces `shell: false` positioned AFTER the ...opts spread, so a caller-supplied shell path can no longer be inherited; accompanying tests assert shell defaults to false and cannot be overridden. Clean one-line safe-default guard forcing spawn to bind git args literally instead of routing through a shell. CWE-78.
  - Source: https://api.osv.dev/v1/vulns/GHSA-hxwm-x553-x359 ; https://github.com/npm/git/security/advisories/GHSA-hxwm-x553-x359 ; https://github.com/npm/git/pull/29 ; https://github.com/npm/git/commit/766bfbedc053904ff25b47582e53e4b8a42d7484  ·  provenance: re-verified-this-session

- **CVE-2025-49141 (GHSA-g4cf-pp4x-hqgw)** — CWE-78 · `haxtheweb/haxcms-nodejs` · fixed 11.0.3 @ `5131fea6b6be611db76a618f89bd2e164752e9b3` · **CONTESTED** (illustrative) · other
  - Mechanism: The authenticated /gitImportSite route took site.git.url from the POST body, minimally validated it (FILTER_VALIDATE_URL + must contain '.git'), and passed it into GitPlus's set_remote('origin', repoUrl) / repo.pull(), which shells out to git via proc_open() with the attacker-controlled URL, giving OS command injection.
  - Affected -> Fixed: npm @haxtheweb/haxcms-nodejs < 11.0.3 -> 11.0.3
  - Vulnerable shape (removed):
    ```
    async function gitImportSite(req, res) {
        if (HAXCMS.validateRequestToken()) {
          if ((req.body['site']['git']['url'])) {
            let repoUrl = req.body['site']['git']['url'];
            if (filter_var(repoUrl, "FILTER_VALIDATE_URL") !== false &&
              repoUrl.indexOf('.git') !== -1
              ) {
              ...
                repo.set_remote("origin", repoUrl);
                repo.pull('origin', 'master');
    ```
  - Guard added (post-patch):
    ```
    (no lines added; the entire src/routes/gitImportSite.js file was deleted, its RoutesMap.js registration and connectionSettings.js/openapi entries removed, eliminating the vulnerable endpoint rather than sanitizing its input)
    ```
  - Reachability: POST /gitImportSite handler (src/routes/gitImportSite.js), reachable by any authenticated user supplying a JWT and a site.git.url in the request body.
  - Verdict: CONTESTED — Re-fetched at haxtheweb/haxcms-nodejs commit 5131fea this session: confirmed genuine CWE-78 fix, but the remedy is a wholesale endpoint deletion (0 additions / 165 deletions — gitImportSite.js removed plus RoutesMap/connectionSettings/openapi entries stripped), NOT a sanitizer. There is no removed->added guard delta to promote as a machine-checkable signature (nothing added to match on). Real fix, kept, but promote_signature=false.
  - Source: https://api.osv.dev/v1/vulns/GHSA-g4cf-pp4x-hqgw ; https://github.com/haxtheweb/issues/security/advisories/GHSA-g4cf-pp4x-hqgw ; https://github.com/haxtheweb/haxcms-nodejs/commit/5131fea6b6be611db76a618f89bd2e164752e9b3 ; https://nvd.nist.gov/vuln/detail/CVE-2025-49141  ·  provenance: re-verified-this-session

Dropped: CVE-2025-9997 / GHSA-22q2-gf4f-hvw6 (Collector-dropped (upheld): BLMon (Schneider Electric) advisory only links a vendor PDF security notice (SEVD-2025-252-02); no source repository, PR, or commit published in the GHSA/NVD record. Version-string-only advisory, no fetchable diff.); CVE-2021-36260 (Hikvision), CVE-2022-30525 / CVE-2023-28771 (Zyxel), CVE-2020-9054 (Zyxel), CVE-2019-16920 (D-Link), CVE-2025-34037 (Linksys), CVE-2021-35394 (Realtek Jungle SDK) (Collector-dropped (upheld): closed-source embedded device firmware; seed corpus Source URLs are NVD detail pages with no linked vendor git repository, so no fix commit is fetchable without fabricating one.); CVE-2023-1389 (TP-Link Archer AX21) / CVE-2024-3400 (PAN-OS) (Collector-dropped (upheld): corpus tags these CWE-77 (mismatch for this CWE-78 bucket) and both are closed-source firmware/appliance code with no public git repo carrying the fix; excluded on CWE-mismatch + no-fetchable-diff.); CVE-2026-26832 / GHSA-8j44-735h-w4w2 (node-tesseract-ocr) (Collector-dropped (upheld): open-source npm CWE-78 match, but OSV record has no FIX reference / linked commit / PR — affected range has no 'fixed' event (last_affected: 2.2.1 only), i.e. no confirmed patch commit exists to cite. No fetchable single fix commit.)

## SQL injection  (CWE-89)

Grounds cards: skills/vulns/sql-injection
Bucket verdict: **THIN — 4 clean IN anchors (gin-vue-admin, librenms, Ghost, Django) + 1 CONTESTED (Sequelize, non-contiguous fix), below the 6-anchor bar. Dominant guard shape is bimodal by injection position: param-binding (?-placeholder + bindings) for value-position SQLi (librenms LIKE, Ghost slug value), and allowlist / exact-match validation for identifier/keyword-position SQLi that cannot be bound as a parameter (gin-vue-admin ORDER BY column, Django boolean connector, Sequelize cast type).**  ·  4 IN / 1 CONTESTED / 10 dropped  ·  4 promotable signatures
Severity-corpus join: Joins the CWE-89 SQLi severity bucket: AV:N/AC:L with C:H dominant (arbitrary DB read) is the corpus baseline; PR splits pre-auth (Ghost slug filter, ~critical) vs authenticated (librenms/gin-vue-admin, ~high), while library-level anchors (Django Q, Sequelize cast) are reachability-gated so app-dependent — matching this bucket's wide PR/scope spread in the severity corpus.

- **CVE-2024-37896** — CWE-89 · `flipped-aurora/gin-vue-admin` · fixed 2.6.6 @ `53d03382188868464ade489ab0713b54392d227f` · **IN** (signature) · exact-match-swap
  - Mechanism: The generic list-export/query builder (sys_export_template.go) reads a client-supplied 'order' query parameter and passes it straight to GORM's db.Order(order), letting an authenticated user inject arbitrary SQL into the ORDER BY clause of the generated export query.
  - Affected -> Fixed: gin-vue-admin <= 2.6.5, fixed in 2.6.6 -> 2.6.6
  - Vulnerable shape (removed):
    ```
    order := values.Get("order")
    if order != "" {
    	db = db.Order(order)
    }
    // 模板的默认order
    if order == "" && template.Order != "" {
    	db = db.Order(template.Order)
    }
    ```
  - Guard added (post-patch):
    ```
    if order == "" && template.Order != "" {
    	// 如果没有order入参，这里会使用模板的默认排序
    	order = template.Order
    }
    
    if order != "" {
    	checkOrderArr := strings.Split(order, " ")
    	orderStr := ""
    	// 检查请求的排序字段是否在字段列表中
    	if _, ok := fields[checkOrderArr[0]]; !ok {
    		return nil, "", fmt.Errorf("order by %s is not in the fields", order)
    	}
    	orderStr = checkOrderArr[0]
    	if len(checkOrderArr) > 1 {
    		if checkOrderArr[1] != "asc" && checkOrderArr[1] != "desc" {
    			return nil, "", fmt.Errorf("order by %s is not secure", order)
    		}
    		orderStr = orderStr + " " + checkOrderArr[1]
    	}
    	db = db.Order(orderStr)
    }
    ```
  - Reachability: Client-controlled 'order' query param on the generic Excel/list export builder (sys_export_template.go) -> reaches db.Order() unguarded; entrypoint is any authenticated request to a template-driven export/list endpoint that calls this shared builder.
  - Verdict: IN — Re-fetched commit 53d0338 at GitHub this session; the removed unguarded db.Order(order) is replaced by a field-name allowlist (fields[checkOrderArr[0]] membership) plus an asc/desc exact-match on the direction token — a clean, isolable ORDER BY (identifier-position) injection guard. CWE-89 confirmed via OSV/NVD. Collector's added_lines trim the fields-population (ColumnTypes) loop, but the guard itself is copied faithfully and is machine-checkable.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-37896 ; https://github.com/flipped-aurora/gin-vue-admin/commit/53d03382188868464ade489ab0713b54392d227f ; https://nvd.nist.gov/vuln/detail/cve-2024-37896  ·  provenance: re-verified-this-session

- **CVE-2024-32461** — CWE-89 · `librenms/librenms` · fixed 24.4.0 @ `d29201fce134347f891102699fbde7070debee33` · **IN** (signature) · param-binding
  - Mechanism: The package-search page (includes/html/pages/search/packages.inc.php) concatenates the raw $_POST['package'] value straight into a LIKE '%...%' clause of the SQL query, letting a globally-authenticated user perform time-based blind SQLi to extract arbitrary DB contents including admin credentials.
  - Affected -> Fixed: LibreNMS < 24.4.0 -> 24.4.0
  - Vulnerable shape (removed):
    ```
    $query .= " WHERE packages.device_id = devices.device_id AND packages.name LIKE '%" . $_POST['package'] . "%' $sql_where GROUP BY packages.name";
    ```
  - Guard added (post-patch):
    ```
    $query .= " WHERE packages.device_id = devices.device_id AND packages.name LIKE ? $sql_where GROUP BY packages.name";
    $param[] = '%' . $_POST['package'] . '%';
    ```
  - Reachability: POST /search/search=packages -> includes/html/pages/search/packages.inc.php -> 'package' POST parameter interpolated into the LIKE clause of $query (reachable by any user with LibreNMS global read privilege).
  - Verdict: IN — Re-fetched commit d29201f this session; the removed raw concatenation of $_POST['package'] into the LIKE '%...%' clause is swapped for a bound placeholder (LIKE ?) with $param[] = '%'.$_POST['package'].'%' — textbook value-position parameter binding. Hunk matches the primary source exactly; CWE-89 confirmed.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-32461 ; https://github.com/librenms/librenms/commit/d29201fce134347f891102699fbde7070debee33 ; https://nvd.nist.gov/vuln/detail/CVE-2024-32461  ·  provenance: re-verified-this-session

- **CVE-2026-26980 (GHSA-w52v-v783-gw97)** — CWE-89 · `TryGhost/Ghost` · fixed 6.19.1 @ `30868d632b2252b638bc8a4c8ebf73964592ed91` · **IN** (signature) · param-binding
  - Mechanism: The Content API's slug-array filter (filter=slug:[a,b,c]) is translated by slug-filter-order.js into an ORDER BY CASE SQL fragment where each slug value is interpolated directly into the SQL string (WHEN `table`.`slug` = 'slug' THEN i), letting an unauthenticated caller inject SQL via a crafted slug value in the filter and read arbitrary DB data.
  - Affected -> Fixed: Ghost 3.24.0 - 6.19.0 -> 6.19.1
  - Vulnerable shape (removed):
    ```
    let order = 'CASE ';
    
    orderSlugs.forEach((slug, index) => {
        order += `WHEN \`${table}\`.\`slug\` = '${slug}' THEN ${index} `;
    });
    
    order += 'END ASC';
    
    return order;
    ```
  - Guard added (post-patch):
    ```
    let caseParts = [];
    let bindings = [];
    
    orderSlugs.forEach((slug, index) => {
        caseParts.push(`WHEN \`${table}\`.\`slug\` = ? THEN ?`);
        bindings.push(slug.trim(), index);
    });
    
    return {
        sql: `CASE ${caseParts.join(' ')} END ASC`,
        bindings
    };
    ```
  - Reachability: Content API filter param slug:[...] -> slugFilterOrder() in ghost/core/core/server/api/endpoints/utils/serializers/input/utils/slug-filter-order.js builds an ORDER BY CASE clause from unsanitized slug values; reachable pre-auth via any Content-API-exposed posts/tags list endpoint that supports slug ordering.
  - Verdict: IN — Re-fetched commit 30868d6 this session; the removed WHEN `table`.`slug` = '${slug}' string interpolation in the ORDER BY CASE builder is replaced by ? placeholders plus a bindings array (slug.trim(), index) returned as {sql, bindings} — clean param-binding of a previously-injectable identifier-comparison value. Diff matches the primary source exactly; pre-auth CWE-89 per GHSA-w52v-v783-gw97.
  - Source: https://github.com/TryGhost/Ghost/security/advisories/GHSA-w52v-v783-gw97 ; https://github.com/advisories/GHSA-w52v-v783-gw97 ; https://github.com/TryGhost/Ghost/commit/30868d632b2252b638bc8a4c8ebf73964592ed91  ·  provenance: re-verified-this-session

- **CVE-2025-64459 (GHSA-frmv-pr5f-9mcr)** — CWE-89 · `django/django` · fixed 4.2.26 / 5.1.14 / 5.2.8 @ `72d2c87431f2ae0431d65d0ec792047f078c8241` · **IN** (signature) · exact-match-swap
  - Mechanism: django.db.models.query_utils.Q accepted an arbitrary '_connector' kwarg and passed it straight through to the tree.Node connector used when building the WHERE clause; a dict-expansion payload for _connector let an attacker control the SQL boolean-connector text injected between Q children, enabling SQL injection through QuerySet.filter()/exclude()/get() and Q().
  - Affected -> Fixed: Django 4.2 < 4.2.26, 5.0-5.1 < 5.1.14, 5.2 < 5.2.8 -> 4.2.26 / 5.1.14 / 5.2.8
  - Vulnerable shape (removed):
    ```
    def __init__(self, *args, _connector=None, _negated=False, **kwargs):
        super().__init__(
            children=[*args, *sorted(kwargs.items())],
            connector=_connector,
    ```
  - Guard added (post-patch):
    ```
    connectors = (None, AND, OR, XOR)
    
    def __init__(self, *args, _connector=None, _negated=False, **kwargs):
        if _connector not in self.connectors:
            connector_reprs = ", ".join(f"{conn!r}" for conn in self.connectors[1:])
            raise ValueError(f"_connector must be one of {connector_reprs}, or None.")
    ```
  - Reachability: _connector kwarg of django.db.models.query_utils.Q.__init__ -> reachable via any application code path that passes user-controlled dict/kwargs into QuerySet.filter()/exclude()/get() or constructs Q(**untrusted_dict) with dictionary expansion.
  - Verdict: IN — Re-fetched commit 72d2c87 this session; the fix is a pure insertion of an allowlist guard — class attr connectors=(None,AND,OR,XOR) plus `if _connector not in self.connectors: raise ValueError` — gating the connector before it reaches the WHERE-clause tree.Node. Note: the collector's 'removed_lines' are actually retained context (the real diff removes nothing; the guard is purely additive), but the added guard is a clean, machine-checkable exact-match/allowlist signature, so kept IN rather than penalized for a presentation nit. CWE-89 via _connector dict-expansion confirmed by GHSA-frmv-pr5f-9mcr.
  - Source: https://github.com/advisories/GHSA-frmv-pr5f-9mcr ; https://github.com/django/django/commit/72d2c87431f2ae0431d65d0ec792047f078c8241  ·  provenance: re-verified-this-session

- **CVE-2026-30951 (GHSA-6457-6jrx-69cr)** — CWE-89 · `sequelize/sequelize` · fixed 6.37.8 @ `b1475280b82159c11b829b43568da370f598a9e4` · **CONTESTED** (illustrative) · exact-match-swap
  - Mechanism: Sequelize v6's _traverseJSON() splits a JSON path key on '::' to extract a cast type for a JSON/JSONB WHERE-clause comparison, then interpolates that cast type raw into 'CAST(... AS <type>)' SQL with no validation; an attacker who controls a JSON object's keys (e.g. a where filter built from user input) can inject arbitrary SQL via the fake 'cast type' segment.
  - Affected -> Fixed: sequelize (npm, v6 line) >= 6.0.0-beta.1, < 6.37.8 -> 6.37.8
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before the CAST(...) SQL is emitted)
    const tmp = path[path.length - 1].split('::');
    cast = tmp[1];
    path[path.length - 1] = tmp[0];
    ```
  - Guard added (post-patch):
    ```
    const ALLOWED_CAST_TYPES = new Set([
      'integer','int','smallint','bigint','float','real','double precision','decimal','numeric',
      'boolean','text','char','varchar','nvarchar','date','timestamp','timestamptz','datetime',
      'json','jsonb','signed','unsigned'
    ]);
    ...
    this._validateCastType(cast);
    ...
    _validateCastType(cast) {
      if (!ALLOWED_CAST_TYPES.has(cast.toLowerCase())) {
        throw new Error(`Invalid cast type: ${cast}`);
      }
    }
    ```
  - Reachability: JSON/JSONB 'key::type' path segment parsed in _traverseJSON (lib/dialects/abstract/query-generator.js) -> reaches raw CAST(...) SQL interpolation; entrypoint is any application code that builds a Sequelize where clause from user-controlled JSON object keys against a JSON/JSONB column, across SQLite/Postgres/MySQL/MariaDB dialects.
  - Verdict: CONTESTED — Re-fetched commit b1475280 this session and confirmed the cast-type allowlist is genuine and class-matches CWE-89 (the raw cast segment is interpolated into CAST(... AS <type>)). But the fix is NON-CONTIGUOUS — spread across a module-level ALLOWED_CAST_TYPES Set (lines ~20-46), a call-site this._validateCastType(cast) inside _traverseJSON (~line 2668+), and a separately-added _validateCastType method — and the collector's hunk reflects exactly that with '(no lines removed)' and '...' elisions. It is not a single clean isolable signature, so illustrative-only (promote_signature=false). Also reclassified guard_type from the collector's 'denylist-to-safe-api' to 'exact-match-swap': the guard is an allowlist (Set membership), the opposite of a denylist.
  - Source: https://github.com/sequelize/sequelize/security/advisories/GHSA-6457-6jrx-69cr ; https://github.com/sequelize/sequelize/commit/b1475280b82159c11b829b43568da370f598a9e4 ; https://advisories.gitlab.com/pkg/npm/sequelize/CVE-2026-30951/  ·  provenance: re-verified-this-session

Dropped: CVE-2024-8465 (Collector-dropped (upheld): PHPGurukul Job Portal demo app has no OSV record (404) and no tracked git repo with a maintainer fix commit to fetch — version-string-only advisory, not admissible.); CVE-2023-34362 (Collector-dropped (upheld): Progress MOVEit Transfer is closed-source/proprietary; no public git repo or fetchable fix diff exists to verify.); CVE-2023-37196 (Collector-dropped (upheld): Schneider Electric StruxureWare Data Center Expert is proprietary; no public git repo or fetchable fix commit.); CVE-2022-33965 (Collector-dropped (upheld): WP Visitor Statistics (GHSA-cffp-89vg-h8vp) returns 404 from OSV and has no linked GitHub git history (WordPress.org SVN-only plugin) — no fetchable single fix commit.); GHSA-j86x-pjmr-9m6w (Collector-dropped (upheld): TYPO3 frontend-login SQLi (2016, TYPO3 6.2/7.6): OSV record has only ECOSYSTEM ranges and WEB references, no GIT range or FIX-type commit/PR link; pre-dates the project's GitHub-native commit history for security fixes.); CVE-2021-31777 (Collector-dropped (upheld): TYPO3 'dce' extension SQLi: OSV record has only ECOSYSTEM ranges; the only fix pointer is prose referencing a Bitbucket commit with no structured GIT range or resolvable diff URL — dropped rather than hand-reconstructed.); CVE-2026-31844 (Collector-dropped (upheld): Koha suggestion.pl SQLi: OSV's GIT 'fixed' events resolve only to autogenerated release-notes commits (credits/timestamps), not the actual code fix; no GitHub PR/commit for bug 41593 was found (Koha patches land on Bugzilla/git.koha-community.org, not reliably mirrored to GitHub with a matching SHA) — no fetchable single fix commit.); CVE-2025-66417 (Collector-dropped (upheld): GLPI unauthenticated SQLi (GHSA-p467-682w-9cc9): OSV's GIT 'fixed' event (f4258ac0a0...) resolves only to the 11.0.3 version-bump/changelog-date commit, not the actual query-building fix; the GitHub advisory has no linked commit/PR — version-string-only in practice.); CVE-2024-5225 (Collector-dropped (upheld): litellm /global/spend/logs SQLi: OSV record has no 'fixed' GIT event (only 'last_affected') and no FIX-type reference (only a huntr.com bounty link) — no resolvable fix commit.); CVE-2025-25257 (Collector-dropped (upheld): FortiWeb GUI SQLi is proprietary Fortinet firmware; no public git repo or fix diff exists.)

## Path traversal / LFI  (CWE-22 / CWE-98)

Grounds cards: skills/vulns/path-traversal-lfi
Bucket verdict: **IN -- 7 clean IN anchors (>=6 threshold) plus 2 CONTESTED (jsPDF: genuine gate entangled with a this-binding/use-strict refactor; Reposilite: genuine Location-normalization fix squashed together with an unrelated Gradle-wrapper bump, import reordering, and a Kotlin `.values()`-\>`.entries` deprecation fix across 5 files). Dominant guard shape: canonicalization -- absolutize / URL-decode / normalize / sanitize the attacker path BEFORE a containment prefix-check (nuclei filepath.Abs, Ghost decode+normalize, openemr check_file_dir_name), with a bound-containment variant (tar-fs inCwd startsWith, pip commonprefix-\>commonpath path-segment fix), a denylist->safe-API variant (hexo Page-model lookup, jsPDF permission/allowlist gate), and an allowlist-regex-anchor variant (tzinfo `^`/`$` -\> `\A`/`\z`, closing a Ruby multiline-anchor bypass of an existing identifier allowlist).**  ·  7 IN / 2 CONTESTED / 8 dropped  ·  7 promotable signatures
Severity-corpus join: Feeds the severity-corpus path-traversal/LFI bucket (CWE-22/23/98): arbitrary file read/write fixes whose real CVSS spans unauth network reads (Ghost GHSA-wf7x-fh6w-34r6 ~7.5, AV:N/PR:N/S:U; Reposilite GHSA-82j3-hf72-7x93 CVSS 3.1 7.5) through authn-scoped local reads (OpenEMR CVE-2025-29789, CVSS 4.0 PR:H/UI:A) and low-severity/limited-impact writes (pip GHSA-6vgw-5pg2-w6jp, CVSS 4.0 ~2.7, traversal bounded to install-dir prefixes) to a high-severity RCE-adjacent read (tzinfo CVE-2022-31163, CVSS 3.1 7.5, arbitrary Ruby file `require`) and untrusted-archive link-traversal write (tar-fs CVE-2024-12905) -- same bug class as the corpus CWE-22 bucket, so these anchors join it directly for the severity vector.

- **CVE-2023-37896 (GHSA-2xx4-jj5v-6mff)** — CWE-22 · `projectdiscovery/nuclei` · fixed 2.9.9 @ `e5154d362af900e83b30fb79028bfab1a7f0c648` · **IN** (signature) · canonicalization
  - Mechanism: Nuclei's Go-SDK payload loader (generator.loadPayloads) built the containment check from filepath.Dir(templatePath) without first converting templatePath to an absolute path. A relative templatePath let the naive prefix check `strings.HasPrefix(pt, templatePathDir)` be satisfied by paths outside the intended template directory, so a custom template/workflow running in 'sandbox' mode via the Go SDK could read arbitrary local files (CLI usage was unaffected).
  - Affected -> Fixed: < 2.9.9 -> 2.9.9
  - Vulnerable shape (removed):
    ```
    if sandbox {
        pt = filepath.Clean(pt)
        templatePathDir := filepath.Dir(templatePath)
    ```
  - Guard added (post-patch):
    ```
    if !allowLocalFileAccess {
        pt = filepath.Clean(pt)
        templateAbsPath, err := filepath.Abs(templatePath)
        if err != nil {
            return nil, errors.Wrap(err, "could not get absolute path")
        }
        templatePathDir := filepath.Dir(templateAbsPath)
    ```
  - Reachability: PayloadGenerator.loadPayloads() in v2/pkg/protocols/common/generators/load.go, invoked from generators.New(), entrypoint = Go-SDK caller supplying a custom templatePath/payload map while sandbox/allowLocalFileAccess is in effect.
  - Verdict: IN — Re-fetched at the commit .diff this session; hunk matches. The security delta is the added filepath.Abs(templatePath) canonicalization feeding filepath.Dir before the unchanged HasPrefix containment check (the sandbox->!allowLocalFileAccess rename is the same gate condition inverted, not an unrelated change). Clean isolable canonicalization guard, CWE-22 relative-path-traversal class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-2xx4-jj5v-6mff ; https://github.com/projectdiscovery/nuclei/security/advisories/GHSA-2xx4-jj5v-6mff ; https://github.com/projectdiscovery/nuclei/commit/e5154d362af900e83b30fb79028bfab1a7f0c648  ·  provenance: re-verified-this-session

- **CVE-2023-32235 (GHSA-wf7x-fh6w-34r6)** — CWE-22 · `TryGhost/Ghost` · fixed 5.42.1 @ `378dd913aa8d0fd0da29b0ffced8884579598b0f` · **IN** (signature) · canonicalization
  - Mechanism: The static-theme middleware's isAllowedFile() ran its allow-path/extension checks (path.extname/path.basename/startsWith('/assets/')) against the raw, still-percent-encoded request path. A crafted request like /assets/built%2F..%2F..%2F bypassed the check because the traversal sequence was hidden by URL-encoding, letting a remote attacker read arbitrary files inside the active theme's folder.
  - Affected -> Fixed: < 5.42.1 -> 5.42.1
  - Vulnerable shape (removed):
    ```
    const ext = path.extname(file);
    const base = path.basename(file);
    
    return allowedFiles.includes(base) || (file.startsWith(allowedPath) && !alwaysDeny.includes(ext));
    ```
  - Guard added (post-patch):
    ```
    const decodedFilePath = decode(file);
    if (decodedFilePath === -1) {
        return false;
    }
    
    const normalizedFilePath = path.normalize(decodedFilePath);
    ...
    const ext = path.extname(normalizedFilePath);
    const base = path.basename(normalizedFilePath);
    
    return allowedFiles.includes(base) || (normalizedFilePath.startsWith(allowedPath) && !alwaysDeny.includes(ext));
    ```
  - Reachability: isAllowedFile() in ghost/core/core/frontend/web/middleware/static-theme.js, reached from forwardToExpressStatic() which serves GET /assets/* static theme requests.
  - Verdict: IN — Re-fetched this session; hunk matches. Fix adds decode(file) URL-decode (with the -1 malformed-sequence guard) plus path.normalize BEFORE the allowedFiles/startsWith(allowedPath)/extname allow-check, defeating %2F..%2F encoded traversal. Clean isolable canonicalization guard, CWE-22 match.
  - Source: https://api.osv.dev/v1/vulns/CVE-2023-32235 ; https://github.com/TryGhost/Ghost/commit/378dd913aa8d0fd0da29b0ffced8884579598b0f ; https://nvd.nist.gov/vuln/detail/CVE-2023-32235  ·  provenance: re-verified-this-session

- **CVE-2023-39584 (GHSA-x2jc-989c-47q4)** — CWE-22 · `hexojs/hexo` · fixed 7.2.0 @ `b5b63caee27256d71a0cee8954c22375ec885d07` · **IN** (signature) · denylist-to-safe-api
  - Mechanism: The {% include_code %} tag built a raw filesystem path from the user-supplied path argument (join(ctx.source_dir, codeDir, path)) and read it directly with hexo-fs's readFile(). No containment check existed, so relative traversal sequences (or backslash-based traversal on Windows) let a blog author/template include arbitrary files from the build host's filesystem into the generated site.
  - Affected -> Fixed: < 7.2.0 -> 7.2.0
  - Vulnerable shape (removed):
    ```
    import { exists, readFile } from 'hexo-fs';
    ...
    const src = join(ctx.source_dir, codeDir, path);
    ...
    return exists(src).then(exist => {
        if (exist) return readFile(src);
    }).then(code => {
        if (!code) return;
    ```
  - Guard added (post-patch):
    ```
    const source = join(codeDir, path).replace(/\\/g, '/');
    
    // Prevent path traversal: https://github.com/hexojs/hexo/issues/5250
    const Page = ctx.model('Page');
    const doc = Page.findOne({ source });
    if (!doc) return;
    
    let code = doc.content;
    ```
  - Reachability: includeCodeTag() in lib/plugins/tag/include_code.ts, entrypoint = a Hexo source post/page rendering the {% include_code %} tag with an attacker-influenced path argument.
  - Verdict: IN — Re-fetched the commit .diff this session; confirmed a single self-contained fix commit (not a merge of unrelated work) and the hunk matches. Guard removes the arbitrary-FS-read sink (readFile(join(source_dir,codeDir,path))) and replaces it with a Page-model lookup (ctx.model('Page').findOne({source})) that only serves registered source files -- a denylist->safe-API swap. The import changes (drop readFile/exists, add url_for) are in-service of the same fix, not an unrelated refactor. CWE-22 class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-x2jc-989c-47q4 ; https://github.com/hexojs/hexo/issues/5250 ; https://github.com/hexojs/hexo/pull/5251 ; https://github.com/hexojs/hexo/commit/b5b63caee27256d71a0cee8954c22375ec885d07  ·  provenance: re-verified-this-session

- **CVE-2025-29789 (GHSA-ffpq-2wqj-v8ff)** — CWE-22 (NVD primary) / CWE-23 (GHSA secondary) · `openemr/openemr` · fixed 7.3.0 @ `8c5332f48f472b82263135da08e5379fdf1e2cb5` · **IN** (signature) · canonicalization
  - Mechanism: interface/code_systems/list_staged.php ('Load Code' feature) built a filesystem path by lower-casing and directly concatenating the attacker-controlled 'db' GET parameter onto $GLOBALS['fileroot'] . "/contrib/", with no validation, so a privileged-but-scoped user could traverse outside the contrib directory to read/reference arbitrary local files (PR:H/UI:A per the CVSS 4.0 vector).
  - Affected -> Fixed: < 7.3.0 -> 7.3.0
  - Vulnerable shape (removed):
    ```
    $mainPATH = $GLOBALS['fileroot'] . "/contrib/" . strtolower($db);
    ```
  - Guard added (post-patch):
    ```
    $mainPATH = $GLOBALS['fileroot'] . "/contrib/" . strtolower(check_file_dir_name($db));
    ```
  - Reachability: interface/code_systems/list_staged.php top-level script, param $_GET['db'], entrypoint = authenticated 'Load Code' admin feature request to list_staged.php?db=<value>.
  - Verdict: IN — Re-fetched this session; confirmed the ONLY change is the single-line sanitizer wrap of the attacker-controlled $db with check_file_dir_name() before concatenation onto fileroot/contrib/. Cleanest isolable canonicalization signature in the bucket; no unrelated changes in the diff. CWE-22/CWE-23 (relative path traversal, a child of CWE-22) in-bucket.
  - Source: https://api.osv.dev/v1/vulns/CVE-2025-29789 ; https://github.com/openemr/openemr/security/advisories/GHSA-ffpq-2wqj-v8ff ; https://github.com/openemr/openemr/commit/8c5332f48f472b82263135da08e5379fdf1e2cb5  ·  provenance: re-verified-this-session

- **CVE-2024-12905 (GHSA-pq67-2wwv-3xjx)** — CWE-22 · `mafintosh/tar-fs` · fixed 1.16.4 / 2.1.2 / 3.0.7 @ `a1dd7e7c7f4b4a8bd2ab60f513baca573b44e2ed` · **IN** (signature) · bound
  - Mechanism: tar-fs's extract() resolved the extraction cwd but never verified that hardlink/symlink targets inside a crafted tar archive stayed within that cwd (srcpath/link target was joined without a containment check), so extracting a malicious tar could follow a link outside the target directory and read/overwrite arbitrary files on disk.
  - Affected -> Fixed: < 1.16.4 (also 2.0.0-2.1.1, 3.0.0-3.0.6) -> 1.16.4 / 2.1.2 / 3.0.7
  - Vulnerable shape (removed):
    ```
    const srcpath = path.join(cwd, path.join('/', header.linkname))
    
    xfs.link(srcpath, name, function (err) {
    ```
  - Guard added (post-patch):
    ```
    cwd = path.resolve(cwd)
    ...
    const dst = path.resolve(path.dirname(name), header.linkname)
    if (!inCwd(dst)) return next(new Error(name + ' is not a valid symlink'))
    ...
    function inCwd (dst) {
      return dst.startsWith(cwd)
    }
    ```
  - Reachability: exports.extract()'s onsymlink()/onlink() handlers in index.js, entrypoint = tar-fs consumer calling extract(cwd, opts) on an attacker-supplied/untrusted tar stream.
  - Verdict: IN — Re-fetched the commit .diff this session; hunk matches. Guard adds cwd=path.resolve(cwd), a resolved dst = path.resolve(path.dirname(name), header.linkname), and the inCwd(dst)=dst.startsWith(cwd) containment check that rejects symlink/hardlink targets escaping the extraction dir. Clean isolable bound/containment guard, CWE-22 link-traversal class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-pq67-2wwv-3xjx ; https://github.com/mafintosh/tar-fs/commit/a1dd7e7c7f4b4a8bd2ab60f513baca573b44e2ed ; https://nvd.nist.gov/vuln/detail/CVE-2024-12905  ·  provenance: re-verified-this-session

- **CVE-2026-1703 (GHSA-6vgw-5pg2-w6jp)** — CWE-22 · `pypa/pip` · fixed 26.0 @ `8e227a9be4faa9594e05d02ca05a413a2a4e7735` · **IN** (signature) · bound
  - Mechanism: pip's archive-extraction containment check `is_within_directory()` computed the common path with `os.path.commonprefix([abs_directory, abs_target])`, which does a naive character-by-character string comparison rather than a path-segment comparison. A malicious wheel/sdist member whose absolute path is a string-prefix sibling of the install directory (e.g. install dir `parent/child` vs. member path `parent/childfoo`) would pass the `prefix == abs_directory` check even though `childfoo` is a sibling directory, not a descendant, letting extraction land outside the intended install directory (impact bounded to prefixes of the install path, per the advisory).
  - Affected -> Fixed: 0 - <26.0 -> 26.0
  - Vulnerable shape (removed):
    ```
    prefix = os.path.commonprefix([abs_directory, abs_target])
    return prefix == abs_directory
    ```
  - Guard added (post-patch):
    ```
    prefix = os.path.commonpath([abs_directory, abs_target])
    return prefix == abs_directory
    ```
  - Reachability: `is_within_directory(directory, target)` in src/pip/_internal/utils/unpacking.py, called once per archive member from both `unzip_file()` and `untar_file()` (each gates `fn`/`path` before writing), themselves invoked from `unpack_file()` during `pip install` of a wheel/sdist archive whose member paths are attacker-controlled.
  - Verdict: IN — Re-fetched the commit .diff this session; single-file, single-line functional change (`commonprefix` -> `commonpath`), plus a news fragment and one added test case (`("parent/child", "parent/childfoo")` -> `False`); no unrelated churn. Clean isolable bound/containment guard — fixes the containment comparison itself from char-wise to path-segment-wise, CWE-22 class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-6vgw-5pg2-w6jp ; https://github.com/pypa/pip/pull/13777 ; https://github.com/pypa/pip/commit/8e227a9be4faa9594e05d02ca05a413a2a4e7735 ; https://nvd.nist.gov/vuln/detail/CVE-2026-1703  ·  provenance: re-verified-this-session

- **CVE-2022-31163 (GHSA-5cm2-9h8c-rvfx)** — CWE-22 / CWE-23 · `tzinfo/tzinfo` · fixed 1.2.10 (also 0.3.61) @ `9905ca93abf7bf3e387bd592406e403cd18334c7` · **IN** (signature) · allowlist-anchor
  - Mechanism: `RubyDataSource#load_timezone_info(identifier)` validated the timezone identifier against `/^[A-Za-z0-9+\-_]+(\/[A-Za-z0-9+\-_]+)*$/` before passing it to `require`. Ruby's `^`/`$` anchors match line boundaries, not string boundaries, so an identifier containing an embedded newline (e.g. `"foo\n/../../../../../tmp/payload"`) satisfied the regex on its first line while the remainder of the string — including `../` traversal sequences — was carried through unchecked into the `require`d path, letting `TZInfo::Timezone.get()` load and execute an arbitrary attacker-reachable `.rb` file.
  - Affected -> Fixed: 1.0.0 - <=1.2.9 -> 1.2.10 (0.3.x line: <=0.3.60 -> 0.3.61 via companion commit 9eddbb5c0e682736f61d0dd803b6031a5db9eadf)
  - Vulnerable shape (removed):
    ```
    raise InvalidTimezoneIdentifier, 'Invalid identifier' if identifier !~ /^[A-Za-z0-9\+\-_]+(\/[A-Za-z0-9\+\-_]+)*$/
    ```
  - Guard added (post-patch):
    ```
    raise InvalidTimezoneIdentifier, 'Invalid identifier' if identifier !~ /\A[A-Za-z0-9\+\-_]+(\/[A-Za-z0-9\+\-_]+)*\z/
    ```
  - Reachability: `TZInfo::RubyDataSource#load_timezone_info(identifier)` in lib/tzinfo/ruby_data_source.rb, reached from `TZInfo::Timezone.get(identifier)`, entrypoint = any application (e.g. a Rails app with a timezone selector or file-upload flow) passing an attacker-controlled string into `Timezone.get`.
  - Verdict: IN — Re-fetched the commit .diff this session; single-file, single-line regex-anchor change plus new test assets/fixtures; no unrelated churn. Clean isolable allowlist-hardening guard — replaces multiline-matching `^`/`$` anchors with true string-boundary `\A`/`\z` anchors, closing the embedded-newline bypass of an already-present identifier allowlist. CWE-22 (relative path traversal via crafted identifier feeding a filesystem `require`) / CWE-23 (secondary) class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-5cm2-9h8c-rvfx ; https://github.com/tzinfo/tzinfo/security/advisories/GHSA-5cm2-9h8c-rvfx ; https://github.com/tzinfo/tzinfo/commit/9905ca93abf7bf3e387bd592406e403cd18334c7 ; https://nvd.nist.gov/vuln/detail/CVE-2022-31163  ·  provenance: re-verified-this-session

- **CVE-2025-68428 (GHSA-f8cm-6447-x5h2)** — CWE-22 · `parallax/jsPDF` · fixed 4.0.0 @ `a688c8f479929b24a6543b1fa2d6364abb03066d` · **CONTESTED** (illustrative) · denylist-to-safe-api
  - Mechanism: jsPDF's Node.js build loadFile()/nodeReadFile() resolved user-supplied paths with only path.resolve(url) (no symlink resolution, no allowlist, no opt-in gate) before fs.readFileSync, so any caller of addImage/html/addFont/loadFile with an attacker-influenced path argument could read arbitrary local files, with contents embedded verbatim in the generated PDF.
  - Affected -> Fixed: < 4.0.0 -> 4.0.0
  - Vulnerable shape (removed):
    ```
    url = path.resolve(url);
    ...
    if (sync) {
      try {
        result = fs.readFileSync(url, { encoding: "latin1" });
    ```
  - Guard added (post-patch):
    ```
    if (!process.permission && !this.allowFsRead) {
      throw new Error(
        "Trying to read a file from local file system. To enable this feature either run node with the --permission and --allow-fs-read flags or set the jsPDF.allowFsRead property."
      );
    }
    
    try {
      url = fs.realpathSync(path.resolve(url));
    } catch (e) { ... }
    
    if (process.permission && !process.permission.has("fs.read", url)) {
      throw new Error(`Cannot read file '${url}'. Permission denied.`);
    }
    
    if (this.allowFsRead) {
      const allowRead = this.allowFsRead.some(allowedUrl => { ... });
      if (!allowRead) {
        throw new Error(`Cannot read file '${url}'. Permission denied.`);
      }
    }
    ```
  - Reachability: nodeReadFile() in src/modules/fileloading.js, reached from jsPDF.loadFile()/addImage()/html()/addFont() when the Node.js build is used with an attacker-influenced file path.
  - Verdict: CONTESTED — Re-fetched this session; the fix is genuine and CWE-22 in-class (adds an opt-in permission/allowFsRead denylist->safe-API gate plus fs.realpathSync canonicalization before the read). But per the fetched diff the same hunk interleaves orthogonal refactor -- removes the 'use strict' directive and rebinds nodeReadFile via .call(this) -- and the guard is a large multi-statement block with '...' elisions (three separate throw-gates), i.e. entangled and not a clean single machine-checkable signature. Keep-biased downgrade: genuine fix, not cleanly isolable -> CONTESTED.
  - Source: https://api.osv.dev/v1/vulns/GHSA-f8cm-6447-x5h2 ; https://github.com/parallax/jsPDF/security/advisories/GHSA-f8cm-6447-x5h2 ; https://github.com/parallax/jsPDF/commit/a688c8f479929b24a6543b1fa2d6364abb03066d  ·  provenance: re-verified-this-session

- **CVE-2024-36117 (GHSA-82j3-hf72-7x93)** — CWE-22 · `dzikoysk/reposilite` · fixed 3.5.12 @ `e172ae4b539c822d0d6e04cf090713c7202a79d6` · **CONTESTED** (illustrative) · canonicalization
  - Mechanism: The `GET /javadoc/{repository}/<gav>/raw/<resource>` handler (`JavadocFacade.findRawJavadocResource`) resolved the attacker-controlled `<resource>` path parameter against the unpacked-javadoc directory using `it.javadocUnpackPath.resolve(resource.toString())` — a raw string concatenation with no normalization — so a `<resource>` containing `/../` sequences (URL-encoded as `%2e%2e%5c%2e%2e%2f...`) escaped `javadocUnpackPath` and read arbitrary files on the host (e.g. the `reposilite.db` credential/token store).
  - Affected -> Fixed: 3.3.0 - 3.5.11 -> 3.5.12
  - Vulnerable shape (removed):
    ```
    private val multipleSlashes = Regex("/+")
    fun of(uri: String): Location =
        uri.replace("\\", "/")
            .replace(multipleSlashes, "/")
    ...
    fun toPath(): Result<Path, String> {
        if (uri.contains("..") || uri.contains(":") || uri.contains("\\")) {
            return Result.error("Illegal path operator in URI")
        }
        return Paths.get(uri).normalize().asSuccess()
    }
    ```
  - Guard added (post-patch):
    ```
    private val multipleDirectoryOperators = Regex("\\.{2,}")
    fun of(uri: String): Location {
        return uri
            .replaceBefore(":", "")
            .replace(":", "")
            .replace(multipleDirectoryOperators, ".")
            .replace("\\", "/")
            .replace(multipleSlashes, "/")
    ...
    fun toPath(): Result<Path, String> {
        if (uri.contains(":") || uri.contains("\\") || uri.contains(multipleDirectoryOperators)) {
            return Result.error("Illegal path operator in URI")
        }
        return Paths.get(uri).normalize().asSuccess()
    }
    ```
  - Reachability: `com.reposilite.storage.api.Location` companion `of()`/`toPath()` in reposilite-backend/.../storage/api/Location.kt, consumed by `JavadocFacade.findRawJavadocResource()` (GET /javadoc/{repository}/<gav>/raw/<resource>), an unauthenticated-reachable route per the advisory PoC.
  - Verdict: CONTESTED — Re-fetched this session; the fix is genuine and CWE-22 in-class (collapses repeated `..` operators and strips `:` in `Location.of()`, replacing an incomplete `uri.contains("..")` denylist with a `multipleDirectoryOperators` regex plus continued `Paths.get(uri).normalize()`). But the single commit bundles four unrelated changes in the same diff: a Gradle-wrapper version bump (8.6->8.7), an import-order-only edit in `FrontendHandler.kt`, a Kotlin `RoutePermission.values()` -> `.entries` deprecation fix in `RouteCommands.kt`, and an AssertJ assertion-method swap in a test helper — none touch the vulnerable path. Keep-biased downgrade: genuine fix, not cleanly isolable to a single-purpose commit -> CONTESTED.
  - Source: https://api.osv.dev/v1/vulns/GHSA-82j3-hf72-7x93 ; https://github.com/dzikoysk/reposilite/security/advisories/GHSA-82j3-hf72-7x93 ; https://github.com/dzikoysk/reposilite/commit/e172ae4b539c822d0d6e04cf090713c7202a79d6 ; https://nvd.nist.gov/vuln/detail/CVE-2024-36117  ·  provenance: re-verified-this-session

Dropped: CVE-2019-11510 (Collector-dropped (pass-through): Pulse Connect Secure is closed-source appliance firmware; no public git repository or fetchable fix commit/diff exists (vendor version-string-only advisory).); CVE-2020-3452 (Collector-dropped (pass-through): Cisco ASA/FTD WebVPN is closed-source firmware; no public git repository or fetchable fix commit exists.); CVE-2025-34028 (Collector-dropped (pass-through): Commvault Command Center is closed-source software; NVD/vendor advisories give only version ranges, no fetchable git diff.); CVE-2019-16278 (Collector-dropped (pass-through): nostromo nhttpd's real upstream (nazgul.ch/SourceForge) is not git-hosted with a trackable fix commit; not present in OSV; only GitHub hits are third-party exploit-PoC repos, not the maintainer's own patch.); CVE-2025-58924 (Collector-dropped (pass-through): WordPress 'Geya' theme is SVN-hosted on wordpress.org, not git; the Patchstack/NVD advisory has no linked commit or PR diff to fetch, so no verbatim hunk is obtainable.); CVE-2025-2193 (Collector-dropped (pass-through): MRCMS/mushroom OSV record (via VulDB CNA) has only introduced/last_affected events, no 'fixed' GIT event and no FIX reference; advisory states the vendor never responded, so no patch commit exists.); CVE-2025-2917 (Collector-dropped (pass-through): ChestnutCMS: no OSV record found under this CVE id (VulDB-only, not GitHub-Advisory-Database-indexed); no resolvable fix commit located within the unauthenticated-fetch constraint.); CVE-2025-1543 (Collector-dropped (pass-through): Dreamer CMS: no OSV record found under this CVE id (VulDB CNA, no GHSA); no resolvable fix commit located.)

## Server-side template injection -> RCE  (CWE-1336 / CWE-94)

Grounds cards: skills/vulns/server-side-template-injection
Bucket verdict: **IN (8 clean IN anchors, >=6). Dominant guard shape splits two ways: (1) escape / JSON-stringify / identifier-allowlist the untrusted value before it is concatenated into compiled template source -- handlebars depthedLookup (JSON.stringify), ejs & smarty (JS/PHP identifier regex), pug (whitespace-only pretty + stringify), prestashop (raw-string wrap); (2) wrap the whole render in a Twig/Jinja sandbox with an allowlist -- cachet (Twig SecurityPolicy), dynaconf (SandboxedEnvironment); with grav a regex denylist variant. CVE-2026-33938 (handlebars AST type-confusion) held out as CONTESTED: genuine deser-type-filter guard but inside a multi-CVE omnibus SHA with a spliced/elided hunk, so not promoted.**  ·  8 IN / 1 CONTESTED / 6 dropped  ·  8 promotable signatures
Severity-corpus join: Joins the CWE-94/1336 template/code-injection severity bucket: SSTI->RCE, network vector / low attack complexity; unauthenticated or config-source cases (dynaconf, ejs, pug, handlebars compile-option) cluster Critical (~9.0-9.8), while authenticated template-author cases (cachet, grav, prestashop admin, smarty multi-tenant) cluster High (~7.2-8.8, PR:L raising complexity), consistent with the same-class vectors in the severity corpus.

- **CVE-2021-23369 (GHSA-f2jv-r9rf-7988)** — CWE-94 · `handlebars-lang/handlebars.js` · fixed 4.7.7 @ `f0589701698268578199be25285b2ebea1c1e427` · **IN** (signature) · canonicalization
  - Mechanism: JavaScriptCompiler.depthedLookup() built the generated function body by directly splicing the raw path/name string into `container.lookup(depths, "<name>")`; a name containing a `"` plus JS syntax breaks out of the string literal in the compiled source and executes during compilation/render (compat-mode lookup).
  - Affected -> Fixed: npm handlebars 0 - <4.7.7 -> 4.7.7
  - Vulnerable shape (removed):
    ```
    depthedLookup: function(name) {
        return [this.aliasable('container.lookup'), '(depths, "', name, '")'];
      },
    ```
  - Guard added (post-patch):
    ```
    depthedLookup: function(name) {
        return [
          this.aliasable('container.lookup'),
          '(depths, ',
          JSON.stringify(name),
          ')'
        ];
      },
    ```
  - Reachability: JavaScriptCompiler.prototype.depthedLookup(name) -> generated function body handed to the internal Function constructor by createFunctionContext; entrypoint Handlebars.compile(untrustedTemplateSource) compiling a template with an attacker-influenced helper/path name.
  - Verdict: IN — Re-fetched this session: commit touches only javascript-compiler.js + spec/security.js + package-lock. Clean single-function canonicalization guard: the raw `name` splice into '(depths, "' + name + '")' is replaced by JSON.stringify(name), escaping the string-literal break-out. Mechanism = CWE-94 code injection into compiled template JS; class-matches the bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-f2jv-r9rf-7988 ; https://github.com/advisories/GHSA-f2jv-r9rf-7988 ; https://github.com/handlebars-lang/handlebars.js/commit/f0589701698268578199be25285b2ebea1c1e427 ; https://nvd.nist.gov/vuln/detail/CVE-2021-23369  ·  provenance: re-verified-this-session

- **CVE-2026-33938 (GHSA-3mfm-83xf-c92r)** — CWE-843 / CWE-94 · `handlebars-lang/handlebars.js` · fixed 4.7.9 @ `68d8df5a88e0a26fe9e6084c5c6aaebe67b07da2` · **CONTESTED** (illustrative) · deser-type-filter
  - Mechanism: A registered helper can overwrite the mutable `@partial-block` data-frame entry with an attacker-controlled object shaped like a Handlebars AST node (a PathExpression whose `depth` is a crafted string instead of an integer); parseWithoutProcessing() trusted any pre-parsed 'Program' AST verbatim, so when `{{> @partial-block}}` compiled the object, the type-confused `depth` string was spliced into generated JS and executed.
  - Affected -> Fixed: npm handlebars 4.0.0 - <=4.7.8 -> 4.7.9
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before the AST is trusted) -- original: `if (input.type === 'Program') { return input; }` returned/trusted any pre-parsed AST with no structural validation.
    ```
  - Guard added (post-patch):
    ```
    if (input.type === 'Program') {
        // When a pre-parsed AST is passed in, validate all node values to prevent
        // code injection via type-confused literals.
        validateInputAst(input);
        return input;
      }
    ...
    if (node.type === 'PathExpression') {
        if (!isValidDepth(node.depth)) {
          throw new Exception(
            'Invalid AST: PathExpression.depth must be an integer'
          );
        }
    ```
  - Reachability: parseWithoutProcessing(input) in lib/handlebars/compiler/base.js, reached whenever a pre-parsed AST-shaped object flows into partial-block resolution (invokePartial/resolvePartial) via `{{#>...}}...{{>@partial-block}}` combined with a helper that mutates @_parent/data context (e.g. handlebars-helpers `merge`).
  - Verdict: CONTESTED — Fix is genuine and re-fetched (validateInputAst/isValidDepth added to base.js; parseWithoutProcessing now validates a pre-parsed Program AST; PathExpression.depth must be an integer). BUT the whole-fix SHA is a multi-CVE omnibus (WebFetch confirms 20 files, +541/-38, message references several GHSAs), and the collector's added hunk is spliced from two non-contiguous sites (the parseWithoutProcessing guard + the PathExpression.depth check inside validateAstNode) with a '...' elision. The deser-type-filter guard is identifiable but not a single clean contiguous delta -> keep as illustrative, do not promote.
  - Source: https://api.osv.dev/v1/vulns/GHSA-3mfm-83xf-c92r ; https://github.com/handlebars-lang/handlebars.js/security/advisories/GHSA-3mfm-83xf-c92r ; https://github.com/handlebars-lang/handlebars.js/commit/68d8df5a88e0a26fe9e6084c5c6aaebe67b07da2 ; https://nvd.nist.gov/vuln/detail/CVE-2026-33938  ·  provenance: re-verified-this-session

- **CVE-2022-29078 (GHSA-phwq-j96m-2c2q)** — CWE-94 · `mde/ejs` · fixed 3.1.7 @ `15ee698583c98dadc456639d6245580d17a24baf` · **IN** (signature) · other
  - Mechanism: `settings[view options][outputFunctionName]` (and localsName/destructuredLocals) was spliced unescaped into the JS source string built for the compiled template function (`'  var ' + opts.outputFunctionName + ' = __append;\n'`); an attacker controlling this compile option (e.g. Express view-options populated from request data) injects arbitrary JS that executes when the template compiles/renders.
  - Affected -> Fixed: npm ejs 0 - <3.1.7 (reported vulnerable at 3.1.6) -> 3.1.7
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before splice) -- unguarded: `if (opts.outputFunctionName) { prepended += '  var ' + opts.outputFunctionName + ' = __append;' + '\n'; }`
    ```
  - Guard added (post-patch):
    ```
    var _JS_IDENTIFIER = /^[a-zA-Z_$][0-9a-zA-Z_$]*$/;
    ...
    if (opts.outputFunctionName) {
            if (!_JS_IDENTIFIER.test(opts.outputFunctionName)) {
              throw new Error('outputFunctionName is not a valid JS identifier.');
            }
            prepended += '  var ' + opts.outputFunctionName + ' = __append;' + '\n';
          }
    ```
  - Reachability: Template.prototype.compile in lib/ejs.js, building the 'prepended' function-body string from opts.outputFunctionName / opts.localsName / opts.destructuredLocals[i] -- entrypoint ejs.compile(str, opts) / ejs.render() when user-controlled view options flow through (e.g. Express settings[view options][outputFunctionName]).
  - Verdict: IN — Re-fetched this session (lib/ejs.js + test only). Adds the _JS_IDENTIFIER allowlist regex and rejects non-identifier outputFunctionName / localsName / destructuredLocals before they are concatenated into the compiled function source. guard_type = identifier-allowlist validation ('other'). CWE corrected: NVD primary tags parent CWE-74, but the mechanism is unambiguous CWE-94 code injection into compiled template JS -> class-matches the bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-phwq-j96m-2c2q ; https://github.com/advisories/GHSA-phwq-j96m-2c2q ; https://github.com/mde/ejs/commit/15ee698583c98dadc456639d6245580d17a24baf ; https://nvd.nist.gov/vuln/detail/CVE-2022-29078  ·  provenance: re-verified-this-session

- **CVE-2021-21353 (GHSA-p493-635q-r6gr)** — CWE-74 / CWE-94 · `pugjs/pug` · fixed pug-code-gen 2.0.3 / 3.0.2 (pug 3.0.1) @ `991e78f7c4220b2f8da042877c6f0ef5a4683be0` · **IN** (signature) · canonicalization
  - Mechanism: Compiler.visitMixinBlock/visitMixin built `"pug_indent.push('" + Array(this.indents+1).join(this.pp) + "');"` by concatenating the compile-time `pretty` (`pp`) option directly into generated JS inside a single-quoted string; a `pp` value containing `'` and JS breaks out of the literal and executes in the render function.
  - Affected -> Fixed: npm pug-code-gen 0 - <2.0.3 and 3.0.0 - <3.0.2 -> pug-code-gen 2.0.3 / 3.0.2 (pug 3.0.1)
  - Vulnerable shape (removed):
    ```
    if (this.pp)
          this.buf.push(
            "pug_indent.push('" + Array(this.indents + 1).join(this.pp) + "');"
          );
    ```
  - Guard added (post-patch):
    ```
    if (this.pp && !/^\s+$/.test(this.pp)) {
        throw new Error(
          'The pretty parameter should either be a boolean or whitespace only string'
        );
      }
    ...
    if (this.pp)
          this.buf.push(
            'pug_indent.push(' +
              stringify(Array(this.indents + 1).join(this.pp)) +
              ');'
          );
    ```
  - Reachability: pug-code-gen Compiler constructor and visitMixinBlock/visitMixin in packages/pug-code-gen/index.js -- entrypoint pug.compile(source, options) where options.pretty is attacker-influenced (e.g. `...req.query` spread into compile options).
  - Verdict: IN — Re-fetched this session (single file packages/pug-code-gen/index.js). Rejects a non-whitespace `pretty` (pp) option and switches the pug_indent.push() emission to stringify(...), escaping the single-quote break-out. Clean isolable canonicalization+validation guard; CWE-94 code injection matches the bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-p493-635q-r6gr ; https://github.com/pugjs/pug/security/advisories/GHSA-p493-635q-r6gr ; https://github.com/pugjs/pug/commit/991e78f7c4220b2f8da042877c6f0ef5a4683be0 ; https://nvd.nist.gov/vuln/detail/CVE-2021-21353  ·  provenance: re-verified-this-session

- **CVE-2024-28119 (GHSA-2m7x-c7px-hp58)** — CWE-94 · `getgrav/grav` · fixed 1.7.45 @ `de1ccfa12dbcbf526104d68c1a6bc202a98698fe` · **IN** (signature) · denylist-to-safe-api
  - Mechanism: Grav exposed the internal Twig environment (`grav.twig.twig.extensions.core`) to page/front-matter Twig; because Twig's EscaperExtension::setEscaper() accepts any PHP callable, an admin-context template author could call `grav.twig.twig.extensions.core.setEscaper('system','system')` to redefine the escaper to `system`, achieving code execution when the escape filter later runs in unsandboxed Twig.
  - Affected -> Fixed: Packagist getgrav/grav 0 - <1.7.45 -> 1.7.45
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard added as a pre-render filter) -- unguarded path: `$content = $item->content();` fed directly into Twig::setTemplate/render with no filtering.
    ```
  - Guard added (post-patch):
    ```
    $bad_twig = [
                'twig_array_map',
                'twig_array_filter',
                'call_user_func',
                'registerUndefinedFunctionCallback',
                'undefined_functions',
                'twig.getFunction',
                'core.setEscaper',
            ];
            $string = preg_replace('/(({{\s*|{%\s*)[^}]*?(' . implode('|', $bad_twig) . ')[^}]*?(\s*}}|\s*%}))/i', '{# $1 #}', $string);
    ...
    $content = Security::cleanDangerousTwig($content);
    ```
  - Reachability: Twig::processPage / processString / processSite in system/src/Grav/Common/Twig/Twig.php rendering page content/front-matter -- entrypoint any admin/editor-authored page content processed by Grav's Twig engine.
  - Verdict: IN — Re-fetched this session (Security.php + Twig.php). Adds Security::cleanDangerousTwig() -- a regex denylist that comments out core.setEscaper/call_user_func/etc. -- called in processPage/processString/processSite before Twig render. Denylist-only guard (fragile / bypass-prone) but it is the genuine, isolable whole-fix for the exposed-Twig-env SSTI; CWE-94 matches. Signature keys on the cleanDangerousTwig call site.
  - Source: https://api.osv.dev/v1/vulns/GHSA-2m7x-c7px-hp58 ; https://github.com/getgrav/grav/security/advisories/GHSA-2m7x-c7px-hp58 ; https://github.com/getgrav/grav/commit/de1ccfa12dbcbf526104d68c1a6bc202a98698fe ; https://nvd.nist.gov/vuln/detail/CVE-2024-28119  ·  provenance: re-verified-this-session

- **CVE-2022-21686 (GHSA-mrq4-7ch7-2465)** — CWE-94 · `PrestaShop/PrestaShop` · fixed 1.7.8.3 @ `d02b469ec365822e6a9f017e57f588966248bf21` · **IN** (signature) · canonicalization
  - Mechanism: LayoutExtension::getLegacyLayout() took the legacy admin .tpl layout's raw content (including an admin-editable `currentIndex` value) and spliced Twig block markers into it via plain str_replace, returning the combined string to be compiled as Twig source; any Twig syntax in that legacy content was parsed and executed, yielding RCE in an admin session.
  - Affected -> Fixed: Packagist prestashop/prestashop 1.7.0.0 - 1.7.8.2 -> 1.7.8.3
  - Vulnerable shape (removed):
    ```
    $content = str_replace(
                [
                    '{$content}',
                    'var currentIndex = \'index.php\';',
                    '</head>',
                    '</body>',
                ],
                [ ... ],
                $layout
            );
    ...
            return $content;
    ```
  - Guard added (post-patch):
    ```
    private function escapeSmarty(string $template): string
        {
            return '{{ \'' . addslashes($template) . '\' | raw }}';
        }
    ```
  - Reachability: PrestaShopBundle\Twig\LayoutExtension::getLegacyLayout() -- entrypoint legacy admin back-office layout rendering (1.7.0.0-1.7.8.2) using a Twig-wrapped legacy .tpl theme.
  - Verdict: IN — Re-fetched this session (single file LayoutExtension.php); WebFetch confirms the change is strictly confined to escaping legacy layout content with NO unrelated refactor. New escapeSmarty() wraps untrusted legacy content as a raw string literal ('{{ '...addslashes(...)...' | raw }}') so it is no longer parsed as Twig -- canonicalization guard, CWE-94 matches. Collector removed_lines carries a '[ ... ]' elision of the str_replace replacement array, but the added escapeSmarty method is the clean, machine-checkable signature.
  - Source: https://api.osv.dev/v1/vulns/GHSA-mrq4-7ch7-2465 ; https://github.com/PrestaShop/PrestaShop/security/advisories/GHSA-mrq4-7ch7-2465 ; https://github.com/PrestaShop/PrestaShop/commit/d02b469ec365822e6a9f017e57f588966248bf21 ; https://nvd.nist.gov/vuln/detail/CVE-2022-21686  ·  provenance: re-verified-this-session

- **CVE-2021-26120 (GHSA-3rpf-5rqv-689q)** — CWE-94 · `smarty-php/smarty` · fixed 3.1.39 @ `165f1bd4d2eec328cfeaca517a725b46001de838` · **IN** (signature) · other
  - Mechanism: `{function name='...'}` compiled the raw, template-author-suppliable function name directly into generated PHP function-definition code with no character-set validation; a `name` containing PHP syntax (e.g. `'rce(){};echo "hi";function '`) closes the generated function definition early and injects arbitrary PHP that executes when the template compiles/runs.
  - Affected -> Fixed: Packagist smarty/smarty 0 - <3.1.39 -> 3.1.39
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before use) -- unguarded: `$_name = trim($_attr[ 'name' ], '\'"'); ... $compiler->parent_compiler->tpl_function[ $_name ] = array();`
    ```
  - Guard added (post-patch):
    ```
    if (!preg_match('/^[a-zA-Z0-9_\x80-\xff]+$/', $_name)) {
    	        $compiler->trigger_template_error("Function name contains invalid characters: {$_name}", null, true);
            }
    ```
  - Reachability: Smarty_Internal_Compile_Function::compile() in libs/sysplugins/smarty_internal_compile_function.php, using $_attr['name'] to build the compiled PHP function name -- entrypoint any `{function name=...}{/function}` tag where the template author is untrusted (multi-tenant Smarty).
  - Verdict: IN — Re-fetched this session (smarty_internal_compile_function.php + test). Adds preg_match('/^[a-zA-Z0-9_\x80-\xff]+$/', $_name) rejecting non-identifier {function name=...} before it is compiled into a PHP function definition. Clean isolable identifier-allowlist validation guard ('other'); CWE-94 code injection matches the bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-3rpf-5rqv-689q ; https://github.com/smarty-php/smarty/security/advisories/GHSA-3rpf-5rqv-689q ; https://github.com/smarty-php/smarty/commit/165f1bd4d2eec328cfeaca517a725b46001de838 ; https://nvd.nist.gov/vuln/detail/CVE-2021-26120  ·  provenance: re-verified-this-session

- **CVE-2023-43661 (GHSA-hv79-p62r-wg3p)** — CWE-74 / CWE-94 · `cachethq/cachet` · fixed 2.4 @ `6fb043e109d2a262ce3974e863c54e9e5f5e0587` · **IN** (signature) · template-sandbox
  - Mechanism: CreateIncidentCommandHandler::parseTemplate() / UpdateIncidentCommandHandler compiled an authenticated user's incident `template` field with a bare Twig_Environment (no sandbox, no filter/function/method allowlist) and rendered it with incident data; a non-admin could submit `{{ ['curl ...','']|sort('system') }}` to invoke arbitrary PHP callables via Twig's sort/reduce filters -> authenticated RCE via POST /api/v1/incidents.
  - Affected -> Fixed: Packagist cachethq/cachet 0 - <2.4 -> 2.4
  - Vulnerable shape (removed):
    ```
    $env = new Twig_Environment(new Twig_Loader_Array([]));
            $template = $env->createTemplate($template->template);
    ...
            return $template->render($vars);
    ```
  - Guard added (post-patch):
    ```
    $policy = new \Twig\Sandbox\SecurityPolicy($this->twigConfig["tags"], 
            $this->twigConfig["filters"],
            $this->twigConfig["methods"],
            $this->twigConfig["props"], 
            $this->twigConfig["functions"]);
    
            $sandbox = new \Twig\Extension\SandboxExtension($policy);
    ...
            return $template->render('secondStageLoader', $vars);
    // config/cachet.php: 'twig' => ['methods'=>[], 'functions'=>[], 'filters'=>['escape'], 'tags'=>['if'], 'props'=>[]]
    ```
  - Reachability: CreateIncidentCommandHandler::parseTemplate() / UpdateIncidentCommandHandler::parseTemplate() in app/Bus/Handlers/Commands/Incident/ -- entrypoint POST /api/v1/incidents (or update equivalent) with an incident template containing Twig syntax, using any user's API token.
  - Verdict: IN — Re-fetched this session (Create/UpdateIncidentCommandHandler.php + config/cachet.php). Wraps user incident-template rendering in a Twig SecurityPolicy/SandboxExtension with an empty methods/functions allowlist (only 'escape' filter, 'if' tag). Clean isolable template-sandbox guard; authenticated SSTI->RCE, CWE-94 matches the bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-hv79-p62r-wg3p ; https://github.com/cachethq/cachet/security/advisories/GHSA-hv79-p62r-wg3p ; https://github.com/cachethq/cachet/commit/6fb043e109d2a262ce3974e863c54e9e5f5e0587 ; https://nvd.nist.gov/vuln/detail/CVE-2023-43661  ·  provenance: re-verified-this-session

- **CVE-2026-33154 (GHSA-pxrr-hq57-q35p)** — CWE-1336 / CWE-94 / CWE-78 · `dynaconf/dynaconf` · fixed 3.2.13 @ `2fbb45ee36b8c0caa5b924fe19f3c1a5e8603fa7` · **IN** (signature) · template-sandbox
  - Mechanism: The `@jinja` resolver rendered attacker-influenced configuration-value strings (env vars, .env files, CI/CD secrets) with a plain, unsandboxed jinja2.Environment; because Jinja2's default environment permits attribute traversal to __globals__/__builtins__, a value like `@jinja {{ cycler.__init__.__globals__.os.popen('id').read() }}` reaches os.popen and executes OS commands when Dynaconf resolves the setting.
  - Affected -> Fixed: PyPI dynaconf 0 - <=3.2.12 -> 3.2.13
  - Vulnerable shape (removed):
    ```
    from jinja2 import Environment
    
        jinja_env = Environment()
    ...
    def _jinja_formatter(value, **context):
        if jinja_env is None:  # pragma: no cover
            raise ImportError(
                "jinja2 must be installed to enable '@jinja' settings in dynaconf"
            )
        return jinja_env.from_string(value).render(**context)
    ```
  - Guard added (post-patch):
    ```
    import jinja2
        from jinja2.sandbox import SandboxedEnvironment
    
        jinja_env = SandboxedEnvironment()
    ...
    def _jinja_formatter(value: str, **context) -> str:
        if jinja_env is None:  # pragma: no cover
            raise ImportError(
                "jinja2 must be installed to enable '@jinja' settings in dynaconf"
            )
        try:
            return jinja_env.from_string(value).render(**context)
        except jinja2.exceptions.SecurityError:
            warnings.warn(f"Unsafe access attempt to: {value}")
            return ""
    ```
  - Reachability: _jinja_formatter() in dynaconf/utils/parse_conf.py, invoked by the @jinja string-resolver whenever a setting value is accessed -- entrypoint any config source (env var, .env, secrets file) Dynaconf loads and lazily resolves.
  - Verdict: IN — Re-fetched this session (parse_conf.py + base.py + tests). Swaps jinja2.Environment() for jinja2.sandbox.SandboxedEnvironment() in the @jinja resolver and catches jinja2 SecurityError. Clean isolable template-sandbox swap; CWE-94/1336 (unsandboxed Jinja2 on attacker-influenced config values -> RCE) matches the bucket.
  - Source: https://api.osv.dev/v1/vulns/GHSA-pxrr-hq57-q35p ; https://github.com/dynaconf/dynaconf/security/advisories/GHSA-pxrr-hq57-q35p ; https://github.com/dynaconf/dynaconf/commit/2fbb45ee36b8c0caa5b924fe19f3c1a5e8603fa7 ; https://nvd.nist.gov/vuln/detail/CVE-2026-33154  ·  provenance: re-verified-this-session

Dropped: CVE-2021-43466 (GHSA-qcj6-jqrg-4wp2, thymeleaf-spring5) (Collector-dropped (concur): OSV record has no FIX-type reference and no GIT range; only refs are an NVD page and a GitHub issue comment (thymeleaf/thymeleaf-spring#263). No single re-fetchable fix commit/PR to extract verbatim hunks from -> unverifiable.); CVE-2025-14700 (Crafty Controller) (Collector-dropped (concur): OSV GIT range has only introduced/last_affected on the same commit with no 'fixed' event; only other ref is a GitLab issue (crafty-4#646) with no linked merge/fix commit -> no fetchable diff, unverifiable.); CVE-2019-3396 (Atlassian Confluence Widget Connector) (Collector-dropped (concur): closed-source commercial product; NVD-only record, no linked git repo/GHSA/fix commit -> nothing public to fetch a diff from, unverifiable.); CVE-2019-11581 (Atlassian Jira ContactAdministrators/SendBulkMail) (Collector-dropped (concur): closed-source commercial product; NVD-only, no OSV/GHSA, no linked git repo or fix commit -> unverifiable.); CVE-2017-12611 (Apache Struts 2 S2-053) (Collector-dropped (concur): NVD-only record predating GHSA/OSV coverage; no OSV entry and no single re-fetchable GitHub fix SHA identifiable from an unauthenticated public source within scope -> unverifiable as a clean signature.); CVE-2024-34359 (llama-cpp-python, GHSA-56xg-wfcc-g829) (Collector-dropped (concur): fix commit is real/fetchable (b454f40a9a1787b2b5659cd2cb00819d983185df) but the PRIMARY GHSA assigns CWE-76, not CWE-94/1336. Class-match is by CWE on the primary record -> out of this bucket despite the SSTI-like unsandboxed-Jinja2 mechanism.)

## XXE  (CWE-611)

Grounds cards: skills/vulns/xxe-injection
Bucket verdict: **IN — 6 clean, re-fetchable anchors, all independently re-verified at primary source this session, 0 CONTESTED. Dominant guard shape is entity-expansion-off: setFeature/setProperty disabling DTD-decl + load-external-dtd + external general/parameter entities (dom4j, jackson-databind, jackson-dataformat-xml, tika, jenkins flaky-test-handler), plus the equivalent binding of a restrictive EntityResolver in place of null (geoserver). Two variants: direct feature/property disabling on the factory/reader, and a swap to a safe-default factory (SAXReader.createDefault()).**  ·  6 IN / 0 CONTESTED / 7 dropped  ·  6 promotable signatures
Severity-corpus join: Joins the same-class CWE-611 severity-corpus bucket: dominant CVSS 3.1 shape AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N (~7.5, file-read/SSRF confidentiality impact); unauthenticated/library-default sinks (dom4j default reader, jackson XmlMapper/DOMDeserializer, geoserver WMS GetMap) anchor the high end, while document-parse sinks (tika PDF-XFA, jenkins report ingest) sit mid-range on more constrained reachability.

- **CVE-2020-10683 (GHSA-hwj3-m3p6-hj38)** — CWE-611 · `dom4j/dom4j` · fixed 2.0.3 / 2.1.3 @ `a8228522a99a02146106672a34c104adbda5c658` · **IN** (signature) · entity-expansion-off
  - Mechanism: org.dom4j.DocumentHelper.parseText(String), a public static convenience method any app calls to parse untrusted XML text, built its SAXReader via `new SAXReader()` and then tried to disable external-DTD/entity features inline, silently swallowing SAXException and falling back to the parser's unsafe defaults (comment: 'Parse with external resources downloading allowed'). No shared safe-default factory existed, so other SAXReader construction paths stayed default-open to external entity/DTD resolution.
  - Affected -> Fixed: < 2.0.3, and 2.1.0 - 2.1.2 -> 2.0.3 / 2.1.3
  - Vulnerable shape (removed):
    ```
    SAXReader reader = new SAXReader();
    try {
        reader.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        reader.setFeature("http://xml.org/sax/features/external-general-entities", false);
        reader.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    } catch (SAXException e) {
        //Parse with external resources downloading allowed.
    }
    ```
  - Guard added (post-patch):
    ```
    SAXReader reader = SAXReader.createDefault();
    
    ... (new factory method in SAXReader.java) ...
    
    public static SAXReader createDefault() {
      SAXReader reader = new SAXReader();
      try {
        reader.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        reader.setFeature("http://xml.org/sax/features/external-general-entities", false);
        reader.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
      } catch (SAXException e) {
        // nothing to do, incompatible reader
      }
      return reader;
    }
    ```
  - Reachability: org.dom4j.DocumentHelper.parseText(String) — static helper for parsing untrusted XML text, now delegates to the new SAXReader.createDefault() factory instead of an inline, exception-swallowing feature-set attempt on a plain `new SAXReader()`.
  - Verdict: IN — Re-fetched the commit this session: the inline exception-swallowing feature-set at DocumentHelper.parseText is replaced by SAXReader.createDefault(), a shared safe-default factory that disables load-external-dtd / external-general-entities / external-parameter-entities. Clean, isolable entity-expansion-off swap (new SAXReader() -> createDefault()); advisory and diff agree; CWE-611 XXE class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-hwj3-m3p6-hj38 ; https://nvd.nist.gov/vuln/detail/CVE-2020-10683 ; https://github.com/dom4j/dom4j/commit/a8228522a99a02146106672a34c104adbda5c658  ·  provenance: re-verified-this-session

- **CVE-2025-58360 (GHSA-fjf5-xgmq-5525)** — CWE-611 · `geoserver/geoserver` · fixed 2.25.6 / 2.26.2 / 2.27.0 @ `ebe34ef8495e328b3d989bfc9020b91ed35c7133` · **IN** (signature) · entity-expansion-off
  - Mechanism: org.geoserver.sld.SLDXmlRequestReader.read() parsed the POST/SLD body of an unauthenticated WMS GetMap request by calling the style-format handler's parse() with a null EntityResolver, so external entity references inside the StyledLayerDescriptor XML (e.g. in a <Name>) were resolved by the underlying parser, confirmed by the fix commit's own added regression test using `<!ENTITY xxe SYSTEM "file:///some/file">`.
  - Affected -> Fixed: < 2.25.6, and 2.26.0 - 2.26.1 -> 2.25.6 / 2.26.2 / 2.27.0
  - Vulnerable shape (removed):
    ```
    StyledLayerDescriptor sld =
            Styles.handler(getMap.getStyleFormat()).parse(reader, getMap.styleVersion(), null, null);
    ```
  - Guard added (post-patch):
    ```
    EntityResolver entityResolver = wms.getCatalog().getResourcePool().getEntityResolver();
    
    StyledLayerDescriptor sld = styleParser.parse(reader, styleVersion, null, entityResolver);
    ```
  - Reachability: org.geoserver.sld.SLDXmlRequestReader.read(Object, Reader, Map) — reached via the unauthenticated WMS GetMap operation (/geoserver/wms) when an SLD body is supplied.
  - Verdict: IN — Re-fetched the commit this session: the style parse() call is changed from a hardcoded null EntityResolver to a restrictive EntityResolver pulled from the catalog ResourcePool, suppressing external-entity resolution on the unauthenticated WMS GetMap SLD path. Clean, isolable entity-resolver binding guard; CWE-611 XXE class-match (guard achieves entity-expansion-off).
  - Source: https://api.osv.dev/v1/vulns/GHSA-fjf5-xgmq-5525 ; https://github.com/geoserver/geoserver/security/advisories/GHSA-fjf5-xgmq-5525 ; https://github.com/geoserver/geoserver/commit/ebe34ef8495e328b3d989bfc9020b91ed35c7133  ·  provenance: re-verified-this-session

- **CVE-2020-25649** — CWE-611 · `FasterXML/jackson-databind` · fixed 2.11.0 (backported to 2.9.10.5, 2.10.5.1) @ `612f971b78c60202e9cd75a299050c8f2d724a59` · **IN** (signature) · entity-expansion-off
  - Mechanism: DOMDeserializer's static, shared DocumentBuilderFactory (DEFAULT_PARSER_FACTORY) only called setExpandEntityReferences(false), which does not fully suppress external DTD/entity resolution on all JAXP implementations, so deserializing untrusted XML into an org.w3c.dom.Document/Node-typed bean field via ObjectMapper remained exploitable for XXE.
  - Affected -> Fixed: before 2.9.10.5 / 2.10.5.1 / 2.11.0 -> 2.11.0 (backported to 2.9.10.5, 2.10.5.1)
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted directly after the existing setExpandEntityReferences(false) try/catch block, before `DEFAULT_PARSER_FACTORY = parserFactory;`)
    ```
  - Guard added (post-patch):
    ```
    // [databind#2589] add two more settings just in case
    try {
        parserFactory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    } catch (Throwable t) { } // as per previous one, nothing much to do
    try {
        parserFactory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
    } catch (Throwable t) { } // as per previous one, nothing much to do
    ```
  - Reachability: com.fasterxml.jackson.databind.ext.DOMDeserializer static initializer (DEFAULT_PARSER_FACTORY) — reached by any ObjectMapper.readValue() call that deserializes untrusted XML/JSON into an org.w3c.dom.Document/Node field.
  - Verdict: IN — Re-fetched the commit this session: confirms insertion of disallow-doctype-decl=true and load-external-dtd=false setFeature calls on DEFAULT_PARSER_FACTORY (the prior setExpandEntityReferences(false) was insufficient across JAXP impls). Insertion-only but a clean, isolable, machine-checkable entity-expansion-off guard; CWE-611 XXE class-match.
  - Source: https://api.osv.dev/v1/vulns/CVE-2020-25649 ; https://github.com/FasterXML/jackson-databind/issues/2589 ; https://github.com/FasterXML/jackson-databind/commit/612f971b78c60202e9cd75a299050c8f2d724a59  ·  provenance: re-verified-this-session

- **CVE-2016-3720 (GHSA-hmq6-frv3-4727)** — CWE-611 · `FasterXML/jackson-dataformat-xml` · fixed 2.7.4 @ `f0f19a4c924d9db9a1e2830434061c8640092cc0` · **IN** (signature) · entity-expansion-off
  - Mechanism: XmlFactory's default construction path created a bare `XMLInputFactory.newInstance()` with no entity-expansion restrictions, so every XmlMapper.readValue() call against untrusted XML used a StAX parser that resolved external general entities by default, enabling classic file-read/SSRF XXE.
  - Affected -> Fixed: < 2.7.4 -> 2.7.4
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted immediately after: `xmlIn = XMLInputFactory.newInstance();`)
    ```
  - Guard added (post-patch):
    ```
    xmlIn = XMLInputFactory.newInstance();
    // as per [dataformat-xml#190], disable external entity expansion by default
    xmlIn.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, Boolean.FALSE);
    ```
  - Reachability: com.fasterxml.jackson.dataformat.xml.XmlFactory (protected constructor, default XMLInputFactory init path) — reached by any XmlMapper.readValue(untrustedXml, ...) call using the default factory.
  - Verdict: IN — Re-fetched the commit this session: confirms IS_SUPPORTING_EXTERNAL_ENTITIES=Boolean.FALSE setProperty inserted right after XMLInputFactory.newInstance() in the default XmlFactory init path. Insertion-only but a clean, isolable, machine-checkable entity-expansion-off guard on the StAX parser; CWE-611 XXE class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-hmq6-frv3-4727 ; https://nvd.nist.gov/vuln/detail/CVE-2016-3720 ; https://github.com/FasterXML/jackson-dataformat-xml/commit/f0f19a4c924d9db9a1e2830434061c8640092cc0  ·  provenance: re-verified-this-session

- **CVE-2025-54988 (GHSA-p72g-pv48-7w9x)** — CWE-611 · `apache/tika` · fixed 3.2.2 @ `94acef2854eed07f0ded357c13a659409495ca49` · **IN** (signature) · entity-expansion-off
  - Mechanism: XMLReaderUtils.getXMLInputFactory() built the shared StAX XMLInputFactory used across Tika's parsers (including the PDF XFA/AcroForm extractor) without disabling DTD support or external entity support, so a crafted XFA XML fragment embedded in a PDF (or any XML processed via this shared factory) could trigger external entity resolution.
  - Affected -> Fixed: 1.13 - 3.2.1 (tika-core); 2.0.0 - 3.2.1 (tika-pdf-module); 1.13 - 1.28.5 (tika-parsers) -> 3.2.2
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted directly after the existing IS_VALIDATING=false setting)
    tryToSetStaxProperty(factory, XMLInputFactory.IS_NAMESPACE_AWARE, true);
    tryToSetStaxProperty(factory, XMLInputFactory.IS_VALIDATING, false);
    ```
  - Guard added (post-patch):
    ```
    tryToSetStaxProperty(factory, XMLInputFactory.SUPPORT_DTD, false);
    tryToSetStaxProperty(factory, XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
    ```
  - Reachability: org.apache.tika.utils.XMLReaderUtils.getXMLInputFactory() — the shared StAX factory used by Tika's XML/OOXML/PDF-XFA parsing paths; reached whenever Tika parses an untrusted document containing embedded or standalone XML (e.g. a crafted PDF with an XFA form).
  - Verdict: IN — Re-fetched the commit this session: confirms SUPPORT_DTD=false and IS_SUPPORTING_EXTERNAL_ENTITIES=false added to the shared getXMLInputFactory() StAX factory. Clean, isolable, machine-checkable entity-expansion-off guard on a widely-shared parser factory; CWE-611 XXE class-match.
  - Source: https://api.osv.dev/v1/vulns/CVE-2025-54988 ; https://api.osv.dev/v1/vulns/GHSA-f58c-gq56-vjjf ; https://github.com/apache/tika/commit/94acef2854eed07f0ded357c13a659409495ca49  ·  provenance: re-verified-this-session

- **CVE-2022-28140 (GHSA-v4rr-65x6-g69f)** — CWE-611 · `jenkinsci/flaky-test-handler-plugin` · fixed 1.2.2 @ `c4ab38fef3658a02315a00288b934bdd9981b3a4` · **IN** (signature) · entity-expansion-off
  - Mechanism: FlakySuiteResult.parse() built a dom4j `SAXReader` with its unsafe library defaults (no doctype/entity restrictions) to parse JUnit XML test-report files, so a build whose test-result XML contains external entity declarations could trigger XXE when Jenkins ingests the report.
  - Affected -> Fixed: <= 1.2.1 -> 1.2.2
  - Vulnerable shape (removed):
    ```
    SAXReader saxReader = new SAXReader();
    ParserConfigurator.applyConfiguration(saxReader,new SuiteResultParserConfigurationContext(xmlReport));
    ```
  - Guard added (post-patch):
    ```
    SAXReader saxReader = new SAXReader();
    saxReader.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    saxReader.setFeature("http://xml.org/sax/features/external-general-entities", false);
    saxReader.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    ParserConfigurator.applyConfiguration(saxReader,new SuiteResultParserConfigurationContext(xmlReport));
    ```
  - Reachability: com.google.jenkins.flakyTestHandler.junit.FlakySuiteResult.parse(File xmlReport, boolean) — invoked when Jenkins ingests JUnit XML test-report files produced by a build.
  - Verdict: IN — Re-fetched the commit this session: confirms three setFeature calls (disallow-doctype-decl=true, external-general-entities=false, external-parameter-entities=false) inserted immediately after `new SAXReader()` in FlakySuiteResult.parse(). Clean, isolable, machine-checkable entity-expansion-off guard on the JUnit-report parse path; CWE-611 XXE class-match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-v4rr-65x6-g69f ; https://api.osv.dev/v1/vulns/CVE-2022-28140 ; https://github.com/jenkinsci/flaky-test-handler-plugin/commit/c4ab38fef3658a02315a00288b934bdd9981b3a4  ·  provenance: re-verified-this-session

Dropped: CVE-2026-24400 / GHSA-rqfh-9r24-8c9r (assertj) (OUT (refactor-not-fix): OSV/GHSA references commit 85ca7eb6609bb179c043b85ae7d290523b1ba79a as the fix, but the fetched diff only adds a @Deprecated annotation and warning Javadoc to XmlStringPrettyFormatter — the vulnerable DocumentBuilderFactory call site in toXmlDocument(String) is untouched, no entity/DTD-disabling guard added, and the advisory itself states no replacement is provided. No removed/added security-relevant lines to extract; fails 'real guard, not just a label'. (Collector-dropped; concur.)); CVE-2024-2374 (WSO2 API Manager) (OUT (unverifiable): no OSV/GHSA record (OSV returns 'Vulnerability not found'); affected components not in a single clearly-tagged public repo with an identifiable single fix commit, so no fetchable diff can be resolved without fabricating one. (Collector-dropped; concur.)); CVE-2022-0221 / GHSA-g89x-g6h5-52vm (Schneider Electric SCADAPack Workbench) (OUT (unverifiable): proprietary closed-source ICS/SCADA desktop application; no public source repository, so no fix commit is fetchable. (Collector-dropped; concur.)); CVE-2024-12476 / GHSA-hvxh-2jj9-wh53 (Schneider Electric Web Designer) (OUT (unverifiable): proprietary closed-source configuration tool; no public source repository, so no fix commit is fetchable. (Collector-dropped; concur.)); CVE-2025-6438 / GHSA-39gj-7c5p-ccx8 (Schneider Electric EcoStruxure IT DCE) (OUT (unverifiable): proprietary closed-source appliance software; no public source repository, so no fix commit is fetchable. (Collector-dropped; concur.)); CVE-2026-1227 / GHSA-67mv-4hj2-xp3g (Schneider Electric EBO Workstation/WebStation) (OUT (unverifiable): proprietary closed-source building-automation software; no public source repository, so no fix commit is fetchable. (Collector-dropped; concur.)); CVE-2026-42212 / GHSA-92vg-f4fq-fxm9 (SolidCAM GPPL-IDE) (OUT (unverifiable): flagged not re-fetchable in the seed corpus (page returns no CVSS/fix data); closed-source vendor tool, no public repo to resolve a commit. (Collector-dropped; concur.))

## Prototype pollution  (CWE-1321)

Grounds cards: skills/vulns/prototype-pollution (already cited; deepen)
Bucket verdict: **IN — 7 clean anchors (>=6). Dominant guard shape: prototype-key-block, i.e. a denylist that blocks '__proto__'/'constructor'/'prototype' path segments (or resets stepped-onto builtin prototype objects) inside a recursive merge / dotted-path setKey / unflatten / config-iterator traversal (6 of 7: lodash, minimist x2, requirejs, ini, flat). One canonicalization variant (dset: string-coerce the key before an existing strict-=== denylist). All 7 re-fetched live at github.com this session with hunks matching the collector verbatim; no structural duplicates (the two minimist CVEs are sequential, distinct guard shapes).**  ·  7 IN / 0 CONTESTED / 2 dropped  ·  7 promotable signatures
Severity-corpus join: Joins the CWE-1321 prototype-pollution bucket of the severity corpus: these JS-ecosystem PP fixes cluster at CVSS 3.1 AV:N/AC:L/PR:N/UI:N — the merge/parse sinks reachable from untrusted JSON/CLI/INI/config input rate 9.8 (lodash, minimist, ini, requirejs) where pollution enables downstream RCE/DoS, and 7.3–7.5 for integrity-scoped library pollution (dset, flat); use CWE-1321 + "prototype-key traversal sink" as the same-class join key.

- **CVE-2019-10744 (GHSA-jf85-cpcp-j695)** — CWE-1321 · `lodash/lodash` · fixed 4.17.12 @ `793f983629f5ccef831360f4d31881bbf6264f8b` · **IN** (signature) · prototype-key-block
  - Mechanism: _.merge/_.mergeWith/_.defaultsDeep(dest, source) recursively copy properties from source into dest via the internal safeGet(object, key) helper; a source shaped like {"constructor":{"prototype":{...}}} (e.g. from JSON.parse of attacker input) made safeGet return the real Function.prototype object for the 'constructor' key, so the merge recursion wrote through it onto Object.prototype.
  - Affected -> Fixed: < 4.17.12 -> 4.17.12
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted at the top of safeGet(object, key), before the pre-existing `if (key == '__proto__') { return; }` check)
    ```
  - Guard added (post-patch):
    ```
    if (key === 'constructor' && typeof object[key] === 'function') {
        return;
      }
    ```
  - Reachability: safeGet(object, key) in _safeGet.js, called from _baseMergeDeep.js during _.merge/_.mergeWith/_.defaultsDeep(dest, source) recursion; entrypoint is any defaultsDeep()/merge() call with an attacker-influenced source object.
  - Verdict: IN — Commit re-fetched live at github.com; the safeGet 'constructor'-block hunk is a clean, isolable prototype-key guard. The release commit (4.17.12) also bumps version/license and touches _baseClone/_createRound, but those live in separate files/hunks and are not entangled with the safeGet guard, which is machine-checkable on its own. CWE-1321 mechanism (constructor.prototype write via merge/defaultsDeep) matches the primary record.
  - Source: https://api.osv.dev/v1/vulns/CVE-2019-10744 ; https://github.com/lodash/lodash/commit/793f983629f5ccef831360f4d31881bbf6264f8b ; https://nvd.nist.gov/vuln/detail/CVE-2019-10744  ·  provenance: re-verified-this-session

- **CVE-2020-7598 (GHSA-vh95-rmgr-6w4m)** — CWE-1321 · `minimistjs/minimist` · fixed 0.2.1 @ `10bd4cdf49d9686d48214be9d579a9cdfda37c68` · **IN** (signature) · prototype-key-block
  - Mechanism: setKey(obj, keys, value) walks a dotted/array key path built from CLI flags like --a.b.c and writes into it without checking for '__proto__' or for having stepped onto a builtin prototype object, so an argument such as --__proto__.x=123 assigned directly onto Object.prototype (or Array/Number/String.prototype).
  - Affected -> Fixed: < 0.2.1 (0.x line, per OSV GIT/SEMVER fixed events; parallel fix on the 1.x line landed at 1.2.3) -> 0.2.1
  - Vulnerable shape (removed):
    ```
    keys.slice(0,-1).forEach(function (key) {
        if (o[key] === undefined) o[key] = {};
        o = o[key];
    });
    
    var key = keys[keys.length - 1];
    if (o[key] === undefined || typeof o[key] === 'boolean') {
    ```
  - Guard added (post-patch):
    ```
    for (var i = 0; i < keys.length-1; i++) {
        var key = keys[i];
        if (key === '__proto__') return;
        if (o[key] === undefined) o[key] = {};
        if (o[key] === Object.prototype || o[key] === Number.prototype
            || o[key] === String.prototype) o[key] = {};
        if (o[key] === Array.prototype) o[key] = [];
        o = o[key];
    }
    
    var key = keys[keys.length - 1];
    if (key === '__proto__') return;
    if (o === Object.prototype || o === Number.prototype
        || o === String.prototype) o = {};
    if (o === Array.prototype) o = [];
    ```
  - Reachability: setKey(obj, keys, value) in index.js, invoked by the parse loop for every --a.b.c value CLI flag; entrypoint minimist(process.argv) parsing untrusted CLI args.
  - Verdict: IN — Commit re-fetched live; the forEach->for-loop conversion is load-bearing (it enables the early `return` out of setKey), so it is part of the security fix, not an unrelated refactor. The added __proto__ key-block plus Object/Number/String/Array.prototype identity resets are a clean, isolable prototype-pollution guard. CWE-1321 matches NVD/GHSA.
  - Source: https://api.osv.dev/v1/vulns/GHSA-vh95-rmgr-6w4m ; https://github.com/minimistjs/minimist/commit/10bd4cdf49d9686d48214be9d579a9cdfda37c68 ; https://nvd.nist.gov/vuln/detail/CVE-2020-7598  ·  provenance: re-verified-this-session

- **CVE-2021-44906 (GHSA-xvch-5gv4-984h)** — CWE-1321 · `minimistjs/minimist` · fixed 0.2.4 (this branch; parallel fix at 1.2.6 on the 1.x line) @ `34e20b8461118608703d6485326abbb8e35e1703` · **IN** (signature) · prototype-key-block
  - Mechanism: Second, distinct regression after CVE-2020-7598: the added isConstructorOrProto() denylist correctly guarded intermediate key segments in setKey(), but the FINAL path segment was still checked only against the literal '__proto__', not against 'constructor'; a payload like --a.constructor.prototype.b=1 could still mutate a function's .prototype via the last segment.
  - Affected -> Fixed: <= 1.2.5 / <= 0.2.3 (per NVD/OSV; fixed at 1.2.6 and 0.2.4 respectively) -> 0.2.4 (this branch; parallel fix at 1.2.6 on the 1.x line)
  - Vulnerable shape (removed):
    ```
    function isConstructorOrProto(obj, key) {
    	return key === 'constructor' && (typeof obj[key] === 'function' || key === '__proto__');
    }
    ...
    	if (key === '__proto__' || isConstructorOrProto(o, key)) {
    ...
    	key = keys[keys.length - 1];
    	if (key === '__proto__') { return; }
    ```
  - Guard added (post-patch):
    ```
    function isConstructorOrProto(obj, key) {
    	return (key === 'constructor' && typeof obj[key] === 'function') || key === '__proto__';
    }
    ...
    	if (isConstructorOrProto(o, key)) {
    ...
    	key = keys[keys.length - 1];
    	if (isConstructorOrProto(o, key)) { return; }
    ```
  - Reachability: setKey(obj, keys, value), final-segment branch in index.js (lines ~25-46); entrypoint minimist(argv) parsing e.g. --a.constructor.prototype.b value.
  - Verdict: IN — Commit re-fetched live; the hunk fixes the isConstructorOrProto parenthesization (previously true only for key==='constructor') and applies the corrected guard to the FINAL path segment, which previously only checked literal '__proto__' — closing the residual --a.constructor.prototype bypass. Distinct guard shape from CVE-2020-7598 (not a structural duplicate). Advisory (GHSA-xvch-5gv4-984h) and diff agree on which check moved. CWE-1321 on the primary record despite the CVE's disputed history; single whole-fix commit on this branch.
  - Source: https://api.osv.dev/v1/vulns/GHSA-xvch-5gv4-984h ; https://github.com/minimistjs/minimist/commit/34e20b8461118608703d6485326abbb8e35e1703 ; https://nvd.nist.gov/vuln/detail/CVE-2021-44906  ·  provenance: re-verified-this-session

- **CVE-2024-21529 (GHSA-f6v4-cf5j-vf3w)** — CWE-1321 · `lukeed/dset` · fixed 3.1.4 @ `16d6154e085bef01e99f01330e5a421a7f098afa` · **IN** (signature) · canonicalization
  - Mechanism: dset(obj, keys, val) denylists '__proto__'/'constructor'/'prototype' key segments using a strict `===` string comparison, but compared the raw `keys[i++]` element without coercing to string first; a keys argument containing a non-plain-string-typed element equal in value to '__proto__' (per the advisory's PoC) failed the strict `===` check due to type mismatch, bypassing the denylist and reaching Object.prototype.
  - Affected -> Fixed: < 3.1.4 -> 3.1.4
  - Vulnerable shape (removed):
    ```
    k = keys[i++];   (identical line present in both src/index.js and src/merge.js)
    ```
  - Guard added (post-patch):
    ```
    k = ''+keys[i++];   (identical fix applied in both src/index.js and src/merge.js)
    ```
  - Reachability: dset(obj, keys, val) in src/index.js and the merge-variant in src/merge.js, in the while(i<l) loop that walks a dotted/array key path; entrypoint any dset(target, userControlledKeyPath, value) call.
  - Verdict: IN — Commit re-fetched live; the identical `k = ''+keys[i++]` one-line change in src/index.js and src/merge.js canonicalizes the key to a string before the pre-existing __proto__/constructor/prototype `===` denylist, closing the non-string-key type-mismatch bypass. Clean, isolable canonicalization guard (the two hunks are the same logical fix in one commit, not a multi-commit spread). CWE-1321 matches the primary record.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-21529 ; https://github.com/lukeed/dset/commit/16d6154e085bef01e99f01330e5a421a7f098afa ; https://nvd.nist.gov/vuln/detail/CVE-2024-21529  ·  provenance: re-verified-this-session

- **CVE-2024-38999 (GHSA-x3m3-4wpv-5vgc)** — CWE-1321 · `requirejs/requirejs` · fixed 2.3.7 @ `ebd7a2ff71473542fa132d0d15c10fb4ed1539e1` · **IN** (signature) · prototype-key-block
  - Mechanism: eachProp(obj, func), the generic own-property iterator used throughout require.js (including internal config-mixing reachable via s.contexts._.configure()), invoked its callback for every property found via hasProp(obj, prop) without excluding '__proto__'/'constructor', so a maliciously-shaped config object's '__proto__'/'constructor' keys got copied into internal context objects, polluting Object.prototype.
  - Affected -> Fixed: <= 2.3.6 -> 2.3.7
  - Vulnerable shape (removed):
    ```
    if (hasProp(obj, prop)) {
    ```
  - Guard added (post-patch):
    ```
    disallowedProps = ['__proto__', 'constructor'];
    ...
    if (hasProp(obj, prop) && disallowedProps.indexOf(prop) == -1) {
    ```
  - Reachability: eachProp(obj, func) in require.js, used by internal config-mixin/context-configure logic; entrypoint requirejs.config({...}) called with attacker-influenced nested configuration.
  - Verdict: IN — Commit re-fetched live; the added `disallowedProps = ['__proto__', 'constructor']` denylist plus the `&& disallowedProps.indexOf(prop) == -1` gate on eachProp's hasProp check is a clean, isolable prototype-key-block in a single commit (PR #1856). CWE-1321 mechanism (config keys copied into internal context objects) matches the primary record.
  - Source: https://api.osv.dev/v1/vulns/GHSA-x3m3-4wpv-5vgc ; https://github.com/requirejs/requirejs/commit/ebd7a2ff71473542fa132d0d15c10fb4ed1539e1 ; https://github.com/requirejs/requirejs/pull/1856 ; https://nvd.nist.gov/vuln/detail/CVE-2024-38999  ·  provenance: re-verified-this-session

- **CVE-2020-7788 (GHSA-qqgx-2p2h-9c37)** — CWE-1321 · `npm/ini` · fixed 1.3.6 @ `56d2805e07ccd94e2ba0984ac9240ff02d44b6f1` · **IN** (signature) · prototype-key-block
  - Mechanism: decode(str) builds a nested object from an INI-format string; section headers ([section]), '[]'-suffixed array keys, and dotted-key path segments were all used as plain object keys with no '__proto__' check, so an INI document containing a `[__proto__]` section (or a `__proto__[]` / dotted `__proto__` segment) let ini.parse() attach parsed values onto Object.prototype.
  - Affected -> Fixed: < 1.3.6 -> 1.3.6
  - Vulnerable shape (removed):
    ```
    (no lines removed; guards inserted at three sites in decode(): before `p = out[section] = out[section] || {}` for section headers; before the '[]'-suffixed array-key branch; and before the dotted-path `parts.forEach` traversal)
    ```
  - Guard added (post-patch):
    ```
    if (section === '__proto__') {
            // not allowed
            // keep parsing the section, but don't attach it.
            p = {}
            return
          }
    ... 
    if (key === '__proto__') return
    ...
    if (part === '__proto__') return
    ```
  - Reachability: decode(str) in ini.js; entrypoint ini.parse(untrustedIniText), e.g. parsing an uploaded or attacker-supplied .ini config file.
  - Verdict: IN — Commit re-fetched live; the three __proto__ key-blocks in decode() (section header, []-array key, dotted-path segment) are the same guard shape applied at all three write sites within one function in one commit — a coherent, isolable prototype-key-block. CWE-1321 matches the primary record.
  - Source: https://api.osv.dev/v1/vulns/CVE-2020-7788 ; https://github.com/npm/ini/commit/56d2805e07ccd94e2ba0984ac9240ff02d44b6f1 ; https://nvd.nist.gov/vuln/detail/CVE-2020-7788  ·  provenance: re-verified-this-session

- **CVE-2020-36632 (GHSA-2j2x-2gpw-g8fm)** — CWE-1321 · `hughsk/flat` · fixed 5.0.1 @ `20ef0ef55dfa028caddaedbcb33efbdb04d18e13` · **IN** (signature) · prototype-key-block
  - Mechanism: unflatten(target, opts) rebuilds a nested object from dot-delimited flat keys (e.g. "a.b.c": 1); the per-segment while(key2 !== undefined) loop wrote into `recipient[key1]` without checking whether key1 was '__proto__', so an attacker-controlled flat key like "__proto__.polluted" caused unflatten() to write onto Object.prototype.
  - Affected -> Fixed: <= 5.0.0 -> 5.0.1
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted immediately before `const type = Object.prototype.toString.call(recipient[key1])` inside the while (key2 !== undefined) loop in unflatten())
    ```
  - Guard added (post-patch):
    ```
    if (key1 === '__proto__') {
            return
          }
    ```
  - Reachability: unflatten(target, opts) in index.js, the while(key2 !== undefined) per-segment loop; entrypoint flat.unflatten(attackerSuppliedFlatKeyedObject).
  - Verdict: IN — Commit re-fetched live; the single `if (key1 === '__proto__') return` guard inserted in unflatten's per-segment while loop is a clean, isolable prototype-key-block. CWE-1321 mechanism (write onto Object.prototype via a `__proto__.x` flat key) matches the primary record.
  - Source: https://api.osv.dev/v1/vulns/CVE-2020-36632 ; https://github.com/hughsk/flat/commit/20ef0ef55dfa028caddaedbcb33efbdb04d18e13 ; https://nvd.nist.gov/vuln/detail/CVE-2020-36632  ·  provenance: re-verified-this-session

Dropped: CVE-2024-21528 (Collector-dropped (passed through): node-gettext / GHSA-g974-hxvm-x689 OSV record has no GIT-type fixed range and no FIX-type reference — only a WEB permalink to a source line and last_affected:3.0.0 with no recorded fixed version. No single resolvable fix commit; unverifiable per the version-string-only / no-patch rule.); CVE-2018-16487 (Collector-dropped (passed through): lodash merge/mergeWith/defaultsDeep < 4.17.11; the seed corpus's authority-disagreement note records NVD's primary weakness assignment as CWE-400/NVD-CWE-noinfo, not CWE-1321, despite a prototype-pollution mechanism in the description. Dropped to respect the CWE-from-primary-record rule and to avoid a duplicate lodash-product anchor alongside CVE-2019-10744 (CWE-1321 at its primary record).)

## JWT / token validation flaws  (CWE-347)

Grounds cards: skills/vulns/jwt-authentication-bypass, skills/patterns/jwt-claim-validation
Bucket verdict: **IN — 6 clean, re-fetched anchors (all fix commits re-fetched at github primary sources this session with hunks matching verbatim; all focused security fixes), every one class-matched to CWE-347 by mechanism. Dominant guard shapes split two ways: (a) reject asymmetric/PEM/SSH keys as HMAC secrets — denylist->safe-API via is_pem_format()/is_ssh_key() (python-jose, pyjwt) and PEM-header regex canonicalization of the public-key matcher (fast-jwt) — to kill algorithm confusion; (b) fail-closed algorithm/signature binding — require an explicit alg and bind it to the header (hono param-binding), refuse unsigned / silent-alg=none tokens (node-jsonwebtoken), and require a SignedJWT when signature configs exist (pac4j). Guard-type corrections applied to 3 anchors (bound/canonicalization -> denylist-to-safe-api / other) for precision; no OUT reclassifications, both collector-dropped ids passed through.**  ·  6 IN / 0 CONTESTED / 2 dropped  ·  6 promotable signatures
Severity-corpus join: Joins the severity-corpus CWE-347 bucket: these are JWT signature-verification / authentication-bypass primitives, nominally CVSS 7.5-9.8 (AV:N / PR:N / UI:N, integrity+confidentiality impact), but real NVD/GHSA vectors cluster mid-to-high because exploitability is conditional — algorithm-confusion (python-jose, pyjwt, fast-jwt, hono) requires the caller not to pin an explicit algorithm allow-list, and alg=none / unsigned-JWT acceptance (node-jsonwebtoken, pac4j) requires the app to accept unsigned tokens (e.g. CVE-2022-29217 scored 7.4 via AV:N/AC:H; CVE-2024-33663 scored 8.1).

- **CVE-2024-33663 (GHSA-6c5p-j8vq-pqhj)** — CWE-327 (GHSA/CNA primary tag); mechanism is algorithm-confusion signature-verification bypass = CWE-347 class member by mechanism · `mpdavis/python-jose` · fixed 3.4.0 @ `12f30c8c87b343ad4f9e27e8b5b9e0ef7d665cb3` · **IN** (signature) · denylist-to-safe-api
  - Mechanism: python-jose's HMACKey.__init__ (both cryptography_backend.py and native.py) rejected asymmetric keys as HMAC secrets using a naive substring denylist (checking for '-----BEGIN PUBLIC KEY-----', 'ssh-rsa', etc. anywhere in the key bytes). The denylist did not cover all PEM/OpenSSH key-format variants (e.g. OpenSSH ECDSA-format public keys), so a key of one format could be reinterpreted and accepted as an HMAC secret, letting an attacker sign an HS256 token using the server's known public key and have jwt.decode() verify it.
  - Affected -> Fixed: 0 - 3.3.0 (introduced at project start, last affected 3.3.0) -> 3.4.0
  - Vulnerable shape (removed):
    ```
    invalid_strings = [
        b"-----BEGIN PUBLIC KEY-----",
        b"-----BEGIN RSA PUBLIC KEY-----",
        b"-----BEGIN CERTIFICATE-----",
        b"ssh-rsa",
    ]
    
    if any(string_value in key for string_value in invalid_strings):
    ```
  - Guard added (post-patch):
    ```
    if is_pem_format(key) or is_ssh_key(key):
        raise JWKError(
            "The specified key is an asymmetric key or x509 certificate and"
            " should not be used as an HMAC secret."
        )
    ```
  - Reachability: HMACKey.__init__ in jose/backends/cryptography_backend.py and jose/backends/native.py, reached via jwt.decode()/jws.verify() whenever the caller does not pass an explicit algorithms allow-list and an attacker controls the JWT header alg=HS256.
  - Verdict: IN — Re-fetched commit 12f30c8 at github (primary source); focused fix (both backends + jose/utils.py helpers + one EC test), hunk matches the diff verbatim. Substring denylist -> is_pem_format()/is_ssh_key() is a clean, isolable denylist->safe-API swap. Mechanism is algorithm-confusion signature-verification bypass (sign HS256 with the server's own public key) = CWE-347 class by mechanism despite the CWE-327 primary tag; class-match is on mechanism. Corrected guard_type canonicalization->denylist-to-safe-api (substring denylist replaced by format-detection safe API).
  - Source: https://api.osv.dev/v1/vulns/GHSA-6c5p-j8vq-pqhj ; https://github.com/mpdavis/python-jose/security/advisories/GHSA-6c5p-j8vq-pqhj ; https://nvd.nist.gov/vuln/detail/CVE-2024-33663 ; https://github.com/mpdavis/python-jose/commit/12f30c8c87b343ad4f9e27e8b5b9e0ef7d665cb3  ·  provenance: re-verified-this-session

- **CVE-2023-48223 (GHSA-c2ff-88x2-x9pg)** — CWE-20 (CNA) / NVD-CWE-noinfo (NIST); mechanism is algorithm-confusion signature bypass = CWE-347 class member · `nearform/fast-jwt` · fixed 3.3.2 @ `15a6e92c9adb39acde41a9b11cec0cbde8ad763b` · **IN** (signature) · canonicalization
  - Mechanism: fast-jwt's publicKeyPemMatcher was a plain string '-----BEGIN PUBLIC KEY-----' checked with String.includes(). It did not match the '-----BEGIN RSA PUBLIC KEY-----' PKCS#1 header variant, so an RSA public key with that header fell through key-type detection and was misclassified as a plain HMAC secret, letting an attacker sign an HS256 token using the server's known RSA public key.
  - Affected -> Fixed: 0 - 3.3.1 -> 3.3.2
  - Vulnerable shape (removed):
    ```
    const publicKeyPemMatcher = '-----BEGIN PUBLIC KEY-----'
    ...
    if (key.includes(publicKeyPemMatcher) || key.includes(publicKeyX509CertMatcher)) {
    ...
    } else if (!key.includes(publicKeyPemMatcher) && !key.includes(publicKeyX509CertMatcher)) {
    ```
  - Guard added (post-patch):
    ```
    const publicKeyPemMatcher = /^-----BEGIN( RSA)? PUBLIC KEY-----/
    ...
    if (key.match(publicKeyPemMatcher) || key.includes(publicKeyX509CertMatcher)) {
    ...
    } else if (!key.match(publicKeyPemMatcher) && !key.includes(publicKeyX509CertMatcher)) {
    ```
  - Reachability: performDetectPrivateKeyAlgorithm / performDetectPublicKeyAlgorithms in fast-jwt/src/crypto.js, reached via createVerifier({key}) / verifySync(token) when the caller does not pin an explicit algorithm and the JWT header sets alg=HS256.
  - Verdict: IN — Re-fetched commit 15a6e92 (primary source); only src/crypto.js is substantive (test file change is whitespace only). String matcher '-----BEGIN PUBLIC KEY-----' + .includes() -> regex /^-----BEGIN( RSA)? PUBLIC KEY-----/ + .match() is a clean canonicalization fix that makes the matcher recognize the PKCS#1 RSA header variant, so the pubkey is no longer misclassified as an HMAC secret. Mechanism = algorithm confusion = CWE-347 class despite the CWE-20/noinfo primary tags. The '...' elisions join the const declaration and its two call sites of the same one-line-shaped fix; verified verbatim against the three per-line diff hunks.
  - Source: https://api.osv.dev/v1/vulns/GHSA-c2ff-88x2-x9pg ; https://github.com/nearform/fast-jwt/security/advisories/GHSA-c2ff-88x2-x9pg ; https://nvd.nist.gov/vuln/detail/CVE-2023-48223 ; https://github.com/nearform/fast-jwt/commit/15a6e92c9adb39acde41a9b11cec0cbde8ad763b  ·  provenance: re-verified-this-session

- **CVE-2022-23540 (GHSA-qwph-4952-7xr6)** — CWE-347 / CWE-287 · `auth0/node-jsonwebtoken` · fixed 9.0.0 @ `834503079514b72264fd13023a3b8d648afd6a16` · **IN** (signature) · other
  - Mechanism: jwt.verify() silently set options.algorithms = ['none'] whenever the caller passed no algorithms option and the token had no signature (empty third segment), so an attacker could send an unsigned token with alg stripped/absent and have it accepted as valid with no signature check at all.
  - Affected -> Fixed: <=8.5.1 -> 9.0.0
  - Vulnerable shape (removed):
    ```
    if (!hasSignature && !options.algorithms) {
      options.algorithms = ['none'];
    }
    ```
  - Guard added (post-patch):
    ```
    if (!hasSignature && !options.algorithms) {
      return done(new JsonWebTokenError('please specify "none" in "algorithms" to verify unsigned tokens'));
    }
    ```
  - Reachability: module.exports (verify function) in verify.js, the '!hasSignature && !options.algorithms' branch — reached via jwt.verify(token, secretOrPublicKey, options) whenever options.algorithms is omitted.
  - Verdict: IN — Re-fetched commit 8345030 (primary source). The production guard in verify.js is a single clean removed line (options.algorithms = ['none']) -> return done(error), cleanly isolable in one file. The other 14 changed files are test-suite updates adapting to the new fail-closed behavior, not an unrelated refactor, so isolability holds. Mechanism = accepting unsigned tokens with no signature check via a silent alg=none default = CWE-347/CWE-287. Reclassified guard_type bound->other: this is a fail-closed default change, not a numeric/range bound.
  - Source: https://api.osv.dev/v1/vulns/CVE-2022-23540 ; https://github.com/auth0/node-jsonwebtoken/security/advisories/GHSA-qwph-4952-7xr6 ; https://nvd.nist.gov/vuln/detail/CVE-2022-23540 ; https://github.com/auth0/node-jsonwebtoken/commit/834503079514b72264fd13023a3b8d648afd6a16  ·  provenance: re-verified-this-session

- **CVE-2026-22817 (GHSA-f67f-6cw9-8mq4)** — CWE-347 · `honojs/hono` · fixed 4.11.4 @ `cc0aa7ae327ed84cc391d29086dec2a3e44e7a1f` · **IN** (signature) · param-binding
  - Mechanism: Hono's JWT verify() made the alg option optional (default 'HS256') and, when using JWK/JWKS-based verification, could let the untrusted JWT header's own alg value select the verification algorithm whenever the resolved JWK omitted an explicit alg field — classic algorithm-confusion token forgery.
  - Affected -> Fixed: < 4.11.4 -> 4.11.4
  - Vulnerable shape (removed):
    ```
    alg?: SignatureAlgorithm
    ...
    export const verify = async (
      token: string,
      publicKey: SignatureKey,
      algOrOptions?: SignatureAlgorithm | VerifyOptionsWithAlg
    ): Promise<JWTPayload> => {
      const {
        alg = 'HS256',
        ...
      } = typeof algOrOptions === 'string' ? { alg: algOrOptions } : algOrOptions || {}
    ```
  - Guard added (post-patch):
    ```
    alg: SignatureAlgorithm
    ...
    export const verify = async (
      token: string,
      publicKey: SignatureKey,
      algOrOptions: SignatureAlgorithm | VerifyOptionsWithAlg
    ): Promise<JWTPayload> => {
      if (!algOrOptions) {
        throw new JwtAlgorithmRequired()
      }
      const {
        alg,
        ...
      } = typeof algOrOptions === 'string' ? { alg: algOrOptions } : algOrOptions
      if (!alg) {
        throw new JwtAlgorithmRequired()
      }
      ...
      if (header.alg !== alg) {
        throw new JwtAlgorithmMismatch(alg, header.alg)
      }
    ```
  - Reachability: verify() in src/utils/jwt/jwt.ts and the jwt() middleware factory in src/middleware/jwt/jwt.ts — entrypoint: the JWT auth middleware validating the Authorization header/cookie on each request.
  - Verdict: IN — Re-fetched commit cc0aa7a (primary source); focused fix touching only 5 JWT files (jwt.ts, middleware jwt.ts, types.ts + 2 tests), no unrelated refactor. alg is made mandatory (alg? -> alg on VerifyOptionsWithAlg and algOrOptions? -> algOrOptions), with JwtAlgorithmRequired throws and, crucially, a header.alg !== alg binding check throwing JwtAlgorithmMismatch — a clean param-binding fix that stops the untrusted header alg from selecting the verification algorithm. Mechanism = algorithm confusion = CWE-347. The '...' elisions in the hunk join coherent parts of the same single fix and were verified verbatim against the diff.
  - Source: https://api.osv.dev/v1/vulns/CVE-2026-22817 ; https://github.com/honojs/hono/security/advisories/GHSA-f67f-6cw9-8mq4 ; https://nvd.nist.gov/vuln/detail/CVE-2026-22817 ; https://github.com/honojs/hono/commit/cc0aa7ae327ed84cc391d29086dec2a3e44e7a1f  ·  provenance: re-verified-this-session

- **CVE-2026-29000 (GHSA-pm7g-w2cf-q238)** — CWE-347 · `pac4j/pac4j` · fixed 4.5.9 @ `d9c57aa68b8da31a1a90bf08b856ac805c9b23e0` · **IN** (signature) · other
  - Mechanism: JwtAuthenticator.validate() only entered its signature-verification branch 'if (signedJWT != null)'. When the incoming token was a JWE (encrypted JWT) wrapping a PlainJWT (unsigned/unencoded JWT payload) rather than a SignedJWT, signedJWT was null and the whole signature-check branch was skipped entirely — so a JWE built from any RSA public key the attacker holds, wrapping an unsigned PlainJWT with arbitrary subject/role claims, was accepted with no signature verification at all.
  - Affected -> Fixed: 4.0 - 4.5.8 (parallel fixes on 5.x at 5.7.9, 6.x at 6.3.3) -> 4.5.9
  - Vulnerable shape (removed):
    ```
    // signed?
    if (signedJWT != null) {
        logger.debug("JWT is signed");
    
        boolean verified = false;
    ```
  - Guard added (post-patch):
    ```
    // signed?
    // If signature configurations are defined, a SignedJWT is required and signature verification must be performed.
    if (!signatureConfigurations.isEmpty()) {
        if (signedJWT == null) {
            throw new CredentialsException("A non-signed JWT cannot be accepted as signature configurations have been defined");
        }
    
        logger.debug("JWT is signed");
    
        boolean verified = false;
    ```
  - Reachability: JwtAuthenticator.validate(TokenCredentials, WebContext) in pac4j-jwt/src/main/java/org/pac4j/jwt/credentials/authenticator/JwtAuthenticator.java — entrypoint: any pac4j authentication flow that authenticates bearer/session JWTs via JwtAuthenticator.
  - Verdict: IN — Re-fetched commit d9c57aa (primary source); focused fix (JwtAuthenticator.java + one test + release-notes). `if (signedJWT != null)` -> `if (!signatureConfigurations.isEmpty()) { if (signedJWT == null) throw CredentialsException }` is a clean, isolable fail-closed guard: when signature configs are defined a SignedJWT is required, closing the JWE-wrapped-PlainJWT path that skipped verification entirely. Mechanism = signature verification wholly bypassed = CWE-347. Parallel 5.x/6.x backports exist but the 4.x commit is a single whole-fix SHA, so not CONTESTED. Reclassified bound->other (fail-closed require-signature guard, not a numeric bound).
  - Source: https://api.osv.dev/v1/vulns/CVE-2026-29000 ; https://nvd.nist.gov/vuln/detail/CVE-2026-29000 ; https://www.pac4j.org/blog/security-advisory-pac4j-jwt-jwtauthenticator.html ; https://github.com/pac4j/pac4j/commit/d9c57aa68b8da31a1a90bf08b856ac805c9b23e0  ·  provenance: re-verified-this-session

- **CVE-2022-29217 (GHSA-ffqj-6fqr-9h24)** — CWE-327 (primary tag); mechanism is algorithm-confusion signature-verification bypass = CWE-347 class member · `jpadilla/pyjwt` · fixed 2.4.0 @ `9c528670c455b8d948aff95ed50e22940d1ad3fc` · **IN** (signature) · denylist-to-safe-api
  - Mechanism: HMACAlgorithm.prepare_key() rejected asymmetric keys as HMAC secrets using a naive substring denylist (checking key bytes for '-----BEGIN PUBLIC KEY-----', 'ssh-rsa', etc.), which missed OpenSSH-format and other PEM header variants. If the caller decoded with the full default algorithm set (jwt.algorithms.get_default_algorithms()) rather than an explicit allow-list, an attacker could sign an HS256 token using the server's known RSA public key as the HMAC secret and have it verified successfully.
  - Affected -> Fixed: 1.5.0 - 2.3.0 -> 2.4.0
  - Vulnerable shape (removed):
    ```
    invalid_strings = [
        b"-----BEGIN PUBLIC KEY-----",
        b"-----BEGIN CERTIFICATE-----",
        b"-----BEGIN RSA PUBLIC KEY-----",
        b"ssh-rsa",
    ]
    
    if any(string_value in key for string_value in invalid_strings):
    ```
  - Guard added (post-patch):
    ```
    if is_pem_format(key) or is_ssh_key(key):
        raise InvalidKeyError(
            "The specified key is an asymmetric key or x509 certificate and"
            " should not be used as an HMAC secret."
        )
    ```
  - Reachability: HMACAlgorithm.prepare_key in jwt/algorithms.py, reached via jwt.decode()/PyJWS.decode() whenever algorithms=jwt.algorithms.get_default_algorithms() (or an equivalently permissive mixed list) is passed and the attacker controls the JWT header alg=HS256.
  - Verdict: IN — Re-fetched commit 9c52867 (primary source); jwt/algorithms.py (guard) + jwt/utils.py (new is_pem_format/is_ssh_key regex helpers) + advisory tests. Substring denylist -> is_pem_format()/is_ssh_key() safe-API is a clean, isolable denylist->safe-API swap. Mechanism = algorithm confusion (sign HS256 with the server's RSA public key when the default algorithm set is used) = CWE-347 class despite the CWE-327 primary tag. Distinct product from python-jose CVE-2024-33663, so retained for cross-product diversity rather than merged. Corrected guard_type canonicalization->denylist-to-safe-api.
  - Source: https://api.osv.dev/v1/vulns/CVE-2022-29217 ; https://github.com/jpadilla/pyjwt/security/advisories/GHSA-ffqj-6fqr-9h24 ; https://nvd.nist.gov/vuln/detail/CVE-2022-29217 ; https://github.com/jpadilla/pyjwt/commit/9c528670c455b8d948aff95ed50e22940d1ad3fc  ·  provenance: re-verified-this-session

Dropped: CVE-2026-34950 (GHSA-mvf2-f6gm-w987, nearform/fast-jwt) (Structural duplicate of IN anchor CVE-2023-48223 — same product (nearform/fast-jwt) and same guard shape (PEM-header regex canonicalization of the public-key matcher). It is the whitespace-defeats-anchor incomplete-fix follow-up to CVE-2023-48223 (its own fix landed in commit 597c4b6e6af3bd823f624debdaa7f57fa92b1e2d / PR #598, 'complete patch for GHSA-mvf2-f6gm-w987 and #586'). Real and re-fetchable, but dropped under the merge-exact-structural-duplicates rule to preserve cross-product diversity; pull it back as a near-duplicate anchor only if a second fast-jwt vector is explicitly wanted.); CVE-2026-48526 (GHSA-xgmm-8j9v-c9wx, jpadilla/PyJWT) (Genuine but entangled: the only fix landed in bundle commit 95791b1759b8aa4f2203575d344d5c78564cdc81 ('Bundle security fixes and hardening into 2.13.0'), which mixes five independent GHSA fixes (GHSA-xgmm-8j9v-c9wx JWK-as-HMAC-secret, GHSA-jq35-7prp-9v3f alg-binding, GHSA-993g-76c3-p5m4 URI-scheme, GHSA-fhv5-28vv-h8m8 cache-eviction, GHSA-w7vc-732c-9m39 b64 DoS) plus unrelated hardening/typing churn in jwt/algorithms.py, with no single-purpose SHA isolating just this fix. This is CONTESTED-flavored (entangled) rather than a hard OUT, but the collector extracted no isolable verbatim hunk and its guard class (asymmetric-key/JWK-as-HMAC-secret rejection) is already cleanly represented by IN anchors CVE-2024-33663 and CVE-2022-29217 — so left in dropped as pass-through rather than promoted to a messy CONTESTED near-duplicate.)

## CSRF  (CWE-352)

Grounds cards: skills/patterns/legacy-route-differential (canonicalization-before-security-filter precedent references a CSRF filter as one of the shared consumers), skills/vulns/business-logic-abuse
Bucket verdict: **IN -- 6 clean anchors across 6 distinct products/ecosystems (Go/gin new-api, PHP Ampache, Node.js Ghost, Go goshs, C++ Sunshine, TypeScript redwoodjs/sdk), clearing the >=6 threshold.**  ·  6 IN / 0 CONTESTED / 14 dropped  ·  6 promotable signatures
Dominant guard shape for the class is a same-origin/authenticity check inserted right before the state-changing sink -- either an **origin/Host-header match** (Ghost session-verify, redwoodjs/sdk server actions), a **synchronizer CSRF token check** (Ampache `verifyForm()`, goshs `checkCSRF()`), or a **verb + parameter-binding fix** that moves the state change off a bare `GET`/query-string request onto a body-bound `POST` (new-api email/WeChat bind) -- with a **non-simple-request content-type gate** (Sunshine) as the minority variant that defeats plain HTML-form/`<img>`/no-cors submission without a token store at all.
Severity-corpus join: Joins the same-class CSRF (CWE-352) severity-corpus bucket (skills/oracles/references/severity-precedent-corpus.md, "CSRF (CWE-352)" section) — that bucket's IN vectors are dominated by ICS/OT firmware and CMS admin-panel CSRF (AV:N/AC:L-H/PR:N/UI:R, C/I/A impact varying with the protected action, up to chained RCE in the Apache OFBiz CVE-2024-48962 case); this bucket supplies the *code-level* guard shapes (origin-check, token-check, verb/binding fix, content-type gate) that back those CVSS vectors, since none of the corpus's OT/ICS-firmware CVEs there have a fetchable public fix commit.

- **CVE-2026-44342 (GHSA-26v7-h57m-gh9m)** — CWE-352 · `QuantumNous/new-api` · fixed 0.12.0-alpha.1 @ `e099117c61391abdf888fb75e382a582e550bd0e` · **IN** (signature) · verb+binding fix
  - Mechanism: The email- and WeChat-account-binding endpoints were registered as `GET` routes and read the binding parameters (`email`, `code`) from the query string. A `GET` request carries the victim's session cookie automatically and is trivially forced via a bare `<img src=...>`/link, so an attacker could bind an attacker-controlled email/WeChat account to a logged-in victim's account purely by getting them to load a URL, enabling downstream account-recovery takeover. Default `SameSite=Strict` cookies partially mitigate this in modern browsers (per the advisory), but the endpoint itself had no CSRF protection.
  - Affected -> Fixed: < 0.12.0-alpha.1 -> 0.12.0-alpha.1
  - Vulnerable shape (removed):
    ```
    apiRouter.GET("/oauth/email/bind", middleware.CriticalRateLimit(), controller.EmailBind)
    apiRouter.GET("/oauth/wechat/bind", middleware.CriticalRateLimit(), controller.WeChatBind)
    ```
    ```
    func EmailBind(c *gin.Context) {
    	email := c.Query("email")
    	code := c.Query("code")
    ```
  - Guard added (post-patch):
    ```
    apiRouter.POST("/oauth/email/bind", middleware.CriticalRateLimit(), controller.EmailBind)
    apiRouter.POST("/oauth/wechat/bind", middleware.CriticalRateLimit(), controller.WeChatBind)
    ```
    ```
    type emailBindRequest struct {
    	Email string `json:"email"`
    	Code  string `json:"code"`
    }

    func EmailBind(c *gin.Context) {
    	var req emailBindRequest
    	if err := common.DecodeJson(c.Request.Body, &req); err != nil {
    		common.ApiError(c, errors.New("invalid request body"))
    		return
    	}
    	email := req.Email
    	code := req.Code
    ```
  - Reachability: router/api-router.go SetApiRouter (route table) + controller/user.go EmailBind / controller/wechat.go WeChatBind, reached via any authenticated user's browser being induced to submit to `/api/oauth/email/bind` or `/api/oauth/wechat/bind`.
  - Verdict: IN — Re-fetched commit this session; delta matches verbatim. Clean, isolable verb+binding guard: the route moves from `GET`+query-string to `POST`+JSON-body, which defeats the cross-origin-`GET`/simple-request forgery vector (a JSON body cannot be attached by a bare link/image/form without a CORS preflight the attacker's origin won't pass). CSRF-via-GET-state-change matches CWE-352.
  - Source: https://github.com/QuantumNous/new-api/security/advisories/GHSA-26v7-h57m-gh9m ; https://nvd.nist.gov/vuln/detail/CVE-2026-44342 ; https://github.com/QuantumNous/new-api/commit/e099117c61391abdf888fb75e382a582e550bd0e.diff  ·  provenance: re-verified-this-session

- **CVE-2024-51485 (GHSA-xvfj-w962-hqcx)** — CWE-352 · `ampache/ampache` · fixed 7.0.1 @ `4974e336c0b1d6a7874bf723fb5bb1ba6625fc4d` · **IN** (signature) · csrf-token check
  - Mechanism: The admin-only plugin/catalog-type/localplay-module install and uninstall actions performed the install/uninstall immediately on request with no CSRF-token verification, so a logged-in admin could be lured into a page that silently enables/disables plugins or installs modules on their behalf.
  - Affected -> Fixed: 7.0.0 -> 7.0.1
  - Vulnerable shape (removed):
    ```
    public function run(ServerRequestInterface $request, GuiGatekeeperInterface $gatekeeper): ?ResponseInterface
    {
        if ($gatekeeper->mayAccess(AccessTypeEnum::INTERFACE, AccessLevelEnum::ADMIN) === false) {
            throw new AccessDeniedException();
        }
    ```
  - Guard added (post-patch):
    ```
    public function run(ServerRequestInterface $request, GuiGatekeeperInterface $gatekeeper): ?ResponseInterface
    {
        if (
            $gatekeeper->mayAccess(AccessTypeEnum::INTERFACE, AccessLevelEnum::ADMIN) === false ||
            !$this->requestParser->verifyForm('install_plugin')
        ) {
            throw new AccessDeniedException();
        }
    ```
  - Reachability: src/Module/Application/Admin/Modules/InstallPluginAction.php run() (and the matching UninstallPluginAction / Install-Uninstall CatalogType / Localplay actions), reached via the admin `?action=install_plugin` (etc.) GUI route; new `ConfirmInstall*` actions were added so the admin UI now renders a token-bearing confirmation page before the state-changing action fires.
  - Verdict: IN — Re-fetched commit this session; the added `!$this->requestParser->verifyForm('install_plugin')` check matches verbatim and the same pattern is repeated identically across the six install/uninstall action classes (plugin, catalog-type, localplay) — a single guard shape applied consistently at each sink, not unrelated churn. Missing per-request CSRF-token validation on an admin state-changing action matches CWE-352.
  - Source: https://github.com/ampache/ampache/security/advisories/GHSA-xvfj-w962-hqcx ; https://nvd.nist.gov/vuln/detail/CVE-2024-51485 ; https://github.com/ampache/ampache/commit/4974e336c0b1d6a7874bf723fb5bb1ba6625fc4d.diff  ·  provenance: re-verified-this-session

- **CVE (GHSA-9m84-wc28-w895)** — CWE-352 · `TryGhost/Ghost` · fixed 6.19.3 @ `ec065a774fa125953d2aa644a59cd8990329e0a0` · **IN** (signature) · origin-check
  - Mechanism: The `/session/verify` one-time-code (OTC) verification endpoint checked only that the submitted code matched the user, not that the request verifying it originated from the same browser session/origin that requested the code — letting an attacker who obtains or brute-forces an OTC (or races a phished one) verify/consume it from an attacker-controlled cross-origin request, decoupling the login session that gets upgraded from the session the legitimate user is sitting in.
  - Affected -> Fixed: 5.101.6 - 6.19.2 -> 6.19.3
  - Vulnerable shape (removed):
    ```
    async function verifyAuthCodeForUser(req, res) {
        const session = await getSession(req, res);
        const secret = getSettingsCache('admin_session_secret');
        return otp.verify(session.user_id, req.body.token, secret);
    }
    ```
  - Guard added (post-patch):
    ```
    async function verifyAuthCodeForUser(req, res) {
        const session = await getSession(req, res);
        cookieCsrfProtection(req, session);

        const secret = getSettingsCache('admin_session_secret');
        const token = req.body && req.body.token;

        return verifyAuthCode(session, token, secret);
    }
    ```
    ```
    function cookieCsrfProtection(req, session) {
        const origin = getOriginOfRequest(req);
        const adminUrl = urlUtils.getAdminUrl() || urlUtils.getSiteUrl();
        const adminOrigin = new URL(adminUrl).origin;

        if (origin !== adminOrigin) {
            throw new BadRequestError({
                message: `Request made from incorrect origin...`
            });
        }
    ```
  - Reachability: ghost/core/core/server/services/auth/session/session-service.js verifyAuthCodeForUser(), reached via POST /ghost/api/admin/session/verify/ during the OTC login step.
  - Verdict: IN — Re-fetched commit this session; the `cookieCsrfProtection()` origin-match guard, invoked before `otp.verify`/`verifyAuthCode`, matches verbatim. The same commit also adds session-bound/time-limited auth-code challenges (`AUTH_CODE_VALIDITY_MS`, `hasValidAuthCodeChallenge`) in the same file for the same mechanism (OTC replay/cross-session binding) — a reinforcing hardening of the identical CSRF-adjacent flaw, not unrelated churn, so treated as one cohesive fix. Cross-origin forgery of a state-changing auth step matches CWE-352.
  - Source: https://github.com/TryGhost/Ghost/security/advisories/GHSA-9m84-wc28-w895 ; https://github.com/TryGhost/Ghost/commit/ec065a774fa125953d2aa644a59cd8990329e0a0.diff  ·  provenance: re-verified-this-session

- **CVE-2026-42091 (GHSA-rhf7-wvw3-vjvm)** — CWE-352 · `patrickhener/goshs` · fixed v2.0.2 @ `0e715b94e10c3d1aa552276000f15f104dee2f32` · **IN** (signature) · csrf-token check
  - Mechanism: A prior fix (GHSA-jrq5-hg6x-j6g3) had added a `checkCSRF()` token check to goshs's `POST` file-upload handler, but the `PUT` upload handler — which performs the same arbitrary-file-write action — was left unguarded. Combined with a wildcard `Access-Control-Allow-Origin: *` on the OPTIONS preflight response, any website a victim visited could issue a cross-origin `PUT` to silently write/overwrite files in the goshs webroot, bypassing the CSRF protection that already existed on the sibling `POST` route.
  - Affected -> Fixed: v2 < 2.0.2 -> 2.0.2 (v1 branch last-affected at 1.1.4, no v1 backport identified)
  - Vulnerable shape (no lines removed; guard inserted before the PUT upload sink, mirroring the existing POST-path `checkCSRF()` guard):
    ```
    func (fs *FileServer) put(w http.ResponseWriter, req *http.Request) {
    	if fs.ReadOnly {
    		fs.handleError(w, req, fmt.Errorf("%s", "Upload not allowed due to 'read only' option"), http.StatusForbidden)
    		return
    ```
  - Guard added (post-patch):
    ```
    func (fs *FileServer) put(w http.ResponseWriter, req *http.Request) {
    	if !fs.checkCSRF(w, req) {
    		return
    	}
    	if fs.ReadOnly {
    		fs.handleError(w, req, fmt.Errorf("%s", "Upload not allowed due to 'read only' option"), http.StatusForbidden)
    		return
    ```
  - Reachability: httpserver/updown.go FileServer.put(), reached via any cross-origin `PUT` request to a goshs upload path from a victim's browser (no auth on goshs by default).
  - Verdict: IN — Re-fetched commit this session; the two-line `checkCSRF()` guard call matches verbatim, single-purpose SHA. Textbook incomplete-parity fix: same guard function already existed and was proven correct on the `POST` sink, this commit is purely "apply the same existing check to the sibling `PUT` sink." Missing-CSRF-check-on-one-of-two-equivalent-verbs matches CWE-352.
  - Source: https://github.com/patrickhener/goshs/security/advisories/GHSA-rhf7-wvw3-vjvm ; https://github.com/patrickhener/goshs/commit/0e715b94e10c3d1aa552276000f15f104dee2f32.diff  ·  provenance: re-verified-this-session

- **CVE-2025-53095 (GHSA-39hj-fxvw-758m)** — CWE-352 · `LizardByte/Sunshine` · fixed 2025.628.4510 @ `738ac93a0ec1cd10412d1f339968775f53bfefe0` · **IN** (signature) · content-type gate
  - Mechanism: Sunshine's web UI used HTTP Basic Authentication, whose credential (the `Authorization` header) the browser attaches automatically to same-origin *and* cross-origin requests once a user has authenticated once in that browser session — there was no CSRF protection at all on any state-changing endpoint. Because the app performs OS command execution by design (the "Command Preparations" feature lets an admin define a command line to run when an app launches), an attacker's page could submit a form that silently reaches an endpoint and injects an arbitrary command, executed with Administrator privileges the next time the victim launches an app in Sunshine.
  - Affected -> Fixed: <= 2025.122.141614 -> 2025.628.4510
  - Vulnerable shape (no lines removed; guard inserted at the top of each state-changing handler, e.g. saveApp before the auth check):
    ```
    void saveApp(resp_https_t response, req_https_t request) {
      if (!authenticate(response, request)) {
        return;
      }
    ```
  - Guard added (post-patch):
    ```
    bool check_content_type(resp_https_t response, req_https_t request, const std::string_view &contentType) {
      auto requestContentType = request->header.find("content-type");
      if (requestContentType == request->header.end()) {
        bad_request(response, request, "Content type not provided");
        return false;
      }
      std::string actualContentType = requestContentType->second;
      size_t semicolonPos = actualContentType.find(';');
      if (semicolonPos != std::string::npos) {
        actualContentType = actualContentType.substr(0, semicolonPos);
      }
      boost::algorithm::trim(actualContentType);
      boost::algorithm::to_lower(actualContentType);
      std::string expectedContentType(contentType);
      boost::algorithm::to_lower(expectedContentType);
      if (actualContentType != expectedContentType) {
        bad_request(response, request, "Content type mismatch");
        return false;
      }
      return true;
    }
    ...
    void saveApp(resp_https_t response, req_https_t request) {
      if (!check_content_type(response, request, "application/json")) {
        return;
      }
      if (!authenticate(response, request)) {
        return;
      }
    ```
  - Reachability: src/confighttp.cpp check_content_type() + call sites in saveApp/closeApp/deleteApp/unpair and ~8 other state-changing endpoint handlers, reached via any POST/DELETE request to the local Sunshine config API while an admin is authenticated in that browser.
  - Verdict: IN — Re-fetched commit this session; the `check_content_type()` function and its call-site insertion into `saveApp()` (and read consistently across the other ~10 endpoints plus matching frontend `fetch()` header additions) match verbatim. Same guard function applied identically at every state-changing sink — large diff (many files) but one clean, isolable guard shape, not entangled unrelated churn. Requiring `Content-Type: application/json` defeats plain HTML-form/basic cross-origin submission (which can only send CORS-simple content-types) without needing a token store — a distinct, valid CSRF-mitigation shape. Matches CWE-352.
  - Source: https://github.com/LizardByte/Sunshine/security/advisories/GHSA-39hj-fxvw-758m ; https://nvd.nist.gov/vuln/detail/CVE-2025-53095 ; https://github.com/LizardByte/Sunshine/commit/738ac93a0ec1cd10412d1f339968775f53bfefe0.diff  ·  provenance: re-verified-this-session

- **CVE-2026-42190 (GHSA-m2m6-cff5-3w7c)** — CWE-352 · `redwoodjs/sdk` (npm `rwsdk`) · fixed 1.2.3 @ `c6e5ca170927f45c7da7a13f2e9d1dc2e47ba392` · **IN** (signature) · origin-check
  - Mechanism: `rwsdk` server actions enforced HTTP-method restrictions (non-`GET` only) but performed no Origin validation. Because `SameSite=Lax` session cookies are attached to top-level and same-site cross-origin requests alike, and the action request's content-type is CORS-safelisted (no preflight fires), any origin the browser treats as "same-site" with the deployed app (a sibling subdomain, or another `localhost` port in local dev) could invoke an authenticated victim's server actions with `mode: "no-cors"` — blind to the response, but still able to trigger writes/state changes.
  - Affected -> Fixed: >= 1.0.0-beta.50, <= 1.2.2 -> >= 1.2.3
  - Vulnerable shape (no lines removed; guard inserted before argument-decoding for non-GET requests):
    ```
    export async function rscActionHandler(
      req: Request,
      { getServerModuleExport, decodeReply }: RscActionHandlerDeps,
    ): Promise<unknown> {
      const url = new URL(req.url);
      const contentType = req.headers.get("content-type");

      let args: unknown[] = [];

      if (req.method === "GET") {
    ```
  - Guard added (post-patch):
    ```
    function validateSameOrigin(
      req: Request,
      allowedOrigins: readonly string[] | undefined,
    ): { valid: true } | { valid: false; response: Response } {
      const origin = req.headers.get("Origin");
      if (!origin) {
        return { valid: false, response: new Response("Missing Origin header", { status: 403 }) };
      }
      const selfOrigin = new URL(req.url).origin;
      if (origin === selfOrigin) {
        return { valid: true };
      }
      if (allowedOrigins && allowedOrigins.includes(origin)) {
        return { valid: true };
      }
      return { valid: false, response: new Response("Origin not allowed", { status: 403 }) };
    }

    export async function rscActionHandler(
      req: Request,
      { getServerModuleExport, decodeReply, allowedOrigins }: RscActionHandlerDeps,
    ): Promise<unknown> {
      const url = new URL(req.url);
      const contentType = req.headers.get("content-type");

      if (req.method !== "GET") {
        const originCheck = validateSameOrigin(req, allowedOrigins);
        if (!originCheck.valid) {
          return originCheck.response;
        }
      }
    ```
  - Reachability: sdk/src/runtime/register/methodEnforcer.ts rscActionHandler(), reached via any non-GET request to the RSC server-action endpoint of an app built with rwsdk (`serverAction()` or an RSC-protocol action), from any same-site-cookie-eligible origin.
  - Verdict: IN — Re-fetched commit this session; the `validateSameOrigin()` function and its call before request-argument decoding match verbatim. Clean, isolable origin-check guard with an explicit `allowedOrigins` escape hatch for legitimately cross-origin callers. Notably this is CSRF from a *same-site* (not cross-site) origin — method enforcement alone (the prior GHSA-x8rx-789c-2pxq fix) was insufficient because SameSite=Lax cookies don't distinguish sibling-subdomain/sibling-port origins. Matches CWE-352.
  - Source: https://github.com/redwoodjs/sdk/security/advisories/GHSA-m2m6-cff5-3w7c ; https://github.com/redwoodjs/sdk/commit/c6e5ca170927f45c7da7a13f2e9d1dc2e47ba392.diff  ·  provenance: re-verified-this-session

Dropped: CVE-2020-7534, CVE-2022-22811, CVE-2023-3589, CVE-2024-0555, CVE-2024-3083, CVE-2024-43684, CVE-2026-24345, CVE-2026-32989 (Schneider Electric Modicon/spaceLYnk, Dassault Teamwork Cloud, Full Compass WIC1200, Proges Sensor Net Connect, Microchip TimeProvider 4100, EZCast Pro II, Precurio Intranet Portal — all proprietary/closed-firmware or closed-source commercial products carried in the severity-precedent-corpus CSRF bucket via ICS-CERT/NVD advisories; none has a public git repository or fetchable fix-commit diff, only a version/firmware-revision bump. Never fabricate a hunk for these — kept in the severity corpus for CVSS-vector purposes only, excluded here for lack of a re-fetchable code delta.); CVE-2023-23724 (WP Email Capture WordPress plugin) (WordPress.org plugin repository is SVN-hosted (plugins.svn.wordpress.org), not git — no fetchable commit-diff URL of the GHSA/OSV/GitHub-commit shape this collector requires.); CVE-2024-39022 (idccms) (Surfaced in the severity corpus via a CNVD/NVD-style disclosure; no public source-code repository could be located this session — dropped for lack of a fetchable fix commit, not confirmed unfixed.); CVE-2024-47846 (Wikimedia MediaWiki Cargo extension) (Real, patched — fix is Gerrit change 1062723 at gerrit.wikimedia.org/r/c/mediawiki/extensions/Cargo/+/1062723. Wikimedia's canonical VCS is Gerrit, not GitHub; the extension is mirrored to github.com/wikimedia/mediawiki-extensions-Cargo but syncing the exact mirrored commit SHA to the Gerrit change wasn't verified this session, so dropped rather than guessed at.); CVE-2024-48962 (Apache OFBiz) (Real fix at commit 761fb67d7f (18.12.17, OFBIZ-13162), but per the severity corpus's own framing this is a chained CSRF+SameSite-bypass+Groovy/SSTI-code-injection fix, not an isolable single-mechanism CSRF guard — CONTESTED-flavored entanglement per the collector's own admissibility rule, dropped rather than force-fit as a clean CSRF-only anchor.); CVE-2026-27146 (GetSimple CMS, GHSA-26rv-8wpp-q84r) (Verified this session: the advisory lists no patched version at all (<=3.3.22 affected, no fix) — there is no fix commit to extract because the vulnerability is unpatched.); CVE-2025-54782 (GHSA-85cg-cmq5-qjm7, @nestjs/devtools-integration) (Verified this session: the advisory names no GIT-type affected range and no FIX-type commit reference, only a version bump to 0.2.1 with prose about a "safer sandbox alternative" and new origin/content-type checks — no single fix SHA could be resolved without further commit-mining not performed this session.)

## Reflected / Stored / DOM XSS  (CWE-79)

Grounds cards: skills/vulns/injection (generic output-neutralization framing; no dedicated XSS vuln card yet in this repo — see also skills/patterns for framework-specific templating guards).
Bucket verdict: **THIN -- 6 clean IN anchors across 6 distinct products (better-auth, Talishar, NocoDB, Statamic CMS, json-markup/Jaeger UI, Roundcube Webmail), one short of the strict "cleared" framing used for other buckets' 6-anchor bar when a 7th is required, plus 1 CONTESTED (Grav admin, multi-CVE omnibus commit) kept as illustrative.**  ·  6 IN / 1 CONTESTED / 6 dropped  ·  6 promotable signatures
Dominant guard shape for the class is bimodal by injection position: (1) **escape** — HTML-entity-encode the attacker-controlled value immediately before it is concatenated/interpolated into an HTML string or template output (better-auth `sanitize()`, Statamic `escapeHtml()`, json-markup `escape(key)`); (2) **param-binding + exact-match allowlist** — coerce the value to a constrained type and reject anything outside a tiny fixed set before it is stored/rendered (Talishar `intval()` + `!==1 && !==2` check); (3) **denylist→safe-API / DOMPurify sanitize** — run the whole untrusted string through a dedicated HTML sanitizer before persisting it (NocoDB `DOMPurify.sanitize()`); (4) **canonicalization-before-denylist-match** — normalize (here: `trim()`) the value before comparing it against a hard-coded denylisted attribute name, closing a whitespace-based filter bypass (Roundcube SVG `<animate>` sanitizer). Reflected and stored sub-mechanisms use the same guard vocabulary; the split is in *where* the guard sits (pre-render vs. pre-store) not in its shape.
Severity-corpus join: Joins the severity-precedent-corpus's "Reflected XSS" and "Stored XSS" (CWE-79) buckets (skills/oracles/references/severity-precedent-corpus.md) — three of this bucket's anchors are the *exact same* GHSA ids cited there for CVSS purposes (GHSA-9x4v-xfq5-m8x5/better-auth, GHSA-65mj-f7p4-wggq/Grav, CVE-2022-2022/NocoDB), letting a single id join a CVSS-vector prior (severity corpus) to a code-delta prior (here). The severity corpus's PR:N/UI:R reflected-XSS vectors (5.1-6.9 Medium) and PR:L-H/UI:R stored-XSS vectors (4.4-9.3, higher when the stored payload targets an admin/privileged viewer) both show up in this bucket's anchors: better-auth and Grav are unauthenticated-or-low-friction reflected cases; NocoDB, Statamic, and Roundcube are authenticated-poster-stores-for-higher-privilege-viewer stored cases matching the corpus's higher-C/I stored-XSS entries.

- **GHSA-9x4v-xfq5-m8x5 (no CVE assigned)** — CWE-79 · `better-auth/better-auth` · fixed 1.1.16 @ `7ae340e2eddad641b7e43d24d37c58a66ce9ddcf` · **IN** (signature) · escape
  - Mechanism: better-auth's `/api/auth/error` endpoint built its HTML error page by interpolating the `errorCode` value (sourced from the `error` URL query parameter) directly into a `<span>` with no output encoding. A victim who clicks an attacker-crafted link with a script payload in the `error` parameter executes attacker JS in the page's origin (reflected).
  - Affected -> Fixed: 0.0.2 - 1.1.16 (SEMVER only; advisory carries no GIT range) -> 1.1.16
  - Vulnerable shape (removed):
    ```
            <div class="error-code">Error Code: <span id="errorCode">${errorCode}</span></div>
    ```
  - Guard added (post-patch):
    ```
    function sanitize(input: string): string {
    	return input
    		.replace(/&/g, "&amp;")
    		.replace(/</g, "&lt;")
    		.replace(/>/g, "&gt;")
    		.replace(/"/g, "&quot;")
    		.replace(/'/g, "&#39;");
    }
    ...
            <div class="error-code">Error Code: <span id="errorCode">${sanitize(
    					errorCode,
    				)}</span></div>
    ```
  - Reachability: packages/better-auth/src/api/routes/error.ts `html()` template used by the `/api/auth/error` endpoint, reached by any unauthenticated request to `/api/auth/error?error=<payload>` — requires a victim click (UI:A) since the payload must be in the URL the victim loads.
  - Verdict: IN — Re-fetched the commit this session; the removed→added delta matches verbatim. Clean, isolable HTML-entity-escape guard applied at the single interpolation site; no entanglement with unrelated changes. Reflected XSS (URL-parameter-into-HTML, victim-click-required) matches CWE-79.
  - Source: https://github.com/advisories/GHSA-9x4v-xfq5-m8x5 ; https://api.osv.dev/v1/vulns/GHSA-9x4v-xfq5-m8x5 ; https://github.com/better-auth/better-auth/commit/7ae340e2eddad641b7e43d24d37c58a66ce9ddcf.diff  ·  provenance: re-verified-this-session

- **CVE-2026-25144 (GHSA-rrr4-h2pc-57g6)** — CWE-79 · `Talishar/Talishar` · fixed @ `09dd00e5452e3cd998eb1406a88e5b0fa868e6b4` (unversioned web app, commit-pinned) · **IN** (signature) · param-binding + exact-match allowlist
  - Mechanism: `SubmitChat.php` took the `playerID` GET parameter verbatim, used it to address per-player chat state, and rendered it back into a `<span>` on the shared game page with no type coercion or bound-check. Any value could be submitted and would be stored/rendered for every viewer of that game (session/impersonation risk), not merely reflected once.
  - Affected -> Fixed: all versions prior to the fix commit -> fixed at `09dd00e5`
  - Vulnerable shape (removed):
    ```
    $playerID = $_GET["playerID"];
    ```
  - Guard added (post-patch):
    ```
    $playerID = intval($_GET["playerID"]);
    if($playerID !== 1 && $playerID !== 2) {
      echo ("Invalid player ID.");
      exit;
    }
    ```
  - Reachability: `SubmitChat.php` top-level script, reached via any request (no auth required beyond an active game) supplying an arbitrary `playerID`; stored per-game and rendered whenever any participant views the current game page.
  - Verdict: IN — Re-fetched the commit this session; the removed→added delta matches verbatim. Clean, isolable param-binding (`intval`) plus a tiny exact-match allowlist (`1`/`2` — the only two valid player slots) inserted immediately at the point of use, before the value is stored/rendered. Stored XSS (attacker-controlled parameter persisted and executed for other viewers) matches CWE-79.
  - Source: https://github.com/Talishar/Talishar/security/advisories/GHSA-rrr4-h2pc-57g6 ; https://api.osv.dev/v1/vulns/CVE-2026-25144 ; https://github.com/Talishar/Talishar/commit/09dd00e5452e3cd998eb1406a88e5b0fa868e6b4.diff  ·  provenance: re-verified-this-session

- **CVE-2022-2022** — CWE-79 · `nocodb/nocodb` · fixed 0.91.7 @ `ffad5a318ad60d1da1c75dd28152827b94c92e9d` · **IN** (signature) · denylist→safe-API (DOMPurify sanitize)
  - Mechanism: NocoDB's project-creation API stored the user-supplied project `title` (and derived `slug`) with a `// todo: sanitize` comment marking the gap — no HTML/JS sanitization was applied before persisting it, and the title is later rendered in the project list/dashboard UI for every user with access to the project, executing any injected script.
  - Affected -> Fixed: < 0.91.7 -> 0.91.7
  - Vulnerable shape (removed):
    ```
    // todo: sanitize
    projectBody.slug = projectBody.title;
    ```
  - Guard added (post-patch):
    ```
    import DOMPurify from 'isomorphic-dompurify';
    ...
      projectBody.title = DOMPurify.sanitize(projectBody.title);
      projectBody.slug = projectBody.title;
    ```
  - Reachability: `packages/nocodb/src/lib/meta/api/projectApis.ts` `projectCreate()`, reached via any authenticated `POST` project-creation request with an HTML/JS payload in `title`; stored in the project record and rendered for every subsequent viewer of the project list/dashboard.
  - Verdict: IN — Re-fetched the commit this session; the removed comment→added `DOMPurify.sanitize()` call matches verbatim at the exact assignment site. The same commit also reformats an unrelated `projectCost()` function (semicolons/comment style) elsewhere in the same file — cosmetic churn, not entangled with the security guard itself, which remains a single clean before/after. Stored XSS matches CWE-79.
  - Source: https://nvd.nist.gov/vuln/detail/CVE-2022-2022 ; https://huntr.dev/bounties/f6082949-40d3-411c-b613-23ada2691913 ; https://api.osv.dev/v1/vulns/CVE-2022-2022 ; https://github.com/nocodb/nocodb/commit/ffad5a318ad60d1da1c75dd28152827b94c92e9d.diff  ·  provenance: re-verified-this-session

- **GHSA-ff9r-ww9c-43x8 (CVE-2026-25759)** — CWE-79 · `statamic/cms` · fixed 6.2.3 @ `6ed4f65f3387686d6dbd816e9b4f18a8d9736ff6` · **IN** (signature) · escape
  - Mechanism: Statamic's admin-panel Command Palette (a Vue component that fuzzy-searches and highlights content titles/other CP-searchable entities) built its highlighted-match HTML by calling `fuzzysort`'s `.highlight()` directly on the raw, unescaped search text and injecting the result as HTML. A user with content-creation permissions could set a title containing HTML/JS; when a higher-privileged user (e.g. an admin) later searched the Command Palette and it matched that title, the payload executed in the admin's session — usable for privilege escalation (e.g. silently creating a super-admin account).
  - Affected -> Fixed: 6.0.0 - 6.2.2 -> 6.2.3
  - Vulnerable shape (removed):
    ```
        let filtered = fuzzysort
            .go(query.value, filterableItems, {
                keys: ['text'],
                scoreFn: fuzzysortScoringAlgorithm,
            })
            .map(result => {
                return {
                    score: result._score,
                    html: result[0].highlight(`<span class="${highlightClasses}">`, '</span>'),
                    ...result.obj,
                };
            });
    ```
  - Guard added (post-patch):
    ```
    import { escapeHtml } from '@/bootstrap/globals.js';
    ...
    function highlightResult(text) {
        const classes = 'text-blue-600 dark:text-blue-400 underline underline-offset-4 decoration-blue-200 dark:decoration-blue-600/45';
        const safeText = escapeHtml(text);
        const result = fuzzysort.single(query.value, safeText);
        return result?.highlight(`<span class="${classes}">`, '</span>') || safeText;
    }
    ...
        let filtered = fuzzysort
            .go(query.value, filterableItems, {
                keys: ['text'],
                scoreFn: fuzzysortScoringAlgorithm,
            })
            .map(result => ({
                score: result._score,
                html: highlightResult(result.obj.text),
                ...result.obj,
            }));
    ```
  - Reachability: `resources/js/components/command-palette/CommandPalette.vue`, reached whenever any CP user with search access (any authenticated admin-panel user) types a query that matches an attacker-titled, attacker-created entity — the escape now runs before the matched text is ever turned into `.highlight()` HTML.
  - Verdict: IN — Re-fetched the commit this session; the removed inline `.highlight()` call and added `highlightResult()`/`escapeHtml()` wrapper match verbatim, applied uniformly to both the fuzzy-matched and the content-search result paths in the same file. Clean, isolable escape-before-render guard. Stored XSS (content-creator payload executes for a higher-privileged searcher) matches CWE-79.
  - Source: https://github.com/statamic/cms/security/advisories/GHSA-ff9r-ww9c-43x8 ; https://api.osv.dev/v1/vulns/GHSA-ff9r-ww9c-43x8 ; https://github.com/statamic/cms/commit/6ed4f65f3387686d6dbd816e9b4f18a8d9736ff6.diff  ·  provenance: re-verified-this-session

- **CVE-2023-36656** — CWE-79 (NVD primary record; the `jaegertracing/jaeger-ui` GHSA for this same CVE instead tags CWE-80, a cross-authority CWE disagreement noted in the severity corpus) · `mafintosh/json-markup` (Jaeger UI's JSON-rendering dependency, `packages/jaeger-ui`'s `KeyValuesTable`) · fixed json-markup 1.1.4 @ `e7fb4df7de6a7d57f2249f0527dda8b5498ad36b` (consumed by jaeger-ui v1.31.0) · **IN** (signature) · escape
  - Mechanism: json-markup (used by Jaeger UI's `KeyValuesTable` via `dangerouslySetInnerHTML` to render trace tag/process key-value objects) built its per-key HTML by string-concatenating the raw object key straight into a `<span>`, with no escaping. A trace containing attacker-controlled JSON object keys (e.g. a span tag key) renders that key unescaped, executing injected HTML/JS when any user views the trace in Jaeger UI. Note: the fetchable fix lives in the dependency's own repo — jaeger-ui's own fix commit is only a `package.json`/lockfile version bump + CHANGELOG entry pulling in the patched dependency, not a code change in jaeger-ui itself.
  - Affected -> Fixed: json-markup < 1.1.4 -> 1.1.4 (jaeger-ui < 1.31.0 -> 1.31.0)
  - Vulnerable shape (removed):
    ```
    return forEach(keys, '{', '}', function (key) {
      return '<span ' + style('json-markup-key') + '>"' + key + '":</span> ' + visit(obj[key])
    })
    ```
  - Guard added (post-patch):
    ```
    return forEach(keys, '{', '}', function (key) {
      return '<span ' + style('json-markup-key') + '>"' + escape(key) + '":</span> ' + visit(obj[key])
    })
    ```
  - Reachability: `mafintosh/json-markup` `index.js` key-rendering closure, reached transitively via `packages/jaeger-ui`'s `KeyValuesTable` component (`json-markup(obj)` call) whenever a trace with attacker-influenced tag/process keys is opened in the Jaeger UI trace view.
  - Verdict: IN — Re-fetched the commit (PR #15 merge, `e7fb4df`) this session; the removed→added delta is a single-line, isolable `escape(key)` wrap with no other changes in the diff. Stored XSS (attacker-controlled data persisted in trace storage, executed whenever any user views the trace) matches CWE-79 by the primary (NVD) CWE assignment and by mechanism (unescaped-key-into-HTML).
  - Source: https://api.osv.dev/v1/vulns/CVE-2023-36656 ; https://github.com/jaegertracing/jaeger-ui/pull/1498 ; https://github.com/mafintosh/json-markup/pull/15.diff  ·  provenance: re-verified-this-session

- **CVE-2024-37383 (GHSA-8j3w-26mp-75xh)** — CWE-79 · `roundcube/roundcubemail` · fixed 1.5.7 / 1.6.7 @ `43aaaa528646877789ec028d87924ba1accf5242` · **IN** (signature) · canonicalization-before-denylist-match
  - Mechanism: Roundcube's HTML sanitizer (`rcube_washtml`) blocks known-dangerous SVG attribute/value combinations (e.g. an `<animate>` element's `attributeName` targeting `href` with a `javascript:` URI) via an exact string-equality check between the attacker-supplied attribute name and the denylisted name. Because the check compared the raw (untrimmed) attribute value, an attacker could pad the attribute name with a trailing space (`attributeName="href "`) to fail the exact match and slip the `<animate>` element past the sanitizer; the element is left in the sanitized HTML and its `javascript:` URI executes when the message is previewed/rendered.
  - Affected -> Fixed: < 1.5.7 (and 1.6.x < 1.6.7) -> 1.5.7 / 1.6.7
  - Vulnerable shape (removed):
    ```
            foreach ($node->attributes as $name => $attr) {
                if (strtolower($name) === $attr_name) {
                    if (strtolower($attr_value) === strtolower($attr->nodeValue)) {
                        return true;
                    }
                }
    ```
  - Guard added (post-patch):
    ```
            foreach ($node->attributes as $name => $attr) {
                if (strtolower($name) === $attr_name) {
                    if (strtolower($attr_value) === strtolower(trim($attr->nodeValue))) {
                        return true;
                    }
                }
    ```
  - Reachability: `program/lib/Roundcube/rcube_washtml.php` `attribute_value()`, reached via the HTML message sanitizer's SVG handling whenever a victim previews/opens an attacker-crafted HTML email containing an `<svg><animate attributeName="href " .../></svg>` payload.
  - Verdict: IN — Re-fetched the commit this session; the removed→added delta is a single `trim()` insertion at the exact comparison site, plus an added regression test (`tests/Framework/Washtml.php`) exercising precisely this bypass. Clean, isolable canonicalization-before-match guard closing a whitespace-based denylist bypass. XSS via HTML-sanitizer bypass in a webmail client (executes for the message-viewing user) matches CWE-79.
  - Source: https://github.com/advisories/GHSA-8j3w-26mp-75xh ; https://nvd.nist.gov/vuln/detail/CVE-2024-37383 ; https://api.osv.dev/v1/vulns/CVE-2024-37383 ; https://github.com/roundcube/roundcubemail/commit/43aaaa528646877789ec028d87924ba1accf5242.diff  ·  provenance: re-verified-this-session

- **CVE-2025-66309 (GHSA-65mj-f7p4-wggq)** — CWE-79 · `getgrav/grav` (fix lands in the `grav-plugin-admin` submodule) · fixed 1.8.0-beta.27 @ `99f653296504f1d6408510dd2f6f20a45a26f9b0` · **CONTESTED** (illustrative) · escape
  - Mechanism: Grav admin's Selectize-backed multi-select form fields (used across several admin panel screens, including the Blog post `data[header][content][items]` field named in the advisory) rendered each option/item's text into the dropdown via a custom `render` function that interpolated the raw item text into HTML with no escaping. An authenticated admin (PR:H) supplying attacker-controlled item text, combined with a victim admin interacting with the field (UI:A), executes injected JS.
  - Affected -> Fixed: < 1.8.0-beta.27 -> 1.8.0-beta.27
  - Vulnerable shape (no lines removed for this GHSA specifically; guard inserted as new default render functions ahead of the existing custom-render call site in `selectize.js`, ADR pattern):
    ```
    export default class SelectizeField {
        constructor(options = {}) {
            this.options = Object.assign({}, options);
    ...
                data = $.extend({}, data, { render: PagesRoute });
            }

            if (!field.length || field.get(0).selectize) { return; }
    ```
  - Guard added (post-patch):
    ```
    // Security: Default render functions that escape HTML to prevent XSS
    // (GHSA-65mj-f7p4-wggq, GHSA-7g78-5g5g-mvfj, GHSA-mpjj-4688-3fxg)
    const SafeRender = {
        option: function(item, escape) {
            return `<div>${escape(item.text || item.value)}</div>`;
        },
        item: function(item, escape) {
            return `<div>${escape(item.text || item.value)}</div>`;
        }
    };
    ...
            // Security: Apply safe render functions by default to escape HTML
            // Only apply if no custom render is already defined
            if (!data.render) {
                data = $.extend({}, data, { render: SafeRender });
            }
    ```
  - Reachability: `themes/grav/app/forms/fields/selectize.js` `SelectizeField`, reached via any admin panel screen using a Selectize field with no custom `render` supplied (the advisory names the Blog post `data[header][content][items]` field) — requires an authenticated attacker (PR:H) and a victim admin interacting with the field (UI:A) per the CVSS vector.
  - Verdict: CONTESTED — Re-fetched the commit this session; the `SafeRender` block and its inline comment explicitly name `GHSA-65mj-f7p4-wggq` as one of four distinct GHSAs this single commit fixes together (`GHSA-65mj-f7p4-wggq`, `GHSA-7g78-5g5g-mvfj`, `GHSA-mpjj-4688-3fxg`, `GHSA-rmw5-f87r-w988`), bundled alongside an unrelated password-reset rate-limiting fix (`GHSA-q3qx-cp62-f6m7`) and cosmetic reformatting of `admin.min.js`. The `selectize.js` hunk itself is clean and attributable to this GHSA via the maintainers' own comment, but the commit as a whole is a squashed multi-CVE release bundle — cited to illustrate the escape-before-render shape, not promoted as a literal single-GHSA signature.
  - Source: https://github.com/advisories/GHSA-65mj-f7p4-wggq ; https://api.osv.dev/v1/vulns/GHSA-65mj-f7p4-wggq ; https://github.com/getgrav/grav-plugin-admin/commit/99f653296504f1d6408510dd2f6f20a45a26f9b0.diff  ·  provenance: re-verified-this-session

Dropped: CVE-2026-42321 (GHSA-hwjc-8228-55x4, GLPI stored XSS in asset locks) (OSV's GIT range 'fixed' event resolves to `d91722c60d7552ae96c79774793bf45d78eb9771`, but that commit is a one-line `GLPI_VERSION` string bump (`10.0.25-dev` -> `10.0.25`) with no code change — a release-tagging commit, not the actual fix. Searched for the real code-level fix commit and could not isolate a single fetchable SHA this session; dropped rather than fabricate a hunk from the version-bump commit.); CVE-2026-24674 (GHSA-gqvp-w22w-w99r, Open eClass reflected XSS across multiple endpoints) (Same failure mode as GLPI above: OSV's GIT 'fixed' SHA `6a98ba9fb5ce499b53d2cd0708f3080d92632dfa` is only an `ECLASS_VERSION` string bump (`4.2-dev` -> `4.2`), not a code diff. No isolable single fix commit found via search; dropped.); CVE-2025-48489 (FreeScout stored XSS, mailbox name field) (Fix commit `9879e29c2054e842143620f40bac0eabf44c8054` is real and fetchable but is a large security-hardening release spanning 18 files (mass-assignment field-allowlisting across 6+ controllers, session/config hardening, policy changes) with the mailbox-name XSS fix entangled inside a broader `$request->all()` -> explicit-`$allowed_fields` mass-assignment refactor — no single isolable escape/sanitize hunk could be extracted as a clean CWE-79-only guard; dropped as over-entangled rather than force-fit.); GHSA-465g-4q99-5x86 (NukeViet multiple anti-XSS filter bypasses, News module) (Advisory prose names the exact fix location — `filterAttr()`/`unhtmlentities()` in `vendor/vinades/nukeviet/Core/Request.php` — but supplies no GIT range and no resolvable commit SHA (only a placeholder in the advisory text and a version-only reference to 4.6.00); could not resolve a fetchable diff this session.); GHSA-w9f3-qc75-qgx9 (PrestaShop stored XSS in Customer Service view) and CVE-2026-33673 (PrestaShop back-office template-variable stored XSS) (Both advisories carry only ECOSYSTEM/Packagist version ranges (fixed 8.2.6/9.1.1 and unspecified respectively), no GIT range and no FIX-type reference; PrestaShop's security advisories on this repo do not consistently link a single commit SHA — dropped for lack of a resolvable fix commit rather than guessed from the version tag.); nocodb `0a4219c0b059faef79a9738462f039edda1f15ec` (the OTHER 'fixed' SHA on the same CVE-2022-2022 GIT range) (This companion commit is package.json/package-lock.json/lockfile version bumps only across 4 packages, no code change — the actual code fix is the sibling SHA `ffad5a318ad60d1da1c75dd28152827b94c92e9d` used as the anchor above; noted here so the dropped SHA isn't mistaken for a second independent anchor.)

# --- TOP-UP ADDENDUM ---

Second-pass anchors: additional anchors for previously-thin buckets (dedup vs the anchors above) and brand-new bucket sections. Same gate and provenance rules as the main corpus.

## SSRF  (CWE-918) — TOP-UP (additional anchors; dedup vs the main section above)

Grounds cards: skills/patterns/ssrf-server-side-fetch, skills/vulns/information-disclosure
Bucket verdict: **IN — 7 clean IN anchors after merge (existing grafana / plane / new-api / axios / next.js + these css_parser & keycloak) plus 2 illustrative CONTESTED (SuiteCRM, parse-server), comfortably above the 6-clean bar. Dominant guard shape: destination-allowlist / SSRF-filter "bound" (4 of 7 clean: plane, new-api, css_parser, keycloak), with a canonicalization sub-cluster (grafana, axios) and one trusted-source param-binding (next.js).**  ·  2 IN / 0 CONTESTED / 3 dropped  ·  2 promotable signatures
Severity-corpus join: Both join the SSRF (CWE-918) severity-corpus bucket's Network-AV/Low-AC outbound-fetch center of mass: css_parser sits at the high end (attacker-@import server-side fetch escalating via a Location: file:// redirect into arbitrary local file read, C:H) while Keycloak's authenticated (PR:L) blind backchannel-logout host-coercion sits mid-bucket — together anchoring the PR:N->PR:L and confidentiality-impact spread already framed by grafana/new-api (unauth/metadata, high) down to SuiteCRM (authenticated proxy, medium).

- **CVE-2026-53727 (GHSA-9pmc-p236-855h)** — CWE-918 · `premailer/css_parser` · fixed 3.0.0 @ `7d2ddf0189cd54b54f378f59daefa10cb036e476` · **IN** (signature) · bound
  - Mechanism: CssParser::Parser#read_remote_file issued a raw Net::HTTP request against any attacker-supplied host/port/scheme with no allowlist, and its own 3xx redirect-follow branch recursed back into the same function which also served file:// URIs directly via File.read -- so a single attacker-controlled HTTP redirect (Location: file://...) upgraded plain SSRF into arbitrary local file disclosure. Reached via Parser#load_uri! or Parser#add_block!(css, base_uri:) resolving an attacker-supplied @import url(...) in CSS (Premailer's canonical use case), requiring only the ability to land one @import rule in CSS the host application parses.
  - Affected -> Fixed: 0.9.0 - 2.2.0 -> 3.0.0 -> 3.0.0
  - Vulnerable shape (removed):
    ```
            uri = Addressable::URI.parse(uri.to_s)
    
            if uri.scheme == 'file'
              # local file
              path = uri.path
              path.gsub!(%r{^/}, '') if Gem.win_platform?
              src = File.read(path, mode: 'rb')
            else
              # remote file
              if uri.scheme == 'https'
                uri.port = 443 unless uri.port
                http = Net::HTTP.new(uri.host, uri.port)
                http.use_ssl = true
              else
                http = Net::HTTP.new(uri.host, uri.port)
              end
    
              res = http.get(uri.request_uri, {'User-Agent' => @options[:user_agent], 'Accept-Encoding' => 'gzip'})
              src = res.body
              charset = res.respond_to?(:charset) ? res.encoding : 'utf-8'
    
              if res.code.to_i >= 400
                @redirect_count = nil
                raise RemoteFileError, uri.to_s if @options[:io_exceptions]
    
                return '', nil
              elsif res.code.to_i >= 300 and res.code.to_i < 400
                unless res['Location'].nil?
                  return read_remote_file Addressable::URI.parse(Addressable::URI.escape(res['Location']))
                end
              end
            end
    ```
  - Guard added (post-patch):
    ```
          unless REMOTE_ALLOWED_SCHEMES.include?(uri.scheme)
            raise RemoteFileError, uri.to_s if @options[:io_exceptions]
    
            return nil, nil
          end
    
          begin
            res = if @options[:allow_local_network]
                    fetch_via_net_http(uri)
                  else
                    SsrfFilter.get(
                      uri.to_s,
                      scheme_whitelist: REMOTE_ALLOWED_SCHEMES,
                      max_redirects: MAX_REDIRECTS,
                      headers: {'User-Agent' => @options[:user_agent]}
                    )
                  end
    ```
  - Reachability: lib/css_parser/parser.rb Parser#read_remote_file(uri), called from Parser#load_uri! and from Parser#add_block!(css, base_uri:) when it scans CSS for @import url(...) rules -- reached by any application (e.g. Premailer) that parses attacker-influenced CSS with a base_uri set
  - Verdict: IN — Re-fetched the commit .diff this session: focused 5-file security fix (Gemfile.lock, css_parser.gemspec adds ssrf_filter ~>1.5, lib/css_parser.rb require, lib/css_parser/parser.rb, test/test_css_parser_loading.rb), not a sprawling refactor, and the removed_lines/added_lines match the real delta. Clean, isolable destination-bound guard: REMOTE_ALLOWED_SCHEMES=%w[http https] rejects any non-http(s) scheme (killing the file:// -> File.read LFI-escalation branch) and the outbound fetch is routed through SsrfFilter.get(scheme_whitelist:, max_redirects:), whose helper also re-validates each redirect hop -- closing both the raw SSRF and the Location: file:// redirect->LFI upgrade in one guard. Attacker-@import server-side fetch matches CWE-918. promote_signature=true.
  - Source: https://api.osv.dev/v1/vulns/GHSA-9pmc-p236-855h ; https://github.com/premailer/css_parser/security/advisories/GHSA-9pmc-p236-855h ; https://github.com/premailer/css_parser/commit/7d2ddf0189cd54b54f378f59daefa10cb036e476.diff  ·  provenance: re-verified-this-session

- **CVE-2026-4874 (GHSA-22rm-wp4x-v5cx)** — CWE-918 · `keycloak/keycloak` · fixed 26.4.13 / 26.6.3 @ `00dd0dd716c4319d3bac3eb2f2ac22d2a94f79fd` · **IN** (signature) · bound
  - Mechanism: During a refresh-token request, OAuth2GrantTypeBase#updateClientSession took the attacker-controlled 'client_session_host' form parameter and stored it verbatim into the client session's CLIENT_SESSION_HOST note with no validation. When a client is configured with a backchannel.logout.url containing the application.session.host placeholder, ResourceAdminManager later substituted that stored, attacker-controlled value directly into the logout URL template and issued the outbound backchannel-logout HTTP request to it -- letting an authenticated attacker coerce Keycloak into sending requests to an arbitrary host.
  - Affected -> Fixed: 26.5.0 - 26.6.2 -> 26.6.3 (also <= 26.4.12 -> 26.4.13, same fix backported) -> 26.4.13 / 26.6.3
  - Vulnerable shape (removed):
    ```
                String oldClientSessionHost = clientSession.getNote(AdapterConstants.CLIENT_SESSION_HOST);
                if (!Objects.equals(adapterSessionHost, oldClientSessionHost)) {
                    clientSession.setNote(AdapterConstants.CLIENT_SESSION_HOST, adapterSessionHost);
                }
    ```
  - Guard added (post-patch):
    ```
                if ((adapterSessionHost != null) && (!adapterSessionHost.trim().isEmpty())) {
                    // CVE-2026-4874 - client_session_host requires validation as an external field that is stored in client
                    // session and can be used to generate logout callback URL.
                    if (!ClientHostUtils.isHostAllowedForClient(adapterSessionHost, client, session)) {
                        logger.warnf("Adapter Session '%s' not valid in ClientSession for client '%s'. Host is '%s' and has been removed.",
                                adapterSessionId, client.getClientId(), adapterSessionHost);
                        return;
                    }
    
                    String oldClientSessionHost = clientSession.getNote(AdapterConstants.CLIENT_SESSION_HOST);
                    if (!Objects.equals(adapterSessionHost, oldClientSessionHost)) {
                        clientSession.setNote(AdapterConstants.CLIENT_SESSION_HOST, adapterSessionHost);
                        logger.debugf("Adapter Session '%s' saved in ClientSession for client '%s'. Host is '%s'",
                                adapterSessionId, client.getClientId(), adapterSessionHost);
                    }
                }
    ```
  - Reachability: services/src/main/java/org/keycloak/protocol/oidc/grants/OAuth2GrantTypeBase.java updateClientSession(), reached via any OAuth2 refresh-token request carrying the client_session_host adapter form parameter; the new ClientHostUtils.isHostAllowedForClient() gate restricts the value to the client's registered management/admin URL host or registered cluster-node hosts before it can ever be stored and later used by ResourceAdminManager.logoutClientSessionWithBackchannelLogoutUrl() to build the outbound backchannel-logout request
  - Verdict: IN — Re-fetched the commit .diff this session: well-contained single-commit fix touching 6 files (upgrade doc, OAuth2GrantTypeBase.java sink, new ClientHostUtils.java + ClientHostUtilsTest.java with 23 tests, ResourceAdminManager.java, integration LogoutTest.java). Clean, isolable destination-allowlist (bound) guard: the attacker-controlled client_session_host is gated by ClientHostUtils.isHostAllowedForClient(adapterSessionHost, client, session) -- restricting it to the client's registered management/admin-URL host or cluster-node hosts -- and the flow returns early before the value can be stored in the CLIENT_SESSION_HOST note that ResourceAdminManager later substitutes into the backchannel.logout.url template. The security guard hunk is verbatim; note the real diff also reformats an adjacent NON-security debug-log line (adds clientSession.getId() to the 'saved in ClientSession' message) that the copied hunk does not fully capture -- cosmetic, does not affect the promotable guard signature. Authenticated (PR:L) refresh-token host-coercion SSRF matches CWE-918. promote_signature=true.
  - Source: https://api.osv.dev/v1/vulns/GHSA-22rm-wp4x-v5cx ; https://github.com/advisories/GHSA-22rm-wp4x-v5cx ; https://github.com/keycloak/keycloak/commit/00dd0dd716c4319d3bac3eb2f2ac22d2a94f79fd  ·  provenance: re-verified-this-session

Dropped: CVE-2026-50552 (Koel, GHSA-jr4p-4xjh-fwvw) (Upheld drop. Fix commit 5f6ce2cefd08f437a269236b677ad971517ccbb6 is a genuine CWE-918 SSRF hardening but is an entangled 28-file multi-concern refactor (helper namespace move, new ip-lib dependency, Guzzle middleware rewrite, per-hop IP pinning, multiple call-site injections, test relocations) with no single isolable guard hunk to promote as a signature; would be CONTESTED at best and no verbatim hunk was supplied. Bucket already clears the 6-clean bar with cleaner anchors, so not promoted.); CVE-2025-62427 (@angular/ssr, GHSA-q63q-pgmf-mxhr) (Deferred, NOT OUT. Collector notes commit 942d76fab514899b65c681425117e8305df3e17c is a clean single-file/single-hunk IN-quality fix (URL-constructor single-string-argument swap) held back only for npm-ecosystem diversity (axios + next.js already in bucket). 'Too much npm' is not a gate drop reason, but no verbatim hunk was supplied and the bucket already reaches IN (7 clean) without it, so it stays available -- promote if a 3rd clean anchor is later wanted.); CVE-2026-1180 (Keycloak jwks_uri, GHSA-7vw6-5q2f-7w5r) (Upheld drop (unverifiable/OUT). OSV record has no GIT range and no FIX/commit/PR reference -- only an ECOSYSTEM last_affected event and a still-open GitHub issue (#45645) with no linked fix commit. No re-fetchable code delta exists at adjudication time.)

## OS command injection -> RCE  (CWE-78) — TOP-UP (additional anchors; dedup vs the main section above)

Grounds cards: skills/vulns/os-command-injection, skills/vulns/injection
Bucket verdict: **IN — 7 clean anchors (5 prior + PraisonAI allowlist + Greenshot denylist), crossing the 6-anchor threshold. Dominant guard shape: neutralize the shell/spawn reachability of attacker-controlled input at the process boundary — either an executable/command allowlist (PraisonAI, strongest form) or shell-metacharacter denylist + quote-escaping before the string reaches cmd.exe/PowerShell/open_process (Greenshot, and the bucket's npm/C/JS argument-quoting fixes). New anchors also diversify ecosystem beyond the prior npm/C/JS concentration into PyPI/Python and NuGet/.NET. Maintainer note: the PraisonAI anchor's commit is the second of two fixes for the same CLI-command-injection bug (first fix 4.5.69/CVE-2026-34935 was incomplete); the Greenshot advisory does not hyperlink its fix commit, corroborated instead by the re-fetched diff matching the advisory's code location and mechanism exactly.**  ·  2 IN / 0 CONTESTED / 4 dropped  ·  2 promotable signatures
Severity-corpus join: Joins the severity-corpus 'command-injection -> RCE' bucket: impact C:H/I:H/A:H, but attack vector is Local — Greenshot via crafted capture filename or malicious greenshot-fixed.ini, PraisonAI via CLI --mcp / config string (AV:L, PR:N/L, UI often required) — so base scores land High (~7.0-8.0), not auto-Critical; escalate to AV:N only where the command/config string is demonstrably supplied from a remote untrusted source.

- **GHSA-9qhq-v63v-fv3j** — CWE-78 (also tagged CWE-77) — GitHub Advisory Database primary record · `MervinPraison/PraisonAI` · fixed 4.5.149 @ `47bff65413beaa3c21bf633c1fae4e684348368c` · **IN** (signature) · allowlist (basename executable allowlist)
  - Mechanism: The praisonai CLI's --mcp flag is parsed by MCPHandler.parse_mcp_command() using shlex.split(), which splits the command string into an executable and args but performs no allowlist/validation of the resulting executable before the result is handed to create_mcp_tools() -> praisonaiagents.MCP() -> anyio.open_process(); arbitrary host binaries (bash -c, python -c, curl|sh, etc.) could be launched via an attacker-influenced --mcp command/config value. This GHSA documents that the gap survived the first fix (4.5.69, GHSA-9gm9-c8mq-vq7m / CVE-2026-34935), which was incomplete; the follow-up commit 47bff654 adds the basename executable allowlist.
  - Affected -> Fixed: PyPI praisonai < 4.5.149 (gap present even after the incomplete 4.5.69 fix for CVE-2026-34935) -> 4.5.149
  - Vulnerable shape (removed):
    ```
            cmd, args, env = self.parse_mcp_command(command, env_vars)
    ```
  - Guard added (post-patch):
    ```
    ALLOWED_MCP_COMMANDS = {
        "npx", "npx.cmd", "npx.exe",
        "node", "node.exe",
        "python", "python3", "python.exe", "python3.exe",
        "uvx", "uvx.exe",
        "uv", "uv.exe",
        "docker", "docker.exe",
        "deno", "deno.exe",
        "bun", "bun.exe",
        "pipx",
    }
    ...
            # Validate executable against allowlist
            basename = os.path.basename(cmd)
            if basename not in ALLOWED_MCP_COMMANDS:
                raise ValueError(
                    f"Command '{cmd}' is not in the allowed MCP executables list. "
                    f"Allowed: {', '.join(sorted(ALLOWED_MCP_COMMANDS - {c for c in ALLOWED_MCP_COMMANDS if '.' in c}))}"
                )
    ...
            try:
                cmd, args, env = self.parse_mcp_command(command, env_vars)
            except ValueError as e:
                self.print_status(str(e), "error")
                return None
    ```
  - Reachability: parse_mcp_command() in src/praisonai/praisonai/cli/features/mcp.py, invoked from MCPHandler.create_mcp_tools(); reached by any use of `praisonai "<prompt>" --mcp "<command>"` (or equivalent config) whose command string is attacker-influenced.
  - Verdict: IN — Re-fetched commit 47bff654 this session via .diff; the three claimed hunks (ALLOWED_MCP_COMMANDS set, os.path.basename allowlist check, try/except around parse_mcp_command) all appear verbatim in src/praisonai/praisonai/cli/features/mcp.py. Single cleanly-isolable executable allowlist that directly blocks arbitrary-binary launch; CWE-78/77 mechanism match confirmed. The second-of-two-fixes history is a maintainer note only, not diff entanglement. New ecosystem (PyPI/Python); no id collision with the bucket's npm/C/JS anchors.
  - Source: https://api.osv.dev/v1/vulns/GHSA-9qhq-v63v-fv3j ; https://github.com/MervinPraison/PraisonAI/security/advisories/GHSA-9qhq-v63v-fv3j ; https://github.com/MervinPraison/PraisonAI/commit/47bff65413beaa3c21bf633c1fae4e684348368c ; https://nvd.nist.gov/vuln/detail/CVE-2026-34935 ; https://github.com/MervinPraison/PraisonAI/security/advisories/GHSA-9gm9-c8mq-vq7m  ·  provenance: re-verified-this-session

- **CVE-2026-22035 (GHSA-7hvw-q8q5-gpmj)** — CWE-78 (GitHub Advisory primary record) · `greenshot/greenshot` · fixed 1.3.311 @ `5dedd5c9f0a9896fa0af1d4980d875a48bf432cb` · **IN** (signature) · denylist (shell-metacharacter denylist + escaping)
  - Mechanism: FormatArguments() built the ExternalCommand plugin's shell argument string with string.Format(arguments, fullpath), splicing the screenshot's full file path directly into a template later executed via cmd.exe/PowerShell, with no metacharacter filtering or quoting. The path is attacker-controllable two ways: (1) a crafted capture filename containing shell metacharacters (e.g. `test.png" & calc.exe & echo ".png`), or (2) a malicious greenshot-fixed.ini supplying the `arguments` template itself; either lets an attacker inject and run arbitrary commands when the ExternalCommand destination processes the file.
  - Affected -> Fixed: Greenshot.Plugin.ExternalCommand (NuGet/.NET, greenshot/greenshot) <= 1.3.310 -> 1.3.311
  - Vulnerable shape (removed):
    ```
    return string.Format(arguments, fullpath);
    ```
  - Guard added (post-patch):
    ```
    // Validate filename doesn't contain shell metacharacters
    char[] dangerousChars = { '&', '|', ';', '$', '`', '(', ')', '<', '>', '\n', '\r', '"', '\'', '\\' };
    
    if (fullpath.IndexOfAny(dangerousChars) >= 0)
    {
        throw new ArgumentException(
            "Filename contains potentially dangerous characters. " +
            "For security reasons, filenames with shell metacharacters are not allowed."
        );
    }
    
    // Validate arguments template doesn't use shell interpreters
    if (arguments.Contains("cmd.exe") || arguments.Contains("powershell"))
    {
        LOG.Warn("ExternalCommand configured with shell interpreter - potential security risk");
    }
    
    // Additional: Ensure proper quoting
    string safePath = fullpath.Replace("\"", "\\\"");
    
    return string.Format(arguments, safePath);
    ```
  - Reachability: FormatArguments(string arguments, string fullpath) in src/Greenshot.Plugin.ExternalCommand/ExternalCommandDestination.cs, called from CallExternalCommand(); reached whenever the ExternalCommand destination plugin exports/opens a capture, via either a crafted capture filename or a malicious greenshot-fixed.ini arguments template.
  - Verdict: IN — Re-fetched commit 5dedd5c this session via .diff; the only security-relevant file changed is ExternalCommandDestination.cs, where `return string.Format(arguments, fullpath);` is replaced by the dangerousChars denylist + IndexOfAny throw + quote-escaping guard (all hunks match verbatim). Other touched file is a readme ticket-URL bump — trivial, non-entangling. Mechanism matches GHSA-7hvw-q8q5-gpmj (crafted filename / malicious ini -> cmd.exe/PowerShell injection). Advisory page doesn't hyperlink the commit, but the diff is definitive and re-fetchable, so IN over CONTESTED. New ecosystem (NuGet/.NET); no id collision with the bucket's npm/C/JS anchors.
  - Source: https://github.com/greenshot/greenshot/security/advisories/GHSA-7hvw-q8q5-gpmj ; https://github.com/greenshot/greenshot/commit/5dedd5c9f0a9896fa0af1d4980d875a48bf432cb ; https://www.sentinelone.com/vulnerability-database/cve-2026-22035/ ; https://secalerts.co/vulnerability/CVE-2026-22035  ·  provenance: re-verified-this-session

Dropped: GHSA-9gm9-c8mq-vq7m / CVE-2026-34935 (Superseded — this is the ORIGINAL PraisonAI advisory; its fix (4.5.69) was itself documented as incomplete, so the follow-up GHSA-9qhq-v63v-fv3j / commit 47bff654 (which adds the actual allowlist guard) is the admissible anchor instead. Structural duplicate of the IN PraisonAI anchor.); GHSA-36p8-mvp6-cv38 / CVE-2026-0933 (Cloudflare Wrangler, --commit-hash) (Real npm CWE-78 fix with a fetchable commit, but same ecosystem (npm/JS) already saturated in this bucket (shell-quote, claudecodeui, node-glob, @npmcli/git); passed over for ecosystem diversity now that the bucket has crossed threshold. Available as a spare if an npm anchor is later invalidated.); CVE-2025-9997 / GHSA-22q2-gf4f-hvw6 (Schneider Electric BLMon/Saitel RTU) (Unverifiable — vendor-PDF-only advisory, no source repo or fetchable commit/diff; re-confirmed no fetchable diff exists. Fails the re-fetchable gate.); Gogs GHSA-67mx-jc2f-jgjm / CVE-2022-1986 (Weaker class-match — mechanism is a crafted-config SSH-key/hook path leading to execution via git hooks, not a direct shell-interpolation/allowlist case; passed over in favor of the two cleaner shell-boundary anchors.)

## Path traversal / LFI  (CWE-22 / CWE-98) — TOP-UP (additional anchors; dedup vs the main section above)

Grounds cards: skills/vulns/path-traversal-lfi
Bucket verdict: **THIN (this run) — 0 net-new clean anchors. Both IN candidates (pip commonprefix->commonpath; tzinfo ^/$ -> \A/\z) and the CONTESTED reposilite candidate are exact-id duplicates already seated in the corpus bucket, so the hard dedup rule drops all three ahead of keep-bias. The existing corpus bucket is unchanged and already stands IN (7 clean IN + 2 CONTESTED, 7 promotable signatures). Dominant guard shapes among the duplicated candidates: bound-containment (pip, char-wise -> path-segment-wise prefix comparison) and allowlist-regex-anchor (tzinfo, Ruby multiline-anchor bypass closed). No promotable signatures added by this run.**  ·  0 IN / 0 CONTESTED / 3 dropped  ·  0 promotable signatures
Severity-corpus join: Would join the severity-corpus path-traversal/LFI bucket (CWE-22/23/98) at its two existing seats — pip GHSA-6vgw-5pg2-w6jp (CVSS 4.0 ~2.7, write bounded to install-dir prefixes) and tzinfo CVE-2022-31163 (CVSS 3.1 7.5, arbitrary Ruby `require`, RCE-adjacent read) — but both are already present, so this run contributes no new severity vectors to that bucket.

Dropped: CVE-2026-1703 (GHSA-6vgw-5pg2-w6jp), pypa/pip (already in corpus — exact-id duplicate of the IN anchor at skills/oracles/references/ghsa-fix-diff-corpus.md:1270. Same GHSA, same fix_sha 8e227a9be4faa9594e05d02ca05a413a2a4e7735, byte-identical removed/added hunk (commonprefix->commonpath, return prefix == abs_directory). Hard dedup DROP per gate rule; not re-adjudicated. (Would otherwise grade IN — clean isolable bound/containment guard, CWE-22 class-match.)); CVE-2022-31163 (GHSA-5cm2-9h8c-rvfx), tzinfo/tzinfo (already in corpus — exact-id duplicate of the IN anchor at skills/oracles/references/ghsa-fix-diff-corpus.md:1287. Same GHSA, same fix_sha 9905ca93abf7bf3e387bd592406e403cd18334c7, byte-identical removed/added hunk (multiline ^/$ anchors -> string-boundary \A/\z on the identifier allowlist). Hard dedup DROP per gate rule. (Would otherwise grade IN — clean isolable allowlist-anchor guard, CWE-22/CWE-23 class-match.)); CVE-2024-36117 (GHSA-82j3-hf72-7x93), dzikoysk/reposilite (already in corpus — collector carried it as CONTESTED/illustrative and it is already seated as the CONTESTED anchor at skills/oracles/references/ghsa-fix-diff-corpus.md:1340 (genuine Location.of() normalization fix bundled with a Gradle-wrapper bump, import reorder, and a Kotlin .values()->.entries deprecation fix across 5 files — entangled, not isolable). Stays dropped from this run's net-new output; no change to its existing CONTESTED standing.)

## Insecure deserialization -> RCE  (CWE-502) — TOP-UP (additional anchors; dedup vs the main section above)

Grounds cards: skills/vulns/insecure-deserialization
Bucket verdict: **IN — 3 new clean IN anchors this pass (serialize-javascript, MessagePack-CSharp, PyTorch) + 3 pre-existing IN (ActiveMQ, fastjson, parquet-java) = 6 clean, clearing the <6 THIN threshold across 4 ecosystems (Java, npm, NuGet, PyPI). Dominant guard shape: deser-type-filter (allow/denylist on a reflectively-resolved class) at 4/6 anchors (ActiveMQ, fastjson, parquet-java, and MessagePack-CSharp made recursive over arrays/generics); two novel shapes added this pass — unpredictable-token+escape-boundary-check (serialize-javascript) and unsafe-fallback-path denial (PyTorch).**  ·  3 IN / 0 CONTESTED / 0 dropped  ·  3 promotable signatures
Severity-corpus join: Joins the CWE-502 deserialization-RCE severity-corpus bucket: RCE sinks cluster at network vector + C:H/I:H/A:H, with overall severity gated by preconditions — serialize-javascript High (CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H = 8.1, needs an eval()-consumer plus a UID guess), PyTorch Critical (weights_only=True silently bypassed on an untrusted legacy-.tar checkpoint), MessagePack-CSharp Medium (needs the Typeless resolver + untrusted payload to bypass the denylist) — spanning Medium->Critical.

- **CVE-2020-7660 (GHSA-hxcc-f52p-wc94)** — CWE-502 · `yahoo/serialize-javascript` · fixed 3.1.0 @ `f21a6fb3ace2353413761e79717b2d210ba6ccbd` · **IN** (signature) · unpredictable-token + escape-boundary check (crypto-random placeholder UID via require('randombytes') replacing Math.random, plus a backslash-precedence test that refuses to substitute a placeholder match found inside an already-escaped string literal)
  - Mechanism: serialize() embeds function/regexp/date/map/set values as string placeholder tokens of the form "@__R-<UID>-0__@" and later regex-replaces them for their unsafe JS source text; the consuming application's documented deserialization step is eval()'ing that output. The internal UID was generated with Math.floor(Math.random()*0x10000000000) -- a ~4-billion-value keyspace guessable over the network -- so an attacker who controls a string field of the serialized object can craft a fake placeholder token matching the guessed UID that the placeholder-substitution regex then fires on inside what should have been an inert string literal, breaking out of the string boundary and splicing attacker JS into the eval()'d output, i.e. RCE via the serialize->eval deserialization path.
  - Affected -> Fixed: npm serialize-javascript >=0, <3.1.0 -> 3.1.0
  - Vulnerable shape (removed):
    ```
    var UID                 = Math.floor(Math.random() * 0x10000000000).toString(16);
    var PLACE_HOLDER_REGEXP = new RegExp('"@__(F|R|D|M|S|U|I)-' + UID + '-(\\d+)__@"', 'g');
    ...
    return str.replace(PLACE_HOLDER_REGEXP, function (match, type, valueIndex) {
    ```
  - Guard added (post-patch):
    ```
    var randomBytes = require('randombytes');
    ...
    var UID_LENGTH          = 16;
    var UID                 = generateUID();
    var PLACE_HOLDER_REGEXP = new RegExp('(\\\\)?"@__(F|R|D|M|S|U|I)-' + UID + '-(\\d+)__@"', 'g');
    ...
    function generateUID() {
        var bytes = randomBytes(UID_LENGTH);
        var result = '';
        for(var i=0; i<UID_LENGTH; ++i) {
            result += bytes[i].toString(16);
        }
        return result;
    }
    ...
    return str.replace(PLACE_HOLDER_REGEXP, function (match, backSlash, type, valueIndex) {
        // The placeholder may not be preceded by a backslash. This is to prevent
        // replacing things like `"a\\"@__R-<UID>-0__@"` and thus outputting
        // invalid JS.
        if (backSlash) {
            return match;
        }
    ```
  - Reachability: module.exports = function serialize(obj, options) in index.js -> final str.replace(PLACE_HOLDER_REGEXP, ...) placeholder-substitution pass, reached by any caller that serializes an object containing attacker-influenced string values and whose output is later run through eval() by the consuming app (serialize-javascript's documented use case for embedding JS/config in server-rendered pages).
  - Verdict: IN — Diff re-fetched this session and matches verbatim; GHSA-hxcc-f52p-wc94 tags CWE-502 ('Insecure serialization leading to RCE', CVSS 8.1 High); the fix is a cleanly isolable two-part guard (crypto-random placeholder UID + backslash-precedence check) directly on the placeholder-substitution path that produces the eval()'d output.
  - Source: https://api.osv.dev/v1/vulns/GHSA-hxcc-f52p-wc94 ; https://github.com/advisories/GHSA-hxcc-f52p-wc94 ; https://github.com/yahoo/serialize-javascript/commit/f21a6fb3ace2353413761e79717b2d210ba6ccbd ; https://nvd.nist.gov/vuln/detail/CVE-2020-7660  ·  provenance: re-verified-this-session

- **CVE-2026-48517 (GHSA-qhmf-xw27-6rqr)** — CWE-502 · `MessagePack-CSharp/MessagePack-CSharp` · fixed 2.5.301 / 3.1.7 @ `f093bdc1207f6576088d39801fa43e92cec1e5c1` · **IN** (signature) · deser-type-filter (denylist check on the resolved type made recursive over array element types and constructed-generic type arguments, not just the outer type name)
  - Mechanism: MessagePackSerializerOptions.ThrowIfDeserializingTypeIsDisallowed(Type) is the documented security mitigation for the Typeless formatter: it is supposed to block instantiation of dangerous/gadget types during untrusted-payload deserialization. The default implementation only checked the exact outer type's FullName against a denylist (DisallowedTypes), with no recursion into array element types or generic type arguments. An attacker able to supply a typeless MessagePack (ext-100) payload could wrap a denylisted type inside an array (MyObject[]) or a generic container (List<MyObject>) -- the wrapper type passes the outer-type check, but the Typeless formatter machinery still materializes and instantiates the disallowed inner type, defeating the blocklist and reaching whatever gadget the inner type provides.
  - Affected -> Fixed: NuGet MessagePack [0.0,2.5.301) and [3.0,3.1.7) -> 2.5.301 / 3.1.7
  - Vulnerable shape (removed):
    ```
    public virtual void ThrowIfDeserializingTypeIsDisallowed(Type type)
    {
        if (type.FullName is string fullName && DisallowedTypes.Contains(fullName))
        {
            throw new MessagePackSerializationException($"Deserialization attempted to create the type {fullName} which is not allowed.");
        }
    }
    ```
  - Guard added (post-patch):
    ```
    public virtual void ThrowIfDeserializingTypeIsDisallowed(Type type)
    {
        this.ThrowIfDeserializingTypeIsDisallowedCore(type);
    
        if (type.HasElementType && type.GetElementType() is Type elementType)
        {
            this.ThrowIfDeserializingTypeIsDisallowed(elementType);
        }
    
        if (type.IsConstructedGenericType)
        {
            foreach (Type genericTypeArgument in type.GenericTypeArguments)
            {
                this.ThrowIfDeserializingTypeIsDisallowed(genericTypeArgument);
            }
        }
    }
    ...
    protected virtual void ThrowIfDeserializingTypeIsDisallowedCore(Type type)
    {
        if (type.FullName is string fullName && DisallowedTypes.Contains(fullName))
        {
            throw new MessagePackSerializationException($"Deserialization attempted to create the type {fullName} which is not allowed.");
        }
    }
    ```
  - Reachability: MessagePackSerializerOptions.ThrowIfDeserializingTypeIsDisallowed(Type) <- TypelessFormatter's per-value type resolution during MessagePackSerializer.Typeless.Deserialize()/ConvertToJson(), reached by any caller deserializing an untrusted MessagePack payload through the Typeless resolver whose ext-100-typed value names an array or generic wrapper around a disallowed inner type.
  - Verdict: IN — Diff re-fetched this session and matches verbatim; GHSA-qhmf-xw27-6rqr tags CWE-502 (with CWE-470) and the added regression test literally carries [Trait("CWE", "502")]; the guard is a single isolable change making the Typeless denylist recurse into array-element and constructed-generic-argument types instead of checking only the outer type name.
  - Source: https://api.osv.dev/v1/vulns/GHSA-qhmf-xw27-6rqr ; https://github.com/advisories/GHSA-qhmf-xw27-6rqr ; https://github.com/MessagePack-CSharp/MessagePack-CSharp/security/advisories/GHSA-qhmf-xw27-6rqr ; https://github.com/MessagePack-CSharp/MessagePack-CSharp/commit/f093bdc1207f6576088d39801fa43e92cec1e5c1 ; https://nvd.nist.gov/vuln/detail/CVE-2026-48517  ·  provenance: re-verified-this-session

- **CVE-2025-32434 (GHSA-53q9-r3pm-6pq6)** — CWE-502 · `pytorch/pytorch` · fixed 2.6.0 @ `8d4b8a920a2172523deb95bf20e8e52d50649c04` · **IN** (signature) · unsafe-fallback-path denial (reject a legacy code path that silently used the full/unrestricted unpickler instead of honoring the caller's requested restricted _weights_only_unpickler, rather than adding a type-filter)
  - Mechanism: torch.load(..., weights_only=True) is documented and relied on as PyTorch's safe-deserialization mode: it routes unpickling through a restricted allowlisting _weights_only_unpickler instead of Python's full pickle. However, the legacy .tar-checkpoint-format branch inside persistent_load() in torch/serialization.py unconditionally opened the archive's embedded 'storages' member and called the plain, unrestricted pickle_module.load() on it regardless of which unpickler had been selected -- so a checkpoint file saved in the old .tar container format silently bypassed the weights_only allowlist entirely, letting a crafted legacy-format file reach full unpickling of attacker-controlled objects and achieve RCE even when the caller explicitly requested weights_only=True.
  - Affected -> Fixed: PyPI torch < 2.6.0 -> 2.6.0
  - Vulnerable shape (removed):
    ```
    (guard-add-only fix: no security-relevant lines removed at the vulnerable call; the pre-existing unrestricted unpickle site is left intact and the guard is inserted immediately before it)
    tar.extract("storages", path=tmpdir)
    with open(os.path.join(tmpdir, "storages"), "rb", 0) as f:
        num_storages = pickle_module.load(f, **pickle_load_args)
    ```
  - Guard added (post-patch):
    ```
    if pickle_module is _weights_only_unpickler:
        raise RuntimeError(
            "Cannot use ``weights_only=True`` with files saved in the "
            "legacy .tar format. " + UNSAFE_MESSAGE
        )
    ```
  - Reachability: torch.load(f, weights_only=True) -> internal load() -> legacy-.tar-format branch of the persistent_load() closure in torch/serialization.py, reached by any caller loading an untrusted checkpoint file saved in PyTorch's old .tar container format.
  - Verdict: IN — Diff re-fetched this session and matches verbatim; GHSA-53q9-r3pm-6pq6 tags CWE-502 (Critical); the guard is a clean, isolable 5-line insertion that refuses the legacy .tar unpickle path when the restricted _weights_only_unpickler is in effect, closing the weights_only=True bypass -- the bundled UNSAFE_MESSAGE relocation is a non-security refactor that does not entangle the guard.
  - Source: https://api.osv.dev/v1/vulns/GHSA-53q9-r3pm-6pq6 ; https://github.com/advisories/GHSA-53q9-r3pm-6pq6 ; https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6 ; https://github.com/pytorch/pytorch/commit/8d4b8a920a2172523deb95bf20e8e52d50649c04 ; https://nvd.nist.gov/vuln/detail/CVE-2025-32434  ·  provenance: re-verified-this-session

## Cross-site scripting (reflected / stored / DOM)  (CWE-79)

Grounds cards: skills/vulns/cross-site-scripting
Bucket verdict: **THIN — 6 clean IN + 1 CONTESTED (Grav, squashed multi-GHSA release bundle, non-promotable) across 6 distinct products (better-auth, Talishar, NocoDB, Statamic, json-markup/Jaeger UI, Roundcube); 6 promotable signatures. Sits exactly at the 6-anchor floor with zero margin: it would clear a bare literal >=6-clean reading, but is held to THIN because the 7th is CONTESTED and the corpus convention for other buckets is 6-clean-PLUS-margin. Dominant guard shape: escape-before-sink — HTML-entity-encode the attacker value immediately before it is interpolated/concatenated into HTML (better-auth sanitize(), Statamic escapeHtml()/highlightResult(), json-markup escape(key), Grav SafeRender escape()). Secondary shapes: param-binding + exact-match allowlist (Talishar intval + {1,2}), denylist->safe-API sanitizer (NocoDB DOMPurify.sanitize), and canonicalization-before-denylist-match (Roundcube trim() before attribute-name compare). Reflected vs stored share the guard vocabulary; the split is where the guard sits (pre-render vs pre-store), not its shape. Dominant thinness driver: OSV 'fixed' SHAs resolving to version-bump/release-tag commits (GLPI, Open eClass) or advisories with no resolvable commit at all (NukeViet, PrestaShop), symptomatic of CMS/PHP projects batching security fixes into version-tagged releases rather than isolable single-purpose commits.**  ·  6 IN / 1 CONTESTED / 6 dropped  ·  6 promotable signatures
Severity-corpus join: Joins the severity-precedent-corpus CWE-79 Reflected XSS (PR:N/UI:R, ~5.1-6.9 Medium) and Stored XSS (PR:L-H/UI:R, 4.4-9.3, higher when the stored payload targets an admin/privileged viewer) buckets; three anchor ids are shared join keys (GHSA-9x4v-xfq5-m8x5/better-auth, CVE-2022-2022/NocoDB, GHSA-65mj-f7p4-wggq/Grav) linking a code-delta prior here to a CVSS-vector prior there — better-auth/Grav sit at the low-friction reflected end, NocoDB/Statamic/Roundcube at the authenticated-poster-stores-for-higher-privilege-viewer stored end (Statamic explicitly stored-XSS->privesc).

- **GHSA-9x4v-xfq5-m8x5** — CWE-79 · `better-auth/better-auth` · fixed 1.1.16 @ `7ae340e2eddad641b7e43d24d37c58a66ce9ddcf` · **IN** (signature) · escape
  - Mechanism: Reflected XSS: /api/auth/error endpoint interpolated the unsanitized `error` URL query parameter (as errorCode) directly into the HTML error page.
  - Affected -> Fixed: 0.0.2 - 1.1.16 -> 1.1.16
  - Vulnerable shape (removed):
    ```
            <div class="error-code">Error Code: <span id="errorCode">${errorCode}</span></div>
    ```
  - Guard added (post-patch):
    ```
    function sanitize(input: string): string {
    	return input
    		.replace(/&/g, "&amp;")
    		.replace(/</g, "&lt;")
    		.replace(/>/g, "&gt;")
    		.replace(/"/g, "&quot;")
    		.replace(/'/g, "&#39;");
    }
    ...
            <div class="error-code">Error Code: <span id="errorCode">${sanitize(
    					errorCode,
    				)}</span></div>
    ```
  - Reachability: packages/better-auth/src/api/routes/error.ts html(), reached via unauthenticated GET /api/auth/error?error=<payload>, requires victim click (UI:A)
  - Verdict: IN — Re-fetched the .diff this session: single file, single interpolation site, removed->added delta matches verbatim. Clean isolable HTML-entity escape (sanitize()) at the one sink; no entanglement. Reflected URL-param-into-HTML matches CWE-79.
  - Source: https://github.com/advisories/GHSA-9x4v-xfq5-m8x5 ; https://api.osv.dev/v1/vulns/GHSA-9x4v-xfq5-m8x5 ; https://github.com/better-auth/better-auth/commit/7ae340e2eddad641b7e43d24d37c58a66ce9ddcf.diff  ·  provenance: re-verified-this-session

- **CVE-2026-25144 / GHSA-rrr4-h2pc-57g6 (GHSA-rrr4-h2pc-57g6)** — CWE-79 · `Talishar/Talishar` · fixed unversioned web app, commit-pinned @ `09dd00e5452e3cd998eb1406a88e5b0fa868e6b4` · **IN** (signature) · param-binding + exact-match allowlist
  - Mechanism: Stored XSS: SubmitChat.php took the playerID GET parameter verbatim, used and rendered it in a <span> on the shared game page for every viewer, with no type/bound check.
  - Affected -> Fixed: all versions prior to fix commit -> unversioned web app, commit-pinned
  - Vulnerable shape (removed):
    ```
    $playerID = $_GET["playerID"];
    ```
  - Guard added (post-patch):
    ```
    $playerID = intval($_GET["playerID"]);
    if($playerID !== 1 && $playerID !== 2) {
      echo ("Invalid player ID.");
      exit;
    }
    ```
  - Reachability: SubmitChat.php top-level script, reached via any request supplying an arbitrary playerID; stored per-game and rendered for every participant viewing the game page
  - Verdict: IN — Re-fetched the .diff this session: single file, delta matches verbatim. Clean isolable param-binding (intval) + tiny exact-match allowlist (only 1/2 valid slots) inserted at point of use before store/render. Stored XSS matches CWE-79.
  - Source: https://github.com/Talishar/Talishar/security/advisories/GHSA-rrr4-h2pc-57g6 ; https://api.osv.dev/v1/vulns/CVE-2026-25144 ; https://github.com/Talishar/Talishar/commit/09dd00e5452e3cd998eb1406a88e5b0fa868e6b4.diff  ·  provenance: re-verified-this-session

- **CVE-2022-2022** — CWE-79 · `nocodb/nocodb` · fixed 0.91.7 @ `ffad5a318ad60d1da1c75dd28152827b94c92e9d` · **IN** (signature) · denylist->safe-API (DOMPurify sanitize)
  - Mechanism: Stored XSS: project-creation API stored the user-supplied project title/slug with a `// todo: sanitize` marker and no sanitization, rendered later in the project UI for every viewer.
  - Affected -> Fixed: < 0.91.7 -> 0.91.7
  - Vulnerable shape (removed):
    ```
    // todo: sanitize
    projectBody.slug = projectBody.title;
    ```
  - Guard added (post-patch):
    ```
    import DOMPurify from 'isomorphic-dompurify';
    ...
      projectBody.title = DOMPurify.sanitize(projectBody.title);
      projectBody.slug = projectBody.title;
    ```
  - Reachability: packages/nocodb/src/lib/meta/api/projectApis.ts projectCreate(), reached via authenticated POST project-creation request with HTML/JS in title; stored and rendered for every viewer of the project list/dashboard
  - Verdict: IN — Re-fetched the .diff this session (3 files: projectApis.ts + package.json + lockfile for the DOMPurify dep-add). Guard is a single clean DOMPurify.sanitize(projectBody.title) at the assignment site; only `// todo: sanitize` was actually removed (the projectBody.slug line in removed_lines is unchanged context) and unrelated projectCost() reformatting is cosmetic churn, not entangled with the guard. Isolable escape-via-sanitizer, matches CWE-79.
  - Source: https://nvd.nist.gov/vuln/detail/CVE-2022-2022 ; https://huntr.dev/bounties/f6082949-40d3-411c-b613-23ada2691913 ; https://api.osv.dev/v1/vulns/CVE-2022-2022 ; https://github.com/nocodb/nocodb/commit/ffad5a318ad60d1da1c75dd28152827b94c92e9d.diff  ·  provenance: re-verified-this-session

- **GHSA-ff9r-ww9c-43x8 (CVE-2026-25759) (GHSA-ff9r-ww9c-43x8)** — CWE-79 · `statamic/cms` · fixed 6.2.3 @ `6ed4f65f3387686d6dbd816e9b4f18a8d9736ff6` · **IN** (signature) · escape
  - Mechanism: Stored XSS -> privilege escalation: admin Command Palette built highlighted search-result HTML by calling fuzzysort's .highlight() directly on raw, unescaped content titles; a content-creator's malicious title executes in a higher-privileged searcher's session.
  - Affected -> Fixed: 6.0.0 - 6.2.2 -> 6.2.3
  - Vulnerable shape (removed):
    ```
        let filtered = fuzzysort
            .go(query.value, filterableItems, {
                keys: ['text'],
                scoreFn: fuzzysortScoringAlgorithm,
            })
            .map(result => {
                return {
                    score: result._score,
                    html: result[0].highlight(`<span class="${highlightClasses}">`, '</span>'),
                    ...result.obj,
                };
            });
    ```
  - Guard added (post-patch):
    ```
    import { escapeHtml } from '@/bootstrap/globals.js';
    ...
    function highlightResult(text) {
        const classes = 'text-blue-600 dark:text-blue-400 underline underline-offset-4 decoration-blue-200 dark:decoration-blue-600/45';
        const safeText = escapeHtml(text);
        const result = fuzzysort.single(query.value, safeText);
        return result?.highlight(`<span class="${classes}">`, '</span>') || safeText;
    }
    ...
        let filtered = fuzzysort
            .go(query.value, filterableItems, {
                keys: ['text'],
                scoreFn: fuzzysortScoringAlgorithm,
            })
            .map(result => ({
                score: result._score,
                html: highlightResult(result.obj.text),
                ...result.obj,
            }));
    ```
  - Reachability: resources/js/components/command-palette/CommandPalette.vue, reached whenever any CP user's search query matches an attacker-titled, attacker-created entity
  - Verdict: IN — Re-fetched the .diff this session: single file. escapeHtml()/highlightResult() wrapper replaces the inline .highlight() call and is applied uniformly to both the fuzzy-match and content-search result paths. The surrounding arrow-fn DRY simplification is the vehicle for the same escape guard, which is isolable to the XSS fix. Content-creator payload executing for a higher-privileged searcher matches CWE-79.
  - Source: https://github.com/statamic/cms/security/advisories/GHSA-ff9r-ww9c-43x8 ; https://api.osv.dev/v1/vulns/GHSA-ff9r-ww9c-43x8 ; https://github.com/statamic/cms/commit/6ed4f65f3387686d6dbd816e9b4f18a8d9736ff6.diff  ·  provenance: re-verified-this-session

- **CVE-2023-36656** — CWE-79 · `mafintosh/json-markup (Jaeger UI dependency)` · fixed json-markup 1.1.4 (consumed by jaeger-ui 1.31.0) @ `e7fb4df7de6a7d57f2249f0527dda8b5498ad36b` · **IN** (signature) · escape
  - Mechanism: Stored XSS: json-markup's key-rendering closure (used by Jaeger UI's KeyValuesTable via dangerouslySetInnerHTML) string-concatenated the raw JSON object key into a <span> with no escaping; an attacker-controlled trace tag key executes when any user views the trace.
  - Affected -> Fixed: json-markup < 1.1.4 (jaeger-ui < 1.31.0) -> json-markup 1.1.4 (consumed by jaeger-ui 1.31.0)
  - Vulnerable shape (removed):
    ```
    return forEach(keys, '{', '}', function (key) {
      return '<span ' + style('json-markup-key') + '>"' + key + '":</span> ' + visit(obj[key])
    })
    ```
  - Guard added (post-patch):
    ```
    return forEach(keys, '{', '}', function (key) {
      return '<span ' + style('json-markup-key') + '>"' + escape(key) + '":</span> ' + visit(obj[key])
    })
    ```
  - Reachability: mafintosh/json-markup index.js key-rendering closure, reached transitively via packages/jaeger-ui's KeyValuesTable component whenever a trace with attacker-influenced tag/process keys is opened
  - Verdict: IN — Re-fetched the PR #15 merge .diff (e7fb4df) this session: single file (index.js), a single-line escape(key) wrap, fully isolated, matches verbatim. Fix lives in the dependency's own repo (jaeger-ui's own commit is only a lockfile/version bump). NVD primary record is CWE-79; the jaeger-ui GHSA tags CWE-80 (a child-of-79 basic-XSS sibling, a cross-authority CWE label difference, not a fix-diff disagreement). Unescaped-key-into-HTML stored XSS matches CWE-79.
  - Source: https://api.osv.dev/v1/vulns/CVE-2023-36656 ; https://github.com/jaegertracing/jaeger-ui/pull/1498 ; https://github.com/mafintosh/json-markup/pull/15.diff  ·  provenance: re-verified-this-session

- **CVE-2024-37383 / GHSA-8j3w-26mp-75xh (GHSA-8j3w-26mp-75xh)** — CWE-79 · `roundcube/roundcubemail` · fixed 1.5.7 / 1.6.7 @ `43aaaa528646877789ec028d87924ba1accf5242` · **IN** (signature) · canonicalization-before-denylist-match
  - Mechanism: XSS via HTML-sanitizer bypass: rcube_washtml's denylist match against SVG <animate> attributeName='href' used an untrimmed comparison, so a trailing space in the attacker-supplied attribute name slipped a javascript: URI past the sanitizer.
  - Affected -> Fixed: < 1.5.7 (and 1.6.x < 1.6.7) -> 1.5.7 / 1.6.7
  - Vulnerable shape (removed):
    ```
            foreach ($node->attributes as $name => $attr) {
                if (strtolower($name) === $attr_name) {
                    if (strtolower($attr_value) === strtolower($attr->nodeValue)) {
                        return true;
                    }
                }
    ```
  - Guard added (post-patch):
    ```
            foreach ($node->attributes as $name => $attr) {
                if (strtolower($name) === $attr_name) {
                    if (strtolower($attr_value) === strtolower(trim($attr->nodeValue))) {
                        return true;
                    }
                }
    ```
  - Reachability: program/lib/Roundcube/rcube_washtml.php attribute_value(), reached via HTML message sanitizer's SVG handling when a victim previews/opens a crafted HTML email containing <svg><animate attributeName="href " .../></svg>
  - Verdict: IN — Re-fetched the .diff this session (3 files: rcube_washtml.php + CHANGELOG + regression test tests/Framework/Washtml.php). Guard is a single trim() insertion at the exact comparison site closing a whitespace-based denylist bypass; changelog + test are expected companions, not entanglement. Sanitizer-bypass XSS in a webmail client matches CWE-79.
  - Source: https://github.com/advisories/GHSA-8j3w-26mp-75xh ; https://nvd.nist.gov/vuln/detail/CVE-2024-37383 ; https://api.osv.dev/v1/vulns/CVE-2024-37383 ; https://github.com/roundcube/roundcubemail/commit/43aaaa528646877789ec028d87924ba1accf5242.diff  ·  provenance: re-verified-this-session

- **CVE-2025-66309 / GHSA-65mj-f7p4-wggq (GHSA-65mj-f7p4-wggq)** — CWE-79 · `getgrav/grav (fix in grav-plugin-admin submodule)` · fixed 1.8.0-beta.27 @ `99f653296504f1d6408510dd2f6f20a45a26f9b0` · **CONTESTED** (illustrative) · escape
  - Mechanism: Reflected XSS: Selectize-backed admin multi-select fields (e.g. Blog post data[header][content][items]) rendered option/item text via a custom render function that interpolated raw text into HTML with no escaping.
  - Affected -> Fixed: < 1.8.0-beta.27 -> 1.8.0-beta.27
  - Vulnerable shape (removed):
    ```
    (no lines removed for this GHSA specifically; guard inserted as new default render functions ahead of the existing custom-render call site)
    ```
  - Guard added (post-patch):
    ```
    // Security: Default render functions that escape HTML to prevent XSS
    // (GHSA-65mj-f7p4-wggq, GHSA-7g78-5g5g-mvfj, GHSA-mpjj-4688-3fxg)
    const SafeRender = {
        option: function(item, escape) {
            return `<div>${escape(item.text || item.value)}</div>`;
        },
        item: function(item, escape) {
            return `<div>${escape(item.text || item.value)}</div>`;
        }
    };
    ...
            if (!data.render) {
                data = $.extend({}, data, { render: SafeRender });
            }
    ```
  - Reachability: themes/grav/app/forms/fields/selectize.js SelectizeField, reached via any admin panel Selectize field with no custom render (advisory names Blog post data[header][content][items]); requires authenticated attacker (PR:H) and victim admin interaction (UI:A)
  - Verdict: CONTESTED — Re-fetched the .diff this session: touches 6 files, and the SafeRender comment explicitly names three GHSAs (GHSA-65mj-f7p4-wggq, GHSA-7g78-5g5g-mvfj, GHSA-mpjj-4688-3fxg) with sibling twig hunks naming still more (GHSA-rmw5-f87r-w988, GHSA-gqxx-248x-g29f) — a squashed multi-CVE release bundle. The selectize.js escape-before-render hunk itself is clean and attributable via the maintainers' own comment, but the commit as a whole is not a single-GHSA-isolable fix. Genuine + correct CWE, so downgraded (not dropped) per keep-bias; kept illustrative, promote_signature=false.
  - Source: https://github.com/advisories/GHSA-65mj-f7p4-wggq ; https://api.osv.dev/v1/vulns/GHSA-65mj-f7p4-wggq ; https://github.com/getgrav/grav-plugin-admin/commit/99f653296504f1d6408510dd2f6f20a45a26f9b0.diff  ·  provenance: re-verified-this-session

Dropped: CVE-2026-42321 / GHSA-hwjc-8228-55x4 (GLPI, stored XSS in asset locks) (OSV GIT-range 'fixed' SHA (d91722c60d7552ae96c79774793bf45d78eb9771) resolves to a one-line GLPI_VERSION string bump (10.0.25-dev -> 10.0.25), a release-tag commit not the code fix; no isolable single fix commit found via search this session. Unverifiable hunk -> OUT/dropped rather than fabricate from the version-bump commit.); CVE-2026-24674 / GHSA-gqvp-w22w-w99r (Open eClass, reflected XSS across multiple endpoints) (Same failure mode as GLPI: OSV GIT 'fixed' SHA (6a98ba9fb5ce499b53d2cd0708f3080d92632dfa) is only an ECLASS_VERSION string bump (4.2-dev -> 4.2), not a code diff; no isolable single fix commit found. Dropped.); CVE-2025-48489 (FreeScout, stored XSS in mailbox name field) (Fix commit (9879e29c2054e842143620f40bac0eabf44c8054) is real and fetchable but is a large 18-file security-hardening release (mass-assignment field-allowlisting across 6+ controllers, session/config hardening) with the XSS fix entangled inside a broader $request->all() -> explicit-$allowed_fields refactor; no single isolable escape/sanitize hunk extractable as a clean CWE-79-only guard. Over-entangled -> dropped rather than force-fit.); GHSA-465g-4q99-5x86 (NukeViet, multiple anti-XSS filter bypasses, News module) (Advisory prose names the exact fix location (filterAttr()/unhtmlentities() in vendor/vinades/nukeviet/Core/Request.php) but supplies no GIT range and no resolvable commit SHA (only a placeholder + a version-only reference to 4.6.00); no fetchable diff resolvable this session.); GHSA-w9f3-qc75-qgx9 (PrestaShop stored XSS, Customer Service view) and CVE-2026-33673 (PrestaShop back-office template-variable stored XSS) (Both advisories carry only ECOSYSTEM/Packagist version ranges (fixed 8.2.6/9.1.1 and unspecified), no GIT range and no FIX-type reference; no single commit SHA resolvable. Dropped for lack of a fetchable fix commit rather than guessed from the version tag.); nocodb 0a4219c0b059faef79a9738462f039edda1f15ec (companion 'fixed' SHA on the same CVE-2022-2022 GIT range) (This SHA is package.json/package-lock.json lockfile version bumps only across 4 packages, no code change; the real code fix is the sibling SHA ffad5a318ad60d1da1c75dd28152827b94c92e9d used as the anchor. Recorded so the dropped SHA isn't mistaken for a second independent anchor.)

## CSRF  (CWE-352)

Grounds cards: (no dedicated card; corpus completeness + severity-corpus join)
Bucket verdict: **THIN — 5 clean IN + 1 CONTESTED (Symfony DI-ordering outlier), below the >=6-clean threshold. Dominant guard shape is force-the-request-non-simple hardening (HTTP-method restriction and/or Content-Type/CORS-preflight enforcement) in 3/6 (new-api, TYPO3, Sunshine), with explicit CSRF-token binding — custom-header double-submit (goshs) and state-cookie double-submit (fastapi-users) — in 2/6; the Symfony DI-ordering fix is the atypical non-promotable outlier.**  ·  5 IN / 1 CONTESTED / 5 dropped  ·  5 promotable signatures
Severity-corpus join: Joins the severity-precedent-corpus CWE-352 (CSRF) bucket: canonical vector AV:N/AC:L/PR:N/UI:R, integrity-led, with blast radius setting severity — goshs (file delete/mkdir) sits low-to-mid (~4-6), while forced account-linking/takeover (new-api, fastapi-users) and the Sunshine CSRF->command-exec chain (S:C) push the high end (~8-9), consistent with the corpus CSRF median that is dominated by the mandatory UI:R.

- **GHSA-26v7-h57m-gh9m** — CWE-352 · `QuantumNous/new-api` · fixed 0.12.0-alpha.1 @ `e099117c61391abdf888fb75e382a582e550bd0e` · **IN** (signature) · HTTP-method restriction + query-string-to-JSON-body migration (GET->POST removes the trivial cross-site-forgeable link/image vector; state-changing params moved out of the URL into a JSON body that a simple cross-origin form cannot forge without triggering CORS preflight)
  - Mechanism: OAuth account-binding endpoints (/api/oauth/email/bind, /api/oauth/wechat/bind) were exposed as HTTP GET routes taking email/verification-code as query-string parameters. A cross-site GET (e.g. an <img>/<script> tag or simple navigation from an attacker page) executed with the victim's session cookies would bind an attacker-chosen email or WeChat account to the victim's account, enabling downstream account-recovery/takeover abuse. Default SameSite=Strict cookies partially mitigate but do not eliminate the exposure (e.g. top-level navigation, same-site subdomains, or relaxed cookie config).
  - Affected -> Fixed: < 0.12.0-alpha.1 -> 0.12.0-alpha.1
  - Vulnerable shape (removed):
    ```
    apiRouter.GET("/oauth/email/bind", middleware.CriticalRateLimit(), controller.EmailBind)
    ...
    apiRouter.GET("/oauth/wechat/bind", middleware.CriticalRateLimit(), controller.WeChatBind)
    // and in controller/user.go: email := c.Query("email"); code := c.Query("code")
    // and in controller/wechat.go: code := c.Query("code")
    ```
  - Guard added (post-patch):
    ```
    apiRouter.POST("/oauth/email/bind", middleware.CriticalRateLimit(), controller.EmailBind)
    ...
    apiRouter.POST("/oauth/wechat/bind", middleware.CriticalRateLimit(), controller.WeChatBind)
    // controller/user.go: type emailBindRequest struct{ Email,Code string `json:...` }; var req emailBindRequest; common.DecodeJson(c.Request.Body, &req)
    // controller/wechat.go: type wechatBindRequest struct{ Code string `json:"code"` }; var req wechatBindRequest; common.DecodeJson(c.Request.Body, &req)
    ```
  - Reachability: router/api-router.go SetApiRouter() -> POST /oauth/email/bind -> controller.EmailBind(); POST /oauth/wechat/bind -> controller.WeChatBind(). Entrypoint: attacker-controlled page loaded by an authenticated victim browser.
  - Verdict: IN — Re-fetched this session: the security hunks (GET->POST on both bind routes plus query->JSON-body param migration in api-router.go/user.go/wechat.go/PersonalSetting.jsx) are a clean, cleanly-isolable CSRF guard matching CWE-352; the only bundled churn (_qn debug-field removal and a SendPasswordResetEmail refactor) is confined to a separate file (controller/misc.go) and does not touch the guard, so it stays IN.
  - Source: https://api.osv.dev/v1/vulns/GHSA-26v7-h57m-gh9m ; https://github.com/advisories/GHSA-26v7-h57m-gh9m ; https://github.com/QuantumNous/new-api/commit/e099117c61391abdf888fb75e382a582e550bd0e ; https://github.com/QuantumNous/new-api/commit/e099117c61391abdf888fb75e382a582e550bd0e.diff  ·  provenance: re-verified-this-session

- **GHSA-jrq5-hg6x-j6g3** — CWE-352 · `patrickhener/goshs` · fixed 2.0.0-beta.6 @ `e3c3d37dc9a08eddd3cd0d7cea4a3f0a49e2b521` · **IN** (signature) · server-side CSRF token check (double-submit style: random per-instance token embedded in the served HTML, required back as a custom header on mutating requests — custom headers cannot be set by simple cross-site forms/img tags)
  - Mechanism: goshs's state-changing operations (?delete, ?mkdir on file-listing GET routes, and the file-upload POST) were authenticated only via HTTP Basic Auth, which browsers transparently replay on any request to the origin (including from <img src=...> tags). With no CSRF token check, an attacker page embedding <img src="http://victim-host:port/path?delete"> or an auto-submitting upload form could delete files/create directories or upload files as the authenticated victim.
  - Affected -> Fixed: 2.0.0-beta.4 - 2.0.0-beta.5 -> 2.0.0-beta.6
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard function inserted before the mkdir/delete/upload sinks) — previously: fetch(url) [no CSRF header] in assets/js/main.js for deleteFile/createDir; xhr.open("POST", ...) with no X-CSRF-Token header for startUpload; and handler.go's mkdir/delete branches and updown.go's upload() called directly with no CSRF check.
    ```
  - Guard added (post-patch):
    ```
    func (fs *FileServer) checkCSRF(w http.ResponseWriter, req *http.Request) bool {
      if fs.User == "" { return true }
      if req.Header.Get("X-CSRF-Token") != fs.CSRFToken {
        http.Error(w, "Forbidden", http.StatusForbidden)
        return false
      }
      return true
    }
    // call sites added: if !fs.checkCSRF(w, req) { return true } before handleMkdir/deleteFile in httpserver/handler.go, and if !fs.checkCSRF(w, req) { return } at top of upload() in httpserver/updown.go. Token generated via generateCSRFToken() (crypto/rand, 32 bytes hex) in server.go, embedded in <meta name="csrf-token"> in index.html, and read/sent as X-CSRF-Token header from assets/js/main.js.
    ```
  - Reachability: httpserver/handler.go earlyBreakParameters() mkdir/delete branches; httpserver/updown.go upload(). Entrypoint: any HTTP client reaching the goshs file-server UI while Basic Auth is configured (fs.User != "").
  - Verdict: IN — Re-fetched this session and confirmed a clean additive CSRF-token guard: crypto/rand 32-byte token in server.go, embedded via <meta name=csrf-token>, required back as X-CSRF-Token and checked in checkCSRF() before the mkdir/delete/upload sinks, with no unrelated refactoring — textbook custom-header double-submit matching CWE-352.
  - Source: https://api.osv.dev/v1/vulns/GHSA-jrq5-hg6x-j6g3 ; https://github.com/patrickhener/goshs/security/advisories/GHSA-jrq5-hg6x-j6g3 ; https://api.github.com/repos/patrickhener/goshs/compare/v2.0.0-beta.5...v2.0.0-beta.6 ; https://github.com/patrickhener/goshs/commit/e3c3d37dc9a08eddd3cd0d7cea4a3f0a49e2b521.diff  ·  provenance: re-verified-this-session

- **GHSA-vvmr-8829-6whx** — CWE-352 · `symfony/symfony` · fixed 5.3.15 / 5.4.4 / 6.0.4 (multi-branch backport) @ `f0ffb775febdf07e57117aabadac96fa37857f50` · **CONTESTED** (illustrative) · dependency-ordering fix (moved form/validation/messenger/notifier/profiler service registration to run strictly after CSRF-protection service registration, so the CSRF token manager is guaranteed present when the Form component wires its CSRF form-type extension)
  - Mechanism: In FrameworkExtension::load(), the Form component's configuration/services (which wire the CSRF form-type extension onto every generated form) were registered before registerSecurityCsrfConfiguration() ran. Under specific container-building orderings this left forms rendered/processed without CSRF protection actually enabled by default, silently disabling CSRF checks for Symfony forms across affected point releases (5.3.14-15, 5.4.3-4, 6.0.3-4) until the ordering bug was fixed.
  - Affected -> Fixed: 5.3.14-5.3.15 (fixed 5.3.15); 5.4.3-5.4.4 (fixed 5.4.4); 6.0.3-6.0.4 (fixed 6.0.4) -> 5.3.15 / 5.4.4 / 6.0.4 (multi-branch backport)
  - Vulnerable shape (removed):
    ```
    // original ordering in FrameworkExtension::load():
    if ($this->isConfigEnabled($container, $config['form'])) { ... $this->registerFormConfiguration($config, $container, $loader); ... }
    // (placed BEFORE) $this->registerSecurityCsrfConfiguration($config['csrf_protection'], $container, $loader);
    $this->registerValidationConfiguration($config['validation'], $container, $loader, $propertyInfoEnabled);
    if ($this->messengerConfigEnabled = ...) { $this->registerMessengerConfiguration(...); } ...
    if ($this->notifierConfigEnabled = ...) { $this->registerNotifierConfiguration(...); }
    ... $this->registerProfilerConfiguration($config['profiler'], $container, $loader); (also moved)
    ```
  - Guard added (post-patch):
    ```
    $this->registerSecurityCsrfConfiguration($config['csrf_protection'], $container, $loader);
    
    // form depends on csrf being registered
    if ($this->isConfigEnabled($container, $config['form'])) { ... $this->registerFormConfiguration($config, $container, $loader); ... }
    // validation depends on form, annotations being registered
    $this->registerValidationConfiguration($config['validation'], $container, $loader, $propertyInfoEnabled);
    // messenger depends on validation being registered
    if ($this->messengerConfigEnabled = ...) { $this->registerMessengerConfiguration(...); } ...
    // notifier depends on messenger, mailer being registered
    if ($this->notifierConfigEnabled = ...) { $this->registerNotifierConfiguration(...); }
    // profiler depends on form, validation, translation, messenger, mailer, http-client, notifier being registered
    $this->registerProfilerConfiguration($config['profiler'], $container, $loader);
    ```
  - Reachability: src/Symfony/Bundle/FrameworkBundle/DependencyInjection/FrameworkExtension.php::load() (container-compilation time). Entrypoint: any Symfony Form rendered and POSTed by an application using symfony/framework-bundle with forms enabled.
  - Verdict: CONTESTED — Re-fetched this session and confirmed a genuine CWE-352 fix, but it is a pure DI-reordering (registerSecurityCsrfConfiguration moved ahead of form registration) with the CSRF-relevant move interleaved with relocating form/validation/messenger/notifier/profiler blocks plus added comments — no discrete, cleanly-isolable sink-guard hunk, so keep-biased downgrade to CONTESTED rather than promote as a guard signature.
  - Source: https://api.osv.dev/v1/vulns/GHSA-vvmr-8829-6whx ; https://symfony.com/cve-2022-23601 ; https://github.com/symfony/symfony/commit/f0ffb775febdf07e57117aabadac96fa37857f50 ; https://github.com/symfony/symfony/commit/f0ffb775febdf07e57117aabadac96fa37857f50.diff  ·  provenance: re-verified-this-session

- **GHSA-ww7h-g2qf-7xv6** — CWE-352 (primary); CWE-749 exposed-dangerous-method (secondary, per NVD/advisory) · `TYPO3-CMS/form` · fixed 10.4.48 / 11.5.42 / 12.4.25 / 13.4.3 @ `93327743f5dfd31c44898ce16e3e004e05f8ba5f` · **IN** (signature) · HTTP-method enforcement (assertAllowedHttpMethod(...,'POST') added to every state-changing action's initialize*Action(), rejecting GET-triggered deep-link invocation; deleteAction's frontend trigger was also converted from a plain navigation/redirect to an async POST)
  - Mechanism: TYPO3 backend Form module actions (create/duplicate/delete form definitions, save a form) were reachable via ordinary GET requests / deep links with no enforced HTTP method restriction. When security.backend.enforceReferrer is disabled or the BE session cookie's SameSite is lax/none, a crafted link visited by a logged-in backend admin (deep link, e.g. in a phishing email or malicious page) could trigger the state-changing action using the admin's active backend session.
  - Affected -> Fixed: 10.0.0-10.4.47 (fixed 10.4.48); 11.0.0-11.5.41 (fixed 11.5.42); 12.0.0-12.4.24 (fixed 12.4.25); 13.0.0-13.4.2 (fixed 13.4.3) -> 10.4.48 / 11.5.42 / 12.4.25 / 13.4.3
  - Vulnerable shape (removed):
    ```
    protected function initializeSaveFormAction(): void {
        $this->defaultViewObjectName = JsonView::class;
    }
    // (FormEditorController — no method assertion)
    protected function initializeCreateAction(): void {
        $this->defaultViewObjectName = JsonView::class;
    }
    protected function initializeDuplicateAction(): void {
        $this->defaultViewObjectName = JsonView::class;
    }
    // deleteAction had no initializeDeleteAction() at all and ended with: return $this->redirect('index');
    ```
  - Guard added (post-patch):
    ```
    use TYPO3\CMS\Core\Http\AllowedMethodsTrait;
    class FormEditorController extends ActionController { use AllowedMethodsTrait; ... }
    protected function initializeSaveFormAction(): void {
        $this->assertAllowedHttpMethod($this->request, 'POST');
        $this->defaultViewObjectName = JsonView::class;
    }
    // FormManagerController:
    use TYPO3\CMS\Core\Http\AllowedMethodsTrait;
    class FormManagerController extends ActionController { use AllowedMethodsTrait; ... }
    protected function initializeCreateAction(): void { $this->assertAllowedHttpMethod($this->request, 'POST'); ... }
    protected function initializeDuplicateAction(): void { $this->assertAllowedHttpMethod($this->request, 'POST'); ... }
    protected function initializeDeleteAction(): void {
        $this->assertAllowedHttpMethod($this->request, 'POST');
        $this->defaultViewObjectName = JsonView::class;
    }
    ```
  - Reachability: Classes/Controller/FormManagerController.php (createAction, duplicateAction, deleteAction) and Classes/Controller/FormEditorController.php (saveFormAction), TYPO3 backend 'form' extension module. Entrypoint: a TYPO3 backend admin with an active session clicking/loading a crafted deep link.
  - Verdict: IN — Re-fetched this session and confirmed clean additive HTTP-method guards: AllowedMethodsTrait plus assertAllowedHttpMethod($this->request,'POST') added to initializeSaveFormAction/Create/Duplicate/Delete, rejecting GET deep-link invocation with no unrelated refactoring; CWE-352 is the primary label (CWE-749 secondary) and the guard is cleanly isolable.
  - Source: https://api.osv.dev/v1/vulns/GHSA-ww7h-g2qf-7xv6 ; https://typo3.org/security/advisory/typo3-core-sa-2025-007 ; https://nvd.nist.gov/vuln/detail/CVE-2024-55922 ; https://github.com/TYPO3-CMS/form/commit/93327743f5dfd31c44898ce16e3e004e05f8ba5f.diff  ·  provenance: re-verified-this-session

- **GHSA-5j53-63w8-8625** — CWE-352 (also tagged CWE-285 improper authorization by the advisory) · `fastapi-users/fastapi-users` · fixed 15.0.2 @ `7cf413cd766b9cb0ab323ce424ddab2c0d235932` · **IN** (signature) · double-submit CSRF cookie binding (a random token is embedded both in the signed OAuth state JWT and in a fresh httponly/secure/samesite cookie set on /authorize; the callback requires the cookie value to match the state's embedded token via constant-time compare before honoring the OAuth result, binding the flow to the initiating browser)
  - Mechanism: The OAuth/SSO authorize+callback flow encoded only an audience-scoped JWT 'state' parameter with no binding to the initiating browser session. An attacker could start their own OAuth flow to obtain a valid state+authorization-code pair, then get a victim to visit the crafted callback URL; the callback would complete login/account-association using the attacker-controlled OAuth identity inside the victim's browser session — a 1-click CSRF leading to account takeover / forced account linking.
  - Affected -> Fixed: < 15.0.2 -> 15.0.2
  - Vulnerable shape (removed):
    ```
    async def authorize(request: Request, scopes: list[str] = Query(None)) -> OAuth2AuthorizeResponse:
        ...
        state_data: dict[str, str] = {}
        state = generate_state_token(state_data, state_secret)
        ...
        return OAuth2AuthorizeResponse(authorization_url=authorization_url)
    # callback():
    token, state = access_token_state
    account_id, account_email = await oauth_client.get_id_email(token["access_token"])
    if account_email is None: raise HTTPException(...)
    try:
        decode_jwt(state, state_secret, [STATE_TOKEN_AUDIENCE])
    except jwt.DecodeError: raise HTTPException(...)
    # (no CSRF-cookie comparison at all before proceeding to oauth_callback)
    ```
  - Guard added (post-patch):
    ```
    CSRF_TOKEN_KEY = "csrftoken"
    CSRF_TOKEN_COOKIE_NAME = "fastapiusersoauthcsrf"
    def generate_csrf_token() -> str:
        return secrets.token_urlsafe(32)
    
    async def authorize(request: Request, response: Response, scopes: list[str] = Query(None), ...):
        csrf_token = generate_csrf_token()
        state_data: dict[str, str] = {CSRF_TOKEN_KEY: csrf_token}
        state = generate_state_token(state_data, state_secret)
        ...
        response.set_cookie(csrf_token_cookie_name, csrf_token, max_age=3600, path=..., domain=..., secure=csrf_token_cookie_secure, httponly=csrf_token_cookie_httponly, samesite=csrf_token_cookie_samesite)
        return OAuth2AuthorizeResponse(authorization_url=authorization_url)
    # callback():
    state_data = decode_jwt(state, state_secret, [STATE_TOKEN_AUDIENCE])
    cookie_csrf_token = request.cookies.get(csrf_token_cookie_name)
    state_csrf_token = state_data.get(CSRF_TOKEN_KEY)
    if not cookie_csrf_token or not state_csrf_token or not secrets.compare_digest(cookie_csrf_token, state_csrf_token):
        raise HTTPException(status_code=400, detail=ErrorCode.OAUTH_INVALID_STATE)
    account_id, account_email = await oauth_client.get_id_email(token["access_token"])
    # (account_email/get_id_email check moved to AFTER the CSRF check)
    ```
  - Reachability: fastapi_users/router/oauth.py: get_oauth_router().authorize/callback and get_oauth_associate_router().authorize/callback (GET /{provider}/authorize, GET /{provider}/callback). Entrypoint: victim visiting an attacker-supplied SSO callback URL/link while unauthenticated or authenticated.
  - Verdict: IN — Re-fetched this session and confirmed a clean additive double-submit CSRF-cookie binding: generate_csrf_token() token placed in both the state JWT and a set_cookie on /authorize, then a secrets.compare_digest cookie-vs-state check raising OAUTH_INVALID_STATE before get_id_email in the callback; implementation-only diff (docs/tests aside), CWE-352 apt for OAuth-state CSRF despite the secondary CWE-285 tag.
  - Source: https://api.osv.dev/v1/vulns/GHSA-5j53-63w8-8625 ; https://github.com/advisories/GHSA-5j53-63w8-8625 ; https://github.com/fastapi-users/fastapi-users/commit/7cf413cd766b9cb0ab323ce424ddab2c0d235932 ; https://github.com/fastapi-users/fastapi-users/commit/7cf413cd766b9cb0ab323ce424ddab2c0d235932.diff  ·  provenance: re-verified-this-session

- **GHSA-39hj-fxvw-758m** — CWE-352 · `LizardByte/Sunshine` · fixed 2025.628.4510 @ `738ac93a0ec1cd10412d1f339968775f53bfefe0` · **IN** (signature) · Content-Type enforcement as an implicit CSRF guard (requiring application/json forces any cross-origin forgery attempt to be a 'not simple' request per the Fetch/CORS spec, which triggers a CORS preflight that the attacker's origin cannot pass without the server's cooperation; plain HTML forms cannot set this content type at all)
  - Mechanism: Sunshine's local web admin REST API (save/delete app, save config, save password/PIN, unpair, restart, upload cover, etc.) authenticated requests only via HTTP Basic Auth (browser-cached, auto-replayed) and performed no CSRF-token or Content-Type validation. A malicious page could auto-submit a simple cross-origin HTML form (application/x-www-form-urlencoded, no preflight) to these endpoints while an admin's browser held cached Basic Auth credentials, forging admin actions — including saveApp, whose 'cmd' field is later executed, so the CSRF chained into command injection as Administrator.
  - Affected -> Fixed: <= 2025.122.141614 -> 2025.628.4510
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard call inserted as the first statement of each mutating handler) — previously e.g.:
    void saveApp(resp_https_t response, req_https_t request) {
        if (!authenticate(response, request)) { return; }
        ...
    }
    (same pattern for closeApp, deleteApp, unpair, unpairAll, saveConfig, uploadCover, savePassword, savePin, resetDisplayDevicePersistence, restart — no content-type check anywhere before authenticate())
    ```
  - Guard added (post-patch):
    ```
    bool check_content_type(resp_https_t response, req_https_t request, const std::string_view &contentType) {
      auto requestContentType = request->header.find("content-type");
      if (requestContentType == request->header.end()) { bad_request(response, request, "Content type not provided"); return false; }
      std::string actualContentType = requestContentType->second;
      size_t semicolonPos = actualContentType.find(';');
      if (semicolonPos != std::string::npos) actualContentType = actualContentType.substr(0, semicolonPos);
      boost::algorithm::trim(actualContentType);
      boost::algorithm::to_lower(actualContentType);
      std::string expectedContentType(contentType);
      boost::algorithm::to_lower(expectedContentType);
      if (actualContentType != expectedContentType) { bad_request(response, request, "Content type mismatch"); return false; }
      return true;
    }
    // each handler gains, before authenticate():
    void saveApp(resp_https_t response, req_https_t request) {
        if (!check_content_type(response, request, "application/json")) { return; }
        if (!authenticate(response, request)) { return; }
        ...
    }
    (identical guard added to closeApp, deleteApp, unpair, unpairAll, saveConfig, uploadCover, savePassword, savePin, resetDisplayDevicePersistence, restart)
    ```
  - Reachability: src/confighttp.cpp: saveApp, closeApp, deleteApp, unpair, unpairAll, saveConfig, uploadCover, savePassword, savePin, resetDisplayDevicePersistence, restart — all mounted as POST/DELETE routes on the local admin web UI. Entrypoint: any page loaded in the browser of a user with a live Basic-Auth session to the Sunshine admin UI (localhost or LAN-exposed).
  - Verdict: IN — Re-fetched this session and confirmed a clean additive check_content_type() (require application/json) inserted before authenticate() across all eleven mutating handlers in confighttp.cpp, forcing a non-simple request/CORS preflight to defeat cross-origin form forgery; guard is cleanly isolable, CWE-352 correct, and the saveApp->cmd exec path makes impact high.
  - Source: https://github.com/LizardByte/Sunshine/security/advisories/GHSA-39hj-fxvw-758m ; https://github.com/LizardByte/Sunshine/commit/738ac93a0ec1cd10412d1f339968775f53bfefe0 ; https://github.com/LizardByte/Sunshine/commit/738ac93a0ec1cd10412d1f339968775f53bfefe0.diff  ·  provenance: re-verified-this-session

Dropped: GHSA-xvfj-w962-hqcx (Ampache, CVE-2024-51485) (Advisory (and osv.dev, which 404s for this id) provides no commit SHA or PR link — only 'affected 7.0.0, fixed 7.0.1' with a blog post + PoC video, neither containing patch details. No fetchable single fix commit; would require diffing the entire 7.0.0->7.0.1 tag range which risks bundling unrelated changes. Dropped per hard rule (no fabricated hunks).); GHSA-26rv-8wpp-q84r (GetSimple CMS, CVE-2026-27146) (Advisory explicitly states 'Patched versions: None' — no fix has shipped at all as of discovery. There is no fix commit to resolve or diff.); GHSA-3jw2-5hjg-hc2c (Jenkins Extensible Choice Parameter Plugin, CVE-2025-64133) (osv.dev record has no GIT-type ranges and no FIX-type references; Jenkins advisory itself states 'No fix' as of publication. No commit to anchor to.); GHSA-3qjh-r982-mhgp (CVE-2025-32250) (404 on api.osv.dev/v1/vulns — record not present/not indexed with GIT ranges; surfaced only via keyword web search with no accessible source repo or fix commit found. Not pursued further to avoid fabricating an anchor.); GHSA-gcw3-8xrx-4mpm (CVE-2024-0392) (404 on api.osv.dev/v1/vulns — same as above, no GIT-based fix data resolvable without further discovery; dropped rather than guessed.)

## Open redirect  (CWE-601)

Grounds cards: (no dedicated card; boundary cross-ref for ssrf-server-side-fetch + severity join)
Bucket verdict: **THIN - 5 clean IN anchors (peering-manager, espocrm, directus, gradio, traccar), below the 6-clean threshold for IN; the 6th (freescout) is a genuine but entangled CWE-601 fix demoted to CONTESTED. Dominant guard shape: allow-list validation of the redirect destination against a configured/registered origin (site URL / PUBLIC_URL / registered redirect-URI set), with two recurring secondary shapes - scheme/host stripping (rebuild from path only) and explicit protocol-relative //host rejection.**  ·  5 IN / 1 CONTESTED / 8 dropped  ·  5 promotable signatures
Severity-corpus join: Joins the CWE-601 open-redirect severity bucket: the reset-email / return_url phishing variants (espocrm, peering-manager) sit at the classic CVSS 3.1 ~4.7-6.1 credential-phishing band (AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N), while the OAuth/SSO redirect-and-code-theft variants (directus, gradio, traccar) reach the upper end since a stolen authorization code/token pushes confidentiality toward High.

- **CVE-2024-28113 (GHSA-f4mf-5g28-q7f5)** — CWE-601 · `peering-manager/peering-manager` · fixed 1.8.3 @ `b74da036b1fba50b4fe8e8e47bca2bb5799c7ee2` · **IN** (signature) · relative-URL allow-check: reject any absolute netloc AND reject more than one leading slash (blocks the //host and ////host protocol-relative bypass)
  - Mechanism: GetReturnURLMixin.get_return_url() accepted a return_url GET/POST param and only checked `not urlparse(return_url).netloc` to decide it was 'relative' - a protocol-relative value like //evil.com or one with multiple leading slashes (////evil.com) passes this check (empty netloc) yet is treated as an absolute redirect by browsers, sending an authenticated user to an attacker-controlled site after a form action.
  - Affected -> Fixed: <=1.8.2 -> 1.8.3
  - Vulnerable shape (removed):
    ```
            if return_url and not bool(urlparse(return_url).netloc):
    ```
  - Guard added (post-patch):
    ```
        @staticmethod
        def is_relative_url(url):
            is_absolute = bool(urlparse(url).netloc)
            count_leading_slash = len(url) - len(url.lstrip("/"))
            return url and not is_absolute and count_leading_slash <= 1
    
            if return_url and self.is_relative_url(return_url):
    ```
  - Reachability: GetReturnURLMixin.get_return_url() in utils/views.py - consumed by generic object edit/delete views across the app that honor a return_url GET/POST parameter after a form submission; unauthenticated attacker crafts the link, authenticated victim clicks it.
  - Verdict: IN — Re-fetched diff confirms the removed one-line netloc check and the added is_relative_url() static method verbatim; discrete isolable guard, CWE-601 protocol-relative bypass is the exact mechanism, single commit, re-fetchable.
  - Source: https://github.com/peering-manager/peering-manager/security/advisories/GHSA-f4mf-5g28-q7f5 ; https://github.com/peering-manager/peering-manager/commit/b74da036b1fba50b4fe8e8e47bca2bb5799c7ee2.diff  ·  provenance: re-verified-this-session

- **CVE-2024-24818 (GHSA-8gv6-8r33-fm7j)** — CWE-601 · `espocrm/espocrm` · fixed 8.1.2 @ `3babdfa3399e328fb1bd83a1b4ed03d509f4c8e7` · **IN** (signature) · allow-list prefix validation against the configured site URL and every registered Portal URL, throwing Forbidden on mismatch
  - Mechanism: The 'Forgot password' flow (POST /api/v1/User/passwordChangeRequest) accepted an attacker-controlled `url` parameter with no validation and embedded it verbatim as the login link in the password-reset email; after the victim resets their password and clicks that link, they are redirected to an attacker-controlled domain, enabling credential-phishing via a cloned login page.
  - Affected -> Fixed: <=8.1.1 -> 8.1.2
  - Vulnerable shape (removed):
    ```
    (no guard lines removed; fix is a pure insertion - new UrlValidator class + constructor injection + a validate() call before the recovery email is built)
    ```
  - Guard added (post-patch):
    ```
            if ($url) {
                $this->urlValidator->validate($url);
            }
    
    // new file application/Espo/Tools/UserSecurity/Password/Recovery/UrlValidator.php, validate():
        public function validate(string $url): void
        {
            $siteUrl = rtrim($this->config->get('siteUrl') ?? '', '/');
    
            if (str_starts_with($url, $siteUrl)) {
                return;
            }
    
            /** @var iterable<Portal> $portals */
            $portals = $this->entityManager
                ->getRDBRepositoryByClass(Portal::class)
                ->find();
    
            foreach ($portals as $portal) {
                $siteUrl = rtrim($portal->getUrl() ?? '', '/');
    
                if (str_starts_with($url, $siteUrl)) {
                    return;
                }
            }
    
            throw new Forbidden("URL does not match Site URL.");
        }
    ```
  - Reachability: RecoveryService::request() in application/Espo/Tools/UserSecurity/Password/RecoveryService.php - public POST /api/v1/User/passwordChangeRequest endpoint's optional `url` parameter, later reflected in the password-reset confirmation email's login link.
  - Verdict: IN — Re-fetched diff confirms the fix is a clean insertion: a new UrlValidator class (validate() body verbatim-matched) plus one gated call site; discrete allow-list guard, CWE-601 match, single commit, re-fetchable.
  - Source: https://github.com/espocrm/espocrm/security/advisories/GHSA-8gv6-8r33-fm7j ; https://github.com/espocrm/espocrm/commit/3babdfa3399e328fb1bd83a1b4ed03d509f4c8e7.diff  ·  provenance: re-verified-this-session

- **CVE-2024-28239 (GHSA-fr3w-2p22-6w7p)** — CWE-601 · `directus/directus` · fixed 10.10.0 @ `5477d7d61babd7ffc2f835d399bf79611b15b203` · **IN** (signature) · allow-list validation (env-configured AUTH_<PROVIDER>_REDIRECT_ALLOW_LIST plus PUBLIC_URL origin-equality match, and explicit rejection of protocol-relative //host paths), applied identically to the OAuth2, OpenID, and SAML drivers before the redirect value is trusted
  - Mechanism: The OAuth2/OpenID/SAML SSO login-initiation routes read an unvalidated `redirect` query parameter and embedded it directly into a signed JWT state cookie (or SAML RelayState) without checking it against any allow list; after the SSO provider completed authentication, the app followed that attacker-supplied value, redirecting the authenticated user to an arbitrary external phishing site.
  - Affected -> Fixed: <10.10.0 -> 10.10.0
  - Vulnerable shape (removed):
    ```
    			const token = jwt.sign(
    				{ verifier: codeVerifier, redirect: req.query['redirect'], prompt },
    				env['SECRET'] as string,
    				{
    					expiresIn: '5m',
    					issuer: 'directus',
    				},
    			);
    ```
  - Guard added (post-patch):
    ```
    			const redirect = req.query['redirect'];
    
    			if (isLoginRedirectAllowed(redirect, providerName) === false) {
    				throw new InvalidPayloadError({ reason: `URL "${redirect}" can't be used to redirect after login` });
    			}
    
    			const token = jwt.sign({ verifier: codeVerifier, redirect, prompt }, env['SECRET'] as string, {
    				expiresIn: '5m',
    				issuer: 'directus',
    			});
    
    // new core guard api/src/utils/is-login-redirect-allowed.ts (verbatim-confirmed against raw file at fix sha):
    export function isLoginRedirectAllowed(redirect: unknown, provider: string): boolean {
    	if (!redirect) return true; // empty redirect
    	if (typeof redirect !== 'string') return false; // invalid type
    
    	const env = useEnv();
    	const publicUrl = env['PUBLIC_URL'] as string;
    
    	if (URL.canParse(redirect) === false) {
    		if (redirect.startsWith('//') === false) {
    			// should be a relative path like `/admin/test`
    			return true;
    		}
    
    		// domain without protocol `//example.com/test`
    		return false;
    	}
    
    	const { protocol: redirectProtocol, hostname: redirectDomain } = new URL(redirect);
    
    	const envKey = `AUTH_${provider.toUpperCase()}_REDIRECT_ALLOW_LIST`;
    
    	if (envKey in env) {
    		if (isUrlAllowed(redirect, [...toArray(env[envKey] as string), publicUrl])) return true;
    	}
    
    	if (URL.canParse(publicUrl) === false) {
    		return false;
    	}
    
    	// allow redirects to the defined PUBLIC_URL
    	const { protocol: publicProtocol, hostname: publicDomain } = new URL(publicUrl);
    
    	return `${redirectProtocol}//${redirectDomain}` === `${publicProtocol}//${publicDomain}`;
    }
    ```
  - Reachability: createOAuth2AuthRouter()/createOpenIDAuthRouter() GET SSO-login routes in api/src/auth/drivers/{oauth2,openid}.ts and createSAMLAuthRouter() in saml.ts - all reading the unauthenticated `redirect` query parameter on the public SSO login-initiation endpoint.
  - Verdict: IN — Guard body verbatim-confirmed against the raw is-login-redirect-allowed.ts at the fix sha; advisory lists CWE-601 as sole weakness. Change spans 3 driver files + a helper tweak (is-url-allowed.ts) but the guard is one clean, well-named isolable function applied consistently - repetition, not entanglement. Single commit, re-fetchable.
  - Source: https://github.com/directus/directus/security/advisories/GHSA-fr3w-2p22-6w7p ; https://github.com/directus/directus/commit/5477d7d61babd7ffc2f835d399bf79611b15b203.diff ; https://raw.githubusercontent.com/directus/directus/5477d7d61babd7ffc2f835d399bf79611b15b203/api/src/utils/is-login-redirect-allowed.ts  ·  provenance: re-verified-this-session

- **CVE-2026-28415 (GHSA-pfjf-5gxr-995x)** — CWE-601 · `gradio-app/gradio` · fixed 6.6.0 @ `dfee0da06d0aa94b3c2684131e7898d5d5c1911e` · **IN** (signature) · scheme/host stripping - the redirect target is rebuilt from only the path, query, and fragment components, discarding any attacker-supplied scheme/host
  - Mechanism: The OAuth post-login redirect helper `_redirect_to_target()` read `_target_url` from the query string and passed it straight into `RedirectResponse(target)` with no validation, letting a crafted `?_target_url=https://evil.com/...` or protocol-relative `//evil.com/...` link redirect a victim off the trusted hf.space domain to an attacker-controlled phishing site after completing HF OAuth login.
  - Affected -> Fixed: <6.6.0 -> 6.6.0
  - Vulnerable shape (removed):
    ```
        return RedirectResponse(target)
    ```
  - Guard added (post-patch):
    ```
        # Prevent open redirect by stripping scheme/host and only using the path.
        parsed = urllib.parse.urlparse(target)
        safe_target = parsed.path or "/"
        if parsed.query:
            safe_target += "?" + parsed.query
        if parsed.fragment:
            safe_target += "#" + parsed.fragment
        return RedirectResponse(safe_target)
    ```
  - Reachability: _redirect_to_target() in gradio/oauth.py - OAuth post-login redirect handler reading the `_target_url` query parameter on the HF Spaces OAuth callback route.
  - Verdict: IN — Re-fetched diff confirms only `return RedirectResponse(target)` was removed (the target= line is unchanged context; collector's removed_lines corrected) and the scheme/host-stripping block added verbatim; single-file, single-function, discrete guard, CWE-601 match, re-fetchable.
  - Source: https://github.com/gradio-app/gradio/security/advisories/GHSA-pfjf-5gxr-995x ; https://github.com/gradio-app/gradio/commit/dfee0da06d0aa94b3c2684131e7898d5d5c1911e.diff  ·  provenance: re-verified-this-session

- **CVE-2026-25649 (GHSA-ccc7-4r59-4pp7)** — CWE-601 · `traccar/traccar` · fixed 6.12.0 @ `d8ad466347455d326777a90973f15204dbe1bdda` · **IN** (signature) · registered-redirect-URI equality check against a per-client allow-set (config format extended from 'clientId:clientSecret' to 'clientId:clientSecret:redirectUri[|redirectUri...]') before the authorization code is issued and redirected
  - Mechanism: The built-in OIDC provider's /api/oidc/authorize endpoint validated only that `client_id` was a known configured client; the `redirect_uri` query parameter itself was never checked against anything and was used verbatim as the destination the freshly-issued OAuth authorization code was redirected to, letting an authenticated attacker steal authorization codes (and, by exchanging them, access tokens) by pointing redirect_uri at an attacker-controlled host.
  - Affected -> Fixed: <=6.11.1 -> 6.12.0
  - Vulnerable shape (removed):
    ```
            if (!getClients().containsKey(clientId)) {
                throw new WebApplicationException(Response.Status.UNAUTHORIZED);
            }
    
            URI target = URI.create(redirectUri);
            String code = sessionManager.issueCode(
                    getUserId(), clientId, target, scope, nonce, codeChallenge, codeChallengeMethod);
    ```
  - Guard added (post-patch):
    ```
            ClientConfig client = getClients().get(clientId);
            if (client == null) {
                throw new WebApplicationException(Response.Status.UNAUTHORIZED);
            }
    
            URI target = URI.create(redirectUri);
            if (!client.redirectUris().contains(target)) {
                throw new WebApplicationException(Response.Status.BAD_REQUEST);
            }
    
            String code = sessionManager.issueCode(
                    getUserId(), clientId, target, scope, nonce, codeChallenge, codeChallengeMethod);
    ```
  - Reachability: OidcResource.authorize() in src/main/java/org/traccar/api/resource/OidcResource.java - authenticated-session GET /api/oidc/authorize?client_id=&redirect_uri=&... endpoint that issues the OAuth 2.0 authorization code and 303-redirects it to redirect_uri.
  - Verdict: IN — Re-fetched diff confirms the added `if (!client.redirectUris().contains(target)) throw BAD_REQUEST` guard verbatim; the ClientConfig record + getClients() type change are supporting scaffolding to hold the allow-set (normal for an allow-list guard), the guard itself is clean and isolable. Single commit, CWE-601 match, re-fetchable.
  - Source: https://github.com/traccar/traccar/security/advisories/GHSA-ccc7-4r59-4pp7 ; https://github.com/traccar/traccar/commit/d8ad466347455d326777a90973f15204dbe1bdda.diff  ·  provenance: re-verified-this-session

- **CVE-2026-34442 (GHSA-822g-7rw5-53xj)** — CWE-601 · `freescout-help-desk/freescout` · fixed 1.8.211 @ `2810916a88595f462979e6030d3e9638de3b527a` · **CONTESTED** (illustrative) · explicit Host-header allow-list comparison (APP_URL host, then APP_TRUSTED_HOSTS list, then a plugin filter hook) replacing the old regex/Symfony-trusted-hosts fallback; an unmatched Host now hits Request::setTrustedHosts([$app_host]) which rejects it
  - Mechanism: TrustHosts middleware compared the incoming Host header against APP_URL, but on mismatch fell back to a permissive subdomain-regex trusted-host list (allSubdomainsOfAppUrl -> '^(.+\.)?<host>$'), and when nothing was configured effectively left Symfony's trusted-host restriction unset. An attacker-supplied Host header therefore propagated into every absolute URL the app generated (redirect Location headers, nav links, /conversation/ajax-html/default_redirect), producing open redirects and external resource loading to attacker infrastructure.
  - Affected -> Fixed: <1.8.211 -> 1.8.211
  - Vulnerable shape (removed):
    ```
        public function handle(Request $request, $next)
        {
            if ($this->shouldSpecifyTrustedHosts()) {
                Request::setTrustedHosts(array_filter($this->hosts()));
            }
    
            return $next($request);
        }
    
        protected function allSubdomainsOfAppUrl()
        {
            if ($host = parse_url($this->app['config']->get('app.url'), PHP_URL_HOST)) {
                return '^(.+\.)?'.preg_quote($host).'$';
            }
        }
    
    // NOTE: re-fetched diff shows the removal is much larger than the two methods above -
    // the whole middleware was rewritten: static property `protected static $subdomains;`
    // plus methods hosts(), at(), shouldSpecifyTrustedHosts(), allSubdomainsOfAppUrl(),
    // and flushState() were all deleted.
    ```
  - Guard added (post-patch):
    ```
        public function handle(Request $request, $next)
        {
            if (//! $this->app->environment('local') &&
                $this->app->runningUnitTests()
            ) {
                return $next($request);
            }
    
            // Check if current host matches APP_URL.
            list($current_host) = explode(':', request()->getHttpHost());
            $current_host = mb_strtolower($current_host);
    
            $app_host = mb_strtolower(\Helper::getDomain());
    
            if ($current_host == $app_host) {
                return $next($request);
            }
    
            // Check hosts from APP_TRUSTED_HOSTS.
            $trusted_hosts = explode(',', config('app.trusted_hosts'));
            foreach ($trusted_hosts as $host) {
                $host = mb_strtolower(trim($host));
                if ($host && $current_host == $host) {
                    return $next($request);
                }
            }
    
            $is_trusted_host = \Eventy::filter('app.is_trusted_host', false, $current_host);
    
            if ($is_trusted_host) {
                return $next($request);
            }
    
            // Throw: Untrusted Host...
            Request::setTrustedHosts([$app_host]);
    
            return $next($request);
        }
    ```
  - Reachability: TrustHosts middleware (app/Http/Middleware/TrustHosts.php) - global HTTP middleware executed on every request; the attacker-controlled entrypoint is the raw Host header, consumed wherever the app builds absolute URLs for redirects/links/assets.
  - Verdict: CONTESTED — Genuine CWE-601 (Host-header-injection open redirect), single commit, re-fetchable - but NOT a discrete isolable redirect guard: the re-fetched diff shows the entire TrustHosts middleware was rewritten (static property $subdomains + five methods hosts()/at()/shouldSpecifyTrustedHosts()/allSubdomainsOfAppUrl()/flushState() deleted and handle() fully replaced), so the collector's two-method removed_lines materially under-represents the removed hunk. Keep-biased downgrade to CONTESTED rather than OUT: real fix, entangled rewrite.
  - Source: https://github.com/freescout-help-desk/freescout/security/advisories/GHSA-822g-7rw5-53xj ; https://github.com/freescout-help-desk/freescout/commit/2810916a88595f462979e6030d3e9638de3b527a.diff  ·  provenance: re-verified-this-session

Dropped: CVE-2023-50345 (HCL DRYiCE MyXalytics is a proprietary vendor product with no public repository; no fetchable fix commit.); CVE-2023-3771 (T1 WordPress theme is distributed via the WordPress.org SVN repository, not a git history with a discrete fix commit; NVD record cites no CNA patch diff.); CVE-2024-22308 (Simple Membership WordPress plugin - same SVN-hosted-plugin situation as CVE-2023-3771; no git fix commit to verify verbatim.); CVE-2023-6389 (WordPress Toolbar plugin - SVN-hosted, no git fix commit available.); CVE-2024-31135 (JetBrains TeamCity is closed-source; no public repository or fix commit to fetch.); CVE-2026-2813 (Esri ArcGIS Server is proprietary; no public repository or fix commit to fetch.); CVE-2020-36845 (KnowBe4 Security Awareness Training is a proprietary SaaS product; no public repository or fix commit to fetch.); CVE-2026-63094 (SigNoz SSO ref-parameter redirect - the CNA's own primary-record CWE tag is CWE-345 (Insufficient Verification of Data Authenticity); CWE-601 appears only as NVD's secondary tag, so it fails the bucket's class-match-by-primary-CWE rule despite the open-redirect-shaped mechanism (consistent with the existing corpus's own annotation on this CVE).)

## HTTP request smuggling  (CWE-444)

Grounds cards: skills/vulns/http-protocol-abuse
Bucket verdict: **IN -- 8 clean IN anchors across 7 distinct products (Netty, Puma, Envoy x2, Jetty, Eventlet, Apache bRPC, HAProxy) clears the >=6-clean-anchor bar, closing the ghsa-fix-diff-oracle coverage-honesty "not yet mined" flag for CWE-444. Dominant guard shape is bimodal: (1) fail-closed input-validation gate at the parser boundary rejecting conflicting/malformed headers -- HAProxy empty-name (x3 parsers h1/hpack/qpack), bRPC dual TE+CL, Puma empty Content-Length, Netty 0x1c-0x1f control-char names, Envoy 27493 outbound illegal-byte allowlist char-table; (2) parser-completeness / state-machine fixes for chunked-encoding and upgrade edge cases -- Jetty quoted chunk-extension CRLF state tracking, Eventlet + Puma arbitrary trailer-section discard, Envoy 23326 101-only upgrade-confirmation gate.**  ·  8 IN / 1 CONTESTED / 2 dropped  ·  8 promotable signatures
Severity-corpus join: Joins the severity-precedent oracle's "HTTP request smuggling (CWE-444)" bucket (severity-precedent-oracle.md line 306): modal 3.1 vector AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N = 7.5 (HIGH); Confidentiality is CONTESTED by demonstrated readback (C:H for request/response capture -- Envoy 27493, Puma 40175, Envoy 23326, Jetty 2332; C:N for control-bypass-only -- bRPC 23452, ATS 53868, HAProxy 25725, Netty 43797), with A:H edge cases (Puma 40175 -> 9.8, HAProxy 25725 -> 9.1); 4.0 side thin.

- **CVE-2021-43797 (GHSA-wx5j-54mm-rqqq)** — CWE-444 · `netty/netty` · fixed ? @ `07aa6b5938a8b6ed7a6586e066400e2643897323` · **IN** (signature) · denylist (control-char 0x1c-0x1f block) + mandatory-OWS canonicalization on the header-name side
  - Mechanism: HttpObjectDecoder.splitHeader() only enforced OWS-only whitespace on the value side of a header line (findNonWhitespace's validateOWS flag was false for the name side), and DefaultHttpHeaders.validateHeaderNameElement() did not reject the control-character range 0x1c-0x1f in header names. A proxy in front of another HTTP parser could forward header names containing these control characters; a downstream parser with different tolerance interpreted the header boundary differently, enabling request smuggling.
  - Affected -> Fixed: netty-codec-http < 4.1.71.Final (fixed 4.1.71.Final) -> ?
  - Vulnerable shape (removed):
    ```
    nameStart = findNonWhitespace(sb, 0, false);
    ...
    valueStart = findNonWhitespace(sb, colonEnd, true);
    ...
    private static int findNonWhitespace(AppendableCharSequence sb, int offset, boolean validateOWS) {
        for (int result = offset; result < sb.length(); ++result) {
            char c = sb.charAtUnsafe(result);
            if (!Character.isWhitespace(c)) {
                return result;
            } else if (validateOWS && !isOWS(c)) {
    // (validateHeaderNameElement switch, byte and char variants, before the 0x00 case:)
    case 0x00:
    case '\t':
    case '\n':
    ```
  - Guard added (post-patch):
    ```
    nameStart = findNonWhitespace(sb, 0);
    ...
    valueStart = findNonWhitespace(sb, colonEnd);
    ...
    private static int findNonWhitespace(AppendableCharSequence sb, int offset) {
        for (int result = offset; result < sb.length(); ++result) {
            char c = sb.charAtUnsafe(result);
            if (!Character.isWhitespace(c)) {
                return result;
            } else if (!isOWS(c)) {
    // (validateHeaderNameElement switch, byte and char variants, now includes:)
    case 0x1c:
    case 0x1d:
    case 0x1e:
    case 0x1f:
    case 0x00:
    ```
  - Reachability: io.netty.handler.codec.http.HttpObjectDecoder.splitHeader() / io.netty.handler.codec.http.DefaultHttpHeaders.validateHeaderNameElement() (byte + char variants), reached whenever Netty parses any inbound HTTP/1.x header line, whether acting as a server or as a reverse proxy in front of another HTTP implementation
  - Verdict: IN — Re-fetched .diff this session: DefaultHttpHeaders.validateHeaderNameElement (both byte and char switch variants) inserts case 0x1c/0x1d/0x1e/0x1f directly before case 0x00, and HttpObjectDecoder.splitHeader/findNonWhitespace drops the validateOWS bypass so OWS is now mandatory on the name side. Collector hunks match verbatim. Clean two-file isolable parser-boundary guard; textbook CWE-444 control-char header-name desync.
  - Source: https://github.com/netty/netty/security/advisories/GHSA-wx5j-54mm-rqqq ; https://github.com/netty/netty/commit/07aa6b5938a8b6ed7a6586e066400e2643897323.diff  ·  provenance: re-verified-this-session

- **CVE-2023-40175 (GHSA-68xg-gqqm-vgj8)** — CWE-444 · `puma/puma` · fixed ? @ `690155e7d644b80eeef0a6094f9826ee41f1080a` · **IN** (signature) · reject-on-empty-value (Content-Length) + correct arbitrary trailer-section boundary detection
  - Mechanism: Puma's Content-Length validator rejected non-digit characters but allowed an empty string through, and its chunked-body reader assumed exactly one trailing CRLF line after the terminal 0-length chunk instead of locating/skipping an arbitrary trailer section, letting a crafted empty Content-Length or trailer content desync Puma's view of request boundaries from a front-end proxy's.
  - Affected -> Fixed: puma < 5.6.7, 6.0.0 - 6.3.0 (fixed 5.6.7 / 6.3.1) -> ?
  - Vulnerable shape (removed):
    ```
    if CONTENT_LENGTH_VALUE_INVALID.match? cl
      raise HttpParserError, "Invalid Content-Length: #{cl.inspect}"
    end
    ...
    last_crlf_size = "\r\n".bytesize
    if rest.bytesize < last_crlf_size
      @buffer = nil
      @partial_part_left = last_crlf_size - rest.bytesize
      return false
    else
      @buffer = rest[last_crlf_size..-1]
    ```
  - Guard added (post-patch):
    ```
    if CONTENT_LENGTH_VALUE_INVALID.match?(cl) || cl.empty?
      raise HttpParserError, "Invalid Content-Length: #{cl.inspect}"
    end
    ...
    if rest.bytesize < CHUNK_VALID_ENDING_SIZE
      @buffer = nil
      @partial_part_left = CHUNK_VALID_ENDING_SIZE - rest.bytesize
      return false
    else
      start_of_rest = if rest.start_with?(CHUNK_VALID_ENDING)
        CHUNK_VALID_ENDING_SIZE
      else # we have started a trailer section, which we do not support. skip it!
        rest.index(CHUNK_VALID_ENDING*2) + CHUNK_VALID_ENDING_SIZE*2
      end
      @buffer = rest[start_of_rest..-1]
    ```
  - Reachability: lib/puma/client.rb Client#setup_body (Content-Length validation) and Client#decode_chunk (chunked-trailer handling), reached on every inbound HTTP/1.1 request Puma parses
  - Verdict: IN — Re-fetched: Content-Length validator now adds `|| cl.empty?`, and the chunk reader replaces the fixed last_crlf_size assumption with CHUNK_VALID_ENDING boundary detection that skips an arbitrary trailer section. Collector hunks match verbatim. Clean isolable dual-guard (empty-CL reject + trailer-completeness). CWE-444 confirmed.
  - Source: https://github.com/advisories/GHSA-68xg-gqqm-vgj8 ; https://github.com/puma/puma/commit/690155e7d644b80eeef0a6094f9826ee41f1080a.diff  ·  provenance: re-verified-this-session

- **CVE-2023-27493 (GHSA-w5w5-487h-qv8q)** — CWE-444 (NVD) / CWE-20 (CNA) · `envoyproxy/envoy` · fixed ? @ `3a9df1fcdcda98d6615b3d5fa8fbd1867247c7d3` · **IN** (signature) · allowlist char-table validation gate inserted before upstream header serialization (behind envoy.reloadable_features.validate_upstream_headers)
  - Mechanism: Envoy generated upstream request headers directly from downstream request properties (e.g. mTLS cert SAN fields via %DOWNSTREAM_PEER_CERT_V3_SAN% and similar formatters) without validating that resulting header names/values contained only legal token/field-content characters. An attacker controlling one of those properties (e.g. a crafted certificate) could embed CR/LF, causing the upstream to parse the single Envoy-forwarded request as two pipelined requests (proxy-to-upstream desync).
  - Affected -> Fixed: envoy < 1.22.9 / 1.23.6 / 1.24.4 / 1.25.3 / 1.26.0 -> ?
  - Vulnerable shape (removed):
    ```
    (no lines removed; a validation gate is inserted before each existing header-encode sink)
    ```
  - Guard added (post-patch):
    ```
    bool HeaderUtility::headerNameIsValid(const absl::string_view header_key) {
      if (!header_key.empty() && header_key[0] == ':') {
        return nghttp2_check_header_name(...) != 0;
      }
      bool is_valid = true;
      for (auto iter = header_key.begin(); iter != header_key.end() && is_valid; ++iter) {
        is_valid &= testChar(kGenericHeaderNameCharTable, *iter);
      }
      return is_valid;
    }
    ...
    Http::Status HeaderUtility::checkValidRequestHeaders(const Http::RequestHeaderMap& headers) {
      if (!Runtime::runtimeFeatureEnabled("envoy.reloadable_features.validate_upstream_headers")) {
        return Http::okStatus();
      }
      ...
        if (!HeaderUtility::headerNameIsValid(header.key().getStringView())) { ... }
        if (!HeaderUtility::headerValueIsValid(header.value().getStringView())) { ... }
      ...
    }
    // call sites added in http1/codec_impl.cc, http2/codec_impl.cc, quic client/server streams:
    RETURN_IF_ERROR(HeaderUtility::checkValidRequestHeaders(headers));
    ```
  - Reachability: source/common/http/header_utility.cc HeaderUtility::checkValidRequestHeaders(), invoked via RETURN_IF_ERROR from the encodeHeaders path in the HTTP/1, HTTP/2, and QUIC(HTTP/3) upstream codecs -- reached on every upstream request Envoy encodes
  - Verdict: IN — Re-fetched: adds HeaderUtility::headerNameIsValid/headerValueIsValid (kGenericHeaderNameCharTable allowlist) plus checkValidRequestHeaders gate wired via RETURN_IF_ERROR at the HTTP/1, HTTP/2 and QUIC upstream encode sites (grep confirmed 4 call-sites + RUNTIME_GUARD). NVD assigns CWE-444; outbound (proxy->upstream) illegal-byte CRLF desync is request smuggling. Opposite direction from inbound parsing but same mechanism family; clean isolable validation gate. IN.
  - Source: https://github.com/envoyproxy/envoy/security/advisories/GHSA-w5w5-487h-qv8q ; https://github.com/envoyproxy/envoy/commit/3a9df1fcdcda98d6615b3d5fa8fbd1867247c7d3.diff  ·  provenance: re-verified-this-session

- **CVE-2024-23326 (GHSA-vcf8-7238-v74c)** — CWE-444 (NVD) / CWE-391 (CNA) · `envoyproxy/envoy` · fixed ? @ `3f4475b5b824c6b13900fc254da0a8daba769f9f` · **IN** (signature) · fail-closed status-code allowlist (only 101 accepted as upgrade confirmation), gated behind envoy.reloadable_features.check_switch_protocol_websocket_handshake
  - Mechanism: Envoy's upstream codec treated any upgrade-header-bearing response as a successful protocol switch regardless of status code, incorrectly accepting HTTP 200 (RFC 7230 6.7 requires 101 Switching Protocols) as upgrade confirmation for a WebSocket handshake, letting a manipulated/compromised upstream desync Envoy's HTTP/1.1 framing state machine (stops applying framing rules, starts tunneling raw bytes) while the frontend still expects an ordinary response.
  - Affected -> Fixed: envoy < 1.27.6 / 1.28.4 / 1.29.5 / 1.30.2 -> ?
  - Vulnerable shape (removed):
    ```
    (no lines removed; a status-code gate is inserted into the paused-for-upgrade decode path)
    ```
  - Guard added (post-patch):
    ```
    if (filter_.callbacks_->upstreamCallbacks()->pausedForWebsocketUpgrade()) {
        const uint64_t status = Http::Utility::getResponseStatus(*headers);
        const auto protocol = filter_.callbacks_->upstreamCallbacks()->upstreamStreamInfo().protocol();
        if (status == static_cast<uint64_t>(Http::Code::SwitchingProtocols) ||
            (protocol.has_value() && protocol.value() != Envoy::Http::Protocol::Http11)) {
          filter_.callbacks_->upstreamCallbacks()->setPausedForWebsocketUpgrade(false);
          filter_.callbacks_->continueDecoding();
        } else {
          filter_.callbacks_->sendLocalReply(
              static_cast<Envoy::Http::Code>(status), "",
              [&headers](Http::ResponseHeaderMap& local_headers) { ... },
              std::nullopt, StreamInfo::ResponseCodeDetails::get().WebsocketHandshakeUnsuccessful);
          return;
        }
    }
    ```
  - Reachability: source/common/router/upstream_codec_filter.cc UpstreamCodecFilter::CodecBridge::decodeHeaders() and source/common/router/upstream_request.cc UpstreamRequest::acceptHeadersFromRouter(), reached whenever a WebSocket-upgrade request is proxied to an HTTP/1.1 upstream
  - Verdict: IN — Re-fetched: the pausedForWebsocketUpgrade path now only clears the paused state when status == SwitchingProtocols (or the upstream is non-HTTP/1.1), else sendLocalReply with WebsocketHandshakeUnsuccessful (grep confirmed pausedForWebsocketUpgrade / SwitchingProtocols / WebsocketHandshakeUnsuccessful / RUNTIME_GUARD). NVD CWE-444; upgrade-response framing desync is request smuggling. Clean status-code gate behind a reloadable flag. IN.
  - Source: https://github.com/envoyproxy/envoy/security/advisories/GHSA-vcf8-7238-v74c ; https://github.com/envoyproxy/envoy/commit/3f4475b5b824c6b13900fc254da0a8daba769f9f.diff  ·  provenance: re-verified-this-session

- **CVE-2026-2332 (GHSA-355h-qmc2-wpwf)** — CWE-444 · `jetty/jetty.project` · fixed ? @ `ef6241188880b5a73546744a2807cdf712694a56` · **IN** (signature) · parser-state tracking (_chunkExtInQuote/_chunkExtQuotedPair) + reject-on-embedded-LF-inside-quoted-string (strict-parse)
  - Mechanism: Jetty's HTTP/1.1 chunk-extension parser had no quoted-string state tracking: a CR/LF byte inside a quoted chunk-extension value (e.g. `1;ext="val<CRLF>...`) was treated as ending the chunk-size line rather than as an illegal embedded control character, letting an attacker terminate the chunk header early from inside a quoted string and inject a smuggled request that a front-end proxy parses differently.
  - Affected -> Fixed: jetty 9.4.0 - 9.4.59 (also 10.x/11.x/12.x per advisory); fixed 9.4.60 (this anchor is the 9.4.x backport) -> ?
  - Vulnerable shape (removed):
    ```
    default:
        break; // TODO review
    ```
  - Guard added (post-patch):
    ```
    private boolean _chunkExtInQuote;
    private boolean _chunkExtQuotedPair;
    ...
    case LF:
        boolean chunkExtWasInQuote = _chunkExtInQuote;
        _chunkExtInQuote = false;
        _chunkExtQuotedPair = false;
        if (chunkExtWasInQuote)
            throw new BadMessageException(HttpStatus.BAD_REQUEST_400, "Bad chunk encoding: LF in quoted chunk extension");
    ...
    default:
        if (_chunkExtQuotedPair)
        {
            _chunkExtQuotedPair = false;
        }
        else if (_chunkExtInQuote)
        {
            if (t.getChar() == '"')
                _chunkExtInQuote = false;
            else if (t.getChar() == '\\')
                _chunkExtQuotedPair = true;
        }
        else if (t.getChar() == '"')
        {
            _chunkExtInQuote = true;
        }
        break;
    ```
  - Reachability: jetty-http/src/main/java/org/eclipse/jetty/http/HttpParser.java parseContent(), CHUNK_PARAMS state -- reached whenever Jetty parses a chunked-encoded HTTP/1.1 message carrying a quoted chunk-extension value
  - Verdict: IN — Re-fetched: adds _chunkExtInQuote / _chunkExtQuotedPair quoted-string state to the chunk-extension parser and throws BadMessageException(400, "Bad chunk encoding: LF in quoted chunk extension") on LF inside a quote, replacing the prior `break; // TODO review`. Collector hunks match verbatim (grep confirmed both fields, the throw, and the removed TODO). Clean isolable parser-state guard. CWE-444 confirmed.
  - Source: https://github.com/jetty/jetty.project/security/advisories/GHSA-355h-qmc2-wpwf ; https://github.com/jetty/jetty.project/commit/ef6241188880b5a73546744a2807cdf712694a56.diff  ·  provenance: re-verified-this-session

- **CVE-2025-58068 (GHSA-hw6f-rjfj-j7j7)** — CWE-444 · `eventlet/eventlet` · fixed ? @ `0bfebd1117d392559e25b4bfbfcc941754de88fb` · **IN** (signature) · sink fix -- fully discard the entire trailer section (loop until blank line) instead of assuming a fixed single-line trailer
  - Mechanism: Eventlet's WSGI chunked-body reader, after reading the terminal 0-length chunk, called rfile.readline() exactly once to consume what it assumed was a single trailing CRLF -- but HTTP chunked trailer sections can contain an arbitrary number of trailer header lines before the final blank line. Treating only one line as the request boundary let a crafted trailer section be misinterpreted differently by Eventlet vs a fronting proxy/cache, enabling smuggling / cache poisoning / control bypass.
  - Affected -> Fixed: eventlet < 0.40.3 (fixed 0.40.3) -> ?
  - Vulnerable shape (removed):
    ```
    if self.chunk_length == 0:
        rfile.readline()
    ```
  - Guard added (post-patch):
    ```
    def _discard_trailers(self, rfile):
        while True:
            line = rfile.readline()
            if not line or line in (b'\r\n', b'\n', b''):
                break
    ...
    if self.chunk_length == 0:
        self._discard_trailers(rfile)
    ```
  - Reachability: eventlet/wsgi.py Input._chunked_read(), reached whenever Eventlet's WSGI server parses a chunked-encoded request body with trailers after the terminal 0-chunk
  - Verdict: IN — Re-fetched (26-line single-file diff): replaces the lone rfile.readline() after the 0-length chunk with a _discard_trailers() loop that consumes to the blank line. Collector hunks match verbatim. Minimal, cleanly isolable sink fix. CWE-444 confirmed.
  - Source: https://github.com/eventlet/eventlet/security/advisories/GHSA-hw6f-rjfj-j7j7 ; https://github.com/eventlet/eventlet/commit/0bfebd1117d392559e25b4bfbfcc941754de88fb.diff  ·  provenance: re-verified-this-session

- **CVE-2024-23452 (GHSA-2862-59r4-c989)** — CWE-444 · `apache/brpc` · fixed ? @ `09b960026089d5efe22416b8cb7ec777663ca1e0` · **IN** (signature) · reject-on-conflicting-headers (fail-closed TE+CL), with an opt-in gflag (allow_chunked_length) escape hatch
  - Mechanism: bRPC's HTTP message parser accepted a message carrying both Transfer-Encoding and Content-Length headers simultaneously (RFC 7230 3.3.3 requires the receiver reject this or strip Content-Length), letting a front-end and bRPC disagree on where a body ends -- classic dual-header desync smuggling. Same commit also hardens the http_parser.cpp state machine (uses_transfer_encoding tracking + stricter token checks).
  - Affected -> Fixed: brpc 0.9.5 - 1.7.0 (fixed 1.8.0) -> ?
  - Vulnerable shape (removed):
    ```
    (no lines removed; the conflict check is inserted into the existing on_headers_complete flow before subsequent header processing)
    ```
  - Guard added (post-patch):
    ```
    if (parser->uses_transfer_encoding && parser->flags & F_CONTENTLENGTH) {
        if (parser->flags & F_CHUNKED && FLAGS_allow_chunked_length) {
            http_message->header().RemoveHeader("Content-Length");
        } else {
            LOG(ERROR) << "HTTP/1.1 protocol error: both Content-Length "
                       << "and Transfer-Encoding are set.";
            return -1;
        }
    }
    ```
  - Reachability: src/brpc/details/http_message.cpp HttpMessage::on_headers_complete(), reached on every inbound HTTP/1.1 message bRPC parses as a server or proxies to a backend
  - Verdict: IN — Re-fetched: on_headers_complete now rejects simultaneous Transfer-Encoding + Content-Length (or strips CL under the opt-in allow_chunked_length gflag). Collector hunk matches verbatim (grep confirmed uses_transfer_encoding / F_CONTENTLENGTH / F_CHUNKED / RemoveHeader / "both Content-Length"). Although the 557-line/6-file commit also rewrites http_parser.cpp, the surrounding changes only supply the uses_transfer_encoding flag the guard reads plus a gflag hatch -- the dual-TE/CL rejection is a discrete canonical CWE-444 signature (severity oracle cites this as the archetypal root cause). Isolable -> IN, not CONTESTED.
  - Source: https://github.com/advisories/GHSA-2862-59r4-c989 ; https://github.com/apache/brpc/commit/09b960026089d5efe22416b8cb7ec777663ca1e0.diff  ·  provenance: re-verified-this-session

- **CVE-2023-25725** — CWE-444 · `haproxy/haproxy` · fixed ? @ `a0e561ad7f29ed50c473f5a9da664267b60d1112` · **IN** (signature) · reject-on-empty-header-name (fail-closed input validation), applied identically across the HTTP/1, HPACK (HTTP/2), and QPACK (HTTP/3) header parsers
  - Mechanism: HAProxy's HTTP/1 header-list parser, HPACK (HTTP/2) decoder, and QPACK (HTTP/3) decoder all accepted an empty (zero-length) header field name. One downstream code path used a zero-length name as an implicit end-of-list signal, so an empty-named header could truncate the remaining header list, silently dropping legitimate headers after parsing -- enabling ACL/authorization bypass and front-end/back-end disagreement about which headers were actually sent.
  - Affected -> Fixed: haproxy < 2.7.3 / 2.6.9 / 2.5.12 / 2.4.22 / 2.2.29 / 2.0.31 -> ?
  - Vulnerable shape (removed):
    ```
    (no lines removed; a length-zero rejection check is inserted at each of the three independent parser sites: src/h1.c, src/hpack-dec.c, src/qpack-dec.c)
    ```
  - Guard added (post-patch):
    ```
    // src/h1.c, h1_headers_to_hdr_list():
    if (col <= sol) {
        state = H1_MSG_HDR_NAME;
        goto http_msg_invalid;
    }
    
    // src/hpack-dec.c, hpack_decode_frame():
    if (!name.len) {
        hpack_debug_printf("##ERR@%d##\n", __LINE__);
        ret = -HPACK_ERR_INVALID_ARGUMENT;
        goto leave;
    }
    
    // src/qpack-dec.c, qpack_decode_fs():
    if (!name.len) {
        qpack_debug_printf(stderr, "##ERR@%d\n", __LINE__);
        ret = -QPACK_DECOMPRESSION_FAILED;
        goto out;
    }
    ```
  - Reachability: src/h1.c h1_headers_to_hdr_list(), src/hpack-dec.c hpack_decode_frame(), src/qpack-dec.c qpack_decode_fs() -- reached on every inbound header list HAProxy parses, regardless of HTTP version
  - Verdict: IN — Re-fetched (55-line diff): inserts the same zero-length-name rejection at three independent parser sites -- h1.c `if (col <= sol) ... goto http_msg_invalid`, hpack-dec.c `if (!name.len) ... -HPACK_ERR_INVALID_ARGUMENT`, qpack-dec.c `if (!name.len) ... -QPACK_DECOMPRESSION_FAILED`. Collector hunks match verbatim. Clean fail-closed input-validation guard replicated across HTTP/1/2/3. CWE-444 confirmed.
  - Source: https://git.haproxy.org/?p=haproxy-2.7.git;a=commit;h=a0e561ad7f29ed50c473f5a9da664267b60d1112 ; https://github.com/haproxy/haproxy/commit/a0e561ad7f29ed50c473f5a9da664267b60d1112.diff  ·  provenance: re-verified-this-session

- **CVE-2024-53868** — CWE-444 · `apache/trafficserver` · fixed ? @ `ffbcfee6b6df664808542be35ab9b9e8694de71f` · **CONTESTED** (illustrative) · reject-on-bare-LF (strict CRLF enforcement) in the chunk state machine, gated by a NEW overridable config (default-on) -- entangled with config-plumbing churn
  - Mechanism: ChunkedHandler::read_size() accepted a bare LF (without a preceding CR) as a valid terminator for the chunk-size line and chunk-extension parsing, non-compliant with RFC 9112, letting a front-end and Traffic Server disagree on chunk/message boundaries.
  - Affected -> Fixed: trafficserver 9.2.0-9.2.9, 10.0.0-10.0.4 (fixed 9.2.10 / 10.0.5) -> ?
  - Vulnerable shape (removed):
    ```
    if (ParseRules::is_cr(*tmp)) {
        ++cr;
    }
    state = CHUNK_READ_SIZE_CRLF; // now look for CRLF
    ...
    } else if (ParseRules::is_cr(*tmp)) {
        if (cr != 0) {
            state = CHUNK_READ_ERROR;
            done  = true;
            break;
        }
        ++cr;
    }
    ...
    if (ParseRules::is_cr(*tmp)) {
        // Skip it
    } else if (ParseRules::is_lf(*tmp) && bytes_used <= 2) {
    ```
  - Guard added (post-patch):
    ```
    if ((prev_is_cr = ParseRules::is_cr(*tmp)) == true) {
        ++num_cr;
    }
    ...
    if (ParseRules::is_lf(*tmp)) {
        if (!prev_is_cr) {
            Dbg(dbg_ctl_http_chunk, "Found an LF without a preceding CR (protocol violation)");
            if (strict_chunk_parsing) {
                state = CHUNK_READ_ERROR;
                done  = true;
                break;
            }
        }
        ...
    }
    // records.yaml.en.rst:
    .. ts:cv:: CONFIG proxy.config.http.strict_chunk_parsing INT 1
       :reloadable:
       :overridable:
    ```
  - Reachability: src/proxy/http/HttpTunnel.cc ChunkedHandler::read_size(), reached whenever Traffic Server parses a chunked-encoded request/response body
  - Verdict: CONTESTED — Re-fetched and confirmed the guard is genuine -- ChunkedHandler::read_size() now flags an LF without a preceding CR and (when strict_chunk_parsing is set) enters CHUNK_READ_ERROR, a real CWE-444 chunk-boundary desync fix, and the collector's removed/added hunks match the actual -/+ lines. BUT the single commit (PR #12149) threads a brand-new overridable knob proxy.config.http.strict_chunk_parsing through 16 files (verified: records.yaml docs, TSOverridableConfigKey enum, apidefs.h.in, HttpConfig.h/.cc, InkAPI.cc, RecordsConfig.cc, ts_lua bindings, HttpSM.cc, overridable_txn_vars.cc, FetchSM.cc, gold tests); the guard fires only under the new default-on flag, so there is no fix-only hunk to promote as a literal signature. Genuine but not cleanly isolable -> keep-biased downgrade to CONTESTED, promote_signature=false. Kept illustrative.
  - Source: https://github.com/apache/trafficserver/pull/12149 ; https://github.com/apache/trafficserver/commit/ffbcfee6b6df664808542be35ab9b9e8694de71f.diff  ·  provenance: re-verified-this-session

Dropped: CVE-2024-34350 (GHSA-77r5-gw3j-2mpf, Next.js) (No fetchable code-fix diff exists publicly. The advisory's own listed fix reference (vercel/next.js commit 44eba020c615f0d9efe431f84ada67b81576f3f5) is an unrelated scripts/publish-release.js retry-logic change, and the cited v13.5.0...v13.5.1 tag compare is only version-bump/canary-release commits with no routing/rewrites code change. Version-string-only per the hard rules; not re-fetched this session but dropping is the conservative direction and does not affect the bucket verdict (already >=6 clean).); CVE-2025-6999 (WatchGuard Fireware OS) (Closed-source vendor firmware (WatchGuard Fireware OS admin portal); no public source repository or fix commit to fetch. Unverifiable -> dropped, consistent with the established dropped-candidate pattern for this class.)

## Unrestricted file upload -> RCE  (CWE-434)

Grounds cards: skills/vulns/arbitrary-file-upload
Bucket verdict: **THIN — only 3 clean IN anchors (Traccar, ShowDoc, Open eClass) against the >=6 bar; 3 further CONTESTED (Dasherr misattributed-fix, Erugo + HAX CMS PHP entangled). Six distinct products total. Dominant guard shape is bimodal: (a) extension/MIME-type allowlist swap replacing a broken/dead/denylist check — Traccar Content-Type-substring -> MIME switch-allowlist; ShowDoc dead-property allowExts -> exts; HAX strpos 4-item denylist -> preg_match allowlist; Dasherr suffix-check repair; and (b) canonicalization/containment for archive-extraction & path-controlled-write variants — Open eClass per-zip-entry filename validation before extractTo(); Erugo realpath() prefix-containment on a client-controlled dest path.**  ·  3 IN / 3 CONTESTED / 10 dropped  ·  3 promotable signatures
Severity-corpus join: CWE-434 upload->RCE bucket: severity tracks Privileges-Required — unauth arbitrary write (Dasherr) at Critical ~9.8 (AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H), authenticated low-priv (Traccar/HAX/Erugo) at High ~8.8 (PR:L), admin-gated archive import (Open eClass) ~7.2 (PR:H); all C:H/I:H/A:H code-exec impact — same CWE-434 severity-corpus bucket with PR the dominant discriminator.

- **CVE-2024-24809 (GHSA-vhrw-72f6-gwp5)** — CWE-434 · `traccar/traccar` · fixed not stated by OSV (commit-level fix 2024-04-04) @ `1c29f3a604fe13c8a337935a1a1ad966b4b62d5b` · **IN** (signature) · denylist-to-safe-api
  - Mechanism: POST /api/devices/{id}/image (DeviceResource.uploadImage) derived the stored file's extension directly from the client-supplied Content-Type header via type.substring("image/".length()); an attacker set an arbitrary Content-Type to control the on-disk extension, combined per the advisory with device-id path traversal to place the file at a web-accessible path — attacker-controlled dangerous-extension upload.
  - Affected -> Fixed: traccar (fix landed 2024-04-04; OSV GIT range only, no numbered release) -> not stated by OSV (commit-level fix 2024-04-04)
  - Vulnerable shape (removed):
    ```
    String extension = type.substring("image/".length());
    ```
  - Guard added (post-patch):
    ```
    private String imageExtension(String type) {
        switch (type) {
            case "image/jpeg":
                return ".jpg";
            case "image/png":
                return ".png";
            case "image/gif":
                return ".gif";
            case "image/webp":
                return ".webp";
            case "image/svg+xml":
                return ".svg";
            default:
                throw new IllegalArgumentException("Unsupported image type");
        }
    }
    ...
    String extension = imageExtension(type);
    ```
  - Reachability: POST /api/devices/{id}/image -> DeviceResource.uploadImage(...) -> extension previously taken verbatim from Content-Type -> mediaManager.createFileStream(uniqueId, name, extension); reachable by any authenticated user with device-image-upload permission (device id separately path-traversal-controllable per the advisory).
  - Verdict: IN — Guard verified verbatim this session: attacker-controlled Content-Type-substring extension replaced by a fixed MIME->extension switch allowlist that throws on unknown types. Clean isolable single-method change in one file (DeviceResource.java, +18/-1). SHA note: OSV's tracked 'fixed' SHA b099b298 is a cosmetic 39-min follow-up ('Remove extra dot' — strips leading dots from the same switch's return strings, no security effect, re-fetched and confirmed); the security guard lives in its direct parent 1c29f3a, which is the anchor. Discrepancy resolved with high confidence.
  - Source: https://api.osv.dev/v1/vulns/CVE-2024-24809 ; https://github.com/traccar/traccar/commit/1c29f3a604fe13c8a337935a1a1ad966b4b62d5b ; https://github.com/traccar/traccar/commit/b099b298f90074c825ba68ce73532933c7b9d901 ; https://github.com/traccar/traccar/security/advisories/GHSA-vhrw-72f6-gwp5  ·  provenance: re-verified-this-session

- **CVE-2025-0520 (GHSA-6jmr-r7p6-f5wr)** — CWE-434 · `star7th/showdoc` · fixed 2.8.7 @ `189b6cedc011a0d2758f4207cb85c565372093dd` · **IN** (signature) · exact-match-swap
  - Mechanism: PageController::uploadImg() set $upload->allowExts = array('jpg','gif','png','jpeg') to restrict uploads, but ThinkPHP's \Think\Upload::upload() reads the property named exts, not allowExts — so the assignment was a silent no-op and the endpoint accepted any extension including .php, allowing upload+direct execution of a webshell.
  - Affected -> Fixed: showdoc/showdoc < 2.8.7 (v1.0.0 through v2.8.6) -> 2.8.7
  - Vulnerable shape (removed):
    ```
    $upload->allowExts  = array('jpg', 'gif', 'png', 'jpeg');// 设置附件上传类型
    ```
  - Guard added (post-patch):
    ```
    $upload->exts  = array('jpg', 'gif', 'png', 'jpeg');// 设置附件上传类型
    ```
  - Reachability: uploadImg() action in server/Application/Home/Controller/PageController.class.php -> \Think\Upload::upload() -> now enforces the $exts allowlist property ThinkPHP actually checks before accepting the file.
  - Verdict: IN — Verified verbatim this session: single-char property-name fix allowExts -> exts. Pre-fix assignment targeted a dead property so every extension was accepted -> direct webshell RCE. Clean, isolable, single-line, single-file; CWE-434 match; corroborated by CVE-2025-0520 / VulnCheck advisory. Commit message 'fix Arbitrary file upload vuln'.
  - Source: https://api.osv.dev/v1/vulns/GHSA-6jmr-r7p6-f5wr ; https://github.com/star7th/showdoc/commit/189b6cedc011a0d2758f4207cb85c565372093dd ; https://www.vulncheck.com/advisories/showdoc-unauthenticated-file-upload-rce  ·  provenance: re-verified-this-session

- **GHSA-rf6j-xgqp-wjxg** — CWE-434 · `gunet/openeclass` · fixed not stated by the advisory; fix commit dated 2025-12-03 @ `3f9d267b79812a4dd708bb1302339e6a5abe67d9` · **IN** (signature) · allowlist
  - Mechanism: modules/admin/theme_options.php's theme-import handler accepted an admin-uploaded ZIP and called $archive->extractTo('courses/theme_data/temp') with no inspection of member filenames, letting an admin embed a PHP webshell in the theme ZIP that lands in a web-accessible dir and executes on direct request.
  - Affected -> Fixed: Open eClass < 4.0.1 (advisory-stated; no fixed version number given) -> not stated by the advisory; fix commit dated 2025-12-03
  - Vulnerable shape (removed):
    ```
    (no lines removed; guard inserted before extractTo())
    ```
  - Guard added (post-patch):
    ```
    // validate contents of zip archive
    for ($i = 0; $i < $archive->numFiles; $i++) {
        $stat = $archive->statIndex($i, ZipArchive::FL_ENC_RAW);
        $files_in_zip[$i] = $stat['name'];
        if (!empty(my_basename($files_in_zip[$i]))) {
            validateUploadedFile(my_basename($files_in_zip[$i]), 3);
        }
    }
    // extract zip archive
    ```
  - Reachability: Admin theme-import upload ($_POST['import'] branch of modules/admin/theme_options.php) -> ZipArchive::open() on the uploaded file -> (new) per-entry validateUploadedFile() loop -> extractTo('courses/theme_data/temp'); requires administrative privilege per the advisory.
  - Verdict: IN — Guard re-verified present in the commit this session (single file, +12/-3): per-zip-entry statIndex()+validateUploadedFile() loop inserted immediately before extractTo(), exactly matching the advisory's described root cause (extractTo with no member-filename inspection). The two co-changes in-file (isset->?? and '== true' cleanup) are trivial cosmetic edits, not entanglement. Provenance caveat: GHSA lists no fixed version and no linked commit (no OSV record); advisory<->commit link independently established via commit-message/file/mechanism match, not advisory-asserted — high-confidence match.
  - Source: https://github.com/gunet/openeclass/security/advisories/GHSA-rf6j-xgqp-wjxg ; https://github.com/gunet/openeclass/commit/3f9d267b79812a4dd708bb1302339e6a5abe67d9  ·  provenance: re-verified-this-session

- **CVE-2023-23607 (GHSA-6rgc-2x44-7phq)** — CWE-434 · `erohtar/Dasherr` · fixed 1.05.00 @ `445325c7cf1148a8cd38af3a90789c6cbf6c5112` · **CONTESTED** (illustrative) · exact-match-swap
  - Mechanism: www/include/filesave.php reads $_POST['file'] as a fully attacker-controlled destination path and $_POST['data'] as raw content, then fopen($fname,'w')+fwrite() writes the POST body verbatim to that path. At the actually-affected release tag v1.04.02 there was NO extension check at all (fetched this session) — an unauthenticated arbitrary file write -> PHP webshell -> RCE.
  - Affected -> Fixed: Dasherr <= v1.04.02 (pre-1.05.00) -> 1.05.00
  - Vulnerable shape (removed):
    ```
    if(substr($fname, -1, 5) != '.json') {
    ```
  - Guard added (post-patch):
    ```
    if(substr($fname, -5) != '.json') {
    ```
  - Reachability: Unauthenticated POST to www/include/filesave.php -> $_POST['file'] used directly as fopen() destination, $_POST['data'] as content; per GHSA-6rgc-2x44-7phq exploited to write and execute a PHP webshell.
  - Verdict: CONTESTED — MISATTRIBUTED FIX. Vuln is genuine CWE-434 unauth arbitrary write -> RCE; at affected tag v1.04.02 filesave.php had NO check at all (verified). But the OSV-cited FIX commit 445325c's diff is a safe->safe refinement: verified empirically in PHP this session that the pre-fix guard in its parent, substr($fname,-1,5), always returns one char and can NEVER equal '.json', so it already blocks EVERY write (fail-closed) — the RCE was accidentally closed by an earlier intermediate commit that introduced the broken check, not by 445325c. The extracted removed/added hunk therefore does not represent the vuln->patch transition and would teach a misleading signature (the truly-vulnerable state is the absence of any check, per v1.04.02, not the broken-substr line). Hunk is verbatim-correct and re-fetchable but must not be promoted.
  - Source: https://api.osv.dev/v1/vulns/CVE-2023-23607 ; https://github.com/erohtar/Dasherr/commit/445325c7cf1148a8cd38af3a90789c6cbf6c5112 ; https://raw.githubusercontent.com/erohtar/Dasherr/v1.04.02/www/include/filesave.php ; https://github.com/erohtar/Dasherr/security/advisories/GHSA-6rgc-2x44-7phq  ·  provenance: re-verified-this-session

- **CVE-2026-24897 (GHSA-336w-hgpq-6369)** — CWE-434 (also tagged CWE-22, CWE-94) · `ErugoOSS/Erugo` · fixed 0.2.15 @ `256bc63831a0b5e9a94cb024a0724e0cd5fa5e38` · **CONTESTED** (illustrative) · canonicalization
  - Mechanism: UploadsController::createShareFromUploads() built a destination directory from the client-supplied filePaths field by exploding/imploding on '/' with no traversal filtering, then mkdir()'d and wrote uploaded content under that raw path; a low-priv authenticated user supplied traversal segments to relocate an uploaded file (e.g. a PHP webshell) into the public web root and execute it via direct HTTP request.
  - Affected -> Fixed: Erugo <= 0.2.14 -> 0.2.15
  - Vulnerable shape (removed):
    ```
    $destPath = $completePath . '/' . $originalPath;
    
          if (!file_exists($destPath)) {
            mkdir($destPath, 0777, true);
          }
    ```
  - Guard added (post-patch):
    ```
    // Sanitize path to prevent directory traversal attacks
            $originalPath = $this->sanitizePath($originalPath);
          }
    
          $destPath = $completePath . '/' . $originalPath;
          
          // Verify the resolved path is within the share directory
          // Create parent directories first so realpath can resolve
          if (!file_exists($destPath)) {
            mkdir($destPath, 0777, true);
          }
          $resolvedPath = realpath($destPath);
          $resolvedSharePath = realpath($completePath);
          
          if ($resolvedPath === false || $resolvedSharePath === false || 
              strpos($resolvedPath, $resolvedSharePath) !== 0) {
            Log::warning('Path traversal attempt detected', [
              'user_id' => $user->id,
              'original_path' => $request->filePaths[$uploadId] ?? '',
              'resolved_path' => $resolvedPath,
              'share_path' => $resolvedSharePath
            ]);
            
            // Clean up and skip this file
            continue;
          }
    ```
  - Reachability: POST /api/uploads/create-share-from-uploads -> UploadsController::createShareFromUploads() -> client-controlled filePaths[uploadId] builds destPath -> now sanitizePath() strips '..'/leading-slashes/null-bytes, then a realpath() prefix-containment check gates the mkdir()/write; reachable by any authenticated user regardless of privilege per the advisory.
  - Verdict: CONTESTED — ENTANGLED, multi-injection-point. Verified this session: the single fix commit 256bc63 applies the same sanitizePath()+realpath()-prefix-containment pattern across THREE separate controllers in one diff (UploadsController.php +49, TusdHooksController.php +63, EmailTemplatesController.php +23; 127 insertions / 3 files). Guard is genuine CWE-434/22/94; only the UploadsController createShareFromUploads() portion matching the CVE's 'share-creation endpoint' is extracted. Not one isolated hunk.
  - Source: https://api.osv.dev/v1/vulns/CVE-2026-24897 ; https://github.com/ErugoOSS/Erugo/commit/256bc63831a0b5e9a94cb024a0724e0cd5fa5e38 ; https://github.com/ErugoOSS/Erugo/security/advisories/GHSA-336w-hgpq-6369  ·  provenance: re-verified-this-session

- **CVE-2025-32028 (GHSA-vj5q-3jv2-cg5p)** — CWE-434 · `haxtheweb/haxcms-php` · fixed 10.0.3 @ `0cde0ae428750e93510dce973f36241a1fbacf40` · **CONTESTED** (illustrative) · denylist-to-safe-api
  - Mechanism: HAXCMSFile::save() gated uploads with a strpos() denylist checking only for '.php', '.sh', '.js', '.css'; this fails open for any other server-executable extension (.phar, .phtml, etc.), letting an authenticated attacker upload and execute a file under an extension absent from the 4-item denylist.
  - Affected -> Fixed: haxcms-php 9.0.0 - 10.0.2 -> 10.0.3
  - Vulnerable shape (removed):
    ```
    strpos($name, '.php') === FALSE &&
                strpos($name, '.sh') === FALSE &&
                strpos($name, '.js') === FALSE &&
                strpos($name, '.css') === FALSE
    ```
  - Guard added (post-patch):
    ```
    preg_match(
                    '/.(jpg|jpeg|png|gif|webm|webp|mp4|mov|csv|ppt|pptx|xlsx|doc|xls|docx|pdf|rtf|txt|html|md)$/i',
                    $upload['name']
                )
    ```
  - Reachability: Any HAXCMSFile::save($upload, ...) call site (file-manager upload; Operations::setUserPhoto(); Operations::saveFile()) — was denylist-gated by strpos(), now allowlist-gated by preg_match() against a fixed extension set; reachable by any authenticated user with file-upload capability per the advisory.
  - Verdict: CONTESTED — ENTANGLED. HAXCMSFile.php guard verified verbatim this session (denylist -> preg_match allowlist, genuine fail-open CWE-434 fix). But fix commit 0cde0ae is 22 files / +427 -262, burying the 13-line HAXCMSFile.php hunk among dozens of built/minified frontend JS bundles (build/es6/node_modules/*), an unrelated HAXCMS.php change, and removal of an unrelated Operations.php importEvolution() endpoint (-38). Advisory lists no linked commit; located via git-tag compare 9.0.21...v10.0.3. Hunk isolable but commit heavily entangled.
  - Source: https://api.osv.dev/v1/vulns/CVE-2025-32028 ; https://github.com/haxtheweb/haxcms-php/commit/0cde0ae428750e93510dce973f36241a1fbacf40 ; https://github.com/haxtheweb/issues/security/advisories/GHSA-vj5q-3jv2-cg5p  ·  provenance: re-verified-this-session

Dropped: CVE-2023-23607 (Dasherr) — NOTE: not dropped, downgraded to CONTESTED (Collector rated this clean IN; adjudicator downgraded to CONTESTED (kept, promote_signature=false). The OSV-cited FIX commit 445325c only swaps substr($fname,-1,5)->substr($fname,-5); empirically the pre-fix substr already blocks all writes (fail-closed), so that commit is a safe->safe refinement, not the RCE fix. The actually-vulnerable state (tag v1.04.02) had no check at all.); CVE-2025-58159 (WeGIA, GHSA-wj2c-237g-cgqp) (Real fix commit a08f04d but a full-file rewrite of controla_xlsx.php entangling the MIME/extension fix with unrelated comment restructuring, a sistema.js UI tweak, and an unrelated index.php path-depth fix — no clean isolable single guard.); CVE-2026-25510 (CI4MS, GHSA-gp56-f67f-m4px) (OSV has no GIT-type range (Packagist fixed-version bump only). The only located commit 86be293 bundles an unrelated README credit, Filters.php config, and AuthController.php changes — entangled, no isolable single-file guard within budget.); CVE-2026-33687 (code16/sharp, GHSA-fr76-5637-w3g9) (OSV has no GIT-type range; only a WEB reference to PR #714 with no independently verified single fix SHA — not pursued within budget.); GHSA-qv4m-m73m-8hj7 (NotrinosERP) (OSV/advisory has no GIT-type range and no FIX-type reference — no fetchable single fix commit.); CVE-2026-32985 (Xerte Online Toolkits) (OSV GIT range gives only a last_affected commit, no 'fixed' event — no resolvable single fix commit within budget.); CVE-2025-34085 (WordPress Simple File List plugin, GHSA-8xp7-p66p-4h9h) (WordPress.org SVN-hosted plugin, not git; changeset served behind a bot/hashcash challenge, not fetchable as a clean diff.); CVE-2026-58480 (Blocksy Companion Pro WordPress plugin) (WordPress.org SVN-hosted plugin, not git — no fetchable commit-diff URL of the required shape.); CVE-2020-25213 (wp-file-manager elFinder connector) (WordPress.org SVN-hosted plugin, not git — same reason.); CVE-2018-9206 (blueimp jQuery-File-Upload) (Real GitHub repo but the historical fix is attributed to two separate commits (aeb47e5, ad4aefd) rather than one clean fetchable single SHA verifiable against a structured OSV FIX/GIT-range — not pursued to a verified single commit within budget.)

## Cryptographic weakness  (CWE-327 / CWE-916 / CWE-330)

Grounds cards: skills/vulns/cryptographic-weakness
Bucket verdict: **THIN — 5 clean IN (form-data, undici, opencast, crypto-js, EnroCrypt) + 1 CONTESTED (serverpod, 15+-file non-single-purpose migration commit), below the 6-clean bar. Dominant guard shape: swap a fast/weak primitive for a cryptographically appropriate one — CSPRNG substitution to kill RNG-predictability (CWE-330: Math.random -> crypto.randomBytes/randomInt), and weak-hash-to-strong-KDF swaps for password storage (CWE-327/916: MD5 / SHA1-iter-1 / single-pass-SHA256 -> BCrypt / Argon2id / high-iteration-PBKDF2). Extra diversity weakness: the two CWE-330 anchors are the identical Math.random-multipart-boundary mechanism in different packages.**  ·  5 IN / 1 CONTESTED / 7 dropped  ·  5 promotable signatures
Severity-corpus join: Joins the severity-corpus weak-crypto / broken-hash / insufficient-entropy bucket at mostly CVSS Medium: the four password-KDF anchors (opencast/serverpod/crypto-js/EnroCrypt) are offline-cracking amplifiers gated on a prior credential-store leak (high AC, no standalone integrity/availability impact), while the CWE-330 RNG-prediction pair (form-data/undici) needs observed boundary outputs (high AC) to gain only limited request-tampering integrity impact.

- **CVE-2025-7783 (GHSA-fjxv-7rqg-78g4)** — CWE-330 · `form-data/form-data` · fixed 2.5.4 / 3.0.4 / 4.0.4 @ `3d1723080e6577a66f17f163ecd345a21d8d0fd0` · **IN** (signature) · CSPRNG substitution (Math.random loop -> crypto.randomBytes(12))
  - Mechanism: FormData.prototype._generateBoundary() built the multipart boundary string by concatenating hex digits from Math.floor(Math.random()*10) in a loop. Math.random()'s V8 xorshift128+ internal state can be recovered from a handful of observed outputs, letting an attacker who can see boundary values (e.g. via an SSRF/webhook echo) predict future boundaries and inject additional multipart form fields/parameters into requests built by the victim app.
  - Affected -> Fixed: npm form-data 0-<2.5.4, 3.0.0-<3.0.4, 4.0.0-<4.0.4 -> 2.5.4 / 3.0.4 / 4.0.4
  - Vulnerable shape (removed):
    ```
    var boundary = '--------------------------';
      for (var i = 0; i < 24; i++) {
        boundary += Math.floor(Math.random() * 10).toString(16);
      }
    
      this._boundary = boundary;
    ```
  - Guard added (post-patch):
    ```
    this._boundary = '--------------------------' + crypto.randomBytes(12).toString('hex');
    ```
  - Reachability: lib/form_data.js FormData.prototype._generateBoundary(), invoked by the FormData constructor on every instance construction; entrypoint is any application using the form-data package to build a multipart/form-data request body.
  - Verdict: IN — Re-fetched diff confirms the verbatim hunk; clean single-guard CSPRNG substitution (Math.random hex loop -> crypto.randomBytes) in a 3-file commit (lib/form_data.js + package.json + new prediction test); textbook CWE-330 boundary-entropy match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-fjxv-7rqg-78g4 ; https://github.com/form-data/form-data/security/advisories/GHSA-fjxv-7rqg-78g4 ; https://github.com/form-data/form-data/commit/3d1723080e6577a66f17f163ecd345a21d8d0fd0.diff ; https://nvd.nist.gov/vuln/detail/CVE-2025-7783  ·  provenance: re-verified-this-session

- **CVE-2025-22150 (GHSA-c76h-2ccp-4975)** — CWE-330 · `nodejs/undici` · fixed 5.28.5 @ `711e20772764c29f6622ddc937c63b6eefdf07d0` · **IN** (signature) · CSPRNG substitution with graceful fallback (crypto.randomInt, falls back to Math.random only if node:crypto is unavailable)
  - Mechanism: extractBody() in the fetch() implementation computed the multipart/form-data boundary as `Math.floor(Math.random() * 1e11)` padded to 11 digits. Math.random() output is predictable once several values are observed, so an attacker able to see boundaries from requests sent to an attacker-controlled/observable endpoint can predict subsequent boundaries and tamper with the multipart body structure of requests aimed at other backends.
  - Affected -> Fixed: npm undici >=4.5.0 <5.28.5 (branch also separately fixed at 6.21.1 and 7.2.3) -> 5.28.5
  - Vulnerable shape (removed):
    ```
    const boundary = `----formdata-undici-0${`${Math.floor(Math.random() * 1e11)}`.padStart(11, '0')}`
    ```
  - Guard added (post-patch):
    ```
    let random
    try {
      const crypto = require('node:crypto')
      random = (max) => crypto.randomInt(0, max)
    } catch {
      random = (max) => Math.floor(Math.random(max))
    }
    ...
    const boundary = `----formdata-undici-0${`${random(1e11)}`.padStart(11, '0')}`
    ```
  - Reachability: lib/fetch/body.js extractBody(), invoked whenever global fetch() (or Request/Response) is called with a FormData body; entrypoint is any app issuing multipart requests via undici's fetch implementation.
  - Verdict: IN — Re-fetched diff confirms the single-file (lib/fetch/body.js) boundary-line change to a crypto.randomInt-with-Math.random-fallback helper; CWE-330 match. Shares the exact Math.random-boundary mechanism with the form-data anchor but is an independent package/CVE/codebase — kept distinct, not merged.
  - Source: https://github.com/advisories/GHSA-c76h-2ccp-4975 ; https://github.com/nodejs/undici/security/advisories/GHSA-c76h-2ccp-4975 ; https://github.com/nodejs/undici/commit/711e20772764c29f6622ddc937c63b6eefdf07d0.diff ; https://hackerone.com/reports/2913312  ·  provenance: re-verified-this-session

- **CVE-2020-5229 (GHSA-h362-m8f2-5x7c)** — CWE-327 · `opencast/opencast` · fixed 7.6 (also 8.1) @ `32bfbe5f78e214e2d589f92050228b91d704758e` · **IN** (signature) · password-encoder algorithm swap (username-salted MD5 -> CustomPasswordEncoder wrapping BCrypt, with legacy-hash detection/migration path)
  - Mechanism: Spring Security's authentication-manager was configured with a username-salted MD5 password encoder (`hash="md5"` + username as salt-source) for storing/verifying user passwords, and identical username+password pairs across accounts collided to the same hash. MD5 is a fast, broken digest unsuitable for password storage, making offline cracking of leaked hashes cheap.
  - Affected -> Fixed: Maven org.opencastproject:opencast-common-jpa-impl 6.6, 7.2-7.5 (also 8.0) -> 7.6 (also 8.1)
  - Vulnerable shape (removed):
    ```
    <!-- The JPA user directory stores md5 hashed, salted passwords, so we must use a username-salted md5 password encoder. -->
    <sec:password-encoder hash="md5"><sec:salt-source user-property="username" /></sec:password-encoder>
    ```
  - Guard added (post-patch):
    ```
    <bean id="passwordEncoder" class="org.opencastproject.kernel.security.CustomPasswordEncoder" />
    ...
    <sec:password-encoder ref="passwordEncoder">
      <!-- This salt is used only for decoding legacy MD5 hased passwords -->
      <sec:salt-source user-property="username" />
    </sec:password-encoder>
    ```
  - Reachability: etc/security/mh_default_org.xml Spring `authentication-manager` bean wiring the `userDetailsService` authentication-provider, used on every username/password login across the Opencast admin/API/user-directory stack.
  - Verdict: IN — Re-fetched diff confirms the verbatim XML password-encoder swap (hash="md5" -> ref CustomPasswordEncoder/BCrypt) plus the new bean; the 7-file commit is single-purpose MD5->BCrypt migration (guard + inherent legacy-hash discovery/compat tooling), and the guard hunk is cleanly isolable in the security XML. CWE-327 broken-password-hash match.
  - Source: https://api.osv.dev/v1/vulns/GHSA-h362-m8f2-5x7c ; https://github.com/advisories/GHSA-h362-m8f2-5x7c ; https://github.com/opencast/opencast/commit/32bfbe5f78e214e2d589f92050228b91d704758e.diff  ·  provenance: re-verified-this-session

- **CVE-2023-46233 (GHSA-xwcq-pm8m-c4vf)** — CWE-327 / CWE-328 / CWE-916 · `brix/crypto-js` · fixed 4.2.0 @ `421dd538b2d34e7c24a5b72cc64dc2b9167db40a` · **IN** (signature) · KDF default hardening (hasher SHA1->SHA256, iterations 1->250000)
  - Mechanism: CryptoJS.PBKDF2's default configuration used SHA1 as the hasher and iterations:1, i.e. a single round of a weak hash for key/password derivation, roughly 1.3 million times weaker than the current recommended work factor. Any caller invoking PBKDF2() without explicitly overriding hasher/iterations (a very common usage pattern) got a derived key/signature that is cheap to brute-force offline.
  - Affected -> Fixed: npm crypto-js, all versions (0-<4.2.0) -> 4.2.0
  - Vulnerable shape (removed):
    ```
    var SHA1 = C_algo.SHA1;
    ...
     * @property {Hasher} hasher The hasher to use. Default: SHA1
     * @property {number} iterations The number of iterations to perform. Default: 1
    ...
    cfg: Base.extend({
        keySize: 128/32,
        hasher: SHA1,
        iterations: 1
    }),
    ```
  - Guard added (post-patch):
    ```
    var SHA256 = C_algo.SHA256;
    ...
     * @property {Hasher} hasher The hasher to use. Default: SHA256
     * @property {number} iterations The number of iterations to perform. Default: 250000
    ...
    cfg: Base.extend({
        keySize: 128/32,
        hasher: SHA256,
        iterations: 250000
    }),
    ```
  - Reachability: src/pbkdf2.js PBKDF2 algorithm `cfg` defaults, used whenever application code calls `CryptoJS.PBKDF2(password, salt)` without passing explicit `hasher`/`iterations` options (the documented, common call shape).
  - Verdict: IN — Re-fetched diff confirms the PBKDF2 default hardening (SHA1/iterations:1 -> SHA256/250000) in a 3-file commit (src/pbkdf2.js + grunt sha1->sha256 dep + test-vector updates); textbook CWE-916/327/328 weak-KDF-default match, guard cleanly isolable in the cfg defaults.
  - Source: https://api.osv.dev/v1/vulns/GHSA-xwcq-pm8m-c4vf ; https://github.com/brix/crypto-js/security/advisories/GHSA-xwcq-pm8m-c4vf ; https://github.com/brix/crypto-js/commit/421dd538b2d34e7c24a5b72cc64dc2b9167db40a.diff  ·  provenance: re-verified-this-session

- **CVE-2024-29886 (GHSA-r75m-26cq-mjxc)** — CWE-916 · `serverpod/serverpod` · fixed 1.2.6 @ `a78b9e9f1de74d1300633a122b6cc0f064139ad6` · **CONTESTED** (illustrative) · KDF algorithm swap (single-pass SHA-256 -> Argon2id via new PasswordHash class), with a legacy-hash detection/migration path (tryMigrateAuthEntry / migrateLegacyPasswordHashes)
  - Mechanism: Emails.generatePasswordHash() derived the stored password hash as a single SHA-256 pass over `password + salt` (salt was a fixed configured secret, optionally with the email appended) — a fast general-purpose digest with no configurable work factor, making offline cracking of a leaked database cheap compared to a proper password KDF.
  - Affected -> Fixed: Pub serverpod_auth_server >=0.9.2 <1.2.6 -> 1.2.6
  - Vulnerable shape (removed):
    ```
    static String generatePasswordHash(String password, String email) {
        var salt = Serverpod.instance.getPassword('email_password_salt') ??
            'serverpod password salt';
        if (AuthConfig.current.extraSaltyHash) {
          salt += ':$email';
        }
        return sha256.convert(utf8.encode(password + salt)).toString();
      }
    ```
  - Guard added (post-patch):
    ```
    static String generatePasswordHash(String password) {
        return PasswordHash.argon2id(
          password,
          pepper: EmailSecrets.pepper,
          allowUnsecureRandom: AuthConfig.current.allowUnsecureRandom,
        );
      }
    ```
  - Reachability: modules/serverpod_auth/serverpod_auth_server/lib/src/business/email_auth.dart Emails.generatePasswordHash(), called from user creation, password change, and password-reset flows; entrypoint is any serverpod_auth_server email/password signup or credential update.
  - Verdict: CONTESTED — Guard hunk (single-pass SHA-256 over password+static-salt -> Argon2id) is verbatim-confirmed and is a clean CWE-916 exemplar, but the re-fetched fix commit spans 15+ files and WebFetch classifies it as NOT a single-purpose migration (new PasswordHash + EmailSecrets infra, endpoint refactor, generated client/protocol code, template pubspecs, CI workflow change, 4 new test files). Genuine fix, but too entangled to serve as a tight isolable exemplar for signature promotion.
  - Source: https://api.osv.dev/v1/vulns/GHSA-r75m-26cq-mjxc ; https://github.com/serverpod/serverpod/security/advisories/GHSA-r75m-26cq-mjxc ; https://github.com/serverpod/serverpod/commit/a78b9e9f1de74d1300633a122b6cc0f064139ad6.diff  ·  provenance: re-verified-this-session

- **CVE-2021-39182 (GHSA-35m5-8cvj-8783)** — CWE-327 / CWE-328 / CWE-916 · `Morgan-Phoenix/EnroCrypt` · fixed 1.1.4 @ `e652d56ac60eadfc26489ab83927af13a9b9d8ce` · **IN** (signature) · insecure API removal (MD5 hashing method deleted, not merely deprecated)
  - Mechanism: The library's hashing.py exposed an `MD5()` method that hashed input via `hashlib.md5`, offered alongside the library's other (stronger) hash methods as an equally-presented option for consumers building password/data-integrity hashes — MD5 is both cryptographically broken (collision-prone) and fast enough to make brute-forcing hashed passwords cheap.
  - Affected -> Fixed: PyPI EnroCrypt 0-<1.1.4 (1.0.0-1.0.7, 1.1.0-1.1.3) -> 1.1.4
  - Vulnerable shape (removed):
    ```
    def MD5(self,data:str):
            sha = hashlib.md5(bytes(data.encode()))
            hash = str(sha.digest())
            return self.__Salt(hash,salt=self.salt)
    ```
  - Guard added (post-patch):
    ```
    (no lines added — the MD5() method was deleted outright from enrocrypt/hashing.py, removing the insecure hashing option entirely rather than wrapping it in a guard)
    ```
  - Reachability: enrocrypt/hashing.py class method `MD5()`, part of the public hashing API surface any consumer of the EnroCrypt package could call directly to hash passwords/data.
  - Verdict: IN — Re-fetched diff confirms a single-file pure deletion of the MD5() method (hashlib.md5 for password/data hashing) with no replacement code; the verbatim removed hunk is a clean, isolable CWE-327/328 vulnerable-pattern exemplar and the insecure-API-removal guard is unambiguous. Deletion-only (no positive guard added) but the removed pattern is the signal.
  - Source: https://api.osv.dev/v1/vulns/GHSA-35m5-8cvj-8783 ; https://github.com/Morgan-Phoenix/EnroCrypt/security/advisories/GHSA-35m5-8cvj-8783 ; https://github.com/Morgan-Phoenix/EnroCrypt/commit/e652d56ac60eadfc26489ab83927af13a9b9d8ce.diff ; https://nvd.nist.gov/vuln/detail/CVE-2021-39182  ·  provenance: re-verified-this-session

Dropped: CVE-2024-5559 / GHSA-46fj-mg88-7m5g (Schneider Electric relay device advisory tagged CWE-327 (weak crypto in a physically-entered reset token), but 'No package listed' and both affected/patched versions are 'Unknown' with no source repository or fix commit — proprietary firmware, nothing re-fetchable.); CVE-2022-34757 / GHSA-8g4c-686x-3qcc (Schneider Electric Easergy P5 weak SSH cipher suites, CWE-327, but no fix version/commit published in the advisory and no public repository exists for this embedded relay firmware — dropped per no-fetchable-commit rule.); CVE-2022-2582 / GHSA-76wf-9vgp-pj7w (AWS S3 Crypto SDK for Go MD5 plaintext-hash-in-metadata issue: advisory is marked Withdrawn/duplicate of GHSA-6jvc-q2x7-pchv, lists no CWE at all, and the mechanism (unencrypted metadata hash aiding offline brute-force) is closer to CWE-311/312 (missing/weak encryption of stored data) than a clean CWE-327/916/330 class match.); CVE-2021-21352 / GHSA-43c9-rx4h-4gqq (anuko/timetracker) (Password-reset tokens derived from md5(uniqid()) (predictable, time-seeded) — a textbook CWE-330 mechanism — but the advisory assigns no CWE at all and lists no fix commit SHA (only a fixed version number), so there is nothing verbatim to extract without guessing at the actual patch commit.); CVE-2023-24828 / GHSA-jf5c-9r77-3j5j (theonedev/onedev) (Weak/insufficiently random access-token and password-reset-token generation enabling privilege escalation to admin — mechanism matches CWE-330, but OneDev is not on GHSA/osv.dev with CWE data, no CWE is assigned in the advisory, and no fix commit SHA is published (version-only fix pointer).); CVE-2025-67504 / GHSA-76gj-pmvx-jcc6 (WBCE/WBCE_CMS) (GenerateRandomPassword() used PHP rand() instead of a CSPRNG for password-reset tokens — same insecure-RNG mechanism as this bucket's CWE-330 anchors, but the GHSA record's assigned CWEs are CWE-287/CWE-331/CWE-338, not CWE-330/327/916, and no fix commit SHA is listed (version-only). Dropped for CWE-tag mismatch plus missing commit, despite close mechanism similarity to the form-data/undici anchors.); CVE-2026-46351 / GHSA-7959-pf2v-xc4h (bigbluebutton/bigbluebutton) (Insecure session-token randomness (CWE-330 confirmed on the advisory) allowing session/account impersonation, but the advisory publishes no fix commit SHA (only a fixed version, bbb-web >=3.0.21) and repeated lookups did not surface a linkable single fix commit — nothing re-fetchable to extract a verbatim hunk from.)

## OAuth / OIDC flow flaws (auth-code reuse, PKCE downgrade, redirect_uri / client binding)  (CWE-287 / CWE-863 (flow))

Grounds cards: skills/patterns/oauth-authorization-code-single-use, skills/patterns/oauth-client-binding, skills/patterns/delegated-capability-attenuation
Bucket verdict: **THIN — 5 verbatim-verified clean IN anchors (authentik, cloudflare, pocket-id, zitadel, doorkeeper), one short of the 6-clean bar; 2 CONTESTED (better-auth, sentry) are genuine but entangled multi-file/cross-primitive fixes whose anchored hunks depend on code outside the shown diff, plus off-headline CWEs (362/288, mechanism-matched only). Dominant guard shape: a single pre-redemption conditional inserted before the token-issuing path that rejects a mismatched or downgraded grant — client_id equality (zitadel, pocket-id), PKCE-presence / verifier-consistency (authentik, cloudflare), or client-confidentiality (doorkeeper). The CONTESTED pair share a secondary shape: atomic single-use redemption (find->consume swap / distributed lock). All 7 fix commits fetched and diffed directly this session (full better-auth SHA resolved to b4bc65a007784b2eb0efb459e5fa6fd8055d3ec9).**  ·  5 IN / 2 CONTESTED / 7 dropped  ·  5 promotable signatures
Severity-corpus join: Joins the severity corpus's OAuth token-endpoint authn-bypass / broken-access-control bucket: all client-binding/PKCE-downgrade anchors score CVSS 3.1 HIGH — authentik AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:N (auth-code injection, UI:R precondition), pocket-id AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:L/A:N (cross-client, scope-changed), zitadel AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N (intercepted-code precondition -> AC:H); the two CONTESTED TOCTOU race anchors (better-auth CWE-362, sentry CWE-288) map to the corpus's single-use-race sub-bucket and sit lower (AC:H race window, token-duplication impact, ~Medium). Consistent with the corpus: 3.1 vectors solid, 4.0 thin.

- **GHSA-mrx3-gxjx-hjqj** — CWE-287 (Improper Authentication) · `goauthentik/authentik` · fixed 2023.8.7 / 2023.10.7 @ `38e04ae12720e5d81b4f7ac77997eb8d1275d31a` · **IN** (signature) · downgrade-prevention conditional (reject a code_verifier at redemption when the code was never issued a code_challenge)
  - Mechanism: PKCE downgrade: the token endpoint only entered the code_verifier<->code_challenge verification branch when the authorization code had a stored code_challenge. If an attacker induced the victim to start an authorization request with code_challenge stripped, the resulting code carried no challenge and PKCE verification was never executed, so the code could be redeemed as if PKCE was never required (defeats auth-code-injection protection).
  - Affected -> Fixed: authentik <= 2023.8.6 and 2023.10.0-2023.10.6 -> 2023.8.7 / 2023.10.7
  - Vulnerable shape (removed):
    ```
    (none removed for the guard block; the guard is appended after the existing code_challenge verification. Note: the same commit separately flips an adjacent `raise TokenError("invalid_request")` -> `raise TokenError("invalid_grant")` in the code_challenge-present branch — an error-code correction, not part of the anchored downgrade guard.)
    ```
  - Guard added (post-patch):
    ```
    +        # Token request had a code_verifier but code did not have a code challenge
    +        # Prevent downgrade
    +        if not self.authorization_code.code_challenge and self.code_verifier:
    +            raise TokenError("invalid_grant")
    ```
  - Reachability: TokenView.__post_init_code, authentik/providers/oauth2/views/token.py -- POST /application/o/token/ (authorization_code grant)
  - Verdict: IN — Fetched and diffed this session; anchored 4-line guard matches the GitHub .diff verbatim. Self-contained additive guard in a single function, CWE-287, textbook PKCE-downgrade mechanism central to this bucket. CVSS 3.1 AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:N (HIGH).
  - Source: https://api.osv.dev/v1/vulns/GHSA-mrx3-gxjx-hjqj ; https://github.com/goauthentik/authentik/commit/38e04ae12720e5d81b4f7ac77997eb8d1275d31a.diff  ·  provenance: re-verified-this-session

- **GHSA-qgp8-v765-qxx9** — CWE-287 (Improper Authentication) · `cloudflare/workers-oauth-provider` · fixed 0.0.5 @ `09a2adb2f197469e5b64e8b89c22b6687cacabc1` · **IN** (signature) · downgrade-prevention conditional guard on the token-exchange handler
  - Mechanism: PKCE downgrade (CVE-2025-4144): PKCE verification ran only when authorization recorded a code_challenge (isPkceEnabled). An attacker causing the authorization request to omit code_challenge could later present any code_verifier (or none) at redemption with no binding check executed, circumventing the PKCE protection OAuth 2.1 / MCP mandate.
  - Affected -> Fixed: @cloudflare/workers-oauth-provider < 0.0.5 -> 0.0.5
  - Vulnerable shape (removed):
    ```
    (none removed; guard inserted immediately before the existing `if (isPkceEnabled) { ... verify codeVerifier ... }` block in the token-exchange handler)
    ```
  - Guard added (post-patch):
    ```
    +    // Reject if code_verifier is provided but PKCE wasn't used in authorization
    +    if (!isPkceEnabled && codeVerifier) {
    +      return this.createErrorResponse('invalid_request', 'code_verifier provided for a flow that did not use PKCE');
    +    }
    ```
  - Reachability: OAuthProviderImpl token-exchange handler, src/oauth-provider.ts (~line 1237) -- POST /token (authorization_code grant)
  - Verdict: IN — Confirmed the collector's SHA-correction: this commit (09a2adb) contains the real guard, verbatim-matching the .diff (the rest of the commit is one added test, isolable). Self-contained conditional, CWE-287, PKCE-downgrade mechanism. Same mechanism as authentik from a distinct product.
  - Source: https://api.osv.dev/v1/vulns/GHSA-qgp8-v765-qxx9 ; https://github.com/cloudflare/workers-oauth-provider/commit/09a2adb2f197469e5b64e8b89c22b6687cacabc1.diff  ·  provenance: re-verified-this-session

- **GHSA-qh6q-598w-w6m2** — CWE-863 (Incorrect Authorization) · `pocket-id/pocket-id` · fixed v2.4.0 @ `34890235ba8c2d856e3a121fdf59fe9d627e8596` · **IN** (signature) · boolean-operator correction (permissive AND -> correct OR in a rejection predicate)
  - Mechanism: Client-binding logic bug (CVE-2026-28513): the token endpoint rejected an authorization code only when client_id mismatched AND the code was expired (&& instead of ||). A code issued to a different client_id remained redeemable as long as it hadn't expired (cross-client token exchange), and an expired code from the correct client also remained redeemable until a 24h cleanup job ran.
  - Affected -> Fixed: github.com/pocket-id/pocket-id/backend before commit 34890235 (module pseudo-version 0.0.0-20260307173642-b59e35cb59ae) -> v2.4.0
  - Vulnerable shape (removed):
    ```
    -	if authorizationCodeMetaData.ClientID != input.ClientID && authorizationCodeMetaData.ExpiresAt.ToTime().Before(time.Now()) {
    ```
  - Guard added (post-patch):
    ```
    +	if authorizationCodeMetaData.ClientID != input.ClientID || authorizationCodeMetaData.ExpiresAt.ToTime().Before(time.Now()) {
    ```
  - Reachability: OidcService.createTokenFromAuthorizationCode, backend/internal/service/oidc_service.go:407 -- OIDC token endpoint (authorization_code grant)
  - Verdict: IN — Diffed this session; the entire prod change is this single one-line &&->|| flip (@@ -404,7 +404,7 @@), verbatim-matching. Cleanest possible isolable guard, CWE-863 cross-client code redemption. CVSS 3.1 AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:L/A:N (HIGH, scope-changed).
  - Source: https://api.osv.dev/v1/vulns/GHSA-qh6q-598w-w6m2 ; https://github.com/pocket-id/pocket-id/commit/34890235ba8c2d856e3a121fdf59fe9d627e8596.diff  ·  provenance: re-verified-this-session

- **GHSA-xqxv-4jc2-x56x** — CWE-287 / CWE-863 · `zitadel/zitadel` · fixed 3.4.12 / 4.15.2 @ `0973b074b48816757c47fe732b06d2488d3d284c` · **IN** (signature) · client_id equality guard inserted before code exchange proceeds
  - Mechanism: Missing client binding (CVE-2026-55672): CodeExchange never verified that the client presenting the authorization code matched the client_id that initiated the authorization request (RFC 6749 4.1.3). An intercepted code could be redeemed under a different client_id. (Same commit also adds matching binding checks to the refresh and device-code flows.)
  - Affected -> Fixed: zitadel < 3.4.12, < 4.15.2 -> 3.4.12 / 4.15.2
  - Vulnerable shape (removed):
    ```
    (none removed; guard inserted before the existing PKCE/code-challenge check in codeExchangeV1)
    ```
  - Guard added (post-patch):
    ```
    +	if authReq.GetClientID() != client.client.ClientID {
    +		return nil, oidc.ErrInvalidClient().WithDescription("client_id does not correspond to the client_id in the authorization request")
    +	}
    ```
  - Reachability: Server.codeExchangeV1, internal/api/oidc/token_code.go (~line 62) -- POST /oauth/v2/token (authorization_code grant); companion client_id guards added to token_device.go and token_refresh.go / command layer for the other flows
  - Verdict: IN — Diffed this session. The commit is multi-file, but the ANCHORED auth-code guard (codeExchangeV1) is fully self-contained — both authReq and client are already in scope, and it does not depend on the signature/plumbing changes (those serve the separate refresh/device flows). Verbatim match, CWE-287/863 client-binding, core to this bucket. CVSS 3.1 AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N (HIGH).
  - Source: https://api.osv.dev/v1/vulns/GHSA-xqxv-4jc2-x56x ; https://github.com/zitadel/zitadel/commit/0973b074b48816757c47fe732b06d2488d3d284c.diff  ·  provenance: re-verified-this-session

- **GHSA-7w2c-w47h-789w** — CWE-287 (Improper Authentication) · `doorkeeper-gem/doorkeeper` · fixed 5.6.6 @ `313af27391d974d314c1869828ca80dc1ae2678c` · **IN** (signature) · added client-confidentiality (identity-assurance) predicate to an existing auto-approval conditional
  - Mechanism: Client-identity/binding bypass (CVE-2023-34246): Doorkeeper auto-approved a repeat authorization whenever a previously-matching token existed (matching_token?), regardless of client confidentiality. Per RFC 8252 8.6 a public client's identity cannot be assured from client_id alone, so a malicious app could skip the consent/re-auth prompt and obtain tokens by impersonating a previously-approved public client.
  - Affected -> Fixed: doorkeeper < 5.6.6 -> 5.6.6
  - Vulnerable shape (removed):
    ```
    -      if skip_authorization? || matching_token?
    ```
  - Guard added (post-patch):
    ```
    +      if skip_authorization? || (matching_token? && pre_auth.client.application.confidential?)
    ```
  - Reachability: Doorkeeper::AuthorizationsController#render_success, app/controllers/doorkeeper/authorizations_controller.rb -- GET/POST /oauth/authorize
  - Verdict: IN — Diffed this session; the sole prod change is this one-line predicate addition (rest of commit is test infra: a spec + a render_with matcher helper, isolable), verbatim match. CWE-287 client-identity-assurance for public clients; adjacent to but distinct from the token-endpoint binding cases (this one is at the authorize endpoint).
  - Source: https://api.osv.dev/v1/vulns/GHSA-7w2c-w47h-789w ; https://github.com/doorkeeper-gem/doorkeeper/commit/313af27391d974d314c1869828ca80dc1ae2678c.diff  ·  provenance: re-verified-this-session

- **GHSA-7w99-5wm4-3g79** — CWE-294 / CWE-362 / CWE-367 (mechanism-matched auth-code reuse; not the bucket's CWE-287/863 headline) · `better-auth/better-auth (@better-auth/oauth-provider)` · fixed 1.6.11 @ `b4bc65a007784b2eb0efb459e5fa6fd8055d3ec9` · **CONTESTED** (illustrative) · non-atomic find-then-delete replaced by an atomic claim-and-delete primitive (consumeVerificationValue)
  - Mechanism: Authorization-code reuse via TOCTOU (CVE-2026-53518): single-use redemption was a non-atomic findVerificationValue + deleteVerificationByIdentifier pair. Two concurrent POST /oauth2/token requests with the same code both passed the find step before either delete completed, each minting an independent access/refresh/id-token set from one single-use code (violates RFC 6749 4.1.2).
  - Affected -> Fixed: @better-auth/oauth-provider >= 1.6.0, < 1.6.11; better-auth >= 1.4.8-beta.7, < 1.6.11 -> 1.6.11
  - Vulnerable shape (removed):
    ```
    -	const verification = await ctx.context.internalAdapter.findVerificationValue(
    -		await storeToken(opts.storeTokens, code, "authorization_code"),
    -	);
    
    	if (!verification) {
    		throw new APIError("UNAUTHORIZED", {
    			error_description: "Invalid code",
    -			error: "invalid_verification",
    		});
    	}
    
    -	// Delete used code (single-use per RFC 6749 §4.1.2)
    -	await ctx.context.internalAdapter.deleteVerificationByIdentifier(
    -		await storeToken(opts.storeTokens, code, "authorization_code"),
    -	);
    ```
  - Guard added (post-patch):
    ```
    +	// Atomic single-use redemption per RFC 6749 §4.1.2. The first caller
    +	// receives the row and mints tokens; concurrent racers receive `null`
    +	// and fall through to the `invalid_grant` error path (RFC 6749 §5.2).
    +	const verification =
    +		await ctx.context.internalAdapter.consumeVerificationValue(
    +			await storeToken(opts.storeTokens, code, "authorization_code"),
    +		);
    
    	if (!verification) {
    		throw new APIError("UNAUTHORIZED", {
    			error_description: "Invalid code",
    +			error: "invalid_grant",
    		});
    	}
    ```
  - Reachability: checkVerificationValue, packages/oauth-provider/src/token.ts -- POST /oauth2/token (authorization_code grant); identical find->consume swap also applied to the oidc-provider and mcp plugins in the same commit
  - Verdict: CONTESTED — Fetched/diffed this session; anchored token.ts hunk matches verbatim and the full SHA resolves (collector's 12-char prefix correct). Downgraded to CONTESTED, not OUT: genuine fix but NOT cleanly isolable — (1) the security guarantee lives in `internalAdapter.consumeVerificationValue` (the atomic claim primitive), which is NOT present in this diff, so the shown hunk alone doesn't prove atomicity; (2) the same find->consume fix is spread across 3 plugins (oauth-provider, oidc-provider, mcp); (3) CWE is race/TOCTOU (362/367/294), mechanism-matched to 'auth-code reuse' but off the 287/863 headline. promote_signature=false pending sight of the consumeVerificationValue implementation.
  - Source: https://github.com/better-auth/better-auth/security/advisories/GHSA-7w99-5wm4-3g79 ; https://github.com/better-auth/better-auth/commit/b4bc65a007784b2eb0efb459e5fa6fd8055d3ec9.diff  ·  provenance: re-verified-this-session

- **GHSA-mgh8-h4xc-pfmj** — CWE-288 (Auth Bypass Using Alternate Path/Channel; mechanism-matched grant reuse, not the bucket's 287/863 headline) · `getsentry/sentry` · fixed 25.5.0 @ `df0af004224f9f3138651bf40ac52adf7d610869` · **CONTESTED** (illustrative) · distributed lock wrapped around validate+create-token+delete-grant to make single-use redemption atomic
  - Mechanism: Authorization-grant (ApiGrant) reuse via race (CVE-2025-53099): grant validation and deletion ran outside any lock, so two concurrent exchange requests against one single-use grant could both pass validation before either delete, yielding two independent access/refresh token pairs from one authorization.
  - Affected -> Fixed: sentry < 25.5.0 -> 25.5.0
  - Vulnerable shape (removed):
    ```
    -                self._validate()
    -                token = self._create_token()
    
    -                # Once it's exchanged it's no longer valid and should not be
    -                # exchangeable, so we delete it.
    -                self._delete_grant()
    ```
  - Guard added (post-patch):
    ```
    +                lock = locks.get(
    +                    ApiGrant.get_lock_key(self.grant.id),
    +                    duration=10,
    +                    name="api_grant",
    +                )
    +
    +                # we use a lock to prevent race conditions when creating the ApiToken
    +                # an attacker could send two requests to create an access/refresh token pair
    +                # at the same time, using the same grant, and get two different tokens
    +                with lock.acquire():
    +                    self._validate()
    +                    token = self._create_token()
    +
    +                    # Once it's exchanged it's no longer valid and should not be
    +                    # exchangeable, so we delete it.
    +                    self._delete_grant()
    ```
  - Reachability: GrantExchanger.run, src/sentry/sentry_apps/token_exchange/grant_exchanger.py -- Sentry-app OAuth token exchange; the OAuth token endpoint path (web/frontend/oauth_token.py -> ApiToken.from_grant, apitoken.py) is locked separately in the same commit, and the get_lock_key primitive is defined in apigrant.py
  - Verdict: CONTESTED — Diffed this session; anchored grant_exchanger.py hunk matches verbatim. Downgraded to CONTESTED, not OUT: genuine fix but entangled across 4 prod files — the anchored hunk references `ApiGrant.get_lock_key`, which is DEFINED in a different file (apigrant.py) in the same commit, and the actual OAuth-token-endpoint fix path is in apitoken.py::from_grant + oauth_token.py (separately locked + active-application filter), so the anchor arguably points at a secondary surface. CWE-288 (mechanism-matched grant reuse, off the 287/863 headline). promote_signature=false.
  - Source: https://github.com/getsentry/sentry/security/advisories/GHSA-mgh8-h4xc-pfmj ; https://github.com/getsentry/sentry/commit/df0af004224f9f3138651bf40ac52adf7d610869.diff  ·  provenance: re-verified-this-session

Dropped: GHSA-4v2w-2wqp-mc85 (OpenIdentityPlatform/OpenAM, CVE-2026-48717, PKCE bypass via codeVerifierEnforced-off-by-default) (Unverifiable: osv.dev lists no GIT-type fixed range and no FIX-type reference, and no matching fix commit/PR could be located in the Java/Maven OpenAM repo. Including it would require fabricating a hunk. Dropped per hard rule (no fabricated diffs).); GHSA-w8p2-r796-3vmq (authlib/authlib, CVE-2026-41479, unauthenticated open redirect via unsupported response_type) (CWE record is CWE-601 only; the vulnerable path fires before client lookup and before redirect_uri validation. Pure open-redirect, not auth-code-reuse/PKCE-downgrade/client-binding. Class mismatch with this bucket (consistent with the corpus's standing CWE-601 exclusion).); GHSA-4pc9-x2fx-p7vj (cloudflare/workers-oauth-provider, missing redirect_uri validation at authorize endpoint) (CWE-601 only; mechanism is redirect_uri not checked against the registered set at the authorize endpoint (open-redirect/phishing), not a token-endpoint client-binding or code-reuse defect. Also a same-product duplicate of the already-included GHSA-qgp8-v765-qxx9. Class mismatch, dropped.); GHSA-9h47-pqcx-hjr4 (better-auth, insecure defaults: alg=none advertised + plain PKCE accepted by default) (Legitimate PKCE-downgrade-via-insecure-default mechanism, but (a) NOT re-verified this session (no osv.dev CWE/fix-commit check performed) and (b) a distinct mechanism held out for per-product diversity — better-auth is already represented (as CONTESTED) by GHSA-7w99-5wm4-3g79, whose own patch comments reference this advisory as an in-flight follow-up on the same surface. Kept out rather than promote an unverified same-product item.); GHSA-pw9m-5jxm-xr6h (better-auth, missing client_secret check on the refresh_token grant) (Real client-authentication-bypass mechanism, but it targets the refresh_token grant, not the authorization_code flow this bucket centers on, and it is a third better-auth advisory. Out of the bucket's auth-code/PKCE/redirect_uri scope + product redundancy.); CVE-2026-28512 (pocket-id redirect_uri validation bypass via userinfo/host confusion) (Surfaced by discovery but NOT independently re-verified this session (no osv.dev CWE/fix-commit check); likely a URL-parsing/open-redirect-adjacent mechanism rather than a clean client-binding defect. Dropped rather than carry an unverified claim.); GHSA-mpwq-j3xf-7m5w (keycloak/keycloak, CVE-2023-6291, redirect_uri validation bypass via host/authority desync) (Advisory classifies as CWE-20 (Improper Input Validation) driven by a URL-decoding/authority-parsing desync between Keycloak and browsers, not a CWE-287/863 authn/authz defect. Class mismatch, dropped.)
