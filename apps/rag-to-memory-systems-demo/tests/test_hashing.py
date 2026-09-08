from memory.hashing import normalize, content_hash


def test_normalize_collapses_whitespace_and_lowercases():
    assert normalize("  Hello   World ") == "hello world"


def test_normalize_strips_trailing_punctuation():
    assert normalize("Hello, world!") == "hello, world"


def test_content_hash_is_deterministic():
    h1 = content_hash("Stripe webhook URL is https://api.acme.com/v2")
    h2 = content_hash("  STRIPE WEBHOOK URL IS https://api.acme.com/v2 ")
    assert h1 == h2


def test_content_hash_distinguishes_different_content():
    assert content_hash("foo") != content_hash("bar")
    assert len(content_hash("foo")) == 64  # sha256 hex
