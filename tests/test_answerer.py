import pytest

from app.exceptions import GenerationError
from app.generation import generator as generator_module
from app.generation.answerer import answer_question, process_citations
from app.generation.generator import Generator
from app.generation.prompts import NOT_FOUND_MESSAGE, build_user_message
from app.retrieval.store import Hit


def hit(page, score=0.8, name="a.pdf", text=None):
    return Hit(chunk_id=f"c{page}", doc_id="d1", file_name=name, page_number=page,
               chunk_index=0, text=text or f"text on page {page}", score=score)


class FakeGenerator:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def generate(self, system_prompt, user_message):
        self.calls.append((system_prompt, user_message))
        return self.reply


def run(reply, hits):
    gen = FakeGenerator(reply)
    answer = answer_question("What?", retrieve_fn=lambda q, doc_ids=None: hits, generator=gen)
    return answer, gen


def test_no_hits_means_not_found_and_the_model_is_never_called():
    answer, gen = run("anything", [])
    assert answer.text == NOT_FOUND_MESSAGE and not answer.found and gen.calls == []


def test_citations_map_to_real_file_and_page():
    answer, _ = run("Leave is 20 days [1]. Carry-over is 5 days [2].", [hit(14), hit(15)])
    assert answer.found and answer.cited
    assert [(s.number, s.file_name, s.page_number) for s in answer.sources] == [
        (1, "a.pdf", 14), (2, "a.pdf", 15)]


def test_only_cited_excerpts_become_sources():
    answer, _ = run("Only this matters [2].", [hit(1), hit(2), hit(3)])
    assert [s.page_number for s in answer.sources] == [2]


def test_made_up_citation_numbers_are_removed():
    answer, _ = run("Real [1]. Fake [9] claim.", [hit(4), hit(5)])
    assert "[9]" not in answer.text
    assert [s.number for s in answer.sources] == [1]
    assert "Fake claim." in answer.text


def test_grouped_citations_are_understood():
    answer, _ = run("Both agree [1, 2].", [hit(1), hit(2)])
    assert answer.text == "Both agree [1][2]."
    assert [s.number for s in answer.sources] == [1, 2]


def test_model_saying_not_found_gives_not_found_with_no_sources():
    answer, _ = run("I couldn\u2019t find this in the uploaded documents.", [hit(1)])
    assert not answer.found and answer.sources == []


def test_answer_without_any_citation_is_flagged():
    answer, _ = run("Leave is 20 days.", [hit(1)])
    assert not answer.found and not answer.cited


def test_uncited_answer_is_retried_then_rejected():
    gen = FakeGenerator("Leave is 20 days.")
    answer = answer_question("What?", retrieve_fn=lambda q, doc_ids=None: [hit(1)], generator=gen)
    assert not answer.found and not answer.cited
    assert len(gen.calls) == 2


def test_user_message_numbers_the_excerpts_with_file_and_page():
    message = build_user_message("Why?", [hit(14, name="hr.pdf"), hit(15, name="hr.pdf")])
    assert "[1] (hr.pdf, page 14)" in message and "[2] (hr.pdf, page 15)" in message
    assert message.endswith("Question: Why?")


def test_process_citations_cleans_spacing():
    text, cited = process_citations("Good [1]. Bad [7] , done.", max_number=2)
    assert text == "Good [1]. Bad, done." and cited == [1]


# ---- Generator (retries and empty answers) ----

class _Response:
    def __init__(self, text):
        self.content = text


class _Completions:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def create(self, messages, model, temperature, max_tokens):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return type(
            "_ChatCompletion",
            (),
            {"choices": [type("_Choice", (), {"message": _Response(reply)})()]},
        )()


class _Client:
    def __init__(self, replies):
        self.chat = type("_Chat", (), {"completions": _Completions(replies)})()


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(generator_module.time, "sleep", lambda s: None)


def test_generator_retries_then_succeeds():
    client = _Client([RuntimeError("429"), "  Hello [1]  "])
    assert Generator(client=client, model="m", max_output_tokens=100).generate("s", "u") == "Hello [1]"
    assert client.chat.completions.calls == 2


def test_generator_gives_up_with_friendly_error_and_treats_empty_as_failure():
    client = _Client([None, "", "   "])
    with pytest.raises(GenerationError):
        Generator(client=client, model="m", max_output_tokens=100).generate("s", "u")
