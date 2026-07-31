from fastmcp import FastMCP

CLAIM_CHECK = """
# Objective
Evaluate the scientific claim:
"{claim}"
Determine the extent to which the retrieved literature supports, contradicts, or refines this claim.

# Instructions
Search broadly enough to capture differing viewpoints.
Evaluate the evidence rather than counting supporting papers.

Differentiate between:
- supporting evidence
- contradictory evidence
- partial support
- conditional findings
- unresolved questions

Where consensus exists, describe it.
Where disagreement exists, explain the reasons rather than merely reporting conflicting conclusions.

# Output
Produce:
1. Claim summary
2. Supporting evidence
3. Contradictory evidence
4. Areas of agreement
5. Areas of disagreement
6. Current scientific consensus
7. Confidence assessment
8. References

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


PAPER_RECOMMENDER = """
# Objective
Recommend papers for the following goal:
"{goal}"
Optimize recommendations for the intended objective rather than citation count alone.

# Instructions
Determine the user's likely needs based on the requested goal.
Select papers that collectively provide the strongest learning or research path.

Consider factors such as:
- foundational importance
- clarity
- technical depth
- historical significance
- implementation value
- influence on later work
- relevance to the requested objective

Avoid recommending multiple papers that serve essentially the same purpose unless comparison is valuable.

# Output
Produce:
1. Understanding of the objective
2. Recommended papers
3. Why each paper was selected
4. Suggested reading order
5. Expected knowledge gained after completing the list
"""


TECHNIQUE_SELECTOR = """
# Objective
Recommend the most appropriate research techniques for solving the following problem:
"{problem}"
Recommendations should be based on evidence from the literature and the characteristics of the problem rather than popularity alone.

# Instructions
Identify the fundamental characteristics of the problem before recommending techniques.

Consider factors including:
- problem formulation
- data availability
- computational constraints
- interpretability
- scalability
- robustness
- theoretical guarantees
- implementation complexity

Compare multiple candidate techniques and explain the trade-offs between them.
Recommend alternatives when different assumptions or priorities would change the preferred approach.

# Output
Produce:
1. Problem analysis
2. Candidate techniques
3. Comparative evaluation
4. Recommended approach
5. Alternative approaches
6. Supporting literature
7. Rationale for the recommendation
"""


EVIDENCE_MATRIX = """
# Objective
Construct an evidence matrix for the research question:
"{question}"
The goal is to organize the available literature according to the conclusions it supports.

# Instructions
Search broadly enough to capture differing perspectives.
Group the literature according to the claims each paper supports rather than publication date.

Identify:
- supporting evidence
- contradictory evidence
- partial evidence
- inconclusive findings
- unanswered questions

Evaluate the strength of evidence presented by each group.
Clearly distinguish established consensus from areas of ongoing debate.

# Output
Produce:
1. Research question
2. Evidence matrix
3. Supporting literature
4. Contradictory literature
5. Areas of uncertainty
6. Current consensus
7. Remaining research questions

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="technique_selector",
        title="Technique Selector",
        description="Recommend and compare research techniques best suited to solving a given scientific or engineering problem.",
    )
    def technique_selector_prompt(problem: str) -> str:
        return TECHNIQUE_SELECTOR.format(problem=problem)

    @mcp.prompt(
        name="evidence_matrix",
        title="Evidence Matrix",
        description="Organize the literature into supporting, contradicting, partial, and inconclusive evidence for a research question.",
    )
    def evidence_matrix_prompt(question: str) -> str:
        return EVIDENCE_MATRIX.format(question=question)

    @mcp.prompt(
        name="paper_recommender",
        title="Paper Recommender",
        description="Recommend research papers tailored to a specific learning, implementation, or research objective.",
    )
    def paper_recommender_prompt(goal: str) -> str:
        return PAPER_RECOMMENDER.format(goal=goal)

    @mcp.prompt(
        name="claim_check",
        title="Scientific Claim Check",
        description="Evaluate whether the scientific literature supports, contradicts, or refines a research claim.",
    )
    def claim_check_prompt(claim: str) -> str:
        return CLAIM_CHECK.format(claim=claim)
