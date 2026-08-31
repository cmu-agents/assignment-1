import asyncio
import time
from pathlib import PurePath
from typing import Any

import modal
from swerex.deployment.modal import ModalDeployment
from swerex.runtime.abstract import Command
from swerex.runtime.remote import RemoteRuntime


def _tls_port_configuration(
    modal_sandbox_kwargs: dict[str, Any], runtime_port: int
) -> tuple[list[int], list[int], dict[str, Any]]:
    """Put the SWE-ReX control port on the TLS tunnel exactly once."""

    kwargs = dict(modal_sandbox_kwargs)
    encrypted = list(kwargs.pop("encrypted_ports", []))
    unencrypted = [
        port for port in kwargs.pop("unencrypted_ports", []) if port != runtime_port
    ]
    encrypted = list(dict.fromkeys([runtime_port, *encrypted]))
    return encrypted, unencrypted, kwargs


class AssignmentModalDeployment(ModalDeployment):
    """Modal deployment with a correctly matched TLS tunnel and URL.

    SWE-ReX 1.4.0 opens its control port as unencrypted TCP but initializes the
    HTTP client with ``Tunnel.url``, which is Modal's HTTPS endpoint. Keep the
    upstream runtime and authentication protocol, but expose that control port
    through ``encrypted_ports`` so its URL and transport agree.
    """

    async def start(self) -> None:
        if self._runtime is not None and self._sandbox is not None:
            self.logger.warning("Deployment is already started; ignoring duplicate start().")
            return

        self.logger.info("Starting Modal sandbox")
        self._hooks.on_custom_step("Starting Modal sandbox")
        started = time.monotonic()
        token = self._get_token()
        encrypted, unencrypted, extra_kwargs = _tls_port_configuration(
            self._modal_kwargs, self._port
        )
        try:
            self._sandbox = await modal.Sandbox.create.aio(
                "/usr/bin/env",
                "bash",
                "-c",
                self._start_swerex_cmd(token),
                image=self._image,
                timeout=int(self._deployment_timeout),
                encrypted_ports=encrypted,
                unencrypted_ports=unencrypted,
                app=self._app,
                **extra_kwargs,
            )
            tunnels = await self._sandbox.tunnels.aio()
            tunnel = tunnels[self._port]
            elapsed = time.monotonic() - started
            log_url = await self.get_modal_log_url()
            self.logger.info("Sandbox %s created in %.2fs", self._sandbox.object_id, elapsed)
            self.logger.info("Modal logs: %s", log_url)
            await asyncio.sleep(1)
            self.logger.info("Starting SWE-ReX runtime at %s", tunnel.url)
            self._hooks.on_custom_step("Starting runtime")
            self._runtime = RemoteRuntime(
                host=tunnel.url,
                timeout=self._runtime_timeout,
                auth_token=token,
                logger=self.logger,
            )
            remaining = max(0, self._startup_timeout - elapsed)
            await self._wait_until_alive(timeout=remaining)
        except Exception as exc:
            details = [f"{type(exc).__name__}: {exc}"]
            if self._sandbox is not None:
                details.append(f"sandbox_id={self._sandbox.object_id}")
                try:
                    details.append(f"logs={await self.get_modal_log_url()}")
                except Exception:
                    pass
                try:
                    await self._sandbox.terminate.aio()
                except Exception:
                    pass
            self._runtime = None
            self._sandbox = None
            raise RuntimeError(
                "Modal sandbox started, but the SWE-ReX control runtime did not "
                "become reachable. " + " | ".join(details)
            ) from exc

