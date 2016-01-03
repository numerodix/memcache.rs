from collections import OrderedDict
import re

from pyperf.socket_stream import BufferedSocketStream


class MemcacheClientParams(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def create_client(self):
        return MemcacheClient(
            host=self.host,
            port=self.port,
        )


class ItemNotFoundError(Exception):
    pass

class SetFailedError(Exception):
    pass


class Item(object):
    def __init__(self, key, flags, value):
        self.key = key
        self.flags = flags
        self.value = value

    def __repr__(self):
        return '<%s key=%r, flags=%r, value=%r>' % (
            self.__class__.__name__,
            self.key,
            self.flags,
            self.value,
        )


class MemcacheClient(object):
    rx_value = re.compile('VALUE (?P<key>[^ ]*) (?P<flags>\d+) (?P<len>\d+)')

    def __init__(self, host, port):
        self.stream = BufferedSocketStream(host, port)

    def get_stats(self):
        dct = OrderedDict()

        # prepare command
        command = 'stats\r\n'

        # execute command
        self.stream.write(command)

        # read response line by line
        stream_terminator = 'END\r\n'

        line = self.stream.read_line()
        while line != stream_terminator:
            kw, key, value = line.split(' ', 2)
            dct[key] = value.strip()

            line = self.stream.read_line()

        return dct

    def print_stats(self):
        dct = self.get_stats()
        for (key, value) in dct.items():
            print('%s: %s' % (key, value))

    def get_multi(self, keys):
        # prepare command
        keys = ' '.join(keys)
        command = 'get %s\r\n' % keys

        # execute command
        self.stream.write(command)

        # parse the response
        dct = OrderedDict()
        stream_terminator = 'END\r\n'

        while True:
            line = self.stream.read_line()
            try:
                key, flags, bytelen = self.rx_value.findall(line)[0]
                flags = int(flags)
                bytelen = int(bytelen)
            except IndexError:
                # no items were returned at all
                if line == stream_terminator:
                    break

            # read value + line terminator
            data = self.stream.read_exact(bytelen + 2)

            data = data[:-2]
            item = Item(key, flags, data)
            dct[key] = item

            if self.stream.peek_contains(stream_terminator, consume=True):
                break

        return dct

    def get(self, key):
        keys = (key,)
        dct = self.get_multi(keys)

        try:
            return dct[key]
        except KeyError:
            raise ItemNotFoundError('The item with key %r was not found' % key)

    def set(self, key, value, flags=0, exptime=0, noreply=False):
        # prepare command
        header = 'set %(key)s %(flags)d %(exptime)d %(bytelen)d %(noreply)s\r\n' % {
            'key': key,
            'flags': flags,
            'exptime': exptime,
            'bytelen': len(value),
            'noreply': 'noreply' if noreply else '',
        }
        command = header + value + '\r\n'

        # execute command
        self.stream.write(command)

        # check for success
        if not noreply:
            resp = self.stream.read_line()
            if not resp == 'STORED\r\n':
                raise SetFailedError('Could not set key %r to %r...' % (key, value[:10]))

    def send_malformed_cmd(self):
        '''Sends an invalid command - causes the server to drop the
        connection'''

        self.stream.write('set 0 1\r\n')
        buf = self.stream.read(4096)
        return buf.strip()
