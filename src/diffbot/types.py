"""Additive type aliases for existing SDK surfaces.

These are structural overlays over the plain ``dict``/``str`` values the SDK already
accepts and returns — no parsing or validation changes at runtime. ``TypedDict``
members are ``total=False`` where the wire shape genuinely allows a field to be
absent, so a server response missing a field never breaks a type-checked caller.
"""

from typing import Any, Dict, List, Literal, Mapping, Sequence, TypedDict, Union


#: Roles accepted by the Diffbot LLM RAG endpoint's chat messages.
ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    role: ChatRole
    content: str


#: `response_format` types accepted by :func:`diffbot.ask.ask`/`ask_json`.
ResponseFormatType = Literal["text", "json_object", "json_schema"]


class JsonSchemaSpec(TypedDict, total=False):
    name: str
    schema: Dict[str, Any]


class ResponseFormat(TypedDict, total=False):
    type: ResponseFormatType
    json_schema: JsonSchemaSpec


#: DQL / Enhance-bulk export formats.
ExportFormat = Literal["json", "jsonl", "csv", "xls", "xlsx"]

#: DQL ``type``: ``crawl`` searches your crawl collections (see ``col``).
DqlType = Literal["query", "text", "queryTextFallback", "crawl"]

#: DQL ``jsonmode``: ``extended`` adds origin info for facts, ``id`` returns only ids and origins.
DqlJsonMode = Literal["extended", "id"]

#: DQL ``cluster`` (Article queries only).
DqlCluster = Literal["all", "best", "dedupe"]


class DqlOptions(TypedDict, total=False):
    """Named DQL options sent in the POST JSON body (keyword-only on ``dql()``).

    ``report`` and ``view`` are deliberately not named; pass them through ``extra``.
    """

    type: DqlType
    col: str
    filter_exclude: str
    exportseparator: str
    exportfile: str
    jsonmode: DqlJsonMode
    non_canonical_facts: bool
    no_dedup_articles: bool
    cluster: DqlCluster


#: How much of each page's matching content `web_search` returns.
SnippetLength = Literal["short", "medium", "long", "full"]

#: Documented crawl/bulk job status codes (``docs__crawl__manage.md``):
#: 0 initializing, 6 paused, 7 in progress, 8 admin-paused, 9 complete.
CrawlJobStatusCode = Literal[0, 6, 7, 8, 9]


# ---------------------------------------------------------------------------
# Response shapes (type-level only)
#
# Every response type is a ``TypedDict(total=False)`` overlay over the plain dict the
# SDK has always returned: nothing is parsed, copied or validated at runtime, and a
# field the server omits is simply absent. Shapes mirror the TypeScript SDK's facades.
# Sources: the OpenAPI specs (DQL, web search, NL, account); Extract, Crawl and Ask are
# undocumented/example-only, so those members are weaker evidence and may lag the
# server. If you index a key not declared here, ``typing.cast(Dict[str, Any], resp)``
# is the escape hatch.
# ---------------------------------------------------------------------------

# ---- DQL (kg.diffbot.com/kg/v3/dql) ----


class DqlEntity(TypedDict, total=False):
    score: float
    entity: Dict[str, Any]
    entity_ctx: Dict[str, Any]
    errors: List[str]
    callbackQuery: str
    upperBound: float
    lowerBound: float
    count: int
    value: str
    uri: str


class DqlRewrite(TypedDict, total=False):
    query: str
    reason: str


class DqlResponse(TypedDict, total=False):
    version: int
    hits: int
    results: int
    kgversion: str
    diffbot_type: str
    facet: bool
    data: List[DqlEntity]
    rewrites: List[DqlRewrite]
    textFallback: bool
    reportId: str


# ---- Web search (llm.diffbot.com/api/v1/web_search) ----


class WebSearchResult(TypedDict, total=False):
    score: float
    pageUrl: str
    title: str
    content: str
    date: str


class WebSearchResponse(TypedDict, total=False):
    query: List[str]
    search_results: List[WebSearchResult]
    timeMs: float


# ---- Natural language (nl.diffbot.com/v1) ----


class NlpMention(TypedDict, total=False):
    text: str
    beginOffset: int
    endOffset: int
    isPronoun: bool
    confidence: float


