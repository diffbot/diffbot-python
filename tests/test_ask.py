import pytest


"""
Live
"""

@pytest.mark.live
def test_live_ask(db):
    chunks = list(db.ask([{"role": "user", "content": "What is Diffbot?"}]))
    response = "".join(chunks)
    assert len(response) > 0
