# Elasticsearch Operations - Simplified Automation

Simple GitLab CI/CD automation for Elasticsearch operations using **version folders** and **`.properties` files**.

## 🎯 Overview

This is a **simplified approach** to automate Elasticsearch operations:
- ✅ **Version folders** (1/, 2/, 3/) for organizing changes
- ✅ **Simple `.properties` files** (key=value format)
- ✅ **Environment selection** via GitLab pipeline parameter
- ✅ **Single Python script** - easy to understand
- ✅ **Minimal effort** for users

## 📁 Project Structure

```
elasticsearch-ops/
├── .gitlab-ci.yml          # GitLab CI/CD pipeline
├── executor.py             # Single Python script (does everything)
├── requirements.txt        # Just Elasticsearch library
├── configs/                # Environment configurations
│   ├── dev.conf
│   ├── qa.conf
│   ├── uat.conf
│   ├── perf.conf
│   ├── perfdr.conf
│   ├── prod.conf
│   └── proddr.conf
└── versions/               # Version folders
    ├──  1/                 # Version 1 operations
    │   ├── index_create.properties
    │   └── delete_index.properties
    └── 2/                  # Version 2 operations
        ├── create_products.properties
        └── template_logs.properties
```

## 🚀 Quick Start

### 1. Configure Environments

Edit `configs/dev.conf` (and other environment files) with your Elasticsearch details:

```properties
ES_HOST=your-elasticsearch-host.com
ES_PORT=9200
ES_SCHEME=https
ES_USERNAME=your_username
ES_PASSWORD=your_password
VERIFY_CERTS=true
STOP_ON_ERROR=false
```

> **Tip**: For security, use GitLab CI/CD variables for credentials instead of hardcoding.

### 2. Create Operations

Create a new version folder and add `.properties` files:

```bash
mkdir versions/3
```

**Example: Create an index** (`versions/3/create_users.properties`):
```properties
operation=create_index
indexname=users
shards=3
replicas=2
inputjson={"mappings":{"properties":{"user_id":{"type":"keyword"},"email":{"type":"keyword"}}}}
```

**Example: Delete an index** (`versions/3/delete_old.properties`):
```properties
operation=delete_index
indexname=old-users
```

### 3. Commit and Push

```bash
git add versions/3/
git commit -m "Version 3: Create users index, delete old-users"
git push
```

### 4. Run in GitLab

1. Go to **CI/CD → Pipelines**
2. Click **"Run pipeline"**
3. Select **Environment** (dev, qa, prod, etc.)
4. Select **Version** (3 or "latest")
5. Click **"Run pipeline"**

Done! The pipeline will execute your operations.

## 📝 Supported Operations

### Create Index
```properties
operation=create_index
indexname=my-index
shards=3
replicas=2
inputjson={"mappings":{"properties":{"field1":{"type":"keyword"}}}}
```

### Delete Index
```properties
operation=delete_index
indexname=my-index
```

### Update Index Settings
```properties
operation=update_index
indexname=my-index
inputjson={"settings":{"number_of_replicas":3}}
```

### Create Index Template
```properties
operation=create_template
templatename=my-template
indexpattern=logs-*
inputjson={"template":{"settings":{"number_of_shards":3},"mappings":{"properties":{"timestamp":{"type":"date"}}}}}
```

### Delete Template
```properties
operation=delete_template
templatename=my-template
```

### Index Document
```properties
operation=index_document
indexname=my-index
docid=doc_001
inputjson={"field1":"value1","field2":"value2"}
```

## 🔄 Workflow

### Typical Development Flow

1. **Create new version folder**:
   ```bash
   mkdir versions/4
   ```

2. **Add operation files**:
   ```bash
   cat > versions/4/create_index.properties << EOF
   operation=create_index
   indexname=new-feature-index
   shards=3
   replicas=2
   inputjson={"mappings":{"properties":{"id":{"type":"keyword"}}}}
   EOF
   ```

3. **Test in dev**:
   - Push to GitLab
   - Run pipeline with `ENVIRONMENT=dev`, `VERSION=4`

4. **Promote to higher environments**:
   - Run same version in qa: `ENVIRONMENT=qa`, `VERSION=4`
   - Then uat, prod, etc.

### Version Management

