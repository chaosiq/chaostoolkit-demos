# Basic Chaos Toolkit experiments demo

## Requirements

* a Kubernetes cluster: minikube or [microk8s](https://microk8s.io/)
  should work (tested on the latter)
* [Chaos Toolkit](https://docs.chaostoolkit.org/reference/usage/install/)
* [chaos mesh](https://chaos-mesh.org/) deployed in your cluster
* [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator) deployed in your cluster
* [vegeta](https://github.com/tsenart/vegeta)

The Kubernetes cluster CNI must support
[Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

You will also need to install extensions for Chaos Toolkit:

```
$ pip install -r requirements.txt
```

## Architecture

We have three web services called front, middle and back. They are chained.
Users talk to the front service over a nodeport and the front service talks,
over HTTP, to the middle service which then talks to the back service.

The idea is to demonstrate the ripple effect of bad conditions happening between
these services.

The front and middle services have a maximum connection timeout of one second
to the other services. So if they don't get a connection, or a response,
within that second, they fail and return a stalled value and an error message.
They still respond with a 200.

### Deploy

The services can be deployed into the cluster as follows:

```
$ kubectl apply -f manifests/all.yaml
```

This will put the front service behind a traefik ingress route. It can then
be reached locally on http://localhost:30080

## Chaos Toolkit Experiment scenarios

### Introducing latency to the middle service

This experiment explores what could happen should the middle service gets
slower. This could happen and the middle service team might not be aware
the frond service team requires a fast response.

To run that scenario:

```
$ chaos run --rollback-strategy=always experiments/middle_service_has_latency.json
```

The experiment has two probes to define the baseline:

* the fact the service responds with a 200
* the fact the service didn't include an error message in the response

When you run this experiment, the condition of latency is introduced by
Chaos Mesh which adds a delay of 1500ms to the middle service, going above the
1000ms timeout allowed by the front service.

During the experiment, we run a very midle load to simulate traffic that can
be used to demonstrate the latency.

Note how we force the rollbacks to happen so that the delay is removed from
the middle service when we terminate the experiment.

### Restarting the middle service

This experiment explores what could happen should the middle gets
restarted. This could happen when you rollout a new version.

To run that scenario:

```
$ rm experiments/data/middle_service_restarts.json
$ export PYTHONPATH=`pwd`/experiments/ctkextensions
$ chaos run experiments/middle_service_restarts.json
```

The experiment has two probes to define the baseline:

* the fact the service responds with a 200
* the fact the service didn't include an error message in the responses of the
  load test we run during the experiment

When you run this experiment, the pod for the middle service is deleted, faking
its restart. Because we ran some load during the restart, we got some error
messages from the front service and that triggered the baseline to deviate.

Notice how we have no rollbacks here because the middle service is of course
restarted by Kubernetes.


### Losing network from the middle service to the back service

This experiment explores what could happen should the middle service loses
network to the back service.

To run that scenario:

```
$ chaos run --rollback-strategy=always experiments/middle_service_restarts.json
```

The experiment has two probes to define the baseline:

* the fact the service responds with a 200
* the fact the service didn't include an error message in the response

When you run this experiment, the network loss is faked by adding a new
network policy with a stricter scope. In essence we tell Kubernetes, the
back service does not allow incoming communication anymore.

Notice how we have rollback here to remove that policy.

This requires that your CNI supports network policies.
