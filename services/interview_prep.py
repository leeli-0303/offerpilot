"""Rule-based interview preparation content generator.

Generates a preparation package for a job application, including
job summary, experience highlights, likely questions, and suggested
counter-questions.  No LLM calls.
"""

import random
from typing import Optional


# ── Question templates ───────────────────────────────────────────────────

# Generic behavioural questions for new grads (Chinese tech interview context)
_BEHAVIORAL_QUESTIONS = [
    "请做一个简单的自我介绍（控制在 2 分钟内）",
    "你为什么选择我们公司？你对我们公司了解多少？",
    "请描述一个你在项目中遇到的最大技术挑战，以及你是如何解决的",
    "在团队协作中，你如何处理意见分歧？请举一个具体的例子",
    "你对自己未来 3-5 年的职业规划是什么？",
    "请分享一个你主动学习新技术并快速应用到项目中的例子",
    "你是如何管理时间和优先级的？尤其是在多任务并行的情况下",
    "描述一次你从失败中学到经验教训的经历",
]

# Technical skill → typical question template
_SKILL_QUESTION_TEMPLATES = {
    "Java": "请谈谈你对 Java 中 JVM 内存模型的理解，以及常见的 GC 算法",
    "Python": "Python 的 GIL 是什么？在什么场景下会影响性能，如何规避？",
    "Go": "请谈谈 Go 语言的并发模型（goroutine / channel），和线程模型的区别",
    "Golang": "请谈谈 Go 语言的并发模型（goroutine / channel），和线程模型的区别",
    "Spring": "Spring Boot 的自动配置原理是什么？你如何自定义一个 starter？",
    "Spring Boot": "Spring Boot 的自动配置原理是什么？你如何自定义一个 starter？",
    "MySQL": "MySQL 的索引底层结构是什么？什么情况下索引会失效？",
    "Redis": "Redis 有哪些常见的数据结构？缓存穿透、击穿、雪崩分别是什么？",
    "Kafka": "Kafka 如何保证消息不丢失？什么是 ISR 机制？",
    "Docker": "Docker 镜像的分层结构是怎样的？如何优化镜像大小？",
    "Kubernetes": "请解释 Kubernetes 中 Pod、Service、Deployment 之间的关系",
    "微服务": "微服务架构中如何处理服务发现、负载均衡和熔断降级？",
    "React": "React 中的虚拟 DOM 是什么？Fiber 架构解决了什么问题？",
    "Vue": "Vue 的响应式原理是什么？Vue3 的 Proxy 相比 Vue2 的 defineProperty 有什么优势？",
    "算法": "请手写一个快速排序，并分析其时间复杂度和空间复杂度",
    "机器学习": "请解释过拟合和欠拟合，以及常见的正则化方法",
    "深度学习": "Transformer 的自注意力机制是什么？为什么它比 RNN 更适合处理长序列？",
    "SQL": "请写一条 SQL 查询每个部门工资排名前 3 的员工（窗口函数）",
    "数据分析": "请描述一个你完整参与的数据分析项目，从数据采集到最终结论",
    "Git": "Git 中 merge 和 rebase 的区别是什么？各适用于什么场景？",
    "Linux": "如何排查服务器 CPU 使用率过高的问题？常用的性能分析工具有哪些？",
    "C++": "请解释 C++ 中的虚函数表（vtable）和虚函数调用机制",
    "JavaScript": "请解释 JavaScript 的事件循环（Event Loop）和宏任务/微任务",
    "TypeScript": "TypeScript 的泛型和类型推断是如何工作的？",
}

# Generic counter-questions for new grads
_COUNTER_QUESTIONS = [
    "请问团队目前的技术栈和主要项目方向是什么？",
    "对于应届生，公司的培养体系和新员工培训是怎样的？",
    "团队现在面临的最大技术挑战是什么？",
    "日常工作中，代码评审和知识分享的流程是怎样的？",
    "公司对技术博客、开源贡献是否有支持？",
    "团队的人员结构和协作方式是怎样？（比如前端：后端：测试的比例）",
    "入职后前 3 个月的期望是什么？新人如何快速上手？",
    "公司的技术演进方向是什么？（比如是否在迁移到微服务/云原生）",
]


# ── Core generator ───────────────────────────────────────────────────────