- **Version folders** are numbered: 1, 2, 3, ...
- Use **"latest"** to automatically run the highest version
- Each version can contain **multiple `.properties` files**
- Files execute in **alphabetical order**

## ⚙️ Configuration

### Environment Config Files (`.conf`)

Simple key=value format in `configs/{environment}.conf`:

```properties
ES_HOST=elasticsearch-dev.example.com
ES_PORT=9200
ES_SCHEME=https
ES_USERNAME=dev_user
ES_PASSWORD=dev_password
VERIFY_CERTS=true
STOP_ON_ERROR=false
```

### Using GitLab CI/CD Variables

For security, store credentials in GitLab:

1. Go to **Settings → CI/CD → Variables**
2. Add variables:
   - `ES_USERNAME` (protected, masked)
   - `ES_PASSWORD` (protected, masked)
3. Reference in executor by setting environment variables in GitLab job

## 🔧 Local Testing

Test locally before running in GitLab:

```bash
# Install dependencies
pip install -r requirements.txt

# Run for dev environment, version 1
python executor.py --environment dev --version 1

# Run latest version
python executor.py --environment dev --version latest
```

## 📊 GitLab Pipeline

The pipeline has a single job with **environment dropdown**:

```yaml
deploy:
  when: manual
  variables:
    ENVIRONMENT:
      options: [dev, qa, uat, perf, perfdr, prod, proddr]
    VERSION:
      value: "latest"
```

**In GitLab UI**:
- Click "Run pipeline"
- Select environment from dropdown
- Optionally change version
- Click "Run"

## ✅ Best Practices

1. **Test in dev first**
   - Always run new versions in dev before higher environments

2. **Use meaningful version numbers**
   - Increment versions for each change

3. **One logical change per version**
   - Keep versions focused (e.g., version 3 = new user index)

4. **Keep inputjson compact**
   - Use JSON minified format (no extra spaces)

5. **Comment your files**
   - Use `# comments` in properties files to document

6. **Stop on error in production**
   - Set `STOP_ON_ERROR=true` for prod/proddr

## 🐛 Troubleshooting

### Connection errors
- Check `ES_HOST`, `ES_PORT`, `ES_SCHEME` in config
- Verify network access to Elasticsearch

### Authentication errors
- Verify `ES_USERNAME` and `ES_PASSWORD`
- Check GitLab CI/CD variables are set correctly

### "Version not found"
- Ensure version folder exists (e.g., `versions/3/`)
- Check folder name is a number

### "No .properties files found"
- Ensure files end with `.properties`
- Check files are in the version folder

### JSON parsing errors
- Validate JSON in `inputjson` field
- Use online JSON validator
- Ensure proper escaping (no quotes around JSON)

## 📖 Examples

### Example Version 1: Create and Delete
```
versions/1/
├── 01_create_index.properties
└── 02_delete_old.properties
```

**01_create_index.properties**:
```properties
operation=create_index
indexname=new-index
shards=3
replicas=2
inputjson={"mappings":{"properties":{"id":{"type":"keyword"},"name":{"type":"text"}}}}
```

**02_delete_old.properties**:
```properties
operation=delete_index
indexname=old-index
```

### Example Version 2: Template
```
versions/2/
└── logs_template.properties
```

**logs_template.properties**:
```properties
operation=create_template
templatename=logs
indexpattern=logs-*,metrics-*
inputjson={"priority":100,"template":{"settings":{"number_of_shards":3},"mappings":{"properties":{"@timestamp":{"type":"date"},"message":{"type":"text"}}}}}
```

## 🎓 Understanding the Code

The `executor.py` script has **detailed comments** explaining every line for Python beginners. Key functions:

- `load_properties_file()` - Reads .properties files
- `load_environment_config()` - Loads environment configs
- `connect_to_elasticsearch()` - Establishes connection
- `find_version_operations()` - Finds operations in version folder
- `execute_operation()` - Routes and executes operations

## 📄 License

[Your License]

## 🤝 Support

For questions:
1. Check this README
2. Review `executor.py` comments (detailed explanations)
3. Test locally with `--verbose` flag (if added)

---

**Simple. Version-based. Effective.** 🚀

**Project Location**: `C:\Users\ramya\.gemini\antigravity\scratch\elasticsearch-ops`
