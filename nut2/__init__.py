# -*- coding: utf-8 -*-

"""A Python module for dealing with NUT (Network UPS Tools) servers.

* PyNUTError: Base class for custom exceptions.
* PyNUTClient: Allows connecting to and communicating with PyNUT
  servers.

Copyright (C) 2019 Ryan Shipp

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import asyncio
import logging

import telnetlib3

__all__ = ["PyNUTError", "PyNUTClient"]

# logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")


class PyNUTError(Exception):
    """Base class for custom exceptions."""


class PyNUTClient:
    """Sync wrapper for NUT client using telnetlib3."""

    def __init__(
        self,
        host="127.0.0.1",
        port=3493,
        login=None,
        password=None,
        debug=False,
        timeout=5,
        connect=True,
        connect_minwait=1.0,
        connect_maxwait=3.0,
    ):
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

        logging.debug("Class initialization...")
        logging.debug(" -> Host = %s (port %s)", host, port)
        logging.debug(" -> Login = '%s' / '%s'", login, password)

        self._loop = None
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._host = host
        self._port = port
        self._login = login
        self._password = password
        self._timeout = timeout
        self._connect_minwait = connect_minwait
        self._connect_maxwait = connect_maxwait
        self._reader = None
        self._writer = None

        if connect:
            self.connect()

    def connect(self):
        self._loop.run_until_complete(self.async_connect())

    async def async_connect(self):
        logging.debug("Connecting to host")
        try:
            self._reader, self._writer = await telnetlib3.open_connection(
                host=self._host,
                port=self._port,
                connect_minwait=self._connect_minwait,
                connect_maxwait=self._connect_maxwait,
            )
            logging.debug("Connected to %s:%s", self._host, self._port)

            if self._login:
                await self._async_send_and_receive(f"USERNAME {self._login}")

            if self._password:
                await self._async_send_and_receive(f"PASSWORD {self._password}")

        except Exception as e:
            raise PyNUTError(f"Connection failed: {e}")

    def _send_and_receive(self, command, expect="\n", timeout=None):
        return self._loop.run_until_complete(self._async_send_and_receive(command, expect, timeout))

    def _read_until(self, expect="\n", timeout=None):
        return self._loop.run_until_complete(self._async_read_until(expect, timeout))

    async def _async_read_until(self, expect, timeout=None):
        if isinstance(expect, str):
            expect = expect.encode()
        try:
            r = await asyncio.wait_for(self._reader.readuntil(expect), timeout or self._timeout)
            if isinstance(r, bytes):
                r = r.decode("utf-8")
            return r
        except asyncio.TimeoutError:
            raise PyNUTError(f"Timeout waiting for response to: {expect.decode().strip()}")

    async def _async_send(self, command):
        logging.debug(f"Sending command: {command}")
        self._writer.write(command + "\n")

    async def _async_send_and_receive(self, command, expect="\n", timeout=None):
        await self._async_send(command)
        return await self._async_read_until(expect, timeout)

    def description(self, ups):
        return self._loop.run_until_complete(asyncio.wait_for(self.async_description(ups), timeout=self._timeout))

    async def async_description(self, ups):
        response = await self._async_send_and_receive(f"GET UPSDESC {ups}")
        try:
            return response.split('"')[1].strip()
        except IndexError:
            raise PyNUTError(response.strip())

    def list_ups(self):
        """Returns the list of available UPS from the NUT server.

        The result is a dictionary containing 'key->val' pairs of
        'UPSName' and 'UPS Description'.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_ups(), timeout=self._timeout))

    async def async_list_ups(self):
        start = await self._async_send_and_receive("LIST UPS")
        if start.strip() != "BEGIN LIST UPS":
            raise PyNUTError(start.strip())

        response = await self._async_read_until("END LIST UPS\n")
        ups_dict = {}
        for line in response.split("\n"):
            if line.startswith("UPS"):
                ups, desc = line[len("UPS ") :].split('"')[:2]
                ups_dict[ups.strip()] = desc.strip()
        return ups_dict

    def get(self, ups, var):
        """Get the value of a variable (alias for get_var)."""
        return self.get_var(ups, var)

    def logout(self):
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self._async_send_and_receive("LOGOUT"), timeout=self._timeout)
            )
        except Exception:
            pass
        if self._writer:
            self._writer.close()

    def __del__(self):
        self.logout()

    def __enter__(self):
        return self

    def __exit__(self, exc_t, exc_v, trace):
        self.logout()

    def list_vars(self, ups):
        """Get all available vars from the specified UPS.

        The result is a dictionary containing 'key->val' pairs of all available vars.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_vars(ups), timeout=self._timeout))

    async def async_list_vars(self, ups):
        await self._async_send(f"LIST VAR {ups}")
        vars_dict = {}
        while True:
            line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
            line = line.decode().strip()
            if line.startswith("BEGIN LIST VAR"):
                continue
            if line.startswith(f"END LIST VAR {ups}"):
                break
            if line.startswith("VAR "):
                try:
                    # VAR <ups> <var> "<value>"
                    _, rest = line.split(" ", 1)
                    parts = rest.split('"')
                    key_part = parts[0].strip()
                    value = parts[1]
                    # key_part is "<ups> <var>", so get var name (skip ups)
                    key_fields = key_part.split(" ", 1)
                    if len(key_fields) == 2:
                        varname = key_fields[1]
                    else:
                        varname = key_part
                    vars_dict[varname] = value
                except Exception as e:
                    raise PyNUTError(f"Invalid VAR line: {line}") from e
        return vars_dict

    def list_commands(self, ups):
        """Get all available commands for the specified UPS.

        The result is a dict object with command name as key and a description
        of the command as value.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_commands(ups), timeout=self._timeout))

    async def async_list_commands(self, ups):
        logging.debug("list_commands called...")

        await self._async_send(f"LIST CMD {ups}")
        cmd_names = []

        while True:
            line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
            line = line.decode("utf-8").strip()

            if line == f"BEGIN LIST CMD {ups}":
                continue
            if line == f"END LIST CMD {ups}":
                break
            if line.startswith("CMD "):
                try:
                    _, rest = line.split(" ", 1)
                    name = rest.strip().split()[1]
                    cmd_names.append(name)
                except Exception as e:
                    raise PyNUTError(f"Invalid CMD line: {line}") from e

        commands = {}
        for name in cmd_names:
            desc_response = await self._async_send_and_receive(f"GET CMDDESC {ups} {name}")
            if desc_response.startswith("CMDDESC"):
                parts = desc_response.split('"')
                if len(parts) > 1:
                    desc = parts[1].strip()
                else:
                    desc = name
            else:
                desc = name
            commands[name] = desc

        return commands

    def list_clients(self, ups=None):
        """
        Returns the list of connected clients from the NUT server.
        The result is a dictionary containing 'UPSName' → list of client names.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_clients(ups), timeout=self._timeout))

    async def async_list_clients(self, ups=None):
        if ups:
            ups_list = await self.async_list_ups()
            if ups not in ups_list:
                raise PyNUTError(f"{ups} is not a valid UPS")
            await self._async_send(f"LIST CLIENTS {ups}")
        else:
            await self._async_send("LIST CLIENTS")

        # Expecting BEGIN
        line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        if line.decode().strip() != "BEGIN LIST CLIENTS":
            raise PyNUTError(f"Unexpected response: {line.decode().strip()}")

        # Read until END
        buffer = ""
        while True:
            line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
            decoded = line.decode()
            buffer += decoded
            if decoded.startswith("END LIST CLIENTS"):
                break

        # Parse CLIENT lines
        clients = {}
        for line in buffer.splitlines():
            if line.startswith("CLIENT "):
                parts = line[len("CLIENT ") :].split(" ", 1)
                if len(parts) == 2:
                    host, upsname = parts
                    clients.setdefault(upsname, []).append(host)
        return clients

    def list_rw_vars(self, ups):
        """Get a list of all writable vars from the selected UPS.

        The result is presented as a dictionary containing 'key -> value' pairs.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_rw_vars(ups), timeout=self._timeout))

    async def async_list_rw_vars(self, ups):
        await self._async_send(f"LIST RW {ups}")
        rw_vars = {}
        while True:
            line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
            line = line.decode().strip()

            if line.startswith("BEGIN LIST RW"):
                continue
            if line.startswith(f"END LIST RW {ups}"):
                break
            if line.startswith("RW "):
                try:
                    _, rest = line.split(" ", 1)
                    parts = rest.split('"')
                    key = parts[0].strip().split(" ", 1)[1]
                    value = parts[1]
                    rw_vars[key] = value
                except Exception as e:
                    raise PyNUTError(f"Invalid RW line: {line}") from e
        return rw_vars

    def list_enum(self, ups, var):
        """Get a list of valid values for an enum variable.

        The result is presented as a list.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_enum(ups, var), timeout=self._timeout))

    async def async_list_enum(self, ups, var):
        await self._async_send(f"LIST ENUM {ups} {var}")
        enum_list = []

        while True:
            line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
            line = line.decode().strip()

            if line.startswith(f"BEGIN LIST ENUM {ups} {var}"):
                continue
            if line.startswith(f"END LIST ENUM {ups} {var}"):
                break
            if line.startswith("ENUM "):
                try:
                    parts = line.split(" ", 3)
                    if len(parts) == 4:
                        enum_value = parts[3].strip().strip('"')
                        enum_list.append(enum_value)
                except Exception as e:
                    raise PyNUTError(f"Invalid ENUM line: {line}") from e

        return enum_list

    def list_range(self, ups, var):
        """Get a list of valid values for a range variable.

        The result is presented as a list of strings.
        """
        return self._loop.run_until_complete(asyncio.wait_for(self.async_list_range(ups, var), timeout=self._timeout))

    async def async_list_range(self, ups, var):
        logging.debug("list_range called...")

        await self._async_send(f"LIST RANGE {ups} {var}")

        # Wait for BEGIN line
        begin_line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        begin_line = begin_line.decode("utf-8")
        expected_begin = f"BEGIN LIST RANGE {ups} {var}\n"
        if begin_line != expected_begin:
            raise PyNUTError(begin_line.strip())

        # Read until END
        end_marker = f"END LIST RANGE {ups} {var}\n"
        lines = []
        while True:
            line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
            line = line.decode("utf-8")
            if line == end_marker:
                break
            lines.append(line.strip())

        offset = len(f"RANGE {ups} {var}")
        try:
            return [c[offset:].split('"')[1].strip() for c in lines]
        except IndexError:
            raise PyNUTError("\n".join(lines))

    def set_var(self, ups, var, value):
        return self._loop.run_until_complete(
            asyncio.wait_for(self.async_set_var(ups, var, value), timeout=self._timeout)
        )

    async def async_set_var(self, ups, var, value):
        response = await self._async_send_and_receive(f"SET VAR {ups} {var} {value}")
        if response.strip() != "OK":
            raise PyNUTError(response.strip())

    def get_var(self, ups, var):
        return self._loop.run_until_complete(asyncio.wait_for(self.async_get_var(ups, var), timeout=self._timeout))

    async def async_get_var(self, ups, var):
        response = await self._async_send_and_receive(f"GET VAR {ups} {var}")
        try:
            return response.split('"')[1].strip()
        except IndexError:
            raise PyNUTError(response.strip())

    def var_description(self, ups, var):
        """Get a variable's description."""
        return self._loop.run_until_complete(
            asyncio.wait_for(self.async_var_description(ups, var), timeout=self._timeout)
        )

    async def async_var_description(self, ups, var):
        await self._async_send(f"GET DESC {ups} {var}")
        line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        line = line.decode().strip()

        if line.startswith("DESC "):
            try:
                return line.split('"', 1)[1].rstrip('"')
            except IndexError:
                raise PyNUTError(f"Invalid DESC line: {line}")
        raise PyNUTError(line)

    def var_type(self, ups, var):
        """Get a variable's type."""
        return self._loop.run_until_complete(asyncio.wait_for(self.async_var_type(ups, var), timeout=self._timeout))

    async def async_var_type(self, ups, var):
        await self._async_send(f"GET TYPE {ups} {var}")
        line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        line = line.decode().strip()

        # result = 'TYPE %s %s %s\n' % (ups, var, type)
        if line.startswith("TYPE "):
            try:
                return line.split(" ", 3)[3].strip()
            except IndexError:
                raise PyNUTError(f"Invalid TYPE line: {line}")
        raise PyNUTError(line)

    def command_description(self, ups, command):
        """Get a command's description from the NUT server."""
        return self._loop.run_until_complete(
            asyncio.wait_for(self.async_command_description(ups, command), timeout=self._timeout)
        )

    async def async_command_description(self, ups, command):
        logging.debug("command_description called for '%s' / '%s'", ups, command)
        response = await self._async_send_and_receive(f"GET CMDDESC {ups} {command}")
        try:
            # Expected format: CMDDESC <ups> <command> "<description>"
            return response.split('"')[1].strip()
        except IndexError:
            raise PyNUTError(f"Unexpected response: {response.strip()}")

    def run_command(self, ups, command):
        """Send a command to the specified UPS."""
        logging.debug("run_command called for '%s' / '%s'", ups, command)
        return self._loop.run_until_complete(
            asyncio.wait_for(self.async_run_command(ups, command), timeout=self._timeout)
        )

    async def async_run_command(self, ups, command):
        await self._async_send(f"INSTCMD {ups} {command}")
        line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        line = line.decode().strip()
        if line != "OK":
            raise PyNUTError(line)

    def fsd(self, ups):
        """Send MASTER and FSD commands."""
        return self._loop.run_until_complete(asyncio.wait_for(self.async_fsd(ups), timeout=self._timeout))

    async def async_fsd(self, ups):
        logging.debug("MASTER called...")
        await self._async_send(f"MASTER {ups}")
        result = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        if result.decode().strip() != "OK MASTER-GRANTED":
            raise PyNUTError(("Master level function are not available", ""))

        logging.debug("FSD called...")
        await self._async_send(f"FSD {ups}")
        result = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        if result.decode().strip() != "OK FSD-SET":
            raise PyNUTError(result.decode().strip())

    def num_logins(self, ups):
        return self._loop.run_until_complete(asyncio.wait_for(self.async_num_logins(ups), timeout=self._timeout))

    async def async_num_logins(self, ups):
        await self._async_send(f"GET NUMLOGINS {ups}")
        line = await asyncio.wait_for(self._reader.readuntil(b"\n"), timeout=self._timeout)
        line = line.decode().strip()

        # Expected format: NUMLOGINS <ups> <number>
        if line.startswith("NUMLOGINS"):
            try:
                return int(line.split()[2])
            except (IndexError, ValueError):
                raise PyNUTError(f"Invalid NUMLOGINS line: {line}")
        raise PyNUTError(line)

    def help(self):
        return self._loop.run_until_complete(asyncio.wait_for(self.async_help(), timeout=self._timeout))

    async def async_help(self):
        return await self._async_send_and_receive("HELP")

    def ver(self):
        return self._loop.run_until_complete(asyncio.wait_for(self.async_ver(), timeout=self._timeout))

    async def async_ver(self):
        return await self._async_send_and_receive("VER")
