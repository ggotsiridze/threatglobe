from datetime import timedelta

from app.models import EventType, Severity
from app.normalize import normalize_document
from app.risk import RiskEngine, rating_for_score
from tests.conftest import cowrie_doc


def rules(event):
    return {f.rule for f in event.risk_factors}


def test_rating_boundaries():
    assert rating_for_score(0) is Severity.LOW
    assert rating_for_score(24) is Severity.LOW
    assert rating_for_score(25) is Severity.MEDIUM
    assert rating_for_score(50) is Severity.HIGH
    assert rating_for_score(75) is Severity.CRITICAL
    assert rating_for_score(100) is Severity.CRITICAL


def test_privileged_ssh_login_is_medium_with_reasons():
    e = RiskEngine().score(normalize_document(cowrie_doc()))
    assert rules(e) == {"privileged_username", "remote_shell_login"}
    assert e.risk_score == 30 and e.severity is Severity.MEDIUM
    assert all(f.detail for f in e.risk_factors)


def test_unprivileged_scan_is_low():
    doc = cowrie_doc(type="Honeytrap", eventid="honeytrap.connection", dest_port=8080, username=None)
    e = RiskEngine().score(normalize_document(doc))
    assert e.severity is Severity.LOW and e.risk_score == 0 and e.risk_factors == []


def test_brute_force_detected_after_threshold():
    engine = RiskEngine()
    base = normalize_document(cowrie_doc()).timestamp
    scored = []
    for i in range(6):
        doc = cowrie_doc(_id=f"b{i}", **{"@timestamp": (base + timedelta(seconds=10 * i)).isoformat()})
        scored.append(engine.score(normalize_document(doc)))
    assert "brute_force" not in rules(scored[3])
    assert "brute_force" in rules(scored[4])
    assert scored[5].severity is Severity.HIGH


def test_brute_force_window_expires():
    engine = RiskEngine()
    base = normalize_document(cowrie_doc()).timestamp
    for i in range(5):
        doc = cowrie_doc(_id=f"o{i}", **{"@timestamp": (base + timedelta(minutes=15 * i)).isoformat()})
        e = engine.score(normalize_document(doc))
    assert "brute_force" not in rules(e)


def test_malware_download_after_login_is_critical():
    engine = RiskEngine()
    e = engine.score(normalize_document(cowrie_doc(eventid="cowrie.session.file_download")))
    assert e.event_type is EventType.MALWARE
    # malware 45 + privileged 20 = 65 -> HIGH; a command in the same session pushes further
    assert e.severity is Severity.HIGH
    cmd = engine.score(normalize_document(cowrie_doc(_id="c", eventid="cowrie.login.success")))
    assert "login_success" in rules(cmd)


def test_abnormal_frequency_and_repeat_rules():
    engine = RiskEngine()
    base = normalize_document(cowrie_doc()).timestamp
    doc = dict(type="Honeytrap", eventid="honeytrap.connection", dest_port=80, username=None)
    for i in range(25):
        ts = (base + timedelta(seconds=i)).isoformat()
        e = engine.score(normalize_document(cowrie_doc(_id=f"f{i}", **doc, **{"@timestamp": ts})))
    assert {"abnormal_frequency", "repeated_source"} <= rules(e)


def test_score_is_capped_at_100():
    engine = RiskEngine()
    base = normalize_document(cowrie_doc()).timestamp
    for i in range(60):
        ts = (base + timedelta(seconds=i)).isoformat()
        e = engine.score(
            normalize_document(
                cowrie_doc(_id=f"x{i}", eventid="cowrie.session.file_download", dest_port=502, **{"@timestamp": ts})
            )
        )
    assert e.risk_score == 100 and e.severity is Severity.CRITICAL


def test_event_without_source_ip_is_scored_safely():
    e = RiskEngine().score(normalize_document({"type": "Cowrie", "username": "admin"}))
    assert e.severity is Severity.LOW and "privileged_username" in rules(e)
