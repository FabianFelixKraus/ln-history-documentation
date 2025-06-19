+++
title = "2025-05-16 - Logbook 0 - Kickoff"
description = "Kickoff of ln-history"
date = "2025-05-16"
+++


## 🎉 Acceptance for Summer of Bitcoin 2025

My application for [Summer of Bitcoin 2025](https://www.summerofbitcoin.org/) got accepted and I am very grateful to bring my project: `ln-history` to life!
[René Pickhardt](https://github.com/renepickhardt) is going to be my mentor.
We already had our official "Kickoff" meeting and I am confident to finish this project.


## 💼 Project structure and management

For my application I created this [Github project](https://github.com/orgs/ln-history/projects/1), to keep track of all issues.
Additionaly I grouped the issues into `milestones` to divide the project into smaller projects that are in itself complete. 


### Updates to the project structure

After the kickoff meeting it became clear, that for the first version of `ln-history-data` a graph database might not be the best solution technically. 
I will go through the milestones and the next issues and update them accordingly. 
I do not want to spend much time planning and managing my project, instead I want to get this done an actually work on the issues. Therefore I will keep them as minimal as possible. 


## 🏋️ Project implementation

### Plugin: `gossip-publisher-zmq`

See this [repository](github.com/ln-history/gossip-publisher-zmq) for the latest version.
I first needed to dive into [Core Lightning plugin](https://docs.corelightning.org/docs/plugins) development, where I found [those recorded coding sessions](https://lnroom.live/2023-03-28-live-0001-understand-cln-plugin-mechanism-with-a-python-example/) especially helpful as well as [zero message queues](https://zeromq.org/) (in short: *zeroMQ*).
Both technologies provide well documentation so I could this [repository](github.com/ln-history/gossip-publisher-zmq) quickly and started to develop the plugin.

I was surprised how well the zeroMQ works and after some time I got the plugin running. 
After that I had to write parsers for the different types of messages. You can see the commit in which I added them [here](https://github.com/ln-history/gossip-publisher-zmq/commit/77a1e24b36b629d5f530de9dffc36e0aa4198fee).
I tested the parser and setup in a `regtest` network.

My next step is to test the plugin in the `mainnet`. I am planning to use [sauron](https://github.com/lightningd/plugins/tree/master/sauron), a Core Lightning plulgin which changes the backend of the node to use an already synced bitcoin node e. g. [Esplora](https://github.com/Blockstream/esplora/blob/master/API.md) 



### Data: `ln-history-database`

In the kickoff meeting, I discussed with René the requirements of the database. In my initial planning I was trying to do two things at once:
- plain storage of the gossip messages 
- storage of the gossip messages in a way that they are ready to be analysed (without / less parsing for the client)

I thought that using a graph database is an obvious choice since the Lightning Network is a graph and I would like to store that.

I am currently testing to store the gossip messages in a SQL database that uses multi-dimensional indices and ranges for timstamps on tables. This will be complimented with a cache, that stores the *live* Lightning Network, meaning all nodes and edges that have not been closed. 


## Micro-Services: `gossip-unifier`, `gossip-syncer`:

I stared to setup the repositories and did local testing with test gossip messages.
Until the next logbook entry I want to have them running on a server.  
 

## Infrastructure: `Kafka`
I want to deploy the Kafka instance on a server and use ssl for authentication. I am planning to use this [docker image](https://github.com/bitnami/containers/blob/main/bitnami/kafka/README.md) and run Kafka in *KRaft* mode.


## Testing: `ln-history-database-test-suite`
I setup this [repository](https://github.com/ln-history/ln-history-database-test-suite) which serves the purpose to create fake gossip messages that can be used to test different services mainly the `ln-history-database`.

I want to use [Faker](https://faker.readthedocs.io/en/master/) to accomplish this.


## Documentation
Until the next logbook entry I want to have decided how I document the platform.
I will use the `README.md` in every repository to explain how they work individually, but I need a place to document the overall platform. 


## ⏮️ Final words

I am looking forward to working on `ln-history`. 
Although I thought a lot about the planning of the project, I will (most likely) need to constantly adapt and improve my planned issues. 
While writing this logbook entry I realize that a solid documentation of every piece is really helpful to maintain an overview of everything.
Since the project starts from the ground up, I have many possibilities on how to tackle this: Which technologies do I use, how do I define my interfaces of the different services, etc. 
Those decisions become much easier if the requirements of the component are well defined and clear. I want to use this approach until the next logbook entry to refactor some parts of the platform, making it easier to maintain and scale.