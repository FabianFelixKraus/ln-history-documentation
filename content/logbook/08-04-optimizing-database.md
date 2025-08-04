+++
title = "How to optimize a database"
description = "Bringing down query execution time from minutes to seconds"
date="2025-08-04"
+++

## Introduction
The core part of the [ln-history](github.com/ln-history) project is the data layer where the gossip messages are stored.
In this article I will share my way how I optimized the database to being able to execute my queries very fast. 

## Requirements
There are 4 + 1 requirements which queries need to run quickly on the database.
1. Generate snapshot by timestamp
2. Generate the difference between two snapshots by timestamps
3. Get all raw_gossip by node_id (and timestamp)
4. Get all raw_gossip by scid (and timestamp)

(5. Insert raw_gossip quickly)


## Challenge
First I present the gossip data that needs to get stored.

### Data
The code for the data types can be found in the [ln-history-client](https://pypi.org/project/lnhistoryclient/).

The topology of nodes and channels in the Lightning Network can be constructed with three message types:
`channel_announcement` (`256`), `node_announcement` (`257`), `channel_update` (`258`).

The messages sent over the Lightning network are highly compact, such that the necessary bandwidth to run a Lightning node is minimal. In fact the messages get send as bytes and the BOLTs specify the format / structure of those bytes. In case of the three mentioned gossip messages, they all start with the length of the message encoded as `varint`. See [here](https://github.com/ln-history/ln-history-python-client/blob/main/lnhistoryclient/parser/common.py) for details about that data type. Followed by a `2` bytes which store the message type (i. e. `256` for channel_announcement). After that the next number of bytes (as decoded from the first part) is the actual message content. This content can be parsed by following the [BOLT](https://github.com/lightning/bolts) protocol.


### Constructing the topology
When a node opens a channel it creates a `channel_announcement` message in which the `node_id` of the two participating nodes as well as the `scid` - the unique identifier of the channel - is written in. The `scid` contains information where the channel "lives on the Bitcoin blockchain" since it follows this schema `{block_height}x{transaction_index}x{output_index}`. More information in the BOLTs [here](https://github.com/lightning/bolts/blob/6c5968ab83cee68683b4e11dc889b5982a2231e9/07-routing-gossip.md#definition-of-short_channel_id).
Right after publishing the `channel_announcement` message both nodes send a `channel_upate` message. Since the channel can be used in both directions, each node is "responsible" for its outbound direction. The topology could be interpreted as a [directed Graph](https://en.wikipedia.org/wiki/Directed_graph).
When a node has opened a channel it can (periodically) send `node_announcement` messages that contain information about the node notably the `addresses`, such that one can directly peer with that node.
Every node provides an interface to let others query for recorded gossip messages. See [here](https://github.com/lightning/bolts/blob/6c5968ab83cee68683b4e11dc889b5982a2231e9/07-routing-gossip.md#query-messages) for details. 

This fairly simple process enables every node to construct its view on the topology of the Bitcoin Lightning network without trusting anyone, since the funding transaction of every channel can be found in the Bitcoin blockchain.


## A walk through the versions 
My initial idea was to store the topology in a large [temporal graph](https://en.wikipedia.org/wiki/Temporal_network). I realized that the peformance is far away from my expectaions of the ln-history platform and I started to dig deeper into sql databases, specifically [Postgres](https://www.postgresql.org/). From the first to the third version I went from parsing the gossip messages to just storing them as raw bytes with metadata attached in an columnar schema.

### V0: Temporal graph database
Since every node and edge has a `from_timestamp` and `to_timestamp` (`NULL` if it still exists), it fits the use case of graph databases.
After playing around with [neo4j](https://neo4j.com/) - one of the most popular graph databases - I realized that the performance I was looking for [ln-history](https://github.com/ln-history) is not reachable.

### v1: Parsed relational database 
![Database schema of v1](../08-04-challenge-parsed.png)
I talked with my mentor [René](https://www.rene-pickhardt.de/) about it and he recommended to go for a sql database, where the gossip messages are cleverly stored.
He also made me realize that for this project and (my) performance expectations its highly unlikely that a software exists that I can just use. I will have to think about a solution independently of the technology and very close to the machine and not just use a software. 
I was *blinded* by the third and fourth requirement which will need some sort of table for the channels and nodes, such that I first decided to parse all gossip messages and store them in a normalized relational schema.
This design only has two advantages:
1. The data is stored without redundance, meaning no handling of "synchronizing" the same data
2. The gossip messages will be parsed before insertion and do not need to get parsed again 

On the other hand there are strong counter arguments: 
1. Since the unparsed gossip messages store the data very compact, parsing them takes orders of magnitude of more storage 
2. You will have to `JOIN` tables, which is significantly more costly than `SELECT`ing from a table (I realized this after v2)

The query execution is faster for smaller tables. There is no need to lose this very useful compacted data structure.
[Christian Deckers](https://scholar.google.ch/citations?user=ZaeGlZIAAAAJ&hl=de) [timemachine script](https://github.com/lnresearch/topology) can run through 5 million gossip messages on a Macbook Pro M1 in 5 minutes, making the argument that "saving" the parsing time obsolete.

Especially the second counter argument 

### v2: Raw relational database
![Database schema of v1](../08-04-challenge-raw-relational.png)
The argument of storing the data in a relational manner without redundancy kept in me. I was talking with [René](https://www.rene-pickhardt.de/) about an ideal design and he proposed a columnar design which would be efficient for snapshot generation but retrieving node or channel information would not be as simple. 
Therefore I continued with a mix out of both worlds (relational schema but storing the raw bytes). 
After inserting millions of gossip messages (`2018`-`2023`) I tested it and a query for snapshot generation took well over `2` minutes. 
Using Postges `EXPLAN ANALYZE` I could see the estimated costs of the query. The big problem were the `JOIN` operations. Although I indexed the columns that got joined, joining two tables with millions of rows takes time.
This design also had a flaw: To fulfill the first two requirements (snapshot generation) multiple joins over large tables where necessary.

### v3: Raw "column-reduced" database
![Database schema of v3](../08-04-challenge-raw-columnar.png "Database schema of v3")
The first crutial step that brought down the query time from 2 minutes to 30 seconds was modifying the schema. Although I had the four requirements in mind, where the thrid and fourth are get_raw_gossip_by_scid/node_id. Those queries are ideal if there is a seperate nodes and channels, channel_updates table. I thought a lot about it and realized that I created a 1:1 mapping between the raw_gossip.raw_gossip to nodes_raw_gossip as well as channels_raw_gossip. This first looked nice and more normalized but now created a lot of performance problems. 

Looking back at the previous approaches and listening to Renès advice I simplified the schema, removing almost every foreign key constraint to only have one join operation left for the snapshot generation. (Which is fine since the table that gets joined has less than `100000` rows)

With this schema I was able to get the query execution time down to 10 seconds.   
I was still unsatisfied with that result and digged deeper. I needed to connect the logical values of my data (specifically the `from_timestamp`) with the location where its stored on the SSD, this way it would be quite easy to "slice" the data.

I already used a two dimensional `btree` index `(from_timestamp, to_timestamp)` and they work very good, but the game changer was to `CLUSTER` the data by that index.
Using the correlation table, we can get this very interesting information for the tables

```sql
SELECT attname, correlation
FROM pg_stats
WHERE tablename = 'nodes_raw_gossip'
```


| attname   |   correlation |
| ----------- | -----------|
| timestamp   |   1 |
| gossip_id    |   0.0075054783 |
| gossip_id_str   |   0.0075054783 |
| node_id_str |   0.001692843 |
| raw_gossip  |   -0.0044449237 |
| node_id |   0.001692843 |




Here is the final query:

```sql
SELECT nrg.raw_gossip 
FROM nodes AS n
JOIN nodes_raw_gossip AS nrg 
ON n.node_id_str = nrg.node_id_str
WHERE {ts} BETWEEN n.from_timestamp AND n.last_seen
AND nrg.timestamp <= {ts}
AND nrg.timestamp >= {ts} - INTERVAL '14 days'

UNION ALL

SELECT c.raw_gossip
FROM channels AS c
WHERE {ts} BETWEEN c.from_timestamp AND c.to_timestamp

UNION ALL

SELECT cu.raw_gossip
FROM channel_updates AS cu
WHERE {ts} BETWEEN cu.from_timestamp AND cu.to_timestamp;
```

Using `UNION ALL` instead of `UNION` makes psql omit the check of duplication of the raw_gossip. Since filtering the result at a later point is possibly cheaply. The `raw_gossip` gets hashed to the `gossip_id`, preventing duplicate `raw_gossip` in the database.

The query now runs in around 1 second, enough for the `ln-history` platform.


## Discussion

This whole topic opened a new world for me. Before the summer school I already worked with (relational) databases, but never reached their limits. With this project I realized that they definitly have limitations and that a good database schema is not always found by normalizing. There is no free lunch, if the databases is optimized for inserting data efficiently, reading will get difficult and vice versa. If the database schema is defined to handle "backend tasks" such as complex filtering, the overall platform will likely not be as fast as it could be possible.   


### Tips and tricks to optimize your queries

- Configuring your database instance like increasing RAM or CPU power is less effective than optimizing the queries
- *ALWAYS* think of both ways: How to `INSERT` and `READ` data
- Using `COPY (<query>) TO '<path>' (FORMAT binary)` is much faster than `SELECT <query>`
- When working with analytical (`READ` heavy) queries: Store he data clustered such that the physical location of the data on disk correlates with the actual value of the data
- Use tools like `EXPLAIN (ANALYZE, BUFFER)` to see what *happens under the hood*
- Plan and take the time to optimize the database schema first before anything else, it will likely be the first bottleneck of the platform 

### Project management: Database schema **FIRST**
I learned a hard lesson: Setting up all micro services first, automating the insertion of data into the database and even optimizing that insertion just to find out that the `READ` queries run too slow. Before this challenge I simply was not aware that the database could be that much of a bottleneck.
It took me multiple weeks to set up the database: Time I thought I could use for building a beautiful frontend.


## Conclusion & Learnings

I realized that my initial expectation was completly different than the outcome. This lies in the fact that I did not have a lot of experience with data engineering on this scale as well as that I did not know enough about my problem. 

In retrospective I was subborn to normalizing the database just because I have only seen it that way before. By working on this problem for multiple weeks I got a deep understanding of it.
The whole debate about the database schema reminded me of the famous qoute `All problems in computer science can be solved by another level of indirection, except for the problem of too many layers of indirection` by `David Wheeler`. I abstracted the database schema such that every possible analysis could be done but by doing so I distanced the requirements from the database schema. This lead to overall weak performaing queries. By removing the abstraction and defining the schema specifically for the requirements, I was able to solve this problem. 

I also learned that for getting a "*near optimal*" result in software engineering means that you *do not* run some software in default configuration. It means to actually go as close to the machine level as possible removing every abstraction the software might create or even build it from scratch.

It took a lot of will power and endurance to start all over again with a new database schema twice. I am happy that I got this working with an extensive knowledge of the database.
By playing around, testing and restarting with a new schema I gained a lot of experience and feel much more confident about sql databases specifically Postgres.