def generate_interview_prep(application, job, resume=None) -> dict:
    """Generate an interview preparation package for an application.

    Args:
        application: An ``Application`` instance.
        job: The ``Job`` linked to this application.
        resume: Optional ``ResumeVersion`` for personalised highlights.

    Returns:
        A dict with keys:
          - **job_summary** (str): brief summary of job requirements
          - **key_experiences** (list[str]): experiences to highlight
          - **likely_questions** (list[str]): 5 questions you might be asked
          - **counter_questions** (list[str]): 3 questions to ask the interviewer
          - **prep_tips** (list[str]): general preparation tips
    """
    job_skills = job.jd_parsed_fields.get("skills", []) or []
    job_keywords = job.jd_parsed_fields.get("keywords", []) or []
    company = job.company or "该公司"
    job_title = job.title or "该岗位"
    direction = job.direction or ""

    # ── 1. Job summary ───────────────────────────────────────────────
    job_summary = _build_job_summary(company, job_title, direction, job_skills, job_keywords)

    # ── 2. Key experiences to highlight ──────────────────────────────
    key_experiences = _build_key_experiences(resume, job_skills, direction)

    # ── 3. Likely questions (5) ──────────────────────────────────────
    likely_questions = _build_likely_questions(job_skills, direction, resume)

    # ── 4. Counter-questions (3) ─────────────────────────────────────
    counter_questions = _build_counter_questions(direction)

    # ── 5. Prep tips ─────────────────────────────────────────────────
    prep_tips = _build_prep_tips(company, job_title)

    return {
        "job_summary": job_summary,
        "key_experiences": key_experiences,
        "likely_questions": likely_questions,
        "counter_questions": counter_questions,
        "prep_tips": prep_tips,
    }


# ── LLM-based interview prep ─────────────────────────────────────────────

def generate_interview_prep_with_llm(application, job, resume=None) -> dict:
    """Generate an interview preparation package via LLM, with rule-based fallback.

    Uses ``call_llm_json()`` for robust JSON extraction — it handles
    markdown code fences, stray text, and other common LLM output quirks.

    On any failure (LLM error, invalid JSON, etc.) automatically falls back
    to the rule-based ``generate_interview_prep()`` and sets ``_fallback``
    on the result dict so the UI can warn the user.

    Args:
        application: An ``Application`` instance.
        job: The ``Job`` linked to this application.
        resume: Optional ``ResumeVersion`` for personalised content.

    Returns:
        A dict with keys: job_summary, key_experiences, likely_questions,
        counter_questions, prep_tips.  Check ``_fallback`` to see whether
        rule-based fallback was used.
    """
    from services.llm_client import call_llm_json

    # ── Gather inputs ──────────────────────────────────────────────────
    job_skills = job.jd_parsed_fields.get("skills", []) or []
    job_keywords = job.jd_parsed_fields.get("keywords", []) or []
    job_direction = job.direction or ""
    job_location = job.location or ""
    jd_text = (job.jd_raw_text or "")[:2500]

    resume_keywords = resume.keywords if resume else []
    resume_highlights = resume.highlights if resume else []
    resume_name = resume.version_name if resume else "未指定"
    resume_direction = resume.target_direction if resume else ""
    app_status = application.status or "已投递"
    app_channel = application.channel or ""

    # ── Build the prompts ──────────────────────────────────────────────
    system_prompt = (
        "你是一个专业的求职面试辅导专家，帮助中国应届生准备技术面试。\n\n"
        "重要规则：\n"
        "1. 所有建议必须基于简历中已有的关键词和项目亮点。绝对不要编造或假设候选人拥有简历中没有的经历\n"
        "2. STAR 回答技巧要结合简历中的具体项目，给出可操作的指导\n"
        "3. 可能被问到的问题要结合岗位要求的技术栈和简历中的项目经验\n"
        "4. 反问面试官的问题要体现候选人对岗位和团队的真诚兴趣\n"
        "5. 内容用中文输出，适合中国应届生求职场景\n"
        "6. 内容简洁实用，每条不超过 80 字\n"
        "7. 只输出 JSON 对象，不要输出任何解释文字、Markdown 标记或代码块"
    )

    # Build highlights text
    if resume_highlights:
        highlights_str = "\n".join(f"- {h}" for h in resume_highlights)
    else:
        highlights_str = "（未填写）"

    user_prompt = (
        "请为以下投递记录生成面试准备包，输出 JSON。\n\n"
        "输出 JSON 格式（严格遵循，所有字段必须存在）：\n"
        "{\n"
        '  "job_summary": "岗位要求的简短摘要（2-3句话）",\n'
        '  "key_experiences_to_highlight": ["面试中应重点强调的经历1", "经历2", "经历3"],\n'
        '  "likely_questions": ["可能被问到的技术/行为问题1", "问题2", ..., "问题5"],\n'
        '  "star_answer_tips": ["STAR回答技巧1", "技巧2", "技巧3"],\n'
        '  "questions_to_ask_interviewer": ["建议反问面试官的问题1", "问题2", "问题3"]\n'
        "}\n\n"
        "字段说明：\n"
        "- job_summary: 简要概括岗位核心要求\n"
        "- key_experiences_to_highlight: 面试中应重点强调的经历/技能点\n"
        "- likely_questions: 5 个可能被问到的问题（技术+行为）\n"
        "- star_answer_tips: 针对简历项目给出 STAR 法则回答技巧\n"
        "- questions_to_ask_interviewer: 3 个建议反问面试官的问题\n\n"
        "=== 岗位信息 ===\n"
        f"公司：{job.company}\n"
        f"岗位：{job.title}\n"
        f"方向：{job_direction or '（未设置）'}\n"
        f"地点：{job_location or '（未设置）'}\n"
        f"要求技能：{', '.join(job_skills) if job_skills else '（未提取）'}\n"
        f"岗位标签：{', '.join(job_keywords) if job_keywords else '（未提取）'}\n"
        f"JD 内容：\n{jd_text}\n\n"
        "=== 简历信息 ===\n"
        f"简历版本：{resume_name}\n"
        f"目标方向：{resume_direction or '不限'}\n"
        f"核心关键词：{', '.join(resume_keywords) if resume_keywords else '（未设置）'}\n"
        f"项目亮点：\n{highlights_str}\n\n"
        "=== 投递状态 ===\n"
        f"当前状态：{app_status}\n"
        f"投递渠道：{app_channel or '（未设置）'}\n\n"
        "请直接输出 JSON 对象。不要包含 ```json 标记或任何其他文字。"
    )

    # ── Build fallback result once (reused on any failure path) ─────────
    fallback = generate_interview_prep(application, job, resume)
    fallback["_fallback"] = True
    fallback["_raw_output"] = ""

    # ── Call LLM ──────────────────────────────────────────────────────
    try:
        result = call_llm_json(user_prompt, system_prompt=system_prompt)
    except Exception as exc:
        fallback["_fallback_reason"] = f"AI 调用异常（{exc}），已回退到规则生成"
        return fallback

    if not result.get("success"):
        err = result.get("error", "未知错误")
        fallback["_fallback_reason"] = f"AI 返回解析失败：{err}"
        return fallback

    # ── Normalize & validate ──────────────────────────────────────────
    data = result.get("data", {})
    raw_output = result.get("raw_output", "")

    try:
        prep = _normalize_llm_prep_result(data)
        # Validate: at minimum need job_summary or some questions
        if not prep.get("job_summary") and not prep.get("likely_questions"):
            fallback["_fallback_reason"] = (
                "AI 返回的关键字段为空（job_summary 和 likely_questions 均为空），已回退到规则生成"
            )
            return fallback
        prep["_fallback"] = False
        prep["_raw_output"] = raw_output
        return prep
    except Exception as exc:
        fallback["_fallback_reason"] = (
            f"AI 返回数据格式异常（{exc}），已回退到规则生成"
        )
        return fallback


