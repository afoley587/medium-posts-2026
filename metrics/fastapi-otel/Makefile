# Make all targets PHONY
MAKEFLAGS += --always-make

help:  ## Show this help.
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

fmt:  ## Format the code using black
	@cd python && \
		poetry run black ./ && \
		poetry run isort --profile black ./

minikube-start: ## Start minikube with appropriate resources
	@echo "Starting minikube..."
	minikube start
	minikube addons enable ingress
	@echo "Minikube started successfully"

minikube-stop: ## Stop minikube
	minikube stop

docker:  ## Build docker images
	@docker build ./python -t afoley587/coding-challenges/fastapi-otel:latest

poetry-install:  ## Install poetry dependencies
	@poetry install --no-root

skaffold:  ## Runs the application with skaffold
	@skaffold dev
