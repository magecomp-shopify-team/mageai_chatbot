"""Convert each provider's raw response into NormalisedResponse."""

from src.ai.base import NormalisedResponse


def normalise_anthropic(response) -> NormalisedResponse:
    return NormalisedResponse(
        text=response.content[0].text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
        provider="anthropic",
        finish_reason=response.stop_reason or "stop",
        raw=response.model_dump(),
    )


def normalise_openai(response) -> NormalisedResponse:
    choice = response.choices[0]
    return NormalisedResponse(
        text=choice.message.content or "",
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        model=response.model,
        provider="openai",
        finish_reason=choice.finish_reason or "stop",
        raw=response.model_dump(),
    )


def normalise_gemini(response) -> NormalisedResponse:
    # Use the SDK's .text accessor first — it handles thought tokens and None parts safely.
    # Fall back to iterating parts only if .text raises (e.g. multi-candidate responses).
    try:
        text = response.text or ""
    except Exception:
        text = ""
        candidate = response.candidates[0] if response.candidates else None
        if candidate and candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                text += part.text or ""

    usage = response.usage_metadata
    candidate = response.candidates[0] if response.candidates else None
    raw_finish = str(candidate.finish_reason) if candidate else "STOP"
    # Gemini SDK returns "FinishReason.STOP" — extract just the last part
    finish_reason = raw_finish.split(".")[-1].lower()

    return NormalisedResponse(
        text=text,
        input_tokens=getattr(usage, "prompt_token_count", None) or 0,
        output_tokens=getattr(usage, "candidates_token_count", None) or 0,
        model=getattr(response, "model_version", None) or getattr(response, "model", "gemini"),
        provider="gemini",
        finish_reason=finish_reason,
        raw={"text": text},
    )


def normalise_deepseek(response) -> NormalisedResponse:
    result = normalise_openai(response)
    return result.model_copy(update={"provider": "deepseek"})


def normalise_mistral(response) -> NormalisedResponse:
    choice = response.choices[0]
    return NormalisedResponse(
        text=choice.message.content or "",
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        model=response.model,
        provider="mistral",
        finish_reason=str(choice.finish_reason or "stop"),
        raw={"choices": [{"message": {"content": choice.message.content}}]},
    )


def normalise_cohere(response) -> NormalisedResponse:
    return NormalisedResponse(
        text=response.text or "",
        input_tokens=getattr(response.meta.tokens, "input_tokens", 0) if response.meta else 0,
        output_tokens=getattr(response.meta.tokens, "output_tokens", 0) if response.meta else 0,
        model=getattr(response, "model", "command-r"),
        provider="cohere",
        finish_reason=str(response.finish_reason or "stop"),
        raw={"text": response.text},
    )


def normalise_groq(response) -> NormalisedResponse:
    result = normalise_openai(response)
    return result.model_copy(update={"provider": "groq"})


def normalise_ollama(response: dict) -> NormalisedResponse:
    msg = response.get("message", {})
    return NormalisedResponse(
        text=msg.get("content", ""),
        input_tokens=response.get("prompt_eval_count", 0),
        output_tokens=response.get("eval_count", 0),
        model=response.get("model", "ollama"),
        provider="ollama",
        finish_reason="stop" if response.get("done") else "length",
        raw=response,
    )
