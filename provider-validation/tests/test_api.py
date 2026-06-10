"""API-layer tests: parity with the engine, determinism, transport errors, no leakage.

The most important guarantee is *parity*: the API must add no divergence from a
direct ``engine.decision_engine.decide()`` call.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine.decision_engine import decide
from engine.loaders import load_all
from tests.fixtures_reject import make_change, make_contract


@pytest.fixture(scope="module")
def bundle():
    return load_all()


@pytest.fixture(scope="module")
def client():
    # The context manager triggers the lifespan handler (loads the store once).
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def sample_ids(bundle):
    """A spread of real change_request_ids (one per distinct expected outcome + extras)."""
    seen: dict[str, str] = {}
    for change in bundle["changes"]:
        key = (
            change.expected_validation_outcome.value
            if change.expected_validation_outcome
            else "?"
        )
        seen.setdefault(key, change.change_request_id)
    ids = list(seen.values())
    # Pad with the first handful of ids for a broader parity sample.
    for change in bundle["changes"][:10]:
        if change.change_request_id not in ids:
            ids.append(change.change_request_id)
    return ids


# --- /health ---------------------------------------------------------------


def test_health_reports_counts(client, bundle):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["contracts"] == len(bundle["contracts"])
    assert body["changes"] == len(bundle["changes"])
    assert body["rules"] == len(bundle["rules"])


# --- parity (most important) ----------------------------------------------


def test_by_id_parity_with_engine(client, bundle, sample_ids):
    """API outcome + winning_rule must equal a direct decide() call."""
    contracts = bundle["contracts"]
    changes_by_id = {c.change_request_id: c for c in bundle["changes"]}

    for cid in sample_ids:
        change = changes_by_id[cid]
        contract = contracts[change.linked_provider_contract_id]
        expected = decide(change, contract)

        resp = client.post("/v1/decisions/by-id", json={"change_request_id": cid})
        assert resp.status_code == 200, cid
        decision = resp.json()["decision"]
        assert decision["outcome"] == expected.outcome.value
        assert decision["winning_rule"] == expected.winning_rule
        assert decision["contract_action"] == expected.contract_action


def test_by_id_full_decision_parity(client, bundle, sample_ids):
    """The whole serialized Decision matches the engine's JSON dump, field-for-field."""
    contracts = bundle["contracts"]
    changes_by_id = {c.change_request_id: c for c in bundle["changes"]}

    for cid in sample_ids:
        change = changes_by_id[cid]
        contract = contracts[change.linked_provider_contract_id]
        expected = decide(change, contract).model_dump(mode="json")

        resp = client.post("/v1/decisions/by-id", json={"change_request_id": cid})
        assert resp.json()["decision"] == expected, cid


def test_inline_parity_with_engine(client):
    change = make_change()
    contract = make_contract()
    expected = decide(change, contract).model_dump(mode="json")

    resp = client.post(
        "/v1/decisions/inline",
        json={
            "change": change.model_dump(mode="json"),
            "contract": contract.model_dump(mode="json"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == expected


# --- determinism -----------------------------------------------------------


def test_determinism_byte_identical(client, sample_ids):
    cid = sample_ids[0]
    payload = {"change_request_id": cid}
    first = client.post("/v1/decisions/by-id", json=payload).json()["decision"]
    second = client.post("/v1/decisions/by-id", json=payload).json()["decision"]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_correlation_id_outside_decision(client, sample_ids):
    cid = sample_ids[0]
    headers = {"X-Correlation-Id": "abc-123"}
    no_corr = client.post("/v1/decisions/by-id", json={"change_request_id": cid})
    with_corr = client.post(
        "/v1/decisions/by-id", json={"change_request_id": cid}, headers=headers
    )
    assert with_corr.json()["correlation_id"] == "abc-123"
    assert no_corr.json()["correlation_id"] is None
    # The correlation id must not perturb the Decision portion.
    assert no_corr.json()["decision"] == with_corr.json()["decision"]


# --- batch -----------------------------------------------------------------


def test_batch_preserves_order_and_reports_unknown(client, sample_ids):
    known = sample_ids[:3]
    ids = [known[0], "CR-NOPE-9999", known[1], known[2]]
    resp = client.post("/v1/decisions/batch", json={"change_request_ids": ids})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert [r["change_request_id"] for r in results] == ids
    assert results[0]["found"] is True and results[0]["decision"] is not None
    assert results[1]["found"] is False and results[1]["decision"] is None
    assert results[1]["error"]
    assert results[2]["found"] is True


# --- transport errors ------------------------------------------------------


def test_by_id_unknown_is_404(client):
    resp = client.post(
        "/v1/decisions/by-id", json={"change_request_id": "CR-DOES-NOT-EXIST"}
    )
    assert resp.status_code == 404


def test_inline_malformed_is_422(client):
    resp = client.post("/v1/decisions/inline", json={"change": {}, "contract": {}})
    assert resp.status_code == 422


def test_unknown_contract_is_404(client):
    resp = client.get("/v1/contracts/PC-DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_unknown_change_is_404(client):
    resp = client.get("/v1/changes/CR-DOES-NOT-EXIST")
    assert resp.status_code == 404


# --- reference read-back ---------------------------------------------------


def test_contract_read_back(client, bundle):
    cid = next(iter(bundle["contracts"]))
    resp = client.get(f"/v1/contracts/{cid}")
    assert resp.status_code == 200
    assert resp.json()["provider_contract_id"] == cid


def test_change_read_back(client, bundle):
    cid = bundle["changes"][0].change_request_id
    resp = client.get(f"/v1/changes/{cid}")
    assert resp.status_code == 200
    assert resp.json()["change_request_id"] == cid


def test_rules_endpoint(client, bundle):
    resp = client.get("/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert "rules" in body
    assert len(body["rules"]) == len(bundle["rules"])


# --- label leakage ---------------------------------------------------------


def test_no_label_fields_in_change_read_back(client, bundle):
    for change in bundle["changes"][:10]:
        resp = client.get(f"/v1/changes/{change.change_request_id}")
        keys = resp.json().keys()
        assert "expected_validation_outcome" not in keys
        assert "expected_contract_action" not in keys


def test_no_label_leakage_anywhere(client, sample_ids, bundle):
    """No serialized response should contain an ``expected_*`` label field."""
    blobs: list[str] = []
    blobs.append(client.get("/health").text)
    blobs.append(client.get("/v1/rules").text)
    for cid in sample_ids:
        blobs.append(
            client.post("/v1/decisions/by-id", json={"change_request_id": cid}).text
        )
        blobs.append(client.get(f"/v1/changes/{cid}").text)
    blobs.append(
        client.post(
            "/v1/decisions/batch", json={"change_request_ids": sample_ids}
        ).text
    )
    for blob in blobs:
        assert "expected_validation_outcome" not in blob
        assert "expected_contract_action" not in blob
