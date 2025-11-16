# Day 1: Infrastructure & Microservices - Interview Prep Guide

## Slide 1: What is Infrastructure as Code (IaC)?

### Definition
Infrastructure as Code (IaC) is the practice of managing and provisioning infrastructure through code instead of manual processes.

### Real-World Analogy
**Without IaC (Manual):**
- Like cooking without a recipe
- Hard to remember exact steps
- Can't share with others
- Mistakes happen every time

**With IaC (Terraform):**
- Written recipe that anyone can follow
- Same result every time
- Version controlled (track changes)
- Shareable with team

### Benefits
- **Repeatability:** Run same code = same infrastructure
- **Version Control:** Track all changes in Git
- **Documentation:** Code IS the documentation
- **Automation:** No manual clicking in portals
- **Consistency:** Dev, Staging, Prod are identical

### Interview Question Answer
**Q: Why use Infrastructure as Code?**

**A:** "I use IaC because it eliminates configuration drift and human error. For example, in my digital twin project, I used Terraform to define Azure resources. This means:
- I can recreate the entire environment in minutes
- My team knows exactly what's deployed (code = documentation)
- We can version control infrastructure changes
- Dev and production environments are identical
This is critical in enterprise environments where consistency and repeatability are paramount."

---

## Slide 2: Terraform Core Concepts

### The 4 Essential Files

#### 1. provider.tf - "Which Cloud?"
```hcl
provider "azurerm" {
  features {}
}
```
**Purpose:** Tells Terraform you're using Azure (not AWS/GCP)
**Analogy:** Choosing which store to shop at (Azure vs AWS)

#### 2. variables.tf - "Settings & Configuration"
```hcl
variable "project_name" {
  default = "refinery-dt"
}
```
**Purpose:** Define reusable values (change once, affects everywhere)
**Analogy:** Your phone settings - set ringtone once, applies to all calls

#### 3. main.tf - "What to Build"
```hcl
resource "azurerm_resource_group" "main" {
  name     = "my-rg"
  location = "eastus"
}
```
**Purpose:** Actual resources to create
**Analogy:** The blueprint of your house

#### 4. outputs.tf - "Show Results"
```hcl
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}
```
**Purpose:** Display important values after creation
**Analogy:** Receipt after shopping

### Interview Question Answer
**Q: Explain your Terraform project structure**

**A:** "I organize Terraform code into logical files:
- `provider.tf` specifies Azure as my cloud provider
- `variables.tf` defines configurable parameters like project name and region - this makes the code reusable
- `main.tf` contains actual resource definitions (Resource Groups, Storage Accounts, AKS clusters)
- `outputs.tf` displays critical values like registry URLs and cluster names

This separation follows best practices for maintainability. For example, to deploy to a different region, I only change the variable file, not the entire configuration."

---

## Slide 3: The 3 Terraform Commands

### 1. terraform init
**What it does:** Downloads provider plugins and initializes backend

**Analogy:** Installing an app before using it

**What happens:**
1. Reads `provider.tf`
2. Downloads Azure provider plugin
3. Initializes state storage
4. Creates `.terraform` folder

**When to run:** 
- First time in a project
- After adding new providers
- After changing backend configuration

### 2. terraform plan
**What it does:** Shows what WILL change (preview mode)

**Analogy:** Looking at menu before ordering food

**Output symbols:**
- `+` = Will CREATE new resource
- `~` = Will UPDATE existing resource
- `-` = Will DELETE resource

**Critical:** ALWAYS run this before `apply`!

**Example output:**
```
Plan: 3 to add, 0 to change, 0 to destroy
```

### 3. terraform apply
**What it does:** Actually creates/modifies/deletes resources

**Analogy:** Clicking "Buy Now" on Amazon

**What happens:**
1. Shows plan again
2. Asks for confirmation: `Enter a value: yes`
3. Executes changes
4. Updates state file
5. Shows outputs

**Safety feature:** 
- Idempotent (safe to run multiple times)
- Only changes what's different

### Interview Question Answer
**Q: Walk me through your Terraform deployment process**

