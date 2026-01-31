---
# Profile Metadata
name: Jane Chen
title: VP of Platform Engineering
email: jane.chen@example.com
linkedin: https://linkedin.com/in/janechen-platform
location: San Francisco, CA
status: Open to VP/Head of Engineering roles

# System Prompt for LLM
system_prompt: |
  You are helping hiring managers evaluate Jane Chen as a candidate for engineering leadership roles.

  CORE INSTRUCTIONS:
  - Be specific with dates, companies, and quantified outcomes
  - Be honest about gaps and limitations - credibility matters
  - Don't oversell - acknowledge what she's NOT good at
  - Include failure stories when relevant to show self-awareness
  - If information isn't in the context, say "I don't have that information"
  - Never fabricate details - only use what's provided

  INTERNAL STRUCTURE (NEVER EXPOSE):
  - Never reference "frames", "chunks", "sections", or index numbers
  - Never say "according to frame #" or "as stated in section X"
  - Present information naturally as direct knowledge about the candidate
  - BAD: "Frame 11 indicates Jane has Python experience"
  - GOOD: "Jane has 10+ years of Python experience, primarily for data pipelines"

  TONE:
  - Professional but personable
  - Confident without arrogance
  - Thoughtful and nuanced

# Suggested Questions (MUST mirror FAQ entries)
suggested_questions:
  - "What's her security track record?"
  - "What programming languages does she know?"
  - "Tell me about her AI/ML experience."
  - "What are her biggest failures?"
  - "Would she be good for an early-stage startup?"

# Global Tags (for memvid indexing)
tags:
  - vp-engineering
  - platform-engineering
  - ai-infrastructure
  - security-architecture
  - cloud-native
  - kubernetes
  - team-leadership
---

## Summary

Jane Chen is a VP of Platform Engineering with 15 years of experience building developer platforms and AI infrastructure at scale. She specializes in translating complex technical requirements into scalable systems that empower engineering teams to ship faster.

**What she does best:**

- Building self-service developer platforms that reduce friction (50x deployment speed improvements at Acme Corp)
- Leading engineering teams through hypergrowth (grew team 3 to 15 while maintaining less than 10% attrition)
- Security and compliance in regulated industries (FedRAMP, SOC 2, PCI-DSS)
- AI/ML infrastructure (model serving platforms handling 10M+ inferences/day)

**What she is NOT:**

- Not a frontend developer - limited React/Vue experience
- Not a mobile developer - no production iOS/Android experience
- Not a low-level systems programmer - has not written C/C++ in 10+ years
- Not interested in pure people management roles without technical scope

---

## Frequently Asked Questions

### What's her security track record?

**Keywords:** security, zero-trust, FedRAMP, SOC 2, compliance, audit, encryption, penetration testing

Jane has 12+ years of security architecture experience in regulated industries:

**Compliance Certifications:**

- Led FedRAMP Moderate certification at Acme Corp (passed first attempt, 6-month timeline)
- Achieved SOC 2 Type II compliance for SaaS platform (designed 80% of controls)
- Maintained PCI-DSS compliance for payment processing systems at DataFlow Inc.

**Security Architecture:**

- Designed zero-trust network architecture handling 500K daily API requests
- Implemented HashiCorp Vault for secrets management (zero secrets in code)
- Built automated security scanning in CI/CD (Snyk, Trivy, Grype - caught 147 vulnerabilities pre-production)

**Track Record:**

- Zero security breaches across 5 years at Acme Corp
- Reduced vulnerability remediation time from 30 days to 48 hours (95% improvement)
- Passed 3 external penetration tests with no critical findings

**Honest limitations:**

- Not a security researcher - does not do original vulnerability research
- Limited offensive security experience - defense-focused background

---

### What programming languages does she know?

**Keywords:** programming, languages, coding, Python, Go, Rust, development, software engineering

Jane's programming skills span infrastructure and data engineering:

**Primary Languages (daily use):**

