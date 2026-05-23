# Secure Corporate RAG Assistant
# 企业文档安全RAG问答助手

## 项目概述

面向公司内部文档的安全RAG问答系统，实现：
- 文档加密存储（AES-256）
- 基于级别和部门的RBAC权限控制
- 敏感信息脱敏
- Prompt Injection防护
- 文档完整性验证与数字签名
- 审计日志追踪

## 权限设计

### 用户级别 (Level)
- **L1_Executive**: 公司高管，可访问所有部门文档
- **L2_Director**: 部门总监，可访问本部门及以下级别文档
- **L3_Manager**: 部门经理，可访问本部门核心文档
- **L4_Staff**: 普通员工，可访问公开文档

### 部门 (Department)
- **Executive**: 执行部门
- **HR**: 人力资源部
- **Finance**: 财务部
- **IT**: 信息技术部
- **Sales**: 销售部
- **R&D**: 研发部
- **Legal**: 法务部
- **Public**: 公共/公开部门

## 目录结构

```
secure-corporate-rag/
├── backend/
│   ├── api/              # API路由
│   ├── models/           # 数据模型
│   ├── security/         # 安全模块
│   │   ├── crypto_utils.py      # AES加密
│   │   ├── hash_utils.py        # SHA-256哈希
│   │   ├── signature_utils.py   # RSA签名
│   │   └── hmac_utils.py         # HMAC认证
│   ├── services/         # 业务服务
│   └── main.py           # FastAPI入口
├── documents/            # 加密文档存储
├── keys/                 # 密钥存储
└── requirements.txt      # Python依赖
```

--------------以下不用看------------------

自用：激活虚拟环境：.\venv\Scripts\Activate.ps1
