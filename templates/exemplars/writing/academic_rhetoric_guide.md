# 顶级学术期刊长文修辞指南与交叉引用规范

## 1. 核心认知：自足性叙事（Self-contained Narrative）

学术论文不是软件代码（DRY 原则不适用），读者进行的是线性认知。每一章、每一节哪怕被孤立抽读，其核心命题与论证链条也必须完整自足。

---

## 2. 四大严禁出现的语言反模式（Writing Anti-Patterns）

| 严禁表达（反模式） | 危害分析 | 顶刊规范范式 |
| :--- | :--- | :--- |
| **① 免责甩锅式元语**<br>“不再重复”、“不赘述”、“同前所述”、“不再展开” | 打破读者心智流，把审稿人当质检员，暴露论证设计的结构性缺陷。 | **最小自足重述 + 括号锚点**：<br>`Recall from Section 3 that [半句话重述核心结论], which...` |
| **② API 说明书式电报指针**<br>“具体字段（参见5.4.3节）”、“按既定算法执行（参见5.3.2节）” | 正文丧失了物理机理概括，沦为纯软件接口文档。 | **机制意图先行**：<br>`系统通过[机制名]维持有序性，其具体实现参数详见第 5.3 节。` |
| **③ 内部合规自查便签进正文**<br>“（定位，非贡献）”、“未作扩大”、“协议要求声明” | 把内部评审便签硬贴在正文大标题与表头，暴露过度防御姿态，严重削弱学术自信。 | **从容的理论映射（Scoping）**：<br>`本节旨在厘清本文模型在经典论证理论中的理论坐标与边界。` |
| **④ 章节代号拟人化作主语**<br>“7.5 节给出了范围比……”、“图 3 证明了……” | 章节、图表只是静态载体，不能作为行动主体。 | **以物理发现/科学实体为主语**：<br>`消融实验表明[核心结论]（第 7.5 节，图 3）。` |

---

## 3. 顶刊经典学术修辞范式与替换模板库（摘自 Raft/Dropout/Spanner/T5）

### 范式 A：机制继承与扩展（扩展前文机制时，绝不写“前文已描述不再重复”）
- **顶刊例句 (Raft §5.4)**:
  > *"Section 5.4 describes how Raft ensures this property; the solution involves an additional restriction on the election mechanism described in Section 5.2."*
- **推荐中文句式**:
  > “本节重点阐述保证该一致性性质的求解算法；该方案通过对第 5.2 节所形式化的选举状态机施加额外单调性约束来实现……”

### 范式 B：前向依赖打下伏笔（在底层提及时，绝不让读者产生困惑）
- **顶刊例句 (Spanner §2)**:
  > *"... but writes are applied by Paxos in order (a fact on which we will depend in Section 4)."*
- **推荐中文句式**:
  > “……底层事件总线严格保证跨节点变更的因果时序，这一确定性保障将成为第 4 节分布式事务状态推演的前提基础。”

### 范式 C：附录优雅外溢（公式推导或实验细节太长时，以服务姿态引导）
- **顶刊例句 (Dropout §JMLR / T5 §JMLR)**:
  > *"A more detailed description of all the experiments and data sets is provided in Appendix B."*  
  > *"Converting examples to the target variant is a little more involved; we describe this process in Appendix B."*
- **推荐中文句式**:
  > “为了兼顾正文的论证主线与实验的严密可复现性，全部 20 组辩题的初始语料预处理流程与超参数分布汇总于附录 B。”

### 范式 D：学术边界从容界定（对比前人奠基工作时，展现从容掌控）
- **顶刊例句 (T5 §2)**:
  > *"Apart from the details mentioned below and the variants we explore in Section 3.2, we do not deviate significantly from this architecture as originally proposed."*
- **推荐中文句式**:
  > “经典抽象论证框架（Dung, 1995）奠定了多主体论辩的形式语义基石。为了厘清本文集合关系模型在论证理论中的定位，表 2 从论证原子、冲突表征与接受状态维护三个层面对二者进行了对比映射。”
