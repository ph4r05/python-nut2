import asyncio

# make logger debug print to stdout
import logging
import sys
import threading
import unittest

from nut2 import PyNUTClient, PyNUTError

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class MockNUTProtocol(asyncio.Protocol):
    last_instance = None

    def __init__(self):
        super().__init__()
        self.transport = None
        self._buffer = b""

        self.valid = b"test"
        self.valid_desc = b'"Test UPS 1"'
        self.broken = False
        self.ok = True
        self.broken_username = None
        self.command = None
        MockNUTProtocol.last_instance = self
        logging.debug("Mock NUT Protocol initialized")

    def connection_made(self, transport):
        self.transport = transport
        self._buffer = b""
        logging.debug("Connection made to Mock NUT Protocol")

    def run_command(self):
        if self.broken and not self.broken_username and self.command == b"USERNAME %s\n" % self.valid:
            return b"OK\n"
        elif self.broken:
            return b"ERR\n"
        elif self.command == b"HELP\n":
            return b"Commands: HELP VER GET LIST SET INSTCMD LOGIN LOGOUT USERNAME PASSWORD STARTTLS\n"
        elif self.command == b"VER\n":
            return b"Network UPS Tools upsd 2.7.1 - http://www.networkupstools.org/\n"
        elif self.command == b"GET CMDDESC %s %s\n" % (self.valid, self.valid):
            return b"CMDDESC " + self.valid + b" " + self.valid + b" " + self.valid_desc + b"\n"
        elif self.command == b"LIST UPS\n":
            return (
                b"BEGIN LIST UPS\nUPS "
                + self.valid
                + b" "
                + self.valid_desc
                + b'\nUPS Test_UPS2 "Test UPS 2"\nEND LIST UPS\n'
            )
        elif self.command == b"LIST VAR %s\n" % self.valid:
            return (
                b"BEGIN LIST VAR "
                + self.valid
                + b"\nVAR "
                + self.valid
                + b' battery.charge "100"\nVAR '
                + self.valid
                + b' battery.voltage "14.44"\nEND LIST VAR '
                + self.valid
                + b"\n"
            )
        elif self.command.startswith(b"LIST VAR"):
            return b"ERR INVALID-ARGUMENT\n"
        elif self.command == b"LIST CMD %s\n" % self.valid:
            return (
                b"BEGIN LIST CMD "
                + self.valid
                + b"\nCMD "
                + self.valid
                + b" "
                + self.valid
                + b"\nEND LIST CMD "
                + self.valid
                + b"\n"
            )
        elif self.command.startswith(b"LIST CMD"):
            return b"ERR INVALID-ARGUMENT\n"
        elif self.command == b"LIST RW %s\n" % self.valid:
            return (
                b"BEGIN LIST RW "
                + self.valid
                + b"\nRW "
                + self.valid
                + b" "
                + self.valid
                + b' "test"\nEND LIST RW '
                + self.valid
                + b"\n"
            )
        elif self.command.startswith(b"LIST RW"):
            return b"ERR INVALID-ARGUMENT\n"
        elif self.command == b"LIST CLIENTS %s\n" % self.valid:
            return b"BEGIN LIST CLIENTS\nCLIENT " + self.valid + b" " + self.valid + b"\nEND LIST CLIENTS\n"
        elif self.command.startswith(b"LIST CLIENTS"):
            return b"ERR INVALID-ARGUMENT\n"
        elif self.command == b"LIST ENUM %s %s\n" % (self.valid, self.valid):
            return (b"BEGIN LIST ENUM %s %s\n" % (self.valid, self.valid)) + (
                b"ENUM %s %s %s\nEND LIST ENUM %s %s\n"
                % (self.valid, self.valid, self.valid_desc, self.valid, self.valid)
            )

        elif self.command == b"LIST RANGE %s %s\n" % (self.valid, self.valid):
            return (b"BEGIN LIST RANGE %s %s\n" % (self.valid, self.valid)) + (
                b"RANGE %s %s %s %s\nEND LIST RANGE %s %s\n"
                % (self.valid, self.valid, self.valid_desc, self.valid_desc, self.valid, self.valid)
            )
        elif self.command == b"SET VAR %s %s %s\n" % (self.valid, self.valid, self.valid):
            return b"OK\n"
        elif self.command.startswith(b"SET"):
            return b"ERR ACCESS-DENIED\n"
        elif self.command == b"INSTCMD %s %s\n" % (self.valid, self.valid):
            return b"OK\n"
        elif self.command.startswith(b"INSTCMD"):
            return b"ERR CMD-NOT-SUPPORTED\n"
        # TODO: LOGIN/LOGOUT commands
        elif self.command == b"USERNAME %s\n" % self.valid:
            return b"OK\n"
        elif self.command.startswith(b"USERNAME"):
            return b"ERR\n"  # FIXME: What does it say on invalid password?
        elif self.command == b"PASSWORD %s\n" % self.valid:
            return b"OK\n"
        elif self.command.startswith(b"PASSWORD"):
            return b"ERR\n"  # FIXME: ^
        elif self.command == b"STARTTLS\n":
            return b"ERR FEATURE-NOT-CONFIGURED\n"
        elif self.command == b"MASTER %s\n" % self.valid:
            return b"OK MASTER-GRANTED\n"
        elif self.command == b"FSD %s\n" % self.valid and self.ok:
            return b"OK FSD-SET\n"
        elif self.command == b"FSD %s\n" % self.valid:
            return b"ERR\n"
        elif self.command == b"GET NUMLOGINS %s\n" % self.valid:
            return b"NUMLOGINS %s 1\n" % self.valid
        elif self.command.startswith(b"GET NUMLOGINS"):
            return b"ERR UNKNOWN-UPS\n"
        elif self.command == b"GET UPSDESC %s\n" % self.valid:
            return b"UPSDESC %s %s\n" % (self.valid, self.valid_desc)
        elif self.command.startswith(b"GET UPSDESC"):
            return b"ERR UNKNOWN-UPS\n"
        elif self.command == b"GET VAR %s %s\n" % (self.valid, self.valid):
            return b'VAR %s %s "100"\n' % (self.valid, self.valid)
        elif self.command.startswith(b"GET VAR %s" % self.valid):
            return b"ERR VAR-NOT-SUPPORTED\n"
        elif self.command.startswith(b"GET VAR "):
            return b"ERR UNKNOWN-UPS\n"
        elif self.command.startswith(b"GET VAR"):
            return b"ERR INVALID-ARGUMENT\n"
        elif self.command == b"GET TYPE %s %s\n" % (self.valid, self.valid):
            return b"TYPE %s %s RW STRING:3\n" % (self.valid, self.valid)
        elif self.command.startswith(b"GET TYPE %s" % self.valid):
            return b"ERR VAR-NOT-SUPPORTED\n"
        elif self.command.startswith(b"GET TYPE"):
            return b"ERR INVALID-ARGUMENT\n"
        elif self.command == b"GET DESC %s %s\n" % (self.valid, self.valid):
            return b"DESC %s %s %s\n" % (self.valid, self.valid, self.valid_desc)
        elif self.command.startswith(b"GET DESC"):
            return b"ERR-INVALID-ARGUMENT\n"
        elif self.command == b"GET CMDDESC %s %s" % (self.valid, self.valid):
            return b"CMDDESC %s %s %s\n" % (self.valid, self.valid, self.valid_desc)
        elif self.command.startswith(b"GET CMDDESC"):
            return b"ERR INVALID-ARGUMENT"
        else:
            return b"ERR UNKNOWN-COMMAND\n"

    def data_received(self, data):
        self.command = data
        command = data.decode().strip()
        logging.debug("Data received: %s", command)

        # Send fake NUT responses
        if command == "LOGOUT":
            self.transport.write(b"OK\n")
            self.transport.close()
        else:
            response = self.run_command()
            logging.debug("Sending response: %s", response.decode())
            self.transport.write(response)