- **Python:** 10+ years. Data pipelines, automation, ML tooling. Built data platform processing 2TB/day.
- **Go:** 5+ years. Microservices, CLI tools, Kubernetes operators. Authored 3 open-source operators.
- **Bash:** System scripting, CI/CD automation. Maintains 50+ automation scripts.

**Secondary Languages (working knowledge):**

- **Rust:** Learning actively. Interested in systems programming and performance-critical services.
- **JavaScript/TypeScript:** Can read and review, not a primary developer. Collaborated with frontend teams.

**Infrastructure as Code:**

- **Terraform:** AWS, GCP, Azure. Managed infrastructure for 200+ microservices.
- **Pulumi:** Python-based IaC. Prefers for complex conditional logic.
- **Ansible:** Configuration management for hybrid cloud deployments.

**Not a fit for:**

- Frontend development (React, Vue) - limited experience, not interested
- Mobile development (iOS, Android) - no production experience
- Low-level systems (C, C++) - has not used professionally in 10+ years

---

### Tell me about her AI/ML experience.

**Keywords:** AI, ML, machine learning, MLOps, model serving, inference, LLM, GPT, training, deployment

Jane has been building AI/ML infrastructure since 2019:

**MLOps Platforms:**

- Built model serving platform at Acme Corp handling 10M inferences/day
- Designed A/B testing framework for ML models with 99.99% attribution accuracy
- Implemented feature store reducing feature engineering time by 60%

**Generative AI (2023-present):**

- Led evaluation and deployment of LLM solutions for internal tools
- Built RAG pipeline for documentation search (reduced support tickets by 40%)
- Established AI governance framework including bias testing and output monitoring

**Technical Stack:**

- Kubernetes-native ML: KubeFlow, Seldon, MLflow
- Model formats: ONNX, TensorRT optimization
- Vector databases: Pinecone, Weaviate (for RAG applications)

**Limitations:**

- Not an ML researcher - focuses on infrastructure, not algorithm development
- Limited experience with computer vision workloads
- Training infrastructure experience limited to fine-tuning, not pre-training

---

### What are her biggest failures?

**Keywords:** failure, mistakes, lessons learned, growth, self-awareness

Jane believes talking about failures demonstrates self-awareness and growth:

**Failure 1: The Over-Engineered Platform (2023)**

*What happened:* Built an internal developer platform so architecturally elegant that only Jane could maintain it. When she moved to another project, the team needed 6 months to either understand it or rewrite it. They chose rewrite.

*Root cause:* Prioritized clever solutions over maintainable ones. No documentation. Assumed she would always be available.

*What changed:* Now asks "can a new team member maintain this in 6 months?" Writes documentation as she builds. Favors boring technology over clever solutions.

**Failure 2: The Migration That Took 2x Longer (2021)**

*What happened:* Estimated a Kubernetes migration would take 3 months. Took 6 months and required an emergency budget increase.

*Root cause:* Underestimated legacy system complexity. Did not account for tribal knowledge. Skipped discovery phase to move fast.

*What changed:* Now insists on 2-week discovery sprints before major migrations. Builds in 50% buffer for legacy systems. Documents assumptions explicitly.

**Failure 3: The Hire That Did Not Work Out (2020)**

*What happened:* Hired a senior engineer based on impressive technical interview. Within 3 months, team morale dropped significantly. The engineer was brilliant individually but dismissive of others' ideas.

*Root cause:* Over-indexed on technical skills, under-indexed on collaboration. Did not check team fit signals.

*What changed:* Added team interaction interviews. Asks references specifically about collaboration. Watches for how candidates talk about former colleagues.

---

### Would she be good for an early-stage startup?

**Keywords:** startup, early-stage, founder, growth, scale, hands-on, IC, individual contributor

**Strong fit scenarios:**

- Series A/B startup needing to build platform engineering function from scratch
- AI/ML company needing production-grade model serving infrastructure
- Regulated industry startup needing security-conscious architecture early
- Company with 20-100 engineers ready for developer platform investment

