import { ChatRole, DemoAccount } from "@/types";

export type MemberRole = ChatRole;

export const MEMBER_OPTIONS: {
    role: MemberRole;
    label: string;
    password: string;
    hint: string;
}[] = [
    {
        role: "employee",
        label: "普通员工 employee",
        password: "password123",
        hint: "只能访问公共资料。",
    },
    {
        role: "hr_manager",
        label: "HR 经理 hr_manager",
        password: "password123",
        hint: "可访问 HR 与公共资料。",
    },
    {
        role: "finance",
        label: "财务经理 finance",
        password: "password123",
        hint: "可访问财务与公共资料。",
    },
    {
        role: "marketing",
        label: "市场经理 marketing",
        password: "password123",
        hint: "可访问市场与公共资料。",
    },
    {
        role: "engineering",
        label: "工程负责人 engineering",
        password: "password123",
        hint: "可访问工程与公共资料。",
    },
    {
        role: "c_level",
        label: "高管 c_level",
        password: "password123",
        hint: "可访问全部部门资料。",
    },
];

export const DEMO_ACCOUNTS: DemoAccount[] = [
    {
        key: "executive",
        label: "Executive 高管",
        username: "ceo",
        email: "ceo@company.com",
        password: "password123",
        level: "L1_Executive",
        department: "Executive",
        is_admin: true,
        chat_role: "c_level",
        scenario: "全公司资料、跨部门问答、审计演示",
    },
    {
        key: "hr",
        label: "HR 经理",
        username: "hr_manager",
        email: "hr_manager@company.com",
        password: "password123",
        level: "L3_Manager",
        department: "HR",
        is_admin: false,
        chat_role: "hr_manager",
        scenario: "HR 员工数据、招聘与公共政策",
    },
    {
        key: "finance",
        label: "Finance 财务",
        username: "finance_manager",
        email: "finance_manager@company.com",
        password: "password123",
        level: "L3_Manager",
        department: "Finance",
        is_admin: false,
        chat_role: "finance",
        scenario: "预算、报表、开支与公共资料",
    },
    {
        key: "engineering",
        label: "Engineering 工程",
        username: "rd_director",
        email: "rd_director@company.com",
        password: "password123",
        level: "L2_Director",
        department: "R&D",
        is_admin: false,
        chat_role: "engineering",
        scenario: "系统架构、SLA、CI/CD 与工程资料",
    },
    {
        key: "marketing",
        label: "Marketing 市场",
        username: "marketing_manager",
        email: "marketing_manager@company.com",
        password: "password123",
        level: "L3_Manager",
        department: "Sales",
        is_admin: false,
        chat_role: "marketing",
        scenario: "营销活动、获客指标与市场报告",
    },
    {
        key: "employee",
        label: "Employee 普通员工",
        username: "employee_demo",
        email: "employee_demo@company.com",
        password: "password123",
        level: "L4_Staff",
        department: "Public",
        is_admin: false,
        chat_role: "employee",
        scenario: "仅公共资料，越权访问会被拒绝",
    },
];

export function verifyMemberPassword(role: MemberRole, password: string): boolean {
    const member = MEMBER_OPTIONS.find((item) => item.role === role);
    return member?.password === password;
}

export function getMemberHint(role: MemberRole): string {
    return MEMBER_OPTIONS.find((item) => item.role === role)?.hint ?? "";
}
