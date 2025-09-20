from pydantic import BaseModel, Field

class ApiGroupDTO(BaseModel):
    id: int
    name: str


class ApiRegionDTO(BaseModel):
    id: int
    name: str
    time_zone_id: str = Field(alias='timeZoneId')

class ApiUserDTO(BaseModel):
    id: int
    telegram_id: int | None = Field(alias='telegramId')
    group_id: int = Field(alias='groupId')
    region_id: int = Field(alias='regionId')
    is_admin: bool = Field(alias='isAdmin')

class ApiCreateUserDTO(BaseModel):
    telegram_id: int = Field(alias='telegramId')
    username: str | None = Field(None, alias='username')
    group_id: int = Field(alias='groupId')
    region_id: int = Field(alias='regionId')
    is_admin: bool = Field(False, alias='isAdmin')

    class Config:
        populate_by_name = True