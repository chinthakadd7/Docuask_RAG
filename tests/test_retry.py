from app.utils.retry import MAX_WAIT_SECONDS, retry_delay


def test_waits_as_long_as_the_api_asks():
    err = RuntimeError("429 RESOURCE_EXHAUSTED. Please retry in 32.77s.")
    assert retry_delay(err, attempt=1) == 32.77 + 1.0


def test_reads_retry_delay_field():
    err = RuntimeError("{'retryDelay': '30s'}")
    assert retry_delay(err, attempt=2) == 31.0


def test_overloaded_server_waits_longer_each_time():
    err = RuntimeError("503 UNAVAILABLE. high demand")
    assert retry_delay(err, 1) == 5.0 and retry_delay(err, 2) == 10.0


def test_unknown_errors_use_short_waits_and_long_hints_are_capped():
    assert retry_delay(RuntimeError("boom"), 2) == 4.0
    assert retry_delay(RuntimeError("retry in 9999s"), 1) == MAX_WAIT_SECONDS
