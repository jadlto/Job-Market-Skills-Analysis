"""
Label TF-IDF phrases for the dashboard: hard vs soft skills, dropping non-relevant text.

Primary signal is ``skill_classifier.predict_skill_label`` (TF-IDF + logistic regression on
bundled seed labels). Lexicon rules in ``_legacy_categorize`` apply only if prediction fails.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from skill_classifier import predict_skill_label

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


def _should_omit_as_boilerplate(phrase: str) -> bool:
    """Recruiting / JD noise; must run before ML so lexicon drops are not overridden."""
    pl = phrase.strip().lower()
    if not pl:
        return True
    if pl in _PHRASE_DROP:
        return True
    words = pl.split()
    if len(words) == 1:
        if words[0] in _SINGLE_DROP:
            return True
        if words[0] in _BROAD_DOMAIN_UNIGRAM_DROP:
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
        if w in _SINGLE_DROP or w in _BROAD_DOMAIN_UNIGRAM_DROP:
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