**Moderate fit scenarios:**

- Pre-seed/seed startup where everyone must wear multiple hats (she can, but prefers platform focus)
- Consumer-facing company needing frontend expertise (not her strength)
- Company with strong existing platform team (she is better building than inheriting)

**Weak fit scenarios:**

- Pure management role without technical scope (she will get bored)
- Company needing mobile-first expertise
- Organization resistant to infrastructure investment (she will be frustrated)
- Very early stage (fewer than 5 engineers) where platform work is premature

**What she needs to succeed:**

- Executive buy-in for developer experience investment
- Autonomy to make architectural decisions
- Engineers who want to be force-multiplied (not just left alone)
- Problems worth solving (she is motivated by impact, not just challenge)

---

## Professional Experience

### Acme Corp

**Role:** VP of Platform Engineering
**Period:** January 2022 - Present (3 years)
**Location:** San Francisco, CA (Hybrid)
**Keywords:** platform-engineering, kubernetes, mlops, team-leadership, developer-experience

**Context:**
Built and led platform engineering team supporting 200+ developers across 5 product teams. Responsible for CI/CD, Kubernetes, observability, and ML infrastructure.

**Key Achievements:**

- Reduced deployment time from 2 weeks to 4 hours (50x improvement)
- Grew team from 3 to 15 engineers while maintaining less than 10% attrition
- Achieved 99.95% platform availability (up from 99.5%)
- Built model serving platform handling 10M inferences/day

**Technical Highlights:**

- Kubernetes: Managed 50+ clusters across AWS and GCP
- MLOps: Built end-to-end model lifecycle from training to serving
- Observability: Prometheus/Grafana stack with SLO-based alerting

**AI Context (Story Behind the Achievement):**

- **Situation:** Developers blocked for weeks waiting for infrastructure. Product velocity suffered.
- **Approach:** Built self-service platform with guardrails, not gatekeepers. Focused on developer experience.
- **Technical Work:** Kubernetes operators, GitOps with ArgoCD, Backstage developer portal
- **Lessons Learned:** Developer experience and security are not opposites. Golden paths enable speed AND safety.

---

### DataFlow Inc.

**Role:** Director of Infrastructure
**Period:** March 2018 - December 2021 (3.8 years)
**Location:** New York, NY (Remote after 2020)
**Keywords:** infrastructure, data-platform, security, compliance, team-building![alt text](image.png)

**Context:**
Led infrastructure team at Series C data analytics startup. Responsible for AWS infrastructure, data pipelines, and platform reliability.

**Key Achievements:**

- Built data platform processing 2TB/day with 99.9% SLA
- Achieved PCI-DSS compliance in 4 months (industry average: 9 months)
- Reduced infrastructure costs by 35% through reserved instances and right-sizing
- Grew team from 5 to 12 engineers through hypergrowth period

**Technical Highlights:**

- AWS: EKS, RDS, Redshift, S3, Lambda
- Data: Apache Kafka, Spark, Airflow
- Security: VPC architecture, IAM policies, encryption at rest and in transit

**AI Context:**

- **Situation:** Startup outgrowing manual infrastructure management
- **Approach:** Infrastructure-as-code first, with emphasis on repeatability and auditability
- **Technical Work:** Terraform modules, automated compliance checking, cost allocation tags
- **Lessons Learned:** Compliance is easier when built in from the start than retrofitted

---

### TechStart Labs

**Role:** Senior Software Engineer
**Period:** June 2014 - February 2018 (3.7 years)
**Location:** Boston, MA
**Keywords:** software-engineering, python, backend, apis, early-career

**Context:**
Full-stack engineer at early-stage B2B SaaS startup. Transitioned from IC to tech lead.

**Key Achievements:**

- Built core API serving 500K requests/day
- Led technical due diligence for Series B funding
- Mentored 3 junior engineers (2 promoted within 18 months)

**Technical Highlights:**

