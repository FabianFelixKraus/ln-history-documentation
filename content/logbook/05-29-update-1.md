+++
title = "2025-05-16 - Logbook 0 - Kickoff"
description = "Kickoff of ln-history"
date = "2025-05-16"
+++

## 🏋️ Project implementation

## 📢 Setup Plugin: Gossip-Publisher-zmq
I continued working on the Core Lightning plugin [gossip-publisher-zmq](https://github.com/ln-history/gossip-publisher-zmq). 

After some trial and error my Core Lightning node started to run on `mainnet`. To keep things as simple as possible I use the [trustedcoin](https://github.com/nbd-wtf/trustedcoin) plugin which removes the hassle of setting up ones own Bitcoin backend.

While building this plugin I looked deeper into the protocol specifications called [BOLT](https://github.com/lightning/bolts/tree/master), specifically [BOLT 7](https://github.com/lightning/bolts/blob/master/07-routing-gossip.md), which defines the structure of the gossip messages.
When using the plugin every gossip message gets published in its raw as well as in a parsed form, giving the node operator the chance to analyze them directly. 

So far plugin as published over `100000` gossip messages.

## Micro-Service: `gossip-unifier`:
Last week I deploed the `gossip-unifier`, which subscribes to the published gossip_messages of the `gossip-publisher-zmq` plugin. The micro service is written in python and runs inside a docker container. Additionaly I use Github Actions as a CI/CD pipeline for automatic deployments.
Right now the `gossip-unifier` is only able to subscribe to one publisher, meaning it can only handle the gossip of one node. As a next step I want to extend the functionality that it is able to handle the gossip of multiple nodes. 


## Micro-Service: `gossip-syncer`:
I am not done with the `gossip-syncer`, since I am still considering the ideal structure of the `ln-history-database`.  Nonetheless, I setup the repository 


## Infrastructure: `Kafka`
I successfully deployed this [docker image](https://github.com/bitnami/containers/blob/main/bitnami/kafka/README.md) via `docker compose`. I am running Kafka in *KRaft* mode with a production ready security setup.


## Testing: `ln-history-database-test-suite`
I wrote a simple "Lightning Network gossip Faker" which creates many gossip messages quickly. I already used this gossip to test out different database technologies.
The well known open source project [postgre-sql](https://www.postgresql.org/docs/) in its base configuration is already able to handle millions of gossip messages very fast (less than 1 second).


## Data `ln-history-database`
The core of this project is still under very active development. I want to be done with this part in the next logbook entry.