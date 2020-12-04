In this lab, we will run a simple Chaos Engineering experiment that looks
at what could happen when the `middle` service is restarted. We are tring to
understand the impact on the general flow of the application.

A Chaos Toolkit experiment is made of several sections, all serving a purpose.
Let's review the most important ones.

The `steady-state hypothesis` declares the baseline of your system, or said
otherwise, when your system is healthy by some measure.

Lets look at it:

```json
$ jq '.["steady-state-hypothesis"]' lab1/experiment.json 
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
      "name": "front-service-does-not-return-an-error",
      "tolerance": true,
      "provider": {
        "type": "python",
        "module": "tolerances",
        "func": "should_not_have_any_errors",
        "arguments": {
          "filepath": "experiments/data/middle_service_restarts.json"
        }
      }
    }
  ]
}
```

This section tells us that we query the health of our system in two ways:

* the front service must be responding with a 200
* the response must not contain any error message

We will explain how the second one works later on. For now, what is useful
to understand is that a hypothesis is a sequence of probes. Each probe
has its way to query for a piece of information and then use the tolerance
to validate if its falls into the range of what is acceptable.

On the first probe, we merely check the response status code. On the second
probe, we perform a simple test about the result of the Python function called
`should_not_have_any_errors`.

```python
from base64 import b64decode
import json
import os.path


def should_not_have_any_errors(filepath: str) -> bool:
    """
    Simple function that acts as a tolerance validator for the term "error"
    in a given file.
    """
    if not os.path.isfile(filepath):
        return True

    with open(filepath) as f:
        for l in f:
            record = json.loads(b64decode(json.loads(l).get("body")))
            error = record.get("error")
            if error:
                logger.error("Found an error in traces: {}".format(error))
                return False
    return True
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
$ jq .method lab1/experiment.json 
[
  {
    "type": "action",
    "name": "simulate-some-traffic",
    "background": true,
    "provider": {
      "type": "process",
      "path": "vegeta",
      "arguments": "attack -targets=experiments/data/middle_service_restarts.txt -workers=1 -rate=2 -timeout=3s -duration=40s -output=experiments/data/middle_service_restarts.bin"
    }
  },
  {
    "type": "action",
    "name": "terminate-middle-pod",
    "pauses": {
      "before": 5,
      "after": 20
    },
    "provider": {
      "type": "python",
      "module": "chaosk8s.pod.actions",
      "func": "delete_pods",
      "arguments": {
        "name": "middle"
      }
    }
  },
  {
    "type": "action",
    "name": "transform-http-traces",
    "provider": {
      "type": "process",
      "path": "vegeta",
      "arguments": "encode --output experiments/data/middle_service_restarts.json --to json < experiments/data/middle_service_restarts.bin"
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
        "label_selector": "app=middle",
        "container_name": "middle",
        "last": "20s"
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
* We terminate the `middle` pod by calling the Kubernetes API directly

Then we have an action that is local. It simply encodes the results of the
load test into a JSON format that can be consumed by the hypothesis second
probe.

Finally, we fetch the `middle` service container logs to see there was indeed
a restart. We could also have fetched them for the `front` service to see
if it logged an error when calling the `middle` service and failed to do so.

It's important to understand that the actions/probes are sequential. With the
exception of actions/probes that are marked to run in the background. This is
the case of the load test action, it needs to run during the entire method or
it won't be very valuable.

Let's now run this experiment against our cluster. First by preparing the
environment

```console
$ rm lab1/vegeta_results.json
$ export PYTHONPATH=`pwd`/ctkextensions
```

Notably the PYTHONPATH needs to be updated so that our
`should_not_have_any_errors` from above can be found by Python since it's not a
full blown Python package.

We are now ready to run it:

```console
$ chaos run lab1/experiments.json 
[2020-12-03 21:56:04 INFO] Validating the experiment's syntax
[2020-12-03 21:56:05 INFO] Experiment looks valid
[2020-12-03 21:56:05 INFO] Running experiment: Rolling out a new version of the middle service does not impact our users
[2020-12-03 21:56:05 INFO] Steady-state strategy: default
[2020-12-03 21:56:05 INFO] Rollbacks strategy: default
[2020-12-03 21:56:05 INFO] Steady state hypothesis: n/a
[2020-12-03 21:56:05 INFO] Probe: front-service-must-be-ok
[2020-12-03 21:56:05 INFO] Probe: front-service-does-not-return-an-error
[2020-12-03 21:56:05 INFO] Steady state hypothesis is met!
[2020-12-03 21:56:05 INFO] Playing your experiment's method now...
[2020-12-03 21:56:05 INFO] Action: simulate-some-traffic [in background]
[2020-12-03 21:56:05 INFO] Pausing before next activity for 5s...
[2020-12-03 21:56:10 INFO] Action: terminate-middle-pod
[2020-12-03 21:56:10 INFO] Pausing after activity for 20s...
[2020-12-03 21:56:30 INFO] Action: transform-http-traces
[2020-12-03 21:56:30 INFO] Probe: fetch-application-logs
[2020-12-03 21:56:45 INFO] Steady state hypothesis: n/a
[2020-12-03 21:56:45 INFO] Probe: front-service-must-be-ok
[2020-12-03 21:56:46 INFO] Probe: front-service-does-not-return-an-error
[2020-12-03 21:56:46 ERROR] Found an error in traces: ConnectTimeout
[2020-12-03 21:56:46 CRITICAL] Steady state probe 'front-service-does-not-return-an-error' is not in the given tolerance so failing this experiment
[2020-12-03 21:56:46 INFO] Experiment ended with status: deviated
[2020-12-03 21:56:46 INFO] The steady-state has deviated, a weakness may have been discovered
```

Tada!

We have run this experiment succesfully. Easy, right!

What exactly happened though? Well, the hypothesis block was applied once and
it passed because the probes validated. This allowed the experiment to move
to its method and run it as well. Finally, the hypothesis block was executed
again and, this time, didn't pass because one of the probes didn't validate
its tolerance. This triggered a deviation status indicating that, under the
given conditions, the system might not be reliable.

What to do from here? Well, you would usually look at your system with this
nex evidence in mind and decide of the best course of action. Sometimes the
remediation is rather simple. In this case for example, one could simply
augment the number of replicas of the `middle` service so that, enough instances
cover the calls.

Let's see:

```
$ kubectl scale --replicas=2 deployment/middle
```

This will add a new pod for the `middle` service. Let's run it again:

```console
$ chaos run lab1/experiments.json 
[2020-12-03 21:57:27 INFO] Validating the experiment's syntax
[2020-12-03 21:57:27 INFO] Experiment looks valid
[2020-12-03 21:57:27 INFO] Running experiment: Rolling out a new version of the middle service does not impact our users
[2020-12-03 21:57:27 INFO] Steady-state strategy: default
[2020-12-03 21:57:27 INFO] Rollbacks strategy: default
[2020-12-03 21:57:27 INFO] Steady state hypothesis: n/a
[2020-12-03 21:57:27 INFO] Probe: front-service-must-be-ok
[2020-12-03 21:57:27 INFO] Probe: front-service-does-not-return-an-error
[2020-12-03 21:57:27 INFO] Steady state hypothesis is met!
[2020-12-03 21:57:27 INFO] Playing your experiment's method now...
[2020-12-03 21:57:27 INFO] Action: simulate-some-traffic [in background]
[2020-12-03 21:57:27 INFO] Pausing before next activity for 5s...
[2020-12-03 21:57:32 INFO] Action: terminate-middle-pod
[2020-12-03 21:57:33 INFO] Pausing after activity for 20s...
[2020-12-03 21:57:53 INFO] Action: transform-http-traces
[2020-12-03 21:57:53 INFO] Probe: fetch-application-logs
[2020-12-03 21:58:08 INFO] Steady state hypothesis: n/a
[2020-12-03 21:58:08 INFO] Probe: front-service-must-be-ok
[2020-12-03 21:58:08 INFO] Probe: front-service-does-not-return-an-error
[2020-12-03 21:58:08 INFO] Steady state hypothesis is met!
[2020-12-03 21:58:08 INFO] Let's rollback...
[2020-12-03 21:58:08 INFO] No declared rollbacks, let's move on.
[2020-12-03 21:58:08 INFO] Experiment ended with status: completed
```

Tada! We do not get the deviation anymore under the same condition. We have
now overcome our weakness of impacting our users when restarting a pod.