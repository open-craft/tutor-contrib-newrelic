NewRelic plugin for Tutor
###############################################################################

This plugin creates a NewRelic alert policy, related synthetics monitors, and
notification channels, utilizing workflows.

As monitoring can be sensitive in several cases **not trying to be clever** and
delete resources. When resources are not needed anymore for the instance, the
operator is responsible of cleaning them up, not the plugin.

Installation
************

.. code-block:: bash

    pip install git+https://github.com/open-craft/tutor-contrib-newrelic

Usage
*****

Add the following to the config:

.. code-block:: yaml

    NEWRELIC_API_KEY: <API_KEY>
    NEWRELIC_ACCOUNT_ID: <ACCOUNT_ID>
    NEWRELIC_REGION_CODE: <REGION (EU or US)>
    NEWRELIC_SYNTHETICS_MONITORS:
      - recipient: email@example.com
        urls:
          - https://instance.example.com/heartbeat
          - https://instance.example.com/heartbeat?extended
          - https://studio.instance.example.com/heartbeat
          - https://mfe.instance.example.com
    # Optional. By default this plugin will create a workflow for you.
    # If specified, will add the created notification policy to this
    # workflow rather than creating a new one.
    NEWRELIC_WORKFLOW_NAME: My Workflow

Enable the plugin and create monitoring policy:

.. code-block:: bash

    tutor plugins enable newrelic
    tutor newrelic create-alert-workflow

License
*******

This software is licensed under the terms of the AGPLv3, see LICENSE.txt.
