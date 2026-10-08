import requests
import time
import re

RAILWAY_GRAPHQL = "https://backboard.railway.app/graphql/v2"

def clean_repo(url_or_name: str) -> str:
    """تبدیل انواع آدرس گیت‌هاب به فرمت owner/repo"""
    text = url_or_name.strip()
    text = re.sub(r'^https?://github\.com/', '', text)
    text = re.sub(r'\.git$', '', text)
    return text.strip('/')

def execute_query(token: str, query: str, variables: dict = None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(
        RAILWAY_GRAPHQL,
        json={"query": query, "variables": variables or {}},
        headers=headers,
        timeout=30
    )
    if resp.status_code != 200:
        raise Exception(f"خطای ارتباط با سرور Railway: کد {resp.status_code}")
    data = resp.json()
    if "errors" in data and data["errors"]:
        error_msg = data["errors"][0].get("message", "خطای ناشناخته در Railway")
        raise Exception(error_msg)
    return data.get("data", {})

def check_token(token: str):
    """بررسی اعتبار توکن کاربر"""
    query = """
    query {
        me {
            id
            email
            name
        }
    }
    """
    data = execute_query(token, query)
    return data.get("me")

def deploy_panel_flow(token: str, project_name: str, github_repo: str):
    """فرآیند کامل ساخت پروژه، اتصال به گیت‌هاب و دریافت دامنه"""
    repo = clean_repo(github_repo)

    # ۱. ساخت پروژه
    create_proj_query = """
    mutation CreateProject($name: String!) {
        projectCreate(input: { name: $name }) {
            id
            name
            environments {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
    }
    """
    proj_data = execute_query(token, create_proj_query, {"name": project_name})
    project = proj_data["projectCreate"]
    project_id = project["id"]
    environment_id = project["environments"]["edges"][0]["node"]["id"]

    # ۲. ساخت سرویس متصل به ریپازیتوری
    create_srv_query = """
    mutation CreateService($projectId: String!, $repo: String!) {
        serviceCreate(input: {
            projectId: $projectId,
            source: {
                repo: $repo
            }
        }) {
            id
            name
        }
    }
    """
    srv_data = execute_query(token, create_srv_query, {
        "projectId": project_id,
        "repo": repo
    })
    service_id = srv_data["serviceCreate"]["id"]

    # چند ثانیه وقفه برای اعمال سرویس
    time.sleep(3)

    # ۳. دریافت دامنه عمومی (up.railway.app)
    create_domain_query = """
    mutation CreateDomain($environmentId: String!, $serviceId: String!) {
        serviceDomainCreate(input: {
            environmentId: $environmentId,
            serviceId: $serviceId
        }) {
            id
            domain
        }
    }
    """
    domain_name = ""
    for _ in range(4):
        try:
            domain_data = execute_query(token, create_domain_query, {
                "environmentId": environment_id,
                "serviceId": service_id
            })
            domain_name = domain_data["serviceDomainCreate"]["domain"]
            if domain_name:
                break
        except Exception:
            time.sleep(2)

    return {
        "project_id": project_id,
        "project_name": project_name,
        "service_id": service_id,
        "domain": domain_name if domain_name else "در حال صدور...",
        "repo": repo
    }

def delete_project_api(token: str, project_id: str):
    """حذف کامل پروژه از Railway"""
    query = """
    mutation DeleteProject($id: String!) {
        projectDelete(id: $id)
    }
    """
    return execute_query(token, query, {"id": project_id})