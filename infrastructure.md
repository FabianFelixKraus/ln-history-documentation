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



## Updating channel_updates

In case a channel_update has a missing to_timestamp this sql-query is able to add it, in case a more recent update has been made.

```sql
WITH ordered_updates AS (
  SELECT
    scid,
    direction,
    validity,
    lower(validity) AS start_time,
    LEAD(lower(validity)) OVER (
      PARTITION BY scid, direction
      ORDER BY lower(validity)
    ) AS next_start
  FROM channel_updates
)
UPDATE channel_updates cu
SET validity = tstzrange(lower(cu.validity), ou.next_start)
FROM ordered_updates ou
WHERE
  cu.scid = ou.scid AND
  cu.direction = ou.direction AND
  cu.validity = ou.validity AND
  ou.next_start IS NOT NULL;
```


## Queries on the database:

1. Get all `raw_gossip` for a given timestamp (snapshot)

After many testing the fastes query to get a snapshot at a given timestamp is this query:
```sql
WITH target_timestamp AS (
    SELECT TIMESTAMPTZ '2023-07-01 12:00:00' AS ts
),
rg_filtered AS (
    SELECT *
    FROM raw_gossip, target_timestamp tt
    WHERE (raw_gossip.timestamp BETWEEN (tt.ts - INTERVAL '14 days') AND tt.ts)
),
valid_nodes AS (
    SELECT node_id
    FROM nodes, target_timestamp tt
    WHERE tt.ts <@ validity
),
valid_channels AS (
    SELECT scid
    FROM channels, target_timestamp tt
    WHERE tt.ts <@ validity
),
valid_updates AS (
    SELECT DISTINCT scid
    FROM channel_updates, target_timestamp tt
    WHERE tt.ts <@ validity
),
matching_gossip_ids AS (
    SELECT DISTINCT rg.gossip_id
    FROM rg_filtered rg
    LEFT JOIN nodes_raw_gossip nrg ON rg.gossip_id = nrg.gossip_id
    LEFT JOIN valid_nodes vn ON nrg.node_id = vn.node_id
    LEFT JOIN channels_raw_gossip crg1 ON rg.gossip_id = crg1.gossip_id
    LEFT JOIN valid_channels vc ON crg1.scid = vc.scid
    LEFT JOIN channels_raw_gossip crg2 ON rg.gossip_id = crg2.gossip_id
    LEFT JOIN valid_updates vu ON crg2.scid = vu.scid
    WHERE vn.node_id IS NOT NULL
       OR vc.scid IS NOT NULL
       OR vu.scid IS NOT NULL
)

SELECT rg.raw_gossip
FROM rg_filtered rg
JOIN matching_gossip_ids mgi ON rg.gossip_id = mgi.gossip_id
```

As one can easily see, there are many joins involved into this query. In general join operations can be considered as expensive operations.
Before throwing away the whole data model and reduce it to one table without joins, making the third and fourth requirement difficult to fulfill we take a look at the cost of the specific joins by analyzing the result of postgresql [EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html) feature.

```sql
SELECT crg.gossip_id AS gossip_id
FROM channel_updates cu
JOIN channels_raw_gossip crg ON cu.scid = crg.scid
WHERE TIMESTAMPTZ '2024-07-01' <@ cu.validity
```
Executing this query yields to this result:
```
Nested Loop  (cost=0.43..3559566.58 rows=224404360 width=33)
  ->  Seq Scan on channels_raw_gossip crg  (cost=0.00..627804.76 rows=31749276 width=46)
  ->  Memoize  (cost=0.43..1.18 rows=6 width=13)
        Cache Key: crg.scid
        Cache Mode: logical
        ->  Index Only Scan using idx_cu_validity_scid on channel_updates cu  (cost=0.42..1.17 rows=6 width=13)
              Index Cond: ((validity @> '2024-07-01 00:00:00+00'::timestamp with time zone) AND (scid = (crg.scid)::text))
```

This shows that this specific oin operation - althoughj the `channel_updates` table has more than 30 million rows - is cheap.

