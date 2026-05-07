import subprocess
from typing import OrderedDict

from powerhint_json.models import DefaultGetter, Node


def create_node(name: str, path: str, values: set[str]) -> Node:
    def safe_default_getter(path: str, _values: set[str]) -> str:
        try:
            result = subprocess.run(
                ['adb', 'shell', 'cat', path],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            print(f'[WARN] Unable to read default value from {path}, using fallback 0')
            return '0'

    return create_node_default(
        name,
        path,
        values,
        safe_default_getter,
    )


def value_key(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def create_node_default(
    name: str, path: str, values: set[str], default_getter: DefaultGetter
) -> Node:
    default_value = default_getter(path, values)

    # avoid duplication of the default value
    if default_value in values:
        values.remove(default_value)
    sorted_values = sorted(values, key=value_key)

    return OrderedDict(
        [
            ('Name', name),
            ('Path', path),
            ('Values', [default_value] + sorted_values),
            ('DefaultIndex', 0),
            ('ResetOnInit', True),
        ]
    )
