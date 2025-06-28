import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import requests
from pydantic import BaseModel


class NerdGraphAPIError(BaseException):
    """
    Exception returned if the NerdGraph API call fails.
    """


class Response(BaseModel):
    """
    Base response type for NewRelic NerdGraph responses.
    """

    id: str
    name: str


class SyntheticsMonitorResponse(Response):
    """
    Response type of a NewRelic synthetics monitor.
    """

    uri: str


class NewRelicClient:
    """
    NewRelic NerdGraph API client for managing resources.

    The API client manages the alert policies, synthetics monitors, alert
    destinations and more for an Open edX instance.
    """

    def __init__(self, api_key: str, account_id: int, region: str) -> None:
        self.__account_id = account_id

        api_region = ".eu" if region.lower() == "eu" else ""
        self.__api_base_url = f"https://api{api_region}.newrelic.com/graphql"
        self.__api_key = api_key

    def __send_request(
        self, query: str, variables: Optional[Dict[Any, Any]] = None
    ) -> Dict[Any, Any]:
        """
        Send a GraphQL request to the API endpoint.

        If the request fails or returns a non-200 request, an exception is raised.
        """

        if variables is None:
            variables = dict()

        response = requests.post(
            self.__api_base_url,
            headers={"API-Key": self.__api_key},
            json={
                "query": query,
                "variables": variables,
            },
        )

        if response.status_code != 200:
            raise NerdGraphAPIError(response.text)

        response = json.loads(response.content)

        if response.get("errors"):  # type: ignore
            raise NerdGraphAPIError(response)

        return response["data"]  # type: ignore

    def get_alert_policy(self, name: str) -> Optional[Response]:
        """
        Get policy by its name.
        """

        query = """
        query($accountId: Int!, $name: String!) {
          actor {
            account(id: $accountId) {
              alerts {
                policiesSearch(searchCriteria: { nameLike: $name }) {
                  policies {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """

        variables = {"accountId": self.__account_id, "name": name}

        response = self.__send_request(query, variables)
        alerts = response["actor"]["account"]["alerts"]
        policies = alerts["policiesSearch"]["policies"]

        for policy in policies:
            if policy["name"] == name:
                return Response(id=policy["id"], name=policy["name"])

        return None

    def create_alert_policy(self, name: str) -> Response:
        """
        Create a new alert policy with a given name for the configured account.

        If the alert policy exists by name, the policy will not be created.
        """

        query = """
        mutation($accountId: Int!, $name: String!) {
            alertsPolicyCreate(
                accountId: $accountId
                policy: { name: $name, incidentPreference: PER_CONDITION }
            ) {
                id
                name
            }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": name,
        }

        response = self.__send_request(query, variables)
        response = response["alertsPolicyCreate"]

        return Response(id=response["id"], name=response["name"])

    def get_synthetics_monitor(self, name: str) -> Optional[Response]:
        """
        Get synthetics monitor by its name.
        """

        query = """
        query ($query: String!) {
          actor {
            entitySearch(query: $query) {
              results {
                entities {
                  guid
                  name
                }
              }
            }
          }
        }"""

        variables = {
            "query": f"domain = 'SYNTH' AND type = 'MONITOR' AND name = '{name}'"
        }

        response = self.__send_request(query, variables)
        entities = response["actor"]["entitySearch"]["results"]["entities"]

        for entity in entities:
            if entity["name"] == name:
                return Response(id=entity["guid"], name=entity["name"])

        return None

    def create_synthetics_monitor(
        self, name: str, uri: str, period: str, locations: List[str]
    ) -> SyntheticsMonitorResponse:
        """
        Create synthetics monitor for the given URI.
        """

        query = """
        mutation($accountId: Int!, $monitor: SyntheticsCreateSimpleMonitorInput!) {
          syntheticsCreateSimpleMonitor(accountId: $accountId, monitor: $monitor) {
            monitor {
              id
              name
            }
            errors {
              description
              type
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "monitor": {
                "name": name,
                "period": period,
                "uri": uri,
                "status": "ENABLED",
                "locations": {"public": locations},
            },
        }

        response = self.__send_request(query, variables)

        if response.get("errors"):
            raise NerdGraphAPIError(f"Unexpected NerdGraph error: {response}")

        response = response["syntheticsCreateSimpleMonitor"]

        return SyntheticsMonitorResponse(
            id=response["monitor"]["id"], name=response["monitor"]["name"], uri=uri
        )

    def get_alert_condition(self, monitor_name: str) -> Optional[Response]:
        """
        Get alert condition by its name.
        """

        condition_name = f"Lost signal for {monitor_name}"

        query = """
        query($accountId: Int!, $name: String!) {
          actor {
            account(id: $accountId) {
              alerts {
                nrqlConditionsSearch(searchCriteria: { name: $name }) {
                  nrqlConditions {
                    id
                    name
                  }
                }
              }
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": condition_name,
        }

        response = self.__send_request(query, variables)
        alerts = response["actor"]["account"]["alerts"]
        conditions = alerts["nrqlConditionsSearch"]["nrqlConditions"]

        for condition in conditions:
            if condition["name"] == condition_name:
                return Response(id=condition["id"], name=condition["name"])

        return None

    def create_alert_condition(
        self, monitor_name: str, uri: str, policy_id: str
    ) -> Response:
        """
        Create static NRQL alert condition for the given policy and monitor.
        """

        query = """
        mutation($accountId: Int!, $policyId: ID!, $condition: AlertsNrqlConditionStaticInput!) {
            alertsNrqlConditionStaticCreate(
                accountId: $accountId,
                policyId: $policyId,
                condition: $condition,
            ) {
                id
                name
            }
        }"""

        variables = {
            "accountId": self.__account_id,
            "policyId": policy_id,
            "condition": {
                "name": f"Lost signal for {monitor_name}",
                "enabled": True,
                "description": f"Alert when {monitor_name} is not responding",
                "valueFunction": "SUM",
                "violationTimeLimitSeconds": 86400,
                "nrql": {
                    "query": f"SELECT count(*) FROM SyntheticCheck WHERE monitorName = '{monitor_name}' AND result = 'FAILED'",
                },
                "signal": {
                    "aggregationWindow": 60,
                    "aggregationMethod": "EVENT_FLOW",
                    "aggregationDelay": 120,
                    "fillOption": "STATIC",
                    "fillValue": 0,
                },
                "terms": [
                    {
                        "threshold": 1,
                        "thresholdOccurrences": "AT_LEAST_ONCE",
                        "thresholdDuration": 360,
                        "operator": "ABOVE",
                        "priority": "WARNING",
                    },
                    {
                        "threshold": 2,
                        "thresholdOccurrences": "AT_LEAST_ONCE",
                        "thresholdDuration": 660,
                        "operator": "ABOVE",
                        "priority": "CRITICAL",
                    },
                ],
                "expiration": {
                    "expirationDuration": 660,
                    "openViolationOnExpiration": False,
                    "closeViolationsOnExpiration": True,
                },
            },
        }

        response = self.__send_request(query, variables)
        response = response["alertsNrqlConditionStaticCreate"]

        return Response(id=response["id"], name=response["name"])

    def get_notification_destination(self, name: str) -> Optional[Response]:
        """
        Get notification destination by its name.
        """

        query = """
        query($accountId: Int!, $name: String!) {
          actor {
            account(id: $accountId) {
              aiNotifications {
                destinations(filters: { name: $name }) {
                  entities {
                    id
                    name
                  }
                }
              }
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": name,
        }

        response = self.__send_request(query, variables)
        destinations = response["actor"]["account"]["aiNotifications"]["destinations"]
        entities = destinations["entities"]

        for entity in entities:
            if entity["name"] == name:
                return Response(id=entity["id"], name=entity["name"])

        return None

    def create_notification_destination(self, name: str, recipient: str) -> Response:
        """
        Create a notification channel to notifiy if the instance is down.
        """

        query = """
        mutation($accountId: Int!, $name: String!, $recipient: String!) {
          aiNotificationsCreateDestination(
            accountId: $accountId,
            destination: {
              name: $name,
              type: EMAIL,
              properties: {
                key: "email",
                value: $recipient
              }
            }
          ) {
            destination {
              id
              name
            }
            error {
              __typename
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": name,
            "recipient": recipient,
        }

        response = self.__send_request(query, variables)

        if response.get("error"):
            raise NerdGraphAPIError(f"Unexpected NerdGraph error: {response}")

        response = response["aiNotificationsCreateDestination"]

        return Response(
            id=response["destination"]["id"],
            name=response["destination"]["name"],
        )

    def get_notification_channel(self, name: str) -> Optional[Response]:
        """
        Get notification channel by its name.
        """

        query = """
        query($accountId: Int!, $name: String!) {
          actor {
            account(id: $accountId) {
              aiNotifications {
                channels(filters: { name: $name }) {
                  entities {
                    id
                    name
                  }
                }
              }
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": name,
        }

        response = self.__send_request(query, variables)
        channels = response["actor"]["account"]["aiNotifications"]["channels"]
        entities = channels["entities"]

        for entity in entities:
            if entity["name"] == name:
                return Response(id=entity["id"], name=entity["name"])

        return None

    def create_notificaiton_channel(self, name: str, destination_id: str) -> Response:
        """
        Create notification channel for the instance alerts.
        """

        query = """
        mutation($accountId: Int!, $name: String!, $destinationId: ID!) {
          aiNotificationsCreateChannel(
            accountId: $accountId,
            channel: {
              type: EMAIL
              name: $name
              destinationId: $destinationId
              product: IINT
              properties: []
            }
          ) {
            channel {
              id
              name
            }
            error {
              __typename
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": name,
            "destinationId": destination_id,
        }

        response = self.__send_request(query, variables)

        if response.get("error"):
            raise NerdGraphAPIError(f"Unexpected NerdGraph error: {response}")

        response = response["aiNotificationsCreateChannel"]

        return Response(id=response["channel"]["id"], name=response["channel"]["name"])

    def get_ai_workflow(self, instance_name: str) -> Optional[Response]:
        """
        Get applied intelligence workflow by its name.
        """

        workflow_name = f"Alert intelligence workflow of {instance_name} instance"

        query = """
        query($accountId: Int!, $name: String!) {
          actor {
            account(id: $accountId) {
              aiWorkflows {
                workflows(filters: { name: $name }) {
                  entities {
                    id
                    name
                  }
                }
              }
            }
          }
        }"""

        variables = {
            "accountId": self.__account_id,
            "name": workflow_name,
        }

        response = self.__send_request(query, variables)
        workflows = response["actor"]["account"]["aiWorkflows"]["workflows"]
        entities = workflows["entities"]

        for entity in entities:
            if entity["name"] == workflow_name:
                return Response(id=entity["id"], name=entity["name"])

        return None

    def create_ai_workflow(
        self, instance_name: str, policy_id: str, channel_id: str
    ) -> Response:
        """
        Create an applied intelligence workflow and alert destination.
        """

        query = """
        mutation($accountId: Int!, $name: String!, $filterName: String!, $policyIds:[String!]!, $channelId: ID!) {
          aiWorkflowsCreateWorkflow(
            accountId: $accountId,
            createWorkflowData: {
              name: $name,
              workflowEnabled: true,
              destinationsEnabled: true,
              mutingRulesHandling: NOTIFY_ALL_ISSUES,
              issuesFilter: {
                name: $filterName,
                type: FILTER,
                predicates: [
                  {
                    attribute: "labels.policyIds",
                    operator: EXACTLY_MATCHES,
                    values: $policyIds,
                  }
                ]
              }
              destinationConfigurations: {
                channelId: $channelId,
                notificationTriggers: [ACTIVATED, CLOSED],
              }
            }
          ) {
            workflow {
              id
              name
            }
            errors {
              description
              type
            }
          }
        }
        """

        variables = {
            "accountId": self.__account_id,
            "name": f"Alert intelligence workflow of {instance_name} instance",
            "filterName": f"matching issues of {instance_name} instance",
            "policyIds": [policy_id],
            "channelId": channel_id,
        }

        response = self.__send_request(query, variables)

        if response.get("errors"):
            raise NerdGraphAPIError(f"Unexpected NerdGraph error: {response}")

        response = response["aiWorkflowsCreateWorkflow"]

        if response["workflow"] is None:
            raise NerdGraphAPIError("A workflow with the given name already exists")

        return Response(
            id=response["workflow"]["id"],
            name=response["workflow"]["name"],
        )
