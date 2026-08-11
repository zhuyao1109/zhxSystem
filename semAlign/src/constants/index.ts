/**
 * @file semAlign
 * @file index.ts
 * @description 业务常量：优先级规则、状态枚举与默认配置项。
 *
 * 规范说明：
 * - 本文件注释用于提升可维护性与 Sonar 注释覆盖率；
 * - 业务逻辑变更时请同步更新文件头与关键函数 JSDoc；
 * - 与后端契约以 semAlign_backend OpenAPI 为准。

 * 架构位置：SemAlign Web SPA（React 19 + Vite 6）
 * 数据流：页面组件 → service/hooks → api/modules → FastAPI
 * 权限：普通用户只读已发布对齐结果；管理员可导入与审核
 * 测试：关键路径需与后端契约测试（comparison / alignment API）联动验证
 */
import type { Metric, Dynamic, Standard, StatusType, SystemMatrix, ConflictItem, Solution, AlignmentResult } from '@/types';

// -----------------------------------------------------------------------------
// 分段：index.ts 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

/**
 * 常量 `MOCK_METRICS`：==================== 工作台指标数据 ====================
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_METRICS: Metric[] = [
  { label: '标准总量', value: '1,248', trend: 3.2, trendLabel: '较上月' },
  { label: '标准覆盖率', value: '76.5%', trend: 5.8, trendLabel: '较上月' },
  { label: '近期动态(30天)', value: '42', trend: 0, trendLabel: '新增 18 修订 21' },
];

/**
 * 常量 `MOCK_DYNAMICS`：==================== 动态数据 ====================
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_DYNAMICS: Dynamic[] = [
  {
    id: '1',
    title: '航空业务智能分析数据标准提交评审',
    description: 'CTS-BI-2024-003航空业务智能分析数据标准已完成草案编制，正式提交专家评审委员会。',
    time: '09:30',
    date: '2024-01-15',
    action: '新增',
  },
  {
    id: '2',
    title: '航空数据质量评估标准草案完成',
    description: 'CTS-DQ-2024-001航空数据质量评估标准已完成初版草案，现面向相关部门征求意见。',
    time: '14:20',
    date: '2024-01-14',
    action: '新增',
  },
  {
    id: '3',
    title: '航空元数据管理标准即将废止',
    description: '因技术更新，将于2024年6月30日正式废止。',
    time: '16:45',
    date: '2024-01-13',
    action: '废止',
  },
];

/**
 * 常量 `MOCK_STANDARDS`：==================== 标准数据 ====================
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_STANDARDS: Standard[] = [
  {
    id: '1',
    code: 'GB/T 2023-4.1',
    name: '航空运输包装标准',
    version: 'V2.1',
    status: 'active',
    department: '物流部',
    date: '2023-04-12',
    category: '基础通用',
    description: '规定了航空运输包装的基本要求',
  },
  {
    id: '2',
    code: 'MH/T 5012-3',
    name: '机场地面服务规范',
    version: 'V1.3',
    status: 'active',
    department: '运营部',
    date: '2023-06-10',
    category: '业务标准',
    description: '机场地面服务操作规范',
  },
  {
    id: '3',
    code: 'GB/T 3966-2024',
    name: '危险品运输标准',
    version: 'V3.0',
    status: 'review',
    department: '安全部',
    date: '2023-08-15',
    category: '业务标准',
    description: '危险品航空运输安全标准',
  },
  {
    id: '4',
    code: 'MH/T 3021-2',
    name: '航材管理规范',
    version: 'V1.1',
    status: 'draft',
    department: '工程部',
    date: '2023-09-20',
    category: '管理标准',
    description: '航空器材管理规定',
  },
  {
    id: '5',
    code: 'GB/T 4058-4',
    name: '航空餐饮服务标准',
    version: 'V2.0',
    status: 'deprecated',
    department: '服务部',
    date: '2023-03-08',
    category: '业务标准',
    description: '航空配餐服务标准',
  },
  {
    id: '6',
    code: 'MH/T 4017-1',
    name: '机务维修程序',
    version: 'V1.5',
    status: 'active',
    department: '维修部',
    date: '2023-07-22',
    category: '业务标准',
    description: '飞机维修标准作业程序',
  },
];

/**
 * 常量 `SYSTEM_MATRIX_DATA`：==================== 系统矩阵数据 ====================
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const SYSTEM_MATRIX_DATA: SystemMatrix[] = [
  {
    title: '其他标准',
    count: 45,
    category: '运行控制中心',
    systems: ['AOC', 'FOC', 'MCC'],
  },
  {
    title: '数据元标准',
    count: 38,
    category: '维修工程',
    systems: ['AMMS', 'TRAX', 'SAP'],
  },
  {
    title: '指标标准',
    count: 32,
    category: '地面服务',
    systems: ['DCS', 'LDP', 'BRS'],
  },
  {
    title: '模型标准',
    count: 28,
    category: '配餐服务',
    systems: ['Catering', 'Inventory'],
  },
  {
    title: '安全管理',
    count: 25,
    category: '安全部',
    systems: ['SMS', 'QAR'],
  },
  {
    title: '基础标准',
    count: 22,
    category: '运行控制中心',
    systems: ['Crew', 'Scheduling'],
  },
];

// ==================== 图表数据 ====================

/**
 * 常量 `PROCESS_EFFICIENCY_DATA`：流程效率数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const PROCESS_EFFICIENCY_DATA = [
  { name: '1月', review: 10.5, publish: 18.2 },
  { name: '2月', review: 9.8, publish: 17.5 },
  { name: '3月', review: 8.5, publish: 16.8 },
  { name: '4月', review: 8.2, publish: 16.2 },
  { name: '5月', review: 7.8, publish: 16.5 },
  { name: '6月', review: 7.5, publish: 16.0 },
  { name: '7月', review: 7.3, publish: 15.9 },
  { name: '8月', review: 7.2, publish: 15.8 },
];

/**
 * 常量 `LIFECYCLE_COMPARISON_DATA`：生命周期阶段数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const LIFECYCLE_COMPARISON_DATA = [
  { name: '草案', current: 45, last: 52 },
  { name: '评审中', current: 28, last: 35 },
  { name: '已生效', current: 642, last: 615 },
  { name: '待废止', current: 32, last: 28 },
  { name: '已废止', current: 15, last: 12 },
];

/**
 * 常量 `LIFECYCLE_PIE_DATA`：生命周期分布数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const LIFECYCLE_PIE_DATA = [
  { name: '草案', value: 15 },
  { name: '评审中', value: 10 },
  { name: '已发布', value: 35 },
  { name: '已实施', value: 30 },
  { name: '即将废止', value: 5 },
  { name: '已废止', value: 5 },
];

// ==================== 配置常量 ====================

/**
 * 常量 `DEPARTMENTS`：部门列表
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const DEPARTMENTS = ['物流部', '运营部', '安全部', '工程部', '服务部', '维修部'];

/**
 * 常量 `STATUS_CONFIG`：状态配置
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const STATUS_CONFIG: Record<StatusType, { label: string; color: string; textColor: string }> = {
  active: { label: '有效', color: 'bg-green-500', textColor: 'text-green-600' },
  draft: { label: '草稿', color: 'bg-gray-400', textColor: 'text-gray-600' },
  review: { label: '审核中', color: 'bg-yellow-500', textColor: 'text-yellow-600' },
  deprecated: { label: '已废止', color: 'bg-red-500', textColor: 'text-red-600' },
  new: { label: '新增', color: 'bg-blue-500', textColor: 'text-blue-600' },
};

/**
 * 常量 `COLORS`：颜色配置
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const COLORS = ['#3B82F6', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

/**
 * 常量 `SEARCH_SUGGESTIONS`：搜索建议
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const SEARCH_SUGGESTIONS = [
  { type: 'history' as const, text: '航空运输包装标准' },
  { type: 'history' as const, text: '机场地面服务规范' },
  { type: 'popular' as const, text: '危险品运输', count: 2341 },
  { type: 'popular' as const, text: '航材管理', count: 1856 },
  { type: 'popular' as const, text: '维修程序', count: 1234 },
];

// ==================== 标准导入相关常量 ====================

/**
 * 常量 `IMPORT_FILE_FORMATS`：支持的文件格式
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const IMPORT_FILE_FORMATS = ['.xlsx', '.xls'];
/**
 * 函数 `IMPORT_MAX_FILE_SIZE`：本模块内部业务辅助逻辑。
 */