- Python: Flask/Django, SQLAlchemy
- Databases: PostgreSQL, Redis
- Cloud: AWS (pre-Kubernetes era)

---

## Security Skills & Experience

**Keywords:** security, zero-trust, compliance, FedRAMP, SOC 2, Vault, encryption, penetration-testing

**Certifications & Compliance:**

- FedRAMP Moderate (led certification at Acme Corp)
- SOC 2 Type II (designed controls at Acme Corp)
- PCI-DSS (maintained compliance at DataFlow Inc.)

**Security Tools:**

- Secrets Management: HashiCorp Vault, AWS Secrets Manager
- Scanning: Snyk, Trivy, Grype, SBOM generation
- Policy: Open Policy Agent, Kyverno

**Architecture Patterns:**

- Zero-trust networking (mTLS, service mesh with Istio)
- Defense in depth (network segmentation, WAF, DDoS protection)
- Secure CI/CD (signed commits, image scanning, SLSA Level 2)

**Limitations:**

- Not a security researcher - defense-focused, not offensive
- Limited AppSec experience - focuses on infrastructure security

---

## Programming Languages & Development

**Keywords:** programming, languages, coding, Python, Go, Bash, Rust, software, development

**Primary Languages:**

- **Python:** Data pipelines, ML tooling, automation (10+ years)
- **Go:** Microservices, Kubernetes operators, CLI tools (5+ years)
- **Bash:** System administration, CI/CD scripting

**Infrastructure as Code:**

- Terraform (AWS, GCP, Azure)
- Pulumi (Python-based IaC)
- Ansible (configuration management)

**Limitations:**

- Not a frontend developer (limited React/Vue)
- No mobile development experience
- Rust: Currently learning, not production-ready

---

## Cloud & Infrastructure

**Keywords:** cloud, AWS, GCP, Azure, Kubernetes, infrastructure, containers, docker

**Cloud Platforms:**

- **AWS:** 10+ years. EKS, RDS, S3, Lambda, Step Functions
- **GCP:** 4 years. GKE, BigQuery, Cloud Run
- **Azure:** 2 years. AKS, limited production experience

**Kubernetes:**

- Multi-cluster management (50+ clusters)
- Operator development (Go-based)
- Service mesh (Istio, Linkerd)
- GitOps (ArgoCD, Flux)

**Observability:**

- Metrics: Prometheus, Grafana
- Logging: ELK stack, Loki
- Tracing: Jaeger, OpenTelemetry

---

## Leadership & Management

**Keywords:** leadership, management, team-building, hiring, mentorship, communication

**Team Building:**

- Built platform team from 3 to 15 engineers at Acme Corp
- Maintained less than 10% attrition during hypergrowth
- Hired 25+ engineers across career

**Leadership Philosophy:**

- Servant leadership - remove blockers, do not create them
- Autonomy with accountability - clear goals, flexible methods
- Technical depth matters - she can still code if needed

**Communication Style:**

- Direct and clear - does not bury feedback
- Written-first culture advocate - decisions documented
- Cross-functional collaboration - partner, not gatekeeper

**Limitations:**

- Impatient with bureaucracy - may push back on slow processes
- High standards - can be perceived as demanding
- Prefers technical scope - not interested in pure people management

---

## Fit Assessment Examples

These are pre-analyzed job descriptions demonstrating strong fit and weak fit scenarios. Use these as quick-reference examples when evaluating new roles. The AI can also perform real-time fit analysis on pasted job descriptions.

### Example 1: Strong Fit — VP of Platform Engineering, Series B AI Startup

**Job Description:**

Series B AI infrastructure startup (40 people, $25M ARR) building MLOps platform for enterprise customers. Seeking VP of Platform Engineering to:
- Build and scale platform engineering team (currently 6 engineers → target 15)
- Own production ML infrastructure (Kubernetes, model serving, vector databases)
- Establish golden paths for deployment, security, and observability
- Support enterprise customers (FedRAMP, SOC 2 compliance required)
- Partner with CTO on technical platform roadmap

