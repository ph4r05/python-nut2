import sys
import telnetlib
import unittest

from mockserver import MockServer

if sys.version_info >= (3, 13):
    import pytest

    pytest.skip("Skipping test_client.py on Python >= 3.13 (telnetlib removed)", allow_module_level=True)
    raise unittest.SkipTest("test_client.py tests are only supported on Python 3.13 or lower")

try:
    from mock import Mock
except ImportError:
    from unittest.mock import Mock

from nut2.nut2_old import PyNUTClient, PyNUTError


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = PyNUTClient(connect=False, debug=True)
        self.client._srv_handler = MockServer(broken=False)
        self.broken_client = PyNUTClient(connect=False, debug=True)
        self.broken_client._srv_handler = MockServer(broken=True)
        self.not_ok_client = PyNUTClient(connect=False, debug=True)
        self.not_ok_client._srv_handler = MockServer(ok=False, broken=False)
        self.valid = "test"
        self.invalid = "does_not_exist"
        self.valid_ups_name = "Test UPS 1"
        self.valid_desc = self.valid_ups_name
        self.valid_value = "100"
        self.valid_command_desc = self.valid_desc
        telnetlib.Telnet = Mock()

    def test_init_with_args(self):
        PyNUTClient(connect=False, login="test", password="test", host="test", port=1)

    def test_supports_context_manager(self):
        try:
            with PyNUTClient(connect=False):
                pass
        except AttributeError:
            raise AssertionError()

    def test_connect(self):
        try:
            PyNUTClient()
        except Exception:
            raise AssertionError()

    def test_connect_debug(self):
        try:
            PyNUTClient(debug=True)
        except Exception:
            raise AssertionError()

    def test_connect_broken(self):
        telnetlib.Telnet = MockServer
        client = PyNUTClient(login=self.valid, password=self.valid, connect=False)
        self.assertRaises(PyNUTError, client._connect)

    def test_connect_credentials(self):
        try:
            PyNUTClient(login=self.valid, password=self.valid, debug=True)
        except TypeError:
            pass
        except PyNUTError:
            pass
        except Exception:
            raise AssertionError()

    def test_connect_credentials_username_ok(self):
        try:
            telnetlib.Telnet = MockServer
            PyNUTClient(login=self.valid, password=self.valid, debug=True)
        except TypeError:
            pass
        except PyNUTError:
            pass
        except Exception:
            raise AssertionError()

    def test_get_ups_list(self):
        ups_list = self.client.list_ups()
        self.assertEqual(type(ups_list), dict)
        self.assertEqual(len(ups_list), 2)
        self.assertEqual(ups_list[self.valid], self.valid_ups_name)

    def test_get_ups_list_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.list_ups)

    def test_get_ups_vars_valid_ups(self):
        vars = self.client.list_vars(self.valid)
        self.assertEqual(type(vars), dict)
        self.assertEqual(len(vars), 2)
        self.assertEqual(vars["battery.charge"], "100")

    def test_get_ups_vars_invalid_ups(self):
        self.assertRaises(PyNUTError, self.client.list_vars, self.invalid)

    def test_get_ups_vars_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.list_vars, self.valid)

    def test_get_ups_commands_valid_ups(self):
        commands = self.client.list_commands(self.valid)
        self.assertEqual(type(commands), dict)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[self.valid], self.valid_command_desc)

    def test_get_ups_commands_invalid_ups(self):
        self.assertRaises(PyNUTError, self.client.list_commands, self.invalid)

    def test_get_ups_commands_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.list_commands, self.valid)

    def test_get_rw_vars_valid_ups(self):
        vars = self.client.list_rw_vars(self.valid)
        self.assertEqual(type(vars), dict)
        self.assertEqual(vars[self.valid], self.valid)

    def test_get_rw_vars_invalid_ups(self):
        self.assertRaises(PyNUTError, self.client.list_rw_vars, self.invalid)

    def test_set_rw_var_valid(self):
        try:
            self.client.set_var(self.valid, self.valid, self.valid)
        except PyNUTError:
            raise AssertionError()

    def test_set_rw_var_invalid(self):
        self.assertRaises(PyNUTError, self.client.set_var, self.invalid, self.invalid, self.invalid)

    def test_set_rw_var_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.set_var, self.valid, self.valid, self.valid)

    def test_run_ups_command_valid(self):
        try:
            self.client.run_command(self.valid, self.valid)
        except PyNUTError:
            raise AssertionError()

    def test_run_ups_command_invalid(self):
        self.assertRaises(PyNUTError, self.client.run_command, self.invalid, self.invalid)

    def test_run_ups_command_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.run_command, self.valid, self.valid)

    def test_fsd_valid_ups(self):
        try:
            self.client.fsd(self.valid)
        except PyNUTError:
            raise AssertionError()

    def test_fsd_invalid_ups(self):
        self.assertRaises(PyNUTError, self.client.fsd, self.invalid)

    def test_fsd_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.fsd, self.valid)

    def test_fsd_not_ok(self):
        self.assertRaises(PyNUTError, self.not_ok_client.fsd, self.valid)

    def test_help(self):
        self.assertEqual(
            self.client.help(), "Commands: HELP VER GET LIST SET INSTCMD LOGIN LOGOUT USERNAME PASSWORD STARTTLS\n"
        )

    def test_ver(self):
        self.assertEqual(self.client.ver(), "Network UPS Tools upsd 2.7.1 - http://www.networkupstools.org/\n")

    def test_list_clients_valid(self):
        clients = self.client.list_clients(self.valid)
        self.assertEqual(type(clients), dict)
        self.assertEqual(clients[self.valid], [self.valid])

    def test_list_clients_invalid(self):
        self.assertRaises(PyNUTError, self.client.list_clients, self.invalid)

    def test_list_clients_none(self):
        self.assertRaises(PyNUTError, self.client.list_clients)

    def test_list_clients_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.list_clients, self.valid)

    def test_num_logins(self):
        self.assertEqual(self.client.num_logins(self.valid), 1)

    def test_num_logins_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.num_logins, self.valid)

    def test_description(self):
        self.assertEqual(self.client.description(self.valid), self.valid_desc)

    def test_description_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.description, self.valid)

    def test_get(self):
        self.assertEqual(self.client.get(self.valid, self.valid), self.valid_value)

    def test_get_var_alias_for_get(self):
        self.assertEqual(self.client.get(self.valid, self.valid), self.client.get_var(self.valid, self.valid))

    def test_get_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.get, self.valid, self.valid)

    def test_var_description(self):
        self.assertEqual(self.client.var_description(self.valid, self.valid), self.valid_desc)

    def test_var_description_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.var_description, self.valid, self.valid)

    def test_command_description(self):
        self.assertEqual(self.client.command_description(self.valid, self.valid), self.valid_desc)

    def test_command_description_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.command_description, self.valid, self.valid)

    def test_list_enum(self):
        self.assertEqual(self.client.list_enum(self.valid, self.valid), [self.valid_desc])

    def test_list_enum_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.list_enum, self.valid, self.valid)

    def test_list_range(self):
        self.assertEqual(self.client.list_range(self.valid, self.valid), [self.valid_desc])

    def test_list_range_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.list_range, self.valid, self.valid)

    def test_var_type(self):
        self.assertEqual(self.client.var_type(self.valid, self.valid), "RW STRING:3")

    def test_var_type_broken(self):
        self.assertRaises(PyNUTError, self.broken_client.var_type, self.valid, self.valid)
