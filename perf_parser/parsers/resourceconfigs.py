import sys
import xml.etree.ElementTree as ET
from typing import Optional

from perf_parser.models import ResourceConfig, ResourceEntry, ResourceKey, TargetInfo


def parse_base_config(filename: str) -> ResourceConfig:
    """
    Parse XML like:

    <PerfResources>
        <Major OpcodeValue="0x0" />
        <Minor OpcodeValue="0x0" Node="..."/>

        <Major OpcodeValue="0x1" />
        <Minor OpcodeValue="0x0" Node="..."/>
        <Minor OpcodeValue="0x1" Node="..."/>
        ...
    """
    tree = ET.parse(filename)
    root = tree.getroot()
    resources = root.find('PerfResources')
    if not resources:
        print(f'PerfResources not found in {filename}')
        sys.exit()

    config: ResourceConfig = {}
    current_major: int = -1

    for elem in resources:
        if elem.tag == 'Major':
            current_major = int(elem.attrib['OpcodeValue'], 0)

        elif elem.tag == 'Minor':
            minor_val = int(elem.attrib['OpcodeValue'], 0)

            key: ResourceKey = (current_major, minor_val)
            config[key] = ResourceEntry(
                supported=elem.attrib.get('Supported', 'yes') != 'no',
                node=elem.attrib.get('Node'),
            )

    return config


def apply_overrides(config: ResourceConfig, filename: str, target: str = None) -> None:
    """
    Parse override XML like:

    <PerfResources>
        <Config MajorValue="0x1" MinorValue="0x1" Supported="no"/>
        <Config MajorValue="0x1" MinorValue="0x3" Supported="no"/>
        <Config MajorValue="0x1" MinorValue="0x4" Supported="no"/>
        <Config MajorValue="0x1" MinorValue="0x2" Node="..."/>
    """
    tree = ET.parse(filename)
    root = tree.getroot()
    resources = root.find('PerfResources')
    if not resources:
        print(f'PerfResources not found in {filename}')
        sys.exit()

    for cfg in resources.findall('Config'):
        # Target 속성 처리: 현재 target이 지정되어 있고, Config의 Target이 있으면서
        # 현재 target이 그 목록에 없으면 이 Config는 건너뜀
        cfg_target = cfg.attrib.get('Target')
        if target and cfg_target:
            target_list = [t.strip() for t in cfg_target.split(',')]
            if target not in target_list:
                continue

        major_val = int(cfg.attrib['MajorValue'], 0)
        minor_val = int(cfg.attrib['MinorValue'], 0)

        key: ResourceKey = (major_val, minor_val)
        entry = config.get(key)
        if not entry:
            print(
                f'{filename} tries to overwrite ({major_val},{minor_val}) which does not exist in the base config'
            )
            sys.exit()

        if 'Node' in cfg.attrib:
            entry.node = cfg.attrib.get('Node')
        if 'Supported' in cfg.attrib:
            entry.supported = cfg.attrib.get('Supported', 'yes') != 'no'


def apply_target_quirks(config: ResourceConfig, target_info: Optional[TargetInfo]) -> None:
    """
    After applying overrides, this function further tailors the resource config
    based on the actual target hardware (e.g., number of clusters).

    For sun (2 clusters), any resource that belongs to a non-existent gold cluster
    (such as bwmon-llcc-gold) will be disabled.
    """
    if target_info is None:
        return

    num_clusters = len(target_info.clusters)
    if num_clusters >= 3:
        # 3개 이상 클러스터가 있는 경우는 gold 경로가 유효할 수 있으므로 그대로 둠
        return

    # 클러스터가 2개 이하일 때는 bwmon-llcc-gold 또는 LLCC_GOLD를 참조하는 리소스를 비활성화
    for key, entry in config.items():
        if not entry.node or not entry.supported:
            continue
        # Major 0x6의 CPU_LLCC_BW 관련 리소스 중, gold 클러스터에만 존재하는 경로 패턴을 비활성화
        # common에 정의된 대표적인 패턴: 'bwmon-llcc-gold'
        if 'bwmon-llcc-gold' in entry.node:
            entry.supported = False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(
            'usage: python resourceconfigs.py commonresourceconfigs.xml targetresourceconfigs.xml'
        )
        sys.exit()

    cfg = parse_base_config(sys.argv[1])
    apply_overrides(cfg, sys.argv[2])

    for (maj, minr), entry in sorted(cfg.items()):
        print(f'(0x{maj:x}, 0x{minr:x}): node={entry.node!r}, supported={entry.supported}')
