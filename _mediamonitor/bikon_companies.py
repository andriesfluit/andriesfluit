"""Topic profiles for the Bikon radar: business/market/tech intelligence.

Same shape as companies.py (label / brief / patterns / search_terms), but the
"companies" here are thematic SPOREN (tracks) rather than akkanto clients. The
LLM filter judges each item for usefulness to Bikon's business or product, not
for "can the client react".

Three buckets:
  1. competitors_funding: named competitors + RegTech/AI-advisory funding
  2. ai_regulation:       EU AI Act, FSMA, NBB, DORA, GDPR+AI
  3. ai_tech_buildradar:  applicable gen-AI technique (RAG, knowledge graphs,
                          agents, evaluation) + reliability/positioning

Discipline mirrors companies.py: patterns cast a tight high-signal net over the
outlet feeds, search_terms do most of the work (each expands to a nl-BE + fr-BE
Google News exact-phrase search via feeds.search_feeds_for). Bikon's world is
more English than the akkanto clients, so terms are mixed NL/FR/EN.
"""

BIKON_COMPANIES = {
    # -----------------------------------------------------------------
    "competitors_funding": {
        "label": "Concurrenten & RegTech/AI-funding",
        "brief": (
            "Concurrenten en aangrenzende spelers van Bikon, plus funding/M&A in "
            "RegTech en AI-advies. Directe en adjacente concurrenten: Ravical "
            "(agentic automation interne processen, KMO), Sinequa (enterprise "
            "search), Warren (AI-pensioencoaching richting werkgevers), Legora en "
            "Harvey (legal AI), Henchman, Silverfin, ML6, Raccoons, AE, Eagl. "
            "Relevant: kapitaalrondes, productlanceringen, bankdeals, partnerships "
            "of overnames van deze spelers, en bredere funding-signalen bij "
            "Belgische of Europese AI/RegTech/legal-tech startups. Nut voor Bikon: "
            "concurrentiepositionering, battlecards, investor- en pitch-updates."
        ),
        "patterns": [
            r"\bRavical\b", r"\bSinequa\b", r"\bLegora\b", r"\bHarvey\s+AI\b",
            r"\bRobin\s+AI\b", r"\bLuminance\b", r"\bHenchman\b", r"\bSilverfin\b",
            r"\bML6\b", r"\bRaccoons\b", r"\bEagl\b",
            r"\bRegTech\b", r"\blegal\s*tech\b", r"\bcompliance\s+AI\b",
            r"\bAI[- ]advies\b", r"\bAI\s+advisory\b",
            r"\bkapitaalronde\b", r"\blev[ée]e\s+de\s+fonds\b",
            r"\bpre[- ]?seed\b", r"\bseed[- ]ronde\b", r"\bSeries\s+[A-C]\b",
        ],
        "search_terms": {
            "competitors": [
                "Ravical", "Sinequa", "Legora", "Harvey AI", "Henchman legal",
                "Silverfin", "ML6 AI", "Raccoons AI", "Eagl fintech",
                "Warren pensioen",
            ],
            "broad": [
                "RegTech funding", "legal AI funding",
                "AI startup kapitaalronde", "compliance AI startup",
                "AI advisory platform", "Belgische AI startup funding",
            ],
        },
    },

    # -----------------------------------------------------------------
    "ai_regulation": {
        "label": "AI-regelgeving & compliance",
        "brief": (
            "Regelgeving die Bikon's product en positionering raakt. EU AI Act "
            "(high-risk classificatie voor finance en gezondheidszorg, codes of "
            "practice, GPAI, Omnibus-vereenvoudiging, implementatietermijnen), "
            "Belgische toezichthouders (FSMA, Nationale Bank/NBB), DORA, GDPR/AVG "
            "in combinatie met AI, en transparantie-, audit- of "
            "traceerbaarheidsvereisten. Nut voor Bikon: compliance is een troef "
            "(citaties, audit trails), en deadlines zijn positionerings- of "
            "submission-kansen (bv. EU-consultaties). Wikifin/FSMA-complementariteit "
            "is relevant voor de pensioencontext."
        ),
        "patterns": [
            r"\bAI\s+Act\b", r"\bAI-verordening\b", r"\bAI-wet\b",
            r"\br[èe]glement\s+(?:sur\s+l['’])?IA\b",
            r"\bhigh[- ]risk\s+AI\b", r"\bhoog[- ]risico\b",
            r"\bcode[s]?\s+of\s+practice\b", r"\bGPAI\b",
            r"\bFSMA\b", r"\bWikifin\b", r"\bDORA\b",
            r"\bNationale\s+Bank\b", r"\bBanque\s+Nationale\b",
            r"\bGDPR\b", r"\bAVG\b", r"\btoezichthouder\b",
            r"\baudit\s+trail\b", r"\btraceerbaarheid\b",
        ],
        "search_terms": {
            "policy": [
                "EU AI Act", "AI Act high-risk", "AI Act financial services",
                "code of practice AI", "FSMA AI", "Nationale Bank AI",
                "DORA compliance", "GDPR AI", "AI verordening", "Wikifin",
            ],
            "broad": [
                "AI regulation finance", "AI compliance Belgium",
                "EU AI Act consultatie",
            ],
        },
    },

    # -----------------------------------------------------------------
    "ai_tech_buildradar": {
        "label": "Gen-AI techniek (build-radar)",
        "brief": (
            "Concrete technologische ontwikkelingen die Bikon's product sterker "
            "maken. Twee lagen. (a) Toepasbare techniek, hoog gewogen: RAG-"
            "verbeteringen (retrieval, reranking, chunking, GraphRAG, hybrid en "
            "late-interaction), knowledge graphs, structured data extraction, "
            "grounding en citations, agent-architecturen (tool use, planning, "
            "multi-agent, guardrails), domeinadaptatie en fine-tuning, embeddings, "
            "retrieval-evaluatie en benchmarking. Dit is wat Bikon kan overnemen of "
            "leren, voer voor het tech-team. (b) Betrouwbaarheid en positionering: "
            "LLM-hallucinatie, accuraatheid in gereguleerde/enterprise-context, "
            "domeinspecifieke versus generieke AI, en thought-leadership voer. "
            "Techniek die Bikon's pipeline kan verbeteren weegt minstens zo zwaar "
            "als concurrent- of regelgevingsnieuws."
        ),
        "patterns": [
            r"\bRAG\b", r"\bGraphRAG\b", r"\bretrieval[- ]augmented\b",
            r"\bknowledge\s+graph\b", r"\bkennisgraaf\b",
            r"\breranking\b", r"\bre[- ]?ranker\b",
            r"\bvector\s+(?:database|search|store)\b", r"\bembeddings?\b",
            r"\bhallucinat", r"\bgrounding\b", r"\bcitations?\b",
            r"\bagentic\b", r"\bAI\s+agents?\b", r"\bmulti[- ]agent\b",
            r"\btool\s+use\b", r"\bfine[- ]tun", r"\bguardrails?\b",
            r"\bbenchmark", r"\bdomain[- ]specific\s+(?:AI|LLM)\b",
        ],
        "search_terms": {
            "technique": [
                "GraphRAG", "agentic RAG", "retrieval augmented generation",
                "knowledge graph AI", "RAG reranking", "LLM evaluation benchmark",
                "grounded AI citations", "domain-specific LLM", "fine-tuning LLM",
                "vector database", "AI agents enterprise",
                "hybrid search retrieval", "semantic chunking", "query rewriting RAG",
                "ColBERT late interaction", "cross-encoder reranker",
                "long context LLM", "context engineering", "RAG evaluation RAGAS",
                "LLM as a judge", "structured outputs LLM", "function calling LLM",
                "multi-agent systems", "agent orchestration", "knowledge graph RAG",
                "Microsoft GraphRAG", "retrieval evaluation", "embedding model benchmark",
                "hallucination detection", "guardrails LLM", "model context protocol",
            ],
            "broad": [
                "LLM hallucination", "RAG accuracy regulated",
                "enterprise AI reliability", "RAG production",
                "AI evaluation framework", "trustworthy AI regulated",
            ],
        },
    },

}


