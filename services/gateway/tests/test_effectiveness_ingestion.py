from common.contracts.effectiveness.governance import EffectivenessLedger
from services.gateway.effectiveness_ingestion import EffectivenessIngestionService, ResponseIngestion


def test_live_and_export_ingestion_pseudonymize_before_ledger() -> None:
    ledger = EffectivenessLedger()
    service = EffectivenessIngestionService(ledger, pseudonym_salt="secret")
    for source in ("live_session", "export"):
        assert service.ingest(ResponseIngestion(
            event_id=f"event-{source}", tenant_id="tenant-a", actor_id="raw-student-id",
            document_id="doc-1", document_version=1, item_id="item-1", answer_set_version=1,
            correct=True, source=source,
        ))
    events = ledger.events_for_tenant("tenant-a")
    assert len(events) == 2
    assert all(event.pseudonymous_actor_id and event.pseudonymous_actor_id.startswith("actor-") for event in events)
    assert all("raw-student-id" not in event.model_dump_json() for event in events)


def test_opted_out_response_is_not_persisted() -> None:
    ledger = EffectivenessLedger()
    service = EffectivenessIngestionService(ledger, pseudonym_salt="secret")
    accepted = service.ingest(ResponseIngestion(
        event_id="event-opt-out", tenant_id="tenant-a", actor_id="student-1",
        document_id="doc-1", document_version=1, item_id="item-1", answer_set_version=1,
        correct=True, opted_out=True,
    ))
    assert not accepted
    assert ledger.events_for_tenant("tenant-a") == ()