**A:** "My workflow follows infrastructure best practices:

1. **terraform init** - I run this first to download the Azure provider and initialize the backend. This sets up Terraform to manage state.

2. **terraform plan** - I always run plan before applying changes. This shows me exactly what will be created, modified, or deleted. For example, when I added the Container Registry, plan showed '+1 to add' which I verified against requirements.

3. **terraform apply** - Only after reviewing the plan do I apply changes. Terraform asks for confirmation to prevent accidents.

4. **Git commit** - I commit the Terraform code to version control so my team can track infrastructure changes.

This process prevents configuration drift and ensures infrastructure changes are reviewed and documented."

---

## Slide 4: Azure Resource Group Explained

### What is a Resource Group?

**Definition:** A logical container for Azure resources

**Analogy:** A folder on your computer
```
C:\
├── Work-Projects\          ← Resource Group
│   ├── file1.docx         ← Storage Account
│   ├── file2.xlsx         ← Container Registry
│   └── file3.pptx         ← AKS Cluster
└── Personal\              ← Another Resource Group
    ├── photo.jpg
    └── video.mp4
```

### Why Resource Groups Matter

**Organization:**
- Group related resources together
- Easy to find everything for one project

**Management:**
- Apply tags to entire group
- Set permissions at group level
- Monitor costs per group

**Lifecycle:**
- Delete resource group = delete ALL resources inside
- Perfect for dev/test environments

### Our Resource Group
```hcl
resource "azurerm_resource_group" "main" {
  name     = "refinery-dt-dev-rg"
  location = "eastus"
  tags = {
    Project   = "Digital Twin"
    ManagedBy = "Terraform"
  }
}
```

### Interview Question Answer
**Q: How do you organize Azure resources?**

**A:** "I use Resource Groups as logical containers for related resources. In my digital twin project, I created 'refinery-dt-dev-rg' which contains:
- Container Registry for Docker images
- Storage Account for Terraform state
- AKS cluster for running microservices
- Networking resources

This organization provides several benefits:
- Easy cost tracking per project
- Simple cleanup (delete group = delete everything)
- Logical grouping makes architecture clear
- RBAC can be applied at group level

I also use tags like 'Environment: dev' and 'ManagedBy: Terraform' for additional organization and cost allocation."

---

## Slide 5: Storage Account & Terraform State

### What is Azure Storage Account?

**Definition:** Cloud storage service (like Google Drive/Dropbox)

**Use cases:**
- File storage
- Database backups
- Images/videos
- **Terraform state** ← Our use!

### Why Terraform Needs Storage?

**The Problem:**
```
Day 1: terraform apply
  → Creates Resource Group
  → Terraform: "I created a resource group"

Day 2: terraform apply again
  → Terraform: "Did I create anything? 🤔"
  → Without state: Creates DUPLICATE resource (error!)
```

**The Solution: State File**
```
terraform.tfstate (stored in Storage Account)
{
  "resources": [
    {
      "type": "azurerm_resource_group",
      "name": "main",
      "id": "/subscriptions/.../resourceGroups/refinery-dt-dev-rg"
    }
  ]
}
```

**How it works:**
1. Run `terraform apply`
2. Terraform creates resources
3. Terraform saves "what I created" to `terraform.tfstate`
4. Next run: Terraform reads state file
5. Terraform: "These already exist, I'll update them"

### Storage Account Settings Explained

```hcl
resource "azurerm_storage_account" "tfstate" {
  name                     = "refinerydevtfstate"
  account_tier             = "Standard"        # Regular speed (vs Premium)
  account_replication_type = "LRS"            # 3 copies same datacenter
}
```

**account_tier:**
- **Standard:** Regular speed, cheaper (good for Terraform state)
- **Premium:** SSD-based, faster, expensive (for databases)

**account_replication_type:**
- **LRS:** Locally Redundant (3 copies in same datacenter) - Cheapest
- **GRS:** Geo-Redundant (6 copies across regions) - More expensive
- **ZRS:** Zone-Redundant (3 copies across availability zones)

### Interview Question Answer
**Q: How do you manage Terraform state?**

