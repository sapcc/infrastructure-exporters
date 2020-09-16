SHELL       := /bin/sh
IMAGE       := keppel.eu-de-1.cloud.sap/ccloud/infrastructure-exporters
VERSION     := 20200916121200

### Executables
DOCKER := docker

### Docker Targets

.PHONY: build
build:
	$(DOCKER) build -t $(IMAGE):$(VERSION) --rm .
	$(DOCKER) tag $(IMAGE):$(VERSION) $(IMAGE):latest

.PHONY: push
push:
	$(DOCKER) push $(IMAGE):$(VERSION)
	$(DOCKER) push $(IMAGE):latest 