"""
Database initialization and sample data
初始化数据库并创建示例数据
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from database import init_db, SessionLocal, reset_database
from services import AuthService, DocumentService, AuditService
from models import User, Document, UserLevel, Department


def create_sample_users(db):
    """Create sample users with different levels and departments"""
    print("Creating sample users...")
    
    users_data = [
        # L1 - Executive level (can access all)
        ("ceo", "ceo@company.com", "password123", "L1_Executive", "Executive", True),
        ("cfo", "cfo@company.com", "password123", "L1_Executive", "Finance", False),
        ("cto", "cto@company.com", "password123", "L1_Executive", "IT", False),
        
        # L2 - Director level
        ("hr_director", "hr_director@company.com", "password123", "L2_Director", "HR", False),
        ("finance_director", "finance_director@company.com", "password123", "L2_Director", "Finance", False),
        ("it_director", "it_director@company.com", "password123", "L2_Director", "IT", False),
        ("sales_director", "sales_director@company.com", "password123", "L2_Director", "Sales", False),
        ("rd_director", "rd_director@company.com", "password123", "L2_Director", "R&D", False),
        
        # L3 - Manager level
        ("hr_manager", "hr_manager@company.com", "password123", "L3_Manager", "HR", False),
        ("finance_manager", "finance_manager@company.com", "password123", "L3_Manager", "Finance", False),
        ("it_manager", "it_manager@company.com", "password123", "L3_Manager", "IT", False),
        ("sales_manager", "sales_manager@company.com", "password123", "L3_Manager", "Sales", False),
        
        # L4 - Staff level
        ("hr_staff1", "hr_staff1@company.com", "password123", "L4_Staff", "HR", False),
        ("hr_staff2", "hr_staff2@company.com", "password123", "L4_Staff", "HR", False),
        ("finance_staff1", "finance_staff1@company.com", "password123", "L4_Staff", "Finance", False),
        ("it_staff1", "it_staff1@company.com", "password123", "L4_Staff", "IT", False),
        ("it_staff2", "it_staff2@company.com", "password123", "L4_Staff", "IT", False),
        ("sales_staff1", "sales_staff1@company.com", "password123", "L4_Staff", "Sales", False),
        ("rd_staff1", "rd_staff1@company.com", "password123", "L4_Staff", "R&D", False),
    ]
    
    created_users = []
    for username, email, password, level, dept, is_admin in users_data:
        try:
            user, token = AuthService.register_user(
                db=db,
                username=username,
                email=email,
                password=password,
                level=level,
                department=dept,
                is_admin=is_admin
            )
            created_users.append(user)
            print(f"  Created: {username} ({level}, {dept})")
        except ValueError as e:
            print(f"  Skipped: {username} ({str(e)})")
    
    return created_users


def create_sample_documents(db, users):
    """Create sample documents"""
    print("\nCreating sample documents...")
    
    doc_service = DocumentService()
    
    # Find users by username
    def find_user(username):
        return next((u for u in users if u.username == username), None)
    
    sample_docs = [
        # HR documents
        ("employees.txt", "HR", "L2_Director", "员工名单（机密）", find_user("hr_director")),
        ("salaries.txt", "HR", "L1_Executive", "薪资表（绝密）", find_user("ceo")),
        ("hiring_plan.txt", "HR", "L3_Manager", "招聘计划", find_user("hr_manager")),
        ("onboarding.txt", "Public", "L4_Staff", "新员工入职指南", find_user("hr_staff1")),
        
        # Finance documents
        ("budget_2026.txt", "Finance", "L1_Executive", "2026年度预算（绝密）", find_user("cfo")),
        ("expense_report.txt", "Finance", "L3_Manager", "部门开支报告", find_user("finance_manager")),
        ("tax_guide.txt", "Public", "L4_Staff", "税务指南", find_user("finance_staff1")),
        
        # IT documents
        ("network_config.txt", "IT", "L2_Director", "网络配置（机密）", find_user("it_director")),
        ("server_passwords.txt", "IT", "L1_Executive", "服务器密码列表（绝密）", find_user("cto")),
        ("security_policy.txt", "IT", "L3_Manager", "安全策略", find_user("it_manager")),
        ("wifi_password.txt", "Public", "L4_Staff", "WiFi密码", find_user("it_staff1")),
        
        # R&D documents
        ("product_roadmap.txt", "R&D", "L1_Executive", "产品路线图（机密）", find_user("rd_director")),
        ("tech_specs.txt", "R&D", "L3_Manager", "技术规格文档", find_user("rd_director")),
        ("research_notes.txt", "Public", "L4_Staff", "研究笔记", find_user("rd_staff1")),
        
        # Sales documents
        ("clients.txt", "Sales", "L2_Director", "客户名单（机密）", find_user("sales_director")),
        ("pricing.txt", "Sales", "L3_Manager", "定价策略", find_user("sales_manager")),
        ("sales_guide.txt", "Public", "L4_Staff", "销售指南", find_user("sales_staff1")),
        
        # Legal documents
        ("contracts.txt", "Legal", "L1_Executive", "合同模板（机密）", find_user("ceo")),
        ("compliance.txt", "Legal", "L2_Director", "合规手册", find_user("sales_director")),
        
        # Public documents
        ("company_intro.txt", "Public", "L4_Staff", "公司简介", find_user("hr_staff1")),
        ("org_chart.txt", "Public", "L4_Staff", "组织架构图", find_user("hr_staff1")),
    ]
    
    for filename, dept, level, description, owner in sample_docs:
        if owner is None:
            print(f"  Skipped: {filename} (owner not found)")
            continue
        
        # Create sample content
        content = f"""
{filename}
部门: {dept}
访问级别: {level}
描述: {description}

