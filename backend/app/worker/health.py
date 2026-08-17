from typing import Literal

from pydantic import BaseModel


class WorkerHealth(BaseModel):
    status: Literal["ready", "not_ready"]
    rabbitmq: Literal["up", "down"]
