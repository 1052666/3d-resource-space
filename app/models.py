from pydantic import BaseModel


class CenterCreate(BaseModel):
    name: str
    x: float
    y: float
    z: float


class CenterResponse(BaseModel):
    id: int
    name: str
    x: float
    y: float
    z: float


class RelationInput(BaseModel):
    center_id: int
    weight: float


class SphereCreate(BaseModel):
    name: str
    radius: float = 1.0
    relations: list[RelationInput]


class SphereUpdate(BaseModel):
    name: str | None = None
    radius: float | None = None
    relations: list[RelationInput] | None = None


class SphereResponse(BaseModel):
    id: int
    name: str
    radius: float
    calculated_x: float
    calculated_y: float
    calculated_z: float
    relations: list[dict]
