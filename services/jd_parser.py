"""Rule-based JD parser.

Parses raw job description text using keyword matching to extract
job type, skills, priority, and risk flags.  No LLM calls.
"""

import re
import json
from typing import Optional

# ── Job type detection ──────────────────────────────────────────────────
# (keyword list, label, mapped direction)

JOB_TYPE_RULES: list[tuple[list[str], str, str]] = [
    (
        ["LLM", "RAG", "Prompt Engineering", "AIGC", "大模型", "Agent",
         "GPT", "生成式", "ChatGPT", "LangChain", "语言模型", "多模态",
         "Fine-tuning", "RLHF", "向量数据库", "语义搜索"],
        "AI / 大模型",
        "算法",
    ),
    (
        ["SQL", "BI", "数据分析", "Tableau", "Power BI", "数据仓库",
         "ETL", "数据建模", "数据治理", "数据可视化", "ClickHouse",
         "数据报表", "指标体系", "AB测试", "A/B测试", "AB Test"],
        "数据分析",
        "数据",
    ),
    (
        ["用户增长", "转化率", "活动运营", "DAU", "留存", "增长黑客",
         "裂变", "拉新", "促活", "用户运营", "内容运营", "社群运营",
         "活动策划", "营销", "增长策略", "私域"],
        "增长 / 运营",
        "运营",
    ),
    (
        ["Java", "Spring", "Spring Boot", "Spring Cloud", "MyBatis",
         "微服务", "分布式系统", "分布式锁", "消息队列", "Kafka",
         "RabbitMQ", "RPC", "Zookeeper", "Nacos", "Dubbo",
         "后端开发", "服务端", "高并发", "高可用", "API 开发"],
        "后端开发",
        "后端",
    ),
    (
        ["React", "Vue", "Vue.js", "Angular", "前端开发", "Web前端",
         "HTML5", "CSS3", "JavaScript", "TypeScript", "Webpack",
         "Vite", "小程序", "H5", "响应式", "跨端"],
        "前端开发",
        "前端",
    ),
    (
        ["推荐系统", "推荐算法", "NLP", "自然语言处理", "CV", "计算机视觉",
         "机器学习", "深度学习", "PyTorch", "TensorFlow", "算法工程师",
         "模型训练", "模型部署", "特征工程", "神经网络", "Transformer",
         "召回", "排序", "CTR预估", "搜索算法", "广告算法"],
        "算法 / AI",
        "算法",
    ),
    (
        ["产品经理", "需求分析", "PRD", "原型设计", "Axure", "Figma",
         "用户研究", "竞品分析", "产品规划", "产品策略", "用户体验",
         "产品迭代", "产品设计"],
        "产品",
        "产品",
    ),
    (
        ["iOS", "Android", "Flutter", "React Native", "客户端开发",
         "移动端", "Swift", "Kotlin", "Objective-C", "App开发"],
        "客户端",
        "客户端",
    ),
    (
        ["自动化测试", "性能测试", "Selenium", "JUnit", "TestNG",
         "测试用例", "压力测试", "QA", "质量保障", "测试工程师",
         "回归测试", "接口测试"],
        "测试 / 质量保障",
        "其他",
    ),
    (
        ["运维", "DevOps", "Kubernetes", "K8s", "Docker", "CI/CD",
         "SRE", "监控", "告警", "发布系统", "容器化", "基础设施",
         "Terraform", "Ansible", "Jenkins", "云原生", "服务网格"],
        "运维 / 基础设施",
        "其他",
    ),
    (
        ["网络安全", "渗透测试", "安全加固", "WAF", "防火墙",
         "安全合规", "安全审计", "数据安全", "信息安全"],
        "安全",
        "安全",
    ),
    (
        ["嵌入式", "单片机", "RTOS", "Linux内核", "驱动开发",
         "硬件", "FPGA", "IoT", "物联网", "ARM"],
        "嵌入式 / 硬件",
        "其他",
    ),
    (
        ["Go", "Golang", "Gin", "Echo", "gRPC", "Go-Zero"],
        "后端开发",
        "后端",
    ),
]

