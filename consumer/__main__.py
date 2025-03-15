from consumer.answers import cli as answers_cli
from consumer.cli import app

app.add_typer(answers_cli)

if __name__ == "__main__":
    app()
