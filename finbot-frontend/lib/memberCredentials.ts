export type MemberRole =
    | "employee"
    | "hr_manager"
    | "finance"
    | "marketing"
    | "engineering"
    | "c_level";

export const MEMBER_OPTIONS: {
    role: MemberRole;
    label: string;
    password: string;
    hint: string;
}[] = [
    {
        role: "employee",
        label: "普通员工 (employee)",
        password: "emp@2026",
        hint: "仅可访问公共文档",
    },
    {
        role: "hr_manager",
        label: "HR 经理 (hr_manager)",
        password: "hr@2026",
        hint: "可访问 HR + 公共文档",
    },
    {
        role: "finance",
        label: "财务成员 (finance)",
        password: "fin@2026",
        hint: "可访问财务 + 公共文档",
    },
    {
        role: "marketing",
        label: "市场成员 (marketing)",
        password: "mkt@2026",
        hint: "可访问市场 + 公共文档",
    },
    {
        role: "engineering",
        label: "工程成员 (engineering)",
        password: "eng@2026",
        hint: "可访问工程 + 公共文档",
    },
    {
        role: "c_level",
        label: "高管 (c_level)",
        password: "ceo@2026",
        hint: "可访问全部部门文档",
    },
];

export function verifyMemberPassword(role: MemberRole, password: string): boolean {
    const member = MEMBER_OPTIONS.find((item) => item.role === role);
    return member?.password === password;
}

export function getMemberHint(role: MemberRole): string {
    return MEMBER_OPTIONS.find((item) => item.role === role)?.hint ?? "";
}
