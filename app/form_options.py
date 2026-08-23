"""Dropdown and multi-select options for intake, objectives, and application forms."""

INDUSTRY_OPTIONS = [
    "Financial services / banking",
    "Healthcare",
    "Healthcare SaaS",
    "E-commerce / retail",
    "SaaS / technology",
    "Manufacturing",
    "Government / public sector",
    "Education",
    "Media / entertainment",
    "Telecommunications",
    "Other",
]

ENGINEERING_SIZE_OPTIONS = [
    "1-10 engineers",
    "11-50 engineers",
    "51-200 engineers",
    "200+ engineers",
]

COUNTRY_OPTIONS = [
    "United States",
    "European Union",
    "United Kingdom",
    "Canada",
    "Australia",
    "Asia-Pacific",
    "Latin America",
    "Middle East & Africa",
    "Global (multi-region)",
    "Other",
]

COMPLIANCE_OPTIONS = [
    "SOC 2",
    "ISO 27001",
    "PCI DSS",
    "HIPAA",
    "NIST",
    "GDPR",
    "Internal controls only",
    "None identified",
]

TOOLING_OPTIONS = [
    "Semgrep",
    "SonarQube",
    "CodeQL",
    "Snyk",
    "GitHub Advanced Security",
    "GitHub Actions",
    "GitLab CI",
    "Jenkins",
    "ArgoCD",
    "Kubernetes",
    "Datadog",
    "Sentry",
    "Trivy",
    "Gitleaks",
    "None",
    "Other",
]

RISK_TOLERANCE_OPTIONS = [
    "Move fast, accept higher risk",
    "Balanced risk and velocity",
    "Conservative, regulated environment",
    "Zero tolerance for production incidents",
]

PRIMARY_GOAL_OPTIONS = [
    "Establish a debt baseline",
    "Reduce vulnerabilities",
    "Prepare for audit",
    "Modernize legacy application",
    "Evaluate acquisition target",
    "Improve engineering velocity",
    "Establish release gates",
    "Continuous monitoring",
]

REPORT_AUDIENCE_OPTIONS = [
    "CTO / engineering leadership",
    "Security team",
    "Developers",
    "Compliance / audit",
    "Board or executives",
    "External auditors",
]

RELEASE_BLOCKER_OPTIONS = [
    "Critical security",
    "High security",
    "Critical quality/debt",
    "High quality/debt",
    "None — advisory only",
]

ASSESSMENT_FREQUENCY_OPTIONS = [
    "Continuous (every commit)",
    "Daily",
    "Weekly",
    "Bi-weekly",
    "Monthly",
    "Quarterly",
    "Ad hoc / on-demand",
    "Annual",
]

REMEDIATION_CAPACITY_OPTIONS = [
    "No dedicated capacity",
    "1 engineer part-time",
    "1 engineer full-time",
    "2-3 engineers part-time",
    "Dedicated team (4+ engineers)",
    "External consultants",
]

PRODUCTION_STATUS_OPTIONS = [
    "Production",
    "Pre-production / staging only",
    "Development",
    "Deprecated / sunset planned",
    "Retired",
]

EXPOSURE_OPTIONS = [
    "Internet-facing public API or web app",
    "Partner or B2B integration",
    "Internal only",
    "Air-gapped or isolated",
]

CRITICALITY_OPTIONS = [
    "Critical — revenue or safety impact",
    "High — significant user impact",
    "Medium — internal operations",
    "Low — experimental or internal tool",
]

DATA_CLASS_OPTIONS = [
    "PII",
    "Payment data",
    "Health data",
    "Credentials / secrets",
    "Financial records",
    "None sensitive",
]

USER_COUNT_OPTIONS = [
    "Under 100",
    "100 - 1,000",
    "1,000 - 10,000",
    "10,000 - 100,000",
    "100,000+",
    "Unknown",
]


def split_multi_value(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]