**A:** "I use Azure Storage Account as a remote backend for Terraform state. Here's why:

**Problem:** If state is local (on my laptop), I face issues:
- Team members can't collaborate (they don't have my state file)
- If my laptop crashes, state is lost
- Can't run Terraform from CI/CD pipelines

**Solution:** Remote state in Azure Storage
- Centralized: Team shares same state
- Secure: Access controlled via Azure RBAC
- Durable: 3 copies (LRS replication)
- Lockable: Prevents concurrent modifications

In my configuration, I use LRS replication and Standard tier because Terraform state files are small (<1MB) and don't need premium performance. The state file tracks all resources Terraform manages, enabling idempotent operations."

---

## Slide 6: Container Registry Explained

### What is Azure Container Registry (ACR)?

**Definition:** Private storage for Docker images

**Analogy:** 
- **Docker Hub** = Public app store (everyone can download)
- **ACR** = Your private app store (only you/your team)

### Why We Need It?

**The Workflow:**
```
1. Developer writes code (Equipment Service in C#)
   ↓
2. Build Docker image: docker build -t equipment:v1
   ↓
3. Push to Container Registry: docker push myregistry.azurecr.io/equipment:v1
   ↓
4. Kubernetes pulls from Registry: kubectl deploy equipment:v1
   ↓
5. Container runs in production
```

**Without Container Registry:**
- Where does Kubernetes get the image?
- How do you share images with team?
- How do you version images?

**With Container Registry:**
- ✅ Centralized image storage
- ✅ Version control (v1, v2, v3)
- ✅ Kubernetes knows where to pull from
- ✅ Private (not public on Docker Hub)

### ACR SKUs Compared

| Feature | Basic | Standard | Premium |
|---------|-------|----------|---------|
| **Price** | $5/month | $20/month | $500/month |
| **Storage** | 10 GB | 100 GB | 500 GB |
| **Webhooks** | 2 | 10 | 500 |
| **Geo-replication** | ❌ | ❌ | ✅ |
| **Best for** | Learning/Dev | Small teams | Enterprise |

**We use Basic** because:
- Cheapest option
- Enough for learning
- 10GB = hundreds of images

### Our Configuration
```hcl
resource "azurerm_container_registry" "acr" {
  name          = "refinerydevacr"
  sku           = "Basic"
  admin_enabled = true  # Allow username/password login
}
```

### Interview Question Answer
**Q: Explain your container registry setup**

**A:** "I use Azure Container Registry as a private Docker image repository for my microservices. Here's my workflow:

1. **Build:** I containerize each microservice (Equipment Service, Sensor Service) using Docker
2. **Push:** Images are pushed to ACR with semantic versioning (equipment:1.0.0)
3. **Deploy:** Kubernetes pulls images from ACR using image pull secrets

I chose Basic SKU because it's cost-effective for a project with ~5 microservices. Each service has 2-3 versions stored, well within the 10GB limit.

I enabled admin access for development simplicity, but in production, I'd use Azure AD integration with RBAC for security.

ACR integrates seamlessly with AKS - the cluster authenticates via managed identity, so no manual credential management needed."

---

## Slide 7: Understanding Docker

### What is Docker?

**Definition:** Platform to package applications in containers

**The Problem Docker Solves:**

**"It works on my machine" syndrome:**
```
Developer's Laptop (Windows):
- .NET 8.0 installed
- SQL Server LocalDB
- Code works perfectly! ✅

Production Server (Linux):
- .NET 6.0 installed
- PostgreSQL database
- Code crashes! ❌ "But it worked on my machine!"
```

**Docker Solution:**
```
Developer creates container with:
- Code
- .NET 8.0 runtime
- All dependencies
- Configuration

Same container runs on:
- Developer's Windows laptop ✅
- Production Linux server ✅
- MacBook ✅
- Cloud (Azure/AWS) ✅

Result: "It works in the container = It works everywhere"
```

### Container vs Virtual Machine

