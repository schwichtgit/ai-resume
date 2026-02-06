from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AskMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ASK_MODE_HYBRID: _ClassVar[AskMode]
    ASK_MODE_SEM: _ClassVar[AskMode]
    ASK_MODE_LEX: _ClassVar[AskMode]
ASK_MODE_HYBRID: AskMode
ASK_MODE_SEM: AskMode
ASK_MODE_LEX: AskMode

class SearchRequest(_message.Message):
    __slots__ = ("query", "top_k", "snippet_chars", "min_relevance", "mode")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    SNIPPET_CHARS_FIELD_NUMBER: _ClassVar[int]
    MIN_RELEVANCE_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    query: str
    top_k: int
    snippet_chars: int
    min_relevance: float
    mode: AskMode
    def __init__(self, query: _Optional[str] = ..., top_k: _Optional[int] = ..., snippet_chars: _Optional[int] = ..., min_relevance: _Optional[float] = ..., mode: _Optional[_Union[AskMode, str]] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("hits", "total_hits", "took_ms")
    HITS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_HITS_FIELD_NUMBER: _ClassVar[int]
    TOOK_MS_FIELD_NUMBER: _ClassVar[int]
    hits: _containers.RepeatedCompositeFieldContainer[SearchHit]
    total_hits: int
    took_ms: int
    def __init__(self, hits: _Optional[_Iterable[_Union[SearchHit, _Mapping]]] = ..., total_hits: _Optional[int] = ..., took_ms: _Optional[int] = ...) -> None: ...

class SearchHit(_message.Message):
    __slots__ = ("title", "score", "snippet", "tags")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SNIPPET_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    title: str
    score: float
    snippet: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, title: _Optional[str] = ..., score: _Optional[float] = ..., snippet: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class AskRequest(_message.Message):
    __slots__ = ("question", "use_llm", "top_k", "filters", "start", "end", "snippet_chars", "mode", "uri", "cursor", "as_of_frame", "as_of_ts", "adaptive")
    class FiltersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    QUESTION_FIELD_NUMBER: _ClassVar[int]
    USE_LLM_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    SNIPPET_CHARS_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    URI_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    AS_OF_FRAME_FIELD_NUMBER: _ClassVar[int]
    AS_OF_TS_FIELD_NUMBER: _ClassVar[int]
    ADAPTIVE_FIELD_NUMBER: _ClassVar[int]
    question: str
    use_llm: bool
    top_k: int
    filters: _containers.ScalarMap[str, str]
    start: int
    end: int
    snippet_chars: int
    mode: AskMode
    uri: str
    cursor: str
    as_of_frame: int
    as_of_ts: int
    adaptive: bool
    def __init__(self, question: _Optional[str] = ..., use_llm: bool = ..., top_k: _Optional[int] = ..., filters: _Optional[_Mapping[str, str]] = ..., start: _Optional[int] = ..., end: _Optional[int] = ..., snippet_chars: _Optional[int] = ..., mode: _Optional[_Union[AskMode, str]] = ..., uri: _Optional[str] = ..., cursor: _Optional[str] = ..., as_of_frame: _Optional[int] = ..., as_of_ts: _Optional[int] = ..., adaptive: bool = ...) -> None: ...

class AskResponse(_message.Message):
    __slots__ = ("answer", "evidence", "stats")
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    answer: str
    evidence: _containers.RepeatedCompositeFieldContainer[SearchHit]
    stats: AskStats
    def __init__(self, answer: _Optional[str] = ..., evidence: _Optional[_Iterable[_Union[SearchHit, _Mapping]]] = ..., stats: _Optional[_Union[AskStats, _Mapping]] = ...) -> None: ...

class AskStats(_message.Message):
    __slots__ = ("candidates_retrieved", "results_returned", "retrieval_ms", "reranking_ms", "used_fallback")
    CANDIDATES_RETRIEVED_FIELD_NUMBER: _ClassVar[int]
    RESULTS_RETURNED_FIELD_NUMBER: _ClassVar[int]
    RETRIEVAL_MS_FIELD_NUMBER: _ClassVar[int]
    RERANKING_MS_FIELD_NUMBER: _ClassVar[int]
    USED_FALLBACK_FIELD_NUMBER: _ClassVar[int]
    candidates_retrieved: int
    results_returned: int
    retrieval_ms: int
    reranking_ms: int
    used_fallback: bool
    def __init__(self, candidates_retrieved: _Optional[int] = ..., results_returned: _Optional[int] = ..., retrieval_ms: _Optional[int] = ..., reranking_ms: _Optional[int] = ..., used_fallback: bool = ...) -> None: ...

class GetStateRequest(_message.Message):
    __slots__ = ("entity", "slot")
    ENTITY_FIELD_NUMBER: _ClassVar[int]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    entity: str
    slot: str
    def __init__(self, entity: _Optional[str] = ..., slot: _Optional[str] = ...) -> None: ...

class GetStateResponse(_message.Message):
    __slots__ = ("found", "entity", "slots")
    class SlotsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    FOUND_FIELD_NUMBER: _ClassVar[int]
    ENTITY_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    found: bool
    entity: str
    slots: _containers.ScalarMap[str, str]
    def __init__(self, found: bool = ..., entity: _Optional[str] = ..., slots: _Optional[_Mapping[str, str]] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ("service",)
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    service: str
    def __init__(self, service: _Optional[str] = ...) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status", "frame_count", "memvid_file")
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[HealthCheckResponse.Status]
        SERVING: _ClassVar[HealthCheckResponse.Status]
        NOT_SERVING: _ClassVar[HealthCheckResponse.Status]
    UNKNOWN: HealthCheckResponse.Status
    SERVING: HealthCheckResponse.Status
    NOT_SERVING: HealthCheckResponse.Status
    STATUS_FIELD_NUMBER: _ClassVar[int]
    FRAME_COUNT_FIELD_NUMBER: _ClassVar[int]
    MEMVID_FILE_FIELD_NUMBER: _ClassVar[int]
    status: HealthCheckResponse.Status
    frame_count: int
    memvid_file: str
    def __init__(self, status: _Optional[_Union[HealthCheckResponse.Status, str]] = ..., frame_count: _Optional[int] = ..., memvid_file: _Optional[str] = ...) -> None: ...
