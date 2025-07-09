# Infrastructure documentation

I will (probably temporarly) use this document for documenting certain parts of my infrastructure.

## Kafka

The Kafka-instance has three topics:

- `gossip`: `List[PlatformEvent]`
The [gossip-syncer](https://github.com/ln-history/gossip-syncer) publishes all collected gossip messages as `PlatformEvent`s to the Kafka instance

- `problem.node`: `List[PlatformEvent]` and `problem.channel`: `List[PlatformEvent]`
The [gossip-post-processor] publishes `PlatformEvent`s to the `problem.*` topics if an error appears when inserting the gossip message into the `ln-history-database`. 


A `PlatformEvent` is described in the [lnhistoryclient](https://pypi.org/project/lnhistoryclient/) exactly here:
[model/platform_internal/PlatformEvent.py](https://github.com/ln-history/ln-history-python-client/blob/main/lnhistoryclient/model/platform_internal/PlatformEvent.py) as:
```py
from dataclasses import dataclass
from typing import Dict

from lnhistoryclient.model.platform_internal.PlatformEventMetadata import PlatformEventMetadata


@dataclass(frozen=True)
class PlatformEvent:
    metadata: PlatformEventMetadata
    raw_gossip_bytes: bytes

    def __str__(self) -> str:
        return f"PlatformEvent(metadata={self.metadata}, raw_gossip_bytes={self.raw_gossip_bytes.hex()})"

    def to_dict(self) -> Dict[str, object]:
        return {"metadata": self.metadata.to_dict(), "raw_gossip_bytes": self.raw_gossip_bytes.hex()}
```


## Valkey-Cache 

To improve performance—especially for tasks like duplication detection—`ln-history` uses [Valkey](https://valkey.io/), a high-performance Redis-compatible key-value store.

## Cache Keys

### 1. Duplicate Gossip Detection

To avoid reprocessing previously seen gossip messages, the cache stores an entry keyed by the SHA256 hash of the raw gossip bytes (especially useful when handling older messages):

- **Key format:** `gossip:{gossip_id}`
- **Type:** Simple key with a dummy value (e.g., `"1"`)
- **Purpose:** Fast O(1) existence checks. If the key exists, the message has already been processed.

### 2. Message Observation Tracking

For analysis purposes, the cache tracks which of the platform's own nodes received a specific gossip message and when they observed it (only live version). This information is namespaced by message type:

- **Key formats:**
  - Channel Announcements → `gossip:256:{gossip_id}`
  - Node Announcements → `gossip:257:{gossip_id}`
  - Channel Updates → `gossip:258:{gossip_id}`

- **Value structure:** A mapping of node IDs to sets of Unix timestamps:
  ```js
  {
    "node_id_1": [timestamp_1, timestamp_3],
    "node_id_2": [timestamp_2]
  }
Purpose: Enables temporal analysis of gossip message propagation and observation across nodes.