# ── Skill keyword bank ──────────────────────────────────────────────────

SKILL_BANK: dict[str, list[str]] = {
    "编程语言": ["Python", "Java", "Go", "Golang", "C++", "C#",
                  "JavaScript", "TypeScript", "Rust", "Scala",
                  "Kotlin", "Swift", "PHP", "Ruby", "MATLAB", "R"],
    "框架": ["Spring", "Spring Boot", "Spring Cloud", "Django", "Flask",
             "FastAPI", "React", "Vue", "Vue.js", "Angular", "Node.js",
             "Express", "Next.js", "Nuxt", "Gin", "Echo", "Koa",
             "MyBatis", "Hibernate", "JPA", "ASP.NET"],
    "数据库 / 存储": ["MySQL", "PostgreSQL", "MongoDB", "Redis",
                      "Elasticsearch", "ES", "ClickHouse", "HBase",
                      "TiDB", "Cassandra", "Neo4j", "HDFS",
                      "MinIO", "Ceph", "Etcd"],
    "消息 / 中间件": ["Kafka", "RabbitMQ", "RocketMQ", "Pulsar",
                      "Nacos", "Zookeeper", "Consul", "Apollo"],
    "云 / 基础设施": ["AWS", "Azure", "GCP", "阿里云", "腾讯云",
                      "Kubernetes", "K8s", "Docker", "Terraform",
                      "Ansible", "Jenkins", "Prometheus", "Grafana",
                      "ELK", "Serverless", "Lambda"],
    "AI / ML": ["PyTorch", "TensorFlow", "Scikit-learn", "Pandas",
                "NumPy", "XGBoost", "LightGBM", "Spark", "Flink",
                "Hadoop", "MLflow", "Kubeflow", "Jupyter",
                "Hugging Face", "Transformers", "OpenCV"],
    "工具 / 其他": ["Git", "Linux", "Shell", "Nginx", "GraphQL",
                    "gRPC", "WebSocket", "OAuth", "JWT", "SSO",
                    "微服务", "DDD", "TDD", "敏捷开发", "Scrum"],
}

# ── Keyword extraction ──────────────────────────────────────────────────

KEYWORD_PATTERNS: list[tuple[list[str], str]] = [
    (["校招", "应届", "毕业生", "New Grad", "Campus", "2026届", "2025届",
      "2027届"], "校招 / 应届"),
    (["实习", "Intern", "Internship"], "实习"),
    (["本科", "硕士", "博士", "Bachelor", "Master", "PhD"], "学历要求"),
    (["985", "211", "双一流", "海归"], "院校偏好"),
    (["内推", "急招", "大量HC", "海量HC"], "内推 / 急招"),
    (["电商", "金融", "云计算", "SaaS", "企业服务", "游戏",
      "社交", "短视频", "直播", "在线教育", "医疗"], "行业领域"),
    (["北京", "上海", "深圳", "杭州", "广州", "成都", "南京",
      "武汉", "西安", "苏州"], "工作城市"),
    (["远程", "Remote", "居家办公", "混合办公"], "远程办公"),
    (["15薪", "16薪", "14薪", "年终奖", "期权", "股票", "RSU"], "薪酬福利"),
]

# ── Priority detection ──────────────────────────────────────────────────

PRIORITY_RULES: list[tuple[list[str], str]] = [
    (["急招", "尽快到岗", "立即入职", "优先", "紧急", "加急",
      "快速入职", "一周内到岗", "快速到岗"], "高"),
    (["长期有效", "储备", "人才库", "人才储备", "常年招聘"], "低"),
]

# ── Risk detection ──────────────────────────────────────────────────────

