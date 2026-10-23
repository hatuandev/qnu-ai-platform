"""Contracts for source-bound, derived knowledge pages. Pages never approve facts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

WIKI_VERSION = "qnu-knowledge-wiki/v1"
WIKI_REFERENCE_MAX_CHARS = 6000
WIKI_MAX_REFERENCES = 20


class WikiContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WikiPolicy(WikiContract):
    compiler_version: Literal["qnu-wiki-compiler/v2", "qnu-wiki-compiler/v3"] = "qnu-wiki-compiler/v2"
    render_mode: Literal["generated", "extractive"] = "generated"
    enabled: bool = True
    packet_chars: int = Field(24000, ge=1000, le=48000)
    max_total_chars: int = Field(180000, ge=100, le=500000)
    max_calls: int = Field(32, ge=2, le=32)
    context_budget_tokens: int = Field(24000, ge=8000, le=32000)
    max_output_tokens: int = Field(2500, ge=1000, le=8192)
    generation_retries: int = Field(2, ge=0, le=2)
    timeout_seconds: int = Field(600, ge=10, le=600)


class WikiReference(WikiContract):
    unit_id: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=WIKI_REFERENCE_MAX_CHARS)
    literal_only: bool = Field(default=False, exclude_if=lambda value: not value)

    @model_validator(mode="after")
    def short_literal(self):
        if len(self.quote) < 3 and not self.literal_only:
            raise ValueError("Short text requires a server-bound literal inventory reference")
        return self


class WikiTemporalScope(WikiContract):
    role: Literal["data", "publication", "effective", "event"]
    years: list[int] = Field(min_length=1, max_length=20)
    references: list[WikiReference] = Field(min_length=1, max_length=WIKI_MAX_REFERENCES)


class WikiSection(WikiContract):
    heading: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=1, max_length=WIKI_REFERENCE_MAX_CHARS * WIKI_MAX_REFERENCES)
    excerpt_unit_id: str | None = Field(default=None, max_length=200, exclude_if=lambda value: value is None)
    references: list[WikiReference] = Field(min_length=1, max_length=WIKI_MAX_REFERENCES)
    temporal: list[WikiTemporalScope] = Field(default_factory=list, max_length=8)
    conditions: list[str] = Field(default_factory=list, max_length=12)
    exceptions: list[str] = Field(default_factory=list, max_length=12)


class WikiOutline(WikiContract):
    kind: Literal["source", "entity", "concept"]
    title: str = Field(min_length=1, max_length=180)
    unit_ids: list[str] = Field(min_length=1, max_length=100)


class WikiAnalysis(WikiContract):
    pages: list[WikiOutline] = Field(min_length=1, max_length=3)


class WikiPage(WikiContract):
    kind: Literal["source", "entity", "concept"]
    title: str = Field(min_length=1, max_length=180)
    sections: list[WikiSection] = Field(min_length=1, max_length=512)


class WikiGeneration(WikiContract):
    pages: list[WikiPage] = Field(min_length=1, max_length=12)


class WikiDraftTemporal(WikiContract):
    role: Literal["data", "publication", "effective", "event"]
    years: list[int] = Field(min_length=1, max_length=20)
    references: list[str] = Field(min_length=1, max_length=WIKI_MAX_REFERENCES)


class WikiSelectionOutline(WikiOutline):
    temporal: list[WikiDraftTemporal] = Field(default_factory=list, max_length=8)


class WikiSelection(WikiAnalysis):
    pages: list[WikiSelectionOutline] = Field(min_length=1, max_length=3)


class WikiDraftSection(WikiContract):
    heading: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=1, max_length=1200)
    references: list[str] = Field(min_length=1, max_length=WIKI_MAX_REFERENCES)
    temporal: list[WikiDraftTemporal] = Field(default_factory=list, max_length=8)
    conditions: list[str] = Field(default_factory=list, max_length=12)
    exceptions: list[str] = Field(default_factory=list, max_length=12)


class WikiDraftPage(WikiContract):
    kind: Literal["source", "entity", "concept"]
    title: str = Field(min_length=1, max_length=180)
    sections: list[WikiDraftSection] = Field(min_length=1, max_length=3)


class WikiPacketGeneration(WikiContract):
    pages: list[WikiDraftPage] = Field(min_length=1, max_length=3)


class WikiSectionPatch(WikiContract):
    target_id: str
    section: WikiDraftSection


class WikiPacketRepair(WikiContract):
    patches: list[WikiSectionPatch] = Field(min_length=1, max_length=9)


class WikiCandidateTemporal(WikiTemporalScope):
    references: list[WikiReference] = Field(min_length=1, max_length=100)


class WikiCandidateSection(WikiSection):
    references: list[WikiReference] = Field(min_length=1, max_length=100)
    temporal: list[WikiCandidateTemporal] = Field(default_factory=list, max_length=8)


class WikiCandidatePage(WikiPage):
    sections: list[WikiCandidateSection] = Field(min_length=1, max_length=3)


class WikiCandidateGeneration(WikiGeneration):
    """Untrusted in-memory candidate; never a stored/ready page contract."""
    pages: list[WikiCandidatePage] = Field(min_length=1, max_length=3)


class WikiDraftCandidateTemporal(WikiDraftTemporal):
    references: list[str] = Field(min_length=1, max_length=100)


class WikiDraftCandidateSection(WikiDraftSection):
    references: list[str] = Field(min_length=1, max_length=100)
    temporal: list[WikiDraftCandidateTemporal] = Field(default_factory=list, max_length=8)


class WikiDraftCandidatePage(WikiDraftPage):
    sections: list[WikiDraftCandidateSection] = Field(min_length=1, max_length=3)


class WikiPacketCandidate(WikiContract):
    """Read a bounded malformed section so it can be repaired, not accepted."""
    pages: list[WikiDraftCandidatePage] = Field(min_length=1, max_length=3)


class WikiReadAction(WikiContract):
    action: Literal["read_pages", "read_source", "search", "done"]
    page_ids: list[str] = Field(default_factory=list, max_length=3)
    unit_ids: list[str] = Field(default_factory=list, max_length=12)
    query: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "read_pages" and (not self.page_ids or self.unit_ids or self.query):
            raise ValueError("read_pages requires only page_ids")
        if self.action == "read_source" and (not self.page_ids or not self.unit_ids or self.query):
            raise ValueError("read_source requires page_ids and unit_ids")
        if self.action == "search" and (not self.query.strip() or self.page_ids or self.unit_ids):
            raise ValueError("search requires only query")
        if self.action == "done" and (self.page_ids or self.unit_ids or self.query):
            raise ValueError("done has no arguments")
        return self


class WikiReadPolicy(WikiContract):
    enabled: bool = True
    max_calls: int = Field(2, ge=1, le=4)
    max_page_chars: int = Field(14000, ge=2000, le=30000)
    timeout_seconds: float = Field(30, ge=1, le=90)
    max_link_depth: int = Field(1, ge=0, le=2)
    max_link_nodes: int = Field(3, ge=1, le=6)
    max_link_edges: int = Field(32, ge=0, le=128)