class Environment:
    """
    Executes bash commands in a Modal sandbox via SWE-ReX.
    """

    # NOTE(source): https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/extra/swerex_modal.py

    def __init__(
        self,
        image: "str | PurePath | modal.Image" = "python:3.12",
        cwd: str = "/",
        startup_timeout: float = 600,
        runtime_timeout: float = 600,
        deployment_timeout: float = 600,
        install_pipx: bool = True,
        modal_sandbox_kwargs: dict[str, Any] | None = None,
    ):
        """Launch a Modal sandbox and block until its runtime answers.

        Args:
            image: A prebuilt `modal.Image`, a Dockerhub or ECR image name, or a
                path to a Dockerfile. Build a task testbed with
                `assignment.utils.image.build_testbed_image`, which is the only
                way to pass a credential to a private clone.
            cwd: Working directory for commands that do not specify one.
            startup_timeout: Seconds to wait for the SWE-ReX runtime to come up.
            runtime_timeout: Seconds a single command may run before timing out.
            deployment_timeout: Seconds the sandbox may stay alive before Modal
                reclaims it.
            install_pipx: Install pipx in the image, needed to bootstrap the
                SWE-ReX server when it is not already present.
            modal_sandbox_kwargs: Additional keyword arguments forwarded to
                ``modal.Sandbox.create``. This is used for capabilities such as
                encrypted port forwarding.
        """
        self.cwd = cwd
        self.deployment = AssignmentModalDeployment(
            image=image,
            startup_timeout=startup_timeout,
            runtime_timeout=runtime_timeout,
            deployment_timeout=deployment_timeout,
            install_pipx=install_pipx,
            modal_sandbox_kwargs=modal_sandbox_kwargs,
        )

        async def _start():
            await self.deployment.start()
            await self.deployment.is_alive()

        asyncio.run(_start())

        # Read the platform from inside the container, not from platform.uname(),
        # which would describe the machine running this code instead.
        self.system, self.release, self.version, self.machine = self.execute(
            "uname -s; uname -r; uname -v; uname -m"
        )["output"].splitlines()

    def execute(
        self,
        command: str | list[str],
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        # Command defaults to shell=False, which requires `command` to be an argv
        # list; default to shell=True so a plain command string works.
        shell: bool | None = True,
        # check=False so a failing command returns its exit code instead of
        # raising and discarding the output the agent needs to see.
        check: bool = False,
    ) -> dict:
        """Run a command in the sandbox and return its result.

        Args:
            command: A shell string, or an argv list if `shell` is False.
            timeout: Seconds before the command is killed. None means no timeout.
            cwd: Working directory to run the command in. Defaults to the
                environment's `cwd`.
            env: Environment variables to set for the command.
            shell: Run the command through a shell, as with `subprocess.run`.
                None is treated as True, since a model calling this as a tool may
                send null for an omitted argument.
            check: Raise on a non-zero exit code instead of reporting it.

        Returns:
            A dict with `output`, `returncode`, and `exception_info`. `output`
            holds stdout and stderr interleaved, as they would appear in a
            terminal. `exception_info` is empty when the command ran, whatever
            its exit code. If the call itself fails (the sandbox died, the
            command timed out), the exception is caught rather than raised:
            `returncode` is -1, `exception_info` describes it, and an `extra` key
            carries the exception type.
        """
        # Command.shell is a strict bool, so None would fail validation.
        shell = True if shell is None else shell

        arguments = {
            "command": command,
            "timeout": timeout,
            "env": env,
            "shell": shell,
            "check": check,
            "merge_output_streams": False,
        }
        if cwd is not None:
            arguments["cwd"] = cwd
        # A cwd from the caller wins; otherwise the environment's default applies.
        arguments.setdefault("cwd", self.cwd)

        try:
            result = asyncio.run(self.deployment.runtime.execute(Command(**arguments)))
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                # The coding agent consumes one observation string, while the
                # task harness needs the streams separately for diagnostics.
                "output": result.stdout,
                "returncode": result.exit_code,
                "exception_info": "",
            }
            if result.stderr:
                output["output"] += result.stderr
        except Exception as e:
            # NOTE(source): https://github.com/SWE-agent/mini-swe-agent/blob/a83fcae82d2a08f0ee0c688f9d137b3566c097f8/src/minisweagent/environments/extra/swerex_modal.py#L82-L87
            # Same keys as the success path, so callers never have to branch on
            # which one they got.
            output = {
                "stdout": "",
                "stderr": str(e) if str(e) else "",
                "output": str(e) if str(e) else "",
                "returncode": -1,
                "exception_info": f"An error occurred while executing the command: {e}",
                "extra": {"exception_type": type(e).__name__, "exception": str(e)},
            }
        return output

    def stop(self, timeout: float = 10):
        """Shut down the runtime and terminate the sandbox.

        Args:
            timeout: Seconds allowed for each of the shutdown and the
                termination steps.
        """

        async def _stop():
            # ModalDeployment.stop() has an inverted poll() check and only
            # terminates sandboxes that have *already* exited, so a live sandbox
            # leaks until deployment_timeout. Terminate it explicitly. Grab the
            # reference first: stop() clears _sandbox.
            sandbox = self.deployment._sandbox
            try:
                await asyncio.wait_for(self.deployment.stop(), timeout=timeout)
            finally:
                if sandbox is not None:
                    await asyncio.wait_for(sandbox.terminate.aio(), timeout=timeout)

        asyncio.run(_stop())

    def tunnel_url(self, port: int) -> str:
        """Return the public URL for a port forwarded when the sandbox started."""

        async def _tunnel_url() -> str:
            tunnels = await self.deployment.sandbox.tunnels.aio()
            try:
                return tunnels[port].url
            except KeyError as exc:
                forwarded = ", ".join(str(item) for item in sorted(tunnels)) or "none"
                raise ValueError(
                    f"Port {port} was not forwarded. Available forwarded ports: {forwarded}."
                ) from exc

        return asyncio.run(_tunnel_url())

    def __enter__(self):
        """Enter a `with` block. The sandbox is already running by this point."""
        return self

    def __exit__(self, *exc):
        """Terminate the sandbox on leaving a `with` block, including on error."""
        self.stop()
