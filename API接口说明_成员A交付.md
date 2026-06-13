# 安全底座 API 接口说明
# 成员A -> 成员B 交付文档
# 版本: 1.0
# 日期: 2026-05-23

---

## 一、基础信息

### 服务地址
```
http://localhost:8000
```

### API 文档（Swagger UI）
```
http://localhost:8000/docs
```

### 认证方式
所有需要认证的接口都需要在请求头中携带 JWT Token：
```
Authorization: Bearer <access_token>
```

---

## 二、数据库表结构

### 2.1 users 表
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| username | VARCHAR(50) | 用户名（唯一） |
| email | VARCHAR(100) | 邮箱（唯一） |
| password_hash | VARCHAR(255) | bcrypt哈希后的密码 |
| level | VARCHAR(20) | 权限级别 |
| department | VARCHAR(20) | 所属部门 |
| is_active | BOOLEAN | 是否激活 |
| is_admin | BOOLEAN | 是否管理员 |
| created_at | DATETIME | 创建时间 |
| last_login | DATETIME | 最后登录时间 |

### 2.2 documents 表
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| doc_id | VARCHAR(50) | 文档唯一ID（UUID） |
| original_filename | VARCHAR(255) | 原始文件名 |
| file_type | VARCHAR(20) | 文件类型 |
| file_size | INTEGER | 文件大小（字节） |
| encrypted_path | VARCHAR(500) | 加密文件存储路径 |
| target_department | VARCHAR(20) | 目标部门 |
| access_level_required | VARCHAR(20) | 所需权限级别 |
| owner_id | INTEGER | 所有者用户ID |
| owner_department | VARCHAR(20) | 所有者部门 |
| is_encrypted | BOOLEAN | 是否加密 |
| sha256_hash | VARCHAR(64) | SHA-256哈希值 |
| is_signed | BOOLEAN | 是否已签名 |
| signature | TEXT | RSA签名 |
| is_verified | BOOLEAN | 是否通过验证 |
| created_at | DATETIME | 创建时间 |

### 2.3 audit_logs 表
| 字段 | 类型 | 说明 |
|-----|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户ID（可为NULL） |
| username | VARCHAR(50) | 用户名 |
| ip_address | VARCHAR(50) | IP地址 |
| action | VARCHAR(50) | 操作类型 |
| resource_type | VARCHAR(50) | 资源类型 |
| resource_id | VARCHAR(50) | 资源ID |
| details | TEXT | 详细信息 |
| risk_level | VARCHAR(20) | 风险级别（low/medium/high/critical） |
| is_suspicious | BOOLEAN | 是否可疑 |
| success | BOOLEAN | 是否成功 |
| error_message | TEXT | 错误信息 |
| timestamp | DATETIME | 时间戳 |

---

## 三、权限级别说明

### 用户级别 (Level)
| 级别代码 | 名称 | 说明 |
|---------|------|------|
| L1_Executive | 公司高管 | 可访问所有部门文档 |
| L2_Director | 部门总监 | 可访问本部门及公共文档 |
| L3_Manager | 部门经理 | 可访问本部门核心文档及公共文档 |
| L4_Staff | 普通员工 | 仅可访问公共文档 |

### 部门 (Department)
| 部门代码 | 名称 |
|---------|------|
| Executive | 执行部门 |
| HR | 人力资源部 |
| Finance | 财务部 |
| IT | 信息技术部 |
| Sales | 销售部 |
| R&D | 研发部 |
| Legal | 法务部 |
| Public | 公共部门 |

### 权限矩阵 (PERMISSION_MATRIX)
```
(L1_Executive, any) -> 可访问所有部门
(L2_Director, HR) -> [HR, Public]
(L2_Director, Finance) -> [Finance, Public]
(L2_Director, IT) -> [IT, Public]
(L3_Manager, HR) -> [HR, Public]
(L3_Manager, Finance) -> [Finance, Public]
(L4_Staff, any) -> [Public]
```

---

## 四、API 接口详细说明

### 4.1 认证接口 (/api/auth)

#### POST /api/auth/register - 注册用户
**请求体：**
```json
{
    "username": "string",
    "email": "user@example.com",
    "password": "string",
    "level": "L4_Staff",
    "department": "Public",
    "is_admin": false
}
```

**响应：**
```json
{
    "id": 1,
    "username": "string",
    "email": "user@example.com",
    "level": "L4_Staff",
    "department": "Public",
    "is_active": true,
    "is_admin": false
}
```

