"""Per-host base URLs and shared transport defaults.

Overridable via ``api_base``/``kg_base``/``llm_base``/``nlp_base`` on the client
constructors; the older per-endpoint ``*_url`` options still win over these when set.
"""

API_BASE = "https://api.diffbot.com"
KG_BASE = "https://kg.diffbot.com"
LLM_BASE = "https://llm.diffbot.com"
NLP_HOST_BASE = "https://nl.diffbot.com"

DEFAULT_TIMEOUT = 30.0
