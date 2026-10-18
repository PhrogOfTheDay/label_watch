from pathlib import Path

from pydantic import BaseModel, TypeAdapter

cwd = Path.cwd().parent


def createTypeAdapter(baseClass: BaseModel) -> TypeAdapter:
    return TypeAdapter(list[baseClass])


def save_set_id(set_id: str):
    data_dir = cwd / "data"
    with open(data_dir / "trackingIds.txt", "wb") as f:
        f.write(f"{set_id}, ")