def _normalize_llm_prep_result(raw: dict) -> dict:
    """Normalize LLM JSON into the same dict shape as the rule-based generator.

    Maps LLM field names → rule-based field names:
      key_experiences_to_highlight → key_experiences
      questions_to_ask_interviewer  → counter_questions
      star_answer_tips              → prep_tips
    """
    def _list_of_str(key: str) -> list[str]:
        val = raw.get(key, [])
        if not isinstance(val, list):
            return []
        return [str(v).strip() for v in val if str(v).strip()]

    return {
        "job_summary": str(raw.get("job_summary", "")).strip(),
        "key_experiences": _list_of_str("key_experiences_to_highlight"),
        "likely_questions": _list_of_str("likely_questions"),
        "counter_questions": _list_of_str("questions_to_ask_interviewer"),
        "prep_tips": _list_of_str("star_answer_tips"),
    }


# ── Internal builders ────────────────────────────────────────────────────

def _build_job_summary(company: str, title: str, direction: str,
                       skills: list[str], keywords: list[str]) -> str:
    """Build a one-paragraph job requirements summary."""
    parts = [f"目标公司：{company}", f"岗位名称：{title}"]
    if direction:
        parts.append(f"岗位方向：{direction}")
    if skills:
        parts.append(f"核心技能要求：{'、'.join(skills[:8])}")
    if keywords:
        parts.append(f"岗位关键标签：{'、'.join(keywords)}")

    return "；".join(parts)


