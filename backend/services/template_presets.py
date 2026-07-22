"""9 种文档类型的预设默认模板（参考 GB/T 8567-2006）"""

PRESET_TEMPLATES = {
    "srs": {
        "name": "需求规格说明书",
        "doc_type": "srs",
        "description": "软件需求规格说明书标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、项目背景、术语定义和参考资料",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本需求规格说明书的编写目的和预期读者"},
                    {"title": "1.2 项目背景", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明项目的名称、委托单位、开发单位、与其他系统的关系"},
                    {"title": "1.3 术语和定义", "level": 2, "sort_order": 3, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "列出文档中使用的专业术语及其定义"},
                    {"title": "1.4 参考资料", "level": 2, "sort_order": 4, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出编写本文档参考的资料和标准"},
                ],
            },
            {
                "title": "2 总体描述",
                "level": 1, "sort_order": 2,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述产品的总体功能、用户特征、约束和假设",
                "children": [
                    {"title": "2.1 产品描述", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述该系统的主要功能、作用和目标"},
                    {"title": "2.2 用户特征", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统预期用户的特征和技能水平"},
                    {"title": "2.3 约束", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述技术约束、政策约束、硬件限制等"},
                    {"title": "2.4 假设和依赖", "level": 2, "sort_order": 4, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出项目的基本假设和对外部因素的依赖"},
                ],
            },
            {
                "title": "3 功能需求",
                "level": 1, "sort_order": 3,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "详细描述系统的各项功能需求，按模块分类",
                "children": [
                    {"title": "3.1 功能概述", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "概述系统的功能模块划分"},
                    {"title": "3.2 功能模块详述", "level": 2, "sort_order": 2, "content_type": "mixed", "table_config": {}, "content_blocks": [], "content_prompt": "逐一详细描述每个功能模块的输入、处理、输出"},
                ],
            },
            {
                "title": "4 非功能需求",
                "level": 1, "sort_order": 4,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统的性能、安全性、可用性等非功能性需求",
                "children": [
                    {"title": "4.1 性能需求", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述响应时间、吞吐量、并发用户数等性能指标"},
                    {"title": "4.2 安全性需求", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述身份认证、权限控制、数据加密等安全要求"},
                    {"title": "4.3 可用性需求", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统可用性、容错性、易用性等要求"},
                    {"title": "4.4 可维护性需求", "level": 2, "sort_order": 4, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述代码规范、文档要求、模块化等可维护性要求"},
                ],
            },
            {
                "title": "5 数据需求",
                "level": 1, "sort_order": 5,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统的数据实体、数据字典和数据流",
                "children": [
                    {"title": "5.1 数据实体", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出系统中的主要数据实体及其关系"},
                    {"title": "5.2 数据字典", "level": 2, "sort_order": 2, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出各数据元素的名称、类型、长度、说明"},
                ],
            },
            {
                "title": "6 接口需求",
                "level": 1, "sort_order": 6,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统的外部接口需求",
                "children": [
                    {"title": "6.1 用户界面", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述用户界面的要求和设计原则"},
                    {"title": "6.2 硬件接口", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述与外部硬件设备的接口"},
                    {"title": "6.3 软件接口", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述与外部软件系统的接口"},
                    {"title": "6.4 通信接口", "level": 2, "sort_order": 4, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述网络通信协议和接口规范"},
                ],
            },
            {
                "title": "7 附录",
                "level": 1, "sort_order": 7,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料，如待确定事项列表等",
            },
        ],
    },

    "hld": {
        "name": "概要设计文档",
        "doc_type": "hld",
        "description": "软件概要设计文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、适用范围和术语定义",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的和预期读者"},
                    {"title": "1.2 适用范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的适用范围"},
                    {"title": "1.3 术语定义", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出文档中使用的专业术语"},
                ],
            },
            {
                "title": "2 总体设计",
                "level": 1, "sort_order": 2,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统的总体架构、设计原则和技术选型",
                "children": [
                    {"title": "2.1 系统架构", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统的总体架构模式和层次划分"},
                    {"title": "2.2 技术选型", "level": 2, "sort_order": 2, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出各技术组件的选型和理由"},
                    {"title": "2.3 设计约束", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统设计中的约束条件"},
                ],
            },
            {
                "title": "3 模块设计",
                "level": 1, "sort_order": 3,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述各功能模块的划分和概要设计",
                "children": [
                    {"title": "3.1 模块划分", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统的模块划分方案和模块间关系"},
                    {"title": "3.2 模块详述", "level": 2, "sort_order": 2, "content_type": "mixed", "table_config": {}, "content_blocks": [], "content_prompt": "逐一描述各模块的功能、接口和内部逻辑"},
                ],
            },
            {
                "title": "4 接口设计",
                "level": 1, "sort_order": 4,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统内部和外部接口的设计",
                "children": [
                    {"title": "4.1 内部接口", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出模块间的接口定义"},
                    {"title": "4.2 外部接口", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述与外部系统的接口设计"},
                ],
            },
            {
                "title": "5 数据结构设计",
                "level": 1, "sort_order": 5,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统的逻辑数据结构和数据流",
                "children": [
                    {"title": "5.1 逻辑数据结构", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统的逻辑数据模型"},
                    {"title": "5.2 数据流设计", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统的主要数据流向"},
                ],
            },
            {
                "title": "6 运行设计",
                "level": 1, "sort_order": 6,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述系统的运行环境、部署方案和运行控制",
                "children": [
                    {"title": "6.1 运行环境", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出系统的软硬件运行环境要求"},
                    {"title": "6.2 部署方案", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述系统的部署架构和方案"},
                ],
            },
            {
                "title": "7 附录",
                "level": 1, "sort_order": 7,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "dd": {
        "name": "详细设计文档",
        "doc_type": "dd",
        "description": "软件详细设计文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、适用范围和术语定义",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的"},
                    {"title": "1.2 适用范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的适用范围"},
                    {"title": "1.3 术语定义", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出文档中使用的专业术语"},
                ],
            },
            {
                "title": "2 模块详细设计",
                "level": 1, "sort_order": 2,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "详细描述每个模块的内部实现逻辑",
                "children": [
                    {"title": "2.1 模块设计说明", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "逐一说明各模块的功能、算法和处理流程"},
                    {"title": "2.2 类/接口设计", "level": 2, "sort_order": 2, "content_type": "mixed", "table_config": {}, "content_blocks": [], "content_prompt": "以表格和文字描述关键类和接口的设计"},
                ],
            },
            {
                "title": "3 数据库详细设计",
                "level": 1, "sort_order": 3,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述数据库表结构、索引、视图等详细设计",
                "children": [
                    {"title": "3.1 表结构设计", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出所有数据表的字段定义"},
                    {"title": "3.2 索引设计", "level": 2, "sort_order": 2, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出各表的索引设计"},
                    {"title": "3.3 视图与存储过程", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述视图和存储过程的设计"},
                ],
            },
            {
                "title": "4 界面详细设计",
                "level": 1, "sort_order": 4,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述各页面的详细设计",
                "children": [
                    {"title": "4.1 页面清单", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式列出所有页面及其功能"},
                    {"title": "4.2 页面元素描述", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述各页面的布局、控件和交互逻辑"},
                ],
            },
            {
                "title": "5 算法设计",
                "level": 1, "sort_order": 5,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述关键算法的详细设计",
            },
            {
                "title": "6 附录",
                "level": 1, "sort_order": 6,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "dbd": {
        "name": "数据库设计文档",
        "doc_type": "dbd",
        "description": "数据库设计文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、适用范围和术语定义",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的"},
                    {"title": "1.2 适用范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的适用范围"},
                    {"title": "1.3 术语定义", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出数据库相关的专业术语"},
                ],
            },
            {
                "title": "2 数据库总体设计",
                "level": 1, "sort_order": 2,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述数据库选型、设计原则和总体架构",
                "children": [
                    {"title": "2.1 数据库选型", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明数据库选型理由"},
                    {"title": "2.2 设计原则", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述数据库设计遵循的原则和规范"},
                    {"title": "2.3 ER 模型", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述实体关系模型"},
                ],
            },
            {
                "title": "3 表结构设计",
                "level": 1, "sort_order": 3,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出所有数据表的详细结构",
                "children": [
                    {"title": "3.1 表清单", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "列出所有数据表及其简要说明"},
                    {"title": "3.2 表结构详述", "level": 2, "sort_order": 2, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "逐一列出每个表的字段名、类型、长度、约束和说明"},
                ],
            },
            {
                "title": "4 索引设计",
                "level": 1, "sort_order": 4,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出索引设计",
            },
            {
                "title": "5 视图设计",
                "level": 1, "sort_order": 5,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述视图的定义和用途",
            },
            {
                "title": "6 存储过程与触发器",
                "level": 1, "sort_order": 6,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述存储过程和触发器的设计",
            },
            {
                "title": "7 数据安全设计",
                "level": 1, "sort_order": 7,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述数据备份、恢复、权限控制等安全设计",
            },
            {
                "title": "8 附录",
                "level": 1, "sort_order": 8,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "tp": {
        "name": "测试计划",
        "doc_type": "tp",
        "description": "测试计划文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、测试范围和术语定义",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的"},
                    {"title": "1.2 测试范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本次测试的范围和内容"},
                    {"title": "1.3 术语定义", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出测试相关的专业术语"},
                ],
            },
            {
                "title": "2 测试资源",
                "level": 1, "sort_order": 2,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述测试所需的人员、环境、工具等资源",
                "children": [
                    {"title": "2.1 人员安排", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格列出测试人员及其职责"},
                    {"title": "2.2 测试环境", "level": 2, "sort_order": 2, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格列出测试所需的软硬件环境"},
                    {"title": "2.3 测试工具", "level": 2, "sort_order": 3, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格列出测试工具及其用途"},
                ],
            },
            {
                "title": "3 测试策略",
                "level": 1, "sort_order": 3,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述测试策略和方法",
                "children": [
                    {"title": "3.1 测试类型", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述功能测试、性能测试、安全测试等测试类型"},
                    {"title": "3.2 测试方法", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述使用的测试方法和工具"},
                    {"title": "3.3 测试通过标准", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "定义测试通过和失败的判定标准"},
                ],
            },
            {
                "title": "4 测试进度",
                "level": 1, "sort_order": 4,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出测试各阶段的计划时间",
            },
            {
                "title": "5 风险管理",
                "level": 1, "sort_order": 5,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出测试风险和应对措施",
            },
            {
                "title": "6 附录",
                "level": 1, "sort_order": 6,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "ts": {
        "name": "测试方案",
        "doc_type": "ts",
        "description": "测试方案文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、适用范围和术语定义",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的"},
                    {"title": "1.2 适用范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的适用范围"},
                    {"title": "1.3 术语定义", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出测试相关的专业术语"},
                ],
            },
            {
                "title": "2 测试目标",
                "level": 1, "sort_order": 2,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述测试的目标和预期成果",
                "children": [
                    {"title": "2.1 测试目标", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述本次测试的具体目标"},
                    {"title": "2.2 测试范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述测试的范围边界"},
                ],
            },
            {
                "title": "3 测试方案详述",
                "level": 1, "sort_order": 3,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "详细描述各项测试的具体方案",
                "children": [
                    {"title": "3.1 功能测试方案", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述功能测试的具体方案"},
                    {"title": "3.2 性能测试方案", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述性能测试的具体方案"},
                    {"title": "3.3 安全测试方案", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述安全测试的具体方案"},
                    {"title": "3.4 兼容性测试方案", "level": 2, "sort_order": 4, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述兼容性测试的具体方案"},
                ],
            },
            {
                "title": "4 测试数据",
                "level": 1, "sort_order": 4,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述测试数据的准备和设计",
            },
            {
                "title": "5 测试环境",
                "level": 1, "sort_order": 5,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出测试环境配置",
            },
            {
                "title": "6 附录",
                "level": 1, "sort_order": 6,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "tc": {
        "name": "测试用例",
        "doc_type": "tc",
        "description": "测试用例文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明编写目的、适用范围和测试用例编号规则",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的"},
                    {"title": "1.2 用例编号规则", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明测试用例的编号规则"},
                ],
            },
            {
                "title": "2 功能测试用例",
                "level": 1, "sort_order": 2,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出所有功能测试用例（用例编号、模块、测试项、前置条件、操作步骤、预期结果、实际结果、状态）",
            },
            {
                "title": "3 性能测试用例",
                "level": 1, "sort_order": 3,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出性能测试用例",
            },
            {
                "title": "4 安全测试用例",
                "level": 1, "sort_order": 4,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出安全测试用例",
            },
            {
                "title": "5 附录",
                "level": 1, "sort_order": 5,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "tr": {
        "name": "测试记录",
        "doc_type": "tr",
        "description": "测试记录文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明测试记录的目的和范围",
            },
            {
                "title": "2 测试执行情况",
                "level": 1, "sort_order": 2,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述测试执行的总体情况",
                "children": [
                    {"title": "2.1 测试执行概况", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述测试执行的时间、人员、环境"},
                    {"title": "2.2 测试用例执行统计", "level": 2, "sort_order": 2, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式统计测试用例执行情况（总数、通过、失败、阻塞）"},
                ],
            },
            {
                "title": "3 测试记录明细",
                "level": 1, "sort_order": 3,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出每条测试用例的执行记录（用例编号、执行时间、执行人、测试结果、备注）",
            },
            {
                "title": "4 缺陷记录",
                "level": 1, "sort_order": 4,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出发现的缺陷（缺陷编号、描述、严重程度、状态、负责人）",
            },
            {
                "title": "5 附录",
                "level": 1, "sort_order": 5,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },

    "trep": {
        "name": "测试报告",
        "doc_type": "trep",
        "description": "测试报告文档标准模板",
        "chapters": [
            {
                "title": "1 引言",
                "level": 1, "sort_order": 1,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "说明测试报告的目的、范围和术语定义",
                "children": [
                    {"title": "1.1 编写目的", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本文档的编写目的"},
                    {"title": "1.2 测试范围", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "说明本次测试的范围"},
                    {"title": "1.3 术语定义", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "列出测试相关的专业术语"},
                ],
            },
            {
                "title": "2 测试概述",
                "level": 1, "sort_order": 2,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "概述测试的背景、目标和测试环境",
                "children": [
                    {"title": "2.1 测试背景", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述测试的背景信息"},
                    {"title": "2.2 测试目标", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述本次测试的目标"},
                ],
            },
            {
                "title": "3 测试环境",
                "level": 1, "sort_order": 3,
                "content_type": "table", "table_config": {}, "content_blocks": [],
                "content_prompt": "以表格形式列出测试环境配置",
            },
            {
                "title": "4 测试结果",
                "level": 1, "sort_order": 4,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "描述测试的执行结果和统计",
                "children": [
                    {"title": "4.1 测试执行统计", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式统计测试用例执行情况"},
                    {"title": "4.2 功能测试结果", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述功能测试的结果"},
                    {"title": "4.3 性能测试结果", "level": 2, "sort_order": 3, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "描述性能测试的结果"},
                ],
            },
            {
                "title": "5 缺陷分析",
                "level": 1, "sort_order": 5,
                "content_type": "mixed", "table_config": {}, "content_blocks": [],
                "content_prompt": "对发现的缺陷进行统计分析",
                "children": [
                    {"title": "5.1 缺陷统计", "level": 2, "sort_order": 1, "content_type": "table", "table_config": {}, "content_blocks": [], "content_prompt": "以表格形式按严重程度统计缺陷"},
                    {"title": "5.2 缺陷分析", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "分析缺陷的分布和趋势"},
                ],
            },
            {
                "title": "6 评估与建议",
                "level": 1, "sort_order": 6,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "对测试结果进行评估，给出建议",
                "children": [
                    {"title": "6.1 测试评估", "level": 2, "sort_order": 1, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "对测试整体情况进行评估"},
                    {"title": "6.2 改进建议", "level": 2, "sort_order": 2, "content_type": "text", "table_config": {}, "content_blocks": [], "content_prompt": "提出改进建议"},
                ],
            },
            {
                "title": "7 附录",
                "level": 1, "sort_order": 7,
                "content_type": "text", "table_config": {}, "content_blocks": [],
                "content_prompt": "补充说明材料",
            },
        ],
    },
"custom": {
        "name": "自定义文档",
        "doc_type": "custom",
        "description": "根据写作要求自由生成文档，不预设章节结构",
        "chapters": [],
    },
}


def get_preset(doc_type: str) -> dict:
    """获取指定文档类型的预设模板"""
    if doc_type not in PRESET_TEMPLATES:
        raise ValueError(f"未知的文档类型: {doc_type}。支持的类型: {list(PRESET_TEMPLATES.keys())}")
    return PRESET_TEMPLATES[doc_type]


def get_all_presets() -> list[dict]:
    """获取所有预设模板的摘要"""
    return [
        {
            "doc_type": key,
            "name": value["name"],
            "description": value["description"],
            "chapter_count": len(value["chapters"]),
        }
        for key, value in PRESET_TEMPLATES.items()
    ]


DOC_TYPE_LABELS = {
    "srs": "需求规格说明书",
    "hld": "概要设计文档",
    "dd": "详细设计文档",
    "dbd": "数据库设计文档",
    "tp": "测试计划",
    "ts": "测试方案",
    "tc": "测试用例",
    "tr": "测试记录",
    "trep": "测试报告",
    "custom": "自定义文档",
}