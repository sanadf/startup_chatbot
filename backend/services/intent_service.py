"""Pure intent routing for the conversational investment chatbot."""

import re
from typing import Literal

from backend.services.smalltalk_service import arithmetic_answer

Intent = Literal[
    "research",
    "followup",
    "compare",
    "knowledge",
    "meta",
    "offtopic",
    "clarify",
]

# Questions about the assistant itself.
META_PATTERNS = [
    r"\bwhat can you (do|help)\b",
    r"\bwho are you\b",
    r"\bwhat are you\b",
    r"\bhow do(es)? (you|this|it) work\b",
    r"\bwhat do you do\b",
    r"^\s*(help|/help)\s*[?!.]*$",
    r"\byour (capabilities|features)\b",
]

# Anything outside investment sourcing.
OFFTOPIC_PATTERNS = [
    r"\bweather\b",
    r"\btell me a joke\b",
    r"\bwrite (me )?(a )?(poem|song|story|essay)\b",
    r"\b(translate|recipe|horoscope|lyrics)\b",
    r"\bwho (won|is the president|is the prime minister)\b",
    r"\bcapital of\b",
    r"\bmeaning of life\b",
    r"\bwhat('s| is) the time\b",
    r"\b(football|soccer|basketball|movie|netflix)\b",
]

GREETING_PATTERN = re.compile(
    r"^\s*(hi|hey|hello|yo|salam|salaam|assalamu alaikum|good "
    r"(morning|afternoon|evening)|how are you|thanks|thank you|ok|okay)"
    r"(\s+(there|everyone|team))?[\s,!.?]*$",
    re.IGNORECASE,
)

ARITHMETIC_PATTERN = re.compile(r"^[\d\s+\-*/=().,^%x]+\??$")

RESEARCH_PATTERNS = [
    r"\b(find|source|sourcing|discover|scan|search for|look for|looking for)\b",
    r"\b(show|give|get) me\b.*\b(startups?|companies|compan(y|ies))\b",
    r"\b(list|shortlist|pipeline|deal flow|dealflow)\b",
    r"\b(startups?|companies|ventures|founders looking)\b.*\b(in|from|across|that|which|with|raising)\b",
    r"\b(invest(ment)? thesis|i want to invest|we invest|our fund)\b",
    r"\b(series [a-d]|pre-?seed|seed stage|growth stage)\b.*\b(startups?|companies)\b",
    r"\bnew (research|search|scan)\b",
]

# Follow-up question vocabulary, mapped to report attribute names.
ATTRIBUTE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (r"\b(linkedin|linked in)\b", ("LinkedIn",)),
    (
        r"\b(ceo|founder|founders|co-?founder|cofounders|who (runs|founded|leads)|"
        r"management|leadership|executive)\b",
        ("Founders",),
    ),
    (r"\b(website|web site|url|domain|homepage)\b", ("Website",)),
    (
        r"\b(funding|raised|raise|round|valuation|capital|money)\b",
        ("Latest Funding Round", "Total Funding", "Funding Stage"),
    ),
    (r"\b(stage)\b", ("Funding Stage",)),
    (
        r"\b(revenue|arr|mrr|sales|turnover|top ?line)\b",
        ("Annual Recurring Revenue (ARR)", "Revenue"),
    ),
    (
        r"\b(employees?|headcount|head count|team size|how many people|staff)\b",
        ("Employee Count",),
    ),
    (
        r"\b(headquarters|hq|based|located|location|office)\b",
        ("Headquarters",),
    ),
    (
        r"\b(founded|established|started|how old|year)\b",
        ("Year Founded",),
    ),
    (r"\b(investors?|backers?|vcs?|cap table)\b", ("Investors",)),
    (
        r"\b(product|products|services|offering|what do they do|what does it do|"
        r"platform|tech|technology)\b",
        ("Products / Services", "Description"),
    ),
    (
        r"\b(business model|monetiz|pricing|revenue model|b2b|b2c|saas)\b",
        ("Business Model",),
    ),
    (r"\b(industry|sector|vertical|space)\b", ("Industry",)),
    (
        r"\b(countries|markets|geograph|regions?|where do they operate)\b",
        ("Operating Countries",),
    ),
    (
        r"\b(advantage|moat|differentiat|competitors?|competition|unique)\b",
        ("Competitive Advantage",),
    ),
    (r"\b(risks?|red flags?|concerns?|due diligence)\b", ()),
    (r"\b(contact|email|phone|reach out|get in touch)\b", ()),
    (r"\b(news|latest|recent|update|press)\b", ()),
    (r"\b(tell me (more )?about|who is|what is|overview|profile|summary)\b", ()),
]

# Investing and startup vocabulary the assistant can explain on its own.
GLOSSARY_PATTERN = re.compile(
    r"\b(series\s*[a-f]|pre-?seed|seed round|safe note|convertible note|"
    r"term sheet|cap table|valuation|dilution|arr|mrr|burn rate|runway|"
    r"due diligence|ebitda|bnpl|fintech|health-?tech|ed-?tech|prop-?tech|"
    r"clean-?tech|deep-?tech|saas|b2b|b2c|venture capital|vc fund|"
    r"\bvcs?\b|\blps?\b|\bgps?\b|dry powder|down round|bridge round|"
    r"\bipo\b|exit|acquisition|\btam\b|\bsam\b|\bcac\b|\bltv\b|churn|"
    r"unit economics|moat|\besop\b|vesting|cliff|pre-?money|post-?money|"
    r"deal ?flow|funding (stage|round)|angel investor|accelerator|incubator|"
    r"bootstrap|runway|traction|product market fit)\b",
    re.IGNORECASE,
)