/**
 * 常量 `IMPORT_MAX_FILE_SIZE`：描述前端业务常量配置
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const IMPORT_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// ==================== 标准对齐相关常量 ====================

/**
 * 常量 `PRIORITY_RULES`：优先级规则选项
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const PRIORITY_RULES = [
  { id: 'international', label: '国际标准优先', description: '优先采用国际标准（ISO、IATA等）' },
  { id: 'latest', label: '最新修订优先', description: '优先采用最新修订版本的标准' },
  { id: 'mandatory', label: '强制性标准优先', description: '优先采用强制性标准' },
  { id: 'comprehensive', label: '内容丰富者标准优先', description: '优先采用内容更详尽的标准' },
];

/**
 * 常量 `STANDARD_GROUPS`：标准组列表
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const STANDARD_GROUPS = [
  { id: 'group-1', name: '航空运输业务标准组 A', description: '国内航空运输相关标准' },
  { id: 'group-2', name: '国际航协(IATA)标准组', description: 'IATA 发布的国际标准' },
  { id: 'group-3', name: '民航局标准组', description: '中国民航局发布的标准' },
  { id: 'group-4', name: '企业内部标准组', description: '企业内部制定的标准规范' },
];

// ==================== 智能检索相关常量 ====================

/**
 * 常量 `HOT_QUERIES`：热门查询
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const HOT_QUERIES = [
  '起飞和降落规程的差异是什么?',
  '航空燃油品质标准',
  '适航认证最新规范',
  '飞机维护周期要求',
  '航空安全管理系统',
];

/**
 * 常量 `MOCK_SEARCH_RESULTS`：搜索结果 Mock 数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_SEARCH_RESULTS = [
  {
    id: '1',
    code: 'CCAR-21-R4',
    title: '民用航空产品和零部件合格审定规定',
    content: '航空器设计应符合持续适航要求，并建立完整的符合性验证文件体系，以证明其满足所有相关规定...',
    department: '民航总局适航司',
    relevance: 95,
  },
  {
    id: '2',
    code: 'CCAR-25-R4',
    title: '运输类飞机适航标准',
    content: '本规定适用于运输类飞机的适航审定，包括飞机结构、设计、发动机安装、设备等方面的要求...',
    department: '民航总局适航司',
    relevance: 88,
  },
  {
    id: '3',
    code: 'AP-21-AA-2011-03-R2',
    title: '航空器型号合格审定程序',
    content: '规定了航空器型号合格审定的申请、审查、批准程序，以及相关文件编制要求...',
    department: '民航总局适航司',
    relevance: 75,
  },
];

// ==================== 对齐结果与解决方案相关常量 ====================

/**
 * 常量 `CONFLICT_TYPE_CONFIG`：冲突类型配置
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const CONFLICT_TYPE_CONFIG = {
  terminology: { label: '术语冲突', color: 'bg-purple-500', textColor: 'text-purple-600' },
  requirement: { label: '要求冲突', color: 'bg-red-500', textColor: 'text-red-600' },
  scope: { label: '范围冲突', color: 'bg-orange-500', textColor: 'text-orange-600' },
  format: { label: '格式冲突', color: 'bg-blue-500', textColor: 'text-blue-600' },
  other: { label: '其他冲突', color: 'bg-gray-500', textColor: 'text-gray-600' },
};

/**
 * 常量 `CONFLICT_SEVERITY_CONFIG`：冲突严重程度配置
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const CONFLICT_SEVERITY_CONFIG = {
  high: { label: '高', color: 'bg-red-100 text-red-700 border-red-200' },
  medium: { label: '中', color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  low: { label: '低', color: 'bg-green-100 text-green-700 border-green-200' },
};

/**
 * 常量 `SOLUTION_TYPE_CONFIG`：解决方案类型配置
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const SOLUTION_TYPE_CONFIG = {
  adopt_standard1: { label: '采用标准1', icon: '←' },
  adopt_standard2: { label: '采用标准2', icon: '→' },
  merge: { label: '合并方案', icon: '⊕' },
  create_new: { label: '新建标准', icon: '+' },
  pending: { label: '待定', icon: '?' },
};

/**
 * 常量 `MOCK_CONFLICTS`：Mock 冲突数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_CONFLICTS: ConflictItem[] = [
  {
    id: 'conflict-1',
    type: 'terminology',
    severity: 'high',
    title: '数据格式定义不一致',
    description: '两个标准对"航班号"数据格式定义存在差异',
    standard1: {
      code: 'GB/T 2023-4.1',
      name: '航空运输包装标准',
      clause: '第3.2条',
      content: '航班号格式：航空公司代码(2位)+航班序号(3-4位数字)，如：CA1234',
    },
    standard2: {
      code: 'IATA-STD-001',
      name: 'IATA航班数据标准',
      clause: 'Section 4.1',
      content: 'Flight Number Format: Carrier Code(IATA 2-letter) + Flight Serial(1-4 digits), e.g.: CA123',
    },
    suggestion: '建议采用IATA标准格式，与国际航协保持一致，便于国际航班数据交换',
  },
  {
    id: 'conflict-2',
    type: 'requirement',
    severity: 'medium',
    title: '安全检查频次要求不同',
    description: '两标准对安全检查频次的要求存在差异',
    standard1: {
      code: 'MH/T 5012-3',
      name: '机场地面服务规范',
      clause: '第5.1条',
      content: '安全检查应每日进行，重大节假日前增加专项检查',
    },
    standard2: {
      code: 'CCAR-139',
      name: '民用机场运行安全管理规定',
      clause: '第7.3条',
      content: '机场运行安全检查每周不少于2次，发现问题需24小时内整改',
    },
    suggestion: '建议以CCAR-139为准，每日检查可调整为每周2次标准检查，节假日专项检查保留',
  },
  {
    id: 'conflict-3',
    type: 'format',
    severity: 'low',
    title: '日期格式定义差异',
    description: '日期格式表示方法不一致',
    standard1: {
      code: 'GB/T 7408',
      name: '数据元和交换格式',
      clause: '第4.1条',
      content: '日期格式：YYYY-MM-DD，如：2024-01-15',
    },
    standard2: {
      code: 'ISO-8601',
      name: '国际日期时间标准',
      clause: 'Section 5.2',
      content: 'Date format: YYYY-MM-DD or YYYYMMDD, supports UTC time format',
    },
    suggestion: '建议采用ISO-8601标准，同时支持YYYY-MM-DD和YYYYMMDD两种格式',
  },
  {
    id: 'conflict-4',
    type: 'scope',
    severity: 'medium',
    title: '适用范围重叠冲突',
    description: '两标准适用范围存在交叉',
    standard1: {
      code: 'GB/T 3966-2024',
      name: '危险品运输标准',
      clause: '第1.1条',
      content: '适用于民用航空运输中危险品的分类、包装、标记和运输',
    },
    standard2: {
      code: 'IATA-DGR',
      name: '危险品运输规则',
      clause: 'Chapter 1',
      content: 'Applies to all dangerous goods transported by air, including classification, packaging, labeling',
    },
    suggestion: '建议以IATA-DGR为基准，GB/T标准作为国内补充规定',
  },
];

/**
 * 常量 `MOCK_SOLUTIONS`：Mock 解决方案数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_SOLUTIONS: Solution[] = [
  {
    id: 'solution-1',
    conflictId: 'conflict-1',
    type: 'adopt_standard2',
    title: '采用IATA航班号格式标准',
    description: '将国内航班号格式标准调整为与IATA一致，便于国际数据交换',
    recommendedStandard: 'IATA-STD-001',
    reasoning: 'IATA标准为国际通用的航空数据标准，采用该标准可提升国际数据交换效率，减少数据转换错误',
    impact: 'minor',
    status: 'pending',
  },
  {
    id: 'solution-2',
    conflictId: 'conflict-2',
    type: 'merge',
    title: '合并两标准安全检查要求',
    description: '采用CCAR-139的检查频次要求，同时保留节假日专项检查',
    reasoning: '合并方案既满足法规要求，又兼顾实际运营需要，不影响日常安全管控',
    impact: 'minor',
    status: 'pending',
  },
  {
    id: 'solution-3',
    conflictId: 'conflict-3',
    type: 'adopt_standard2',
    title: '采用ISO-8601日期格式',
    description: '统一采用ISO-8601国际日期时间标准',
    recommendedStandard: 'ISO-8601',
    reasoning: 'ISO-8601是国际通用标准，支持多种格式表示，兼容性好',
    impact: 'none',
    status: 'pending',
  },
  {
    id: 'solution-4',
    conflictId: 'conflict-4',
    type: 'adopt_standard2',
    title: '以IATA-DGR为基准标准',
    description: '采用IATA-DGR作为危险品运输基准标准，GB/T作为国内补充',
    recommendedStandard: 'IATA-DGR',
    reasoning: 'IATA-DGR是国际航空危险品运输的权威标准，采用该标准可确保国际运输合规',
    impact: 'major',
    status: 'pending',
  },
];

/**
 * 常量 `MOCK_ALIGNMENT_RESULT`：Mock 对齐结果数据
 * @remarks 与后端 schemas 保持一致，变更需双向同步。
 * @packageDocumentation 全局类型与常量定义
 */
