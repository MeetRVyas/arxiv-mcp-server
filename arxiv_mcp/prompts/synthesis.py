from mcp.server.fastmcp import FastMCP

LITERATURE_REVIEW = """
# Objective
Produce a comprehensive literature review on "{topic}".
Develop a coherent understanding of the research landscape by synthesizing evidence from the literature rather than summarizing papers individually.

# Instructions
Search broadly enough to capture foundational work, influential papers, surveys, and recent developments.
Organize the literature into meaningful research themes instead of publication chronology.

For each theme, identify:
- key research questions
- representative papers
- major methodologies
- significant findings
- strengths
- limitations

Analyze how the field has evolved over time, where research converges or diverges, and what challenges remain.
Clearly distinguish established findings from your own synthesis.
Avoid treating citation count or publication date as indicators of research quality.

# Output
Produce:
1. Executive summary
2. Overview of the research landscape
3. Major research themes
4. Comparative analysis across themes
5. Evolution of the field
6. Current challenges
7. Open research questions
8. Conclusions
9. References

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


SURVEY_GENERATOR = """
You are an experienced researcher writing the foundation of an academic survey paper.

# Objective
Produce a comprehensive survey of "{topic}" by synthesizing the retrieved literature into a coherent understanding of the field.

# Instructions
Identify the major research directions and organize the literature into meaningful themes rather than simply summarizing papers individually.
Analyze how methodologies evolved, where approaches differ, what problems they solve, and the trade-offs between them.
Highlight recurring evaluation practices, strengths, weaknesses, and remaining challenges.
Clearly distinguish evidence from the literature from your own synthesis.

# Output
Produce a survey-style document including:
- Introduction
- Taxonomy of approaches
- Major research themes
- Representative papers
- Comparative analysis
- Current challenges
- Future research directions
"""


FIELD_DIGEST = """
# Objective
Produce a research digest summarizing recent developments within the requested field.
The goal is to identify emerging research directions rather than summarize papers individually.

# Input
- Field: {topic}
- Time Window: {time_window}
- Categories: {categories}

# Instructions
Analyze recent publications across the requested categories and time window.
Group papers into coherent research themes.

Identify:
- emerging topics
- recurring ideas
- new methodologies
- notable applications
- research trends
- surprising developments

Highlight themes that appear to be gaining momentum as well as areas showing slower progress.
Avoid simply listing papers in chronological order.

# Output
Produce:
1. Executive summary
2. Emerging research themes
3. Representative papers for each theme
4. Notable trends
5. Areas receiving increasing attention
6. Interesting observations
7. Topics worth monitoring in the near future
"""


STATE_OF_THE_ART = """
# Objective
Determine the current state of the art for "{topic}".
Identify the strongest existing methods, the problems they solve, and the challenges that remain.

# Instructions
Analyze recent and influential literature rather than relying solely on publication dates.
Compare leading approaches using their reported evidence.

Discuss:
- leading methodologies
- benchmark performance
- strengths
- weaknesses
- practical trade-offs
- computational requirements
- scalability
- robustness

Distinguish mature techniques from emerging approaches.
Avoid assuming that the most recent paper represents the current state of the art.

# Output
Produce:
1. Executive summary
2. Current leading approaches
3. Comparative analysis
4. Benchmark landscape
5. Remaining challenges
6. Open research questions
7. Outlook for the field

# Important Considerations
- Base conclusions on evidence from the retrieved literature.
- Clearly distinguish evidence from interpretation.
- Acknowledge uncertainty where evidence is limited or conflicting.
- Prefer synthesis over enumeration.
"""


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="literature_review",
        title="Literature Review",
        description="Conduct a comprehensive literature review by synthesizing foundational, influential, and recent research into coherent themes.",
    )
    def literature_review_prompt(topic: str) -> str:
        return LITERATURE_REVIEW.format(topic = topic)


    @mcp.prompt(
        name="survey_generator",
        title="Survey Generator",
        description="Generate a survey-style synthesis of a research field by organizing the literature into themes, comparing approaches, and identifying future directions.",
    )
    def survey_generator_prompt(topic: str) -> str:
        return SURVEY_GENERATOR.format(topic = topic)


    @mcp.prompt(
        name="field_digest",
        title="Field Digest",
        description="Summarize recent developments in a research field by identifying emerging themes, trends, and representative papers.",
    )
    def field_digest_prompt(
        topic: str,
        time_window: str = "last 30 days",
        categories: list[str] | None = None,
    ) -> str:
        return FIELD_DIGEST.format(
            topic=topic,
            time_window=time_window,
            categories=", ".join(categories) if categories else "Auto-detect",
        )


    @mcp.prompt(
        name="state_of_the_art",
        title="State of the Art",
        description="Identify and compare the current leading approaches, benchmarks, and open challenges in a research area.",
    )
    def state_of_the_art_prompt(topic: str) -> str:
        return STATE_OF_THE_ART.format(topic = topic)