**Virtual Machine (Old way):**
```
Physical Server
├── Hypervisor
├── VM 1: Entire OS + App 1 (4GB RAM)
├── VM 2: Entire OS + App 2 (4GB RAM)
└── VM 3: Entire OS + App 3 (4GB RAM)
Total: 12GB RAM for 3 apps
```

**Container (New way):**
```
Physical Server
├── Docker Engine
├── Container 1: App 1 (100MB)
├── Container 2: App 2 (100MB)
└── Container 3: App 3 (100MB)
Total: 300MB for 3 apps (shares same OS kernel)
```

**Benefits:**
- ✅ Lightweight (MBs vs GBs)
- ✅ Fast startup (seconds vs minutes)
- ✅ Efficient (more apps per server)

### Real-World Analogy

**Shipping Containers:**
```
Before containers:
- Cargo loaded loosely on ships
- Different sizes, shapes
- Hard to transfer between ships/trucks/trains
- Slow loading/unloading

After containers:
- Standard 20ft/40ft containers
- Fits on ships, trucks, trains
- Easy transfer (crane → anywhere)
- Fast loading/unloading

Same with Docker:
- Standard format
- Runs anywhere
- Easy deployment
```

### Interview Question Answer
**Q: Why use Docker for your microservices?**

**A:** "Docker solves the 'works on my machine' problem and enables several enterprise patterns:

**Consistency:** My Equipment Service runs identically on:
- My development Codespace
- CI/CD pipeline
- Staging Kubernetes cluster
- Production AKS

**Efficiency:** Containers are lightweight. My Equipment Service container is ~200MB vs a VM which would be 4GB+. This means:
- Faster deployments
- Lower cloud costs
- More services per node

**Isolation:** Each microservice runs in its own container with:
- Own dependencies (.NET 8 for Equipment, Node.js for Sensor)
- No conflicts between services
- Easy to scale independently

**DevOps Enablement:** Containers make CI/CD trivial:
- Build once (docker build)
- Deploy anywhere (Kubernetes pulls from registry)
- Rollback easily (revert to previous image tag)

In my digital twin platform, I have 5+ microservices all containerized, managed by Kubernetes for orchestration."

---

## Slide 8: Dockerfile Explained - Line by Line

### Multi-Stage Build Pattern

Our Dockerfile uses **two stages**:
1. **Build stage:** Compile code (large image with dev tools)
2. **Runtime stage:** Run app (small image, only runtime)

### Stage 1: Build

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
```
**What it means:** Start with Microsoft's official .NET 8 SDK image
- **SDK** = Software Development Kit (has compilers, build tools)
- **Size:** ~1.5 GB
- **Purpose:** To BUILD code

**Analogy:** Full workshop with all tools to build furniture

---

```dockerfile
WORKDIR /src
```
**What it means:** Create and enter `/src` folder
**Equivalent to:** `mkdir /src && cd /src`

---

```dockerfile
COPY *.csproj ./
RUN dotnet restore
```
**What it means:** 
1. Copy only `.csproj` file (list of NuGet packages)
2. Download all packages

**Why copy .csproj FIRST?**
```
Smart caching optimization:

❌ Bad order:
1. COPY all code
2. RUN dotnet restore
→ Every code change = re-download ALL packages (slow!)

✅ Good order:
1. COPY *.csproj
2. RUN dotnet restore  ← Docker caches this layer
3. COPY all code
→ Code changes don't trigger package re-download (fast!)
```

**Analogy:** 
- Check fridge for milk before going to store
- If milk exists (cached), don't buy again

---

```dockerfile
COPY . ./
RUN dotnet publish -c Release -o /app/publish
```
**What it means:**
1. Copy all remaining code
2. Compile into production-ready DLL files

**Flags explained:**
- `-c Release` = Optimize for production (faster code, smaller size)
- `-o /app/publish` = Output compiled files to `/app/publish`

**Analogy:** 
- Raw ingredients (code) → Cooking (compile) → Ready meal (published app)

---

### Stage 2: Runtime

```dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
```
**What it means:** Start fresh with runtime-only image
- **ASPNET** = Only what's needed to RUN apps (no build tools)
- **Size:** ~200 MB
- **Purpose:** Production deployment

**Why switch images?**
```
Build image (SDK):     1.5 GB  ← Has compilers, debuggers
Runtime image (ASPNET): 200 MB ← Only runtime libraries

