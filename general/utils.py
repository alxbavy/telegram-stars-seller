import json
from decimal import Decimal, InvalidOperation
from dataclasses import is_dataclass, asdict, fields
from typing import cast, override, overload, TypeVar


DT = TypeVar("DT")
VT = TypeVar("VT")


def cast_force[C](_: type[C], source: object, /) -> C:
    return cast(C, source)  # noqa


class DataclassEncoder(json.JSONEncoder):
    @override
    def default(self, o: object):
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)  # noqa
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)  # pyright: ignore[reportAny]


class DataclassDecoder:
    @staticmethod
    def _get_decimal_or_none(val: object) -> Decimal | None:
        if not isinstance(val, str):
            return None

        if not val or val.isalpha():
            return None

        try:
            return Decimal(val)

        except InvalidOperation:
            return None

    @classmethod
    def _parse_value(
            cls,
            value: dict[str, object] | list[object] | object | None,
            target_type: type[VT] | str | None = None
    ) -> VT | dict[str, object] | list[object] | Decimal | object | None:
        """Рекурсивно обрабатывает значения, восстанавливая Decimal и датаклассы."""

        if target_type is not None:
            if target_type is Decimal or target_type == "Decimal":
                return Decimal(value) if value is not None else None  # noqa  # pyright: ignore[reportArgumentType]

            if is_dataclass(target_type) and isinstance(value, dict):
                return cls.decode_dataclass(cast(dict[str, object], value), target_type)  # noqa

        if isinstance(value, dict):
            return {k: cls._parse_value(v) for k, v in cast(dict[str, object], value).items()}  # noqa

        if isinstance(value, list):
            return [cls._parse_value(item) for item in cast(list[object], value)]  # noqa

        if target_type is None and (converted := cls._get_decimal_or_none(value)) is not None:
            return converted

        return value

    @classmethod
    def decode_dataclass(cls, data: dict[str, object] | object, dataclass_type: type[DT] | None) -> DT:
        """Явно собирает конкретный датакласс из словаря."""
        if dataclass_type is None or not is_dataclass(dataclass_type):
            raise TypeError(f"{dataclass_type} is not a dataclass")

        if not isinstance(data, dict):
            raise ValueError(f"Parsed json is not a dict: parsed_json = {data}")

        data = cast(dict[str, object] , data)  # noqa

        type_hints = {f.name: f.type for f in fields(dataclass_type)}  # noqa
        kwargs: dict[str, object] = {}

        for key, value in data.items():
            target_type = type_hints.get(key)
            kwargs[key] = cls._parse_value(value, target_type)

        return dataclass_type(**kwargs)  # noqa

    @classmethod
    def from_json(
            cls,
            json_str: str | bytes | bytearray,
            target_cls: type[DT] | None = None
    ) -> DT | dict[str, object] | list[object] | Decimal | object | None:
        """
        Главная точка входа.

        - Если `target_cls` передан — вернет датакласс.

        - Если не передан — вернет обычный `list`/`dict`, но восстановит `Decimal` из `любого` подходящего `str` (в том
        числе и те, которые могут предполагаться `str`, например, `"123"` будет конвертировано в `Decimal("123")`).
        """
        parsed_json = cast(object, json.loads(json_str))
        if target_cls is not None:
            return cls.decode_dataclass(
                parsed_json,  # noqa
                target_cls
            )

        return cls._parse_value(parsed_json)


def json_dumps(
        obj: object,
        *,
        ensure_ascii: bool = False, indent: int | None = None,
        skip_keys: bool = False,
        sort_keys: bool = False
) -> str:
    return json.dumps(
        obj, cls=DataclassEncoder,
        ensure_ascii=ensure_ascii, indent=indent,
        skipkeys=skip_keys,
        sort_keys=sort_keys
    )


@overload
def json_loads(string: str | bytes | bytearray, target_dataclass: type[DT]) -> DT: ...

@overload
def json_loads(string: str | bytes | bytearray, target_dataclass: type[DT] | None = None) -> DT | object: ...

def json_loads(string: str | bytes | bytearray, target_dataclass: type[DT] | None = None) -> DT | object:
    return DataclassDecoder.from_json(string, target_dataclass)