```sql
When analyzing this query:
SELECT rg.gossip_id
FROM raw_gossip rg
WHERE EXISTS (
    SELECT 1
    FROM channels_raw_gossip crg
    JOIN channel_updates cu ON crg.scid = cu.scid
    WHERE crg.gossip_id = rg.gossip_id
      AND TIMESTAMPTZ '2024-07-01' <@ cu.validity
);
```

We see that this join is very expensive making this kind of query unviable.
```
Gather  (cost=1951705.18..6547366.81 rows=31745744 width=33)
  Workers Planned: 4
  ->  Parallel Hash Semi Join  (cost=1950705.18..3371792.41 rows=7936436 width=33)
        Hash Cond: (rg.gossip_id = crg.gossip_id)
        ->  Parallel Seq Scan on raw_gossip rg  (cost=0.00..1180231.34 rows=8988934 width=33)
        ->  Parallel Hash  (cost=1263576.23..1263576.23 rows=54970316 width=33)
              ->  Nested Loop  (cost=0.43..1263576.23 rows=54970316 width=33)
                    ->  Parallel Seq Scan on channels_raw_gossip crg  (cost=0.00..389676.36 rows=7936436 width=46)
                    ->  Memoize  (cost=0.43..1.41 rows=6 width=13)
                          Cache Key: crg.scid
                          Cache Mode: logical
                          ->  Index Only Scan using idx_cu_validity_scid on channel_updates cu  (cost=0.42..1.40 rows=6 width=13)
                                Index Cond: ((validity @> '2024-07-01 00:00:00+00'::timestamp with time zone) AND (scid = (crg.scid)::text))
```

Because of this problem generating a snapshot takes around `30` seconds, which is too long for our requirement. 

To solve this we try to remove the raw_gossip table and split its content between the channels_raw_gossip and nodes_raw_gossip table. 


```sql
COPY (
WITH target_timestamp AS (
    SELECT TIMESTAMPTZ '2024-07-14 12:00:00' AS ts
)

SELECT rg.raw_gossip
FROM raw_gossip rg
CROSS JOIN target_timestamp tt
WHERE (rg.timestamp BETWEEN (tt.ts - INTERVAL '14 days') AND tt.ts)
AND (
    EXISTS (
        SELECT 1 FROM nodes_raw_gossip nrg 
        JOIN nodes n ON nrg.node_id = n.node_id
        AND tt.ts <@ n.validity
    )
    OR
    EXISTS (
        SELECT 1 FROM channels_raw_gossip crg
        JOIN channels c ON crg.scid = c.scid
        AND tt.ts <@ c.validity
    )
    OR
    EXISTS (
        SELECT 1 FROM channels_raw_gossip crg
        JOIN channel_updates cu ON crg.scid = cu.scid
        AND tt.ts <@ cu.validity
    )
) ) TO '/var/lib/postgresql/data/raw_gossip_2024_export.bin' (FORMAT binary)
```

2. Get all `raw_gossip` between two timestamps (difference between two snapshots)
```sql
SELECT *
FROM raw_gossip
WHERE timestamp BETWEEN :from_time AND :to_time;
```

3. Get all `raw_gossip` for a given `scid`
```sql
SELECT rg.*
FROM raw_gossip rg
JOIN channels_raw_gossip crg ON rg.gossip_id = crg.gossip_id
WHERE crg.scid = :scid_value;
```


4. Get all `raw_gossip` for a given `node_id`
```sql
SELECT rg.*
FROM raw_gossip rg
JOIN nodes_raw_gossip nrg ON rg.gossip_id = nrg.gossip_id
WHERE nrg.node_id = :node_id;
```


## "rules"


- We count a `channel_dying` message not as an update to the last_seen value of a node

- We define *snapshot at a given timestamp t* of the Lightning Network as following:
The collection of all channel_update gossip messages that were published between `t` and `t-14 days` and all channel_announcement messages.

Note: This definition aligns with the [rationale in BOLT #7](https://github.com/lightning/bolts/blob/6c5968ab83cee68683b4e11dc889b5982a2231e9/07-routing-gossip.md?plain=1#L547): 


We define the difference between two snapshots of the Lightning Network as following:

We take a look on data-level NOT message-level, meaning that when during t_0 and t_1 a just reannounced the same information, e. g. node_announcement or channel_update with same values (same base and ppm fee), this is NOT part of the difference

Note:
