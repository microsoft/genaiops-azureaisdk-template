# GenAIOps Accelerator using Azure AI Foundry

This documentation provides a step-by-step guide to setting up, running, and managing the GenAIOps accelerator using Azure AI Foundry. It supports multiple use cases, each with a predefined folder structure and configuration files. The guide is designed to help both beginners and experienced users get started with running experiments locally and on GitHub.

** detailed documentation is available in the [docs](./docs/index.md) folder. ** 

## Azure AI Foundry GenAIOps Features

### Inner Loop - Experimentation and Evaluation

* **Local Development Environment Integration**
   - Seamless integration with VS Code and development tools for local experimentation
   - Support for rapid prototyping and testing of Use cases
   - Built-in version control and experiment tracking capabilities

* **Customizable Evaluation Framework**
   - Comprehensive set of out-of-box evaluators for common metrics and benchmarks
   - Ability to create and integrate custom evaluators for specific use cases (lib folder)
   - Automated evaluation pipelines for consistent assessment

* **AI Azure Agents Integration**
   - Native support for Azure AI agents
   - Automated agent deployment and testing capabilities
   - Built-in monitoring and evaluation for agent behavior

### Outer Loop - Deployment and Inference

* **Streamlined Deployment Pipeline**
   - Automated deployment processes for models and associated infrastructure
   - Integration with Azure's robust security and compliance features

* **Online Evaluation and Observability**
   - Real-time monitoring of model performance and system health
   - Comprehensive logging and tracing capabilities across the deployment stack

## Platform Capabilities

* **Unified Platform Experience**
   - Single interface for managing multiple AI use cases and workflows
   - Centralized dashboard for monitoring all aspects of AI operations
   - Integrated tooling for collaboration and knowledge sharing
   - Integrated Github Actions for CI/CD

* **Flexible Execution Options**
   - Support for both cloud and local execution environments
   - Hybrid deployment options for optimized resource utilization
   - Seamless scaling between development and production environments

* **Advanced Monitoring and Analytics**
   - Detailed metrics and KPIs for model performance tracking
   - Built-in tools for A/B testing and model comparison
   - Comprehensive audit trails for regulatory compliance and governance

