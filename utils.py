from typing import cast


def cast_force[C](_: type[C], source: object) -> C:
    return cast(C, source)  # noqa