# -----------------------------------------------------------------------
# Bikon outlet-feed catalogue. Replaces the akkanto Belgian/sector press.
# Mostly Google News site: queries (when:4d, trimmed to the real lookback by
# fetcher.py); international outlets use en-US locale for better ranking,
# Belgian ones use nl-BE / fr-BE. Note: Google News indexes news sites well
# but personal/dev blogs only patchily, so the spoor-3 search_terms above are
# the main driver for technique coverage; these blog outlets are a bonus.

def _gn(site, hl="en-US", gl="US", ceid="US:en"):
    # when:4d covers the longest gap between Bikon sends (Fri -> Mon, ~72h)
    # with margin. fetcher.py then trims to the exact lookback window, so
    # nothing older than the last send leaks in.
    return (f"https://news.google.com/rss/search?q=site:{site}+when:4d"
            f"&hl={hl}&gl={gl}&ceid={ceid}")


def _gn_be_nl(site):
    return _gn(site, hl="nl-BE", gl="BE", ceid="BE:nl")


def _gn_be_fr(site):
    return _gn(site, hl="fr-BE", gl="BE", ceid="BE:fr")


BIKON_OUTLET_FEEDS = {
    # Belgische business / tech-pers
    "detijd":      _gn_be_nl("tijd.be"),
    "lecho":       _gn_be_fr("lecho.be"),
    "trends_nl":   _gn_be_nl("trends.knack.be"),
    "trends_fr":   _gn_be_fr("trends.levif.be"),
    "datanews_nl": _gn_be_nl("datanews.knack.be"),
    "datanews_fr": _gn_be_fr("datanews.levif.be"),

    # Internationale tech/AI + Europese startup-funding + RegTech/fintech
    "techcrunch":  _gn("techcrunch.com"),
    "sifted":      _gn("sifted.eu"),
    "techeu":      _gn("tech.eu"),
    "eustartups":  _gn("eu-startups.com"),
    "finextra":    _gn("finextra.com"),
    "theregister": _gn("theregister.com"),
    "mittech":     _gn("technologyreview.com"),
    "venturebeat": _gn("venturebeat.com"),

    # EU-regelgeving / beleid
    "euractiv":    _gn("euractiv.com"),
    "politico_eu": _gn("politico.eu"),

    # Build-radar: AI-technique news (well-indexed in Google News)
    "thedecoder":    _gn("the-decoder.com"),
    "marktechpost":  _gn("marktechpost.com"),
    "venturebeat_ai": _gn("venturebeat.com/ai"),

    # Build-radar: model labs
    "huggingface":   _gn("huggingface.co"),
    "anthropic":     _gn("anthropic.com"),
    "deepmind":      _gn("deepmind.google"),
    "openai":        _gn("openai.com"),
    "googleresearch": _gn("research.google"),
    "mistral":       _gn("mistral.ai"),
    "cohere":        _gn("cohere.com"),

    # Build-radar: retrieval / RAG / vector tooling
    "langchain":     _gn("blog.langchain.dev"),
    "llamaindex":    _gn("llamaindex.ai"),
    "pinecone":      _gn("pinecone.io"),
    "weaviate":      _gn("weaviate.io"),
    "qdrant":        _gn("qdrant.tech"),
    "jina":          _gn("jina.ai"),
    "databricks":    _gn("databricks.com"),

    # Build-radar: practitioner blogs
    "simonwillison": _gn("simonwillison.net"),
    "thegradient":   _gn("thegradient.pub"),
    "raschka":       _gn("magazine.sebastianraschka.com"),
    "eugeneyan":     _gn("eugeneyan.com"),
}
