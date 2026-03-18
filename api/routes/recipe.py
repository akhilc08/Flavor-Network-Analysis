from __future__ import annotations
import os
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

router = APIRouter()

RECIPE_SYSTEM = (
    "You are a culinary scientist and chef. Write for curious food lovers "
    "who appreciate both great cooking and the science behind it."
)


class RecipeRequest(BaseModel):
    ingredients: list[str]
    shared_molecules: list[str]
    flavor_labels: dict[str, str]
    api_key: str | None = None

    @field_validator("ingredients")
    @classmethod
    def at_least_two(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 ingredients required.")
        return v


def _build_prompt(req: RecipeRequest) -> str:
    ing_list = ", ".join(i.title() for i in req.ingredients)
    mol_str = ", ".join(req.shared_molecules[:5]) or "(not available)"
    label_str = "; ".join(f"{k}: {v}" for k, v in req.flavor_labels.items())
    return f"""Create a recipe using these molecularly paired ingredients: {ing_list}.

Shared flavor compounds: {mol_str}.
Pairing classifications: {label_str}.

Your recipe MUST:
1. Give the dish a creative, evocative name
2. Explain in 2-3 sentences WHY these ingredients work together — reference the specific shared compounds by name
3. List all ingredients with quantities
4. Provide clear step-by-step cooking instructions (6-10 steps)
5. End with a ## Flavor Science section explaining the molecular pairing rationale in plain English

Be specific about the flavor compounds and write with confidence."""


def _stream_recipe(prompt: str, api_key: str):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


@router.post("/recipe")
def recipe(req: RecipeRequest):
    key = req.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No API key provided.")
    prompt = _build_prompt(req)
    return StreamingResponse(_stream_recipe(prompt, key), media_type="text/event-stream")