class NlpEntityType(TypedDict, total=False):
    name: str
    diffbotUri: str
    dbpediaUri: str


class NlpLocation(TypedDict, total=False):
    latitude: float
    longitude: float
    precision: float


class NlpEntity(TypedDict, total=False):
    name: str
    diffbotUri: str
    confidence: float
    salience: float
    sentiment: float
    allUris: List[str]
    allTypes: List[NlpEntityType]
    mentions: List[NlpMention]
    location: NlpLocation


class EntitiesResponse(TypedDict, total=False):
    """What :meth:`Diffbot.entities` returns (``entities`` + ``sentiment``)."""

    entities: List[NlpEntity]
    sentiment: float


#: Fields ``nlp()`` can request (``fields`` query param of the NL endpoint).
NlpField = Literal["entities", "sentiment", "facts", "records", "categories", "sentences", "language", "summary"]

#: ``format`` of the submitted document.
NlpFormat = Literal["plain text", "plain text with title"]


class NlpCustomSummary(TypedDict, total=False):
    """Summary generation options (wire: ``customSummary.maxNumberOfSentences``)."""

    max_number_of_sentences: int


class NlpResponse(TypedDict, total=False):
    """What :meth:`Diffbot.nlp` returns: any of the requested ``fields`` may be present.

    Only the ones with a documented shape here are typed in detail; the rest are
    left loose (``Any``) because the spec examples are the only source.
    """

    entities: List[NlpEntity]
    sentiment: float
    facts: List[Any]
    records: List[Any]
    categories: List[Any]
    sentences: List[Any]
    language: str
    summary: str


# ---- Extract (api.diffbot.com/v3/{api}) ----

#: Built-in Extract APIs; any other string is a Custom API name.
ExtractApi = Literal["analyze", "article", "product", "discussion", "job", "image", "video", "list", "event"]


class ExtractObject(TypedDict, total=False):
    """Fields common to every extracted object (also what a Custom API returns)."""

    type: str
    title: str
    pageUrl: str
    diffbotUri: str


class ArticleTag(TypedDict, total=False):
    label: str
    score: float


class ArticleObject(ExtractObject, total=False):
    text: str
    html: str
    author: str
    date: str
    tags: List[ArticleTag]


class ProductObject(ExtractObject, total=False):
    offerPrice: str
    regularPrice: str
    availability: bool
    productId: str


class DiscussionObject(ExtractObject, total=False):
    text: str
    posts: List[Dict[str, Any]]


class JobObject(ExtractObject, total=False):
    pass


class ImageObject(ExtractObject, total=False):
    naturalHeight: int
    naturalWidth: int


class VideoObject(ExtractObject, total=False):
    duration: float


class ListObject(ExtractObject, total=False):
    items: List[Dict[str, Any]]


class EventObject(ExtractObject, total=False):
    startDate: str
    endDate: str


# TypedDict cannot be generic on Python 3.9, so each API gets its own response type
# (the object list is the only thing that differs).
class ExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[ExtractObject]
    humanLanguage: str
    errorCode: int
    error: str


class ArticleExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[ArticleObject]
    humanLanguage: str
    errorCode: int
    error: str


class ProductExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[ProductObject]
    humanLanguage: str
    errorCode: int
    error: str


class DiscussionExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[DiscussionObject]
    humanLanguage: str
    errorCode: int
    error: str


class JobExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[JobObject]
    humanLanguage: str
    errorCode: int
    error: str


class ImageExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[ImageObject]
    humanLanguage: str
    errorCode: int
    error: str


class VideoExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[VideoObject]
    humanLanguage: str
    errorCode: int
    error: str


class ListExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[ListObject]
    humanLanguage: str
    errorCode: int
    error: str


class EventExtractResponse(TypedDict, total=False):
    request: Dict[str, Any]
    objects: List[EventObject]
    humanLanguage: str
    errorCode: int
    error: str


