"""
Label skill phrases for charts: O*NET session overrides (when present), else lexicon drops
and ``skill_classifier.predict_skill_label`` for TF-IDF fallback; ``_legacy_categorize``
runs only if prediction fails.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from skill_classifier import predict_skill_label

# Set by skill_analyzer when using O*NET extraction; also loaded from disk in dashboard.
_SESSION_ONET_HARD: frozenset[str] | None = None
_SESSION_ONET_SOFT: frozenset[str] | None = None


def set_onet_session_overrides(
    hard: frozenset[str] | None,
    soft: frozenset[str] | None,
) -> None:
    """Lowercased Technology Skill examples (hard) and Skills elements (soft)."""
    global _SESSION_ONET_HARD, _SESSION_ONET_SOFT
    _SESSION_ONET_HARD, _SESSION_ONET_SOFT = hard, soft


# Soft skills / interpersonal signals (token match inside phrase).
_SOFT_LEXICON = frozenset(
    """
    communication leadership negotiation collaboration teamwork presentation interpersonal
    mentoring coaching empathy listening writing speaking stakeholder relationship persuasion
    influence facilitation adaptability diplomacy consensus collaborative organizational
    verbal oral written multicultural diversity inclusion problem solving critical thinking
    conflict resolution customer service detail oriented self motivated cross functional
    emotional intelligence decision making strategic planning public speaking active listening
    time management accountability initiative proactive resilience flexibility relationship
    building people skills client facing executive presence thought coaching facilitating
    mediation negotiate negotiates negotiating inspires compassionate patience tact discretion
    judgement judgment analytical creative strategic executive written interpersonal social
    multicultural inclusive servant authentic transparency trustworthy trust honesty integrity
    ethical compliant deadlines multitasking prioritization deadline organizational skills
    research skills writing skills analytical skills presentation skills listening skills
    oral written verbal interpersonal skills communication skills leadership skills
    management skills organizational skills teamwork skills collaborative skills
    """.split()
)

# Exact phrases (lowercase) that are never skills — recruiting / meta language.
_PHRASE_DROP = frozenset(
    """
    entry level mid level senior level associate level staff level
    equal opportunity pay equity pay transparency at will employment
    full time part time drug screen background check local attorney
    growing team growing firm growing company growing practice fast paced environment
    equal employment opportunity eeo aa veteran disability status
    """.split()
)

# Single-token junk common in job boards (not domain tools). "employment" alone is noise;
# bigrams like "employment law" stay (handled by phrase rules).
_SINGLE_DROP = frozenset(
    """
    attorney attorneys lawyer lawyers associate associates counsel paralegal solicitor
    partner partners clerk clerks growing sought seeking seek hiring hired recruit
    recruitment candidate candidates applicant applicants applicant position positions
    job jobs listing listings opening openings vacancy vacancies posting postings
    salary salaries wage wages hourly bonus benefits perk perks vacation equity 401k
    remote hybrid onsite relocation travel flexible schedule schedules resume resumes
    apply applying application interview interviews submission submissions coordinator
    recruiter recruiters staffing personnel workforce employer employers employee employees
    department departments division divisions organization organizations firm firms office
    offices company companies team teams employer staffing hiring recruitment career
    careers opportunity opportunities employment listing posted listing description
    requirements qualifications preferred minimum desired necessary plus required requires
    supervisor supervisory supervising manages managing managed oversees overseeing reports
    reporting directly indirectly internship internships exempt nonexempt overtime eligible
    eligibility sponsorship sponsor h1b clearance authorized authorization nationwide
    nationally regional regions global fortune industry sector vertical premier
    leading leader fastest dynamic innovation passionate passion driven cutting edge
    excellence excellent established reputation recognized recognition award awards ranked
    ranking rankings tier glassdoor indeed linkedin headquartered headquarters campus campuses
    states state province provinces country countries nationwide statewide locally local
    nationally joining join participated participation collaborative excellence world class
    competitive compensation negotiable commensurate annual annually hourly weekly monthly
    quarterly signing retention relocation bonus stock options package packages band bands
    grade grades step steps ladder level levels entry senior junior mid staff associate
    employment firm company corporation llc inc plc corp team group practice area office
    experience experiences insurance enterprise technology business
    looking looks
    """.split()
)

# Vague domain nouns that often surface from TF-IDF but are not concrete tools (SQL, Python, …).
# Only applied to single-token phrases so bigrams like "data analysis" still go to the classifier.
_BROAD_DOMAIN_UNIGRAM_DROP = frozenset(
    """
    analysis analyses reporting analytics insight insights metric metrics
    visualization visualisation forecasting
    """.split()
)

# JD filler verbs/adjectives (single-token only) — keep off soft-skill words like
# communication, collaboration, leadership, agile, scrum, presentation, negotiation, …
_JD_PROSE_DROP = frozenset(
    """
    ensure ensures ensuring assured assure assures assuring
    strong stronger strongest weak weaker weakly
    decision decisions decisive
    validation validations validate validates validated validity verify verifies verified
    various multiple several certain generally typically usually often occasionally frequently
    including included excludes excluding exclude following follows follow
    based using use uses used utilizing utilizes utilized useful
    important critical essential desirable demonstrated demonstrate demonstrates
    participate participates participating participation contributed contribute contributes contributing
    excellent excellence outstanding proficient adequately
    relevant relevance familiarity familiar understands understanding understood
    preferred minimum maximum optimal wishes wish wishing
    goals objectives objective tactical operational operationalize
    execute executes executing execution performs performing performed deliver delivers delivered
    maintain maintains maintained maintenance improve improves improving improvement improved
    develop develops developing developed development design designs designed designing
    implement implements implementing implemented establish establishes established establishing
    identify identifies identifying identified determine determines determining determined determination
    analyze analyzes analyzing analyse analyse assessed assessing assessments assessment
    evaluate evaluates evaluating evaluated evaluation recommends recommending recommendation
    justify justified supporting supports supported oversight supervise supervised supervises
    oversee oversees overseeing monitor monitors monitoring monitored review reviews reviewing reviewed
    prepare prepares preparing prepared readiness timely timelines timeline milestones
    approximately roughly estimated estimates estimate summaries summary outlined outline listing lists listed
    comprehensive partially partial participation contributions deadlines deadline prioritize prioritized
    primarily principally mainly largely substantially materially exclusively solely
    furthermore moreover additionally besides accordingly hence thus therefore consequently
    overall holistic aggregate aggregated consolidated consolidate notable notably emphasis emphasize
    amongst among between throughout via per equally likewise similarly unlike versus
    """.split()
)

# Role/organization nouns surfaced as “skills” (single-token only).
_GENERIC_ROLE_THING_DROP = frozenset(
    """
    product products service services solution solutions offering offerings deliverable deliverables
    capability capabilities feature features function functions module modules component components
    platform platforms system systems application applications software hardware dataset datasets
    database databases warehouse warehouses pipeline pipelines workflow workflows process processes
    procedure procedures operation operations initiative initiatives program programs project projects
    portfolio portfolios engagement engagements role roles title titles category categories
    domain domains field fields sector sectors vertical verticals industry industries market markets
    segment segments business businesses enterprise enterprises organization organizations company companies
    firm firms group groups vendor vendors supplier suppliers partnership partnerships account accounts
    """.split()
)


def reject_raw_tfidf_term(term: str) -> bool:
    """
    Drop vector terms before scoring/heuristics: pure numbers, Section/list artifacts, etc.
    Raw terms from sklearn are typically lowercased by the vectorizer.
    """
    t = (term or "").strip().lower()
    if not t:
        return True
    if re.fullmatch(r"[\d,\.\s]+$", t):
        return True
    if t in {"id", "ids", "req", "reqs", "ref", "no", "yes", "na", "n/a"}:
        return True
    return False


def _should_omit_as_boilerplate(phrase: str) -> bool:
    """Recruiting / JD noise; must run before ML so lexicon drops are not overridden."""
    pl = phrase.strip().lower()
    if not pl:
        return True
    if pl in _PHRASE_DROP:
        return True
    words = pl.split()
    if len(words) == 1:
        w = words[0]
        if w in _SINGLE_DROP:
            return True
        if w in _BROAD_DOMAIN_UNIGRAM_DROP:
            return True
        if w in _JD_PROSE_DROP:
            return True
        if w in _GENERIC_ROLE_THING_DROP:
            return True
        return False
    if all(w in _SINGLE_DROP for w in words):
        return True
    return False


def _legacy_categorize(phrase: str) -> Optional[Literal["hard", "soft"]]:
    """TF-IDF-era heuristic when ML is unavailable."""
    pl = phrase.strip().lower()
    if not pl:
        return None

    if pl in _PHRASE_DROP:
        return None

    tokens = set(re.findall(r"[a-z]+", pl))
    if tokens & _SOFT_LEXICON:
        return "soft"

    words = pl.split()

    if len(words) == 1:
        w = words[0]
        if (
            w in _SINGLE_DROP
            or w in _BROAD_DOMAIN_UNIGRAM_DROP
            or w in _JD_PROSE_DROP
            or w in _GENERIC_ROLE_THING_DROP
        ):
            return None
        return "hard"

    if all(w in _SINGLE_DROP for w in words):
        return None

    return "hard"


def categorize_phrase(phrase: str) -> Optional[Literal["hard", "soft"]]:
    """
    Labels phrases with a small TF-IDF + logistic model (hard / soft / non-relevant),
    keeping only hard & soft for downstream charts. Non-relevant maps to None.

    Falls back to lexicon rules if prediction fails.
    """
    pl = phrase.strip()
    if not pl:
        return None
    if reject_raw_tfidf_term(pl):
        return None
    plow = pl.strip().lower()
    if _SESSION_ONET_HARD and plow in _SESSION_ONET_HARD:
        return "hard"
    if _SESSION_ONET_SOFT and plow in _SESSION_ONET_SOFT:
        return "soft"
    if _should_omit_as_boilerplate(pl):
        return None
    try:
        lab = predict_skill_label(pl)
    except Exception:
        return _legacy_categorize(pl)
    if lab == "non_relevant":
        return None
    return lab  # hard | soft


def is_boilerplate(phrase: str) -> bool:
    """True if phrase should not appear in charts at all."""
    return categorize_phrase(phrase) is None
