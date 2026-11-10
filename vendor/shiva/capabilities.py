"""The Shiva capability taxonomy — the single vocabulary the gate, delta, drift and
blast-radius all speak. Extracted from Kartikeya (see second-brain/products/_shiva/
capability-taxonomy.md)."""
from __future__ import annotations
from enum import Enum


class Capability(str, Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    PROCESS_SPAWN = "process-spawn"
    CODE_EXECUTION = "code-execution"
    CREDENTIAL_ACCESS = "credential-access"
    DATA_EGRESS = "data-egress"
    EXTERNAL_API = "external-api"
    MEMORY_RETRIEVAL = "memory-retrieval"
    SUB_AGENT_SPAWN = "sub-agent-spawn"


# Default blast-radius weight per class — a tunable prior, NOT law (High=3, Medium=2, Low=1).
# These get tuned against outcome data; they are not fixed by decree.
BLAST_RADIUS_WEIGHT: "dict[Capability, int]" = {
    Capability.NETWORK: 2,
    Capability.FILESYSTEM: 2,
    Capability.PROCESS_SPAWN: 3,
    Capability.CODE_EXECUTION: 3,
    Capability.CREDENTIAL_ACCESS: 3,
    Capability.DATA_EGRESS: 3,
    Capability.EXTERNAL_API: 2,
    Capability.MEMORY_RETRIEVAL: 1,
    Capability.SUB_AGENT_SPAWN: 3,
}