这是示例文档内容。
实际部署时，这里应该包含真实的文档内容。
文档已被AES-256加密存储，并使用SHA-256计算哈希值。
""".encode('utf-8')
        
        try:
            doc, metadata = doc_service.upload_document(
                db=db,
                file_content=content,
                filename=filename,
                owner=owner,
                target_department=dept,
                access_level_required=level,
                description=description,
                sign_document=True
            )
            print(f"  Created: {filename} ({dept}, {level})")
        except Exception as e:
            print(f"  Error creating {filename}: {e}")


def create_sample_audit_logs(db):
    """Create some sample audit logs for demonstration"""
    print("\nCreating sample audit logs...")
    
    # Get first user
    user = db.query(User).first()
    if not user:
        print("  No users found, skipping audit logs")
        return
    
    audit_service = AuditService()
    
    sample_events = [
        ("login", True, "Normal login"),
        ("document_upload", True, "Uploaded employee handbook"),
        ("document_view", True, "Viewed salary information"),
        ("access_denied", False, "Attempted to access CEO documents"),
        ("login_failed", False, "Failed login attempt with wrong password"),
    ]
    
    for action, success, details in sample_events:
        try:
            audit_service.log_event(
                db=db,
                action=action,
                user_id=user.id,
                username=user.username,
                success=success,
                details=details
            )
        except Exception as e:
            print(f"  Error creating audit log: {e}")
    
    print("  Sample audit logs created")


def main():
    """Initialize database and create sample data"""
    print("""
    =============================================
       Secure Corporate RAG Assistant
          Database Initialization
    =============================================
    """)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    print("Database initialized!")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create sample data
        users = create_sample_users(db)
        create_sample_documents(db, users)
        create_sample_audit_logs(db)
        
        print("\n" + "=" * 50)
        print(" Database initialization complete!")
        print("=" * 50)
        print("\nSample Users:")
        print("  CEO (Admin):     ceo@company.com / password123")
        print("  HR Director:      hr_director@company.com / password123")
        print("  HR Manager:       hr_manager@company.com / password123")
        print("  HR Staff:         hr_staff1@company.com / password123")
        print("  IT Staff:         it_staff1@company.com / password123")
        print("\nStart the server with:")
        print("  cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("=" * 50)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
