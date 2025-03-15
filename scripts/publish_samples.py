import argparse
import asyncio
from pathlib import Path

import logfire

from consumer.settings import Settings, configure_logfire, get_mqtt_client

PARENT_DIR = Path(__file__).parent


async def bulk_publish(
    settings: Settings,
    topic: str,
    payloads: list[str],
) -> None:
    async with get_mqtt_client(settings.mqtt) as client:
        logfire.info("Connected to {mqtt}", mqtt=settings.mqtt)

        for payload in payloads:
            try:
                input(f"About to publish {payload}. Continue? (^C to abort)")
            except KeyboardInterrupt:
                return
            await client.publish(topic, payload)
            logfire.info(
                "Published {payload!r} to {topic!r}",
                payload=payload,
                topic=topic,
            )


def get_sample_payloads(samples_file: Path) -> list[str]:
    return [
        payload
        for payload in map(str.strip, samples_file.read_text().splitlines())
        if payload and not payload.startswith("#")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("samples_file")
    parser.add_argument("topic")
    args = parser.parse_args()
    topic = args.topic
    payloads = get_sample_payloads(Path(args.samples_file))
    settings = Settings()
    configure_logfire()
    logfire.info("Read {n_payloads} samples to publish", n_payloads=len(payloads))
    asyncio.run(bulk_publish(settings, topic, payloads))


if __name__ == "__main__":
    main()
