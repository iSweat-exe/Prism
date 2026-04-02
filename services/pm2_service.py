import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PrismAPI")


class PM2Service:
    @staticmethod
    async def _run_command(args: List[str]) -> Optional[str]:
        """Executes a PM2 command and returns the stdout."""
        try:
            process = await asyncio.create_subprocess_exec(
                "pm2", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"PM2 command failed: {' '.join(args)} - Error: {stderr.decode().strip()}")
                return None

            return stdout.decode().strip()
        except Exception as e:
            logger.error(f"Failed to execute PM2 command: {str(e)}")
            return None

    async def list_processes(self) -> Optional[List[Dict[str, Any]]]:
        """Returns the list of all PM2 processes (jlist)."""
        output = await self._run_command(["jlist"])
        if output is None:
            return None

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            logger.error("Failed to parse PM2 jlist output")
            return None

    async def process_action(self, id_or_name: str, action: str) -> bool:
        """Executes a lifecycle action (start, stop, restart, reload, delete)."""
        output = await self._run_command([action, id_or_name])
        return output is not None

    async def save_config(self) -> bool:
        """Saves current PM2 process list."""
        output = await self._run_command(["save"])
        return output is not None

    async def get_logs(self, id_or_name: str, lines: int = 100) -> List[Dict[str, Any]]:
        """Fetches the last N lines of logs in JSON format."""
        output = await self._run_command(["logs", id_or_name, "--lines", str(lines), "--json", "--noprefix"])
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse PM2 logs JSON output for {id_or_name}")
        return []

    async def log_streamer(self, id_or_name: str):
        """Generator to stream real-time logs using SSE."""
        cmd = ["pm2", "logs", id_or_name, "--raw", "--noprefix"]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                # yield as SSE format
                log_line = line.decode().strip()
                if log_line:
                    yield f"data: {json.dumps({'line': log_line})}\n\n"

        except Exception as e:
            logger.error(f"Error streaming logs for {id_or_name}: {str(e)}")
            yield f"data: {json.dumps({'error': 'stream_interrupted', 'message': 'The log stream was interrupted'})}\n\n"
        finally:
            if process.returncode is None:
                process.terminate()
                await process.wait()


pm2_service = PM2Service()
