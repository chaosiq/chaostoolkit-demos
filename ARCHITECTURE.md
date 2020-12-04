These labs run a set of Chaos Engineering experiments against a very simple
web application.

A `front` application is listening for incoming requests on its root path.
When it gets one, it calls the `middle` service over HTTP. The `middle` service
in turns calls the `back` service. The response of the `back` service is
forwarded back to the `middle` then `front` services, finally to the client.

The `front` and `middle` services have a timeout of 1.0 second for their 
respective calls. When such timeout, or any transport error, occurs, they
still return a 200 response but with the last seen value knwon to them and
an error message. The client can therfore inspect the payload to determine
it receives an actual stalled/errored response.

All the applications expose a `/metrics` endpoint monitored by Prometheus. In
particular they expose the number of errors seen so far.

All applications run in the `default` namespace.