"""Shared semantic boundary for reporting a source, explaining a rule and applying it."""

ANSWER_OBLIGATIONS = """
Determine completeness from what the ORIGINAL question asks the answer to establish:
* SOURCE REPORTING: when asked what a named source row/field records, report that exact
  value and its conditions. A field referring to another section is itself a valid
  attributed answer. Preserve the pointer; never invent the referenced content or
  claim a real case satisfies it. Do not require the entire referenced section merely
  to quote what the cell says. Such a literal field query may use cells mode.
* RULE EXPLANATION / HYPOTHETICAL: explain the quoted rule within its explicit class,
  year and exclusions. User-supplied hypothetical premises constrain the question;
  they are not source facts and must not be presented as verified real-world events.
  A necessary prerequisite remains necessary when another prerequisite is met.
  Quoting the rule requiring BOTH prerequisites can answer a scenario missing one;
  preserve that requirement and the source scope. Do not demand documentary proof
  that a hypothetical case is a real eligible member merely to explain the scoped
  rule. Conversely a sufficient path, optional item or alternative is not a universal
  necessary prerequisite; missing one alternative alone cannot prove ineligibility.
* ACTUAL CASE ASSESSMENT: certifying that a real case qualifies requires all applicable
  source conditions and case evidence. A quoted reference, a hypothetical assertion,
  a matching code or a summary row cannot by itself certify eligibility/approval.
These distinctions never waive source binding, requested scope/year, contradictions,
missing required evidence or independent verification. Keep required conditions in
public text. A source pointer alone does not answer a request to explain its contents.
The source can identify a rule by a code in a table while its body uses a class name.
document_position.role=location_only is a transport label for the original section's
physical position. It is NOT that row's subject or an applicability restriction;
the row's literal cells/headers and actual source rules must establish those roles.
Read exact same-source identity-row and ancestor-heading references as attribution
proof, together with the primary body's own subject and restrictions. They cannot
rescue a primary body about another subject or transfer a rule between groups.
"""