## Table of Contents
1. [Introduction](#1-introduction)
2. [Repository Structure](#2-repository-structure)
3. [Prerequisites](#3-prerequisites)
4. [Local Execution](#4-local-execution)
5. [GitHub Execution](#5-github-execution)
6. [Configuration Files](#6-configuration-files)
7. [Environment Variables](#7-environment-variables)
8. [Best Practices](#8-best-practices)
9. [Infrastructure Deployment with Terraform](#9-infrastructure-deployment-with-terraform)

---

## 1. Introduction
The GenAIOps accelerator is designed to streamline the *development, evaluation - both offline and online, and deployment* of generative AI experiments using Azure AI Foundry. It supports multiple use cases, each with a predefined folder structure and configuration files. The accelerator allows you to run experiments locally and execution on GitHub using GitHub Actions.

---

## 2. Repository Structure
The repository has the following structure:

```
genaiops-azureaisdk-template/
├── .github/ # Contains github actions and workflows
├── docs/ # Contains documentation and guides
├── infra/ # Contains terraform code for building public infrastructure
├── lib/ # Contains reusable code for like custom evaluators
├── llmops/ # Main scripts for running experiments
├── math_coding/ # sample use case folder
├── tests/ # Contains unit tests for llmops scripts
├── .gitignore # Contains files and folders to ignore
├── .env.sample # Sample environment variables file
├── README.md # Main documentation file
```

The repository has the following structure for each use case:

```
use_case_name/
├── data/ # Contains datasets for evaluation
├── flows/ # Contains flow definitions for experiments
├── evaluation/ # Contains evaluation logic and scripts
├── online-evaluations/ # Contains scripts for online evaluations
├── deployment/ # Contains deployment scripts and configurations
├── experiment.yaml # Main configuration file for the experiment
├── experiment.<env>.yaml # Environment-specific configuration files
```

---

## 3. Prerequisites
Before getting started, ensure you have the following:

- **Azure Subscription**: Access to an Azure subscription with the necessary permissions.
- **Azure CLI**: Installed and configured on your local machine.
- **Python 3.9 or above**: Installed on your local machine.
- **Conda**: For managing Python environments.
- **Git**: For version control and cloning the repository.
- **GitHub Account**: For executing workflows and managing secrets.

---

## 4. Local Execution

### Step 1: Clone the Repository
Clone the repository to your local machine:
```bash
git clone <repository_url>
cd <repository_name>
```

Step 2: Log in to Azure
Log in to Azure using the Azure CLI:

```bash
az login
```

Step 3: Set Up the Python Environment
Create and activate a Conda environment:

```bash
conda create -n myenv python=3.9
conda activate myenv
```


Install the required Python packages:

```bash
python -m pip install -r ./.github/requirements/execute_job_requirements.txt
python -m pip install -r ./.github/requirements/build_validation_requirements.txt
python -m pip install -e .
```

Step 4: Configure Environment Variables
Create a .env file from the provided .env.sample file and populate it with the right values:

```bash
cp .env.sample .env
```

Step 5: Run the Experiment
Execute the experiment locally:

```bash 
python -m llmops.eval_experiments --environment_name dev --base_path math_coding --report_dir .
``` 


## 5. GitHub Execution

The repository uses two primary workflows to automate validation, experimentation, and deployment:

### 5.1 PR Validation Workflow (math_coding_pr_workflow.yaml)
Purpose: Validates code quality, runs tests, and ensures build stability during pull requests.
Triggers:
 - workflow_dispatch (manual trigger)
 - Pull requests targeting main or development branches
 - Changes to paths: math_coding/**, .github/**, or llmops/**

### 5.2 CI/CD Dev Workflow (math_coding_ci_dev_workflow.yaml)
Purpose: Executes full experimentation, evaluation, and deployment when code is merged into dev.
Triggers:
 - workflow_dispatch (manual trigger)
 - Pushes to main or development branches
 - Changes to paths: math_coding/**, .github/**, or llmops/**


### 5.3: Configure GitHub Secrets for each environment (pr, dev, test, prod etc):
Ensure all secrets from the .env file are added to GitHub Secrets in your repository settings.

Additionally, add the following secrets:
a. AZURE_CREDENTIALS: Azure service principal credentials for authentication.
b. ENABLE_TELEMETRY: Set to True to enable telemetry during execution

### 5.4: Push Code to GitHub from feature branch
Push your code to the repository:

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

## Key features of the GitHub workflows:
### Reusable Workflows:
 - Both workflows reuse shared workflows (platform_pr_dev_workflow.yaml and platform_ci_dev_workflow.yaml).
 - Promotes DRY (Don’t Repeat Yourself) principles.

### Input Parameters:
 - env_name: Environment to target (pr for validation, dev for deployment).
 - use_case_base_path: Path to the use case (e.g., math_coding).

### Triggers:
 - PR Workflow: Runs on pull requests or manual triggers.
 - Dev Workflow: Runs on code merges to dev or manual triggers.

### Path Filtering:
 - Only triggers if changes affect math_coding/**, .github/**, or llmops/**.

## 6. Configuration Files
### experiment.yaml
This file contains the main configuration for the experiment. 

Example:

```yaml
# Name of the experiment. Must match use case folder name
name: math_coding

# Description of what the experiment does
description: "This is a math coding experiment"

# Path to the flow definition file. Must match the folder structure
flow: flows/math_code_generation

# Function to be called when flow starts. Must math the flow definition
entry_point: pure_python_flow:get_math_response

# List of available connection configurations. Uses Environment Variables for secrets
# These secrets are defined in .env file and github secrets
# These connections are referred in experiments and evaluations
onnections:
  - name: aoai
    connection_type: AzureOpenAIConnection
    api_base: https://demoopenaiexamples.openai.azure.com/
    api_version: 2023-07-01-preview
    api_key: ${AOAI_API_KEY}
    api_type: azure
    deployment_name: ${GPT4O_DEPLOYMENT_NAME}
  - name: gpt4o
    connection_type: AzureOpenAIConnection
    api_base: https://demoopenaiexamples.openai.azure.com/
    api_version: 2023-07-01-preview
    api_key: ${GPT4O_API_KEY}
    api_type: azure
    deployment_name: ${GPT4O_DEPLOYMENT_NAME}

# List of connection configurations to use
connections_ref:
 - aoai
 - gpt4o

# Environment variables needed for the experiment
env_vars:
 - env_var1: "value1"  # Static value
 - env_var2: ${GPT4O_API_KEY}  # Value from environment variable
 - PROMPTY_FILE: another_template.prompty  # Template file path

# Evaluation configuration
evaluators:
 - name: eval_f1_score  # Name of evaluator
   flow: evaluations    # Path to evaluation flow
   entry_point: pure_python_flow:get_math_response  # Evaluation function
   connections_ref:     # Connections for evaluation
     - aoai
     - gpt4o
   env_vars:           # Environment variables for evaluation
     - env_var3: "value1"
     - env_var4: ${GPT4O_API_KEY}
     - ENABLE_TELEMETRY: True
   datasets:           # Test datasets configuration
     - name: math_coding_test
       source: data/math_data.jsonl  # Path to test data
       description: "This dataset is for evaluating flows."
       mappings:      # How to map data fields
         ground_truth: "${data.answer}"    # Expected output
         response: "${target.response}"    # Actual output
```

### Environment specific experiment.yaml
Environment-specific configuration files (e.g., experiment.dev.yaml) and it can override settings in experiment.yaml.


## 7. Environment Variables
The .env file contains sensitive information such as API keys and connection strings. Ensure this file is not committed to the repository. Example .env file:

```bash 
GPT4O_API_KEY=your_api_key_here
AOAI_API_KEY=your_aoai_key_here
```

## 8. Best Practices
Secrets Management: Always store sensitive information in GitHub Secrets or .env files.
Environment Isolation: Use separate environments (e.g., dev, test, prod) for different stages of development.
Version Control: Regularly commit and push changes to GitHub to ensure code is backed up and workflows are triggered.# genaiops-azureaisdk-template

## **9. Infrastructure Deployment with Terraform**
The repository includes Terraform code (`infra/terraform/`) for provisioning required **Azure infrastructure**:

✅ **Resource Group**  
✅ **Azure Storage Account**  
✅ **Azure Key Vault**  
✅ **Application Insights**  
✅ **Azure AI Services & AI Hub**  
✅ **Azure Container Registry**  

### **9.1 Prerequisites**
Ensure the following before deploying the infrastructure:

- **Azure Subscription** with appropriate permissions (Contributor or Owner).  
- **Azure CLI** installed and configured (`az login`).  
- **Terraform CLI** installed ([Terraform Download](https://developer.hashicorp.com/terraform/downloads)).  
- **GitHub Secrets** configured for authentication:
  - `AZURE_CREDENTIALS` (Service Principal JSON for authentication)
  - `STORAGE_ACCOUNT_NAME`
  - `STORAGE_CONTAINER_NAME`
  - `STORAGE_RG_NAME`
  - `AZURE_SUBSCRIPTION_ID`
  - `TF_STATE_KEY`

---

### **9.2 Deploying via GitHub Actions**
Terraform deployment is automated using **GitHub Actions**.

#### **Triggering the Deployment**
1. Navigate to **GitHub Actions** in your repository.  
2. Select **Terraform Deployment Workflow**.  
3. Click **Run workflow** to trigger an infrastructure deployment.

#### **GitHub Workflow Highlights**
- **Terraform Plan & Validate**: Ensures the infrastructure is valid before applying.  
- **Terraform Apply**: Deploys changes automatically upon manual trigger.  
- **Remote State Storage**: Uses **Azure Storage** to store Terraform state for consistency.  

📌 **Workflow File:**  
The deployment workflow is located in `.github/workflows/infra_deploy_terraform_workflow.yaml`.