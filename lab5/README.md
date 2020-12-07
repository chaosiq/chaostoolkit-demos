This lab is the same as lab4 except we are going to add a safeguard control
to protect the system of running Chaos Engineering experiments.

When a Chaos Engineering is executed, it usually involves degrading the system
in some fashion. However, often, you need to ensure this does not happen
during some critical situations of your system. For instance, your system
is under a real attack, you probably want to interrupt all the experiments
as soon as possible so that your teams can focus on the real issue at hand.

To achoeve that, we are foing to rely on a Chaos Toolkit feature called
`controls`. A control is merely a piece of code that runs during the execution
of the experiment and can do anything to it: interrupting it, changing it on
the fly, logging it, etc. You can learn more about `controls` on the
Chaos Toolkit [documentation](https://docs.chaostoolkit.org/reference/extending/create-control-extension/).

Lets look at the controls block of the experiment now:

```json
$ jq .controls lab5/experiment.json 
[
  {
    "name": "safeguard",
    "provider": {
      "type": "python",
      "module": "chaosaddons.controls.safeguards",
      "arguments": {
        "probes": [
          {
            "name": "no-crashloop-alerted",
            "type": "probe",
            "provider": {
              "type": "python",
              "module": "probes",
              "func": "alert_is_not_firing"
            },
            "frequency": 30,
            "tolerance": true
          }
        ]
      }
    }
  }
]
```

You can have multiple controls running concurrently. Here we are using a
public control from the [chaostoolkit-addons](https://github.com/chaostoolkit/chaostoolkit-addons)
project which acts as a safeguard. The safeguard control takes a sequence
of probes and plays them, if any of them doesn't validate, it immediatly
interrupts the execution of the experiment. Here we play this control every
30s during the experiment's entire run. Namely, we are using the following
probe:

```python
from chaoslib.exceptions import ActivityFailed
from chaoslib.types import Configuration
import requests

__all__ = ["alert_is_not_firing"]


def alert_is_not_firing(alert_name: str, configuration: Configuration) -> bool:
    base = (configuration or {}).get(
        "prometheus_base_url", "http://localhost:9090")
    url = "{base}/api/v1/alerts".format(base=base)
    r = requests.get(url, headers={"Accept": "application/json"})
    if r.status_code > 399:
        raise ActivityFailed("Prometheus alert failed: {m}".format(m=r.text))
    alerts = r.json()
    for alert in alerts.get("data", []):
        if alert["labels"]["name"] == alert_name:
            if alert["state"] == "firing":
                return False
    return True
```

It reads the alerts from our Prometheus endpoint and fails the validation
when the named alert is firing. This triggers the safeguard control that
understands the experiment then must be interrupted as soon as possible.

The probe needs the address of the prometheus endpoint to query
it. This is provided through the configuration `prometheus_base_url`:

```json
$ jq .configuration lab4/experiment.json 
{
  "prometheus_base_url": {
    "type": "env",
    "key": "PROMETHEUS_URL",
    "default": "http://localhost:9090/"
  }
}
```

We need to lookup the prometheus base url:

```console
$ export PROMETHEUS_URL=http://$(kubectl -n monitoring get svc prometheus-k8s --output jsonpath='{.spec.clusterIP}'):9090
```

For the purpose of this lab, we have a specific application that is meant to
fail its startup so it leads quickly to CrashLoopBackoff error
from Kubernetes that is caught as an alert by Prometheus.

```console
$ kubectl apply -f manifests/failingapp.yaml
```

We are now ready to run our experiment.

```console
$ chaos run --rollback-strategy=always lab5/experiment.json 
[2020-12-07 15:38:31 INFO] Validating the experiment's syntax
[2020-12-07 15:38:32 INFO] Experiment looks valid
[2020-12-07 15:38:32 INFO] Running experiment: Losing the ability to talk to the internal services should be adjusted for
[2020-12-07 15:38:32 INFO] Steady-state strategy: default
[2020-12-07 15:38:32 INFO] Rollbacks strategy: always
[2020-12-07 15:38:32 INFO] Steady state hypothesis: n/a
[2020-12-07 15:38:32 INFO] Probe: front-service-must-be-ok
[2020-12-07 15:38:32 INFO] Pausing before next activity for 20s...
[2020-12-07 15:38:52 INFO] Probe: fetch-number-of-failed-calls-from-front-to-middle
[2020-12-07 15:38:52 INFO] Steady state hypothesis is met!
[2020-12-07 15:38:52 INFO] Playing your experiment's method now...
[2020-12-07 15:38:52 INFO] Action: simulate-some-traffic [in background]
[2020-12-07 15:38:52 INFO] Pausing before next activity for 5s...
[2020-12-07 15:38:57 INFO] Action: deny-all-ingress-traffic
[2020-12-07 15:38:57 INFO] Pausing after activity for 5s...
[2020-12-07 15:39:02 CRITICAL] Safeguard 'no-crashloop-alerted' triggered the end of the experiment
[2020-12-07 15:39:02 WARNING] Caught signal num: '10'
[2020-12-07 15:39:05 WARNING] Received the exit signal: 20
[2020-12-07 15:39:05 WARNING] Rollbacks were explicitly requested to be played
[2020-12-07 15:39:05 INFO] Let's rollback...
[2020-12-07 15:39:05 INFO] Rollback: remove-deny-all-ingress-traffic
[2020-12-07 15:39:05 INFO] Action: remove-deny-all-ingress-traffic
[2020-12-07 15:39:05 INFO] Experiment ended with status: interrupted
```

Tada!

We have run this experiment succesfully. Easy, right!

Here, what we notice is that, after 30s, our experiment gets interrupted
by our safeguard control due to the alert that was triggered.

Controls, like the safeguard control, are powerful and allow for some solid
operational strategies of your Chaos Engineering efforts. They provide a
safety framework.
