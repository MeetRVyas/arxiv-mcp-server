from fastmcp import FastMCP

PAPER_COMPARISON = """
# Objective
Compare the provided papers as competing or complementary approaches to a similar research problem.
Base the comparison on the retrieved papers rather than prior knowledge.

# Papers
{papers}

# Instructions
Retrieve complete information for every paper before comparing them.
Look beyond the paper abstracts.

Compare the papers from multiple perspectives, including:
- research motivation
- problem formulation
- methodology
- assumptions
- experimental design
- datasets
- evaluation metrics
- strengths
- weaknesses
- limitations
- claimed contributions
- practical applicability

Identify where papers agree, differ, improve upon one another, or solve different aspects of the problem.
Avoid treating newer papers as inherently superior.

# Output
Produce:
1. Executive summary
2. Comparison table
3. Detailed comparative analysis
4. Major similarities
5. Major differences
6. Strengths and weaknesses of each paper
7. Recommended reading order depending on different goals
8. Overall conclusions
"""


PAPER_CRITIQUE = """
# Objective
Provide a balanced academic critique of paper "{arxiv_id}".
Evaluate both the paper itself and how subsequent research has responded to it.

# Instructions
Study the paper together with its citation context.

Assess:
- significance of the research problem
- soundness of the methodology
- quality of experimental evaluation
- strengths
- limitations
- assumptions
- reproducibility
- practical usefulness

Determine whether later work extended, challenged, refined, or superseded its conclusions.
Avoid hindsight bias and evaluate the paper within the context of its publication period.

# Output
Produce:
1. Paper overview
2. Major contributions
3. Strengths
4. Limitations
5. Influence on later work
6. How well the paper has aged
7. Overall assessment
"""


RESEARCH_LINEAGE = """
# Objective
Explain how the ideas behind paper "{arxiv_id}" evolved.
Go beyond identifying references—construct the intellectual lineage that led to the paper.

# Instructions
Study the paper together with the work it builds upon.
Identify the sequence of important ideas, how each contributed to later developments, and why the chosen paper became possible.
Focus on conceptual evolution rather than publication chronology alone.
Where multiple research directions converged, explain how they influenced one another.
Clearly distinguish established historical developments from your own synthesis.

# Output
Produce:
1. Overview
2. Foundations of the field
3. Major milestones
4. Evolution of ideas
5. How the selected paper fits into the lineage
6. Key conceptual breakthroughs
7. Lasting impact on subsequent research
"""


AUTHOR_PROFILE = """
# Objective
Analyze the research career of "{author}".
Identify how their research interests, contributions, and impact have evolved over time.

# Instructions
Study the author's publication history as a whole rather than evaluating papers independently.
Identify recurring themes, shifts in research direction, collaborations where relevant, and major scientific contributions.
Highlight influential work and explain why it became significant.
Focus on the evolution of ideas rather than publication counts.

# Output
Produce:
1. Career overview
2. Major research themes
3. Evolution of research interests
4. Most influential contributions
5. Representative papers
6. Research impact
7. Overall assessment of the author's body of work
"""


CITATION_SUMMARY = """
# Objective
Explain why paper "{arxiv_id}" became influential.
The goal is to understand the nature of its impact rather than simply reporting citation counts.

# Instructions
Study both the paper and the work that cites it.

Identify:
- ideas that were widely adopted
- concepts that inspired later work
- applications enabled by the paper
- techniques that became standard
- limitations discovered by later research

Differentiate between influence through extension, application, comparison, and criticism.
Focus on explaining the paper's scientific legacy.

# Output
Produce:
1. Paper overview
2. Reasons for its influence
3. Major ideas adopted by the community
4. How later work built upon it
5. Criticisms and limitations
6. Overall scientific legacy
"""


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="paper_comparison",
        title="Compare Papers",
        description="Compare multiple research papers across methodology, assumptions, evaluation, strengths, limitations, and contributions.",
    )
    def paper_comparison_prompt(arxiv_ids: list[str]) -> str:
        return PAPER_COMPARISON.format(papers="\n".join(f"- {paper_id}" for paper_id in arxiv_ids))

    @mcp.prompt(
        name="research_lineage",
        title="Research Lineage",
        description="Trace the intellectual foundations and evolution of ideas leading to an ArXiv paper.",
    )
    def research_lineage_prompt(arxiv_id: str) -> str:
        return RESEARCH_LINEAGE.format(arxiv_id=arxiv_id)

    @mcp.prompt(
        name="paper_critique",
        title="Paper Critique",
        description="Critically evaluate an ArXiv paper by assessing its methodology, evidence, limitations, and long-term influence.",
    )
    def paper_critique_prompt(arxiv_id: str) -> str:
        return PAPER_CRITIQUE.format(arxiv_id=arxiv_id)

    @mcp.prompt(
        name="author_profile",
        title="Author Profile",
        description="Analyze a researcher's publications, evolving research interests, major contributions, and scientific impact.",
    )
    def author_profile_prompt(author: str) -> str:
        return AUTHOR_PROFILE.format(author=author)

    @mcp.prompt(
        name="citation_summary",
        title="Citation Summary",
        description="Explain why a paper became influential by analyzing how later research adopted, extended, or challenged its ideas.",
    )
    def citation_summary_prompt(arxiv_id: str) -> str:
        return CITATION_SUMMARY.format(arxiv_id=arxiv_id)
