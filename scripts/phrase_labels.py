"""
Classify TF-IDF phrases into Hard vs Soft skills, or drop recruiting boilerplate.

Hard ≈ tools, domain methods, regulations, technical procedures (not people-skills lexicon).
Soft ≈ overlap with a lexicon of interpersonal / communication-style terms.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

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
    """.split()
)


def categorize_phrase(phrase: str) -> Optional[Literal["hard", "soft"]]:
    """
    Return 'soft' if soft-skill lexicon hits; 'hard' for other non-boilerplate skill-like
    phrases; None to omit (titles, recruiting fluff, generic tokens).
    """
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
        if w in _SINGLE_DROP:
            return None
        return "hard"

    # Multi-word: drop if every word is a junk singleton token
    if all(w in _SINGLE_DROP for w in words):
        return None

    # Keep domain / tool-like phrases (e.g. employment law, civil litigation, microsoft excel)
    return "hard"


def is_boilerplate(phrase: str) -> bool:
    """True if phrase should not appear in charts at all."""
    return categorize_phrase(phrase) is None
