"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">

  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <summary>
      The dominant sequence transduction models are based on complex recurrent
      or convolutional neural networks. We propose a new simple network
      architecture, the Transformer.
    </summary>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <arxiv:primary_category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <link rel="alternate" type="text/html" href="https://arxiv.org/abs/1706.03762"/>
    <link title="pdf" type="application/pdf" href="https://arxiv.org/pdf/1706.03762"/>
    <arxiv:doi>10.48550/arXiv.1706.03762</arxiv:doi>
    <arxiv:comment>15 pages, 5 figures. NIPS 2017.</arxiv:comment>
  </entry>

</feed>"""

EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
</feed>"""


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """`get_settings()` is `lru_cache`d process-wide; clear it between tests
    so env-var monkeypatches in one test can't leak into the next."""
    from arxiv_mcp.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def sample_feed() -> str:
    return SAMPLE_ATOM_FEED


@pytest.fixture
def empty_feed() -> str:
    return EMPTY_FEED
