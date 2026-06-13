"""
Demo script for Secure Corporate RAG Assistant
演示脚本：展示系统的安全功能
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"


class DemoClient:
    """Demo client for testing the API"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.token = None
        self.headers = {}
    
    def register_user(self, username: str, email: str, password: str, level: str, department: str):
        """Register a new user"""
        response = requests.post(
            f"{self.base_url}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "level": level,
                "department": department
            }
        )
        return response.json()
    
    def login(self, username: str, password: str):
        """Login and get access token"""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            return True
        else:
            print(f"  登录失败: {response.status_code} - {response.text}")
            return False
    
    def get_me(self):
        """Get current user info"""
        response = requests.get(f"{self.base_url}/api/auth/me", headers=self.headers)
        return response.json()
    
    def get_permissions(self):
        """Get current user permissions"""
        response = requests.get(f"{self.base_url}/api/rbac/permissions", headers=self.headers)
        return response.json()
    
    def upload_document(self, filepath: str, target_department: str, access_level: str, description: str = ""):
        """Upload a document"""
        with open(filepath, 'rb') as f:
            files = {'file': f}
            data = {
                'target_department': target_department,
                'access_level_required': access_level,
                'description': description
            }
            response = requests.post(
                f"{self.base_url}/api/documents/upload",
                files=files,
                data=data,
                headers=self.headers
            )
        return response.json()
    
    def list_documents(self):
        """List accessible documents"""
        response = requests.get(f"{self.base_url}/api/documents/", headers=self.headers)
        return response.json()
    
    def verify_document(self, doc_id: str):
        """Verify document integrity"""
        response = requests.get(f"{self.base_url}/api/documents/{doc_id}/verify", headers=self.headers)
        return response.json()
    
    def get_risk_dashboard(self):
        """Get risk dashboard (admin only)"""
        response = requests.get(f"{self.base_url}/api/audit/dashboard", headers=self.headers)
        return response.json()


def print_separator(title: str):
    """Print section separator"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def demo_basic_flow():
    """演示基本工作流程"""
    client = DemoClient()
    
    print_separator("演示1: 注册不同级别用户")
    
    # Register users of different levels
    users = [
        ("admin_user", "admin@company.com", "admin123", "L1_Executive", "Executive"),
        ("hr_director", "hr_director@company.com", "hr123", "L2_Director", "HR"),
        ("hr_manager", "hr_manager@company.com", "hr123", "L3_Manager", "HR"),
        ("it_staff", "it_staff@company.com", "it123", "L4_Staff", "IT"),
        ("sales_staff", "sales_staff@company.com", "sales123", "L4_Staff", "Sales"),
    ]
    
    for username, email, password, level, dept in users:
        try:
            result = client.register_user(username, email, password, level, dept)
            print(f"  注册 {username} ({level}, {dept}): 成功")
        except Exception as e:
            print(f"  注册 {username}: 可能已存在或其他错误")
    
    print_separator("演示2: 不同用户登录并查看权限")
    
    # Login as different users (each gets a new client with fresh token)
    test_users = [
        ("admin_user", "admin123"),
        ("hr_director", "password123"),  # Use correct password from init_db.py
        ("it_staff1", "password123"),
    ]
    
    for username, password in test_users:
        client = DemoClient()  # Fresh client for each user
        success = client.login(username, password)
        if success:
            me = client.get_me()
            perms = client.get_permissions()
            print(f"\n  用户: {username}")
            print(f"  级别: {me.get('level', 'N/A')}")
            print(f"  部门: {me.get('department', 'N/A')}")
            print(f"  可访问部门: {perms.get('permissions', {}).get('can_access_departments', [])}")


def demo_rbac_permissions():
    """演示RBAC权限控制"""
    print_separator("演示3: RBAC权限控制")
    
    client_hr = DemoClient()
    client_it = DemoClient()
    
    # Login as HR director and IT staff
    hr_login = client_hr.login("hr_director", "password123")
    it_login = client_it.login("it_staff1", "password123")
    
    print("\n  IT员工尝试访问HR部门信息...")
    perms = client_it.get_permissions()
    print(f"  可访问部门: {perms.get('permissions', {}).get('can_access_departments', [])}")
    can_access_hr = 'HR' in perms.get('permissions', {}).get('can_access_departments', [])
    print(f"  能否访问HR部门: {'是' if can_access_hr else '否'}")
    
    print("\n  HR总监尝试访问HR部门信息...")
    perms_hr = client_hr.get_permissions()
    print(f"  可访问部门: {perms_hr.get('permissions', {}).get('can_access_departments', [])}")
    can_access_hr_hr = 'HR' in perms_hr.get('permissions', {}).get('can_access_departments', [])
    print(f"  能否访问HR部门: {'是' if can_access_hr_hr else '否'}")


def demo_encryption_verification():
    """演示加密和验证"""
    print_separator("演示4: 文档加密与完整性验证")
    
    client = DemoClient()
    client.login("ceo", "password123")  # CEO has full access
    
    # Check if there are documents to verify
    docs = client.list_documents()
    if docs:
        print(f"\n  找到 {len(docs)} 个文档")
        for doc in docs[:3]:  # Show first 3
            print(f"\n  文档: {doc.get('filename', 'N/A')}")
            print(f"  部门: {doc.get('owner_department', 'N/A')}")
            print(f"  权限级别: {doc.get('access_level_required', 'N/A')}")
            print(f"  已加密: {doc.get('is_encrypted', False)}")
            print(f"  已签名: {doc.get('is_signed', False)}")
            
            # Verify document
            verification = client.verify_document(doc.get('doc_id'))
            print(f"  完整性检查: {verification.get('integrity_check', 'N/A')}")
            print(f"  签名验证: {verification.get('signature_valid', 'N/A')}")
    else:
        print("\n  当前没有文档，请先上传文档进行测试")


def demo_risk_dashboard():
    """演示风险仪表盘"""
    print_separator("演示5: 风险仪表盘")
    
    client = DemoClient()
    client.login("ceo", "password123")  # CEO is admin
    
    try:
        dashboard = client.get_risk_dashboard()
        print(f"\n  时间范围: {dashboard.get('period', 'N/A')}")
        print(f"  总事件数: {dashboard.get('summary', {}).get('total_events', 0)}")
        print(f"  失败事件: {dashboard.get('summary', {}).get('failed_events', 0)}")
        print(f"  可疑事件: {dashboard.get('summary', {}).get('suspicious_events', 0)}")
        
        print("\n  按风险级别分类:")
        for level, count in dashboard.get('by_risk_level', {}).items():
            print(f"    {level}: {count}")
        
        print("\n  按操作类型分类:")
        for action, count in dashboard.get('by_action', {}).items():
            print(f"    {action}: {count}")
    except Exception as e:
        print(f"  获取仪表盘失败: {e}")


def main():
    """Run all demos"""
    print("""
    =============================================
       Secure Corporate RAG Assistant
          企业文档安全RAG问答助手 - 演示
    =============================================
    """)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("API未正常运行")
            return
    except:
        print(f"无法连接到API服务器 ({API_BASE_URL})")
        print("请确保服务器正在运行: uvicorn main:app --reload")
        return
    
    # Run demos
    try:
        demo_basic_flow()
        demo_rbac_permissions()
        demo_encryption_verification()
        demo_risk_dashboard()
    except Exception as e:
        import traceback
        print(f"演示过程中出错: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(" 演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
