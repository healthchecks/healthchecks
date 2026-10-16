from __future__ import annotations

import os
from subprocess import call

from django.conf import settings

from hc.api.models import Flip, Notification
from hc.api.transports import Transport, TransportError
from hc.lib.string import replace


class Shell(Transport):
    def is_noop(self, status: str) -> bool:
        if status == "down" and not self.channel.shell.cmd_down:
            return True

        if status == "up" and not self.channel.shell.cmd_up:
            return True

        return False

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.SHELL_ENABLED:
            raise TransportError("Shell commands are not enabled")

        if flip.new_status == "up":
            cmd = self.channel.shell.cmd_up
        elif flip.new_status == "down":
            cmd = self.channel.shell.cmd_down

        check = flip.owner
        env = {
            "CODE": str(check.code),
            "STATUS": flip.new_status,
            "NOW": flip.created.replace(microsecond=0).isoformat(),
            "NAME": check.name,
            "TAGS": check.tags,
        }

        for i, tag in enumerate(check.tags_list()):
            env[f"TAG{i + 1}"] = tag

        code = call(cmd, env=env, shell=True)
        if code != 0:
            raise TransportError(f"Command returned exit code {code}")
