from typing import Annotated

import aiomqtt
import logfire
from pydantic import AfterValidator

type StrippedStr = Annotated[str, AfterValidator(str.strip)]


def should_skip(
    message: aiomqtt.Message,
    expected_topic: str,
    *,
    side_effect_log: bool = True,
) -> bool:
    if not message.topic.matches(expected_topic):
        if side_effect_log:
            logfire.info(
                "Skipping payload {payload} from irrelevant topic "
                "{topic!r} (only watching {watching_topic!r})",
                payload=get_message_payload(message),
                topic=message.topic.value,
                watching_topic=expected_topic,
            )
        return True
    return False


def get_message_payload(message: aiomqtt.Message) -> str:
    # `.payload` attribute values in the received messages are always `bytes`
    # TODO(#1): Report `aiomqtt.types.PayloadType` is incorrectly used upstream
    assert isinstance(message.payload, bytes)
    return message.payload.decode()
