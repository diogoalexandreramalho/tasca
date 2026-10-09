from core.config import Settings


def _build(cors: object) -> Settings:
    return Settings(cors_origins=cors)  # type: ignore[arg-type]


def test_cors_origins_comma_separated_string() -> None:
    assert _build("http://a,http://b").cors_origins == ["http://a", "http://b"]


def test_cors_origins_trims_whitespace_and_empty_segments() -> None:
    assert _build("http://a, ,http://b").cors_origins == ["http://a", "http://b"]


def test_cors_origins_passthrough_for_list() -> None:
    assert _build(["http://a", "http://b"]).cors_origins == ["http://a", "http://b"]