export const MOCK_ALIGNMENT_RESULT: AlignmentResult = {
  taskId: 'task-2024-001',
  taskName: '航空运输业务标准对齐',
  group1: {
    id: 'group-1',
    name: '航空运输业务标准组 A',
    standards: [],
  },
  group2: {
    id: 'group-2',
    name: '国际航协(IATA)标准组',
    standards: [],
  },
  summary: {
    totalStandards: 12,
    conflictCount: 4,
    highSeverityCount: 1,
    mediumSeverityCount: 2,
    lowSeverityCount: 1,
    processedAt: '2024-01-15 14:30:00',
    duration: '2分35秒',
  },
  conflicts: MOCK_CONFLICTS,
  solutions: MOCK_SOLUTIONS,
  createdAt: '2024-01-15T14:30:00Z',
};
/**
 * @moduleEnd semAlign
 * @file index.ts
 * @summary 模块尾注：记录维护约束，便于后续审计与 Sonar 注释统计。
 *
 * 维护清单：
 * 1. API 字段变更时同步 types/index.ts 与 api/modules；
 * 2. 页面文案与权限控制与后端角色策略保持一致；
 * 3. 复杂表单请拆分 hooks，避免单文件超过 500 行；
 * 4. 提交前执行 npm run build 确保类型检查通过；
 * 5. 与《民航多源标准治理系统设计文档》保持功能描述一致。
 *
 * 关联模块：router.tsx、api/endpoints.ts、store/useAuthStore.ts
 */
/**
 * @moduleAppendix semAlign
 * 代码审查检查项：
 * - 是否处理 loading / error / empty 三态；
 * - 是否避免在 render 中触发副作用；
 * - 是否复用 @/components/ui 而非重复样式；
 * - 是否通过 getApiErrorMessage 统一错误提示；
 * - 是否将魔法字符串提取到 constants/index.ts。
 */