RISK_RULES: list[tuple[str, str]] = [
    (r"99[56]", "提醒：JD 提及 996，可能存在加班文化"),
    (r"大小周", "提醒：JD 提及大小周工作制"),
    (r"加班|高强度|抗压", "提示：JD 提及加班 / 高强度 / 抗压"),
    (r"外包|派遣|驻场|外派", "注意：可能为外包或驻场岗位，确认合同关系"),
    (r"薪资面议|待遇面议|薪酬面议", "注意：薪资不透明，建议面试时确认"),
    (r"博士优先|博士及以上", "注意：学历门槛较高（博士优先）"),
    (r"要求.*\d+.*年.*经验", "注意：岗位可能要求非应届经验"),
    (r"社招|社会招聘", "注意：岗位明确标注社招，投递前确认是否接受应届生"),
]


# ── Public API ──────────────────────────────────────────────────────────

def parse_jd_rule_based(jd_text: str) -> dict:
    """Parse a raw JD string into structured fields using rule-based matching.

    Args:
        jd_text: The full job description text.

    Returns:
        A dict with keys:
          - job_type: human-readable job category label
          - job_type_direction: mapped DIRECTION_OPTIONS value
          - skills: list of detected tech skills
          - keywords: list of notable non-skill keywords
          - priority: "高" / "中" / "低"
          - risk_notes: list of warning strings
    """
    text = jd_text.strip() if jd_text else ""
    if not text:
        return _empty_result()

    text_lower = text.lower()

    job_type, job_type_direction = _detect_job_type(text)
    skills = _extract_skills(text)
    keywords = _extract_keywords(text)
    priority = _detect_priority(text)
    risk_notes = _detect_risks(text)

    return {
        "job_type": job_type,
        "job_type_direction": job_type_direction,
        "skills": skills,
        "keywords": keywords,
        "priority": priority,
        "risk_notes": risk_notes,
    }


# ── Internal helpers ────────────────────────────────────────────────────

def _empty_result() -> dict:
    return {
        "job_type": "",
        "job_type_direction": "",
        "skills": [],
        "keywords": [],
        "priority": "中",
        "risk_notes": [],
    }


def _detect_job_type(text: str) -> tuple[str, str]:
    """Return (job_type_label, direction) based on keyword scoring."""
    scores: dict[tuple[str, str], int] = {}
    text_lower = text.lower()
    for keywords, label, direction in JOB_TYPE_RULES:
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            # Short keywords (≤4 chars) use word-boundary match to avoid
            # false positives (e.g. 'SQL' inside 'MySQL').
            if len(kw) <= 4:
                pattern = r'(?<![a-zA-Z])' + re.escape(kw_lower) + r'(?![a-zA-Z])'
                if re.search(pattern, text_lower):
                    score += 1
            elif kw_lower in text_lower:
                score += 1 if len(kw) <= 8 else 2  # longer keywords weighted higher
        if score > 0:
            scores[(label, direction)] = score

    if not scores:
        return ("", "")
    # Return the highest-scoring match
    best = max(scores, key=scores.get)
    return best


def _extract_skills(text: str) -> list[str]:
    """Extract technology skill names mentioned in the text.

    Uses word-boundary matching for short skill names (≤3 chars) to avoid
    false positives like 'R' matching inside 'Engineer'.
    """
    found: list[str] = []
    seen: set[str] = set()
    text_lower = text.lower()

    for _category, skill_list in SKILL_BANK.items():
        for skill in skill_list:
            sk_lower = skill.lower()
            if sk_lower in seen:
                continue
            if len(skill) <= 3:
                # Short skill names: require word boundary match
                pattern = r'(?<![a-zA-Z])' + re.escape(sk_lower) + r'(?![a-zA-Z])'
                if re.search(pattern, text_lower):
                    found.append(skill)
                    seen.add(sk_lower)
            else:
                if sk_lower in text_lower:
                    found.append(skill)
                    seen.add(sk_lower)
    return found


