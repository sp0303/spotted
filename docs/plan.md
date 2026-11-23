# AI Search & Business Visibility Intelligence — Product Research & Plan

## 1. Product idea

A self-service tool that helps an SMB understand whether its business is discovered, mentioned, recommended, and represented accurately across traditional search engines, maps, and AI-powered search experiences.

The user enters their website URL. The system extracts and validates the business profile, locations, services, categories, and target markets. It then creates realistic customer-search prompts, runs a controlled set of searches and AI queries, captures evidence, compares competitors, and produces an actionable visibility report.

**Core question the product answers:**

> When a potential customer in the business's target market asks a search engine or AI assistant for a business like this, does this business appear—and if not, who appears instead, what sources influence the answer, and what can the business improve?

This is not merely a website summarizer or an AI-generated SEO score.

---

## 2. User journey

### Step 1 — Website input

User submits a URL.

### Step 2 — Business profile extraction

Extract, infer, and allow user confirmation of:

- Business / brand name
- Website domain
- Business category and subcategories
- Products and services
- Physical locations
- Service areas
- Address(es)
- Contact information
- Business hours (where available)
- Target customer
- Unique differentiators
- Relevant languages
- Existing business profiles / listings
- Competitors (suggested, editable)

Clearly distinguish information **extracted from the website** from information **inferred** or **confirmed by the user**. Do not silently assume service areas.

### Step 3 — Confirm the target market

The business owner should confirm where they want customers to find them.

For each location/service area:

- Country
- State / region
- City
- Neighborhood / postcode, if relevant
- Language
- Whether the business serves that area
- Priority / importance

A US florist should not be evaluated against Indian search results unless the user specifically wants that market.

### Step 4 — Generate customer-style prompts

Generate prompts based on the business, category, location, services, and intent. The user can review, edit, add, remove, and prioritize prompts.

### Step 5 — Choose measurement method / audit configuration

Configure platforms, query set, locations, search conditions, repetitions, and whether the test uses official APIs, consumer applications, or both.

### Step 6 — Run tests

Run controlled tests across search, maps, and AI platforms. Save raw evidence and configuration.

### Step 7 — Report

Present findings with evidence, screenshots, response excerpts, citations, competitor comparisons, limitations, and recommendations.

### Step 8 — Track over time

Allow repeat audits using the same prompts, markets, platforms, and settings to compare results.

---

## 3. What should be tested / measured?

### A. Traditional search visibility

For relevant customer queries:

- Google Search result page
- Bing Search result page
- Organic ranking / position
- Business website presence
- Competitor domains appearing
- Search features / AI-generated summaries where present
- Query intent and localization
- Date/time of capture
- Screenshot and result URL where permitted

Potential query groups:

1. Category: “florists in Dallas”
2. Service: “same-day flower delivery Dallas”
3. Problem / occasion: “flowers for funeral in Dallas”
4. Budget: “affordable wedding florist Dallas”
5. Comparison: “best florist near Uptown Dallas”
6. Branded: “Acme Flowers Dallas”
7. Neighborhood: “florist near [neighborhood]”

### B. Google Maps / local pack visibility

For applicable local businesses:

- Google Maps / Google Business Profile search results
- Local pack results in Search
- Business listing name
- Position within sampled results
- Rating and review count, if shown
- Category
- Address / service area
- Hours / availability
- Website / phone links
- Competitors appearing
- Search location and query
- Screenshot / evidence

Do not treat a single Maps result snapshot as a stable rank. Results may vary by location, query, account, time, and personalization.

### C. AI answer visibility

Potential platforms to investigate and support:

- ChatGPT Search
- Google AI Overviews / AI Mode
- Gemini
- Claude (where search is available)
- Perplexity
- Microsoft Copilot
- Other platforms based on demand and reliable access

For each query and platform, record:

- Exact prompt
- Exact response
- Brand mentioned? (yes/no)
- Mention type: explicit, indirect, or absent
- Recommended / merely mentioned?
- Recommendation position, where a list/order is identifiable
- Competitors mentioned
- Context of mention
- Sentiment / descriptive framing (with evidence)
- Business facts asserted
- Incorrect, outdated, or unsupported facts
- Source citations / links
- Whether the business's own website was cited
- Source domains cited
- Search/retrieval appeared to occur?
- Platform / model / mode
- Date and time
- Geographic and session configuration
- Screenshot (where applicable)

### D. Citation / source intelligence

Analyze sources that appear in AI answers and search results:

- Which domains are cited?
- Which local directories appear?
- Which review platforms appear?
- Which publishers / news sites appear?
- Which competitor websites appear?
- Is the business's own domain cited?
- Are competitors represented by third-party sources absent for this business?
- Which sources appear repeatedly across relevant prompts?
- Are source pages accurate and relevant?

Do not claim a source caused an AI recommendation unless evidence supports that conclusion. Report observed association, not causal certainty.

### E. Competitor intelligence

For each prompt, identify:

- Businesses recommended / mentioned
- Their order, if discernible
- Frequency across prompts and repetitions
- Geographic relevance
- Citations associated with their mentions
- Categories and services AI attributes to them
- Competitor overlap across platforms

### F. Brand / entity accuracy

Check whether AI and search platforms correctly understand:

- Business name
- Location
- Service area
- Category
- Services
- Hours
- Phone / contact
- Website
- Business identity (possible confusion with similarly named businesses)
- Key differentiators

---

## 4. Prompt taxonomy

Prompts should represent actual customer intent, not just branded questions.

### Discovery / category
- “Who are the best [category] in [city]?”
- “Recommend [category] businesses in [city].”
- “Top-rated [category] near [neighborhood].”

### Service-specific
- “Who offers [specific service] in [city]?”
- “Best company for [service] in [location].”

### Problem / need
- “I need [customer problem] solved in [location]. Who should I contact?”
- “Which business can help me with [problem]?”

### Budget / price
- “Affordable [category] in [city].”
- “Who provides [service] within [budget] in [city]?”

### Attributes / differentiators
- “Which [category] offers [attribute] in [location]?”
- “Recommend a [category] with [specific requirement].”

### Comparison
- “Compare [business] with other [category] companies in [city].”
- “Which business is best for [specific customer type / need]?”

### Neighborhood / proximity
- “Best [category] near [neighborhood / postcode].”
- “Who serves [specific area]?”

### Branded
- “What is [business] and what services does it offer?”
- “Is [business] a good option for [service]?”
- “What do customers say about [business]?”

### Accuracy / diagnostic
- Ask about location, services, hours, contact, and differentiators to detect incorrect or missing information.

Prompt sets should be business-specific, editable, and versioned. Avoid excessive duplicate prompts.

---

## 5. Geographic and personalization research — unresolved key question

A central technical research question is:

> What environment most accurately reproduces the AI/search results experienced by a real potential customer in the target market?

Do not assume that explicit prompt location, IP location, account location, browser location, cookies, or search provider settings have the same effect across platforms.

### Variables to investigate

- Explicit city / state / country in prompt
- IP geolocation: country, region, city
- Residential IP vs datacenter IP
- VPN vs proxy
- Browser geolocation permission
- Account country / location settings
- Logged-in vs logged-out
- Cookies / session state
- Search history and personalization
- Conversation history
- Browser language / locale
- Timezone
- Device / mobile vs desktop
- Search provider and geographic configuration
- Search-enabled vs non-search mode
- Platform / model / mode
- Prompt wording
- Time / freshness
- Repeated-run variance
- Platform caching or retrieval behavior (where observable)

### Hypotheses to test

1. Explicit city in prompt may be enough for some platforms.
2. IP location may affect some retrieval systems and consumer experiences.
3. API location parameters may reproduce some location context but may not match consumer apps.
4. Browser location, account settings, and IP may conflict.
5. Residential proxies may offer more realistic geographic context than datacenter IPs, but this must be tested—not assumed.
6. VPNs may provide country-level context but may not be sufficient for reliable city-level testing.
7. Results may vary between repeated runs even with the same configuration.
8. Consumer application results and API results may differ.
9. A business's service area should determine test locations; its website address alone should not.

### Proposed controlled experiment

Choose a test SMB and a target market (example: florist in Dallas, Texas).

Run a small factorial experiment:

| Test | IP / network | Prompt location | Browser locale / timezone | Session |
|---|---|---|---|---|
| A | India | Explicit Dallas | en-IN / India | Fresh |
| B | US | Explicit Dallas | en-US / Dallas | Fresh |
| C | US | “Near me” | en-US / Dallas | Fresh |
| D | India | “Near me” | en-IN / India | Fresh |
| E | US | Explicit Dallas | en-US / Dallas | Logged-in / controlled account |
| F | US | Explicit Dallas | en-US / Dallas | Repeat run |

Run the same prompt and platform where possible. Record response, mentions, citations, competitors, and screenshots. Repeat enough times to observe variance.

This is an experiment design, not a claim that every platform exposes or respects all these variables.

---

## 6. APIs vs consumer applications vs proxies

### Option A — Official / provider APIs

Investigate whether APIs offer:

- Web search
- User location context
- Search grounding
- Citations / source URLs
- Structured output
- Search configuration
- Reproducibility
- Cost controls

Advantages:
- More scalable
- Easier automation
- Stable interfaces relative to UI automation
- May support explicit location context
- Easier to record parameters

Limitations:
- API responses may not match consumer apps
- API model / search mode may differ
- Personalization may not be replicated
- Search retrieval can still be opaque

### Option B — Consumer web applications

Test actual ChatGPT, Gemini, Claude, Perplexity, Copilot, and relevant Google/Bing experiences.

Advantages:
- Closer to the actual consumer product experience
- Can inspect UI-specific search behavior and citations
- Can capture screenshots

Limitations:
- Automation fragility
- Login / account-state complexity
- CAPTCHA / bot controls
- UI changes
- Harder to scale and repeat
- Terms and access constraints must be reviewed

