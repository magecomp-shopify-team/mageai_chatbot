from unittest.mock import MagicMock

from src.ai.normaliser import (
    normalise_anthropic,
    normalise_cohere,
    normalise_gemini,
    normalise_groq,
    normalise_mistral,
    normalise_ollama,
    normalise_openai,
)


def _mock_anthropic_response(text="hello", input_t=10, output_t=5, model="claude-haiku-4-5-20251001"):
    r = MagicMock()
    r.content = [MagicMock(text=text)]
    r.usage.input_tokens = input_t
    r.usage.output_tokens = output_t
    r.model = model
    r.stop_reason = "stop"
    r.model_dump.return_value = {}
    return r


def _mock_openai_response(text="hi", prompt_t=8, completion_t=4, model="gpt-4o-mini"):
    choice = MagicMock()
    choice.message.content = text
    choice.finish_reason = "stop"
    r = MagicMock()
    r.choices = [choice]
    r.usage.prompt_tokens = prompt_t
    r.usage.completion_tokens = completion_t
    r.model = model
    r.model_dump.return_value = {}
    return r


def test_normalise_anthropic():
    r = normalise_anthropic(_mock_anthropic_response())
    assert r.text == "hello"
    assert r.input_tokens == 10
    assert r.output_tokens == 5
    assert r.provider == "anthropic"
    assert r.finish_reason == "stop"


def test_normalise_openai():
    r = normalise_openai(_mock_openai_response())
    assert r.text == "hi"
    assert r.input_tokens == 8
    assert r.output_tokens == 4
    assert r.provider == "openai"


def test_normalise_groq():
    r = normalise_groq(_mock_openai_response(model="llama-3.3-70b-versatile"))
    assert r.provider == "groq"
    assert r.text == "hi"


def test_normalise_mistral():
    choice = MagicMock()
    choice.message.content = "mistral reply"
    choice.finish_reason = "stop"
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 12
    resp.usage.completion_tokens = 6
    resp.model = "mistral-small-latest"
    r = normalise_mistral(resp)
    assert r.text == "mistral reply"
    assert r.provider == "mistral"


def test_normalise_ollama():
    raw = {
        "message": {"content": "ollama reply"},
        "prompt_eval_count": 15,
        "eval_count": 7,
        "model": "llama3.3",
        "done": True,
    }
    r = normalise_ollama(raw)
    assert r.text == "ollama reply"
    assert r.provider == "ollama"
    assert r.finish_reason == "stop"
    assert r.input_tokens == 15
    assert r.output_tokens == 7
