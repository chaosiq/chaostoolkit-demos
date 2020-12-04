# Environment Overview

The labs run against a Kubernetes cluster, any recent version (1.16+)
should do.

Locally, you can for instance use:

* minikube
* microk8s

In addition, on the client side, you need Python 3.5 or above.

## Installation of a local Kubernetes

### Minikube

```
$ minikube start --driver none --kubernetes-version v1.19.1
```

### Microk8s

```
$ sudo snap install microk8s --classic --channel=1.19
$ microk8s.enable dns rbac
```

Please review the [microk8s documentation](https://microk8s.io/docs)
for further instructions.

## Installation of Kubernetes dependencies

### Prometheus

We use the [Prometheus operator](https://github.com/prometheus-operator/prometheus-operator).
It will run in the `monitoring` namespace by default and expose:

* Prometheus
* Grafana
* alert manager

Once installed, as explained below, you can view the services running:

```
$ kubectl -n monitoring get all
```

#### minikube

```
$ git clone https://github.com/prometheus-operator/kube-prometheus
$ kubectl apply -f kube-prometheus/manifests/setup/
$ kubectl apply -f kube-prometheus/manifests/
```

#### microk8s

```
$ microk8s.enable prometheus
```

### Chaos Mesh

Chaos Mesh is a powerful fault injection tool for Kubernetes which can create
turbulences on physical and OS resources.

It is used by the Chaos Toolkit in rich Chaos Engineering experiments.

```
$ curl -sSL https://mirrors.chaos-mesh.org/v1.0.2/install.sh | bash
```

See all its services running:

```
$ kubectl -n chaos-testing get all
```

You can access its dashboard as follows:

```
$ kubectl -n chaos-testing port-forward --address 0.0.0.0 service/chaos-dashboard 2333:2333
```

### Traefik

We use traefik as an ingress provider to service our application.

```
$ kubectl apply -f manifests/traefik.yaml
```


### Installation of the Chaos Toolkit and its dependencies

The [Chaos Toolkit](https://chaostoolkit.org/) is the Chaos Engineering
automation framework from Reliably. It is an open source project written in
Python. Assuming you have a proper Python 3.5 available, you should be able to
install it as follows:

```
$ pip install chaostoolkit
```

You can verify it is now available by running:

```
$ chaos info core
```

In itself, Chaos Toolkit does not have any capabilities to operate systems. You
need to installation that target these systems.

```
$ pip install chaostoolkit-kubernetes chaostoolkit-prometheus
```

You can verify they are now available by running:

```
$ chaos info extensions
```

Finally, we install a plugin to generate reports of experiment runs:

```
$ pip install chaostoolkit-reporting
```

### Installation of experiments dependencies

The following labs are going to rely on a variety of tools.

#### Vegeta

[Vegeta](https://github.com/tsenart/vegeta) is a standalone binary that can
induce load onto a web application. We often use it for simple load during an
experiment, to understand how the traffic is impacted by an experiment.

```
$ wget https://github.com/tsenart/vegeta/releases/download/v12.8.4/vegeta_12.8.4_linux_386.tar.gz
$ tar -zxf vegeta_12.8.4_linux_386.tar.gz
$ sudo cp ./vegeta /usr/local/bin/
$ sudo chmod +x /usr/local/bin/vegeta
```
### Installation of the applications

You can now installa the application services:

```
$ kubectl apply -f manifests/all.yaml
```