### Option C — Geographic proxy / VPN / residential IP

Investigate only after the controlled experiment shows geographic network location matters for a platform and testing method.

Questions:
- Is country-level location enough?
- Is city-level targeting required?
- Does residential IP materially change results?
- Does the platform accept or ignore the IP location?
- Does proxy location conflict with account/browser location?
- Is provider usage compliant with platform terms?
- What is cost per query / audit?
- Can the location be validated independently?
- What is the failure / blocked-query rate?

Do not assume residential proxies are automatically necessary or automatically better.

### Recommended research stance

Evaluate each platform independently. A single universal collection method may not be accurate across all platforms.

Potentially use a hybrid methodology:
- API-based tests for scale and structured monitoring
- Consumer-app spot checks for validation
- Geographic proxy testing only where evidence justifies it

Label the methodology clearly in reports.

---

## 7. Screenshots and evidence

The report should provide visual evidence, but screenshots are supporting evidence—not the underlying dataset.

Potential evidence:

- Google Search screenshot
- Google Maps screenshot
- Bing Search screenshot
- AI answer screenshot
- Exact response text
- Citations / URLs
- Query and geographic configuration
- Timestamp
- Platform / mode
- Method used (API, consumer app, etc.)

Store structured data first, then attach screenshot references. Screenshots should be captured only through approved and reliable collection methods.

---

## 8. Report layout / UX concept

### Overview

- Audit date
- Business profile
- Target locations / markets
- Platforms tested
- Number of prompts and runs
- Collection method and limitations

### Visibility summary

Possible metrics—define methodology before displaying:

- Mention rate
- Recommendation rate
- Citation rate
- First recommendation / position rate (only where meaningful)
- Competitor mention rate
- Brand website citation rate
- Accuracy / factual consistency findings

Avoid a single opaque “AI score” until there is a defensible methodology.

### Platform results

For each platform:

- Prompt
- Response
- Mention status
- Recommendation status
- Competitors
- Citations
- Screenshot
- Location / session configuration

### Search & Maps

- Google Search result evidence
- Bing Search result evidence
- Maps / local results evidence
- Business listing completeness
- Relevant competitors

### Competitor landscape

- Frequently mentioned competitors
- Queries where competitors appear but the client does not
- Competitor sources / citations
- Comparison across platforms and locations

### Citation / digital presence gaps

- Missing / weak directory presence
- Review-source gaps
- Publisher / press mentions
- Website content gaps
- Local landing-page gaps
- Inconsistent business information
- Structured data / entity clarity

### Recommendations

Every recommendation should contain:

- Finding
- Evidence
- Why it may matter
- Specific action
- Priority
- Confidence / limitation
- Relevant tool or workflow to fix it (if the product has one)

Avoid generic recommendations such as “improve SEO” without evidence.

---

## 9. Revisible competitor reference

Reference: https://www.revisible.com/in/services/ai-visibility/

The page positions AI visibility as part of a broader service combining:

- AEO
- GEO
- Google AI Overview optimization
- Voice search
- Google Business Profile
- Content
- Reviews
- Directory / NAP listings
- Authority building
- AI visibility monitoring and reporting

Its free audit page describes:
- Live prompt results
- Exact AI responses
- Competitor visibility
- Visibility scorecard
- Specific fixes / prioritized recommendations

Research questions for competitor teardown:

- What platforms does it test?
- Does it expose exact prompts?
- Does it expose raw answers?
- Does it show screenshots?
- Does it show citations?
- How does it measure visibility?
- Does it test geographic context?
- Does it disclose API vs consumer-app methodology?
- How does it identify competitors?
- What does its report look like?
- What is free vs paid?
- How does it convert audit users to ongoing monitoring?

Competitor pages are positioning evidence, not proof of technical methodology or result accuracy.

---

## 10. Other products to investigate

Research the following product categories and companies:

- Profound — enterprise AI visibility analytics
- Otterly.AI — AI search monitoring
- Peec AI — AI visibility analytics / share of voice
- Scrunch — AI search / agent-facing website optimization
- Ahrefs Brand Radar — brand visibility research
- Semrush AI Visibility — integration with traditional SEO
- Rankscale — AI visibility monitoring / GEO audit
- AthenaHQ — AI visibility analytics
- VisibilityIndex.ai — local AI visibility audits
- Reevol “How AI Sees You” — lightweight SMB-facing AI visibility report

Questions to compare:
- Platforms supported
- Prompt design
- Location handling
- Data collection method
- Evidence and citations
- Repetition / monitoring
- Competitor analysis
- Recommendations
- Screenshot support
- Report export
- Pricing
- SMB vs enterprise positioning

---

## 11. Technical architecture — conceptual

```text
Website URL
    |
    v
Website crawler / extractor
    |
    v
Business Profile
  - Name
  - Category
  - Services
  - Locations / service areas
  - Differentiators
  - Languages
    |
    v
User confirmation
    |
    v
Prompt generator + prompt taxonomy
    |
    v
Audit configuration
  - Platforms
  - Markets / locations
  - Locale / timezone
  - API vs consumer test
  - Session conditions
  - Repetitions
    |
    v
Collection adapters
  - Search APIs
  - AI APIs
  - Approved consumer-app testing
  - Maps / local search collection
    |
    v
Raw evidence store
  - Exact prompt
  - Exact response
  - Citations
  - Screenshot
  - Metadata
  - Configuration
    |
    v
Analysis
  - Brand mentions
  - Recommendation / position
  - Competitors
  - Citations
  - Accuracy
  - Sentiment / context
    |
    v
Report + recommendations + historical comparison
```

### Potential data entities

- `businesses`
- `business_locations`
- `services`
- `business_profiles`
- `audit_runs`
- `audit_configurations`
- `prompt_templates`
- `audit_prompts`
- `platform_runs`
- `responses`
- `mentions`
- `competitor_mentions`
- `citations`
- `search_results`
- `screenshots`
- `recommendations`
- `measurements`
- `methodology_versions`

Version the prompts and methodology. Historical comparisons should disclose if the collection configuration changed.

---

## 12. Validation plan before product development

### Phase 1 — Market / competitor teardown

For Revisible and other competitors:
- Create trial accounts where possible
- Run the same SMB
- Compare prompts, results, metrics, screenshots, report UX
- Record pricing and limitations

### Phase 2 — Platform behavior experiment

For 2–3 platforms:
- Compare API and consumer app
- Compare explicit location vs IP location
- Compare fresh session vs logged-in
- Compare browser locale and timezone
- Compare repeated runs
- Compare search-enabled vs non-search mode

### Phase 3 — Geographic experiment

Use a test business in a market different from the tester's own location.

- Target city explicitly in prompt
- Target-country IP
- Target-city IP where feasible
- Browser geolocation / locale if supported
- Account context
- Search results and AI results

Determine whether proxy / residential IP changes the result materially.

### Phase 4 — Data reliability

- Repeat prompts
- Track variability
- Validate extracted citations
- Validate mention detection
- Validate position detection
- Detect false positives from similar business names
- Compare screenshots to parsed results

### Phase 5 — MVP scope

Only after the methodology is validated, select:
- Platforms
- Collection methods
- Location configuration
- Metrics
- Prompt count
- Repetitions
- Screenshot strategy
- Report format
- Monitoring cadence

---

## 13. Important product principles

1. **Evidence first:** every finding should link to the observed response, result, citation, or screenshot.
2. **No guaranteed rankings:** AI recommendations are probabilistic and can vary.
3. **Methodology transparency:** disclose API vs consumer application, location context, and session conditions.
4. **No false precision:** scores should have clear definitions and sample sizes.
5. **Separate observation from inference:** “competitor was cited” is an observation; “this citation caused the recommendation” is an inference.
6. **Location relevance:** test the actual service markets, not arbitrary countries.
7. **Repeatability:** preserve prompts, settings, platform, time, and methodology for comparisons.
8. **User confirmation:** website extraction should not silently create incorrect service-area assumptions.
9. **Compliance:** review platform terms, API terms, proxy-provider terms, privacy requirements, and automation restrictions.
10. **Actionable recommendations:** tie each recommendation to evidence and a specific improvement.

---

## 14. Questions we have not answered yet

### Location / environment
- Does each platform use IP location?
- Is explicit prompt location sufficient?
- Are residential IPs necessary?
- Does browser geolocation matter?
- Does account location matter?
- Does locale/timezone matter?
- Can a proxy reproduce the target city reliably?
- How do we validate the proxy's actual location?

### APIs
- Which APIs provide search?
- Which APIs support geographic context?
- How closely do API results match consumer apps?
- Can citations and search queries be captured?
- What are the per-audit costs?
- What API limitations apply?

### Consumer platforms
- Can they be tested reliably?
- Are browser automation methods allowed?
- Can we capture screenshots?
- How do we handle login and session state?
- What are the operational and legal limitations?

### Measurement
- What constitutes a mention?
- What constitutes a recommendation?
- How do we calculate visibility?
- How many prompts and repetitions are sufficient?
- How should uncertainty be presented?
- How do we handle contradictory results?
- How do we detect the same business under alternate names?

### Business profile
- How reliably can website data be extracted?
- How do we identify multiple locations?
- How do we identify service areas?
- How do we resolve ambiguous businesses?
- How do we allow user corrections?

### Report
- Which evidence should be shown?
- Google Search screenshots?
- Google Maps screenshots?
- AI platform screenshots?
- Exact prompts and answers?
- Citation sources?
- Competitor comparisons?
- Recommendations?
- PDF / shareable report?

---

## 15. Initial MVP hypothesis (not a final decision)

A first version could provide:

1. Website URL input
2. Business profile extraction and confirmation
3. Location / service-area selection
4. Customer prompt generation
5. AI platform tests
6. Google Search / Bing Search evidence
7. Google Maps / local results evidence where applicable
8. Exact responses and citations
9. Mention / recommendation / competitor analysis
10. Screenshots
11. Evidence-based recommendations
12. Downloadable report
13. Saved audit and rerun comparison

