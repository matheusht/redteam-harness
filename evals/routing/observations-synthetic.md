# Blind recon observations — case B

You are the routing orchestrator. Below are raw recon observations from one engagement. You do NOT
have any verdicts, strengths, or expected card mappings. Derive them.

| # | Observation | Where |
| --- | --- | --- |
| 1 | an owner-id field is present in the chat-read request body | chat_api request |
| 2 | two route versions (v1 and v2) exist for the same resource | chat_api routing |
| 3 | a UI-restricted model id travels in the request body | model_selector / chat_api request |
| 4 | model output is rendered through a markdown / diagram pipeline | render_pipeline |
