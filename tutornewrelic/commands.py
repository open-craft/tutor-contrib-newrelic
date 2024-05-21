import click
from tutor import config
from tutor.commands.k8s import K8sContext

from .newrelic import NewRelicClient


@click.group(help="Commands for registering NewRelic alerts.")
@click.pass_context
def newrelic(context: click.Context) -> None:
    """
    NewRelic command group.
    """

    context.obj = K8sContext(context.obj.root)


@newrelic.command(help="Register NewRelic monitoring resources")
@click.pass_obj
def create_alert_workflow(context: click.Context) -> None:
    """
    Create the necessary resources on NewRelic for the instance.
    """

    loaded_config = config.load(context.root)  # type: ignore
    instance_name = str(loaded_config["NEWRELIC_NAME"])

    client = NewRelicClient(
        api_key=str(loaded_config["NEWRELIC_API_KEY"]),
        account_id=int(loaded_config["NEWRELIC_ACCOUNT_ID"]),  # type: ignore
        region=str(loaded_config["NEWRELIC_REGION_CODE"]),
    )

    click.echo(f"Setting up NewRelic monitoring for {instance_name}")

    policy_name = f"{instance_name.title()} - Open edX Instance"
    if (policy := client.get_alert_policy(name=policy_name)) is None:
        policy = client.create_alert_policy(name=policy_name)

    for monitor_config in loaded_config["NEWRELIC_SYNTHETICS_MONITORS"]:  # type: ignore
        dst_name = f"Default notification channel for {instance_name}"
        if (destination := client.get_notification_destination(dst_name)) is None:
            destination = client.create_notification_destination(
                name=f"Default notification channel for {instance_name}",
                recipient=monitor_config["recipient"],  # type: ignore
            )

        channel_name = f"Default notification channel for {instance_name}"
        if (channel := client.get_notification_channel(channel_name)) is None:
            channel = client.create_notificaiton_channel(
                name=f"Default notification channel for {instance_name}",
                destination_id=destination.id,
            )

        if (workflow := client.get_ai_workflow(instance_name)) is None:
            workflow = client.create_ai_workflow(
                instance_name=instance_name,
                policy_id=policy.id,
                channel_id=channel.id,
            )

        for url in monitor_config["urls"]:  # type: ignore
            if (monitor := client.get_synthetics_monitor(name=url)) is None:
                monitor = client.create_synthetics_monitor(
                    name=url,
                    uri=url,
                    period=loaded_config["NEWRELIC_MONITORING_PERIOD"],  # type: ignore
                    locations=[loaded_config["NEWRELIC_MONITORING_LOCATION"]],  # type: ignore
                )

            if client.get_alert_condition(monitor_name=monitor.name) is None:
                client.create_alert_condition(
                    monitor_name=monitor.name, uri=url, policy_id=policy.id
                )

    click.echo(f"NewRelic monitoring is set up for {instance_name}")
