from app.core.security import get_password_hash, verify_password


def test_password_hash_and_verify():
    raw = "SuperSecret123!"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)


