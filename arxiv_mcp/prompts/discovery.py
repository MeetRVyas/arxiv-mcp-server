from mcp.server.fastmcp import FastMCP

FIND_RELATED_WORK = """
# Objective
Identify literature that is most relevant to "{topic_or_paper}".
The goal is to build a meaningful set of related work rather than maximize the number of retrieved papers.

# Instructions
Search broadly enough to identify foundational work, closely related research, competing approaches, complementary techniques, surveys, and recent developments.
Select papers based on conceptual relevance rather than keyword overlap alone.
For each recommended paper, explain why it is relevant and how it relates to the requested topic or paper.

Classify related work where appropriate, such as:
- foundational work
- direct extensions
- competing approaches
- complementary methods
- applications
- surveys
- recent advances

Avoid recommending papers that serve essentially the same purpose unless comparison provides additional value.

# Output
Produce:
1. Summary of the research area
2. Categorized related work
3. Relationship of each paper to the topic
4. Recommended reading order
5. Important observations
6. References

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


GAP_SPOTTER = """
# Objective
Identify meaningful research opportunities in the literature surrounding "{topic}".
Base your conclusions on evidence from the retrieved literature rather than speculation.

# Instructions
Study the current body of work before identifying gaps.

Analyze the literature from multiple perspectives, including but not limited to:
- unexplored research problems
- conflicting findings
- methodological limitations
- missing benchmarks
- missing datasets
- unrealistic assumptions
- scalability limitations
- evaluation weaknesses
- reproducibility concerns
- opportunities for algorithmic improvement

Differentiate between well-established conclusions, emerging evidence, and your own synthesis.

Prioritize research gaps according to:
- novelty
- scientific significance
- feasibility
- expected research impact

# Output
Produce a structured research gap analysis containing:
1. Overview of the field
2. Current state of research
3. Identified research gaps
4. Supporting evidence
5. Promising future research directions
6. Highest-priority opportunities

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


NOVELTY_CHECKER = """
# Objective
Evaluate the novelty of the following research idea:
"{idea}"
Assess the idea against the existing literature without assuming it is either novel or already solved.

# Instructions
Search broadly for related work.
Identify literature addressing similar ideas, methodologies, objectives, or assumptions.

Evaluate:
- conceptual similarity
- methodological similarity
- novelty of the proposed contribution
- incremental versus substantial differences
- existing limitations the idea may overcome
- prior attempts at similar ideas

Where similar work exists, explain precisely how the proposed idea differs.
Where novelty appears limited, suggest directions that may increase originality.
Avoid making definitive claims of novelty based only on retrieved literature.

# Output
Produce:
1. Summary of the proposed idea
2. Closest existing work
3. Similarities
4. Differences
5. Assessment of novelty
6. Potential contributions
7. Suggestions for strengthening originality
8. Confidence assessment
"""


CROSS_DOMAIN_BRIDGE = """
# Objective
Identify opportunities to transfer ideas between "{domain_a}" and "{domain_b}".
Focus on conceptual connections that could inspire new research rather than superficial similarities.

# Instructions
Study both research areas independently before comparing them.

Identify:
- shared research problems
- transferable methodologies
- analogous assumptions
- complementary strengths
- opportunities for interdisciplinary research

Distinguish established interdisciplinary work from speculative opportunities.
Support proposed connections with evidence wherever possible.

# Output
Produce:
1. Overview of both domains
2. Shared concepts
3. Transferable methodologies
4. Existing cross-domain research
5. Novel interdisciplinary opportunities
6. Promising research directions
7. Assessment of feasibility
"""


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="find_related_work",
        title="Find Related Work",
        description="Discover and organize foundational, competing, complementary, and recent papers related to a research topic or paper.",
    )
    def find_related_work_prompt(topic_or_paper: str) -> str:
        return FIND_RELATED_WORK.format(topic_or_paper = topic_or_paper)


    @mcp.prompt(
        name="gap_spotter",
        title="Research Gap Spotter",
        description="Identify evidence-backed research gaps, methodological limitations, conflicting findings, and promising future directions.",
    )
    def gap_spotter_prompt(topic: str) -> str:
        return GAP_SPOTTER.format(topic = topic)

    @mcp.prompt(
        name="novelty_checker",
        title="Novelty Checker",
        description="Assess the originality of a research idea by comparing it against existing literature and identifying similar work.",
    )
    def novelty_checker_prompt(idea: str) -> str:
        return NOVELTY_CHECKER.format(idea = idea)


    @mcp.prompt(
        name="cross_domain_bridge",
        title="Cross-Domain Bridge",
        description="Discover meaningful conceptual and methodological connections between two research domains.",
    )
    def cross_domain_bridge_prompt(domain_a: str, domain_b: str) -> str:
        return CROSS_DOMAIN_BRIDGE.format(
            domain_a = domain_a,
            domain_b = domain_b
        )