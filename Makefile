OS := $(shell uname -s)
PKG = github.com/sapcc/infrastructure-exporters
PREFIX := /usr

GO_BUILDFLAGS :=
GO_LDFLAGS    := -s -w
ifdef DEBUG
	BINDDATA_FLAGS = -debug
endif

# which packages to test with static checkers?
GO_ALLPKGS := $(PKG) $(shell go list $(PKG)/pkg/...)
# which packages to test with `go test`?
GO_TESTPKGS := $(shell go list -f '{{if .TestGoFiles}}{{.ImportPath}}{{end}}' $(PKG)/pkg/...)
# which packages to measure coverage for?
GO_COVERPKGS := $(shell go list $(PKG)/pkg/... | grep -v plugins)
# output files from `go test`
GO_COVERFILES := $(patsubst %,build/%.cover.out,$(subst /,_,$(GO_TESTPKGS)))

all: clean dependencies build check

# This target uses the incremental rebuild capabilities of the Go compiler to speed things up.
# If no source files have changed, `go install` exits quickly without doing anything.
generate: dependencies FORCE
	# generate mocks
	mockgen --source pkg/storage/interface.go --destination pkg/storage/genmock.go --package storage
	mockgen --source pkg/keystone/interface.go --destination pkg/keystone/genmock.go --package keystone
	# generate UI
	go-bindata $(BINDDATA_FLAGS) -pkg ui -o pkg/ui/bindata.go -ignore '(.*\.map|bootstrap\.js|bootstrap-theme\.css|bootstrap\.css)'  web/templates/... web/static/...
	gofmt -s -w ./pkg/ui/bindata.go
	# fix generated code comment in order to be respected by golint
	sed -i.bak  's,// Code generated by go-bindata\.$$,// Code generated by go-bindata. DO NOT EDIT.,g' pkg/ui/bindata.go

build: generate FORCE
	# build infrastructure-exporters
	go build $(GO_BUILDFLAGS) -ldflags '-s -w -linkmode external'
	go install $(GO_BUILDFLAGS) -ldflags '$(GO_LDFLAGS)' '$(PKG)'

build/platforms: build
	docker run --rm -v "$$PWD":"/go/src/github.com/sapcc/infrastructure-exporters" -w "/go/src/github.com/sapcc/infrastructure-exporters" -e "GOPATH=/go" golang:1.12-stretch env CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -a -ldflags '-s -w -linkmode external -extldflags -static' -o infrastructure-exporters_linux_amd64
ifeq ($(OS), windows)
	env CGO_ENABLED=1 go build $(GO_BUILDFLAGS) -ldflags '-s -w -linkmode external'
else
	echo "Windows build only supported on Windows"
endif
ifeq ($(OS), Darwin)
	env CGO_ENABLED=1 go build $(GO_BUILDFLAGS) -ldflags '-s -w -linkmode external'
else
	echo "OS X build only supported on OS X"
endif
	chmod +x infrastructure-exporters_*_amd64

# down below, I need to substitute spaces with commas; because of the syntax,
# I have to get these separators from variables
space := $(null) $(null)
comma := ,

check: static-check build/cover.html FORCE
	@echo -e "\e[1;32m>> All tests successful.\e[0m"
static-check: FORCE
	@if s="$$(gofmt -s -l *.go pkg 2>/dev/null)"                            && test -n "$$s"; then printf ' => %s\n%s\n' "gofmt -s -d -e" "$$s"; false; fi
	@if s="$$(golint . && find pkg -type d -exec golint {} \; 2>/dev/null)" && test -n "$$s"; then printf ' => %s\n%s\n' golint "$$s"; false; fi
	go vet $(GO_ALLPKGS)
build/%.cover.out: FORCE dependencies
	# echo "testing packages $(GO_COVERPKGS)"
	go test $(GO_BUILDFLAGS) -ldflags '$(GO_LDFLAGS)' -coverprofile=$@ -covermode=count -coverpkg=$(subst $(space),$(comma),$(GO_COVERPKGS)) $(subst _,/,$*)
build/cover.out: $(GO_COVERFILES)
	# echo "merge coverage files for $(GO_COVERFILES)"
	pkg/test/util/gocovcat.go $(GO_COVERFILES) > $@
build/cover.html: build/cover.out
	go tool cover -html $< -o $@

install: FORCE all
	install -D -m 0755 ./infrastructure-exporters "$(DESTDIR)$(PREFIX)/bin/infrastructure-exporters"

clean: FORCE
	glide cc
	rm -f build/*
	rm -f -- ./infrastructure-exporters_*_*
	rm -rf vendor
	# remove generated mocks
	rm -f pkg/storage/genmock.go
	rm -f pkg/keystone/genmock.go

build/docker.tar: dependencies
ifeq ($(OS), Darwin)
	docker run --rm -v "$$PWD":"/go/src/github.com/sapcc/infrastructure-exporters" -w "/go/src/github.com/sapcc/infrastructure-exporters" -e "GOPATH=/go" golang:1.12-stretch env CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -a -ldflags '-s -w -linkmode external -extldflags -static' -o infrastructure-exporters_linux_amd64
else
	env CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -a -ldflags '-s -w -linkmode external -extldflags -static' -o infrastructure-exporters_linux_amd64
endif
	tar cf - ./infrastructure-exporters_linux_amd64 > build/docker.tar

DOCKER       := docker
DOCKER_IMAGE := hub.global.cloud.sap/monsoon/infrastructure-exporters
DOCKER_TAG   := latest

docker: build/docker.tar
	$(DOCKER) build -t "$(DOCKER_IMAGE):$(DOCKER_TAG)" .

vendor: FORCE
	glide update -v

dependencies:
	# provide dependencies
	glide install -v
.PHONY: FORCE