# Elasticsearch Operations Automation

A GitLab CI/CD-based automation tool to manage Elasticsearch operations through configuration files stored in Git, providing full audit trails, version control, and safe environment promotion.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Environment Promotion Workflow](#environment-promotion-workflow)
- [Supported Operations](#supported-operations)
- [GitLab CI/CD Pipeline](#gitlab-cicd-pipeline)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This project automates Elasticsearch operations using a **configuration-driven approach**. Instead of running manual curl commands, you define operations in YAML files, commit them to Git, and let the CI/CD pipeline execute them across environments.

### Why This Approach?

✅ **Full Audit Trail** - Every change tracked in Git history  
✅ **Version Control** - Roll back changes easily  
✅ **Safe Promotions** - Test in dev before promoting to production  
✅ **No Lost Commands** - All operations documented in config files  
✅ **Repeatable** - Same operations work across all environments  

## ✨ Features

- **Configuration-Driven**: Define operations in YAML files
- **Multi-Environment**: Support for dev, qa, uat, perf, perfdr, prod, proddr
- **Automated Validation**: Validates configurations before execution
- **Dry-Run Mode**: Preview changes without executing them
- **Error Handling**: Robust retry logic and error reporting
- **Audit Reports**: JSON reports of all executed operations
- **Manual Approvals**: Required for higher environments (UAT+)
- **Beginner-Friendly**: Detailed comments in all Python code

## 📁 Project Structure

```
elasticsearch-automation/
├── .gitlab-ci.yml              # CI/CD pipeline definition
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── config/
│   ├── environments/          # Environment configurations
│   │   ├── dev.yml
│   │   ├── qa.yml
│   │   ├── uat.yml
│   │   ├── perf.yml
│   │   ├── perfdr.yml
│   │   ├── prod.yml
│   │   └── proddr.yml
│   └── operations/            # Operation definitions
│       ├── indices/
│       │   ├── create/        # Index creation operations
│       │   ├── update/        # Index update operations
│       │   └── delete/        # Index deletion operations
│       ├── index_templates/   # Template operations
│       │   └── create/
│       └── documents/         # Document operations
│           └── create/
└── src/                       # Python source code
    ├── es_automation.py       # Main automation script
    ├── es_client.py           # Elasticsearch client wrapper
    ├── config_parser.py       # Configuration parser
    ├── validators.py          # Validation logic
    └── utils.py               # Utility functions
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Access to Elasticsearch cluster(s)
- GitLab account with CI/CD enabled

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd elasticsearch-automation
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment settings**
   
   Edit `config/environments/dev.yml` with your Elasticsearch details:
   ```yaml
   elasticsearch:
     host: your-elasticsearch-host.com
     port: 9200
     scheme: https
     username: ${ES_USERNAME}  # Set via GitLab CI/CD variables
     password: ${ES_PASSWORD}  # Set via GitLab CI/CD variables
   ```

4. **Set GitLab CI/CD variables**
   
   In GitLab: Settings → CI/CD → Variables, add:
   - `ES_USERNAME` - Elasticsearch username
   - `ES_PASSWORD` - Elasticsearch password (masked)
   - Repeat for each environment

### Test Locally

Run in dry-run mode to test without executing:

```bash
export DRY_RUN=true
python src/es_automation.py --environment dev --config ./config
```

## ⚙️ Configuration

### Environment Configuration

Each environment file (`config/environments/<env>.yml`) contains:

```yaml
elasticsearch:
  host: elasticsearch-dev.example.com
  port: 9200
  scheme: https
  username: ${ES_USERNAME}    # Use GitLab CI/CD variables
  password: ${ES_PASSWORD}
  verify_certs: true

stop_on_error: false          # Set true for prod
report_file: ./reports/dev-execution-report.json
```

### Operation Configuration

Operation files define what actions to perform. Examples:

**Create Index** (`config/operations/indices/create/users_index.yml`):
```yaml
operation: create_index
index_name: users

settings:
  number_of_shards: 3
  number_of_replicas: 2

mappings:
  properties:
    user_id:
      type: keyword
    username:
      type: text
    email:
      type: keyword
    created_at:
      type: date
```

**Create Index Template** (`config/operations/index_templates/create/logs_template.yml`):
```yaml
operation: create_index_template
template_name: logs_template

index_patterns:
  - "logs-*"

template:
  settings:
    number_of_shards: 3
  mappings:
    properties:
      timestamp:
        type: date
      level:
        type: keyword
      message:
        type: text
```

## 💻 Usage

### Adding a New Operation

1. **Create operation file**
   
   Create a YAML file in the appropriate directory:
   ```bash
   # Example: Create new index
   nano config/operations/indices/create/my_new_index.yml
   ```

2. **Define the operation**
   ```yaml
   operation: create_index
   index_name: my_new_index
   
   settings:
     number_of_shards: 3
     number_of_replicas: 2
   
   mappings:
     properties:
       id:
         type: keyword
       name:
         type: text
   ```

3. **Commit and push**
   ```bash
   git add config/operations/indices/create/my_new_index.yml
   git commit -m "Add my_new_index definition"
   git push origin dev
   ```

4. **Pipeline automatically runs**
   
   GitLab CI/CD will validate and deploy to dev environment.

### Running Manually

For local testing or troubleshooting:

```bash
# Normal execution
python src/es_automation.py --environment dev

# Dry-run mode (simulation only)
DRY_RUN=true python src/es_automation.py --environment dev

# Verbose logging
python src/es_automation.py --environment dev --verbose

# Custom config directory
python src/es_automation.py --environment dev --config /path/to/config
```

## 🔄 Environment Promotion Workflow

### Typical Workflow

1. **Development**
   ```bash
   # Create feature branch
   git checkout dev
   git pull origin dev
   git checkout -b feature/new-index
   
   # Add operation file
   nano config/operations/indices/create/new_index.yml
   
   # Commit and push
   git add config/operations/indices/create/new_index.yml
   git commit -m "Add new index for feature X"
   git push origin feature/new-index
   
   # Create merge request to dev branch
   # After approval, merge to dev → auto-deploys to dev environment
   ```

2. **Promote to QA**
   ```bash
   git checkout qa
   git merge dev
   git push origin qa
   # Auto-deploys to QA environment
   ```

3. **Promote to UAT**
   ```bash
   git checkout uat
   git merge qa
   git push origin uat
   # ⚠️ Manual approval required in GitLab UI
   ```

4. **Promote to Production**
   ```bash
   git checkout prod
   git merge uat  # Merge from UAT (already tested)
   git push origin prod
   # ⚠️ Manual approval required in GitLab UI
   ```

### Rollback Procedure

If something goes wrong:

```bash
# Revert the merge commit
git checkout prod
git revert -m 1 HEAD
git push origin prod

# This will trigger pipeline to revert changes
```

## 🔧 Supported Operations

### Index Operations

| Operation | Description | Required Fields |
|-----------|-------------|-----------------|
| `create_index` | Create a new index | `index_name`, optional: `settings`, `mappings` |
| `delete_index` | Delete an index | `index_name` |
| `update_index_settings` | Update index settings | `index_name`, `settings` |

### Index Template Operations

| Operation | Description | Required Fields |
|-----------|-------------|-----------------|
| `create_index_template` | Create/update template | `template_name`, `index_patterns`, `template` |
| `delete_index_template` | Delete template | `template_name` |

### Document Operations

| Operation | Description | Required Fields |
|-----------|-------------|-----------------|
| `index_document` | Create/update document | `index_name`, `document`, optional: `doc_id` |
| `delete_document` | Delete document | `index_name`, `doc_id` |

## 🔄 GitLab CI/CD Pipeline

### Pipeline Stages

1. **validate** - Validates all configuration files (runs on every commit)
2. **deploy-dev** - Auto-deploys to dev (on `dev` branch)
3. **deploy-qa** - Auto-deploys to QA (on `qa` branch)
4. **deploy-uat** - Manual approval required (on `uat` branch)
5. **deploy-perf** - Manual approval required (on `perf` branch)
6. **deploy-perfdr** - Manual approval required (on `perfdr` branch)
7. **deploy-prod** - Manual approval required (on `prod` branch)
8. **deploy-proddr** - Manual approval required (on `proddr` branch)

### Pipeline Features

- ✅ Automatic validation on all branches
- ✅ Auto-deployment to dev and QA
- ✅ Manual approval gates for higher environments
- ✅ Execution reports saved as artifacts
- ✅ Environment tracking in GitLab

## 📝 Best Practices

1. **Always test in dev first**
   - Never commit directly to higher environment branches

2. **Use descriptive commit messages**
   ```bash
   # Good
   git commit -m "Add users index with email and profile fields"
   
   # Bad
   git commit -m "update"
   ```

3. **One operation per file**
   - Makes changes easier to track and review

4. **Review before promoting**
   - Check GitLab pipeline logs and execution reports
   - Verify changes in lower environment before promoting

5. **Use dry-run for testing**
   ```bash
   DRY_RUN=true python src/es_automation.py --environment prod
   ```

6. **Keep production settings strict**
   - Set `stop_on_error: true` in prod environments
   - Require manual approvals

## 🐛 Troubleshooting

### Common Issues

**Issue: Connection refused**
```
Error: Failed to connect to Elasticsearch at https://...
```
**Solution**: Check host/port in environment config, verify network access

**Issue: Authentication failed**
```
Error: [AuthenticationException] ...
```
**Solution**: Verify GitLab CI/CD variables are set correctly for the environment

**Issue: Index already exists**
```
Error: resource_already_exists_exception
```
**Solution**: Either delete the existing index first or change to update operation

**Issue: Pipeline validation fails**
```
Error: Missing required fields...
```
**Solution**: Check your YAML syntax and ensure all required fields are present

### Checking Logs

**GitLab CI/CD**:
- Go to CI/CD → Pipelines → Select pipeline → View job logs

**Local execution**:
- Add `--verbose` flag for detailed logging
- Check execution reports in `reports/` directory

**Elasticsearch logs**:
- Check Elasticsearch server logs for any cluster-side issues

### Getting Help

1. Check execution reports for detailed error information
2. Run locally with `--verbose` flag
3. Use dry-run mode to test without execution
4. Review Elasticsearch documentation for specific operation errors

## 📄 License

[Your License Here]

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a merge request

---

**Built with ❤️ for reliable Elasticsearch operations management**
