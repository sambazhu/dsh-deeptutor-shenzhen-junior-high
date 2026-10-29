---
name: tutor-explain
description: 调用 DeepTutor 引擎（结合深圳初一教材知识库 sz-g7-math-bsd 与秋宇错题库 qiuyu-wrongbook）对台账错题进行教材对齐精讲、双法复核、同类变式出题，并按单向写回规范更新题库.json 与错题 Word。
---

# DeepTutor 教材对齐精讲与变式出题（tutor-explain）

## 触发条件

- 家长或孩子针对台账里的某道错题要求“用 DeepTutor 讲透这道题”“按北师大课本方法讲”“出一道同类变式题”；
- 新错题入库（`wrong-question-filing`）后，需要补充教材章节依据、分步精讲或同类变式；
- 考前/周末需要根据 `qiuyu-wrongbook` 中的薄弱知识点生成针对性练习或复习路径（`mastery_path`）。

## 知识库与工具约定

| 知识库名称 | 对应学科与教材版本 | 数据方向 |
|---|---|---|
| `sz-g7-math-bsd` | 数学 · 北师大版七年级上册（209页 MinerU 公式全文，默认知识库） | 台账 `00_教材与参考书/02_数学/` → DeepTutor（只读导入） |
| `sz-g7-chinese-tb` | 语文 · 统编版七年级上册（166页全文） | 台账 `00_教材与参考书/01_语文/` → DeepTutor（只读导入） |
| `sz-g7-english-hj` | 英语 · 沪教牛津版七年级上册（169页全文） | 台账 `00_教材与参考书/03_英语/` → DeepTutor（只读导入） |
| `sz-g7-geography-xj` | 地理 · 湘教版七年级上册（136页全文） | 台账 `00_教材与参考书/04_地理/` → DeepTutor（只读导入） |
| `sz-g7-history-tb` | 历史 · 统编版七年级上册（134页全文） | 台账 `00_教材与参考书/05_历史/` → DeepTutor（只读导入） |
| `sz-g7-biology-rj` | 生物 · 人教版七年级上册（146页全文） | 台账 `00_教材与参考书/06_生物/` → DeepTutor（只读导入） |
| `sz-g7-morality-tb` | 道法 · 统编版七年级上册（114页全文） | 台账 `00_教材与参考书/07_道法/` → DeepTutor（只读导入） |
| `qiuyu-wrongbook` | 朱秋宇全科错题档案（含历史错因、知识点、变式） | 台账 `0X_学科/错题集/题库.json` → DeepTutor（只读导入） |

> **纯向量检索（`vector` 模式）查询扩写规则**：
> 当前 DeepTutor 检索配置为 `retrieval_profile: "vector"`（`qwen3.7-text-embedding` 1024维语义向量），以避免英文 BM25 分词器对中文教材产生跨主题噪声。纯向量检索对自然语言概念和具体算式判别力极强，但对孤立的「例题号、题号、短字面词」（如 `"例2"`、`"第12题"`、`"例2 加法交换律"`）不敏感。
> **规则**：调用 `deeptutor_kb(action="search")` 前，若查询含例题号、题号或少于 10 个字，必须**先扩写成包含章节背景、知识概念或具体算式的自然语言描述句**再检索（例如将 `"例2 加法交换律"` 扩写为 `"第二章 有理数的加减运算 例2 如何运用加法交换律和结合律简便计算"`）。

## 标准执行步骤

1. **读取台账错题记录**
   - 从对应学科 `0X_学科/错题集/题库.json` 读取目标题目的 `id`、`topic`、`question`、`answer`、`mistake_reason`。

2. **调用 DeepTutor 获取教材对齐精讲或变式题**
   - **首选一键工具 `deeptutor_practice`（P2 定制工具）**：
     - 直接调用 `deeptutor_practice(question_id="MATH-20261016-12", mode="both", num_variants=2)`（或 `mode="explain"` / `mode="variant"`）。
     - 该工具会自动只读检索 `题库.json`、自动挂载 `sz-g7-math-bsd` 与 `qiuyu-wrongbook`、构造北师大教材对齐与双方法验证提示词，并返回结构化的 `patch`（自带 `explanation_source: "deeptutor"` 与 `verified: false`）。
   - **通用工具 `deeptutor_run`**：
     - **错题精讲**：调用 `deeptutor_run(capability="deep_solve", subject="数学")`，Prompt 中明确要求：
       - 严格使用**深圳七年级上册（北师大版数学）**对应章节的概念与方法，严禁超纲（不用二元一次方程组、函数、相似等）；
       - 给出**主解法** + **第二种独立验证方法**（如特殊值代入检验、总棱长减未剪棱长核对、程序/枚举复核）；
       - 提炼一句适合初一学生考场记忆的**避坑口诀**。
     - **同类变式出题**：调用 `deeptutor_run(capability="deep_question", subject="数学")`，要求只改动数值或场景、保持相同核心考点与难度，附完整验算过程。
   - **孩子直接交互模式**：若为孩子生成伴学页，可传入 `child_mode=true` 或配合 `html=` 参数生成自包含交互式 HTML 学习卡，且第一屏只给思路引导与分步提示，折叠最终答案。

3. **遵循台账质量校验规则写回 `题库.json`**
   - **唯一事实源**：所有修改只写回台账 `0X_学科/错题集/题库.json`，不在 DeepTutor Notebook 另存一套错题本。
   - **必填溯源字段**：
     - `"explanation_source": "deeptutor"`
     - 若模型给出的结论尚未经过第二种方法或程序独立复核，必须设置 `"verified": false`（此时生成的 Word 讲解版会自动标注 `（DeepTutor生成 · ❓待核对）`）；
     - 若已通过第二种方法或 Python 脚本独立复核无误，将复核方式写入 `"verified"` 字符串（例如 `"2026-10-28 双法复核：①... ②..."`）。
   - **不覆盖已确认答案**：模型生成的 `answer` 绝不覆盖老师/家长已确认的标准答案。

4. **重新生成 Word 错题集并同步知识库**
   ```bash
   cd /Users/sambazhu/dshworkplace/朱秋宇初一学习台账
   ~/.deeptutor-venv/bin/python tools/build_wrongbook.py 数学
   ~/.deeptutor-venv/bin/python tools/sync_to_deeptutor.py --wrongbook
   ```
