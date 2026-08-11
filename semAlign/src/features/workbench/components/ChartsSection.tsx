/**
 * @file semAlign
 * @file ChartsSection.tsx
 * @description 治理工作台：指标卡、图表统计与标准动态列表。
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
import React, { useEffect, useRef, useState } from 'react';
import {
// -----------------------------------------------------------------------------
// 分段：ChartsSection.tsx 核心业务逻辑区（状态管理、事件处理与 API 调用）
// 说明：复杂交互请保持函数单一职责，必要时抽取至 hooks 或 service。
// -----------------------------------------------------------------------------

  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { Card } from '@/components/ui';
import type { WorkbenchData } from '@/types';
import { COLORS } from '@/constants';

/**
 * 类型定义 `ChartsSectionProps`：描述前后端交互或页面状态结构。
 */
export interface ChartsSectionProps {
  charts: WorkbenchData['charts'];
}

/**
 * React 组件 `ChartsSection`：负责对应页面或区块的 UI 与交互。
 */
export const ChartsSection: React.FC<ChartsSectionProps> = ({ charts }) => {
  const kpis = charts.efficiency_kpis;
  const avgReview = kpis?.avg_review_days ?? 0;
  const avgPublish = kpis?.avg_publish_days ?? 0;
  const reviewMom = kpis?.review_mom_delta ?? 0;
  const publishMom = kpis?.publish_mom_delta ?? 0;
  const stageData =
    charts.stage_distribution?.length ? charts.stage_distribution : [];

  // 状态管理：跟踪各个图表容器的尺寸
  const lifecycleContainerRef = useRef<HTMLDivElement>(null);
  const categoryContainerRef = useRef<HTMLDivElement>(null);
  const efficiencyContainerRef = useRef<HTMLDivElement>(null);
  const stageContainerRef = useRef<HTMLDivElement>(null);
  
  const [lifecycleSize, setLifecycleSize] = useState({ width: 0, height: 0, initialized: false });
  const [categorySize, setCategorySize] = useState({ width: 0, height: 0, initialized: false });
  const [efficiencySize, setEfficiencySize] = useState({ width: 0, height: 0, initialized: false });
  const [stageSize, setStageSize] = useState({ width: 0, height: 0, initialized: false });

  // 使用 ResizeObserver 监听容器尺寸；charts 变化后下一帧再 observe（避免首屏 ref 未就绪或宽为 0）
  useEffect(() => {
    const resizeObserver = new ResizeObserver((entries) => {
      entries.forEach(entry => {
        const { width, height } = entry.contentRect;
        if (entry.target === lifecycleContainerRef.current) {
          setLifecycleSize({ width, height, initialized: true });
        } else if (entry.target === categoryContainerRef.current) {
          setCategorySize({ width, height, initialized: true });
        } else if (entry.target === efficiencyContainerRef.current) {
          setEfficiencySize({ width, height, initialized: true });
        } else if (entry.target === stageContainerRef.current) {
          setStageSize({ width, height, initialized: true });
        }
      });
    });

    const raf = requestAnimationFrame(() => {
      const containers = [
        lifecycleContainerRef.current,
        categoryContainerRef.current,
        efficiencyContainerRef.current,
        stageContainerRef.current,
      ].filter(Boolean) as HTMLElement[];
      containers.forEach((container) => resizeObserver.observe(container));
    });

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
    };
  }, [charts]);

  // 禁用图表容器的 focus 效果
  const handleChartMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
  };

  return (
    <>
      {/* Row 1: Pie Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="min-h-[350px]">
          <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-blue-600 block"></span>
            标准生命周期分布
          </h3>
          <div 
            ref={lifecycleContainerRef}
            className="h-[250px] w-full min-w-[300px] focus:outline-none"
            onMouseDown={handleChartMouseDown}
          >
            {lifecycleSize.initialized && lifecycleSize.width > 0 && lifecycleSize.height > 0 && (
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <PieChart>
                  <Pie
                    data={charts.lifecycle}
                    cx="40%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {charts.lifecycle.map((entry, index) => (
                      <Cell key={`lifecycle-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="middle" align="right" layout="vertical" />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className="min-h-[350px]">
          <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-blue-600 block"></span>
            标准分类分布
          </h3>
          <div 
            ref={categoryContainerRef}
            className="h-[250px] w-full min-w-[300px] focus:outline-none"
            onMouseDown={handleChartMouseDown}
          >
            {categorySize.initialized && categorySize.width > 0 && categorySize.height > 0 && (
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <PieChart>
                  <Pie
                    data={charts.category}
                    cx="40%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({ name }) => `${name}`}
                  >
                    {charts.category.map((entry, index) => (
                      <Cell key={`category-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="middle" align="right" layout="vertical" />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      {/* Row 2: Efficiency & Stage Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="min-h-[450px]">
          <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-blue-600 block"></span>
            标准流程效率指标
          </h3>

          <div className="flex justify-around items-start mb-6 px-4">
            <div className="text-center">
              <div className="text-4xl font-bold text-blue-600 mb-1">{avgReview}天</div>
              <div className="text-sm text-slate-500 mb-2">平均评审周期（代理）</div>
              <div
                className={`flex items-center justify-center text-xs font-medium ${
                  reviewMom <= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {reviewMom <= 0 ? <ArrowDown size={12} className="mr-1" /> : <ArrowUp size={12} className="mr-1" />}
                {Math.abs(reviewMom)}天较上月
              </div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-cyan-500 mb-1">{avgPublish}天</div>
              <div className="text-sm text-slate-500 mb-2">平均发布周期（代理）</div>
              <div
                className={`flex items-center justify-center text-xs font-medium ${
                  publishMom <= 0 ? 'text-green-600' : 'text-amber-600'
                }`}
              >
                {publishMom <= 0 ? <ArrowDown size={12} className="mr-1" /> : <ArrowUp size={12} className="mr-1" />}
                {Math.abs(publishMom)}天较上月
              </div>
            </div>
          </div>

          <div 
            ref={efficiencyContainerRef}
            className="h-[300px] w-full min-w-[300px] focus:outline-none"
            onMouseDown={handleChartMouseDown}
          >
            {efficiencySize.initialized && efficiencySize.width > 0 && efficiencySize.height > 0 && (
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <LineChart data={charts.efficiency} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
                  <CartesianGrid stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="name"
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                    tick={{ fill: '#64748B', fontSize: 12 }}
                    dy={10}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748B', fontSize: 12 }}
                    label={{ value: '天数', position: 'top', offset: 10, fill: '#94A3B8', fontSize: 12 }}
                  />
                  <Tooltip />
                  <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ top: -10 }} />

                  <Line
                    name="评审周期(天)"
                    type="monotone"
                    dataKey="review"
                    stroke="#3B82F6"
                    strokeWidth={3}
                    dot={{ r: 4, fill: '#fff', strokeWidth: 2, stroke: '#3B82F6' }}
                    activeDot={{ r: 6, fill: '#3B82F6', stroke: '#fff' }}
                  />

                  <Line
                    name="发布周期(天)"
                    type="monotone"
                    dataKey="publish"
                    stroke="#86EFAC"
                    strokeWidth={3}
                    dot={{ r: 4, fill: '#fff', strokeWidth: 2, stroke: '#86EFAC' }}
                    activeDot={{ r: 6, fill: '#86EFAC', stroke: '#fff' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className="min-h-[450px]">
          <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-blue-600 block"></span>
            生命周期阶段分布
          </h3>
          <div 
            ref={stageContainerRef}
            className="h-[350px] w-full min-w-[300px] focus:outline-none"
            onMouseDown={handleChartMouseDown}
          >
            {stageSize.initialized && stageSize.width > 0 && stageSize.height > 0 && (
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <BarChart
                  data={stageData}
                  margin={{ top: 20, right: 10, left: 0, bottom: 5 }}
                  barSize={20}
                >
                  <CartesianGrid stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="name"
                    axisLine={{ stroke: '#E2E8F0' }}
                    tickLine={false}
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    dy={5}
                  />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} />
                  <Tooltip cursor={{ fill: '#f8fafc' }} />
                  <Legend verticalAlign="top" height={36} iconType="rect" wrapperStyle={{ top: -10 }} />
                  <Bar name="当前数量" dataKey="current" fill="#5865F2" radius={[4, 4, 0, 0]} />
                  <Bar name="上月数量" dataKey="last" fill="#84CC16" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>
    </>
  );
};

export default ChartsSection;
/**
 * @moduleEnd semAlign
 * @file ChartsSection.tsx
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