def _extract_keywords(text: str) -> list[str]:
    """Extract non-skill notable keywords (education, campus, perks, etc.)."""
    found: list[str] = []
    seen: set[str] = set()
    for kw_list, label in KEYWORD_PATTERNS:
        for kw in kw_list:
            if kw.lower() in text.lower() and label not in seen:
                found.append(label)
                seen.add(label)
                break  # one match per category
    return found


def _detect_priority(text: str) -> str:
    """Detect priority from urgency signals. Default: "中"."""
    for kw_list, pri in PRIORITY_RULES:
        for kw in kw_list:
            if kw.lower() in text.lower():
                return pri
    return "中"


def _detect_risks(text: str) -> list[str]:
    """Detect potential risk flags."""
    risks: list[str] = []
    for pattern, message in RISK_RULES:
        if re.search(pattern, text):
            risks.append(message)
    return risks


# ── LLM-based JD Parser ─────────────────────────────────────────────────

# Mapping from job type string → direction
_JOB_TYPE_TO_DIRECTION: dict[str, str] = {
    "后端开发": "后端",
    "后端": "后端",
    "前端开发": "前端",
    "前端": "前端",
    "算法": "算法",
    "算法工程师": "算法",
    "AI": "算法",
    "大模型": "算法",
    "AI / 大模型": "算法",
    "算法 / AI": "算法",
    "数据分析": "数据",
    "数据": "数据",
    "数据工程师": "数据",
    "数据开发": "数据",
    "产品": "产品",
    "产品经理": "产品",
    "运营": "运营",
    "增长 / 运营": "运营",
    "客户端": "客户端",
    "客户端开发": "客户端",
    "iOS": "客户端",
    "Android": "客户端",
    "安全": "安全",
    "测试": "其他",
    "测试 / 质量保障": "其他",
    "运维": "其他",
    "运维 / 基础设施": "其他",
    "嵌入式": "其他",
    "嵌入式 / 硬件": "其他",
}


def _map_job_type_to_direction(job_type: str) -> str:
    """Map a job_type string to one of the DIRECTION_OPTIONS values."""
    if not job_type:
        return ""
    # Exact match
    if job_type in _JOB_TYPE_TO_DIRECTION:
        return _JOB_TYPE_TO_DIRECTION[job_type]
    # Fuzzy match: check if any key is contained in job_type or vice versa
    jt_lower = job_type.lower()
    for key, direction in _JOB_TYPE_TO_DIRECTION.items():
        if key.lower() in jt_lower or jt_lower in key.lower():
            return direction
    return ""


def _extract_json(text: str) -> Optional[str]:
    """Try to extract a JSON string from LLM response text.

    Handles:
      - Plain JSON
      - JSON wrapped in ```json ... ``` code fences
      - JSON wrapped in ``` ... ``` code fences
      - Text with JSON object somewhere inside
    """
    if not text:
        return None

    # Strip markdown code fences
    fence_patterns = [
        r"```json\s*\n?(.*?)\n?```",
        r"```\s*\n?(.*?)\n?```",
    ]
    for pattern in fence_patterns:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()

    # Try to find the outermost JSON object
    # Find first '{' and last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return None


