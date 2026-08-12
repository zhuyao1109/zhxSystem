export interface CreateAlignmentTaskInput {
  group1Id: string;
  group2Id: string;
  group1Name?: string;
  group2Name?: string;
  priorityRules: string[];
  customRule?: string;
}

/**
 * 将前端「标准组 + 规则」表单转换为后端要求的 { text, options }
 */
export function buildCreateAlignmentTaskBody(
  data: CreateAlignmentTaskInput
): { text: string; options: Record<string, unknown> } {
  const g1Name = data.group1Name?.trim() || data.group1Id;
  const g2Name = data.group2Name?.trim() || data.group2Id;
  const parts: string[] = [
    `对齐请求：标准「${g1Name}」与「${g2Name}」`,
  ];
  if (data.priorityRules.length > 0) {
    parts.push(`优先级规则：${data.priorityRules.join('、')}`);
  }
  if (data.customRule?.trim()) {
    parts.push(`补充说明：${data.customRule.trim()}`);
  }
  return {
    text: parts.join('。\n'),
    options: {
      group1Id: data.group1Id,
      group2Id: data.group2Id,
      group1Name: data.group1Name,
      group2Name: data.group2Name,
      priorityRules: data.priorityRules,
      customRule: data.customRule,
    },
  };
}
