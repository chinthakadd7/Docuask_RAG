import pytest

from app.exceptions import EmbeddingError
from app.retrieval import embedder as embedder_module
from app.retrieval.embedder import Embedder


class _Emb:
    def __init__(self, values):
        self.values = values


class FakeModels:
    def __init__(self, fail_times=0):
        self.calls = []
        self.fail_times = fail_times

    def embed_content(self, model, contents, config):
        self.calls.append((model, list(contents), config))
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("429 rate limited")

        class Response:
            embeddings = [_Emb([float(len(c)), 0.0]) for c in contents]

        return Response()


class FakeClient:
    def __init__(self, **kwargs):
        self.models = FakeModels(**kwargs)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(embedder_module.time, "sleep", lambda s: None)


def test_batches_and_keeps_order():
    client = FakeClient()
    emb = Embedder(client=client, model="m", batch_size=2, dimensions=2)
    vectors = emb.embed_texts(["a", "bb", "ccc"])
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0]
    assert len(client.models.calls) == 2
    assert client.models.calls[0][2]["task_type"] == "RETRIEVAL_DOCUMENT"


def test_query_uses_query_task_type():
    client = FakeClient()
    Embedder(client=client, model="m", dimensions=2).embed_query("hello")
    assert client.models.calls[0][2]["task_type"] == "RETRIEVAL_QUERY"


def test_retries_then_succeeds():
    client = FakeClient(fail_times=2)
    vectors = Embedder(client=client, model="m", dimensions=2).embed_texts(["x"])
    assert len(vectors) == 1 and len(client.models.calls) == 3


def test_gives_up_with_friendly_error():
    client = FakeClient(fail_times=10)
    with pytest.raises(EmbeddingError):
        Embedder(client=client, model="m", dimensions=2).embed_texts(["x"])