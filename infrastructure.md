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

### 1a. Duplicate Gossip Detection

To avoid reprocessing previously seen gossip messages, the cache stores an entry keyed by the SHA256 hash of the raw gossip bytes (especially useful when handling older messages):

- **Key format:** `gossip:{gossip_id}`
- **Type:** Simple key with a dummy value (e.g., `"1"`)
- **Purpose:** Fast O(1) existence checks. If the key exists, the message has already been processed.

### 1b. Temporary Node ID Caching

During initial project setup, the platform temporarily caches known `node_id`s to reduce database load when checking for node existence.

- **Key format:** `node:{node_id}`
- **Type:** Simple key with a dummy value (e.g., `"1"`)
- **Purpose:** Prevents repeated PostgreSQL lookups for node presence during bulk imports or replayed gossip events.

⚠️ This cache is **not permanent** and can be safely cleared once the setup phase is complete.


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
- **Purpose**: Enables temporal analysis of gossip message propagation and observation across nodes.



## 📚 Event Model Overview in `ln-history`

In the `ln-history` data platform, we distinguish between two types of events:

### 🔌 `PluginEvent`: Raw Data from Core Lightning Plugin

A `PluginEvent` is the raw event data emitted by the [`gossip-publisher-zmq`](https://github.com/ln-history/gossip-publisher-zmq) plugin for Core Lightning. These events are Python `dict` objects (or `TypedDict`s) and are deliberately kept **loosely structured and flexible**, allowing the plugin to forward various gossip message types **without performing validation** or enforcing schema constraints.

**Benefits of this approach:**
- Lower dependency footprint: users can easily consume and forward events without strict schema enforcement.
- Faster iteration: the plugin remains lightweight and generic, acting only as a forwarder.

The following classes define the structure of plugin events:

```python
# Metadata for each event
class PluginEventMetadata(TypedDict):
    type: int
    timestamp: int
    sender_node_id: str
    length: str  # Length in bytes, excluding 2-byte message type prefix

# Base structure for all plugin events
class BasePluginEvent(TypedDict):
    metadata: PluginEventMetadata
    raw_gossip_hex: str

# Extended plugin event types
class PluginChannelAnnouncementEvent(BasePluginEvent):
    parsed: ChannelAnnouncementDict

class PluginNodeAnnouncementEvent(BasePluginEvent):
    parsed: NodeAnnouncementDict

class PluginChannelUpdateEvent(BasePluginEvent):
    parsed: ChannelUpdateDict

ParsedGossipDict = Union[
    ChannelAnnouncementDict,
    NodeAnnouncementDict,
    ChannelUpdateDict,
]

# Generic plugin event
class PluginEvent(BasePluginEvent):
    parsed: ParsedGossipDict
```

These definitions can be found in the [lnhistoryclient.model.types](https://github.com/ln-history/ln-history-python-client/blob/main/lnhistoryclient/model/types.py) module, which provides type annotations and structure for downstream consumers and IDEs.


### ⚙️ PlatformEvent: Validated Internal Event Structure
A `PlatformEvent` is a stricter, validated structure that is used internally within the `ln-history` platform. These events follow a uniform schema enforced via Python `dataclasses`, and are validated at the beginning of the processing pipeline.

**Benefits of this approach**:
- **Strict schema enforcement** avoids runtime errors deeper in the pipeline.
- **Improved traceability**: malformed or unexpected events can be dropped and logged for analysis.
- Enables consistent downstream processing in Kafka consumers and analytics systems.

```python
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class PlatformEventMetadata:
    type: int
    id: str  # SHA256 hash as hex string of raw_gossip_hex of the PlatformEvent
    timestamp: int

    def __str__(self) -> str:
        return f"PlatformEventMetadata(type={self.type}, id={self.id}, timestamp={self.timestamp})"

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type,
            "id": self.id,
            "timestamp": self.timestamp,
        }

from dataclasses import dataclass
from typing import Dict

from lnhistoryclient.model.platform_internal.PlatformEventMetadata import PlatformEventMetadata

@dataclass(frozen=True)
class PlatformEvent:
    metadata: PlatformEventMetadata
    raw_gossip_hex: str

    def __str__(self) -> str:
        return f"PlatformEvent(metadata={self.metadata}, raw_gossip_hex={self.raw_gossip_hex})"

    def to_dict(self) -> Dict[str, object]:
        return {"metadata": self.metadata.to_dict(), "raw_gossip_hex": self.raw_gossip_hex}
```
Before a `PluginEvent` is processed further, it is converted into a `PlatformEvent` using transformation and validation logic. If the event doesn't meet the required structure (e.g., missing fields, invalid encoding), it will be dropped early, ensuring robustness of the pipeline.

### 🔗 Where to Find These Models
All relevant types and data structures for `PluginEvent` and `PlatformEvent` can be found in the ln-history Python client, specifically in the [lnhistoryclient.model.types](https://github.com/ln-history/ln-history-python-client/blob/main/lnhistoryclient/model/) module.

This separation of plugin-facing vs platform-facing types provides both flexibility for **plugin developers and stability for data consumers**.