DEFINITIONAL_PATTERN = re.compile(
    r"\b(what (is|are|does|do)|what'?s|whats|explain|define|definition of|"
    r"meaning of|difference between|how does .{0,40}work|why do|"
    r"should i|is it (normal|common|good|bad))\b",
    re.IGNORECASE,
)

COMPARE_PATTERNS = [
    r"\b(compare|comparison|versus|\bvs\b|which (one|of them|is better)|"
    r"rank|best (one|option|fit)|top (pick|choice)|side by side)\b",
    r"\b(all of them|each (of them|company)|across the (companies|startups))\b",
]

ORDINAL_WORDS = {
    "first": 0, "1st": 0, "one": 0, "number one": 0,
    "second": 1, "2nd": 1, "two": 1, "number two": 1,
    "third": 2, "3rd": 2, "three": 2,
    "fourth": 3, "4th": 3, "four": 3,
    "fifth": 4, "5th": 4, "five": 4,
}

PRONOUN_PATTERN = re.compile(
    r"\b(it|its|it's|they|their|them|theirs|this (company|startup|one)|"
    r"that (company|startup|one)|the company|the startup|he|she|his|her)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "a", "an", "inc", "llc", "ltd", "co", "company", "technologies",
    "technology", "labs", "group", "holdings", "corp", "and", "of", "for",
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.casefold())


def _significant_words(name: str) -> list[str]:
    return [
        word
        for word in _normalize(name).split()
        if word and word not in STOPWORDS and len(word) > 2
    ]


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def resolve_company(message: str, company_names: list[str]) -> str | None:
    """Find which researched company a message refers to, if any."""
    if not company_names:
        return None

    normalized = f" {_normalize(message)} "

    # Exact or near-exact name mention wins, longest name first.
    for name in sorted(company_names, key=len, reverse=True):
        candidate = _normalize(name).strip()
        if candidate and (
            f" {candidate} " in normalized or f" {candidate}s " in normalized
        ):
            return name

    # Every distinctive word of the name appears in the message.
    for name in sorted(company_names, key=len, reverse=True):
        words = _significant_words(name)
        if words and all(f" {word} " in normalized for word in words):
            return name

    # Positional reference: "the second one", "#3".
    numbered = re.search(r"#\s*(\d+)|\bnumber\s+(\d+)\b", message)
    if numbered:
        index = int(next(group for group in numbered.groups() if group)) - 1
        if 0 <= index < len(company_names):
            return company_names[index]

    # Longest phrase first, so "the second one" is not read as "one".
    for word, index in sorted(
        ORDINAL_WORDS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if re.search(rf"\b{re.escape(word)}\b", message, re.IGNORECASE):
            if index < len(company_names):
                return company_names[index]

    return None


def requested_attributes(message: str) -> list[str]:
    """Report attribute names a follow-up question is asking about."""
    names: list[str] = []
    for pattern, attributes in ATTRIBUTE_KEYWORDS:
        if re.search(pattern, message, re.IGNORECASE):
            for attribute in attributes:
                if attribute not in names:
                    names.append(attribute)
    return names


def asks_about_company_detail(message: str) -> bool:
    return any(
        re.search(pattern, message, re.IGNORECASE)
        for pattern, _ in ATTRIBUTE_KEYWORDS
    )


def classify(message: str, company_names: list[str] | None = None) -> tuple[Intent, str | None]:
    """Route one chat message to an intent and, when relevant, a company."""
    company_names = company_names or []
    text = message.strip()

    if len(text) < 2:
        return "clarify", None

    if GREETING_PATTERN.match(text):
        return "meta", None

    if _matches_any(META_PATTERNS, text):
        return "meta", None

    if (
        ARITHMETIC_PATTERN.match(text)
        or arithmetic_answer(text) is not None
        or _matches_any(OFFTOPIC_PATTERNS, text)
    ):
        return "offtopic", None

    company = resolve_company(text, company_names)

    # An explicit research ask always starts a new scan, even if it names
    # a sector that happens to overlap with an earlier result.
    research_ask = _matches_any(RESEARCH_PATTERNS, text)
    if research_ask and not company:
        return "research", None

    # A general question about investing terminology, not about a company.
    refers_to_context = bool(company_names) and bool(PRONOUN_PATTERN.search(text))

    if (
        not company
        and not refers_to_context
        and DEFINITIONAL_PATTERN.search(text)
        and GLOSSARY_PATTERN.search(text)
    ):
        return "knowledge", None

    if company_names and _matches_any(COMPARE_PATTERNS, text):
        return "compare", None

    if company:
        return "followup", company

    if company_names and (
        asks_about_company_detail(text) or PRONOUN_PATTERN.search(text)
    ):
        return "followup", None

    if research_ask:
        return "research", None

    # Sector + geography phrasing without an explicit verb is still sourcing.
    if len(text.split()) >= 4 and re.search(
        r"\b(startups?|companies|fintech|healthtech|saas|ai|edtech|logistics|"
        r"e-?commerce|proptech|cleantech|biotech|marketplace)\b",
        text,
        re.IGNORECASE,
    ):
        return "research", None

    return "clarify", None
