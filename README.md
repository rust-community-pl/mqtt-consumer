### Local MQTT server ([_mosquitto_](https://mosquitto.org/))

#### Configure the local MQTT user for the `mqtt` service

```bash
> docker compose run -it --rm mqtt sh
$ mosquitto_passwd -c /mosquitto/config/pwfile user
Password: foobar
Reenter password: foobar
$ exit
```

#### Set up MQTT credentials in the `.env` file

```bash
SUBSCRIBER_MQTT_HOSTNAME="127.0.0.1"
SUBSCRIBER_MQTT_PORT="1883"
SUBSCRIBER_MQTT_USERNAME="user"
SUBSCRIBER_MQTT_PASSWORD="foobar"
```

To use a custom `.env` file, set `SUBSCRIBER_ENV_FILE` to the desired path.

### Database

#### Upgrade to the latest version
```bash
alembic upgrade head
```

#### Generate migrations
```bash
alembic revision --autogenerate -m "What was changed?"
```

### Consumer

#### Consume and save answers

```bash
python -m consumer
```

#### Publish sample messages

```bash
for SAMPLE_FILE in scripts/samples-*.txt
do
    python -m scripts.publish-samples $SAMPLE_FILE
done
```

#### Prune saved answers

```bash
python -m consumer prune
```

### Tests

```bash
pytest
```

#### Accept docstring updates

```bash
pytest --accept
```
