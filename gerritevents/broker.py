import asyncio
import asyncssh
import aiozmq
import zmq
import sys
import json

from gerritevents import Log

log = Log(__name__)


class MySSHClientSession(asyncssh.SSHClientSession):
    def data_received(self, data, datatype):
        log.debug(event='data.received', message=data)
        GerritEventBroker.raw_messages.put_nowait(data)

    def connection_lost(self, exc):
        if exc:
            log.error(event='connection.lost', message=exc)


class GerritEventBroker():

    raw_messages = asyncio.Queue()

    def __init__(self, server='', port=29418, events=[], zmq_port=''):
        self.server = server
        self.port = port
        self.events = events
        self.zmq_port = zmq_port
        self.messages = asyncio.Queue()
        self.publisher = None

    async def ssh_connection(self):
        """
        Connect to gerrit server and stream events to messages queue
        """
        log.info(event='ssh.connection', message='starting')
        async with asyncssh.connect(self.server, port=self.port) as conn:
            chan, session = await conn.create_session(MySSHClientSession,
                                                      'gerrit stream-events')
            await chan.wait_closed()
        log.error(event='ssh.connection', message='terminating application')
        self.publisher.close()
        sys.exit(1)


    async def message_handler(self):
        """
        Handle and parse all events from the 'gerrit stream-events' to match
        our filters
        """
        while True:
            raw_data = await self.raw_messages.get()
            data = json.loads(raw_data)
            if data['type'] in self.events:
                self.messages.put_nowait([data['type'], data['project']])

    async def zmq_publisher(self):
        """
        Create a publisher server which is feeding the stream with all events
        occuring in the self.messages Queue
        """
        log.info(event='zmq.publisher', message='starting')
        self.publisher = await aiozmq.create_zmq_stream(
            zmq.PUB, bind='tcp://*:' + self.zmq_port)
        while True:
            data = await self.messages.get()
            msg = (b'gerritstream', str(data[0]).encode('utf-8'),
                   str(data[1]).encode('utf-8'))
            log.debug(event='zmq.publisher', message=msg)
            self.publisher.write(msg)

    async def zmq_keepalive(self):
        """
        Keep-alive and rudimentary heartbeat (client will simply be informed
        when the server dies and can do alternative syncs meanwhile)
        """
        while True:
            self.messages.put_nowait(['keepalive', 'ping'])
            await asyncio.sleep(10)


if __name__ == '__main__':
    print('override me!')
