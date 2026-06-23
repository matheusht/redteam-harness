# Blind recon observations — case A

You are the routing orchestrator. Below are raw recon observations from one engagement. You do NOT
have any verdicts, strengths, or expected card mappings. Derive them.

| # | Observation | Where |
| --- | --- | --- |
| 1 | a chat-read request carries an owner-id field in the query/body that differs from the authenticated session principal | chat_api request |
| 2 | two versions of the same chat endpoint (v1 and v2) are both mounted and answering | chat_api routing |
| 3 | the newer route version calls an owner-access validation helper that the older version does not | chat_api handlers |
| 4 | there is a UI model picker, but the chosen model id also travels in the request body (field `modelAi`) | model_selector / chat_api request |
| 5 | the client sends a `mandatoryTools` list in the request body | tool_dispatch / chat_api request |
| 6 | model output is rendered through a markdown / diagram (mermaid) pipeline | render_pipeline |
| 7 | a server-side model filter is applied to every request regardless of user class | model_selector |
| 8 | export/owner resolution is taken from the authenticated principal, not from a request field | chat_api export |
