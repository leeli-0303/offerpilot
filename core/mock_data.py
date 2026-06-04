"""Mock data for development and demo purposes."""

from datetime import datetime, timedelta

from core.models import (
    Job, JobStatus, ResumeVersion, Application,
    InterviewRecord, InterviewRound, MatchResult, WeeklyReview,
)

now = datetime.now()


# ── Jobs (5) ────────────────────────────────────────────────────────────

def get_mock_jobs() -> list[Job]:
    return [
        Job(
            id="job-001",
            company="字节跳动",
            title="后端开发工程师（校招）",
            status=JobStatus.INTERVIEWING,
            jd_raw_text=(
                "负责字节跳动核心产品的后端服务开发与维护；"
                "参与系统架构设计，解决高并发、高可用等工程问题；"
                "与产品、前端团队紧密协作，推动业务需求落地。"
            ),
            jd_parsed_fields={
                "requirements": ["熟悉至少一门后端语言（Python/Java/Go/C++）", "了解常用数据结构与算法", "有良好的编码习惯和团队协作能力"],
                "preferred": ["有分布式系统经验优先", "有开源项目贡献优先", "有实习经验优先"],
                "education": "本科及以上，计算机相关专业",
            },
            location="北京",
            salary_range="25-40K·15薪",
            tags=["大厂", "内推", "急招"],
            direction="后端",
            priority="高",
            source_url="https://job.toutiao.com/xxx",
            notes="学长内推，HR 反馈很快",
            created_at=now - timedelta(days=21),
            updated_at=now - timedelta(days=1),
        ),
        Job(
            id="job-002",
            company="Google",
            title="Software Engineer, New Grad 2026",
            status=JobStatus.APPLIED,
            jd_raw_text=(
                "Design, develop, test, deploy, maintain, and improve software. "
                "Work on projects that handle massive scale and complexity. "
                "Collaborate with engineers, product managers, and designers across teams."
            ),
            jd_parsed_fields={
                "requirements": ["BS/MS in CS or related field", "Strong coding skills in one of: Java/Python/C++/Go", "Solid understanding of data structures and algorithms"],
                "preferred": ["Internship experience in software development", "Open source contributions", "Experience with distributed systems"],
                "education": "BS or MS in Computer Science or equivalent",
            },
            location="Mountain View, CA",
            salary_range="$130K-$160K",
            tags=["外企", "英语"],
            direction="后端",
            priority="高",
            source_url="https://careers.google.com/xxx",
            notes="已通过简历筛选，等待面试排期",
            created_at=now - timedelta(days=14),
            updated_at=now - timedelta(days=3),
        ),
        Job(
            id="job-003",
            company="阿里巴巴",
            title="Java 开发工程师（淘天集团）",
            status=JobStatus.INTERESTED,
            jd_raw_text=(
                "参与电商平台核心系统设计与开发；"
                "负责业务模块的代码编写、单元测试和性能优化；"
                "协助排查线上问题，保障系统稳定运行。"
            ),
            jd_parsed_fields={
                "requirements": ["精通 Java，熟悉 Spring 生态", "熟悉 MySQL、Redis、Kafka 等中间件", "了解分布式系统基本原理"],
                "preferred": ["有电商项目经验优先", "有大规模系统开发经验优先"],
                "education": "本科及以上，计算机相关专业",
            },
            location="杭州",
            salary_range="20-35K·16薪",
            tags=["大厂", "电商"],
            direction="后端",
            priority="中",
            source_url="https://talent.alibaba.com/xxx",
            notes="JD 很匹配，准备用后端-中文简历投递",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        ),
        Job(
            id="job-004",
            company="腾讯",
            title="前端开发工程师（腾讯云）",
            status=JobStatus.OFFERED,
            jd_raw_text=(
                "负责腾讯云控制台前端开发；"
                "参与组件库建设和前端工程化实践；"
                "与设计师和后端工程师协作完成产品迭代。"
            ),
            jd_parsed_fields={
                "requirements": ["精通 HTML/CSS/JavaScript", "熟悉 React 或 Vue 框架", "了解前端工程化和性能优化"],
                "preferred": ["有 TypeScript 经验优先", "有云产品开发经验优先"],
                "education": "本科及以上",
            },
            location="深圳",
            salary_range="22-38K·14薪",
            tags=["大厂", "内推"],
            direction="前端",
            deadline=now + timedelta(days=7),
            priority="高",
            source_url="https://join.qq.com/xxx",
            notes="已收到正式 Offer，考虑中。薪资还可谈",
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=2),
        ),
        Job(
            id="job-005",
            company="美团",
            title="算法工程师（推荐系统）",
            status=JobStatus.REJECTED,
            jd_raw_text=(
                "参与推荐系统、搜索排序等核心算法研发；"
                "负责特征工程、模型训练及线上部署；"
                "跟踪学术界和工业界前沿技术并落地应用。"
            ),
            jd_parsed_fields={
                "requirements": ["精通 Python/C++", "熟悉主流推荐算法和深度学习框架", "有实际项目经验"],
                "preferred": ["有顶会论文优先", "有大规模推荐系统经验优先"],
                "education": "硕士及以上，计算机/AI相关专业",
            },
            location="北京",
            salary_range="25-40K·15薪",
            tags=["大厂", "AI"],
            direction="算法",
            priority="低",
            source_url="https://zhaopin.meituan.com/xxx",
            notes="三面挂，算法题没做出来。继续刷题",
            created_at=now - timedelta(days=35),
            updated_at=now - timedelta(days=10),
        ),
    ]


