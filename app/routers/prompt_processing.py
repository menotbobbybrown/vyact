"""Settings for ordinary and project chat prompt composition."""
from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator
from services.prompt_processing import BUILTIN_IDS, EDITABLE_IDS, defaults, load_settings, save_settings

router = APIRouter()


class PromptItem(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    enabled: bool
    title: str | None = Field(default=None, max_length=120)
    content: str | None = Field(default=None, max_length=50000)
    source: str | None = None
    createdOrder: int | None = Field(default=None, ge=0)


class PromptSettings(BaseModel):
    general: list[PromptItem] = Field(max_length=200)
    project: list[PromptItem] = Field(max_length=200)

    @model_validator(mode="after")
    def validate_items(self):
        for scope in ("general", "project"):
            items = getattr(self, scope)
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate prompt IDs")
            expected = {item["id"] for item in defaults(scope)}
            if set(ids) & set(BUILTIN_IDS) != expected:
                raise ValueError("Missing or invalid built-in prompts")
            for item in items:
                if item.id in expected:
                    if item.source is not None or item.id not in EDITABLE_IDS and item.content is not None:
                        raise ValueError("Built-in prompt content is read-only")
                elif item.source != "user" or not item.id.startswith("custom:"):
                    raise ValueError("Invalid custom prompt")
        return self


@router.get("/prompt-processing")
async def get_prompt_processing():
    settings, exists = await load_settings()
    return {"settings": settings, "configured": exists}


@router.put("/prompt-processing")
async def put_prompt_processing(body: PromptSettings):
    settings = body.model_dump(exclude_none=True)
    await save_settings(settings)
    return {"settings": settings, "configured": True}