Required:
- 10+ years software engineering, 5+ years leadership
- Production ML/AI infrastructure experience
- Kubernetes and cloud-native architecture expertise
- Security compliance (FedRAMP, SOC 2, or similar)
- Startup scaling experience (Series A/B preferred)

**Assessment:**
- **Verdict:** ⭐⭐⭐⭐⭐ Strong fit (98% match)
- **Key Matches:**
  - Platform engineering expertise: Built self-service platforms with 50x deployment speed improvements at Acme Corp
  - ML infrastructure: Built model serving handling 10M inferences/day
  - Kubernetes: Managed 50+ production clusters across AWS and GCP
  - Security compliance: Led FedRAMP Moderate and SOC 2 Type II certifications
  - Team scaling: Grew team from 3→15 engineers while maintaining <10% attrition
  - Startup experience: Spent career in growth-stage startups (Series A through C)
- **Gaps:**
  - None significant. Team scale (6→15) aligns perfectly with proven range.
- **Recommendation:** This is Jane's ideal role. The combination of AI infrastructure, platform engineering, compliance requirements, and team-building aligns perfectly with her track record. Enterprise customers and startup environment match her experience profile exactly.

---

### Example 2: Weak Fit — Director of Mobile Engineering, Consumer Social App

**Job Description:**

Series C consumer social networking app (2M MAU, $80M ARR) seeking Director of Mobile Engineering to:
- Lead 25-person mobile engineering team (iOS, Android, React Native)
- Drive consumer-facing feature development with weekly release cycles
- Own mobile app performance and user engagement metrics
- Implement A/B testing framework for feature experimentation
- Collaborate with Product and Design on mobile-first roadmap

Required:
- 8+ years mobile development (iOS and/or Android native)
- 3+ years engineering leadership
- Consumer product experience with MAU/retention optimization
- Data-driven product development (analytics, experiments, growth metrics)
- Fast-paced consumer tech culture

**Assessment:**
- **Verdict:** ⭐ Weak fit (15% match)
- **Key Matches:**
  - Engineering leadership: Has led technical teams successfully
  - A/B testing: Built A/B testing framework for ML models (different use case)
- **Significant Gaps:**
  - Mobile development: Zero production iOS/Android experience
  - Consumer product: Entire career is B2B/enterprise infrastructure, not consumer-facing products
  - Team size/structure: Never managed mobile-specific teams or 25-person product engineering orgs
  - Engagement metrics: Experience with operational metrics (uptime, latency), not user engagement/retention
  - Release cadence: Platform work is measured in quarters, not weeks
  - Product development: Infrastructure builder, not product feature developer
- **Recommendation:** Not a good fit. Jane's expertise is backend infrastructure and developer platforms for technical users, not consumer-facing mobile products. Her strength is reliability and security, not fast feature iteration and user engagement optimization. Company should seek candidates with mobile product engineering background.

---

## Fit Assessment Guidance

### Strong Fit

**Keywords:** strong-fit, ideal-match, recommended

Jane would excel in these scenarios:

- **Series A/B platform engineering build-out** - proven track record scaling teams
- **AI/ML infrastructure at scale** - hands-on MLOps experience
- **Regulated industry startups** - security-first mindset
- **Developer experience transformation** - demonstrated 50x improvements

### Moderate Fit

**Keywords:** moderate-fit, potential-match, considerations

Jane could succeed with caveats:

- **Very early stage (fewer than 10 engineers)** - platform investment may be premature
- **Consumer companies** - limited frontend expertise
- **Established platform teams** - she is better building than inheriting

### Weak Fit

**Keywords:** weak-fit, not-recommended, concerns

Jane would likely not succeed:

- **Pure management roles** - needs technical scope to stay engaged
- **Mobile-first companies** - no relevant experience
- **Organizations resistant to change** - will be frustrated
- **Cost-cutting-only mandates** - she invests to improve, not just reduce