# ── ResumeVersions (3) ──────────────────────────────────────────────────

def get_mock_resumes() -> list[ResumeVersion]:
    return [
        ResumeVersion(
            id="resume-001",
            version_name="后端开发-中文",
            file_path="/uploads/resume_backend_cn.pdf",
            parsed_content={
                "raw_text": "教育背景：北京大学 计算机科学与技术 硕士...",
            },
            summary_fields={
                "education": "北京大学 · 计算机科学与技术 · 硕士 · 2026届",
                "skills": ["Python", "Java", "Go", "MySQL", "Redis", "Docker", "Kubernetes"],
                "internships": ["字节跳动 · 后端开发实习生 · 2025.06-2025.09", "阿里巴巴 · 暑期实习生 · 2024.07-2024.09"],
                "projects": ["分布式KV存储系统", "基于Go的微服务网关"],
            },
            tags=["后端", "中文", "主力"],
            target_direction="后端",
            keywords=["Python", "Java", "Go", "MySQL", "Redis", "Docker"],
            highlights=["分布式KV存储系统 · 支持10万QPS", "基于Go的微服务网关 · 日均处理千万请求"],
            created_at=now - timedelta(days=60),
            updated_at=now - timedelta(days=7),
        ),
        ResumeVersion(
            id="resume-002",
            version_name="Backend Engineering-EN",
            file_path="/uploads/resume_backend_en.pdf",
            parsed_content={
                "raw_text": "Education: Peking University, M.S. in Computer Science...",
            },
            summary_fields={
                "education": "Peking University · Computer Science · M.S. · Class of 2026",
                "skills": ["Python", "Java", "Go", "MySQL", "Redis", "Docker", "Kubernetes"],
                "internships": ["ByteDance · Backend Engineer Intern · Jun-Sep 2025", "Alibaba · Summer Intern · Jul-Sep 2024"],
                "projects": ["Distributed KV Store", "Microservice Gateway in Go"],
            },
            tags=["后端", "英文", "外企"],
            target_direction="后端",
            keywords=["Python", "Java", "Go", "MySQL", "Redis", "Docker"],
            highlights=["Distributed KV Store · 100K QPS", "Microservice Gateway in Go · 10M daily requests"],
            created_at=now - timedelta(days=45),
            updated_at=now - timedelta(days=14),
        ),
        ResumeVersion(
            id="resume-003",
            version_name="算法工程师-中文",
            file_path="/uploads/resume_ml_cn.pdf",
            parsed_content={
                "raw_text": "教育背景：北京大学 计算机科学与技术 硕士 研究方向：推荐系统...",
            },
            summary_fields={
                "education": "北京大学 · 计算机科学与技术 · 硕士 · 2026届",
                "skills": ["Python", "C++", "PyTorch", "TensorFlow", "Scikit-learn", "SQL"],
                "internships": ["美团 · 算法实习生 · 2025.03-2025.08"],
                "projects": ["基于Transformer的CTR预估模型", "实时推荐系统A/B实验平台"],
            },
            tags=["算法", "中文", "AI"],
            target_direction="算法",
            keywords=["Python", "C++", "PyTorch", "TensorFlow", "推荐系统"],
            highlights=["基于Transformer的CTR预估模型 · AUC提升3%", "实时推荐系统A/B实验平台 · 支持日均千万级用户"],
            created_at=now - timedelta(days=40),
            updated_at=now - timedelta(days=30),
        ),
    ]


# ── Applications (8) ────────────────────────────────────────────────────