Benefit: Ship smaller image to production
         = Faster deployments, less security surface
```

**Analogy:**
- Use full workshop to build furniture
- Ship only the furniture (not the entire workshop!)

---

```dockerfile
COPY --from=build /app/publish .
```
**What it means:** Copy compiled app from build stage to runtime stage

**Multi-stage magic:**
```
Stage 1 (build):
- Uses SDK image (1.5GB)
- Compiles code
- Creates /app/publish folder

Stage 2 (runtime):
- Uses ASPNET image (200MB)
- Copies ONLY /app/publish from Stage 1
- Ignores everything else from Stage 1

Final image size: ~220MB (not 1.5GB!)
```

---

```dockerfile
EXPOSE 80
EXPOSE 443
```
**What it means:** Document that app listens on ports 80 (HTTP) and 443 (HTTPS)

**Note:** This is DOCUMENTATION, not security
- Doesn't actually open ports
- Tells developers/operators: "This app uses these ports"

**Port numbers explained:**
- **80:** Standard HTTP (web traffic)
- **443:** Standard HTTPS (secure web traffic)
- **5000:** Common for ASP.NET Core development

---

```dockerfile
ENTRYPOINT ["dotnet", "EquipmentService.dll"]
```
**What it means:** When container starts, run this command

**Equivalent to:**
```bash
$ dotnet EquipmentService.dll
```

**ENTRYPOINT vs CMD:**
- **ENTRYPOINT:** Command that ALWAYS runs (can't override easily)
- **CMD:** Default command (can be overridden)

For apps, use ENTRYPOINT (more explicit)

### Interview Question Answer
**Q: Explain your Dockerfile**

**A:** "I use a multi-stage Dockerfile following Docker best practices:

**Build Stage:**
- Starts with .NET SDK image (1.5GB) which has all build tools
- Copies .csproj first and runs dotnet restore - this creates a cached layer for NuGet packages
- If I only change code, Docker reuses the cached package layer, speeding up builds significantly
- Compiles application with Release configuration for production optimization

**Runtime Stage:**
- Switches to ASPNET runtime image (200MB) - much smaller as it only includes runtime libraries
- Copies compiled artifacts from build stage
- Final image is ~220MB instead of 1.5GB

**Benefits:**
- Smaller image = faster deployments to Kubernetes
- Reduced attack surface (no build tools in production)
- Faster CI/CD pipeline builds due to layer caching

This pattern is standard in enterprise environments where you want lean, secure production containers."

---

## Slide 9: ASP.NET Core Microservice Architecture

### What is a Microservice?

**Definition:** Small, independent service that does ONE thing well

**Monolith vs Microservices:**

**Monolith (Old way):**
```
Single Application:
├── Equipment Module
├── Sensor Module
├── Analytics Module
├── User Module
└── All in one codebase

