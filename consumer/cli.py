
import typer

from consumer.settings import configure_logfire

app = typer.Typer(name="mqtt-consumer", no_args_is_help=True)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand:
        configure_logfire()


if __name__ == "__main__":
    app()
