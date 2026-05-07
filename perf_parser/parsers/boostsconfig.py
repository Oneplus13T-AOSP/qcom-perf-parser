import sys
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

from perf_parser.models import Boost


def parse_int_list(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    toks = re.findall(r'0x[0-9a-fA-F]+|\d+', raw)
    return [int(tok, 0) for tok in toks]


def parse_resources(resources_str: Optional[str]) -> List[Tuple[int, int]]:
    nums = parse_int_list(resources_str)

    if len(nums) % 2 != 0:
        print(f"[WARN] Odd resource count, dropping last value: {nums[-1]}")
        nums = nums[:-1]

    return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]


def parse_targets(target_str: Optional[str]) -> List[str]:
    if not target_str:
        return []
    return [t.strip() for t in target_str.split(',') if t.strip()]


def parse_fps(fps_str: Optional[str]) -> List[int]:
    return parse_int_list(fps_str)


def parse_type_and_fps(type_str: Optional[str], fps_str: Optional[str]) -> Tuple[int, List[int]]:
    type_val = -1
    fps_list: List[int] = []

    if type_str:
        values = parse_int_list(type_str)

        if len(values) == 1:
            type_val = values[0]
        elif len(values) > 1:
            fps_list = values

    if fps_str:
        fps_list = parse_int_list(fps_str)

    return type_val, fps_list


def parse_boost_xml(filename: str) -> List[Boost]:
    tree = ET.parse(filename)
    root = tree.getroot()

    perfboosts: List[Boost] = []

    for cfg in root.iter('Config'):
        try:
            boost_id = int(cfg.attrib['Id'], 0)
        except Exception:
            print(f"[WARN] invalid Id: {cfg.attrib.get('Id')}")
            continue

        type_val, fps_val = parse_type_and_fps(
            cfg.attrib.get('Type'),
            cfg.attrib.get('Fps') or cfg.attrib.get('FPS')
        )

        try:
            timeout = int(cfg.attrib.get('Timeout', '0'), 0)
        except Exception:
            timeout = 0

        enable = cfg.attrib.get('Enable', 'true').lower() == 'true'

        resources = parse_resources(cfg.attrib.get('Resources'))
        targets = parse_targets(cfg.attrib.get('Target'))

        boost = Boost(
            id=boost_id,
            type=type_val,
            enable=enable,
            timeout=timeout,
            target=targets,
            resources=resources,
            fps=fps_val,
        )

        perfboosts.append(boost)

    return perfboosts


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python perfboostsconfig.py perfboostsconfig.xml')
        sys.exit()

    perfboost_list = parse_boost_xml(sys.argv[1])

    for pb in perfboost_list:
        print(pb)
