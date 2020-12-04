In this lab, we are going to explore the impact of latency on the entire
chain of services when one intermediate service gets slower.

Let's remember that the `front` service communicates with the `middle`
service and expects a connection and response unde 1 second each. Likewise,
the `middle` service speaks to the `back` service with the same expectations.
This means that, a latency may be timing out any of these two services.

The `steady-state hypothesis` declares the baseline of your system, or said
otherwise, when your system is healthy by some measure.

Lets look at it:

```json
$ jq '.["steady-state-hypothesis"]' lab2/experiment.json 
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
      "tolerance": {
        "type": "jsonpath",
        "target": "body",
        "path": "$.error",
        "count": 0
      },
      "provider": {
        "type": "http",
        "url": "${front_url}"
      }
    }
  ]
}
```

This section tells us that we query the health of our system in two ways:

* the front service must be responding with a 200
* the response must not contain any error message

The second tolerance uses [jsonpath](https://jsonpath2.readthedocs.io/en/latest/exampleusage.html#syntax)
to extract the information used to validate the probe. The response from
the `front` service should not contain an `error` field.

A hypothesis block has to be valid for all probes to be declared positive.
Any failing probe triggers a negative outcome which can lead to two states.

If the block failed before the next block, the `method` was executed, then
the experiment is failed. We cannot learn if we don't have a healthy system
already. If the hypothesis block was negative after the `method`, then the
experiment showed a deviation of our system, likely due to the condition
we introduced.

The method, for this experiment, looks like this:

```json
 $ jq .method lab2/experiment.json 
[
  {
    "type": "action",
    "name": "simulate-some-traffic",
    "background": true,
    "provider": {
      "type": "process",
      "path": "vegeta",
      "arguments": "attack -targets=lab1/vegeta.txt -workers=1 -rate=1 -connections=3  -duration=25s -output=lab2/vegeta_results.bin"
    }
  },
  {
    "type": "action",
    "name": "inject-latency",
    "provider": {
      "type": "python",
      "module": "chaosk8s.crd.actions",
      "func": "create_custom_object",
      "arguments": {
        "group": "chaos-mesh.org",
        "plural": "networkchaos",
        "version": "v1alpha1",
        "resource": {
          "apiVersion": "chaos-mesh.org/v1alpha1",
          "kind": "NetworkChaos",
          "metadata": {
            "name": "delaying-middle-1",
            "namespace": "default"
          },
          "spec": {
            "action": "delay",
            "mode": "one",
            "selector": {
              "namespaces": [
                "default"
              ],
              "labelSelectors": {
                "app": "middle"
              }
            },
            "delay": {
              "latency": "1500ms"
            },
            "duration": "10s",
            "scheduler": {
              "cron": "@every 15s"
            }
          }
        }
      }
    },
    "pauses": {
      "before": 5,
      "after": 20
    }
  },
  {
    "type": "action",
    "name": "plot-traffic",
    "provider": {
      "type": "process",
      "path": "vegeta",
      "arguments": "plot lab2/vegeta_results.bin > lab2/vegeta_results.html"
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
        "last": "25s"
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
* We use [Chaos Mesh](https://chaos-mesh.org) to inject network latency
  between the `front` and `middle` services. We do so by sending a custom
  resource object that the Chaos Mesh operator will see and apply.

Then we have an action that is local. It simply plots the results of the
load test into HTML.

Finally, we fetch the `front` service container logs to see there was indeed
an error.

It's important to understand that the actions/probes are sequential. With the
exception of actions/probes that are marked to run in the background. This is
the case of the load test action, it needs to run during the entire method or
it won't be very valuable.

We are now ready to run it:

```console
$ chaos run --rollback-strategy=always lab2/experiment.json 
[2020-12-04 14:35:42 INFO] Validating the experiment's syntax
[2020-12-04 14:35:43 INFO] Experiment looks valid
[2020-12-04 14:35:43 INFO] Running experiment: We can tolerate a small latency from internal services
[2020-12-04 14:35:43 INFO] Steady-state strategy: default
[2020-12-04 14:35:43 INFO] Rollbacks strategy: default
[2020-12-04 14:35:43 INFO] Steady state hypothesis: n/a
[2020-12-04 14:35:43 INFO] Probe: front-service-must-be-ok
[2020-12-04 14:35:43 INFO] Probe: front-service-does-not-return-an-error
[2020-12-04 14:35:43 INFO] Steady state hypothesis is met!
[2020-12-04 14:35:43 INFO] Playing your experiment's method now...
[2020-12-04 14:35:43 INFO] Action: simulate-some-traffic [in background]
[2020-12-04 14:35:43 INFO] Pausing before next activity for 5s...
[2020-12-04 14:35:48 INFO] Action: inject-latency
[2020-12-04 14:35:48 INFO] Pausing after activity for 20s...
[2020-12-04 14:36:08 INFO] Action: plot-traffic
[2020-12-04 14:36:08 INFO] Probe: fetch-application-logs
[2020-12-04 14:36:09 INFO] Steady state hypothesis: n/a
[2020-12-04 14:36:09 INFO] Probe: front-service-must-be-ok
[2020-12-04 14:36:10 INFO] Probe: front-service-does-not-return-an-error
[2020-12-04 14:36:11 CRITICAL] Steady state probe 'front-service-does-not-return-an-error' is not in the given tolerance so failing this experiment
[2020-12-04 14:36:11 INFO] Experiment ended with status: deviated
[2020-12-04 14:36:11 INFO] The steady-state has deviated, a weakness may have been discovered
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
    "name": "remove-latency",
    "provider": {
      "type": "python",
      "module": "chaosk8s.crd.actions",
      "func": "delete_custom_object",
      "arguments": {
        "group": "chaos-mesh.org",
        "plural": "networkchaos",
        "version": "v1alpha1",
        "name": "delaying-middle-1"
      }
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
nex evidence in mind and decide of the best course of action. In this case,
you know that latency will impact the `front` service so you can go to the
`middle` service team and mention this with them. You could even set a service
level object (SLO) to measure it.
