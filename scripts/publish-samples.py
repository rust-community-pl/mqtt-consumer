import argparse
import asyncio
from pathlib import Path

import logfire

from consumer.main import ANSWER_TOPIC
from consumer.settings import Settings, get_mqtt_client

PARENT_DIR = Path(__file__).parent


async def bulk_publish(
    settings: Settings,
    topic: str,
    payloads: list[str],
) -> None:
    async with get_mqtt_client(settings.mqtt) as client:
        for payload in payloads:
            await client.publish(topic, payload)
            logfire.info(
                "Published {payload} to {topic}",
                payload=payload,
                topic=topic,
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("samples_file")
    args = parser.parse_args()

    payloads = list(filter(bool, Path(args.samples_file).read_text().splitlines()))
    logfire.info("Read {n_payloads} samples to publish", n_payloads=len(payloads))

    settings = Settings()
    logfire.configure(inspect_arguments=False)
    asyncio.run(bulk_publish(settings, ANSWER_TOPIC, payloads))


if __name__ == "__main__":
    main()
