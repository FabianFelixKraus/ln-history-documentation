+++
title = "Lightning Network History"
description = "An open source project to unvail the Lightning Networks history."
+++

## ⚡️ Motivation
Since the beginning of Bitcoin on Janurary 3rd 2009, it has kept many of its promises and is establishing itself as a store-of-value solution.
Nonetheless Satoshi Nakamoto titled in the [Bitcoin Whitepaper](https://bitcoin.org/bitcoin.pdf) "Bitcoin: A Peer-to-Peer Electronic Cash System", emphesising on its use case as digital cash for peer to peer transactions. The Bitcoin blockchain, the leger that keeps track of every transaction, is limited in its scaleability. To keep the Bitcoin blockchain as decentralized as possible, any idea of directly scaling it by e. g. increasing the storage size per block, failed. 

With a constant rate of adoption, storing information on the Bitcoin blockchain is scarce. In 2024 transaction costs reached record highs, making it unaffordable for daily use.

The Lightning Network - a second layer solution on top of Bitcoin - deployed in 2018, promises lightning fast and cheap payments, ultimatly scaling the transaction volume of Bitcoin. 
The technology of the Bitcoin Lightning Network is defined in [BOLTS](https://github.com/lightning/bolts/tree/master).
Although more than seven years passed, there are open questions for research about the Bitcoin Lightning Network.

## 🏁 Goal 
The aim of this open source project is to build a platform for researchers as well as node runners to help understand the (changing) topology of the Bitcoin Lightning Network, making it more accessible. 

Precisly we want the following requirements to be met
- Get a snapshot (raw gossip messages) of the network at a given timestamp (How did the network look?)
- Get the difference between two snapshots for two given timestamps (How did the network change?)
- Get all gossip messages by a given node_id (How much did a node contribute to the network change?)
- Get all gossip messages by a given scid (How much did a channel change ?)

We also build a backend that exposes an [API](api.ln-history.info) that can be accessed to get those analysis results. 
See [here](https://github.com/FabianFelixKraus/LN-history) for the code behind the analysis.


## 📊 Data
The analyzed gossip messages come from [Christian Deckers](https://github.com/cdecker) [lnresearch](https://github.com/lnresearch/topology/tree/main) repository.
Additionally we spin up our one nodes in July 2025 to record gossip messages.

We currently have a total number of around 100 million recorded gossip messages.

![Number of recorded gossip messages grouped by type](01-01-data-set-analysis-total-number-of-gossip-messages.svg)

We can see that the number of channel update messages has been changing a lot.

![Number of channel update messages](01-02-data-set-analysis-number-of-channel-update-messages.svg)

As the number of nodes in the Bitcoin Lightning Network rose, the number of node anouncement messages also rose.

![Number of node announcement messages](01-03-dataset-analysis-number-of-node-announcement-messages.svg)

## ⊰⊱ Schema
To meet the requirements we use a [postgresql](https://www.postgresql.org/) database with the [btree_gist](https://www.postgresql.org/docs/current/btree-gist.html) extension.

You can build the database yourself by creating the following tables:
```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 1. GossipMessageTypes
CREATE TABLE gossip_message_types (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL UNIQUE
);

INSERT INTO gossip_message_types (id, name) 
VALUES 
  (256, 'channel_announcement'),
  (257, 'node_announcement'),
  (258, 'channel_update');

-- 2. RawGossip
CREATE TABLE raw_gossip (
  gossip_id BYTEA PRIMARY KEY CHECK (octet_length(gossip_id) = 32),  -- sha256 is 32 bytes
  gossip_message_type INTEGER NOT NULL REFERENCES gossip_message_types(id),
  timestamp TIMESTAMPTZ NOT NULL,
  raw_gossip BYTEA NOT NULL
);

-- 3. NodesRawGossip
CREATE TABLE nodes_raw_gossip (
  gossip_id BYTEA PRIMARY KEY REFERENCES raw_gossip(gossip_id),
  node_id BYTEA NOT NULL CHECK (octet_length(node_id) = 33)  -- 33 bytes
);

-- 4. Nodes
CREATE TABLE nodes (
  node_id BYTEA PRIMARY KEY CHECK (octet_length(node_id) = 33) -- 33 bytes,
  validity tstzrange NOT NULL  -- from_timestamp, last_seen as range
);

-- 5. ChannelsRawGossip
CREATE TABLE channels_raw_gossip (
  gossip_id BYTEA PRIMARY KEY REFERENCES raw_gossip(gossip_id),
  scid VARCHAR(23) NOT NULL
);

-- 6. Channels
CREATE TABLE channels (
  scid VARCHAR(23) PRIMARY KEY,
  source_node_id BYTEA NOT NULL REFERENCES nodes(node_id),
  target_node_id BYTEA NOT NULL REFERENCES nodes(node_id),
  validity tstzrange NOT NULL, -- from_timestamp to to_timestamp
  amount_sat INTEGER
);

-- 7. ChannelUpdates
CREATE TABLE channel_updates (
  scid VARCHAR(23) NOT NULL REFERENCES channels(scid),
  direction BOOLEAN NOT NULL,
  validity tstzrange NOT NULL, -- from_update_timestamp to to_update_timestamp as range
  PRIMARY KEY (scid, direction)
);
```


<!-- ## ✨ Results
Currently we have two objectives of our analysis of the Lightning Networks history.

1. Lightning Network metrics

To get an overall view of the topology we want to show different metrics of the topology at different timestamps.

2. Lightning Network vs Bitcoin Blockchain

We try to find correlations of the Bitcoin Lightning Network with the Bitcoin blockchain. More precisely, we research if the cost of a payment in the Lightning Network correlates with the fees on the Bitcoin blockchain. Those results could be particularly interesting for (routing) nodes that need to manage their liquidity as cost-efficient as possible. -->

## 💻 Api
See [here](https://api.ln-history.info) for the swagger documentation of our API. The backend code can be found on [GitHub](https://github.com/FabianFelixKraus/LN-history) or mirrored on my univerisities [GitLab](https://git.tu-berlin.de/lightning-network-analysis/ln-history)