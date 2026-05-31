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
        label: "Student 学生",
        password: "student@2026",
        hint: "只能访问公开课程资料。",
    },
    {
        role: "engineering",
        label: "TA / Teacher 教学资料",
        password: "teacher@2026",
        hint: "可访问教学资料、评分标准与公开资料。",
    },
    {
        role: "c_level",
        label: "Admin 管理员",
        password: "admin@2026",
        hint: "可管理全部演示资料和系统能力。",
    },
];

export const DEMO_ACCOUNTS: DemoAccount[] = [
    {
        key: "admin",
        label: "Admin 管理员",
        username: "admin_demo",
        email: "admin_demo@finbot.local",
        password: "admin@2026",
        level: "L1_Executive",
        department: "Executive",
        is_admin: true,
        chat_role: "c_level",
        scenario: "资料管理、归档查看、全部课程资料访问",
    },
    {
        key: "teacher",
        label: "Teacher 教师",
        username: "teacher_demo",
        email: "teacher_demo@finbot.local",
        password: "teacher@2026",
        level: "L2_Director",
        department: "R&D",
        is_admin: false,
        chat_role: "engineering",
        scenario: "查看教师答案、评分标准和受限教学资料",
    },
    {
        key: "ta",
        label: "TA 助教",
        username: "ta_demo",
        email: "ta_demo@finbot.local",
        password: "ta@2026",
        level: "L3_Manager",
        department: "R&D",
        is_admin: false,
        chat_role: "engineering",
        scenario: "查看评分标准、工程说明和课程归档",
    },
    {
        key: "student",
        label: "Student 学生",
        username: "student_demo",
        email: "student_demo@finbot.local",
        password: "student@2026",
        level: "L4_Staff",
        department: "Public",
        is_admin: false,
        chat_role: "employee",
        scenario: "只能访问公开资料，越权请求会被拒绝",
    },
];

export function verifyMemberPassword(role: MemberRole, password: string): boolean {
    const member = MEMBER_OPTIONS.find((item) => item.role === role);
    return member?.password === password;
}

export function getMemberHint(role: MemberRole): string {
    return MEMBER_OPTIONS.find((item) => item.role === role)?.hint ?? "";
}