#### POST /api/auth/login - 用户登录
**请求体（form-data）：**
```
username: string
password: string
```

**响应：**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
}
```

#### GET /api/auth/me - 获取当前用户信息
**需要认证：是**

**响应：**
```json
{
    "id": 1,
    "username": "string",
    "email": "user@example.com",
    "level": "L1_Executive",
    "department": "Executive",
    "is_active": true,
    "is_admin": true
}
```

#### POST /api/auth/logout - 用户登出
**需要认证：是**

---

### 4.2 文档接口 (/api/documents)

#### POST /api/documents/upload - 上传文档
**需要认证：是**
**权限：需有对应部门的文档上传权限**

**请求体（multipart/form-data）：**
| 字段 | 类型 | 说明 |
|-----|------|------|
| file | File | 上传的文件 |
| target_department | string | 目标部门（默认Public） |
| access_level_required | string | 所需权限级别（默认L4_Staff） |
| description | string | 文档描述 |
| sign_document | boolean | 是否签名（默认true） |

**响应：**
```json
{
    "message": "Document uploaded successfully",
    "document": {
        "doc_id": "uuid-string",
        "filename": "example.pdf",
        "is_encrypted": true,
        "is_signed": true,
        "sha256_hash": "..."
    },
    "metadata": {
        "original_hash": "...",
        "encrypted": true,
        "signature": "..."
    }
}
```

**安全特性：**
- 文件自动使用 AES-256-GCM 加密
- 自动计算 SHA-256 哈希
- 如果用户有签名权限，自动添加 RSA 签名

#### GET /api/documents/ - 列出可访问文档
**需要认证：是**

**说明：** 自动根据用户权限过滤，只返回用户有权访问的文档

**响应：**
```json
[
    {
        "doc_id": "uuid-string",
        "filename": "example.pdf",
        "owner_department": "HR",
        "access_level_required": "L2_Director",
        "is_encrypted": true,
        "is_signed": true
    }
]
```

#### GET /api/documents/{doc_id} - 获取文档元信息
**需要认证：是**
**权限：根据文档的 access_level_required 和 target_department 判断**

#### GET /api/documents/{doc_id}/download - 下载文档
**需要认证：是**
**权限：同上**

**响应：** 文件流，自动解密后返回原始文件

#### GET /api/documents/{doc_id}/verify - 验证文档完整性
**需要认证：是**

**响应：**
```json
{
    "doc_id": "uuid-string",
    "filename": "example.pdf",
    "stored_hash": "abc123...",
    "current_hash": "abc123...",
    "is_signed": true,
    "is_verified": true,
    "signature_valid": true,
    "integrity_check": "valid",
    "status": "ok"
}
```

**integrity_check 可能值：**
- `valid` - 文档完整，未被篡改
- `tampered` - 文档已被篡改
- `error` - 验证过程出错

#### POST /api/documents/{doc_id}/sign - 签名文档
**需要认证：是**
**权限：L1_Executive 或 L2_Director 或 is_admin=true**

---

### 4.3 RBAC 接口 (/api/rbac)

#### GET /api/rbac/permissions - 获取当前用户权限
**需要认证：是**

**响应：**
```json
{
    "user": {
        "username": "hr_director",
        "level": "L2_Director",
        "level_name": "部门总监",
        "department": "HR",
        "department_name": "人力资源部"
    },
    "permissions": {
        "can_access_departments": ["HR", "Public"],
        "can_upload_to": ["HR"],
        "can_sign_documents": true,
        "can_manage_users": false,
        "can_view_audit_logs": true
    },
    "restrictions": {
        "cannot_access_departments": ["Executive", "Finance", "IT", "Sales", "R&D", "Legal"]
    }
}
```

#### GET /api/rbac/can-upload/{department} - 检查上传权限
**需要认证：是**

**响应：**
```json
{
    "can_upload": true,
    "user_level": "L2_Director",
    "user_department": "HR",
    "target_department": "HR"
}
```

#### GET /api/rbac/can-sign - 检查签名权限
**需要认证：是**

#### GET /api/rbac/can-manage-users - 检查用户管理权限
**需要认证：是**

---

### 4.4 审计日志接口 (/api/audit)

#### GET /api/audit/logs - 获取审计日志
**需要认证：是**
**权限：L1_Executive, L2_Director 或 is_admin=true**

**查询参数：**
| 参数 | 类型 | 说明 |
|-----|------|------|
| user_id | int | 按用户ID筛选 |
| action | string | 按操作类型筛选 |
| start_date | datetime | 开始时间 |
| end_date | datetime | 结束时间 |
| risk_level | string | 按风险级别筛选 |
| limit | int | 返回数量限制 |

**响应：**
```json
{
    "total": 100,
    "logs": [
        {
            "id": 1,
            "username": "hr_director",
            "action": "document_upload",
            "details": "Uploaded employees.txt to HR department",
            "risk_level": "low",
            "success": true,
            "timestamp": "2026-05-23T10:30:00"
        }
    ]
}
```

#### GET /api/audit/dashboard - 风险仪表盘
**需要认证：是**
**权限：is_admin=true**

**响应：**
```json
{
    "period": "Last 24 hours",
    "generated_at": "2026-05-23T15:00:00",
    "summary": {
        "total_events": 62,
        "failed_events": 6,
        "suspicious_events": 0
    },
    "by_action": {
        "login": 9,
        "document_upload": 22,
        "access_denied": 1
    },
    "by_risk_level": {
        "critical": 2,
        "low": 59,
        "medium": 1
    },
    "top_active_users": [...],
    "critical_events": [...]
}
```

---

## 五、安全工具函数

### 5.1 加密工具 (security/crypto_utils.py)

```python
from backend.security.crypto_utils import CryptoUtils

