
import json
from collections.abc import Iterator

import httpx


def iter_research_events(
    api_url: str,
    payload: dict,
) -> Iterator[tuple[str, dict]]:
    """Read actual SSE events from the FastAPI backend."""

    timeout = httpx.Timeout(300.0, connect=10.0)

    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            f"{api_url}/api/research/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()

            event_name = "message"
            data_lines = []

            for line in response.iter_lines():
                if line.startswith("event:"):
                    event_name = line[6:].strip()

                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())

                elif line == "":
                    if data_lines:
                        data = json.loads(
                            "\n".join(data_lines)
                        )
                        yield event_name, data

                    event_name = "message"
                    data_lines = []

            if data_lines:
                yield event_name, json.loads(
                    "\n".join(data_lines)
                )
