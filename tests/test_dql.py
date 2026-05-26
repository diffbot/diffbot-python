import pytest


"""
Live
"""

@pytest.mark.live
def test_live_dql(db):
    result = db.dql('type:Organization name:"Diffbot"', size=1)
    assert "data" in result
    assert len(result["data"]) > 0
    entity = result["data"][0]["entity"]
    assert entity.get("name") == "Diffbot"
