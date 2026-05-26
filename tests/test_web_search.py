import pytest


"""
Live
"""

@pytest.mark.live
def test_live_web_search(db):
    result = db.web_search("diffbot knowledge graph", num_results=3)
    assert "search_results" in result
    assert len(result["search_results"]) > 0
