from pydantic import BaseModel, ConfigDict


class YaBotObject(BaseModel):
    """Base model for all Yandex Messenger Bot API objects."""

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        populate_by_name=True,
        use_enum_values=True,
    )
