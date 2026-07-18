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
Bucket verdict: **THIN -- 5 clean IN anchors (below the >=6 threshold) plus 1 CONTESTED (jsPDF: genuine gate entangled with a this-binding/use-strict refactor). Dominant guard shape: canonicalization -- absolutize / URL-decode / normalize / sanitize the attacker path BEFORE a containment prefix-check (nuclei filepath.Abs, Ghost decode+normalize, openemr check_file_dir_name), with a bound-containment variant (tar-fs inCwd startsWith) and a denylist->safe-API variant (hexo Page-model lookup, jsPDF permission/allowlist gate).**  ·  5 IN / 1 CONTESTED / 8 dropped  ·  5 promotable signatures
Severity-corpus join: Feeds the severity-corpus path-traversal/LFI bucket (CWE-22/23/98): arbitrary file read/write fixes whose real CVSS spans unauth network reads (Ghost GHSA-wf7x-fh6w-34r6 ~7.5, AV:N/PR:N/S:U) through authn-scoped local reads (OpenEMR CVE-2025-29789, CVSS 4.0 PR:H/UI:A) and untrusted-archive link-traversal write (tar-fs CVE-2024-12905) -- same bug class as the corpus CWE-22 bucket, so these six join it directly for the severity vector.

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