Problems:
❌ Deploy all or nothing
❌ One bug crashes everything
❌ Hard to scale parts independently
❌ Team conflicts in same codebase
```

**Microservices (Modern way):**
```
Equipment Service (C# .NET)
Sensor Service (Node.js)
Analytics Service (Python)
User Service (Go)

Benefits:
✅ Deploy independently
✅ One service fails, others continue
✅ Scale only what's needed
✅ Teams own services independently
✅ Different tech stacks for different needs
```

### Our Equipment Service Architecture

```
EquipmentService/
├── Controllers/
│   └── EquipmentController.cs   ← HTTP endpoints (REST API)
├── Models/
│   └── Equipment.cs              ← Data structure
├── Program.cs                    ← App startup & configuration
└── appsettings.json              ← Configuration
```

### Model-View-Controller (MVC) Pattern

**Equipment Model:**
```csharp
public class Equipment
{
    public int Id { get; set; }
    public string TagNumber { get; set; }
    public string Name { get; set; }
    public string Type { get; set; }
    // Represents data structure
}
```

**Equipment Controller:**
```csharp
[ApiController]
[Route("api/[controller]")]
public class EquipmentController : ControllerBase
{
    [HttpGet]
    public ActionResult<IEnumerable<Equipment>> GetAll()
    {
        // Handles HTTP GET /api/equipment
        return Ok(equipmentList);
    }
}
```

**Responsibility separation:**
- **Model:** Data structure (what equipment looks like)
- **Controller:** HTTP handling (how to get/create equipment)
- **Service (future):** Business logic (rules and validations)

### RESTful API Design

**REST** = Representational State Transfer

**Our endpoints:**
```
GET    /api/equipment       → Get all equipment
GET    /api/equipment/1     → Get equipment #1
POST   /api/equipment       → Create new equipment
PUT    /api/equipment/1     → Update equipment #1
DELETE /api/equipment/1     → Delete equipment #1
```

**HTTP Methods = Actions:**
- **GET:** Read (safe, no changes)
- **POST:** Create (new resource)
- **PUT:** Update (replace existing)
- **DELETE:** Remove

**Status Codes:**
- **200 OK:** Success
- **201 Created:** Successfully created
- **404 Not Found:** Resource doesn't exist
- **400 Bad Request:** Invalid input

### Dependency Injection in ASP.NET Core

**What is Dependency Injection?**

**Without DI (Bad):**
```csharp
public class EquipmentController
{
    private EquipmentService _service = new EquipmentService();
    // Controller creates its own dependencies
    // Hard to test, tightly coupled
}
```

**With DI (Good):**
```csharp
public class EquipmentController
{
    private readonly IEquipmentService _service;
    
    public EquipmentController(IEquipmentService service)
    {
        _service = service;  // Injected by framework
        // Easy to test (inject mock), loosely coupled
    }
}
```

**Benefits:**
- Easy testing (inject fake service for tests)
- Loose coupling (swap implementations)
- Framework manages object lifetime

### Interview Question Answer
**Q: Explain your microservice architecture**

**A:** "My Equipment Service follows enterprise microservice patterns:

**Architecture Decisions:**
1. **Single Responsibility:** Equipment Service ONLY manages equipment data. Sensor data is in a separate service. This enables:
   - Independent scaling (scale equipment service without affecting sensors)
   - Team autonomy (different teams can own different services)
   - Technology flexibility (Equipment in C#, Sensors could be Node.js)

2. **RESTful API Design:** I follow REST conventions:
   - HTTP methods map to CRUD (GET=Read, POST=Create, PUT=Update, DELETE=Delete)
   - Resource-based URLs (/api/equipment/{id})
   - Proper status codes (200, 201, 404, 400)
   - Stateless operations

3. **Dependency Injection:** ASP.NET Core's built-in DI container manages dependencies:
   - Services registered in Program.cs
   - Injected into controllers via constructor
   - Enables testing (inject mocks) and loose coupling

4. **API Documentation:** Swagger/OpenAPI auto-generates documentation:
   - Developers can explore API interactively
   - Auto-updated when code changes
   - Provides client code generation

**Future Enhancements:** Currently using in-memory storage, will add:
- Entity Framework Core with PostgreSQL
- CQRS pattern for complex operations
- Event-driven communication with Kafka"

---

## Slide 10: Common Mistakes & How to Avoid Them

### Mistake 1: Not Using .gitignore

**Problem:**
```
❌ Commits secrets to Git:
git add .
git commit -m "add code"
# Accidentally commits appsettings.json with passwords!
# Now passwords are in Git history FOREVER
```

**Solution:**
```
✅ Use .gitignore:
bin/
obj/
*.user
appsettings.Development.json  ← Don't commit secrets
terraform.tfstate              ← State has sensitive data
.env                           ← Environment variables
```

**How to fix if you already committed secrets:**
1. Change the passwords immediately
2. Use `git filter-branch` to remove from history
3. Better: Use Azure Key Vault for secrets

---

### Mistake 2: Hardcoding Configuration

**Problem:**
```csharp
❌ Bad:
public class EquipmentController
{
    private string _connectionString = "Server=prod-db;User=admin;Password=secret123";
    // Hardcoded! Can't change without recompiling
}
```

**Solution:**
```csharp
✅ Good:
// appsettings.json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=..."
  }
}

