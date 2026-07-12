from typing import ParamSpec, TypeVar

from celery import Task as CeleryTask


if not hasattr(CeleryTask, "__class_getitem__"):
    CeleryTask.__class_getitem__ = classmethod(lambda cls, params: cls)  # pyright: ignore[reportAttributeAccessIssue, reportUnknownArgumentType, reportUnknownLambdaType]

P = ParamSpec("P")
R = TypeVar("R")
Task = CeleryTask[P,R]