def get_mock_applications() -> list[Application]:
    return [
        Application(
            id="app-001",
            job_id="job-001",
            resume_id="resume-001",
            applied_date=now - timedelta(days=14),
            channel="内推",
            current_stage="技术二面",
            status="二面",
            notes="一面已过，准备二面",
            application_url="https://job.toutiao.com/apply/xxx",
            created_at=now - timedelta(days=14),
            updated_at=now - timedelta(days=1),
        ),
        Application(
            id="app-002",
            job_id="job-002",
            resume_id="resume-002",
            applied_date=now - timedelta(days=10),
            channel="官网",
            current_stage="简历筛选通过",
            status="已投递",
            notes="等待面试排期通知",
            application_url="https://careers.google.com/apply/xxx",
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=3),
        ),
        Application(
            id="app-003",
            job_id="job-004",
            resume_id="resume-001",
            applied_date=now - timedelta(days=25),
            channel="内推",
            current_stage="已发 Offer",
            status="offer",
            notes="薪资 25K*14+股票，回复截止日 5月25日",
            application_url="https://join.qq.com/apply/xxx",
            created_at=now - timedelta(days=25),
            updated_at=now - timedelta(days=2),
        ),
        Application(
            id="app-004",
            job_id="job-005",
            resume_id="resume-003",
            applied_date=now - timedelta(days=28),
            channel="BOSS 直聘",
            current_stage="三面",
            status="终止",
            termination_reason="三面算法题未通过，面试官建议加强动态规划和图论练习",
            notes="三面算法题未通过，HR 反馈可半年后再试",
            created_at=now - timedelta(days=28),
            updated_at=now - timedelta(days=10),
        ),
        Application(
            id="app-005",
            job_id="job-001",
            resume_id="resume-002",
            applied_date=now - timedelta(days=5),
            channel="官网",
            current_stage="简历筛选",
            status="已投递",
            notes="用英文简历也投了一次，增加概率",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        ),
        Application(
            id="app-006",
            job_id="job-002",
            resume_id="resume-001",
            applied_date=now - timedelta(days=7),
            channel="内推",
            current_stage="简历评估",
            status="简历评估",
            notes="请学长帮忙内推，HR 已确认收到简历",
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=7),
        ),
        Application(
            id="app-007",
            job_id="job-003",
            resume_id="resume-001",
            applied_date=now - timedelta(days=2),
            channel="官网",
            current_stage="已投递",
            status="已投递",
            notes="刚投递，等待筛选",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        ),
        Application(
            id="app-008",
            job_id="job-003",
            resume_id="resume-002",
            applied_date=None,
            channel="",
            current_stage="准备投递",
            status="已投递",
            notes="还在改简历，准备这周投",
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        ),
    ]


# ── InterviewRecords (2) ────────────────────────────────────────────────

def get_mock_interviews() -> list[InterviewRecord]:
    return [
        InterviewRecord(
            id="int-001",
            application_id="app-001",
            round=InterviewRound.TECH_1,
            interview_date=now - timedelta(days=5),
            interviewer_feedback="基础扎实，项目经验较好，Go 并发模型理解到位。算法题 medium 难度 15 分钟完成。不足之处：系统设计经验偏少。",
            self_rating=4,
            notes="面试官很 nice，主要问了 Go 的 goroutine 调度和项目中的分布式锁实现",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        ),
        InterviewRecord(
            id="int-002",
            application_id="app-001",
            round=InterviewRound.TECH_2,
            interview_date=now + timedelta(days=2),
            interviewer_feedback="",
            self_rating=0,
            notes="待面试。重点准备系统设计（秒杀系统、Feed流）和项目深挖",
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        ),
    ]


# ── MatchResults (1) ────────────────────────────────────────────────────

def get_mock_match_results() -> list[MatchResult]:
    return [
        MatchResult(
            id="match-001",
            job_id="job-001",
            resume_id="resume-001",
            match_score=82.0,
            matched_points=[
                "后端语言能力匹配（Go/Python/Java）",
                "有字节跳动实习经验，熟悉公司文化",
                "项目经验（分布式KV存储、微服务网关）与岗位方向高度相关",
                "硕士学历满足岗位要求",
            ],
            gaps=[
                "系统设计经验偏少（JD 要求高并发系统架构能力）",
                "未提及消息队列相关项目经验（Kafka/RabbitMQ）",
                "缺少大规模数据处理相关描述",
            ],
            suggestions=[
                "在简历中突出 Go 语言项目经验和并发编程能力",
                "补充消息队列使用经验（或在面试中主动提及相关理解）",
                "建议在简历中添加系统设计相关术语（CAP、一致性哈希、负载均衡）",
                "如有 ACM/编程竞赛经历请补充，该岗位对算法要求较高",
            ],
            created_at=now - timedelta(days=10),
        ),
    ]


# ── WeeklyReviews (1) ───────────────────────────────────────────────────

def get_mock_weekly_reviews() -> list[WeeklyReview]:
    return [
        WeeklyReview(
            id="review-001",
            week_label="2026年第20周",
            date_range="2026.05.11 - 2026.05.17",
            stats={
                "new_jobs": 2,
                "applications_sent": 3,
                "interviews_completed": 1,
                "offers_received": 1,
            },
            highlights=[
                "腾讯发来正式 Offer，薪资 25K*14+股票",
                "字节跳动通过技术一面，进入二面",
                "阿里巴巴完成投递",
            ],
            next_week_focus=[
                "字节跳动技术二面（5月20日）",
                "决定是否接受腾讯 Offer（截止 5月25日）",
                "Google 准备英文技术面试",
                "继续投递 2-3 个外企岗位",
            ],
            created_at=now - timedelta(days=1),
        ),
    ]


# ── Legacy alias (keeps existing data_store code working) ───────────────

def get_mock_reports() -> list:
    """Deprecated: use get_mock_match_results() and get_mock_weekly_reviews() instead."""
    return []