async def start_mock_nut_server(host="127.0.0.1", port=3493):
    loop = asyncio.get_running_loop()
    server = await loop.create_server(MockNUTProtocol, host, port, reuse_address=True)
    logging.debug("Mock NUT server started on %s:%s", host, port)
    return server


class TestWithMockNUTServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = "test"
        cls.invalid = "does_not_exist"
        cls.valid_ups_name = "Test UPS 1"
        cls.valid_desc = cls.valid_ups_name
        cls.valid_value = "100"
        cls.valid_command_desc = cls.valid_desc

        cls.loop = asyncio.new_event_loop()
        cls.server_thread = threading.Thread(target=cls._start_server, daemon=True)
        cls.server_thread.start()
        asyncio.run(asyncio.sleep(0.4))  # Give time to start

    @classmethod
    def _start_server(cls):
        asyncio.set_event_loop(cls.loop)
        server = start_mock_nut_server()
        cls.loop.run_until_complete(server)
        cls.loop.run_forever()

    @classmethod
    def client(cls):
        return PyNUTClient(timeout=40, connect_minwait=0, connect_maxwait=0)

    def test_list_ups(self):
        client = self.client()
        result = client.list_ups()
        logging.debug("Received result: %s", result)
        self.assertIn("test", result)
        self.assertEqual(result["test"], "Test UPS 1")

    def test_get_ups_vars_valid_ups(self):
        client = self.client()
        vars = client.list_vars(self.valid)
        self.assertEqual(type(vars), dict)
        self.assertEqual(len(vars), 2)
        self.assertEqual(vars["battery.charge"], "100")

    def test_help(self):
        client = self.client()
        help_text = client.help()
        self.assertIn("HELP", help_text)

    def test_ver(self):
        client = self.client()
        ver_text = client.ver()
        self.assertIn("Network UPS Tools", ver_text)

    def test_get_var(self):
        client = self.client()
        val = client.get_var(self.valid, self.valid)
        self.assertEqual(val, "100")

    def test_description(self):
        client = self.client()
        desc = client.description(self.valid)
        self.assertEqual(desc, self.valid_desc)

    def test_set_var_valid(self):
        client = self.client()
        try:
            client.set_var(self.valid, self.valid, self.valid)
        except Exception as e:
            self.fail("set_var raised Exception unexpectedly: %s" % e)

    def test_run_command_valid(self):
        client = self.client()
        try:
            client.run_command(self.valid, self.valid)
        except Exception as e:
            self.fail("run_command raised Exception unexpectedly: %s" % e)

    def test_fsd_valid(self):
        client = self.client()
        try:
            client.fsd(self.valid)
        except Exception as e:
            self.fail("fsd raised Exception unexpectedly: %s" % e)

    def test_num_logins(self):
        client = self.client()
        count = client.num_logins(self.valid)
        self.assertEqual(count, 1)

    def test_var_description(self):
        client = self.client()
        desc = client.var_description(self.valid, self.valid)
        self.assertEqual(desc, self.valid_desc)

    def test_var_type(self):
        client = self.client()
        var_type = client.var_type(self.valid, self.valid)
        self.assertEqual(var_type, "RW STRING:3")

    def test_list_commands(self):
        client = self.client()
        cmds = client.list_commands(self.valid)
        self.assertEqual(cmds, {self.valid: self.valid_desc})

    def test_list_enum(self):
        client = self.client()
        enums = client.list_enum(self.valid, self.valid)
        self.assertEqual(enums, [self.valid_desc])

    def test_list_range(self):
        client = self.client()
        ranges = client.list_range(self.valid, self.valid)
        self.assertEqual(ranges, [self.valid_desc])

    def test_command_description(self):
        client = self.client()
        desc = client.command_description(self.valid, self.valid)
        self.assertEqual(desc, self.valid_desc)

    def test_list_rw_vars(self):
        client = self.client()
        rw_vars = client.list_rw_vars("test")
        self.assertIsInstance(rw_vars, dict)
        self.assertIn("test", rw_vars)

    def test_get_var_not_found(self):
        client = self.client()
        with self.assertRaises(PyNUTError):
            client.get_var("test", "nonexistent")

    def test_set_var_access_denied(self):
        client = self.client()
        with self.assertRaises(PyNUTError):
            client.set_var("test", "readonly.var", "value")

    def test_run_command_invalid(self):
        client = self.client()
        with self.assertRaises(PyNUTError):
            client.run_command("test", "unsupported")

    def test_list_range_missing_end(self):
        client = self.client()

        async def broken_reader():
            return 'BEGIN LIST RANGE test var\nRANGE test var "10" "20"\n'  # no END

        client._async_send_and_receive = lambda *a, **k: broken_reader()
        with self.assertRaises(PyNUTError):
            client.list_range("test", "var")

    def test_list_clients(self):
        client = self.client()
        clients = client.list_clients("test")
        self.assertIsInstance(clients, dict)
        self.assertIn("test", clients)
        self.assertIn("test", clients["test"])
