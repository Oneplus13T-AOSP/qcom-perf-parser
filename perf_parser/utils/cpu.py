import subprocess
from typing import Iterable

from perf_parser.models import TargetInfo


def get_cpu_index_for_cluster(target_info: TargetInfo, cluster_id: int) -> int:
    num_clusters = len(target_info.clusters)
    if num_clusters == 0:
        return 0

    # 존재하지 않는 클러스터 ID는 마지막(prime) 클러스터로 매핑
    if cluster_id >= num_clusters:
        cluster_id = num_clusters - 1

    cpu_idx = 0
    for cluster in target_info.clusters:
        if cluster.id == cluster_id:
            break
        else:
            cpu_idx += cluster.numCores

    return cpu_idx


def get_cpus_for_cluster(target_info: TargetInfo, cluster_id: int) -> Iterable[int]:
    num_clusters = len(target_info.clusters)
    if num_clusters == 0:
        return []

    # 존재하지 않는 클러스터 ID는 마지막(prime) 클러스터로 매핑
    if cluster_id >= num_clusters:
        cluster_id = num_clusters - 1

    cpu_idx = 0
    for cluster in target_info.clusters:
        if cluster.id == cluster_id:
            return range(cpu_idx, cpu_idx + cluster.numCores)
        else:
            cpu_idx += cluster.numCores

    return []


def get_available_frequencies_for_cpu(cpu: int) -> Iterable[int]:
    try:
        scaling_available_frequencies = subprocess.check_output(
            [
                'adb',
                'shell',
                'cat',
                f'/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_available_frequencies',
            ],
            text=True,
        )
        return [int(f, 0) for f in scaling_available_frequencies.split(' ') if f.strip()]
    except subprocess.CalledProcessError:
        print(f'[WARN] Unable to read available frequencies for CPU{cpu}, using raw requested value.')
        return []


def get_next_available_frequency_for_cpu(cpu: int, requested_frequency: int) -> int:
    freqs = get_available_frequencies_for_cpu(cpu)
    if not freqs:
        return requested_frequency
    return min(freqs, key=lambda x: abs(x - requested_frequency))


def get_next_available_frequency_for_cluster(
    target_info: TargetInfo, cluster_id: int, requested_frequency: int
) -> int:
    return get_next_available_frequency_for_cpu(
        get_cpu_index_for_cluster(target_info, cluster_id), requested_frequency
    )