def _normalize_llm_result(raw: dict, jd_text: str) -> dict:
    """Normalize and validate the LLM-parsed JSON into the standard format.

    Ensures all expected fields exist with sensible defaults.
    """
    job_type = str(raw.get("job_type", "")).strip()
    direction = _map_job_type_to_direction(job_type)

    # Skills: ensure it's a list of strings
    skills = raw.get("skills", [])
    if not isinstance(skills, list):
        skills = []
    skills = [str(s).strip() for s in skills if str(s).strip()]

    # Keywords: ensure it's a list of strings
    keywords = raw.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k).strip() for k in keywords if str(k).strip()]

    # Risk notes: ensure it's a list of strings
    risk_notes = raw.get("risk_notes", [])
    if not isinstance(risk_notes, list):
        risk_notes = []
    risk_notes = [str(r).strip() for r in risk_notes if str(r).strip()]

    # Priority: normalize to 高/中/低
    priority = str(raw.get("priority", "中")).strip()
    if priority not in ("高", "中", "低"):
        priority = "中"

    return {
        "company": str(raw.get("company", "")).strip(),
        "title": str(raw.get("title", "")).strip(),
        "job_type": job_type,
        "job_type_direction": direction,
        "location": str(raw.get("location", "")).strip(),
        "skills": skills,
        "keywords": keywords,
        "education_requirement": str(raw.get("education_requirement", "")).strip(),
        "deadline": str(raw.get("deadline", "")).strip(),
        "priority": priority,
        "risk_notes": risk_notes,
    }


def parse_jd_with_llm(jd_text: str) -> dict:
    """Parse a job description using LLM (via call_llm_json), with rule-based fallback.

    Uses the call_llm_json() helper for robust JSON extraction — it handles
    markdown code fences, stray text, and other common LLM output quirks.

    If the LLM call fails, the response cannot be parsed as JSON, or
    critical fields (job_type + skills) are missing, the function
    automatically falls back to parse_jd_rule_based() and sets the
    ``_fallback`` flag so the UI can warn the user.

    Args:
        jd_text: The full job description text.

    Returns:
        A dict with keys: company, title, job_type, job_type_direction,
        location, skills, keywords, education_requirement, deadline,
        priority, risk_notes.  When fallback is triggered the dict also
        contains ``_fallback: True`` and ``_fallback_reason: str``.
    """
    from services.llm_client import call_llm_json

    if not jd_text or not jd_text.strip():
        return _empty_llm_result()

    # ── System prompt: role-play as a Chinese JD parsing assistant ─────
    system_prompt = (
        "你是一个专业的求职岗位 JD 解析助手。"
        "你的任务是从用户提供的岗位描述（JD）文本中，提取结构化的关键信息。\n\n"
        "要求：\n"
        "1. 仔细阅读 JD 文本，准确提取以下所有字段\n"
        "2. 如果某个字段在 JD 中没有明确提及，使用空字符串 \"\" 或空数组 []\n"
        "3. **只输出 JSON 对象，不要输出任何解释文字、Markdown 标记或代码块**\n"
        "4. 确保 JSON 格式完全正确，key 和 value 使用双引号\n"
        "5. 技能（skills）只列出明确要求的技术名词，不要包含岗位类型本身"
    )

    # ── User prompt: strict JSON-only instruction + JD text ────────────
    user_prompt = (
        "请解析以下岗位描述（JD），提取结构化信息并输出 JSON。\n\n"
        "输出 JSON 格式（严格遵循，所有字段必须存在）：\n"
        "{\n"
        '  "company": "公司名称（JD 中明确出现的公司名，否则留空）",\n'
        '  "title": "岗位名称（如：后端开发工程师（校招））",\n'
        '  "job_type": "岗位类型（从以下选择最匹配的：后端开发、前端开发、算法/AI、AI/大模型、'
        '数据分析、产品、产品经理、运营/增长、客户端、安全、测试/质量保障、运维/基础设施、嵌入式/硬件）",\n'
        '  "location": "工作城市（如：北京、上海、深圳、杭州、广州、成都等，JD 未提及则留空）",\n'
        '  "skills": ["技能1", "技能2"],\n'
        '  "keywords": ["标签1", "标签2"],\n'
        '  "education_requirement": "学历要求（如：本科及以上、硕士及以上、博士，JD 未提及则留空）",\n'
        '  "deadline": "截止时间（JD 未提及则留空）",\n'
        '  "priority": "高 / 中 / 低（根据急招、尽快到岗、长期有效等关键词判断，默认为 中）",\n'
        '  "risk_notes": ["风险提示1", "风险提示2"]\n'
        "}\n\n"
        "字段说明：\n"
        "- skills: 技术技能名词列表，如 Java、Spring Boot、MySQL、Redis、Kafka 等\n"
        "- keywords: 非技术标签，如 校招、应届、实习、本科、硕士、内推、急招、远程、15薪 等\n"
        "- priority: 出现「急招」「尽快到岗」「立即入职」等关键词→高；"
        "「长期有效」「人才储备」→低；其他→中\n"
        "- risk_notes: 风险提示，如 996、大小周、外包/驻场、薪资面议、社招、要求N年经验 等\n\n"
        "=== JD 原文 ===\n"
        f"{jd_text}\n"
        "=== JD 结束 ===\n\n"
        "请直接输出 JSON 对象。不要包含 ```json 标记或任何其他文字。"
    )

    # ── Build fallback result once (reused on any failure path) ───────
    fallback = _convert_rule_to_llm_format(parse_jd_rule_based(jd_text))

    # ── Call LLM ──────────────────────────────────────────────────────
    try:
        result = call_llm_json(user_prompt, system_prompt=system_prompt)
    except Exception as exc:
        fallback["_fallback"] = True
        fallback["_fallback_reason"] = f"AI 调用异常（{exc}），已回退到规则解析"
        return fallback

    # ── Check for LLM errors ──────────────────────────────────────────
    if not result.get("success"):
        err = result.get("error", "未知错误")
        fallback["_fallback"] = True
        fallback["_fallback_reason"] = f"AI 返回解析失败：{err}"
        return fallback

    # ── Normalize the parsed data ─────────────────────────────────────
    data = result.get("data", {})
    normalized = _normalize_llm_result(data, jd_text)

    # ── Validate critical fields ──────────────────────────────────────
    # Require at least job_type or skills to be non-empty; otherwise the
    # LLM likely didn't understand the task and the result is useless.
    if not normalized.get("job_type") and not normalized.get("skills"):
        fallback["_fallback"] = True
        fallback["_fallback_reason"] = (
            "AI 解析结果缺少关键字段（岗位类型和技能均为空），已回退到规则解析"
        )
        return fallback

    normalized["_fallback"] = False
    normalized["_raw_output"] = result.get("raw_output", "")
    return normalized