# AES-256-GCM 加密
encrypted_data, nonce, tag = CryptoUtils.encrypt(data)

# 解密
decrypted_data = CryptoUtils.decrypt(encrypted_data, nonce, tag)

# Fernet 对称加密（更简单的API）
token = CryptoUtils.fernet_encrypt(data)
original_data = CryptoUtils.fernet_decrypt(token)
```

### 5.2 哈希工具 (security/hash_utils.py)

```python
from backend.security.hash_utils import HashUtils

# SHA-256 哈希
hash_value = HashUtils.sha256(data)

# 验证
is_valid = HashUtils.verify_sha256(data, expected_hash)
```

### 5.3 签名工具 (security/signature_utils.py)

```python
from backend.security.signature_utils import SignatureUtils

# 生成密钥对（仅首次需要）
public_key, private_key = SignatureUtils.generate_keypair()

# RSA 签名
signature = SignatureUtils.sign(data, private_key)

# 验证签名
is_valid = SignatureUtils.verify(data, signature, public_key)
```

### 5.4 HMAC 工具 (security/hmac_utils.py)

```python
from backend.security.hmac_utils import HMACUtils

# 生成 HMAC
hmac_value = HMACUtils.generate_hmac(data, key)

# 验证 HMAC
is_valid = HMACUtils.verify_hmac(data, hmac_value, key)
```

---

## 六、RBAC 权限检查服务

### 6.1 检查用户是否有权访问文档

```python
from backend.services.rbac_service import RBACService

# 获取用户可访问的部门列表
accessible_depts = RBACService.get_accessible_departments(user)

# 检查用户是否可以上传到指定部门
can_upload = RBACService.can_upload_to_department(user, "HR")

# 检查用户是否可以签名文档
can_sign = RBACService.can_sign_documents(user)

# 检查文档访问权限
allowed, reason = RBACService.check_document_access(user, document)
# allowed: True/False
# reason: "Access granted" 或拒绝原因
```

### 6.2 获取用户的权限矩阵

```python
permission_info = RBACService.get_permission_matrix_for_user(user)
# 返回包含 user, permissions, restrictions 的字典
```

---

## 七、审计日志记录

### 7.1 记录审计事件

```python
from backend.services.audit_service import AuditService

audit_service = AuditService()

# 记录事件
audit_service.log_event(
    db=db,
    action="document_upload",      # 操作类型
    user_id=user.id,
    username=user.username,
    success=True,
    details="Uploaded employees.txt",
    risk_level="low"              # low/medium/high/critical
)

