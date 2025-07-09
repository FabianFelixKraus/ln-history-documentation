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