// Code
public class EquipmentController
{
    private readonly IConfiguration _config;
    
    public EquipmentController(IConfiguration config)
    {
        _config = config;
        var connString = _config.GetConnectionString("DefaultConnection");
    }
}
```

**Better: Use Azure App Configuration or Key Vault**

---

### Mistake 3: Not Reading Error Messages

**Problem:**
```
❌ Developer sees error:
"Error: Storage account name must be between 3 and 24 characters"

Developer: *immediately asks for help*
```

**Solution:**
```
✅ Developer reads error:
"Storage account name must be between 3 and 24 characters"

Developer: "Oh, my name 'my-very-long-storage-account-name' is 33 characters"
Developer: Changes to 'mystorageacct' (13 characters)
Developer: Runs again → Works!
```

**Most errors tell you exactly what's wrong!**

---

### Mistake 4: Running Terraform Apply Without Plan

**Problem:**
```
❌ Dangerous:
terraform apply
# No preview! What if it deletes production database?
```

**Solution:**
```
✅ Safe workflow:
terraform plan        # Review changes first
# Check output carefully:
# - 5 to add
# - 0 to change  
# - 0 to destroy ← GOOD! Nothing being deleted
terraform apply       # Now execute
```

**In production: Require approval between plan and apply**

---

### Mistake 5: Mixing Manual Changes with Terraform

**Problem:**
```
1. Create resource with Terraform
2. Go to Azure Portal
3. Manually change something
4. Run terraform apply again
5. Terraform: "State doesn't match reality!" 😕
6. Terraform overwrites your manual change
```

**Solution:**
```
✅ Rule: If using Terraform, ONLY change via Terraform
- Don't mix manual + IaC
- All changes go through code
- Manual changes get overwritten
```

**Exception:** Debugging in dev environment is OK (but document it!)

---

### Mistake 6: Not Using Semantic Versioning for Containers

**Problem:**
```
❌ Bad tagging:
docker build -t equipment:latest
docker build -t equipment:latest  ← Overwrites previous!
# Can't rollback, don't know what version is deployed
```

**Solution:**
```
✅ Semantic versioning:
docker build -t equipment:1.0.0
docker build -t equipment:1.0.1
docker build -t equipment:1.1.0
# Clear versions, can rollback to 1.0.0 if 1.1.0 breaks
```

**Format:** MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

---

### Mistake 7: Not Using Health Checks

**Problem:**
```
❌ Container starts but app crashes after 30 seconds
Kubernetes thinks: "Container running = healthy"
Keeps sending traffic to broken container
```

**Solution:**
```csharp
✅ Add health check endpoint:
[HttpGet("/health")]
public IActionResult Health()
{
    // Check database connection
    // Check dependencies
    return Ok("Healthy");
}
```

```yaml
# Kubernetes config
livenessProbe:
  httpGet:
    path: /health
    port: 80
  periodSeconds: 10