def _build_key_experiences(resume, job_skills: list[str], direction: str) -> list[str]:
    """Generate 3-5 key experience highlights for the interview."""
    highlights: list[str] = []

    # From resume highlights
    if resume and resume.highlights:
        for h in resume.highlights[:3]:
            highlights.append(f"重点准备项目经历：{h}，准备好 STAR 描述（背景、任务、行动、结果）")

    # From skill overlap
    if resume and resume.keywords and job_skills:
        matched = [s for s in job_skills
                   if any(s.lower() in k.lower() or k.lower() in s.lower()
                          for k in resume.keywords)]
        if matched:
            highlights.append(
                f"强调技术栈匹配：{'、'.join(matched[:5])} — "
                f"准备用具体项目证明掌握程度"
            )

    # From direction
    if direction and resume and resume.target_direction == direction:
        highlights.append(
            f"突出方向匹配：简历方向「{direction}」与岗位一致，"
            f"强调在该方向的积累和兴趣"
        )

    # Generic highlights for new grads
    if len(highlights) < 3:
        highlights.append("强调学习能力和快速上手能力 — 应届生的核心优势")
    if len(highlights) < 3:
        highlights.append("准备 1-2 个体现团队协作的校园/实习经历")
    if len(highlights) < 3:
        highlights.append("如有竞赛、开源贡献或论文，务必在面试中主动提及")

    return highlights[:5]


def _build_likely_questions(skills: list[str], direction: str, resume=None) -> list[str]:
    """Build a list of 5 likely interview questions."""
    questions: list[str] = []

    # Technical questions based on detected skills
    for skill in skills:
        if skill in _SKILL_QUESTION_TEMPLATES:
            q = _SKILL_QUESTION_TEMPLATES[skill]
            if q not in questions:
                questions.append(q)
        if len(questions) >= 3:
            break

    # Direction-specific question
    if direction and len(questions) < 4:
        direction_questions = {
            "后端": "请设计一个短链接系统（类似 TinyURL），需要考虑高并发和持久化",
            "前端": "请实现一个简单的虚拟滚动列表组件，需要支持动态加载和回收",
            "算法": "给定一个大规模语料，请设计一个文本分类系统的完整 pipeline",
            "数据": "请设计一个数据看板的指标体系，平衡实时性和准确性",
            "产品": "请分析一款你常用的产品，指出它的三个优点和一个可以改进的地方",
            "客户端": "请描述 App 启动优化的完整方案，从冷启动到界面渲染",
        }
        dq = direction_questions.get(direction)
        if dq and dq not in questions:
            questions.append(dq)

    # Behavioral questions to fill up to 5
    shuffled = list(_BEHAVIORAL_QUESTIONS)
    random.shuffle(shuffled)
    for bq in shuffled:
        if bq not in questions and len(questions) < 5:
            questions.append(bq)

    # Ensure exactly 5
    while len(questions) < 5:
        fallback = [
            "请介绍一下你最有代表性的一个项目",
            "你认为你在这次面试中的优势和劣势分别是什么？",
            "你的期望薪资范围是多少？",
            "你还有什么问题想问我吗？",
        ]
        for fq in fallback:
            if fq not in questions and len(questions) < 5:
                questions.append(fq)

    return questions[:5]


def _build_counter_questions(direction: str) -> list[str]:
    """Pick 3 good questions for the candidate to ask the interviewer."""
    # Always include one direction-relevant question
    direction_q = {
        "后端": "团队目前主要使用什么技术栈？是否有自研框架或中间件？",
        "前端": "团队的前端工程化体系是怎样的？用哪些工具链和 CI/CD？",
        "算法": "团队在模型部署和在线推理方面遇到的主要挑战是什么？",
        "数据": "团队的数据基础设施是怎样的？数据治理和质量保障如何做的？",
        "产品": "产品的需求发现和优先级排序流程是怎样的？",
        "客户端": "团队的客户端发版节奏和热修复方案是怎样的？",
    }

    selected: list[str] = []

    # Direction-specific
    dq = direction_q.get(direction)
    if dq:
        selected.append(dq)

    # Generic useful ones
    shuffled = list(_COUNTER_QUESTIONS)
    random.shuffle(shuffled)
    for q in shuffled:
        if q not in selected and len(selected) < 3:
            selected.append(q)
        if len(selected) >= 3:
            break

    # Ensure exactly 3
    while len(selected) < 3:
        fb = [
            "请问面试流程的下一步是什么？大概多久会有反馈？",
            "如果有幸加入，我可以在入职前做哪些准备？",
        ]
        for fq in fb:
            if fq not in selected and len(selected) < 3:
                selected.append(fq)

    return selected[:3]


def _build_prep_tips(company: str, job_title: str) -> list[str]:
    """Generate general preparation tips."""
    return [
        f"提前了解 {company} 的最新动态（产品发布、融资、技术博客等），在面试中展现对公司的关注",
        f"仔细阅读「{job_title}」的 JD，逐条对照自己的经历，准备对应的回答",
        "准备 2-3 个具体的项目案例，每个都按 STAR 法则（情境、任务、行动、结果）组织",
        "提前准备简洁的自我介绍（1-2 分钟版本），重点突出与岗位匹配的技能和经历",
        "面试当天确保网络和设备正常；提前 5-10 分钟进入会议室/链接",
    ]