# 记录失败事件
audit_service.log_event(
    db=db,
    action="access_denied",
    user_id=user.id,
    username=user.username,
    success=False,
    details="Attempted to access salary.txt without permission",
    risk_level="medium"
)
```

### 7.2 可用操作类型 (AuditAction)

| 操作类型 | 说明 |
|---------|------|
| LOGIN | 登录 |
| LOGIN_FAILED | 登录失败 |
| LOGOUT | 登出 |
| USER_CREATE | 创建用户 |
| USER_UPDATE | 更新用户 |
| DOCUMENT_UPLOAD | 上传文档 |
| DOCUMENT_DOWNLOAD | 下载文档 |
| DOCUMENT_VIEW | 查看文档 |
| DOCUMENT_VERIFY | 验证文档 |
| DOCUMENT_SIGN | 签名文档 |
| ACCESS_GRANTED | 访问授权 |
| ACCESS_DENIED | 访问拒绝 |
| PROMPT_INJECTION_BLOCKED | Prompt注入攻击拦截 |
| PII_DETECTED | 检测到PII信息 |

---

## 八、使用示例

### 8.1 B 成员接入示例：实现 RAG 问答时的权限过滤

```python
from backend.services.rbac_service import RBACService
from backend.database import SessionLocal

def rag_query(user, query_text):
    """RAG 问答时过滤用户无权访问的文档"""
    db = SessionLocal()

    # 1. 获取用户可访问的部门
    accessible_depts = RBACService.get_accessible_departments(user)

    # 2. 获取用户可访问的级别
    accessible_levels = RBACService.get_accessible_levels(user)

    # 3. 从向量数据库检索时，只返回这些文档
    documents = vector_db.similarity_search(
        query_text,
        filter={
            "department": {"$in": accessible_depts},
            "access_level": {"$in": accessible_levels}
        }
    )

    db.close()
    return documents
```

### 8.2 B 成员接入示例：记录 Prompt Injection 攻击

```python
from backend.services.audit_service import AuditService

def detect_prompt_injection(user_input: str) -> bool:
    """检测 Prompt Injection 攻击"""
    # ... 检测逻辑 ...

    if attack_detected:
        # 记录到审计日志
        db = SessionLocal()
        audit_service = AuditService()
        audit_service.log_event(
            db=db,
            action="prompt_injection_blocked",
            user_id=get_current_user_id(),
            username=get_current_username(),
            success=False,
            details=f"Blocked prompt injection: {user_input[:100]}...",
            risk_level="high"
        )
        db.close()
        return True
    return False
```

### 8.3 B 成员接入示例：文档篡改检测

```python
from backend.services.document_service import DocumentService

def verify_source_before_citing(doc_id: str):
    """验证文档来源可信后再引用"""
    db = SessionLocal()
    doc_service = DocumentService()

    result = doc_service.verify_document_integrity(
        db=db,
        doc_id=doc_id,
        user=get_current_user()
    )

    if result["is_verified"] and result["signature_valid"]:
        # 可以安全引用
        return {"can_cite": True, "source": result}
    else:
        # 拒绝引用未验证的文档
        return {"can_cite": False, "reason": "Document not verified"}

    db.close()
```

---

## 九、测试账号

初始化数据库后可使用以下测试账号：

| 角色 | 用户名 | 密码 | 级别 | 部门 |
|-----|--------|------|------|------|
| 高管/Admin | ceo | password123 | L1_Executive | Executive |
| HR总监 | hr_director | password123 | L2_Director | HR |
| HR经理 | hr_manager | password123 | L3_Manager | HR |
| HR员工 | hr_staff1 | password123 | L4_Staff | HR |
| IT员工 | it_staff1 | password123 | L4_Staff | IT |
| 财务总监 | finance_director | password123 | L2_Director | Finance |
| IT总监 | it_director | password123 | L2_Director | IT |

---

## 十、常见问题

### Q1: 用户上传文档需要什么权限？
- L4_Staff 只能上传到 Public 部门
- L3_Manager/L2_Director 可以上传到自己部门
- L1_Executive/is_admin 可以上传到任何部门

### Q2: 用户下载文档时如何过滤？
使用 `GET /api/documents/` 会自动根据权限过滤，无需手动处理。

### Q3: 如何判断用户是否有文档访问权限？
```python
from backend.services.rbac_service import RBACService

document = db.query(Document).filter(Document.doc_id == doc_id).first()
allowed, reason = RBACService.check_document_access(user, document)
```

### Q4: 加密文档存在哪里？
加密后的文档存储在 `documents/` 目录下，文件名为 `doc_id.enc`。

---

## 十一、联系方式

如有接口问题，请联系成员A。

---

**文档版本：** 1.0
**最后更新：** 2026-05-23
**维护者：** 成员A（第一棒）
