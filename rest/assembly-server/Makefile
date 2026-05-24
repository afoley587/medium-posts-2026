# Make all targets PHONY
MAKEFLAGS += --always-make

help:  ## Show this help.
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

build:  ## Builds the tiny-server
	@mkdir -p build/ && \
		clang -arch arm64 server.s -o build/tiny-server

run:  ## Runs the server
	@./build/tiny-server

curl:  ## Test the server with 'curl'
	@curl http://localhost:8080/health

clean:  ## Cleans up artifacts
	@rm -r build/
