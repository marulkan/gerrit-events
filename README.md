============
gerritevents
============

Fetch git-bare repos from gerrit when they are updated and propagated to the mirrors.

Run broker with::
	
	$ gerrit-event-broker --config-file ./config.yaml --log-file ./gerrit-events-broker.log

Run client with::
	
	$ gerrit-event-client --config-file ./config.yaml --log-file ./gerrit-events-clients.log

Why
===

Instead of having a lot of servers connected to the ssh port of gerrit and 
listening for the same event, let them subscribe to a ZeroMQ socket where the 
update is published. Primarly intended to have the amount of connections to 
the gerrit server kept to a minimum.

How
===

Gerritevents consists of 2 applications, one listening for gerrit 
stream-events through SSH and is intended to run as a systemd service. 
Example file of this will be found in examples folder soon(tm). 
A predefined subset of stream-events will be broadcasted on a ZeroMQ PUBLISH 
socket.

The second application connects to the broker application with ZeroMQ 
SUBSCRIBE socket. When receiving a message the client makes a lookup in its 
config if the repo is defined. If it's defined it will create a subprocess 
with git-fetch.

Requirements
============

  * aiozmq (sending messages between broker and client)
  * pyzmq
  * asyncssh (connection to gerrit server)
  * PyYAML (for configuration)