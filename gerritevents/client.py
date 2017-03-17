import asyncio
import zmq
import zmq.asyncio
import sys
import argparse
import logging

from gerritevents import Log

log = Log(__name__)


class GerritEventSubscriber:
    def __init__(self, loop, git_binary=None, brokers=None, repos=None):
        self.loop = loop
        self.git_binary = git_binary
        self.brokers = brokers
        self.ctx = zmq.asyncio.Context()
        self.beat = asyncio.Queue()
        self.message_queue = asyncio.Queue()
        self.sock = self.ctx.socket(zmq.SUB)
        self.repos = repos
        self.running_fetch = []
        self.re_schedule_fetch = []

    async def heartbeat(self):
        """
        Very simple heartbeat handler. Will make the client stop if no beats
        are received during a 60 sec time frame
        """
        log.info(event='heartbeat', message='starting heartbeat')
        counter = 0
        while True:
            try:
                log.debug(event='heartbeat', message='received')
                self.beat.get_nowait()
                counter = 0
            except:
                log.warning(
                    event='heartbeat', message='missed', counter=counter)
                counter += 1
            if counter >= 5:
                msg = 'too many beats missed! shutting down!'
                log.error(event='heartbeat', message=msg)
                # Closing our zmq socket so we get a clean exit
                self.sock.close()
                break
            await asyncio.sleep(10)

    async def dispatcher(self):
        """
        server that listens for queue events where it schedule git fetches
        """
        log.info(event='dispatcher', message='starting')
        while True:
            repo = await self.message_queue.get()
            log.debug(
                event='dispatcher', message='new dispatch', repository=repo)
            if repo not in self.running_fetch:
                log.debug(
                    event='dispatcher',
                    message='scheduling fetch',
                    repository=repo)
                self.running_fetch.append(repo)
                asyncio.ensure_future(self.fetch_git(repo))
            else:
                if repo not in self.re_schedule_fetch:
                    log.debug(
                        event='dispatcher',
                        message='scheduling re-fetch',
                        repository=repo)
                    self.re_schedule_fetch.append(repo)
                    asyncio.ensure_future(self.re_dispatcher(repo))
                else:
                    log.debug(
                        event='dispatcher',
                        message='already in re-fetch',
                        repository=repo)

    async def re_dispatcher(self, repo):
        """
        Sorting out rescheduling of git fetches when an instance is alread
        running
        """
        while True:
            if repo not in self.running_fetch:
                log.debug(
                    event='re.dispatcher',
                    message='scheduling fetch',
                    repository=repo)
                self.running_fetch.append(repo)
                self.re_schedule_fetch.remove(repo)
                await self.fetch_git(repo)
                break
            log.debug(
                event='re.dispatcher',
                message='waiting for timeslot',
                repository=repo)
            await asyncio.sleep(1)

    async def fetch_git(self, repo):
        """
        Subprocess that updates the git repo
        """
        log.debug(event='fetch.git', message='starting', repository=repo)
        proc = await asyncio.create_subprocess_exec(
            self.git_binary,
            '-C',
            self.repos[repo]['path'],
            'fetch',
            self.repos[repo]['origin'],
            self.repos[repo]['refs'],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout = await proc.stdout.read()
        stderr = await proc.stderr.read()
        await proc.wait()
        log.info(event='fetch.git', message='completed', repository=repo)
        log.debug(
            event='fetch.git',
            message='output',
            repository=repo,
            stdout=stdout.decode('ascii').rstrip(),
            stderr=stderr.decode('ascii').rstrip())
        self.running_fetch.remove(repo)

    async def zmq_subscriber(self):
        """
        Subscribe to events from configured ZMQ brokers
        """
        log.info(event='zmq.subscriber', message='starting')
        self.sock.setsockopt(zmq.SUBSCRIBE, b'gerritstream')
        for broker in self.brokers:
            self.sock.connect(broker)
        while True:
            answer = await self.sock.recv_multipart()
            message = [x.decode('utf-8') for x in answer[1:]]
            if message[0] == 'keepalive':
                self.beat.put_nowait(message[1])
            elif message[0] == 'ref-replication-done':
                if message[1] in self.repos.keys():
                    log.debug(
                        event='zmq.subscriber',
                        message='placing in queue',
                        repository=message[1])
                    self.message_queue.put_nowait(message[1])
                else:
                    log.debug(
                        event='zmq.subscriber',
                        message='unknown repo',
                        repository=message[1])
            else:
                log.debug(
                    event='zmq.subscriber',
                    message='unknown message type',
                    payload=message)


if __name__ == '__main__':
    print('you should override me!')