**This is a hypothesis to validate, not a locked implementation plan.**

---

## 16. Research sources / references

- Revisible AI Visibility Services: https://www.revisible.com/in/services/ai-visibility/
- Revisible Free Audit: https://www.revisible.com/in/free-audit/
- Revisible AI Search FAQ: https://www.revisible.com/in/faq/
- Revisible — How to Get Found on ChatGPT & AI Search: https://www.revisible.com/in/how-to-get-found-on-chatgpt-and-ai-search/
- Profound: https://www.tryprofound.com/
- Otterly.AI: https://otterly.ai/
- Peec AI: https://peec.ai/
- Scrunch: https://scrunch.com/
- Ahrefs Brand Radar: https://ahrefs.com/brand-radar
- Semrush: https://www.semrush.com/
- Rankscale: https://rankscale.ai/
- AthenaHQ: https://athenahq.ai/
- VisibilityIndex.ai: https://visibilityindex.ai/ai-visibility-audit
- Reevol: https://catalog.reevol.com/tools/ai-visibility

---

## Summary

The product should measure how a real potential customer discovers businesses through traditional search, maps, and AI answers—not simply how an AI summarizes a submitted website.

The biggest unresolved research area is measurement validity: how to reproduce the target customer's geographic, search, account, session, and platform context, and whether APIs, consumer apps, proxies, or a hybrid approach provide the most reliable evidence.

The next step is controlled research and competitor teardown, followed by a validated collection methodology. Implementation decisions should come after that.


---

# Updated Research Notes — Foundations, AI Access, Citation Intelligence, Actions, and Voice
**Updated: 20 November 2026**

These additions reflect the latest product discussion. They expand the plan rather than prematurely locking the implementation or claiming that any single factor guarantees AI recommendations.

## 1. Foundational discoverability audit (run before visibility diagnosis)

The product should first check whether the business's website is technically discoverable and eligible to be surfaced.

### Google Search
- Is the domain/site present in Google Search?
- Is the homepage indexed?
- Check important service, location, product, and contact pages individually where possible.
- Check for `noindex`, canonical conflicts, robots.txt blocks, HTTP errors, redirects, and inaccessible content.
- Check whether a sitemap exists, is valid, and contains canonical/indexable URLs.
- Check if important pages are linked internally and have crawlable links.
- If the user connects Google Search Console, use verified property data and URL Inspection / Page Indexing evidence. Do not imply that a third-party checker can see private Search Console status.
- Explain that submitting a URL or requesting indexing is a request, not a guarantee.

### Bing Search
- Is the site/domain discoverable in Bing?
- Check important pages and sitemap.
- Recommend Bing Webmaster Tools verification and submission where appropriate.
- Check whether IndexNow is configured and usable for the site/platform. IndexNow is a notification mechanism supported by participating search engines; it is not a guarantee of indexing and should not be described as a Google indexing submission mechanism.
- If the user connects Bing Webmaster Tools, use its verified data and URL inspection/indexing evidence where available.

### Search-index checks versus verified status
Distinguish these levels in the report:
1. **Observed in public search:** a search query returned a URL/domain.
2. **Likely indexed:** evidence suggests it is indexed, but no owner-verified console data is available.
3. **Verified indexing status:** confirmed through an authorized Google Search Console or Bing Webmaster Tools connection/data.
4. **Submission/request made:** a URL or sitemap was submitted/requested; this is not the same as indexed.

Never present a `site:` query as definitive index coverage.

## 2. Crawlability and AI/search bot access audit

Inspect robots.txt, HTTP responses, meta robots, `X-Robots-Tag`, CDN/firewall behavior, and rendered content where feasible. Check access by crawler identity rather than one generic “AI bot allowed” status.

### Bot groups to distinguish

| Bot / crawler | Purpose and interpretation |
|---|---|
| Googlebot | Google Search crawling; foundational for Google Search and Google Search AI features |
| Google-Extended | Google control related to certain Gemini/AI training and grounding uses; do not equate it with Google Search indexing or AI Overviews eligibility |
| Bingbot | Bing Search crawling and related Bing-powered discovery |
| OAI-SearchBot | OpenAI search crawler; relevant to inclusion in ChatGPT search results |
| GPTBot | OpenAI crawler associated with potential model training; separate control from OAI-SearchBot |
| ChatGPT-User | User-triggered page access in some ChatGPT experiences; not equivalent to automatic search crawling |
| PerplexityBot | Perplexity's crawler; test its documented access policy and observed behavior |
| ClaudeBot / Claude-SearchBot | Anthropic crawler identities; distinguish training-related crawling from search-related access where applicable |
| Other declared AI crawlers | Maintain a versioned registry, validate each crawler's current official documentation, and avoid assuming every bot is used for the same purpose |

The audit should report each crawler separately:
- robots.txt rule: Allow / Disallow / no explicit rule
- HTTP access test: accessible / blocked / error / inconclusive
- CDN or WAF challenge suspected
- Relevant page-level indexing directives
- Last checked timestamp
- Evidence and limitations

**Important:** A robots.txt check is not proof that a crawler can fetch a page. It is also not proof that the crawler actually visited the page. Conversely, allowing a bot does not guarantee crawling, indexing, citations, or recommendations.

### Recommended crawl checks
- robots.txt accessible and syntactically readable
- sitemap.xml and sitemap index accessible
- HTTP status and redirect chain
- TLS/HTTPS
- `noindex` and `X-Robots-Tag`
- canonical URL
- rendered versus raw HTML content
- important content available without login
- JavaScript-rendered content visibility
- CDN/WAF/bot-protection behavior
- internal links to important pages
- page response errors and soft-404-like behavior

Do not automatically recommend allowing every crawler. Show what each bot is documented to do and let the business choose based on its content/data preferences.

## 3. Webmaster tools onboarding and remediation

The report should include a prioritized “Connect and verify” foundation checklist:
- Google Search Console: verify the domain/property, submit sitemap, inspect important URLs, review indexing issues.
- Bing Webmaster Tools: verify site, submit sitemap, inspect visibility/indexing, consider IndexNow if supported by the site stack.
- Explain how to request indexing for selected important URLs, with the caveat that requests do not guarantee indexing.
- If credentials/connected account are unavailable, provide a guided checklist and label the status **Not verified** rather than guessing.

Potential product feature: guided onboarding links and a step-by-step checklist. Later, integrations could retrieve authorized data directly.

## 4. AI discovery and retrieval access is not the same as model training

The product must explain these separately in plain language:
- **Search/retrieval crawler access:** may help a platform retrieve a site when answering a current query.
- **Training crawler access:** relates to whether content may be collected for training, subject to each platform's policies and controls.
- **User-triggered fetches:** a user may ask an assistant to open a page; this can behave differently from automatic search crawling.
- **Search index inclusion:** a site may be indexed by Google/Bing but still not be retrieved or cited by an AI answer.
- **Model knowledge/training:** a business may be known from prior data or model knowledge, but this is not equivalent to live search visibility.

The product must not tell users that allowing GPTBot automatically makes them visible in ChatGPT Search. OpenAI documents OAI-SearchBot separately from GPTBot. Similarly, Google Search AI feature eligibility is tied to normal Search technical eligibility, and Google says no special AI markup or machine-readable files are required.

## 5. Customer-friendly explanation of uncertainty

A core product education section should say:

> **These actions improve discoverability and make your business easier for search systems and AI experiences to access and understand. They do not guarantee a recommendation or top placement.**
>
> AI answers can also depend on the query, location, retrieval sources, platform, ranking and selection systems, model behavior, business/category relevance, available evidence, freshness, and other factors we cannot directly control.

Use a transparent status model:
- **Foundation issue found** — an observable technical/discoverability problem.
- **Foundation checked** — no issue detected in the tests performed.
- **Opportunity identified** — evidence suggests a potential improvement.
- **Recommendation** — a plausible action, not a guaranteed causal fix.
- **Outcome observed** — visibility changed in a later test; avoid claiming the action caused the change unless the experiment supports that conclusion.

Do not promise “rank #1 in AI,” “guaranteed citations,” or a deterministic AI score.

## 6. Action recommendations — evidence-first, not generic SEO checklists

Every recommendation should ideally contain:
- Problem/finding
- Evidence observed
- Specific affected queries/platforms
- Source or competitor evidence
- Recommended action
- Why this action is relevant
- Priority and effort estimate
- Confidence and limitations
- Action status (Not started / In progress / Done / Dismissed)
- Optional generated draft, checklist, or implementation assistance

### Action categories
1. **Indexing/discovery:** Google/Bing index coverage, sitemap, URL inspection, webmaster tools.
2. **Crawler access:** robots.txt, meta robots, headers, CDN/WAF and bot-specific access.
3. **Citation/source opportunities:** domains and URLs repeatedly cited in relevant answers; competitors appearing there; practical opportunities for the business to earn legitimate coverage.
4. **Entity/brand presence:** sources that describe the brand, missing profiles, conflicting information, mistaken identity, and weak brand evidence.
5. **Recommendation evidence:** the specific attributes or evidence AI answers use to recommend competitors (e.g. projects, specialties, pricing, location, reviews)—only when observed.
6. **Content/query gaps:** missing information that is relevant to tested customer-intent prompts and retrieval evidence.
7. **Review/reputation evidence:** review sources and themes actually observed; no fabricated or manipulative review recommendations.
8. **Platform-specific access and findings:** distinguish each platform's documented crawler/search behavior and observed results.
9. **Voice/conversational discovery:** query patterns and answer tests described below.
10. **Measurement:** rerun the exact prompt/platform/context and compare before/after evidence.

Avoid generic action prescriptions such as “write more blogs,” “add FAQ schema,” “create llms.txt,” or “build backlinks” unless the audit identifies a specific reason and presents the recommendation as evidence-backed or clearly labeled best practice.