# Per-API ``fields=`` values (``extract.json``). ``links``/``extlinks``/``meta``/
# ``querystring``/``breadcrumb`` are common to all of them.
_CommonField = Literal["links", "extlinks", "meta", "querystring", "breadcrumb"]
AnalyzeField = _CommonField
ArticleField = Literal["links", "extlinks", "meta", "querystring", "breadcrumb", "quotes"]
ProductField = _CommonField
DiscussionField = Literal["links", "extlinks", "meta", "querystring", "breadcrumb", "sentiment"]
JobField = _CommonField
ImageField = Literal["links", "extlinks", "meta", "querystring", "breadcrumb", "displayHeight", "displayWidth"]
VideoField = _CommonField
ListField = _CommonField
EventField = _CommonField
#: Custom API names get the common set.
CustomField = _CommonField

#: ``mode=`` for Analyze: restrict to one Extract API, or ``llm`` for markdown output.
ExtractMode = Literal["article", "product", "discussion", "image", "video", "list", "event", "llm"]
#: ``naturalLanguage=`` fields accepted by Article extract.
NaturalLanguageField = Literal[
    "entities", "sentiment", "summary", "facts", "openFacts", "records", "categories", "sentences", "language"
]
#: ``useProxy=``: Diffbot's datacenter proxy, or explicitly none.
UseProxy = Literal["default", "none"]


#: ``fallback=`` for Analyze: the API to use when a page classifies as ``other``.
ExtractFallback = Literal["article", "product", "discussion", "image", "video", "list", "event"]


# Keyword options of ``extract()`` per API, used as ``**options: Unpack[...]`` in the
# client overloads (type-level only). ``timeout`` is the server-side fetch timeout in
# milliseconds; the transport timeout is raised to at least ``timeout + 10s``.
# ``proxy``/``proxyAuth`` are deliberately not named: pass them through ``extra``.
class _ExtractCommonOptions(TypedDict, total=False):
    timeout: int
    use_proxy: UseProxy
    extra: Mapping[str, Any]


class AnalyzeExtractOptions(_ExtractCommonOptions, total=False):
    mode: ExtractMode
    fallback: ExtractFallback
    fields: Sequence[AnalyzeField]
    discussion: bool


class ArticleExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[ArticleField]
    paging: bool
    max_tags: int
    tag_confidence: float
    category_confidence: float
    discussion: bool
    natural_language: Sequence[NaturalLanguageField]
    summary_num_sentences: int


class ProductExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[ProductField]
    discussion: bool


class DiscussionExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[DiscussionField]
    paging: bool
    max_pages: Union[int, Literal["all"]]


class JobExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[JobField]


class ImageExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[ImageField]


class VideoExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[VideoField]


class ListExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[ListField]


class EventExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[EventField]


class CustomExtractOptions(_ExtractCommonOptions, total=False):
    fields: Sequence[CustomField]


# ---- Crawl (api.diffbot.com/v3/crawl) ----


class CrawlJobStatus(TypedDict, total=False):
    status: int
    message: str


class CrawlJob(TypedDict, total=False):
    """A crawler job record (``crawl_get_job`` returns ``{}`` for a missing job)."""

    name: str
    jobStatus: CrawlJobStatus
    type: str
    seeds: List[str]
    roundsCompleted: int
    pageCrawlAttempts: int
    pageCrawlSuccesses: int
    pageCrawlSuccessesThisRound: int
    pagesInQueue: int
    downloadJson: str
    downloadUrls: str


class CrawlDataRecord(ExtractObject, total=False):
    """One extracted record from ``crawl_download(..., format="json")``."""

    text: str
    html: str


#: ``crawl_download`` formats.
CrawlDownloadFormat = Literal["json", "csv"]


# ---- Account (api.diffbot.com/v4/account) ----


class AccountUsage(TypedDict, total=False):
    date: str
    nlp: int
    credits: int
    extractions: int
    proxies: int
    entities: int
    refresh: int
    facets: int
    videos: int
    subtitles: int


class AccountResponse(TypedDict, total=False):
    """``token`` and ``childTokens`` are secrets: never log or print this whole dict."""

    name: str
    email: str
    plan: str
    planCredits: int
    status: str
    created: str
    token: str
    childTokens: List[str]
    usage: List[AccountUsage]


# ---- Ask / RAG (llm.diffbot.com/rag/v1/chat/completions, undocumented) ----


class AskDelta(TypedDict, total=False):
    content: str


class AskChoice(TypedDict, total=False):
    delta: AskDelta


class AskChunk(TypedDict, total=False):
    """One parsed SSE chunk of the streaming chat completion."""

    choices: List[AskChoice]