```

**Kubernetes will restart unhealthy containers**

---

### Interview Question Answer
**Q: What mistakes did you encounter and how did you solve them?**

**A:** "I encountered several common mistakes that taught me important lessons:

**1. State Management:**
Initially ran Terraform without remote state. When I switched computers, Terraform lost track of resources and tried to recreate them. I fixed this by:
- Configuring Azure Storage as remote backend
- Enabling state locking to prevent concurrent modifications
- Now team members share the same state

**2. Container Versioning:**
Started using 'latest' tag for Docker images. When a deployment failed, I couldn't rollback because I didn't know which version was working. I adopted semantic versioning:
- Major.Minor.Patch (e.g., 1.2.3)
- Tag each build with Git commit SHA
- Can easily rollback to specific versions

**3. Configuration Management:**
Hardcoded database connection in code initially. When moving to staging, had to recompile. I refactored to use:
- appsettings.json for configuration
- Environment variables for secrets
- Azure Key Vault in production
- Now can deploy same container to any environment

**4. Error Handling:**
Terraform errors seemed cryptic at first, but I learned to:
- Read the entire error message carefully
- Most errors explicitly state the problem
- Google the exact error message
- Check Azure resource naming rules

These mistakes taught me the importance of following infrastructure and DevOps best practices from the start."

---

## Slide 11: Key Takeaways - Day 1

### What We Built Today

✅ **Infrastructure as Code**
- Terraform configuration for Azure
- Resource Group, Storage Account, Container Registry
- Repeatable, version-controlled infrastructure

✅ **Microservice**
- Equipment Service in ASP.NET Core
- RESTful API with CRUD operations
- Swagger documentation

✅ **Containerization**
- Multi-stage Dockerfile
- Optimized image (~220MB)
- Production-ready container

✅ **Version Control**
- Everything in Git
- Proper .gitignore
- Commit history for tracking

### Technologies Demonstrated

**Infrastructure:**
- Terraform (IaC)
- Azure Cloud Platform
- Resource Groups
- Container Registry

**Development:**
- C# .NET 8
- ASP.NET Core Web API
- REST API design
- Dependency Injection

**DevOps:**
- Docker (containerization)
- Multi-stage builds
- Git version control
- VS Code Codespaces

### Tomorrow's Plan (Day 2)

**Add Kubernetes:**
- Azure Kubernetes Service (AKS) cluster
- Deploy Equipment Service to AKS
- Kubernetes concepts (Pods, Deployments, Services)

**Add CI/CD:**
- GitHub Actions workflow
- Automated build on push
- Automated deployment to AKS

**Expected deliverable:**
- Live Kubernetes cluster
- Equipment API running in AKS
- Automated pipeline working

### Interview Preparation Tips

**Be ready to explain:**
1. Why Infrastructure as Code? (consistency, version control, repeatability)
2. Terraform workflow (init → plan → apply)
3. Why containers? (consistency across environments)
4. Why Kubernetes? (orchestration, scaling, self-healing)
5. Your microservice design choices

**Practice:**
- Draw your architecture on whiteboard
- Explain each component's purpose
- Walk through deployment process
- Discuss trade-offs and alternatives

**GitHub Portfolio:**
- Make README.md detailed
- Add architecture diagrams
- Document each service
- Include getting started guide

### Enterprise Patterns Demonstrated

**Infrastructure:**
- ✅ Infrastructure as Code (Terraform)
- ✅ Remote state management
- ✅ Resource tagging for organization

**Application:**
- ✅ Microservice architecture
- ✅ RESTful API design
- ✅ Dependency Injection
- ✅ Configuration management

**DevOps:**
- ✅ Containerization
- ✅ Multi-stage Docker builds
- ✅ Version control
- ✅ Documentation (Swagger)

**Next to add:**
- Kubernetes orchestration
- CI/CD automation
- Monitoring & logging
- Database persistence

---

## Additional Resources for Further Learning

### Official Documentation
- Terraform Azure Provider: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
- ASP.NET Core: https://docs.microsoft.com/aspnet/core
- Docker: https://docs.docker.com
- Azure: https://docs.microsoft.com/azure

### Free Learning Resources
- Microsoft Learn (Azure): https://learn.microsoft.com/training/azure
- Terraform tutorials: https://learn.hashicorp.com/terraform
- Docker tutorials: https://docs.docker.com/get-started

### Best Practices
- 12-Factor App: https://12factor.net
- REST API Guidelines: https://docs.microsoft.com/azure/architecture/best-practices/api-design
- Terraform Best Practices: https://www.terraform-best-practices.com

### Interview Preparation
- System Design Primer: https://github.com/donnemartin/system-design-primer
- Cloud Native Patterns: https://www.manning.com/books/cloud-native-patterns
- Microservices Patterns: https://microservices.io/patterns

---

## End of Day 1 Interview Prep Guide

**Remember:** 
- This is YOUR brain's "storage account" 
- Review before interviews
- Practice explaining concepts out loud
- Draw diagrams to solidify understanding
- Each day builds on previous days

**Next:** Day 2 - Kubernetes & CI/CD preparation