## 7. Citation and source intelligence (core capability)

For every answer that exposes sources/citations, store:
- Exact citation URL and domain
- Source title where available
- Source type/category
- Which query and platform produced it
- Position/order in citations
- Whether the source mentions the customer's business
- Whether it mentions competitors
- What claim/recommendation the citation appears to support
- Whether it is the business's own site or third-party
- Recurrence across prompts, platforms, and runs
- Timestamp and captured evidence

Do not treat every citation as a ranking signal or causal explanation. Distinguish:
- **Cited source**
- **Source containing the brand**
- **Source apparently supporting a recommendation**
- **Potential opportunity**
- **Verified causal influence** (usually not available)

## 8. Voice and conversational search testing

Include a prompt category for voice and natural-language discovery. Do not assume voice results are identical to typed results; test them where a platform/device interface can be captured.

### Prompt patterns
- “Who is the best [service] near me?”
- “Can you find a reliable [business type] in [location]?”
- “I need [service] for [specific situation]. Who would you recommend?”
- “What is a good affordable option for [need]?”
- “Which [provider] has experience with [attribute]?”
- “Can you compare a few options and tell me which one is best for me?”
- Follow-up conversational prompts: “Why that one?”, “Any cheaper options?”, “What about near [neighborhood]?”, “Can you find one with [constraint]?”

### Voice test metadata
Where possible record:
- Platform/device/voice assistant
- Spoken query versus typed query
- Exact transcription
- Locale/language/accent settings
- Location context
- Answer text/audio or transcript
- Businesses mentioned and order
- Citations/links, if provided
- Follow-up conversation context
- Whether the answer changes from typed search

MVP can simulate voice intent through natural-language prompts and label these **voice-style prompts**. Actual voice assistant testing should be a separate method because device integrations and access differ.

## 9. Updated audit/report order

1. Business profile and target-market confirmation
2. Technical discoverability foundation
   - Google index/search presence
   - Bing index/search presence
   - Sitemap/webmaster tools
   - Crawlability and bot access
   - Page accessibility/rendering
3. AI search visibility and recommendation testing
4. Citation/source intelligence
5. Competitor recommendation and evidence analysis
6. Voice/conversational query coverage
7. Brand accuracy and misinformation
8. Evidence-backed opportunity/action plan
9. Limitations, uncertainty, and test methodology
10. Retest/monitoring plan

Foundational issues should be surfaced early, but they should not be used to explain every AI visibility failure without evidence.

## 10. Product methodology safeguards

- Use verified Search Console/Bing data when authorized; otherwise label public checks as estimates.
- Keep crawler policy data versioned and sourced from official documentation.
- Test robots rules against actual crawler identities; do not infer successful crawl from permission alone.
- Separate indexing, crawling, retrieval, citation, mention, recommendation, and conversion.
- Distinguish APIs from consumer applications and disclose test context.
- Store exact prompt, location, language, platform, mode, timestamp, run, and response evidence.
- Repeat tests when results are volatile.
- Avoid causal claims from simple before/after observations.
- Recommendations should be specific to the customer's tested queries and market.
- Provide practical steps for users who do not understand technical SEO or webmaster tools.
- Offer generated drafts/checklists, but do not silently change website content or account settings without authorization.

## 11. Research references to validate and keep current

Official documentation reviewed for this update:
- Google Search technical requirements: https://developers.google.com/search/docs/essentials/technical
- Google Search AI features and website guidance: https://developers.google.com/search/docs/appearance/ai-features
- Google Search crawling/indexing overview: https://developers.google.com/search/docs/crawling-indexing
- Google robots.txt guidance: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- Google Search crawling and indexing troubleshooting: https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors
- OpenAI crawler overview: https://developers.openai.com/api/docs/bots

Key official-documentation observations (verify again when implementing because crawler behavior/policies may change):
- Google states pages must meet its Search technical requirements to be eligible; eligibility does not guarantee indexing.
- Google states AI Overviews/AI Mode do not require special AI markup or machine-readable files; existing Search fundamentals remain relevant.
- Google distinguishes crawling from indexing and serving.
- OpenAI distinguishes OAI-SearchBot (ChatGPT Search discovery) from GPTBot (training-related crawling) and ChatGPT-User (some user-triggered visits).
- Bot access, indexing, retrieval, citations, and recommendations are distinct states and must not be collapsed into a single “AI-ready” score.

## 12. Current product direction (not a final scope decision)

The product is evolving toward:

**Discoverability foundation → AI/search visibility testing → citation/source intelligence → competitor evidence → specific action plan → retesting/monitoring.**

The above is a research-informed direction, not a locked implementation plan. More platform-specific experiments and competitor teardown are still needed before finalizing feature scope, scoring, data collection methods, and technical architecture.


---

# Update 2 — Product Loop, SEO Integration, Expectations, and Technical Foundations
**Updated: 20 November 2026**

Items marked **[verify]** are working assumptions from current knowledge. Confirm each against the platform's official documentation before building checks or making customer-facing claims, and record the doc URL and date checked.

## 13. Product loop and Action Center

The product is a loop, not a one-time report:

| Stage | Question it answers | Output |
|---|---|---|
| **1. Discover** | Where does the business appear across AI search, Google, Bing, Maps and voice? | Visibility evidence per platform / query / location |
| **2. Diagnose** | Why is it missing? What do competitors have that it lacks? Which sources influence answers? | Foundation issues, source gaps, competitor evidence |
| **3. Recommend** | What specifically should the business do, in what order? | Prioritized, evidence-backed actions |
| **4. Execute** | How does the business actually do it? | Guides, templates, generated drafts, integrations |
| **5. Measure** | Did anything change? | Re-run of the same prompts / platforms / locations, before–after comparison |

### Action Center
Instead of only a downloadable report, the customer gets an action list:
- Each action has: title, category, priority (High / Medium / Low), effort, linked evidence, and **status** (Not started → In progress → Done / Dismissed).
- Summary counts by priority (e.g. "12 actions: 4 high, 5 medium, 3 low").
- Completing actions schedules or suggests a re-test.

### Actions the tool could execute later (not MVP)
Prove recommendation quality first; automate later.

| Action | Future capability |
|---|---|
| Create a missing page | Generate a page draft for the service + location |
| Improve an existing page | Analyze the page and suggest specific edits |
| FAQ content | Generate questions from the actual prompts tested |
| Google Business Profile | Generate description, categories and service list |
| Directory listing | Provide ready-to-copy listing details (consistent NAP) |
| Structured data | Generate JSON-LD (LocalBusiness, Service, etc.) |
| Citation / source opportunities | List target sites and draft outreach messages |
| Review analysis | Identify themes in existing reviews |
| Track changes | Automatically re-run visibility tests after actions |

Never change the customer's website or accounts without explicit authorization.

## 14. Fit with the existing SEO product

AI visibility is a component of the existing SEO product, not a separate tool.

- Every recommendation links to an existing tool or workflow where one exists (e.g. "missing service page" → content tool; "noindex on key page" → technical SEO audit; "robots.txt blocks OAI-SearchBot" → crawler access check).
- Workflow: **Traditional SEO audit → AI visibility audit → competitor & citation intelligence → actions → re-run & monitor.**
- **Retention:** run the initial audit → fix actions → **re-audit after ~30 days** → see what changed → monitor competitors → alerts when visibility changes. The repeat audit is the reason customers come back.

## 15. Setting expectations: training data, brand age and authority

Customers must understand what fixes can and cannot change.

- AI models learn partly from **training data** collected before their cutoff. Older, well-established businesses with years of mentions across the web may already be "known" to the model.
- A new or small business may be invisible in model knowledge even with a perfect website. Fixes improve **live search / retrieval** eligibility much faster than they change what a model learned in training.
- Brand age, volume of independent mentions, reviews and press accumulate slowly; there is no shortcut.
- Model updates happen on the platform's schedule, not the customer's.

Plain-language version for the report:

> Some AI answers come from what the AI learned in the past, and some come from searching the web right now. Fixing your website and listings mainly helps the "searching right now" part, and can show results within weeks. Being "known" to the AI from its past learning depends on how long and how widely your business has been mentioned online — that builds over months and years.

Report both: (a) does the platform know the business without search (model knowledge), and (b) does it find the business with search on (retrieval).

## 16. Competitor comparison table (teardown template)

Fill one column per product after hands-on testing with the same test business.

| Feature | Our idea | Revisible | Otterly | Peec | Profound | Scrunch | Semrush AI |
|---|---|---|---|---|---|---|---|
| Website analysis / profile extraction | | | | | | | |
| Prompt generation | | | | | | | |
| Location targeting | | | | | | | |
| Exact AI responses shown | | | | | | | |
| Screenshots | | | | | | | |
| Citations / sources | | | | | | | |
| Competitor analysis | | | | | | | |
| Google Maps / local | | | | | | | |
| Google / Bing search | | | | | | | |
| Indexing & crawler audit | | | | | | | |
| Voice / conversational | | | | | | | |
| Recommendations / actions | | | | | | | |
| Historical monitoring | | | | | | | |
| API vs consumer-app method disclosed | | | | | | | |
| SMB pricing | | | | | | | |

The goal is to find what is already commoditized and where we can differentiate.

## 17. Bing as a foundation for ChatGPT and Copilot

Bing deserves its own section in the foundation audit, not a footnote under Google.

- **Microsoft Copilot** is built on Bing search.
- **ChatGPT search** has used Bing as one of its search providers alongside OpenAI's own crawling (OAI-SearchBot). **[verify current provider mix]**
- **Alexa** has used Bing for web answers. **[verify]**
- Bing's index also feeds other products and search partners (e.g. DuckDuckGo results in part). **[verify]**

