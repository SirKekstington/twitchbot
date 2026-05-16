#!/usr/bin/env python3

import os
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key


@dataclass
class ExecCommand:
    script: str
    output: str
    args: dict[str, str]


@dataclass
class Command:
    name: str
    permission: str = "everyone"
    response: str | None = None
    exec_command: ExecCommand | None = None


class TwitchTokenManager:
    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
    VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"

    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        self.client_id = self._require("TWITCH_CLIENT_ID")
        self.client_secret = self._require("TWITCH_CLIENT_SECRET")
        self.access_token = self._require("TWITCH_ACCESS_TOKEN")
        self.refresh_token = self._require("TWITCH_REFRESH_TOKEN")

    @staticmethod
    def _require(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(f"{key} fehlt in .env")
        return value

    def get_irc_oauth(self) -> str:
        return f"oauth:{self.access_token}"

    def validate_token(self) -> bool:
        try:
            response = requests.get(
                self.VALIDATE_URL,
                headers={"Authorization": f"OAuth {self.access_token}"},
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def refresh(self) -> None:
        print("[AUTH] Refreshing token...")

        response = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=15,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Refresh failed: HTTP {response.status_code} - {response.text}"
            )

        payload = response.json()
        new_access_token = payload.get("access_token")
        new_refresh_token = payload.get("refresh_token")

        if not new_access_token:
            raise RuntimeError("Refresh response enthält keinen access_token")

        self.access_token = new_access_token

        if new_refresh_token:
            self.refresh_token = new_refresh_token

        set_key(self.env_path, "TWITCH_ACCESS_TOKEN", self.access_token)
        set_key(self.env_path, "TWITCH_REFRESH_TOKEN", self.refresh_token)

        print("[AUTH] Token refreshed and .env updated.")

    def ensure_valid(self) -> None:
        if not self.validate_token():
            self.refresh()


class XMLCommandLoader:
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.commands: dict[str, Command] = {}

    def load(self) -> None:
        if not Path(self.xml_path).exists():
            raise FileNotFoundError(f"Command XML nicht gefunden: {self.xml_path}")

        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        loaded: dict[str, Command] = {}

        for cmd_node in root.findall("command"):
            name = cmd_node.get("name")

            if not name:
                continue

            permission = cmd_node.get("permission", "everyone").lower()

            response = None
            response_node = cmd_node.find("response")

            if response_node is not None and response_node.text:
                response = response_node.text.strip()

            exec_command = None
            exec_node = cmd_node.find("exec")

            if exec_node is not None:
                script = exec_node.get("script")
                output = exec_node.get("output", "none").lower()

                if not script:
                    raise RuntimeError(f"Command '{name}' hat <exec>, aber kein script")

                exec_args: dict[str, str] = {}

                for arg_node in exec_node.findall("arg"):
                    arg_name = arg_node.get("name")
                    arg_value = arg_node.text or ""

                    if arg_name:
                        exec_args[arg_name] = arg_value.strip()

                exec_command = ExecCommand(
                    script=script,
                    output=output,
                    args=exec_args,
                )

            loaded[name.lower()] = Command(
                name=name.lower(),
                permission=permission,
                response=response,
                exec_command=exec_command,
            )

        self.commands = loaded
        print(f"[XML] Loaded {len(self.commands)} commands.")

    def get(self, name: str) -> Command | None:
        return self.commands.get(name.lower())


class TwitchBot:
    SERVER = "irc.chat.twitch.tv"
    PORT = 6667

    def __init__(
        self,
        username: str,
        channel: str,
        token_manager: TwitchTokenManager,
        command_loader: XMLCommandLoader,
        prefix: str = "!",
    ):
        self.username = username.lower()
        self.channel = channel.lower().lstrip("#")
        self.token_manager = token_manager
        self.command_loader = command_loader
        self.prefix = prefix
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        self.token_manager.ensure_valid()

        self.sock = socket.socket()
        self.sock.connect((self.SERVER, self.PORT))

        self._send_raw(f"PASS {self.token_manager.get_irc_oauth()}")
        self._send_raw(f"NICK {self.username}")

        # nötig für badges: moderator, vip, broadcaster
        self._send_raw("CAP REQ :twitch.tv/tags")

        self._send_raw(f"JOIN #{self.channel}")

        print(f"[IRC] Connected to #{self.channel} as {self.username}")

    def reconnect(self, refresh_token: bool = False) -> None:
        print("[IRC] Reconnecting...")

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        if refresh_token:
            self.token_manager.refresh()

        time.sleep(3)
        self.connect()

    def _send_raw(self, message: str) -> None:
        if not self.sock:
            raise RuntimeError("Socket not connected.")

        self.sock.send((message + "\r\n").encode("utf-8"))

    def send_chat(self, message: str) -> None:
        self._send_raw(f"PRIVMSG #{self.channel} :{message}")

    def run(self) -> None:
        self.connect()
        buffer = ""

        while True:
            try:
                data = self.sock.recv(4096).decode("utf-8", errors="ignore")

                if not data:
                    self.reconnect()
                    continue

                buffer += data

                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    self.handle_line(line)

            except KeyboardInterrupt:
                print("\n[EXIT] Bot stopped.")
                break

            except Exception as exc:
                print(f"[ERROR] {exc}")
                time.sleep(5)
                self.reconnect()

    def handle_line(self, line: str) -> None:
        print(f"[RAW] {line}")

        if line.startswith("PING"):
            self._send_raw("PONG :tmi.twitch.tv")
            return

        if "Login authentication failed" in line:
            print("[AUTH] Login failed. Trying token refresh.")
            self.reconnect(refresh_token=True)
            return

        parsed = self.parse_privmsg(line)

        if not parsed:
            return

        user, message, tags = parsed

        print(f"[CHAT] {user}: {message}")

        if message.startswith(self.prefix):
            self.handle_command(user, message, tags)

    @staticmethod
    def parse_privmsg(line: str) -> tuple[str, str, dict[str, str]] | None:
        if " PRIVMSG " not in line:
            return None

        try:
            tags: dict[str, str] = {}

            if line.startswith("@"):
                tags_part, rest = line.split(" ", 1)

                for item in tags_part[1:].split(";"):
                    if "=" in item:
                        key, value = item.split("=", 1)
                        tags[key] = value

                line = rest

            user = line.split("!", 1)[0].lstrip(":")
            message = line.split(" :", 1)[1]

            return user, message, tags

        except Exception:
            return None

    def handle_command(
        self,
        user: str,
        message: str,
        tags: dict[str, str],
    ) -> None:
        raw_after_prefix = message[len(self.prefix) :].strip()
        parts = raw_after_prefix.split(maxsplit=1)

        if not parts:
            return

        command_name = parts[0].lower()
        message_without_command = parts[1] if len(parts) > 1 else ""
        args = message_without_command.split() if message_without_command else []

        if command_name == "reload":
            self.command_loader.load()
            self.send_chat("Commands reloaded.")
            return

        command = self.command_loader.get(command_name)

        if not command:
            return

        if not self.has_permission(command.permission, tags):
            return

        context = {
            "user": user,
            "command": command_name,
            "message": message_without_command,
            "args": message_without_command,
        }

        for i, arg in enumerate(args, start=1):
            context[f"arg{i}"] = arg

        if command.response:
            response = self.render_template(command.response, context)
            if response:
                self.send_chat(response)

        if command.exec_command:
            exec_response = self.run_exec_command(command.exec_command, context)

            if command.exec_command.output == "chat" and exec_response:
                self.send_chat(exec_response)

    @staticmethod
    def has_permission(required: str, tags: dict[str, str]) -> bool:
        required = required.lower()

        if required in ("everyone", "follower"):
            return True

        badges_raw = tags.get("badges", "")
        badges = set()

        for badge in badges_raw.split(","):
            if "/" in badge:
                badge_name = badge.split("/", 1)[0]
                badges.add(badge_name)

        if required == "vip":
            return "vip" in badges or "moderator" in badges or "broadcaster" in badges

        if required == "mod":
            return "moderator" in badges or "broadcaster" in badges

        if required == "broadcaster":
            return "broadcaster" in badges

        return False

    @staticmethod
    def render_template(template: str, context: dict[str, str]) -> str:
        rendered = template

        for key, value in context.items():
            rendered = rendered.replace(f"{{{key}}}", value)

        return rendered

    def run_exec_command(
        self,
        exec_command: ExecCommand,
        context: dict[str, str],
    ) -> str:
        script_path = Path(exec_command.script)

        if not script_path.exists():
            return f"Script not found: {exec_command.script}"

        cmd = ["python", str(script_path)]

        for arg_name, arg_template in exec_command.args.items():
            arg_value = self.render_template(arg_template, context)
            cmd.extend([f"--{arg_name}", arg_value])

        print(f"[EXEC] {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            if result.returncode != 0:
                print(f"[EXEC ERROR] {result.stderr.strip()}")
                return "Command execution failed."

            stdout = result.stdout.strip()

            if stdout:
                print(f"[EXEC OUT] {stdout}")

            return stdout

        except subprocess.TimeoutExpired:
            return "Command timeout."

        except Exception as exc:
            print(f"[EXEC ERROR] {exc}")
            return "Command error."


def main() -> None:
    load_dotenv()

    username = os.getenv("TWITCH_BOT_USERNAME")
    channel = os.getenv("TWITCH_CHANNEL")
    prefix = os.getenv("COMMAND_PREFIX", "!")
    xml_path = os.getenv("COMMANDS_XML", "commands.xml")

    if not username:
        raise RuntimeError("TWITCH_BOT_USERNAME fehlt")

    if not channel:
        raise RuntimeError("TWITCH_CHANNEL fehlt")

    token_manager = TwitchTokenManager(".env")

    command_loader = XMLCommandLoader(xml_path)
    command_loader.load()

    bot = TwitchBot(
        username=username,
        channel=channel,
        token_manager=token_manager,
        command_loader=command_loader,
        prefix=prefix,
    )

    bot.run()


if __name__ == "__main__":
    main()
