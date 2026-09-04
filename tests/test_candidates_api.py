"""End-to-end: trigger a screening run, then read it back through the API
— proves the service, persistence, and routing are wired together
correctly (requirements.md section 4.1's "persist each screening run")."""
from __future__ import annotations


async def test_trigger_then_list_candidates_and_runs(client):
    trigger_response = await client.post("/api/v1/candidates/run")
    assert trigger_response.status_code == 200
    run = trigger_response.json()
    assert run["candidate_count"] >= 0
    assert run["universe_size"] > 0

    candidates_response = await client.get("/api/v1/candidates")
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()
    assert len(candidates) == run["candidate_count"]
    if len(candidates) > 1:
        scores = [c["score"] for c in candidates]
        assert scores == sorted(scores, reverse=True)
    for candidate in candidates:
        assert candidate["run_id"] == run["run_id"]

    runs_response = await client.get("/api/v1/candidates/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert any(r["run_id"] == run["run_id"] for r in runs)

    scoped_response = await client.get(f"/api/v1/candidates?run_id={run['run_id']}")
    assert scoped_response.status_code == 200
    assert len(scoped_response.json()) == run["candidate_count"]