Bing checks:
- Site verified in **Bing Webmaster Tools** (can import directly from Google Search Console).
- Sitemap submitted in Bing Webmaster Tools.
- URL Inspection for key pages (homepage, main service pages, location pages, contact).
- Bingbot not blocked in robots.txt, CDN or firewall.
- IndexNow configured (below).
- Bing Places for Business listing claimed and consistent (local businesses).

A site that is fine in Google but missing in Bing is a concrete, fixable issue that may affect ChatGPT and Copilot.

## 18. IndexNow — what it is and isn't

- IndexNow is a protocol for **notifying** search engines that a URL was added, changed or deleted.
- Setup requires a **key**: a text file hosted on the site (e.g. `https://example.com/<key>.txt` containing the key) that proves ownership; submissions reference that key.
- Participating engines include **Bing, Yandex, Seznam, Naver and Yep**. A ping to one is shared with the others. **[verify current list]**
- **Google does not support IndexNow.** Google discovery relies on crawling, sitemaps and Search Console. Never present IndexNow as a way to get indexed by Google.
- Notification is not a guarantee of crawling or indexing.
- Many platforms and plugins support it (e.g. Cloudflare Crawler Hints, popular WordPress SEO plugins, Bing Webmaster Tools' own IndexNow). **[verify]**

Audit checks:
- Is a key file present and reachable? (Discoverable only if known or listed by a plugin; otherwise ask the user / check Bing Webmaster Tools IndexNow report.)
- Is the CMS / plugin configured to ping automatically on publish?
- Recent submissions visible in Bing Webmaster Tools?

## 19. Cloudflare and CDN/WAF bot blocking — the hidden blocker

- Cloudflare began **blocking known AI crawlers by default** for new domains (mid-2025), and offers one-click "Block AI bots", managed robots.txt, "AI Crawl Control" and pay-per-crawl options. **[verify current defaults]**
- Result: a site's robots.txt can say *Allow* while Cloudflare (or another CDN/WAF/bot-protection layer) returns a block page, challenge or 403 to the same crawler.
- Many SMB owners don't know this setting exists — it is likely the most common invisible reason AI crawlers can't reach a site.

Audit checks:
- Detect CDN/WAF provider from response headers (e.g. `server: cloudflare`, `cf-ray`).
- Request key pages with each crawler's user-agent and compare status code and body with a normal browser request (403 / 503 / challenge page / empty body = likely block).
- Note the limitation: a user-agent test from our IP is not identical to the real crawler (real crawlers come from verified IP ranges; some WAFs check IPs). Report "likely blocked" vs "verified blocked".
- Give the owner plain instructions: where the setting lives in Cloudflare and which crawlers to allow based on their choice (search vs training).

## 20. Expanded crawler registry

Add to the bot table in section 2 (Update 1). Keep this registry versioned and sourced from each vendor's official docs.

| Crawler | Operator | Purpose / interpretation |
|---|---|---|
| Claude-User | Anthropic | Fetches pages when a Claude user asks; user-triggered, not automatic crawling |
| Claude-SearchBot | Anthropic | Search indexing for Claude's search results |
| ClaudeBot | Anthropic | Training-related crawling |
| Perplexity-User | Perplexity | User-triggered fetches in Perplexity answers (Perplexity has said it may not follow robots.txt for user-initiated requests) **[verify]** |
| PerplexityBot | Perplexity | Indexing for Perplexity search |
| Applebot | Apple | Crawls for Siri, Spotlight and Safari suggestions |
| Applebot-Extended | Apple | Controls whether Applebot-crawled content can be used to train Apple's AI models (Apple Intelligence); it does not crawl itself — it's a robots.txt control token |
| Meta-ExternalAgent | Meta | Crawling for Meta AI / model training |
| Meta-ExternalFetcher | Meta | User-triggered fetches from Meta AI **[verify]** |
| Amazonbot | Amazon | Crawling used for Alexa answers and other Amazon services |
| OAI-SearchBot / GPTBot / ChatGPT-User | OpenAI | (already listed) search / training / user-triggered |
| Googlebot / Google-Extended | Google | (already listed) search / AI training & grounding control token |
| Bingbot | Microsoft | (already listed) Bing search, Copilot |

Group the report by purpose so owners can decide:
1. **Search & answer crawlers** (help you be found): Googlebot, Bingbot, OAI-SearchBot, Claude-SearchBot, PerplexityBot, Applebot, Amazonbot
2. **User-triggered fetchers** (a person asked the AI to open your page): ChatGPT-User, Claude-User, Perplexity-User, Meta-ExternalFetcher
3. **Training controls** (whether content may train models): GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, Meta-ExternalAgent

Blocking group 3 generally does not remove a site from search; blocking groups 1–2 can. **[verify per vendor]**

## 21. Voice assistants use listings, not just websites

Voice answers for local queries mostly come from **business listing / maps data**, not the website. Each assistant uses different sources: **[verify all]**

| Assistant | Main local data sources | What the business should check |
|---|---|---|
| **Siri** (Apple) | Apple Maps, **Apple Business Connect**; Yelp and other partners for reviews/ratings | Claim Apple Business Connect listing; name, address, hours, category, phone consistent |
| **Alexa** (Amazon) | **Bing** (web and local), **Yelp** and other data partners | Bing Places listing; Yelp listing claimed and complete |
| **Google Assistant / Gemini** | **Google Business Profile**, Google Maps, Google Search | Google Business Profile complete, verified, reviews, categories, hours |
| **ChatGPT voice** | Same as ChatGPT search (OpenAI crawl + search providers) | Covered by AI visibility checks |

Implications:
- For voice, **listing completeness and consistency** (name, address, phone, hours, categories, reviews) matter more than website content.
- The voice section of the audit should include a **listings check** for Apple Business Connect, Bing Places, Yelp and Google Business Profile.
- Voice assistants usually give **one answer**, not ten — being #1 matters more than in typed search.
- MVP: voice-style prompts + listing audit. Real device testing is a later, separate method.

## 22. Rendering without JavaScript

- **Googlebot renders JavaScript** (with delay). **Most AI crawlers do not** — tests of GPTBot, ClaudeBot, PerplexityBot and others have shown they fetch raw HTML and don't execute JS. **[verify per crawler]**
- Sites built as client-side React/Vue/Angular apps, or site builders that load content with JS, can look **empty** to AI crawlers even though they look fine in a browser and in Google.

Audit checks:
- Fetch key pages without executing JavaScript and extract visible text.
- Compare with the rendered (browser) version: business name, services, location, phone, hours, prices.
- Flag pages where key facts appear only after JS runs.
- Check that navigation links exist as real `<a href>` links in raw HTML.
- Recommend server-side rendering, static generation or pre-rendering where content is missing — evidence first.

## 23. Updated foundation audit order

1. Google indexing (Search Console, sitemap, URL inspection, noindex/canonical)
2. Bing indexing (Bing Webmaster Tools, sitemap, URL inspection, Bing Places)
3. IndexNow (key file, CMS/plugin ping, submissions)
4. Crawler access by bot group (robots.txt per crawler)
5. CDN/WAF blocking (Cloudflare AI bot settings, user-agent tests)
6. JavaScript rendering (raw vs rendered content)
7. Business listings for voice (Google Business Profile, Apple Business Connect, Bing Places, Yelp)
8. Voice-style and conversational prompt tests

Work through these one by one, verifying each against official documentation, then update this file with findings.


---

# Update 3 — Prompt Budget, Speed Target and Tech Stack
**Updated: 20 November 2026**

**Approach decision:** no separate MVP-scoping phase. We build in small steps and test as we go.

## 24. Sample size and prompt budget

Not yet decided before this update; numbers below are a starting proposal to be validated by the pilot.

### What sets the total
`calls per audit = prompts × repeat runs × platforms × locations × (search off + search on)`

Example: 25 prompts × 3 runs × 5 platforms × 1 location = **375 AI calls** for one audit. A second city doubles it.

### Proposed starting point

| Setting | Proposal | Why |
|---|---|---|
| Core prompts | 25 (5 intents × ~5), same set on every platform | Lets us compare platforms directly |
| Repeat runs | 3 per core prompt | Answers vary between runs; one run can mislead |
| Branded / accuracy prompts | 5, 1 run each | Facts change less, so fewer repeats are needed |
| Model knowledge vs live search | Core prompts run with search off and search on | Tests training data vs retrieval |
| Locations | Main service city first; extra cities as an add-on | Cost multiplies per city |
| Platforms | ChatGPT, Gemini, Perplexity, Claude, Copilot, plus Google AI Overviews | Same prompt set on each |

### Statistical reality
- 25 prompts is a small sample. "Mentioned in 20%" (5 of 25) has a plausible true range of roughly 7–40%.
- Reports show **counts** ("appeared in 5 of 25 prompts, 3 runs each"), not precise-looking percentages.
- A small change between audits (5 → 7) is not evidence of improvement.
- Trend monitoring needs more prompts or the same prompts tracked over several audits.

### Pilot to settle the numbers
1. One test business: 50 prompts × 10 runs on 2 platforms.
2. Measure how often the recommended businesses change between runs of the same prompt.
3. Stable answers → 2–3 runs are enough. Volatile answers → 5+ runs, or fewer prompts with more repeats.
4. Record real latency and cost per call; price audit tiers from that.
5. Run alongside the location experiment (section 5).

## 25. Speed target: first results within 60 seconds

**Decision: two tiers with different speed targets.**

| Tier | Scope | Time target | Delivery |
|---|---|---|---|
| **Free run** | 3 LLM providers × 5–10 prompts each, 1 run, all in parallel (15–30 calls) + foundation checks + search/Maps data | **≤ 60 s** | Live on screen, results streaming in |
| **Paid audit** | Full prompt set, repeat runs, search off/on, all platforms, extra locations, screenshots, consumer-app spot checks | **Up to ~1 hour** is acceptable | Full report sent to the user when complete (email + in-app) |

Notes:
- 15–30 parallel calls for one user stays well within provider rate limits. Many free users at the same moment could still add up, so keep a **global concurrency cap** per provider and queue the excess.
- Which 3 providers for the free run: proposal **ChatGPT, Gemini, Perplexity** (high usage, search built in) **[decide]**.
- Free runs cost us money per run: limit per email/IP, cache recent results for the same domain, and block abuse.
- The paid tier's 1-hour window removes the time pressure, so it can use slower reasoning modes, more repeats and browser-based captures.

Stages:

| Stage | Time | What runs | Notes |
|---|---|---|---|
| Profile extraction | ~5–15 s | Fetch homepage + key pages, one LLM call to extract the profile | User confirms or edits; the 60 s clock starts at confirm (or auto-start with edit later — decide in testing) |
| **Free run** | ≤ 60 s | All in parallel: foundation checks (robots.txt, headers, sitemap, CDN, raw vs rendered HTML), SERP/Maps data, 3 providers × 5–10 prompts × 1 run | Results stream to the UI as each call finishes; calls over ~45 s show as "still running" and fill in later |
| **Paid audit** | Up to ~1 h, in background | Full prompt budget (section 24), repeat runs, search-off runs, extra locations, screenshots, consumer-app spot checks | Report sent to the user when complete |

Speed rules:
- Everything independent runs concurrently (async I/O).
- Use fast, non-reasoning model modes for the quick scan; slower modes only in the full audit. **[verify per provider]**
- Stream progress to the browser (Server-Sent Events).
- Hard timeouts on every external call; partial results are better than a blank screen.
- Respect each provider's rate limits; track them per API key.

## 26. Tech stack proposal (under review)

| Area | Proposal | Reasoning |
|---|---|---|
| Backend language | **Python** | Camoufox is Python-first; Playwright for Python is mature; strongest LLM SDK and data tooling |
| API | **FastAPI** (async) | Async fits massive parallel I/O; SSE support; typed models |
| LLM calls | **Direct provider SDKs** (OpenAI, Anthropic, Google GenAI, Perplexity), behind our own thin adapter | We need exact control of web-search tools, `user_location`, citations and raw responses. Abstraction layers can lag new features and drop citation metadata |
| LangChain / LangGraph | **Not now** | The audit is a fixed, parallel pipeline, not an agent. LangGraph can be reconsidered later for multi-step agentic features (e.g. generating action drafts) |
| Browser automation | **Scripted Playwright**, not LLM browser agents | Agents are slow, non-deterministic and costly — incompatible with the 60 s target and repeatable measurement. Use Playwright for: JS-rendering check, screenshots, specific captures |
| Search / Maps results | **SERP data APIs first** (e.g. DataForSEO, SerpApi, Bright Data SERP) **[evaluate]**; own Playwright + residential proxies only if APIs can't deliver | Faster (seconds), location-targeted, and avoids running our own anti-bot infrastructure |
| Camoufox + residential proxies | **Only for tests that require them**, after the location experiment proves they matter | Automating consumer AI apps and search pages may breach their terms of service; review compliance before building. Slow and fragile; keep out of the quick scan |
| Database | **PostgreSQL** (use JSONB for raw responses) | Data is relational (business → audit → prompt → run → response → mentions → citations) and needs aggregate queries. One database; MongoDB not needed |
| Job queue | **Postgres-backed queue** (e.g. `SELECT … FOR UPDATE SKIP LOCKED`, or a library such as Procrastinate / PgQueuer) **[evaluate]** | Background full audits without extra infrastructure |
| Redis | **Not needed now** | Postgres covers queue and progress (LISTEN/NOTIFY). Add Redis later for caching, rate-limit counters or high-volume pub/sub |
| Frontend | **React + TypeScript** | Live-updating report via SSE |
| Deployment | **Oracle Cloud (OCI)**, Docker containers | API, workers and browser workers as separate containers; scale browser workers independently |
| Postgres hosting | OCI Database with PostgreSQL (managed) or self-hosted on a VM **[evaluate]** | Managed saves ops; self-hosted is cheaper |
| Compute | OCI Ampere A1 (ARM) for API/workers **[verify Camoufox ARM support]**; x86 for browser workers if needed | Ampere is cost-effective; browser builds may need x86 |
| Observability | Per-call log of latency, cost, tokens, errors, provider, model | Needed for the speed target and pricing |

### Services
```text
React TS frontend ──SSE──> FastAPI API ──> Postgres (data + queue)
                                 │
                 ┌───────────────┼────────────────┐
          LLM worker pool   Foundation checker   Browser worker pool
          (async SDK calls) (HTTP, robots, JS)   (Playwright / Camoufox,
                 │                                 screenshots, later)
          SERP / Maps APIs
```

### Open stack questions
- Real per-provider latency and rate limits for search-enabled calls (pilot).
- Which SERP API gives reliable city-level Google, Bing and Maps results, and at what cost.
- Camoufox and Playwright Firefox on ARM.
- Terms-of-service review for any consumer-app or search-page automation.
- Whether one Postgres queue handles peak load or Redis becomes necessary.


---

# Update 4 — Published Research and Location Profiles
**Updated: 20 November 2026**

## 27. What published research already shows

Mostly vendor-published studies, not peer-reviewed; methods and definitions differ, so numbers aren't directly comparable. The direction is consistent.

### API answers differ from app answers
- **Surfer (1,000 prompts):** API and ChatGPT app answers to the same prompt shared only **21–32% of brands**. App cited ~12 sources per answer, API ~3.
- **Paprik:** API without web search named 135 unique brands vs 845 in the ChatGPT UI on the same prompts; with web search on, the API reached 580.
- **Outrigger (1,000 questions):** API with web search vs ChatGPT Search gave a different visibility result on ~16% of questions; the top brand sometimes changed.
- The API doesn't enable web search or location by default; the app does both.

**Conclusion:** API-only measurement does not represent what app users see. **App-based checks are needed**, at least to calibrate API results.

### Answers change almost every run
- **SparkToro + Gumshoe (~3,000 prompts; ChatGPT, Claude, Google AI Overviews):** the same brand list came back **<1%** of the time, same order **<0.1%**. The pool of brands is fairly stable (top brands in 55–77% of answers).
- **Spyglasses follow-up:** two runs of the same prompt shared **74%** of recommended brands; two differently worded prompts with the same intent shared **54%**.

**Conclusion:** report appearance frequency across many runs, never rank position. Repeat runs are required (plan for 5+ in the paid audit). Prompt wording variants matter.

### Location
- **OpenAI's help docs:** ChatGPT search uses an approximate location derived from IP for local queries; a VPN can change it; it may rewrite "near me" queries to include the inferred city. Precise device location is optional. Memory can also influence results. The IP itself is not passed to third-party search providers.
- **No controlled study found** comparing local business recommendations across VPN/proxy locations. SEO tool vendors claim VPNs work, without published data.

**Our opening:** a controlled local-SMB location study does not exist. Our Test 1 targets exactly that gap, and the results could be published as marketing.

### Revised Test 1
Skip the general API-vs-app comparison (already shown). Test, for local queries: how close is each method — API with `user_location`, app via VPN/proxy, app with city in prompt — to the app used from a real US location? Use 5+ runs per prompt.

Sources:
- https://www.farandwide.io/blog/ai-visibility-real-apps-vs-api
- https://paprik.ai/blog/accurate-api-based-ai-visibility-tracking-chatgpt-ui
- https://www.outriggerai.com/research/chatgpt-api-vs-search
- https://www.searchenginejournal.com/ai-recommendations-change-with-nearly-every-query-sparktoro/566242/
- https://research.spyglasses.io/articles/prompt-phrasing-consistency
- https://help.openai.com/en/articles/9237897-searching-the-web-with-chatgpt

## 28. Location profiles

Idea: predefine a library of location profiles (~200–300 worldwide) and use one only when a test genuinely needs it.

### What a profile contains
A profile is configuration, not a running machine. When needed, a fresh browser context is launched with it:
- Proxy exit location (country, state, **city**)
- Browser geolocation coordinates + permission (Playwright supports setting these)
- Locale / `Accept-Language` (e.g. en-US)
- Timezone (e.g. America/Chicago)
- Fresh, isolated session (no cookies, logged out) — or a dedicated test account for that country if logged-in tests are needed
- Device type (desktop / mobile)

### Granularity
- **State level is too coarse** for local SMBs: "florist near me" in Dallas and Houston differ, and IP geolocation is usually reliable at country and region level and only roughly at city level.
- Use **metro-level** profiles: top US metros (~50–100) instead of 50 states, plus major cities in other target countries. ~200–300 total is realistic.
- Add new metros on demand when a customer's service area isn't covered.
- Verify each profile periodically: check the exit IP's geolocation in more than one geo-IP database, and that the platform infers the intended city.

### When a profile is used
- **Not** for the free run (APIs with `user_location` + city in the prompt).
- **Paid audit:** calibration spot checks in the consumer apps for "near me" and local queries.
- **Research:** the location experiment.

### VPN vs residential proxy

| | Consumer VPN | Residential proxy | ISP (static residential) proxy |
|---|---|---|---|
| IP type | Datacenter, often flagged | Real home ISP IPs | ISP-registered, hosted in datacenters |
| City targeting | Few cities | Most providers offer city targeting | Limited set of cities |
| Parallel locations | One tunnel per machine | Per browser context, many at once | Per context |
| Session stability | Stable | Rotating or sticky sessions (minutes) | Stable, long-lived |
| Bot detection | Often challenged | Least flagged | Low |
| Cost | Cheap monthly | Per GB of traffic **[verify pricing]** | Per IP per month |
| Fit | **Manual tests now** | **Production app checks** | Logged-in test accounts needing a stable IP |

**Recommendation:**
- **Now (manual Test 1):** a VPN is fine — cheap and quick.
- **Production:** **residential proxies with city targeting**, one sticky session per browser context, driven by Playwright/Camoufox. ISP proxies only if we run logged-in accounts that need a stable IP.
- Use a provider that documents ethically sourced residential IPs (consenting users).
- Block images/media in proxied sessions to keep bandwidth (and cost) low.

**Compliance:** automating consumer AI apps and search pages through proxies may breach those platforms' terms of service. Review before building, keep volumes low (calibration, not bulk scraping), and prefer official APIs wherever the calibration shows they're close enough.

## 29. Login and proxy cost

### Login: mostly not needed
Logged-out sessions are better for clean tests: no memory, history or personalization.

| Platform | Logged out? |
|---|---|
| ChatGPT | Yes; web search works logged out |
| Perplexity | Yes |
| Google AI Overviews / AI Mode | Yes |
| Copilot | Yes, tighter limits |
| Gemini | Logged-out use exists; limits and features may differ **[verify]** |
| Claude | No; requires an account |

Caveats:
- Logged-out users may get a different model and lower limits than logged-in or paying users. Most real customers are logged in, so reports label results **"logged-out view"**.
- Logged-out sessions see more CAPTCHAs and challenges (see compliance note above).

### Residential proxy pricing (Nov 2026, varies by source — check vendor pages)

| Provider | Small volume | At scale | Notes |
|---|---|---|---|
| Decodo | ~$3.75/GB (3 GB plan), $4/GB pay-as-you-go | ~$2/GB at 1 TB | Low–mid range |
| Oxylabs | ~$6/GB | ~$2.50/GB at 1 TB | Higher at small volume |
| Bright Data | ~$8/GB list, promos ~$4 | Lower on large plans | ZIP and city targeting |
| IPRoyal | ~$7/GB at 1 GB | ~$1.75/GB custom at 10 TB | Traffic never expires |
| Budget (Evomi, DataImpulse) | ~$0.50–1/GB | — | Check quality and IP sourcing |

### Cost estimate per audit (to measure in the pilot)
- One app check with images/media blocked: ~2–5 MB (scripts are the heavy part; reuse one browser session across prompts).
- At ~3 MB per check: 1 GB ≈ 300 checks ≈ **$0.01–0.02 per check** at $4/GB.
- Paid audit with 30 app checks × 5 runs = 150 checks ≈ 0.5 GB ≈ **$1–3 proxy cost per audit**.
- For early testing a small plan (e.g. Decodo 3 GB ≈ $11, or IPRoyal non-expiring traffic) is enough.
- Proxy traffic is unlikely to be the main cost; AI API calls and CAPTCHA failures/retries probably cost more. Measure all three.

Sources:
- https://www.itechguides.com/how-much-do-residential-proxies-cost-per-gb-plans-and-hidden-fees-compared-november/
- https://proxyfacts.com/blog/proxy-pricing-comparison
- https://www.technology.org/2026/10/13/best-residential-proxies-in-2026-what-six-providers-actually-charge/
- https://proxyadvice.net/residential-proxy-prices/

### Testing now without a VPN or proxy
We don't have a VPN or proxy yet. Test 1 can still start:

| Run | Needs VPN/proxy? | How |
|---|---|---|
| App from India, city in prompt | No | Manual, normal browser, logged out |
| API with `user_location` = Dallas | No | Script |
| API without location | No | Script |
| App with US IP | Yes | Free VPN with US servers (e.g. Proton VPN free tier, country-level only) or a small proxy plan later |
| **Real US user (ground truth)** | No | Ask a contact in the US to run the same prompts logged out and send screenshots |

The real-US-user baseline is the most valuable run: it is what every other method is compared against. Browser geolocation can also be overridden separately in Chrome DevTools (Sensors panel) to test GPS location without changing IP.


---

# Update 5 — Test 1, Round 1 Results
**Updated: 20 November 2026**

Test business: florists in Dallas, Texas. Prompts: "best florists in Dallas", "same-day flower delivery Dallas", "best florist near me".

## 30. Manual app test (incognito, logged out, from India)

Platforms: ChatGPT, Google AI Mode, Copilot / Bing. VPN on = Proton free, US server (exited in **Miami**). Mostly one run per condition.

| Prompt | Platform | Businesses (VPN on / off) | In both | Overlap |
|---|---|---|---|---|
| Best florists | ChatGPT | 10 / 8 | 5 | 38% |
| Same-day | ChatGPT | 5 / 6 | 4 | 57% |
| Best florists | Google AI Mode | 10 / 6 | 5 | 45% |
| Same-day | Google AI Mode | 7 / 5 | 4 | 50% |
| Near me, refresh (VPN off) | Google AI Mode | 6 / 6 | 2 | 20% |

Findings:
1. **City in the prompt works without a VPN.** From India, all platforms gave Dallas florists. VPN on/off changed the lists about as much as a re-run does; top picks stayed (Google #1 McShan both times; ChatGPT same-day #1 Estrella's both times). Repeat runs are needed to separate VPN effect from normal variance.
2. **"Near me" follows the IP.** ChatGPT with VPN → Miami; ChatGPT and Google without VPN → Hyderabad. A country-level VPN lands in whatever city the server is in, so Dallas "near me" needs a Dallas proxy exit (location profiles).
3. **Protocol flaw: one chat thread for all prompts.** Incognito isolates cookies, not the conversation. ChatGPT asked "Dallas (from your earlier question) or Miami?"; Copilot said "Dallas-area near you"; Google AI Mode said "you are in central Dallas… 6-minute drive" (unexplained with a Miami VPN). **Fix: a new chat for every prompt.**
4. **Each platform uses different sources.** ChatGPT cited blog lists (Petal Republic, Thursd); Copilot cited D Magazine and The Knot and leaned to wedding florists no one else named; Google used Maps listings with review counts.
5. **ChatGPT entity errors.** Its map labeled The T Shop a "cell phone store" and Le Bloom a "coffee shop" while recommending both as florists. Ratings differ from Google (McShan 4.2 vs 4.9 from 5K reviews; Dr Delphinium 3.9 vs 4.7). ChatGPT uses a different place-data source than Google — a concrete brand-accuracy finding.
6. **Time of day matters.** Copilot noted "late evening in Dallas" and advised against same-day; Bing listed shops "open Friday Nov 20". Record the target city's local time; test during its business hours.
7. **Stable core.** McShan, Petals & Stems, Dr Delphinium and Estrella's appeared almost everywhere; the rest varied. Matches SparkToro.

## 31. Gemini API test (gemini-3.8-flash, paid key, 3 runs each)

Setups: Google Search grounding (no location setting exists for search); Google Maps grounding with the user placed in downtown Dallas (lat/lng). 18 of 27 calls succeeded.

| Prompt | Setup | Run-to-run agreement | Overlap with ChatGPT app | Overlap with Google AI Mode |
|---|---|---|---|---|
| Best florists | Search | 64% | 27–50% | 22–50% |
| Best florists | Maps, Dallas | 52% | 46–50% | 33–44% |
| Same-day | Search | 37% | 9% | 19–24% |
| Same-day | Maps, Dallas | 61% | 7–26% | 16–19% |
| Near me | Search | 100% (all India) | — | — |
| Near me | Maps, Dallas | 78% (Dallas) | — | — |

App comparisons use single, same-thread app runs, so treat overlaps as rough.

Findings:
1. **The API is not location-neutral.** "Near me" via search returned Indian services every time (Interflora India, FNP, FlowerAura, Blinkit, Zepto, Instamart) because the request came from India. **In production, answers follow the server's location** — an OCI server in India would bias every audit. Always pass the target location explicitly.
2. **Maps grounding with lat/lng is the API's location profile.** "Near me" with Dallas coordinates returned Dallas florists, 78% stable. No proxy needed for this.
3. **Search + Maps in one request is rejected** (400 INVALID_ARGUMENT) on this model. Run them as separate calls.
4. **API ≠ app.** Overlap 7–50%, in line with published studies (21–32%). Search added national services for same-day (UrbanStems, 1-800-Flowers, DoorDash, Whole Foods); Maps picked small shops near the downtown point (Lovely Flowers, All Blooming Flowers). The apps favored established local names.
5. **Shared core.** McShan, Dr Delphinium, DIRT, PRESCH, Designs East and In Bloom appear across the API, ChatGPT, Google and Bing.
6. **Speed fits the free run.** Single calls 10–39 s; 27 calls in 84 s at 6 concurrent. Fully parallel ≈ the slowest call (~40 s). Tail latency is the risk to the 60 s target.
7. **Gemini searches like an SEO.** For "best florists" it queried "best florists in Dallas D Magazine". D Magazine also drove Copilot's answer — a cross-platform source worth targeting.

## 32. Decisions from round 1

- **Free run:** API-based is viable, but always send the target city — Maps lat/lng for local queries plus the city in the prompt. Never rely on server location.
- **Paid audit:** needs app checks; API answers alone overlap only 7–50% with what users see.
- **Report labels:** "API view" vs "app view (logged out)" on every result.
- **Server location:** whatever OCI region hosts API calls, results must not depend on it — verify by re-running "near me" from the production server.
- **Next round:** new chat per prompt, 3+ runs, add Perplexity, record VPN city and Dallas local time, run during Dallas business hours, US friends as the real baseline. Test OpenAI and Perplexity APIs when keys are available.

Test code and raw results: `gemini_test/` (test_gemini.py, app_results.json, results/20261120-144042).


---

# Update 6 — Modern Web Guidance (Google Chrome)
**Updated: 20 November 2026**

Source: https://github.com/GoogleChrome/modern-web-guidance-src (Apache-2.0; stewarded by the Chrome, Edge, Firefox and MDN teams). A set of guides that coding agents load to write modern web code: 262 web platform features across CSS, performance, accessibility, forms and built-in AI. Each guide ships with expectations, a grader and test tasks, evaluated nightly.

Most of it is about building websites, not AI discoverability. Four parts are adopted.

## 33. Use it to build our own frontend
- Install the skill for the coding agent that builds our React TS app: `npx modern-web-guidance@latest install` (Node 22+).
- Result: native dialogs, popovers, container queries, view transitions and accessible components instead of heavy libraries; better INP and accessibility.
- When: as soon as the frontend project exists.

## 34. New audit check: AI agent readiness (WebMCP)
- **WebMCP** is a new browser API: `document.modelContext.registerTool({ name, description, inputSchema, execute })` lets a page offer actions (e.g. "check same-day delivery to a ZIP", "book a consultation", "get price list") that browser agents, extensions and system assistants can discover and call directly.
- Why it matters: being recommended is step one; an AI agent completing the order on the site is the next step.
- **Check:** does the customer's site register any WebMCP tools? (Detect `modelContext.registerTool` in page scripts; later, run the page in a supporting browser and list registered tools.)
- **Action:** suggest 1–3 tools that fit the business type, with name, description and input schema drafts.
- **Status:** emerging and experimental **[verify current browser support]**. Report as an "early opportunity", never a score penalty or a visibility claim.

## 35. Hidden-content check (extends section 22, JavaScript rendering)
- Content in accordions, tabs and "Read more" sections is often hidden in ways that remove it from the page source.
- `<details>` and `hidden="until-found"` keep the text in the HTML, so it stays readable by search engines and AI crawlers, findable with Find-in-page, and deep-linkable via URL fragments and text fragments.
- Content injected by script only on click is invisible to most AI crawlers. FAQs, prices, service lists and delivery areas are often hidden this way.
- **Check:** compare raw HTML with the fully expanded rendered page; flag important text present only after interaction.
- **Action:** recommend `<details>` (or `hidden="until-found"` when needed), with the exact sections affected.

## 36. Evaluation method for our recommendation engine
Copy the repo's evaluation approach:
- Per business type (florist, interior designer, dentist…): an **expectations** file listing what good recommendations must include and must avoid (e.g. no "add FAQ schema" without evidence; must cite the observed sources).
- A **grader** (rules + LLM judge) that scores each generated report against the expectations.
- A fixed **test set** of real businesses with saved audit data, re-run whenever prompts or models change.
- **Nightly evals** and a dashboard to track recommendation quality over time and catch regressions before customers see them.

## Not adopted
- `legacy-scan` scans source code; customers give us a URL, not their code.
- CSS, layout and UI guides don't affect AI visibility.
- Built-in AI APIs (on-device translation, summarization) aren't relevant to discoverability.


---

# Update 7 — Database Schema (draft v1)
**Updated: 20 November 2026**

## 37. PostgreSQL schema

File: `schema/schema.sql` (PostgreSQL 15+; 25 tables, 21 enums; parses cleanly with Postgres's own SQL parser, not yet run against a live database). Raw provider payloads go in JSONB; anything we query or count is a column. After v1, changes go through migrations (e.g. Alembic).

| Group | Tables | Holds |
|---|---|---|
| Business | `users`, `businesses`, `business_aliases`, `business_locations`, `services`, `competitors` | Profile with extracted / inferred / confirmed origin per field; target locations; alternate names for matching |
| Reference | `location_profiles`, `crawlers` | ~200–300 metro profiles (coords, locale, timezone, proxy target, last verified city); crawler registry by purpose (search / user fetch / training) |
| Audit | `audits`, `prompt_templates`, `audit_prompts` | Tier (free/paid), status, methodology version, config, timings for the 60 s target, cost, link to previous audit |
| AI runs | `platform_runs`, `responses`, `mentions`, `citations` | One row per call: platform, API vs app, model, search on/off, grounding, location method, server region, exit-IP city, run index, latency, tokens, cost. Answer text, search queries, maps places, screenshot. Businesses named (position, recommended vs mentioned, attributes, wrong facts). Cited URLs with source type |
| Search | `search_results` | Google / Bing / Maps results from SERP APIs, incl. rating and review count |
| Foundations | `foundation_checks`, `crawler_access`, `listings` | Every check with plain-language summary and evidence level (observed / likely / verified / submitted only); per-crawler robots rule, HTTP status, CDN challenge; GBP / Apple / Bing Places / Yelp listing consistency |
| Report & actions | `audit_metrics`, `recommendations` | Numerator and denominator behind every number; Action Center items with evidence links, priority, effort, confidence, best-practice flag, linked tool, draft, status, carried across re-audits |
| Evals | `eval_expectations`, `eval_runs`, `eval_scores` | Must / must-not rules per business type and scores per run |
| Queue | `jobs` | Postgres job queue for `SELECT … FOR UPDATE SKIP LOCKED` workers |

Design rules:
- Every reported number is stored as counts, never a bare percentage.
- Every recommendation points at the runs, citations or checks it rests on.
- `methodology_version` on every audit, so re-audits disclose method changes.
- `surface` (API / app) and `location_method` on every run, so reports can label "API view" vs "app view".
- `server_region` on every API run, because API answers follow the server's location (Test 1).

### Build order using the schema
1. Business profile: `businesses`, `business_locations`, `services` — URL in, profile out, owner confirms.
2. Foundation checks: `foundation_checks`, `crawler_access`, `crawlers` — no AI calls needed.
3. AI runs: `audits`, `audit_prompts`, `platform_runs`, `responses`, `mentions`, `citations` — free run first.
4. Report numbers: `audit_metrics`.
5. Actions: `recommendations`.
6. Search and listings: `search_results`, `listings`.
7. Evals and paid-audit extras: `eval_*`, `location_profiles`, app runs.


---

# Update 8 — Product Name
**Updated: 20 November 2026**

## 38. Working name: Spotted
"Did AI spot your business?" Chosen over Shortlisted, Jaada and Surface.

- **Surface / Surfaced rejected:** "Surfaced" is an existing GEO/AEO platform; "Surface" is a Microsoft trademark.
- **Existing products named Spotted:** none found in AI visibility, GEO or SEO (web search, 20 Nov 2026).
- **Domains (DNS check only, confirm with a registrar):**
  - Taken: spotted.ai and spotted.com (listed on Afternic marketplace — buyable, likely expensive), spotted.app, spotted.io, spotted.in, getspotted.ai, getspotted.com, getspotted.app, tryspotted.com, spottedby.ai, usespotted.com.
  - **spottedhq.com** is active on Vercel — check what it is before using "Spotted HQ".
  - No DNS record (may be free): **tryspotted.ai**, **spottedhq.ai**, **spotted.so**.
- **To do before launch:** register a domain, check what runs on spottedhq.com, and run a trademark search for "Spotted" (US USPTO and India, software class 9/42). "Spotted" is a common word, so a word-plus-design mark or a compound name (e.g. "Spotted AI") may be needed.


---

# Update 9 — Model Comparison (Test 2)
**Updated: 24 November 2026**

## 39. Which AI models are worth running?
Same three Dallas florist prompts, 3 runs each, 117 calls. Business names were extracted with gemini-3.8-flash; names not seen in any app or Google Maps answer were checked with Gemini + Google Search. Code and raw results: `research/model_compare/` (compare_models.py, results/20261124-014456).

| Model | Web search | Overlap with apps | Run-to-run | Real & open Dallas florists | Avg seconds |
|---|---|---|---|---|---|
| Claude Haiku 5.5 (OpenRouter `:online`) | yes | 27% | 61% | 95% | 11 |
| Gemini 3.8 Flash + Google Maps (Dallas lat/lng) | yes | 24% | 71% | 100% | 19 |
| Gemini 3.8 Flash + Google Search | yes | 24% | 63% | 95% | 15 |
| GPT-5 mini (OpenRouter `:online`, 1 answer) | yes | 21% | – | 100% | 22 |
| Perplexity Sonar | yes | 16% | 41% | 95% | 6 |
| Gemini 3.8 Flash, no tools | no | 15% | 30% | 91% | 16 |
| Kimi K3.1 Pro (NVIDIA) | no | 17% | 66% | 88% | 175 |
| MiniMax, Nemotron Ultra/Lightning, Mistral Large, Gemma 4 (NVIDIA) | no | 2–4% | 17–58% | 81–92% | 7–126 |

Findings:
1. **Only web-search models are worth running.** They overlap 16–27% with what the apps showed (in line with section 27's 21–32%) and name real, open businesses 95–100% of the time.
2. **Models without search are not useful for local visibility.** 2–17% overlap; they named closed shops (Cebolla Fine Flowers, Randy's Flowers), shops in other cities (Bachman's, J. Morris Flowers), non-florists (CB2, Dempsey's) and businesses that don't exist (Deep Ellum Florist, Luna & Grove). Several asked for a location on "near me". Kimi and Mistral took 2–3 minutes per answer.
3. **"Model knowledge" runs still have a narrow use:** in the paid audit, a search-off run shows what a model remembers about the business; never as the visibility score.
4. **Even web-search models name closed businesses** (Cebolla Fine Flowers via Claude and Gemini, Freesia via Perplexity) — worth reporting to competitors' disadvantage, and a reason to verify names before showing them as "recommended instead of you".
5. **Cost:** answers + name extraction + checks for 117 calls ≈ $0.85 in Gemini/OpenRouter tokens; Gemini grounding stayed within the 5,000 free requests a month.
6. **OpenRouter free accounts** ran out of credit after ~15 web-search calls; ChatGPT, Perplexity, Claude, Copilot and Google AI Mode are "Coming soon" in the product until direct keys are added.

## 40. Build status
- Steps 1–2: profile extraction, owner confirmation, foundation checks (MongoDB storage).
- Step 3 free run: up to 10 profile-based prompts, Gemini + Google Search and Gemini + Google Maps (target location geocoded with OpenStreetMap on confirm), all in parallel, results stream to the page; mentions, competitors, cited sources (typed: own site, competitor, directory, publication, marketplace…), wrong facts, and cost per run. Live test on DIRT Flowers (Dallas): named in 6 of 7 Search and 5 of 7 Maps answers; 16 calls, first answer 26 s, $0.17.
