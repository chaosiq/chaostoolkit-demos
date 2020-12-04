This lab is the same as lab3 except we are going to use
[Prometheus](https://prometheus.io/) to collect information we will be
validating during the hypothesis. This simply demonstrates you should rely on
your observability stack in general.

Lets look at it:

```json
$ jq '.["steady-state-hypothesis"]' lab4/experiment.json 
{
  "title": "n/a",
  "probes": [
    {
      "type": "probe",
      "name": "front-service-must-be-ok",
      "tolerance": 200,
      "provider": {
        "type": "http",
        "url": "${front_url}"
      }
    },
    {
      "type": "probe",
      "name": "fetch-number-of-failed-calls-from-front-to-middle",
      "tolerance": {
        "type": "probe",
        "name": "error-count",
        "provider": {
          "type": "python",
          "module": "tolerances",
          "func": "error_count_should_not_grow",
          "arguments": {}
        }
      },
      "provider": {
        "type": "python",
        "module": "chaosprometheus.probes",
        "func": "query_interval",
        "arguments": {
          "query": "failed_call_total{to='middle'}",
          "start": "30 seconds ago",
          "end": "now",
          "step": 3
        }
      },
      "pauses": {
        "before": 20
      }
    }
  ]
}
```

This section tells us that we query the health of our system in two ways:

* the front service must be responding with a 200
* the number of faled calls in the last 30s did not grow

The second tolerance relies on a Prometheus probe to query the number of
failed calls in the last 30s from Prometheus. This metric is reported by
our application services and consumed by Prometheus.

Then we validate the growth with a Python tolerance as follows:

```python
from typing import Any, Dict

from chaoslib.exceptions import ActivityFailed


def error_count_should_not_grow(value: Dict[str, Any] = None) -> bool:
    """
    Go through all the error counts and raise an error when we notice an
    increase.
    """
    values = value["data"]["result"][0]["values"]
    if not values:
        return True

    values = set(values[1:len(values):2])
    if len(values) > 1:
        raise ActivityFailed("Error counts: {}".format(values))

    return True
```

The function looks a bit complicated because the response from Prometheus
is fairly nested. But basically, we look that there was no growth.

The Prometheus extension needs the address of the prometheus endpoint to query
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

A hypothesis block has to be valid for all probes to be declared positive.
Any failing probe triggers a negative outcome which can lead to two states.

If the block failed before the next block, the `method` was executed, then
the experiment is failed. We cannot learn if we don't have a healthy system
already. If the hypothesis block was negative after the `method`, then the
experiment showed a deviation of our system, likely due to the condition
we introduced.

The method, for this experiment, looks like this:

```json
$ jq .method lab4/experiment.json
[
  {
    "type": "action",
    "name": "simulate-some-traffic",
    "background": true,
    "provider": {
      "type": "process",
      "path": "vegeta",
      "arguments": "attack -targets=lab4/vegeta.txt -workers=2 -rate=10 -timeout=3s -duration=10s -output=lab4/vegeta.bin"
    }
  },
  {
    "type": "action",
    "name": "deny-all-ingress-traffic",
    "pauses": {
      "before": 5,
      "after": 5
    },
    "provider": {
      "type": "python",
      "module": "chaosk8s.networking.actions",
      "func": "deny_all_ingress",
      "arguments": {
        "label_selectors": {
          "app": "back"
        }
      }
    }
  },
  {
    "type": "action",
    "name": "plot-traffic",
    "provider": {
      "type": "process",
      "path": "vegeta",
      "arguments": "plot lab4/vegeta.bin > lab4/vegeta.html"
    }
  },
  {
    "type": "probe",
    "name": "fetch-application-logs",
    "provider": {
      "type": "python",
      "module": "chaosk8s.pod.probes",
      "func": "read_pod_logs",
      "arguments": {
        "label_selector": "app=front",
        "container_name": "front",
        "last": "10s"
      }
    }
  }
]

```

The action is a sequence of interleaved actions and probes. Actions are
operations against the system whereas probes are merely used to collect data as
we run the experiment for analysis later on.

In this particular case, we have the first two actions that impact the system.

* We run some very mild load against the `front` service using vegeta
* We use [network policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
  to control the network ingress to the `back` service

Then we have an action that is local. It simply plots the results of the
load test into HTML.

Finally, we fetch the `front` service container logs to see there was indeed
an error.

It's important to understand that the actions/probes are sequential. With the
exception of actions/probes that are marked to run in the background. This is
the case of the load test action, it needs to run during the entire method or
it won't be very valuable.

First we need to lookup the prometheus base url:

```console
$ export PROMETHEUS_URL=http://$(kubectl -n monitoring get svc prometheus-k8s --output jsonpath='{.spec.clusterIP}'):9090
```

We are now ready to run it:

```console
$ chaos run --rollback-strategy=always lab4/experiment.json 
[2020-12-04 15:27:17 INFO] Validating the experiment's syntax
[2020-12-04 15:27:17 INFO] Experiment looks valid
[2020-12-04 15:27:17 INFO] Running experiment: Losing the ability to talk to the internal services should be adjusted for
[2020-12-04 15:27:17 INFO] Steady-state strategy: default
[2020-12-04 15:27:17 INFO] Rollbacks strategy: always
[2020-12-04 15:27:17 INFO] Steady state hypothesis: n/a
[2020-12-04 15:27:17 INFO] Probe: front-service-must-be-ok
[2020-12-04 15:27:17 INFO] Pausing before next activity for 20s...
[2020-12-04 15:27:37 INFO] Probe: fetch-number-of-failed-calls-from-front-to-middle
[2020-12-04 15:27:37 INFO] Steady state hypothesis is met!
[2020-12-04 15:27:37 INFO] Playing your experiment's method now...
[2020-12-04 15:27:37 INFO] Action: simulate-some-traffic [in background]
[2020-12-04 15:27:37 INFO] Pausing before next activity for 5s...
[2020-12-04 15:27:42 INFO] Action: deny-all-ingress-traffic
[2020-12-04 15:27:43 INFO] Pausing after activity for 5s...
[2020-12-04 15:27:48 INFO] Action: plot-traffic
[2020-12-04 15:27:48 INFO] Probe: fetch-application-logs
[2020-12-04 15:27:48 INFO] Steady state hypothesis: n/a
[2020-12-04 15:27:48 INFO] Probe: front-service-must-be-ok
[2020-12-04 15:27:49 INFO] Pausing before next activity for 20s...
[2020-12-04 15:28:09 INFO] Probe: fetch-number-of-failed-calls-from-front-to-middle
[2020-12-04 15:28:10 CRITICAL] Steady state probe 'fetch-number-of-failed-calls-from-front-to-middle' is not in the given tolerance so failing this experiment
[2020-12-04 15:28:10 WARNING] Rollbacks were explicitly requested to be played
[2020-12-04 15:28:10 INFO] Let's rollback...
[2020-12-04 15:28:10 INFO] Rollback: remove-deny-all-ingress-traffic
[2020-12-04 15:28:10 INFO] Action: remove-deny-all-ingress-traffic
[2020-12-04 15:28:10 INFO] Experiment ended with status: deviated
[2020-12-04 15:28:10 INFO] The steady-state has deviated, a weakness may have been discovered
```

Tada!

We have run this experiment succesfully. Easy, right!

Notice how we force Chaos Toolkit to run our rollbacks because we need to
remove the latency injection no matter the result of the experiment. Indeed,
when the experiment deviates, the rollbacks are not applied so you can
review the system.

Let's see the rollbacks:

```json
$ jq .rollbacks lab2/experiment.json 
[
  {
    "type": "action",
    "name": "remove-deny-all-ingress-traffic",
    "provider": {
      "type": "python",
      "module": "chaosk8s.networking.actions",
      "func": "remove_deny_all_ingress"
    }
  }
]
```

What exactly happened though? Well, the hypothesis block was applied once and
it passed because the probes validated. This allowed the experiment to move
to its method and run it as well. Finally, the hypothesis block was executed
again and, this time, didn't pass because one of the probes didn't validate
its tolerance. This triggered a deviation status indicating that, under the
given conditions, the system might not be reliable.

What to do from here? Well, you would usually look at your system with this
new evidence in mind and decide of the best course of action. In this case,
we know that losing ingress networking to the `back` service will have a dire
impact on the whole chain. Can we protect this from happening? It's probably
difficult to fully prevent so your best best is heavy monitoring of the
infrastructure and platform. As we used a network policy here, you could also
prevent users to apply such policy through RBAC or even an
[Open Policy Agent](https://www.openpolicyagent.org/) rule.
