SHELL       := /bin/sh
IMAGE       := hub.global.cloud.sap/monsoon/infrastructure-exporters
VERSION     := latest

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