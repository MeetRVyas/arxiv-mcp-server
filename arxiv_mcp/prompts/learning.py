from fastmcp import FastMCP

EXPLAIN_PAPER = """
# Objective
Explain paper "{arxiv_id}" at a level appropriate for the intended audience.
Your goal is to develop understanding rather than summarize sections of the paper.

# Instructions
Determine the depth of explanation based on the requested audience or infer a reasonable level when unspecified.

Explain:
- the problem being addressed
- why it matters
- the intuition behind the proposed approach
- methodology
- experimental evaluation
- key findings
- limitations
- practical implications

Where appropriate, introduce prerequisite concepts before explaining advanced ideas.
Clarify terminology and assumptions without oversimplifying the technical contributions.
Avoid reproducing the structure of the paper section by section unless it improves understanding.

# Output
Produce:
1. Executive summary
2. Problem and motivation
3. Core intuition
4. Methodology explained
5. Experimental evaluation
6. Main contributions
7. Limitations
8. Key takeaways
9. Suggested next reading
"""


METHOD_EVOLUTION = """
# Objective
Explain how the method or technique "{method}" evolved over time.
The objective is to understand the progression of the underlying idea rather than individual papers.

# Instructions
Identify the foundational work introducing the method and trace the important refinements that followed.

Explain:
- why each improvement was proposed
- what limitations it addressed
- how it changed the methodology
- what challenges remained

Highlight conceptual rather than incremental improvements.
Where multiple variants emerged, explain why they diverged.

# Output
Produce:
1. Overview of the method
2. Origins
3. Major evolutionary stages
4. Significant innovations
5. Current state of the method
6. Remaining challenges
7. Future directions
"""


RESEARCH_BRIEF = """
# Objective
Produce an executive research briefing on "{topic}".
The briefing should enable an informed reader to quickly understand the field, its current direction, and its significance.

# Instructions
Synthesize the literature into a concise, high-information overview.
Prioritize understanding over completeness.
Cover the most influential work, dominant methodologies, current trends, important challenges, and future opportunities.
Avoid excessive detail while maintaining scientific accuracy.

# Output
Produce:
1. Executive summary
2. Why the topic matters
3. Major research directions
4. Key papers
5. Current trends
6. Open challenges
7. Recommended next reading

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


RESEARCH_MENTOR = """
# Role
You are an experienced research mentor helping someone develop expertise in a research area.
Adapt your guidance to the user's background, goals, and current level of understanding.

# Objective
Help the user learn, navigate, and contribute to the research area surrounding "{topic}".
Your objective is not simply to recommend papers, but to build understanding and guide continued learning.

# Instructions
Determine an appropriate learning path based on the user's experience and objectives.

Identify:
- foundational papers
- milestone papers
- influential surveys
- recent advances
- important authors
- major research directions
- open problems

Explain why each recommendation matters and how it connects to previous work.
Where appropriate, recommend implementation papers before highly theoretical ones.
Highlight common misconceptions, prerequisites, and topics requiring deeper study.
Encourage progression toward independent research rather than passive reading.

# Output
Produce:
1. Assessment of the research area
2. Personalized learning strategy
3. Recommended reading path
4. Important concepts to master
5. Suggested implementation opportunities
6. Open research problems
7. Recommended next steps
"""


RESEARCH_TIMELINE = """
# Objective
Construct a chronological narrative of how "{topic}" evolved into its current state.
The goal is to explain the progression of ideas rather than simply listing influential papers.

# Instructions
Identify the major milestones in the field, including foundational work, paradigm shifts, influential breakthroughs, and significant refinements.
Explain why each milestone mattered and how it changed subsequent research.
When multiple research directions emerged simultaneously, describe how they diverged, interacted, or converged over time.
Focus on the evolution of ideas, methodologies, and scientific understanding.

# Output
Produce:
1. Executive summary
2. Timeline of major milestones
3. Key conceptual breakthroughs
4. Evolution of methodologies
5. Turning points in the field
6. Current direction of research
7. Likely future evolution
"""


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="explain_paper",
        title="Explain Paper",
        description="Explain an ArXiv paper by developing conceptual understanding of its motivation, methodology, findings, and significance.",
    )
    def explain_paper_prompt(arxiv_id: str) -> str:
        return EXPLAIN_PAPER.format(arxiv_id=arxiv_id)

    @mcp.prompt(
        name="research_timeline",
        title="Research Timeline",
        description="Construct a chronological narrative of how a research field evolved through major milestones and breakthroughs.",
    )
    def research_timeline_prompt(topic: str) -> str:
        return RESEARCH_TIMELINE.format(topic=topic)

    @mcp.prompt(
        name="method_evolution",
        title="Method Evolution",
        description="Trace how a research method or technique evolved through major conceptual and methodological improvements.",
    )
    def method_evolution_prompt(method: str) -> str:
        return METHOD_EVOLUTION.format(method=method)

    @mcp.prompt(
        name="research_brief",
        title="Research Brief",
        description="Produce a concise executive briefing summarizing the current state and direction of a research area.",
    )
    def research_brief_prompt(topic: str) -> str:
        return RESEARCH_BRIEF.format(topic=topic)

    @mcp.prompt(
        name="research_mentor",
        title="Research Mentor",
        description="Act as an adaptive research mentor by guiding learning, recommending literature, and suggesting future research directions.",
    )
    def research_mentor_prompt(topic: str) -> str:
        return RESEARCH_MENTOR.format(topic=topic)