def _empty_llm_result() -> dict:
    """Return an empty LLM parse result."""
    return {
        "company": "",
        "title": "",
        "job_type": "",
        "job_type_direction": "",
        "location": "",
        "skills": [],
        "keywords": [],
        "education_requirement": "",
        "deadline": "",
        "priority": "中",
        "risk_notes": [],
    }


def _convert_rule_to_llm_format(rule_result: dict) -> dict:
    """Convert a rule-based parser result to the LLM result format
    (superset, so it can be used identically downstream)."""
    return {
        "company": "",
        "title": "",
        "job_type": rule_result.get("job_type", ""),
        "job_type_direction": rule_result.get("job_type_direction", ""),
        "location": "",
        "skills": rule_result.get("skills", []),
        "keywords": rule_result.get("keywords", []),
        "education_requirement": "",
        "deadline": "",
        "priority": rule_result.get("priority", "中"),
        "risk_notes": rule_result.get("risk_notes", []),
    }


# ── Legacy stub (keeps existing imports working) ────────────────────────

def parse_jd(jd_raw_text: str) -> dict:
    """Legacy wrapper. Calls the rule-based parser and merges into the old format."""
    result = parse_jd_rule_based(jd_raw_text)
    return {
        "company": "",
        "title": "",
        "location": "",
        "salary_range": "",
        "requirements": result.get("skills", []),
        "preferred": result.get("keywords", []),
        "raw": jd_raw_text,
        "job_type": result.get("job_type", ""),
        "priority": result.get("priority", ""),
        "risk_notes": result.get("risk_notes", []),
    }
